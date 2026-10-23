#!/usr/bin/env python3
# ==========================================================
# FILE: C:\fanding\fanding_fetch.py   (FANDING_FETCH_V1.2.0)
#   저장소 위치: bot_office/fanding_fetch_win.py (서버에선 실행하지 않음 · 윈도우가 GitHub 에서 내려받음)
# 윈도우 PC 전용: 팬딩 가격표 이미지를 가져와 사무실 서버로 보내고 종료
# 1.1.0: 글 안의 큰 이미지를 모두 보냄 → 서버가 가격표만 골라냄 (이미지 순서가 바뀌어도 OK)
# 1.2.0: 시리즈 목록 끝까지 내려 모든 글을 모은 뒤 글 번호가 가장 큰 것(= 가장 최근 글)을 고름
#
#  준비 (한 번만)
#    py -m pip install playwright
#    py -m playwright install chromium
#    py fanding_fetch.py login     ← 창이 뜨면 네이버로 팬딩 로그인 후 창 닫기
#    py fanding_fetch.py test      ← 가격표를 찾는지 확인 (서버로 안 보냄)
#
#  매일 (작업 스케줄러가 자동 실행)
#    py fanding_fetch.py run       ← 새 가격표를 찾을 때까지 몇 분 간격 재시도, 보내면 종료
#
#  설정: 같은 폴더의 config.json
#    {"office_url": "https://사무실주소", "upload_token": "서버와 같은 암호",
#     "series_url": "https://fanding.kr/@laofus/series/1933/", "stop_at": "11:30",
#     "retry_min": 5, "headless": true}
# ==========================================================
import hashlib, json, re, sys, time, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path

VERSION = "1.2.0"
HERE = Path(__file__).resolve().parent
CFG = HERE / "config.json"
PROFILE = HERE / "browser_profile"      # 팬딩 로그인이 저장되는 전용 브라우저 폴더
LAST = HERE / "last_sent.txt"
DEBUG = HERE / "debug"


def log(*a):
    print(datetime.now().strftime("%m-%d %H:%M:%S"), *a, flush=True)


def cfg():
    c = {"series_url": "https://fanding.kr/@laofus/series/1933/", "stop_at": "11:30", "retry_min": 5, "headless": True}
    c.update(json.loads(CFG.read_text(encoding="utf-8")))
    return c


