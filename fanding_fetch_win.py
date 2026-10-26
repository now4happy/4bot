#!/usr/bin/env python3
# ==========================================================
# FILE: C:\fanding\fanding_fetch.py   (FANDING_FETCH_V1.5.0)
#   저장소 위치: bot_office/fanding_fetch_win.py (서버에선 실행하지 않음 · 윈도우가 GitHub 에서 내려받음)
# 윈도우 PC 전용: 팬딩 가격표 이미지를 가져와 사무실 서버로 보내고 종료
# 1.1.0: 글 안의 큰 이미지를 모두 보냄 → 서버가 가격표만 골라냄 (이미지 순서가 바뀌어도 OK)
# 1.2.0: 시리즈 목록 끝까지 내려 모든 글을 모은 뒤 글 번호가 가장 큰 것(= 가장 최근 글)을 고름
# 1.4.0: 매일 실행 끝에 과거 글 10개씩 천천히(글마다 20~40초 쉬며) 보내 매매 규칙 분석용 기록 쌓기
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
import hashlib, json, random, re, sys, time, urllib.parse, urllib.request
from datetime import timedelta, timezone
from datetime import datetime
from pathlib import Path

VERSION = "1.5.0"
HERE = Path(__file__).resolve().parent
CFG = HERE / "config.json"
PROFILE = HERE / "browser_profile"      # 팬딩 로그인이 저장되는 전용 브라우저 폴더
LAST = HERE / "last_sent.txt"
BACKFILL = HERE / "backfill_done.json"     # 이미 보낸 과거 글 목록
DEBUG = HERE / "debug"


def log(*a):
    print(datetime.now().strftime("%m-%d %H:%M:%S"), *a, flush=True)


def cfg():
    c = {"series_url": "https://fanding.kr/@laofus/series/1933/", "stop_at": "11:30", "retry_min": 5, "headless": True,
         "backfill_per_day": 10}
    c.update(json.loads(CFG.read_text(encoding="utf-8")))
    return c


def post_server(c, data=b"", note="", post="", batch="", idx=0, count=0, mode="live", request=None):
    url = c["office_url"].rstrip("/") + "/api/fanding/upload"
    h = {"X-Fanding-Token": c["upload_token"], "Content-Type": "application/octet-stream"}
    if note:
        h["X-Fanding-Note"] = urllib.parse.quote(note)
    if post:
        h["X-Fanding-Post"] = urllib.parse.quote(post, safe=":/@?=&%")
    if batch:
        h.update({"X-Fanding-Batch": batch, "X-Fanding-Index": str(idx), "X-Fanding-Count": str(count)})
    if request:
        h["X-Fanding-Request"] = request["id"]
        h["X-Fanding-Expected"] = request["expected"]
    if mode == "history":
        h["X-Fanding-Mode"] = "history"
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


def grab_images(page, post_url, limit=16):
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


