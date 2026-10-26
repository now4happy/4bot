#!/usr/bin/env python3
# ==========================================================
# FILE: C:\fanding\fanding_vr6.py   (FANDING_VR6_WIN_V1.0.0)
#   저장소 위치: bot_office/fanding_vr6_win.py (서버에선 실행하지 않음 · 윈도우에 GitHub 에서 내려받아 fanding_vr6.py 로 저장)
# 윈도우 PC 전용: 팬딩 VR6기(TQQQ) 게시글의 표 이미지를 가져와 사무실 서버로 보냄 (2주에 한 번)
#   - 기존 P 가격표 수집기(fanding_fetch.py)와 별개 프로그램. 같은 폴더·같은 config.json·같은 로그인(browser_profile)을 씀.
#   - 진행일은 서버가 관리. 실행하면 먼저 서버에 '오늘 진행일인가?' 물어보고, 아니면 바로 끝남(브라우저도 안 열음).
#   - 진행일이면 시리즈의 가장 최근 글(글 번호 최대)의 큰 이미지를 모두 올림. 이미 처리한 글 번호 이하면 새 글을 기다림.
#
#  준비 (한 번만. P 수집기를 이미 쓰고 있으면 설치·로그인은 이미 되어 있음)
#    py fanding_vr6.py test     ← 글·이미지를 찾는지 확인 (서버와 대화 안 함, test_vr6 폴더에 저장)
#
#  평소: run.bat 의 맨 위에 한 줄 추가 →  py fanding_vr6.py run >> fetch_log.txt 2>&1
#        (진행일이 아니면 1초 만에 끝나서 기존 P 수집기에 영향이 없음)
#  수동: py fanding_vr6.py run     진행일이면 진행 · py fanding_vr6.py send   진행일과 상관없이 최신 글 보내기
#
#  설정: 같은 폴더의 config.json (office_url·upload_token 은 P 와 같음). VR6 용 항목은 모두 선택:
#    "vr6_post_url": "https://fanding.kr/@laofus/post/226323/"   (시리즈 주소를 모를 때 이 글에서 시리즈를 찾음)
#    "vr6_series_url": "https://fanding.kr/@laofus/series/숫자/"  (알면 이걸 쓰는 게 가장 확실)
#    "vr6_stop_at": "23:00"  "retry_min": 5  "headless": true
# ==========================================================
import hashlib, json, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = "1.0.0"
HERE = Path(__file__).resolve().parent
CFG = HERE / "config.json"
PROFILE = HERE / "browser_profile"
TEST_DIR = HERE / "test_vr6"
DEBUG = HERE / "debug_vr6"
KST = timezone(timedelta(hours=9))


def log(*a):
    print(datetime.now().strftime("%m-%d %H:%M:%S"), *a, flush=True)


def cfg():
    c = {"vr6_post_url": "https://fanding.kr/@laofus/post/226323/", "vr6_series_url": "", "vr6_stop_at": "23:00",
         "retry_min": 5, "headless": True}
    c.update(json.loads(CFG.read_text(encoding="utf-8")))
    return c