def post_server(c, data=b"", note="", post="", batch="", idx=0, count=0):
    url = c["office_url"].rstrip("/") + "/api/fanding/upload"
    h = {"X-Fanding-Token": c["upload_token"], "Content-Type": "application/octet-stream"}
    if note:
        h["X-Fanding-Note"] = urllib.parse.quote(note)
    if post:
        h["X-Fanding-Post"] = urllib.parse.quote(post, safe=":/@?=&%")
    if batch:
        h.update({"X-Fanding-Batch": batch, "X-Fanding-Index": str(idx), "X-Fanding-Count": str(count)})
    req = urllib.request.Request(url, data=data or b"-", headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def browser(p, headless):
    PROFILE.mkdir(exist_ok=True)
    return p.chromium.launch_persistent_context(
        str(PROFILE), headless=headless, locale="ko-KR", timezone_id="Asia/Seoul",
        viewport={"width": 1280, "height": 1800}, args=["--disable-blink-features=AutomationControlled"])


def _post_links(page, creator, series_path):
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    out = {}
    for u in hrefs:
        path = urllib.parse.urlparse(u).path.rstrip("/")
        m = re.search(r"/(?:post|posts|p|series/\d+)/(\d+)$", path)
        if creator in path and path != series_path and m:
            out[u.split("?")[0].split("#")[0]] = int(m.group(1))
    return out


def latest_post_url(page, series_url):
    """시리즈의 글을 끝까지 모아서 글 번호가 가장 큰(=가장 최근) 글부터 돌려줌"""
    page.goto(series_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    for label in ("최신순", "최신"):          # 정렬 버튼이 있으면 최신순으로
        try:
            btn = page.get_by_text(label, exact=True)
            if btn.count():
                btn.first.click(timeout=3000); page.wait_for_timeout(2500); break
        except Exception:
            pass
    m = re.search(r"fanding\.kr/(@[^/]+)/", series_url)
    creator = m.group(1) if m else "@"
    series_path = urllib.parse.urlparse(series_url).path.rstrip("/")
    links, same = {}, 0
    for _ in range(60):                        # 목록 끝까지 내리기 (더 안 늘어나면 멈춤)
        before = len(links)
        links.update(_post_links(page, creator, series_path))
        for label in ("더보기", "더 보기"):
            try:
                more = page.get_by_text(label, exact=True)
                if more.count():
                    more.first.click(timeout=2000); page.wait_for_timeout(1500)
            except Exception:
                pass
        page.mouse.wheel(0, 4000); page.wait_for_timeout(900)
        same = same + 1 if len(links) == before else 0
        if same >= 4:
            break
    posts = sorted(links, key=lambda u: links[u], reverse=True)
    log(f"시리즈 글 {len(posts)}개 발견 · 최신 글 번호 {links[posts[0]] if posts else '-'}")
    return posts


def looks_logged_out(page):
    t = page.inner_text("body")[:4000]
    return ("로그인하고" in t or "익명의 팬" in t) and "로그아웃" not in t


def grab_images(page, post_url, limit=8):
    """글 안의 큰 이미지를 위에서부터 모두 가져옴 (가격표 판별은 서버가 함)"""
    page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    for _ in range(6):
        page.mouse.wheel(0, 1200); page.wait_for_timeout(600)
    imgs = page.eval_on_selector_all(
        "img", "els => els.map((e,i) => ({i, src: e.currentSrc || e.src, w: e.naturalWidth, h: e.naturalHeight}))")
    cands = [x for x in imgs if x["w"] >= 300 and x["h"] >= 300][:limit]
    out, seen = [], set()
    els = page.query_selector_all("img")
    for x in cands:
        data = None
        if x["src"].startswith("http"):
            try:
                r = page.context.request.get(x["src"], headers={"Referer": post_url}, timeout=30000)
                if r.ok:
                    data = r.body()
            except Exception as e:
                log("이미지 직접 받기 실패, 화면 캡처로 대신:", e)
        if not data or len(data) < 5000:
            try:
                els[x["i"]].scroll_into_view_if_needed()
                data = els[x["i"]].screenshot(type="jpeg", quality=95)
            except Exception as e:
                log("캡처 실패:", e); continue
        h = hashlib.sha256(data).hexdigest()
        if h not in seen:
            seen.add(h); out.append(data)
    return out, imgs


def once(c, upload=True):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = browser(p, c["headless"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            posts = latest_post_url(page, c["series_url"])
            if looks_logged_out(page):
                return "logged_out", None
            if not posts:
                DEBUG.mkdir(exist_ok=True)
                page.screenshot(path=str(DEBUG / "series.png"), full_page=True)
                (DEBUG / "series.html").write_text(page.content(), encoding="utf-8")
                return "no_posts", None
            log("찾은 글:", posts[:3])
            images, imgs = grab_images(page, posts[0])
            if not images:
                DEBUG.mkdir(exist_ok=True)
                page.screenshot(path=str(DEBUG / "post.png"), full_page=True)
                (DEBUG / "post_imgs.json").write_text(json.dumps(imgs, ensure_ascii=False, indent=1), encoding="utf-8")
                return "no_image", None
            sha = hashlib.sha256(b"".join(hashlib.sha256(d).digest() for d in images)).hexdigest()
            if not upload:
                folder = HERE / "test_images"
                folder.mkdir(exist_ok=True)
                for old in folder.glob("*.jpg"):
                    old.unlink()
                for i, d in enumerate(images, 1):
                    (folder / f"image_{i}.jpg").write_bytes(d)
                return "test_ok", f"{len(images)}장 → {folder}"
            if LAST.exists() and LAST.read_text().strip() == sha:
                return "same_as_last", None
            for i, d in enumerate(images, 1):
                res = post_server(c, d, post=posts[0], batch=sha[:16], idx=i, count=len(images))
                if not res.get("ok"):
                    return "server_error", str(res)
            LAST.write_text(sha)
            return "sent", f"{len(images)}장 · {posts[0]}"
        finally:
            ctx.close()


def cmd_login():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = browser(p, False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://fanding.kr/", timeout=60000)
        print("\n열린 창에서 [로그인] → 네이버로 로그인 하세요.")
        print("로그인이 끝나고 가격표 시리즈가 보이면 이 검은 창에서 Enter 를 누르세요.\n")
        input()
        ctx.close()
    print("로그인 정보가 저장됐어요. 이제 'py fanding_fetch.py test' 로 확인해 보세요.")


def cmd_run():
    c = cfg()
    stop = datetime.now().replace(hour=int(c["stop_at"][:2]), minute=int(c["stop_at"][3:5]), second=0)
    warned = False
    while True:
        try:
            r, info = once(c)
        except Exception as e:
            r, info = "error", f"{type(e).__name__}: {e}"
        log("결과:", r, info or "")
        if r == "sent":
            return
        if r == "logged_out" and not warned:
            warned = True
            try:
                post_server(c, note="팬딩 로그인이 풀렸어요. PC에서 'py fanding_fetch.py login' 을 다시 해 주세요.")
            except Exception as e:
                log("서버 알림 실패:", e)
        if datetime.now() >= stop:
            msg = {"same_as_last": "새 가격표 글이 아직 없어요 (마지막 보낸 것과 같음)",
                   "no_posts": "시리즈 글 목록을 못 찾았어요 (debug 폴더 확인)",
                   "no_image": "글 안에서 가격표 이미지를 못 찾았어요 (debug 폴더 확인)"}.get(r, f"가져오기 실패: {r} {info or ''}")
            try:
                post_server(c, note=f"{c['stop_at']}까지 시도했지만 실패 · {msg}")
            except Exception as e:
                log("서버 알림 실패:", e)
            return
        time.sleep(int(c["retry_min"]) * 60)


if __name__ == "__main__":
    cmd = (sys.argv[1:] or ["run"])[0]
    log(f"팬딩 가져오기 v{VERSION} · {cmd}")
    if cmd == "login":
        cmd_login()
    elif cmd == "test":
        r, info = once(cfg(), upload=False)
        print("결과:", r, info or "")
        if r == "test_ok":
            print("test_images 폴더의 사진들 중에 가격표가 들어 있는지 확인하세요. (순서는 상관없어요)")
    elif cmd == "send":       # 지금 바로 1번 보내기 (같은 그림이어도 다시 보냄)
        LAST.unlink(missing_ok=True)
        print("결과:", *once(cfg()))
    else:
        cmd_run()
