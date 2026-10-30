#!/usr/bin/env python3
# ==========================================================
# FILE: C:\fanding\fanding_fetch.py   (FANDING_FETCH_V1.5.4)
#   저장소 위치: bot_office/fanding_fetch_win.py (서버에선 실행하지 않음 · 윈도우가 GitHub 에서 내려받음)
# 윈도우 PC 전용: 팬딩 가격표 이미지를 가져와 사무실 서버로 보내고 종료
# 1.1.0: 글 안의 큰 이미지를 모두 보냄 → 서버가 가격표만 골라냄 (이미지 순서가 바뀌어도 OK)
# 1.2.0: 시리즈 목록 끝까지 내려 모든 글을 모은 뒤 글 번호가 가장 큰 것(= 가장 최근 글)을 고름
# 1.4.0: 매일 실행 끝에 과거 글 10개씩 천천히(글마다 20~40초 쉬며) 보내 매매 규칙 분석용 기록 쌓기
# 1.5.2: 과거 글 이미지를 PC(history 폴더)에도 보관 · 서버에 이미 보낸 글은 PC에만 보완 저장 (PC에서 직접 수정된 버전)
# 1.5.3 (사무실 v1.0.59 예정, 2026-10-29):
#   · 과거 수집 하루 30개 글 (config.json 의 backfill_per_day 가 있으면 그 값)
#   · 서버에 아직 안 보낸 글을 먼저, PC 보관만 빠진 글은 그다음 (할당을 재저장에 먼저 쓰던 문제)
#   · 과거 글을 다 모으면 backfill_complete.json 을 남기고 다음 날부터 과거 수집 종료 (브라우저도 안 엶)
#   · 매일 받는 가격표 글 1개는 PC 보관 + 수집 완료 목록에 추가 → 다음 날 '남은 글'로 다시 세지 않음
#   · 다시 모으려면 backfill_complete.json 삭제, 또는 py fanding_fetch.py backfill (수동은 종료 표시 무시)
#
# 1.5.4: 최초 실패 즉시 중단·1회 진단, KST 09:00 1회 재시도, 재실패 시 버전별 영구 정지
#
#  준비 (한 번만)
#    py -m pip install playwright
#    py -m playwright install chromium
#    py fanding_fetch.py login     ← 창이 뜨면 네이버로 팬딩 로그인 후 창 닫기
#    py fanding_fetch.py test      ← 가격표를 찾는지 확인 (서버로 안 보냄)
#
#  매일 (작업 스케줄러가 자동 실행)
#    py fanding_fetch.py run       ← 첫 실패 즉시 중단, 09:00 단 1회 재시도
#
#  설정: 같은 폴더의 config.json
#    {"office_url": "https://사무실주소", "upload_token": "서버와 같은 암호",
#     "series_url": "https://fanding.kr/@laofus/series/1933/", "stop_at": "11:30",
#     "retry_min": 5, "headless": true}
# ==========================================================
import hashlib, json, random, re, sys, time, urllib.parse, urllib.request, urllib.error, os, tempfile
from datetime import timedelta, timezone
from datetime import datetime
from pathlib import Path

VERSION = "1.5.4"
HERE = Path(__file__).resolve().parent
CFG = HERE / "config.json"
PROFILE = HERE / "browser_profile"      # 팬딩 로그인이 저장되는 전용 브라우저 폴더
LAST = HERE / "last_sent.txt"
BACKFILL = HERE / "backfill_done.json"     # 이미 보낸 과거 글 목록
BACKFILL_COMPLETE = HERE / "backfill_complete.json"   # 과거 글 다 모음 표시 (있으면 매일 과거 수집 안 함)
DEBUG = HERE / "debug"


# 1.5.4 상태 파일: 동일 버전 09:00 실패 뒤에는 날짜가 바뀌어도 자동 접속 금지.
RETRY_STATE = HERE / "fanding_retry_state.json"
KST = timezone(timedelta(hours=9))
DIAG_STEPS = ("사이트 시리즈 목록 가져오기", "로그인 상태 확인", "글 목록·최신 글 선택",
              "글 페이지 가져오기", "글 안 이미지 가져오기", "서버로 이미지 전송",
              "서버 판독 결과 대기·확인")