def post_id(url):
    m = re.search(r"/(?:post|posts|p)/(\d+)", url or "") or re.search(r"/series/\d+/(\d+)", url or "")
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------- 서버와 대화 (기존 /api/fanding/upload 한 곳만 사용)
def call(c, kind, data=b"-", post="", idx=0, count=0, note=""):
    h = {"X-Fanding-Token": c["upload_token"], "X-Fanding-Kind": kind, "X-Fanding-Version": VERSION,
         "Content-Type": "application/octet-stream"}
    if post:
        h["X-Fanding-Post"] = urllib.parse.quote(post, safe=":/@?=&%")
    if idx:
        h["X-Fanding-Index"], h["X-Fanding-Count"] = str(idx), str(count)
    if note:
        h["X-Fanding-Note"] = urllib.parse.quote(note)
        h.pop("X-Fanding-Kind")                    # 알림은 기존 P 알림 경로(윈도우 PC 알림 메시지)로 보냄
    req = urllib.request.Request(c["office_url"].rstrip("/") + "/api/fanding/upload", data=data or b"-", headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def tell(c, text):
    try:
        call(c, "vr6", note="[VR6] " + text)
    except Exception as e:
        log("서버 알림 실패:", type(e).__name__)


# ---------------------------------------------------------- 브라우저 (P 수집기와 같은 방식)
def browser(p, headless):
    PROFILE.mkdir(exist_ok=True)
    return p.chromium.launch_persistent_context(
        str(PROFILE), headless=headless, locale="ko-KR", timezone_id="Asia/Seoul",
        viewport={"width": 1280, "height": 1800}, args=["--disable-blink-features=AutomationControlled"])


def looks_logged_out(page):
    t = page.inner_text("body")[:4000]
    return ("로그인하고" in t or "익명의 팬" in t) and "로그아웃" not in t


def find_series(page, post_url):
    """VR6 글 안의 시리즈 링크를 찾아 시리즈 주소를 돌려줌 (없으면 빈 문자열)"""
    page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    found = []
    for u in hrefs:
        path = urllib.parse.urlparse(u).path.rstrip("/")
        if re.fullmatch(r"/@[^/]+/series/\d+", path) and u.split("?")[0] not in found:
            found.append(u.split("?")[0])
    log("글 안의 시리즈 링크:", found or "없음")
    return found[0] if found else ""


def _post_links(page, creator, series_path):
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    out = {}
    for u in hrefs:
        path = urllib.parse.urlparse(u).path.rstrip("/")
        m = re.search(r"/(?:post|posts|p|series/\d+)/(\d+)$", path)
        if creator in path and path != series_path and m:
            out[u.split("?")[0].split("#")[0]] = int(m.group(1))
    return out


def list_posts(page, series_url):
    """시리즈의 글을 끝까지 모아 글 번호가 큰(최신) 순서로"""
    page.goto(series_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)
    for label in ("최신순", "최신"):
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
    for _ in range(40):
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
    log(f"시리즈 글 {len(posts)}개 · 최신 글 번호 {links[posts[0]] if posts else '-'}")
    return posts


def grab_images(page, post_url, limit=8):
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
    return out


def fetch_latest(c, last_post_id, force):
    """브라우저로 최신 글을 찾아 (결과, 글주소, 이미지들). 결과: ok / logged_out / no_series / no_posts / no_new_post / no_image"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = browser(p, c["headless"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            series = (c.get("vr6_series_url") or "").strip()
            if not series:
                series = find_series(page, c["vr6_post_url"])
                if looks_logged_out(page):
                    return "logged_out", "", []
                if not series:
                    DEBUG.mkdir(exist_ok=True)
                    page.screenshot(path=str(DEBUG / "vr6_post.png"), full_page=True)
                    return "no_series", "", []
            posts = list_posts(page, series)
            if looks_logged_out(page):
                return "logged_out", "", []
            if not posts:
                DEBUG.mkdir(exist_ok=True)
                page.screenshot(path=str(DEBUG / "vr6_series.png"), full_page=True)
                return "no_posts", series, []
            newest = posts[0]
            if post_id(newest) <= int(last_post_id) and not force:
                return "no_new_post", newest, []
            images = grab_images(page, newest)
            if looks_logged_out(page):
                return "logged_out", newest, []
            return ("ok" if images else "no_image"), newest, images
        finally:
            ctx.close()


def run_once(c, force=False, test=False, fetcher=fetch_latest):
    """돌려주는 값: (결과, 설명). 결과: sent / test_ok / not_due / 그 외는 실패 이유"""
    info = {"last_post_id": 0, "cycle": "-"} if test else (call(c, "vr6-status").get("vr6") or {})
    if not info:
        return "server_error", "서버가 VR6 를 모릅니다 (서버 업데이트 필요)"
    if not info.get("state_ok", True):
        log("주의: 서버 VR6 상태 파일을 웹서버가 읽지 못합니다 (권한 확인)")
    due = bool(info.get("due")) or force
    if not due and not test:
        return "not_due", f"다음 진행일 {info.get('cycle')}"
    result, post, images = fetcher(c, info.get("last_post_id", 0), force or bool(info.get("force")) or test)
    if result != "ok":
        return result, post
    log(f"글 {post} · 이미지 {len(images)}장")
    if test:
        TEST_DIR.mkdir(exist_ok=True)
        for i, d in enumerate(images, 1):
            (TEST_DIR / f"vr6_{post_id(post)}_{i}.jpg").write_bytes(d)
        return "test_ok", f"{post} · {len(images)}장 → test_vr6 폴더"
    for i, d in enumerate(images, 1):
        if not call(c, "vr6", d, post=post, idx=i, count=len(images)).get("ok"):
            return "server_error", f"이미지 {i}번 전송 실패"
    if not call(c, "vr6-done", post=post, count=len(images)).get("ok"):
        return "server_error", "완료 표시 실패"
    return "sent", f"{post} · {len(images)}장"


FAIL_TEXT = {"logged_out": "팬딩 로그인이 풀렸어요. PC에서 py fanding_fetch.py login 을 다시 해 주세요",
             "no_series": "글에서 시리즈 링크를 못 찾았어요. config.json 에 vr6_series_url 을 넣어 주세요 (debug_vr6 폴더 확인)",
             "no_posts": "시리즈의 글 목록을 못 찾았어요 (debug_vr6 폴더 확인)",
             "no_new_post": "새 VR6 글이 아직 없어요 (마지막 처리한 글과 같음)",
             "no_image": "최신 글에서 표 이미지를 못 찾았어요"}


def cmd_run(force=False):
    c = cfg()
    h, m = map(int, c.get("vr6_stop_at", "23:00").split(":"))
    stop = datetime.now(KST).replace(hour=h, minute=m, second=0, microsecond=0)
    warned = set()
    while True:
        try:
            result, info = run_once(c, force=force)
        except Exception as e:
            result, info = "error", f"{type(e).__name__}: {str(e)[:120]}"
        log("결과:", result, info or "")
        if result in ("sent", "not_due"):
            return
        if result in ("logged_out", "no_series") and result not in warned:
            warned.add(result)
            tell(c, FAIL_TEXT[result])
        if datetime.now(KST) >= stop:
            tell(c, f"{c.get('vr6_stop_at', '23:00')}까지 시도했지만 못 가져왔어요 · " + FAIL_TEXT.get(result, f"{result} {info or ''}")[:200])
            return
        time.sleep(int(c["retry_min"]) * 60)


def cmd_login():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = browser(p, False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://fanding.kr/", timeout=60000)
        print("\n열린 창에서 [로그인] → 네이버로 로그인 하세요. (P 수집기와 같은 로그인 폴더를 씁니다)")
        print("로그인이 끝나고 VR6 글이 보이면 이 검은 창에서 Enter 를 누르세요.\n")
        input()
        ctx.close()


if __name__ == "__main__":
    cmd = (sys.argv[1:] or ["run"])[0]
    log(f"팬딩 VR6 v{VERSION} · {cmd}")
    if cmd == "login":
        cmd_login()
    elif cmd == "test":
        r, i = run_once(cfg(), test=True)
        print("결과:", r, i or "")
        if r == "test_ok":
            print("test_vr6 폴더의 그림에 VR6 표가 들어 있는지 확인하세요.")
    elif cmd == "send":
        cmd_run(force=True)
    else:
        cmd_run()