def control(c, stage="idle", request_id=""):
    data = json.dumps({"stage":stage, "request_id":request_id, "version":VERSION}).encode()
    req = urllib.request.Request(c["office_url"].rstrip("/") + "/api/fanding/control", data=data,
                                 headers={"X-Fanding-Token":c["upload_token"], "Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=30) as reply:
        return json.load(reply)


def once(c, upload=True, request=None):
    from playwright.sync_api import sync_playwright
    def stage(name):
        if upload and request:
            control(c, name, request["id"])
    stage("connecting")
    with sync_playwright() as p:
        ctx = browser(p, c["headless"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            stage("listing")
            posts = latest_post_url(page, c["series_url"])
            if looks_logged_out(page):
                return "logged_out", None
            if not posts:
                return "no_posts", None
            # Publication date is not the price sheet's close date: Saturday can be Monday's material.
            candidates = posts[:max(1, min(5, int(c.get("recent_posts", 3))))]
            total = 0
            for post in candidates:
                stage("images")
                images, _ = grab_images(page, post)
                if looks_logged_out(page):
                    return "logged_out", None
                if not images:
                    continue
                if not upload:
                    folder = HERE / "test_images"; folder.mkdir(exist_ok=True)
                    for i, image in enumerate(images, 1):
                        (folder / f"post_{total}_image_{i}.jpg").write_bytes(image)
                else:
                    stage("uploading")
                    sha = hashlib.sha256((post + (request or {}).get("id", "")).encode()).hexdigest()
                    for i, image in enumerate(images, 1):
                        reply = post_server(c, image, post=post, batch=sha[:16], idx=i, count=len(images), request=request)
                        if not reply.get("ok"):
                            return "server_error", None
                total += len(images)
                if upload and request:
                    # Wait for server acknowledgement before sending older posts; reduce paid AI calls.
                    for _ in range(60):
                        ack = control(c, "parsing", request["id"])
                        if ack.get("ready"):
                            return "sent", f"필요 종가일 자료 확보 · {total}장 전송"
                        if not ack.get("pending_images"):
                            break
                        time.sleep(30)
                    else:
                        return "server_error", "서버 판독 대기30분 초과"
            return ("sent" if upload else "test_ok", f"{total}장 / 최근 {len(candidates)}개 글") if total else ("no_image", None)
        finally:
            ctx.close()


def watch(stay_open=False):
    # One persistent worker per PC; existing daily task may start another instance safely.
    lock = (HERE / "watch.lock").open("a+b")
    lock.seek(0); lock.write(b"0"); lock.flush(); lock.seek(0)
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("대기 프로그램이 이미 실행 중입니다."); lock.close(); return
    completed = set()
    start = datetime.now(timezone(timedelta(hours=9)))
    settings = cfg()
    stop_h, stop_m = map(int, settings.get("stop_at", "11:30").split(":"))
    minimum_end = start + timedelta(hours=1)
    stop = max(start.replace(hour=stop_h, minute=stop_m, second=0, microsecond=0), minimum_end)
    log("작업 시작: 최소1시간 유지 · 당일 자료 확보·과거 수집 완료 후 자동 종료" if not stay_open else "상시 대기 모드")
    try:
        while True:
            try:
                c = cfg()
                reply = control(c, LAST_STAGE["value"])
                request = reply.get("request")
                if request and request["id"] not in completed:
                    try:
                        result, info = once(c, request=request)
                    except Exception as exc:
                        result, info = "error", type(exc).__name__
                    control(c, result, request["id"])
                    completed.add(request["id"])
                    if len(completed) > 100: completed = {request["id"]}
                    log("수집 결과:", result, info or "")
                    # Keep failure visible between heartbeats; do not claim parsing success on upload.
                    c["last_stage"] = result
                    LAST_STAGE["value"] = result
                reply = control(c, LAST_STAGE["value"])
                day = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
                hist = HERE / "backfill_day.txt"
                if reply.get("ready") and 8 <= datetime.now(timezone(timedelta(hours=9))).hour < 12 and (not hist.exists() or hist.read_text() != day):
                    c["watch_mode"] = True
                    try:
                        backfill(c)
                    except Exception as exc:
                        log("과거 수집 실패(오늘 자료는 확보됨):", type(exc).__name__)
                    hist.write_text(day)
                    LAST_STAGE["value"] = "sent"
                if not stay_open:
                    final = control(c, LAST_STAGE["value"])
                    if final.get("ready") and datetime.now(timezone(timedelta(hours=9))) >= minimum_end:
                        try:
                            control(c, "daily_done")
                            post_server(c, note="오늘 필요 자료 확보·PC 수집 작업 완료. 수집기를 자동 종료합니다. 재판독이 필요하면 PC에서 run.bat를 다시 실행하세요.")
                        except Exception:
                            log("완료 알림 전송 실패 · 확보된 자료는 서버에서 확인")
                        log("오늘 작업 완료 · 자동 종료")
                        return
                    if datetime.now(timezone(timedelta(hours=9))) >= stop:
                        control(c, "daily_stopped")
                        post_server(c, note="오늘 자료 미확보 상태로 종료 시각에 도달했습니다. /진단 확인 후 필요시 PC run.bat를 다시 실행하세요.")
                        return
            except Exception as exc:
                log("서버 연결 실패:", type(exc).__name__, "주소·네트워크·서버 업데이트 확인")
                if not stay_open and datetime.now(timezone(timedelta(hours=9))) >= stop:
                    log("종료시각 도달 · 서버 연결 실패는 fetch_log.txt 확인")
                    return
            time.sleep(30)
    finally:
        lock.close()


LAST_STAGE = {"value":"idle"}


def backfill(c, n=None):
    """과거 글 n개를 최신→과거 순서로 천천히 보냄 (알림·주문 없이 서버에 기록만)"""
    n = int(c.get("backfill_per_day", 10) if n is None else n)
    if n <= 0:
        return
    from playwright.sync_api import sync_playwright
    done = set(json.loads(BACKFILL.read_text(encoding="utf-8"))) if BACKFILL.exists() else set()
    sent = 0
    with sync_playwright() as p:
        ctx = browser(p, c["headless"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            if c.get("watch_mode"): control(c, "history")
            posts = latest_post_url(page, c["series_url"])
            if looks_logged_out(page) or not posts:
                log("과거 수집: 로그인 풀림 또는 글 목록 없음 → 건너뜀"); return
            todo = [u for u in posts[1:] if u not in done][:n]
            for u in todo:
                if c.get("watch_mode"): control(c, "history")
                time.sleep(random.uniform(20, 40))        # 사람이 보듯 천천히
                try:
                    images, _ = grab_images(page, u)
                    b = hashlib.sha256(u.encode()).hexdigest()[:16]
                    for i, d in enumerate(images, 1):
                        post_server(c, d, post=u, batch=b, idx=i, count=len(images), mode="history")
                    done.add(u); sent += 1
                    BACKFILL.write_text(json.dumps(sorted(done)), encoding="utf-8")
                    log(f"과거 글 보냄 {sent}/{len(todo)}: {u} ({len(images)}장)")
                except Exception as e:
                    log("과거 글 실패:", u, e)
            left = len([u for u in posts[1:] if u not in done])
        finally:
            ctx.close()
    if sent:
        try:
            post_server(c, note=f"과거 가격표 글 {sent}개 보냄 · 남은 글 {left}개")
        except Exception as e:
            log("서버 알림 실패:", e)


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
    watch()


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
    elif cmd == "backfill":   # 과거 글 지금 바로 보내기 (예: py fanding_fetch.py backfill 3)
        backfill(cfg(), int(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif cmd == "watch":
        watch(stay_open=True)
    elif cmd == "send":       # 지금 바로 1번 보내기 (같은 그림이어도 다시 보냄)
        LAST.unlink(missing_ok=True)
        print("결과:", *once(cfg()))
    else:
        cmd_run()