TRACE = {"step": "사이트 시리즈 목록 가져오기", "last": "없음", "post": ""}
SCAN_POLICY = {"value": "first"}


def progress(step, success=False, post=""):
    if step not in DIAG_STEPS:
        raise ValueError("잘못된 수집 단계")
    TRACE["step"] = step
    if success:
        TRACE["last"] = step
    if post:
        TRACE["post"] = post


def kst_now():
    return datetime.now(KST)


def read_retry_state():
    if not RETRY_STATE.exists():
        return {}
    try:
        state = json.loads(RETRY_STATE.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError("invalid")
        return state
    except (ValueError, OSError):
        # 손상된 정지 기록을 지워서 자동 사이트 접속하는 쪽으로 처리하지 않는다.
        return {"version": VERSION, "phase": "stopped", "reason": "정지 기록 읽기 실패"}


def save_retry_state(state):
    atomic_write(RETRY_STATE, json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8"))


def retry_state_for_today(now, expected):
    state = read_retry_state()
    if state.get("version") != VERSION:
        # 새 버전에서만 이전 버전의 영구 정지를 해제한다. 운영자가 파일 삭제해도 초기화된다.
        state = {}
    if state.get("phase") == "stopped":
        return state
    if state.get("date") != now.date().isoformat():
        if state.get("phase") in ("waiting_09", "retrying_09"):
            state["phase"] = "stopped"  # 전날에 중단된 시도를 새 날에 자동 재개하지 않음.
            save_retry_state(state)
            return state
        state = {}
    if not state:
        state = {"version": VERSION, "date": now.date().isoformat(), "expected": expected,
                 "phase": "first", "first_diag_sent": False, "retry_diag_sent": False}
        save_retry_state(state)
    return state


def retry_action(state, now):
    """사이트 접근을 허용하는 순간만 first/at_09로 반환. 같은 버전 정지는 절대 허용하지 않음."""
    phase = state.get("phase")
    nine = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if phase == "first":
        return "first"
    if phase == "waiting_09":
        return "at_09" if now >= nine and state.get("date") == now.date().isoformat() else "wait"
    if phase in ("retrying_09", "stopped"):
        return "stop"
    return "done" if phase == "ready" else "stop"


def failure_label(result, info):
    labels = {"logged_out": "로그인 풀림 의심", "no_posts": "글 없음", "no_image": "이미지 없음",
              "parsing": "필요 종가일 자료 없음(날짜 오독·가격표 아님 가능)",
              "server_error": "서버 전송 실패 또는 판독 대기 초과", "error": "수집 단계 오류"}
    return labels.get(result, "수집 실패") + (" · " + str(info)[:38] if info else "")


def report_failure(c, state, kind, result, info):
    """한 시도당 진단 한 번. 전송 실패 시 무한 재전송하지 않고 로컬 기록에 남긴다."""
    key = "first_diag_sent" if kind == "first" else "retry_diag_sent"
    if state.get(key):
        return
    state[key] = True
    save_retry_state(state)  # 네트워크 전송 전 1회 플래그를 고정하여 중복 통지 방지
    failed_at = kst_now().strftime("%Y-%m-%d %H:%M:%S KST")
    late_first = kind == "first" and kst_now().hour >= 9
    next_step = ("09:00 이후 첫 실패입니다. 추가 자동 재시도 없이 업데이트까지 멈춥니다" if late_first else
                 "KST 09:00에 1회 다시 시도합니다" if kind == "first" else
                 "09:00 재시도도 실패했습니다. 자동 재시도를 멈춥니다. 업데이트 뒤 새 코드로 다시 시도합니다")
    # 서버의 X-Fanding-Note는 300자까지만 전달: 식별자, 상세 오류 원문 노출 금지.
    parts = ["⚠️ 팬딩 PC 수집 진단", "실패 단계: " + TRACE["step"],
             "마지막 성공: " + TRACE["last"], "사유: " + failure_label(result, info),
             "시각: " + failed_at, "필요 종가일: " + str(state.get("expected") or "미확인")]
    if TRACE.get("post"):
        parts.append("글: " + TRACE["post"][:80])
    parts.append(next_step)
    note = "\n".join(parts)
    if len(note) > 300:
        # 필수 항목 + 마지막 일정은 보존, 긴 글 주소는 축약.
        parts[3] = "사유: " + failure_label(result, "")
        for i, part in enumerate(parts):
            if part.startswith("글: "):
                parts[i] = "글: " + part[3:40]
        note = "\n".join(parts)
    log(note)
    try:
        post_server(c, note=note[:300])
    except Exception as exc:
        log("진단 전달 실패(재전송하지 않음):", type(exc).__name__)


def set_gate(c, policy, request_id=""):
    SCAN_POLICY["value"] = policy
    try:
        control(c, "daily_stopped" if policy == "stopped" else "idle", request_id)
    except Exception as exc:
        log("수집 중단 상태 서버 통지 실패:", type(exc).__name__)

def log(*a):
    print(datetime.now().strftime("%m-%d %H:%M:%S"), *a, flush=True)


def cfg():
    c = {"series_url": "https://fanding.kr/@laofus/series/1933/", "stop_at": "11:30", "retry_min": 5, "headless": True,
         "backfill_per_day": 30}
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


def grab_images(page, post_url, limit=16, trace=None):
    """글 이미지 1회 가져오기. 기존 fallback은 유지하고 진단 단계만 기록."""
    if trace:
        trace("글 페이지 가져오기", post=post_url)
    page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
    if trace:
        trace("글 페이지 가져오기", success=True)
        trace("글 안 이미지 가져오기")
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
    if trace and out:
        trace("글 안 이미지 가져오기", success=True)
    return out, imgs

def control(c, stage="idle", request_id=""):
    policy = SCAN_POLICY["value"]
    # 서버가 새 요청을 만들어도 '대기/정지'에서는 사이트 접속을 유발할 수 없다.
    data = json.dumps({"stage":stage, "request_id":request_id, "version":VERSION,
                       "mode": "watch" if WORKER_MODE["stay_open"] else "run",
                       "run_path": str(Path(__file__).resolve()),
                       "want_scan": policy in ("first", "retry_09"),
                       "scan_policy": policy}).encode()
    req = urllib.request.Request(c["office_url"].rstrip("/") + "/api/fanding/control", data=data,
                                 headers={"X-Fanding-Token":c["upload_token"], "Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as reply:
            result = json.load(reply)
    except urllib.error.HTTPError as exc:
        hints = {404: "서버 /api/fanding/control 연결 누락: server.py 수정본 적용 필요",
                 401: "서버가 control 요청에 로그인 요구: control 경로 연결 확인",
                 403: "업로드 토큰 불일치 또는 서버 접근 설정 확인"}
        raise RuntimeError(hints.get(exc.code, "서버 control HTTP " + str(exc.code))) from None
    if not isinstance(result, dict) or not result.get("ok"):
        raise RuntimeError("서버 control 응답 형식 오류")
    return result

def once(c, upload=True, request=None):
    from playwright.sync_api import sync_playwright
    TRACE.update(step="사이트 시리즈 목록 가져오기", last="없음", post="")
    def stage(name):
        if upload and request:
            control(c, name, request["id"])
    stage("connecting")
    with sync_playwright() as p:
        ctx = browser(p, c["headless"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            progress("사이트 시리즈 목록 가져오기")
            stage("listing")
            posts = latest_post_url(page, c["series_url"])
            progress("사이트 시리즈 목록 가져오기", success=True)
            progress("로그인 상태 확인")
            if looks_logged_out(page):
                return "logged_out", None
            progress("로그인 상태 확인", success=True)
            progress("글 목록·최신 글 선택")
            if not posts:
                return "no_posts", None
            progress("글 목록·최신 글 선택", success=True)
            candidates = posts[:max(1, min(5, int(c.get("recent_posts", 3))))]
            total = 0
            for post in candidates:
                stage("images")
                images, _ = grab_images(page, post, trace=progress)
                progress("로그인 상태 확인")
                if looks_logged_out(page):
                    return "logged_out", None
                progress("로그인 상태 확인", success=True)
                if not images:
                    # 첫 오류에서 바로 중단. 다음 글/이미지 접근 없음.
                    progress("글 안 이미지 가져오기", post=post)
                    return "no_image", None
                if not upload:
                    folder = HERE / "test_images"; folder.mkdir(exist_ok=True)
                    for i, image in enumerate(images, 1):
                        (folder / f"post_{total}_image_{i}.jpg").write_bytes(image)
                else:
                    stage("uploading")
                    progress("서버로 이미지 전송")
                    sha = hashlib.sha256((post + (request or {}).get("id", "")).encode()).hexdigest()
                    for i, image in enumerate(images, 1):
                        reply = post_server(c, image, post=post, batch=sha[:16], idx=i, count=len(images), request=request)
                        if not reply.get("ok"):
                            return "server_error", None
                    progress("서버로 이미지 전송", success=True)
                total += len(images)
                if upload and request:
                    progress("서버 판독 결과 대기·확인")
                    for _ in range(60):
                        ack = control(c, "parsing", request["id"])
                        if ack.get("ready"):
                            progress("서버 판독 결과 대기·확인", success=True)
                            keep_daily_post(c, post, images)
                            return "sent", f"필요 종가일 자료 확보 · {total}장 전송"
                        if not ack.get("pending_images"):
                            break
                        time.sleep(30)
                    else:
                        return "server_error", "서버 판독 대기30분 초과"
                    # 어떤 이유든 필요 종가일 자료가 없는 것을 '오류'로 보고 즉시 중단.
                    return "parsing", f"{total}장 전송 · 필요 종가일 자료 없음"
            return ("sent" if upload else "test_ok", f"{total}장 / 최근 {len(candidates)}개 글") if total else ("no_image", None)
        finally:
            ctx.close()

def watch(stay_open=False):
    # 원본의 단일 실행 잠금과 정상 성공 후 최소 1시간/stop_at/과거 수집 동작은 보존.
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
    WORKER_MODE["stay_open"] = stay_open
    start = kst_now()
    settings = cfg()
    stop_h, stop_m = map(int, settings.get("stop_at", "11:30").split(":"))
    minimum_end = start + timedelta(hours=1)
    stop = max(start.replace(hour=stop_h, minute=stop_m, second=0, microsecond=0), minimum_end)
    log("작업 시작: 첫 오류 뒤 KST 09:00 단 한 번 재시도 · 실패 시 버전 정지")
    state = retry_state_for_today(start, "")
    try:
        if state.get("phase") == "stopped":
            log("동일 버전 정지 상태 · 사이트 접속하지 않음. 업데이트 또는 정지 파일 직접 삭제 필요")
            set_gate(settings, "stopped")
            return
        if state.get("phase") == "retrying_09":
            state["phase"] = "stopped"  # 재시도 도중 중단/충돌 시 세 번째 접근 차단
            save_retry_state(state)
            set_gate(settings, "stopped")
            return
        while True:
            now = kst_now()
            action = retry_action(state, now)
            if action == "stop":
                set_gate(settings, "stopped")
                return
            if action == "wait":
                SCAN_POLICY["value"] = "waiting_09"
                # 기존 서버는 요청을 생성할 수 있으나 PC는 while 대기 중 어떤 사이트 코드도 호출하지 않음.
                try:
                    control(settings, "idle")
                except Exception as exc:
                    log("09:00 대기 폴링 실패:", type(exc).__name__)
                time.sleep(min(30, max(1, (now.replace(hour=9, minute=0, second=0, microsecond=0) - now).total_seconds())))
                continue
            if action in ("first", "at_09"):
                kind = "first" if action == "first" else "retry"
                SCAN_POLICY["value"] = "first" if kind == "first" else "retry_09"
                if kind == "retry":
                    state["phase"] = "retrying_09" # 재시도 시작 전 기록: 재시작으로 3차 접속 방지
                    save_retry_state(state)
                TRACE.update(step="서버 판독 결과 대기·확인", last="없음", post="")
                try:
                    c = cfg()
                    reply = control(c, LAST_STAGE["value"])
                    expected = reply.get("expected") or state.get("expected") or ""
                    state["expected"] = expected
                    save_retry_state(state)
                    if reply.get("ready"):
                        result, info = "sent", "서버에서 이미 필요 종가일 자료 확보"
                    else:
                        request = reply.get("request")
                        if not request or not request.get("id"):
                            result, info = "server_error", "서버가 수집 요청을 주지 않음"
                        else:
                            state["expected"] = request.get("expected") or expected
                            save_retry_state(state)
                            result, info = once(c, request=request)
                            ack = control(c, result, request["id"])
                            if ack.get("ready"):
                                result = "sent"
                            elif result == "sent":
                                result, info = "parsing", "서버에서 필요 종가일 확보 확인 불가"
                except Exception as exc:
                    result, info = "error", type(exc).__name__
                log("수집 결과:", result, info or "")
                LAST_STAGE["value"] = result
                if result == "sent":
                    state["phase"] = "ready"
                    save_retry_state(state)
                    SCAN_POLICY["value"] = "ready"
                else:
                    is_final = kind == "retry" or kst_now() >= now.replace(hour=9, minute=0, second=0, microsecond=0)
                    state["phase"] = "stopped" if is_final else "waiting_09"
                    save_retry_state(state)
                    # 진단 알림 서버 전송보다 먼저 게이트를 동기화해 서버 자동 새 요청 틈을 줄인다.
                    set_gate(settings, state["phase"])
                    report_failure(c if 'c' in locals() else settings, state, "retry" if kind == "retry" else "first", result, info)
                    if is_final:
                        # 09:00 이후 첫 실패라면 09:00이 지난 상태: 그날 추가 사이트 접속을 하지 않음.
                        if kind == "first":
                            log("첫 실패 시각이 이미 09:00 이후여서 09:00 재시도 건너뜀 · 영구 정지")
                        return
                    continue
            # 자료 확보 후에는 원본의 과거 수집과 자동 종료 흐름을 그대로 유지.
            try:
                c = cfg()
                SCAN_POLICY["value"] = "ready"
                reply = control(c, LAST_STAGE["value"])
                day = kst_now().date().isoformat()
                hist = HERE / "backfill_day.txt"
                if reply.get("ready") and 8 <= kst_now().hour < 12 and (not hist.exists() or hist.read_text() != day):
                    c["watch_mode"] = True
                    try:
                        backfill(c)
                    except Exception as exc:
                        log("과거 수집 실패(오늘 자료는 확보됨):", type(exc).__name__)
                    hist.write_text(day)
                    LAST_STAGE["value"] = "sent"
                if not stay_open:
                    final = control(c, LAST_STAGE["value"])
                    if final.get("ready") and kst_now() >= minimum_end:
                        try:
                            control(c, "daily_done")
                            post_server(c, note="오늘 필요 자료 확보·PC 수집 작업 완료. 수집기를 자동 종료합니다. 재판독이 필요하면 PC에서 run.bat를 다시 실행하세요.")
                        except Exception:
                            log("완료 알림 전송 실패 · 확보된 자료는 서버에서 확인")
                        log("오늘 작업 완료 · 자동 종료")
                        return
                    if kst_now() >= stop:
                        control(c, "daily_stopped")
                        post_server(c, note="오늘 자료 미확보 상태로 종료 시각에 도달했습니다. /진단 확인 후 필요시 PC run.bat를 다시 실행하세요.")
                        return
            except Exception as exc:
                log("성공 후 서버 연결 실패:", type(exc).__name__)
                if not stay_open and kst_now() >= stop:
                    return
            time.sleep(30)
    finally:
        lock.close()

LAST_STAGE = {"value":"idle"}
WORKER_MODE = {"stay_open": False}


def atomic_write(path, data):
    """같은 폴더의 임시 파일에 쓴 뒤 교체하여 중간 종료에 대비한다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".history-")
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


class HistoryArchive:
    """Windows PC에 저장한 과거 이미지. 설정/토큰/로그인 정보는 기록하지 않는다."""
    def __init__(self, c):
        folder = Path(c.get("history_dir") or "history")
        self.root = (folder if folder.is_absolute() else HERE / folder).resolve()
        self.index_file = self.root / "index.json"
        self.index = json.loads(self.index_file.read_text(encoding="utf-8")) if self.index_file.exists() else {"version": 1, "posts": {}}
        if not isinstance(self.index, dict) or not isinstance(self.index.get("posts"), dict):
            raise ValueError("과거 자료 index.json 형식 확인 필요")

    def folder(self, post):
        rel = self.index["posts"].get(post)
        if rel is None:
            ident = re.search(r"/(\d+)/?$", urllib.parse.urlparse(post).path)
            name = "post_" + (ident.group(1) + "_" if ident else "") + hashlib.sha256(post.encode()).hexdigest()[:12]
            rel = datetime.now(timezone(timedelta(hours=9))).date().isoformat() + "/" + name
        target = (self.root / rel).resolve()
        if self.root not in target.parents:
            raise ValueError("과거 자료 경로 확인 필요")
        return target

    def metadata(self, post):
        folder = self.folder(post)
        file = folder / "metadata.json"
        if not file.exists():
            return None
        data = json.loads(file.read_text(encoding="utf-8"))
        if data.get("post_url") != post or not data.get("images"):
            return None
        for image in data["images"]:
            name = image.get("file", "")
            if Path(name).name != name or not name:
                raise ValueError("과거 이미지 파일명 확인 필요")
            path = folder / name
            if not path.is_file() or path.stat().st_size != image.get("size"):
                return None
        return data

    def has(self, post):
        return self.metadata(post) is not None

    def read(self, post):
        data = self.metadata(post)
        if not data:
            return None
        images = [(self.folder(post) / image["file"]).read_bytes() for image in data["images"]]
        if any(hashlib.sha256(raw).hexdigest() != image["sha256"] for raw, image in zip(images, data["images"])):
            return None
        return images

    def save(self, post, images):
        if not images:
            raise ValueError("이미지가 없어 저장 완료로 처리하지 않음")
        folder = self.folder(post)
        folder.mkdir(parents=True, exist_ok=True)
        # 먼저 경로를 기억하여 실패/다음날 재시도도 같은 폴더를 사용한다.
        self.index["posts"][post] = folder.relative_to(self.root).as_posix()
        atomic_write(self.index_file, json.dumps(self.index, ensure_ascii=False, indent=2).encode())
        entries = []
        seen = set()
        for raw in images:
            sha = hashlib.sha256(raw).hexdigest()
            if sha in seen:
                continue
            seen.add(sha)
            suffix = ".jpg" if raw.startswith(b"\xff\xd8\xff") else ".png" if raw.startswith(b"\x89PNG") else ".webp" if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP" else ".bin"
            name = sha + suffix
            file = folder / name
            if not file.exists() or hashlib.sha256(file.read_bytes()).hexdigest() != sha:
                atomic_write(file, raw)
            entries.append({"file": name, "sha256": sha, "size": len(raw)})
        data = {"post_url": post, "saved_at_kst": datetime.now(timezone(timedelta(hours=9))).isoformat(),
                "images": entries}
        atomic_write(folder / "metadata.json", json.dumps(data, ensure_ascii=False, indent=2).encode())
        return folder


def keep_daily_post(c, post, images):
    """매일 받은 가격표 글: PC 보관 + 수집 완료 목록에 추가 (서버에는 이미 오늘 자료로 들어감 → 다시 보내지 않음)"""
    try:
        HistoryArchive(c).save(post, images)
        done = set(json.loads(BACKFILL.read_text(encoding="utf-8"))) if BACKFILL.exists() else set()
        if post not in done:
            done.add(post)
            atomic_write(BACKFILL, json.dumps(sorted(done), ensure_ascii=False).encode())
        log("오늘 가격표 글 PC 보관·수집 목록 추가:", post)
    except Exception as e:
        log("오늘 가격표 글 보관 실패(주문 흐름과 무관):", type(e).__name__, e)


def backfill(c, n=None, force=False):
    """과거 글 n개를 PC에 먼저 저장하고, 미전송분만 서버에 기록한다. 다 모으면 종료 표시."""
    if BACKFILL_COMPLETE.exists() and not force:
        log("과거 글 수집 완료 상태 → 건너뜀 (다시 하려면 backfill_complete.json 삭제)")
        return
    n = int(c.get("backfill_per_day", 30) if n is None else n)
    if n <= 0:
        return
    from playwright.sync_api import sync_playwright
    done = set(json.loads(BACKFILL.read_text(encoding="utf-8"))) if BACKFILL.exists() else set()
    sent = 0
    archived = 0
    archive = HistoryArchive(c)
    with sync_playwright() as p:
        ctx = browser(p, c["headless"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            if c.get("watch_mode"): control(c, "history")
            posts = latest_post_url(page, c["series_url"])
            if looks_logged_out(page) or not posts:
                log("과거 수집: 로그인 풀림 또는 글 목록 없음 → 건너뜀"); return
            # 서버에 안 보낸 글 먼저(오래된 순서 아님, 최신→과거), PC 보관만 빠진 글은 그다음
            todo = ([u for u in posts[1:] if u not in done] + [u for u in posts[1:] if u in done and not archive.has(u)])[:n]
            for u in todo:
                if c.get("watch_mode"): control(c, "history")
                time.sleep(random.uniform(20, 40))        # 사람이 보듯 천천히
                try:
                    images = archive.read(u)
                    if images is None:
                        images, _ = grab_images(page, u)
                    folder = archive.save(u, images)
                    archived += 1
                    log(f"과거 자료 PC 저장 {archived}/{len(todo)}: {folder} ({len(images)}장)")
                    if u not in done:
                        b = hashlib.sha256(u.encode()).hexdigest()[:16]
                        for i, d in enumerate(images, 1):
                            response = post_server(c, d, post=u, batch=b, idx=i, count=len(images), mode="history")
                            if not response.get("ok"):
                                raise RuntimeError("서버가 과거 이미지 전송을 확인하지 못함 · PC 저장본 유지")
                        done.add(u); sent += 1
                        atomic_write(BACKFILL, json.dumps(sorted(done), ensure_ascii=False).encode())
                    else:
                        log("서버에 이미 보낸 글: PC에만 보완 저장 (중복 전송 안 함)")
                except Exception as e:
                    log("과거 글 실패:", u, e)
            left = len([u for u in posts[1:] if u not in done or not archive.has(u)])
            if left == 0:
                atomic_write(BACKFILL_COMPLETE, json.dumps({"completed_at_kst": datetime.now(timezone(timedelta(hours=9))).isoformat(),
                                                           "posts": len(posts) - 1}, ensure_ascii=False).encode())
                log("과거 글 수집 완료 → 다음부터 과거 수집 안 함")
        finally:
            ctx.close()
    if archived:
        try:
            post_server(c, note=f"과거 자료 PC 저장 {archived}개 글 · 서버 신규 전송 {sent}개 글 · 남은 글 {left}개"
                        + (" · ✅ 과거 글 수집 완료, 내일부터 과거 수집 종료" if left == 0 else ""))
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
    if cmd in ("login", "test", "backfill", "send") and read_retry_state().get("version") == VERSION and read_retry_state().get("phase") in ("waiting_09", "retrying_09", "stopped"):
        log("팬딩 수집 접근 중단 상태 · 정지 파일 삭제 또는 새 버전 업데이트 전 사이트 접속하지 않음")
        sys.exit(0)
    if cmd == "login":
        cmd_login()
    elif cmd == "test":
        r, info = once(cfg(), upload=False)
        print("결과:", r, info or "")
        if r == "test_ok":
            print("test_images 폴더의 사진들 중에 가격표가 들어 있는지 확인하세요. (순서는 상관없어요)")
    elif cmd == "backfill":   # 과거 글 지금 바로 보내기 (예: py fanding_fetch.py backfill 3)
        backfill(cfg(), int(sys.argv[2]) if len(sys.argv) > 2 else None, force=True)
    elif cmd == "watch":
        watch(stay_open=True)
    elif cmd == "send":       # 지금 바로 1번 보내기 (같은 그림이어도 다시 보냄)
        LAST.unlink(missing_ok=True)
        print("결과:", *once(cfg()))
    else:
        cmd_run()
