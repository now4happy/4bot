#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""팬딩 서버 직접 수집기 — fanding_fetch_server.py  (VERSION v1.7.1)

하는 일 (이것만 한다)
  서버(GCP)가 fanding.kr 작성자 페이지에서 최신 가격표 글을 찾아,
  글 안에서 가장 큰 이미지를 받아 기존 /api/fanding/upload 로 POST 한다.
  그 뒤의 판독(Gemini→DeepSeek)·날짜 대조·state.json·자동주문·자동환전·텔레그램 버튼은
  기존 fanding_trade.py loop 가 그대로 한다. 이 모듈은 그 코드를 부르지도 바꾸지도 않는다.

쓰는 기존 함수 (읽기만)
  fanding_trade.cfg()                  설정 읽기 (upload_token, missing_alert_kst, diag_send_kst)
  fanding_trade.last_session_date()    expected(필요 종가일) — request_scan 과 같은 방식
  fanding_trade.bridge_state()         스캔 게이트 읽기 (값을 바꾸지 않음)
  fanding_trade.fanding_scan_paused()  게이트가 멈춤(waiting_09/retry_09/stopped)이면 접속 안 함
  fanding_trade.now_kst(), HOME, INBOX

명령
  run            매일 아침 타이머가 실행 (07:50 KST~). 새 글이 나올 때까지 5분 간격, 11:00 에 종료
  check          시험 조회: 로그인 확인 + 최신 글 + 가장 큰 이미지 크기만 출력 (업로드·상태 변경 없음)
  login          한 번만: 아이디·비밀번호를 SSH 창에서 직접 입력 (화면에 안 보임, 어디에도 저장 안 함)
  login-cookies  로그인 대안: 쿠키 JSON 파일을 프로필에 넣고 파일은 지움
  init           한 번만: 지금 최신 글을 '이미 처리한 글'로 기록 (어제 표를 다시 올리지 않게)
  reset          자동 중단(halted) 해제 — 문제를 고친 뒤에만
  status         상태 파일 출력

비밀 규칙: 토큰·비밀번호를 코드·로그·상태 파일에 적지 않는다. 토큰은 fanding.json 에서 읽기만 한다.
"""

VERSION = "v1.7.1"

import argparse
import contextlib
import fcntl
import getpass
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta

import fanding_trade as ft

# ── 설정 (fanding.json 의 "server_fetch": {...} 로 덮어쓸 수 있음. 비밀값은 여기 없음) ──
DEFAULTS = {
    "author_url": "https://fanding.kr/@laofus/",
    "login_url": "https://fanding.kr/login",
    # 글 주소 모양. 마지막 괄호 = 글 번호(숫자). 서버 check 결과를 보고 맞지 않으면 설정에서 고친다.
    "post_regex": r"^https?://(?:www\.)?fanding\.kr/(?:[a-z]{2}/)?@laofus/(?:post|posts|p|feed|community/post)/(\d+)",
    "upload_url": "http://127.0.0.1:8765/api/fanding/upload",
    "poll_minutes": 5,            # 새 글 확인 간격 (지시문 §6-2)
    "min_image_pixels": 200000,   # 이보다 작은 이미지(아이콘·프로필)는 표 후보에서 뺀다
    "nav_timeout_s": 45,
}

STATE_F = ft.HOME / "server_fetch_state.json"
PROFILE = ft.HOME / "server_fetch_profile"     # 서버 전용 브라우저 프로필 (PC 프로필 복사 안 함)
LOCK_F = ft.HOME / ".server_fetch.lock"
DEBUG_PNG = ft.HOME / "server_fetch_debug.png"

BROWSER_ARGS = [  # 1GB 서버용: 가볍게
    "--disable-dev-shm-usage", "--disable-gpu", "--disable-extensions", "--mute-audio",
    "--no-first-run", "--renderer-process-limit=1", "--js-flags=--max-old-space-size=192",
]

NOTE_PREFIX = "[서버 수집기] "


class FetchError(Exception):
    pass


def log(msg):
    print(f"{ft.now_kst().strftime('%m-%d %H:%M:%S')} {msg}", flush=True)


def scfg():
    c = dict(DEFAULTS)
    c.update(ft.cfg().get("server_fetch") or {})
    return c


# ── 상태 파일 (토큰·비밀번호 없음) ──
def load_state():
    try:
        return json.loads(STATE_F.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as e:
        log(f"상태 파일 읽기 실패, 빈 상태로 시작: {e}")
        return {}


def save_state(st):
    ft.HOME.mkdir(parents=True, exist_ok=True)
    tmp = STATE_F.with_name(STATE_F.name + ".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, STATE_F)


# ── 이미지 검사: http_upload 과 같은 조건 ──
def image_ok(data):
    if not 1000 < len(data) <= 8_000_000:
        return "bad_size"
    if not (data[:3] == b"\xff\xd8\xff" or data[:4] == b"\x89PNG" or data[:4] == b"RIFF"):
        return "not_image"
    return ""


# ── note: http_upload 의 note 와 같은 이름·인코딩으로 inbox 에 직접 쓴다 ──
# (헤더로 보내면 한글이 latin-1 에서 깨지므로 직접 쓴다. 이름 형식 {unix시간}_{hex6}.note, UTF-8)
def write_note(text):
    ft.INBOX.mkdir(parents=True, exist_ok=True)
    name = f"{int(time.time())}_{uuid.uuid4().hex[:6]}.note"
    tmp = ft.INBOX / f".{name}.tmp"           # *.note 로 잡히지 않는 임시 이름 → 다 쓰고 이름 바꿈
    tmp.write_text(NOTE_PREFIX + text, encoding="utf-8")
    os.replace(tmp, ft.INBOX / name)
    log(f"note 남김: {text[:80]}")


# ── 전달: 기존 /api/fanding/upload 로 POST (http_upload 이 그대로 inbox 에 씀) ──
def _ascii_url(u):
    return urllib.parse.quote(u, safe=":/?&=#@%+~.-_")


def deliver(post, data, expected, sc=None):
    sc = sc or scfg()
    bad = image_ok(data)
    if bad:
        raise FetchError(f"이미지 형식/크기 불량({bad}, {len(data)}바이트)")
    token = ft.cfg().get("upload_token") or ""
    if len(token) < 20:
        raise FetchError("서버 설정에 upload_token 이 없음")
    batch = hashlib.sha256(f"{post}|{expected}".encode()).hexdigest()[:16]
    headers = {
        "X-Fanding-Token": token,
        "X-Fanding-Post": _ascii_url(post)[:300],
        "X-Fanding-Batch": batch,
        "X-Fanding-Index": "0",
        "X-Fanding-Count": "1",
        "X-Fanding-Mode": "live",
        "X-Fanding-Expected": expected,
        "Content-Type": "application/octet-stream",
    }
    req = urllib.request.Request(sc["upload_url"], data=data, headers=headers, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 127.0.0.1 → 프록시 안 탐
    try:
        with opener.open(req, timeout=30) as r:
            body = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as e:
        raise FetchError(f"업로드 거절 HTTP {e.code}")
    except Exception as e:
        raise FetchError(f"업로드 연결 실패: {type(e).__name__}")
    try:
        ok = json.loads(body).get("ok") is True
    except Exception:
        ok = False
    if status != 200 or not ok:
        raise FetchError(f"업로드 응답 이상 HTTP {status}")
    log(f"업로드 완료: {len(data)}바이트 expected={expected} batch={batch}")


# ── 스캔 게이트 (읽기만) ──
def gate_paused():
    with ft.bridge_state() as b:
        return bool(ft.fanding_scan_paused(dict(b)))


# ── 시각 계산 ──
def kst_at(now, hhmm):
    h, m = (int(x) for x in str(hhmm).split(":"))
    return now.replace(hour=h, minute=m, second=0, microsecond=0)


# ── 아침 루틴 (브라우저와 분리 → 시험 가능) ──
# fetch(known_id) 결과 dict: kind = ok | no_new | logged_out | error
#   ok: post, post_id, data   /   logged_out·error: detail
def routine(st, *, now, sleep, fetch, send, note, paused, expected, deadline, retry_at, poll_s):
    """반환: sent | already | halted | no_baseline | gate_paused | gate_error | logged_out | stopped | deadline"""
    exp = expected
    st["last_run"] = {"at": now().isoformat(), "expected": exp}
    if st.get("halted"):
        log(f"자동 중단 상태라 접속 안 함 ({st['halted'].get('reason', '')}). 고친 뒤 reset 필요")
        return "halted"
    if st.get("done_expected") == exp:
        log(f"{exp} 표는 이미 보냄. 접속 안 함")
        return "already"
    if not st.get("last_post_id"):
        if st.get("no_baseline_noted") != exp:
            note("init 을 아직 안 해서 수집하지 않았어요. 서버에서 init 을 한 번 실행해 주세요.")
            st["no_baseline_noted"] = exp
        return "no_baseline"

    errors = 0
    while now() < deadline:
        try:
            if paused():
                log("스캔 게이트가 멈춤 상태라 접속하지 않음")
                return "gate_paused"
        except Exception as e:
            note(f"스캔 게이트를 읽지 못해 수집하지 않았어요 ({type(e).__name__}).")
            return "gate_error"

        r = fetch(st["last_post_id"])
        kind = r.get("kind")
        if kind == "ok":
            try:
                send(r["post"], r["data"], exp)
            except Exception as e:
                r = {"kind": "error", "detail": str(e)}
                kind = "error"
            else:
                st["done_expected"] = exp
                st["last_post_id"] = r["post_id"]
                st["last_post"] = r["post"]
                st["last_sent"] = {"at": now().isoformat(), "expected": exp, "bytes": len(r["data"])}
                return "sent"
        if kind == "no_new":
            log(f"새 글 없음 → {poll_s // 60}분 뒤 다시 확인")
            sleep(poll_s)
            continue
        if kind == "logged_out":
            note("팬딩 로그인이 풀려서 수집하지 않았어요. 서버에서 login 을 다시 해 주세요. "
                 f"({r.get('detail', '')})")
            st["halted"] = {"at": now().isoformat(), "reason": "logged_out"}
            return "logged_out"
        # 오류: 1차 → 진단 1회 + 09:00 자동 1회 재시도 / 2차(또는 09:00 이후 1차) → 진단 1회 + 자동 중단
        errors += 1
        detail = r.get("detail", "알 수 없는 오류")
        if errors == 1 and now() < retry_at and retry_at < deadline:
            note(f"수집 1차 실패: {detail}. 사이트 재시도를 멈추고 {retry_at.strftime('%H:%M')}에 한 번만 다시 해요.")
            wait = (retry_at - now()).total_seconds()
            sleep(max(0, wait))
            continue
        note(f"수집 실패: {detail}. 자동 재시도를 멈췄어요. 고친 뒤 reset 해야 다시 수집해요. "
             "(기존 09:40·11:00 알림 흐름은 그대로)")
        st["halted"] = {"at": now().isoformat(), "reason": detail[:200]}
        return "stopped"
    log("11:00 까지 새 표 없음 → 종료 (기존 미도착 알림 흐름에 맡김)")
    return "deadline"


# ── 브라우저 (수집할 때만 띄우고 바로 닫음) ──
@contextlib.contextmanager
def browser(sc):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise FetchError("playwright 미설치")
    PROFILE.mkdir(parents=True, exist_ok=True)
    os.chmod(PROFILE, 0o700)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=True, args=BROWSER_ARGS,
            viewport={"width": 1280, "height": 1800}, locale="ko-KR", timezone_id="Asia/Seoul")
        try:
            ctx.set_default_timeout(sc["nav_timeout_s"] * 1000)

            def _route(route):
                if route.request.resource_type in ("font", "media"):
                    return route.abort()
                return route.continue_()
            ctx.route("**/*", _route)
            yield ctx
        finally:
            ctx.close()


def _settle(page, ms=15000):
    try:
        page.wait_for_load_state("networkidle", timeout=ms)
    except Exception:
        pass


def _looks_login(url):
    u = url.lower()
    return any(k in u for k in ("/login", "/signin", "/sign-in", "/auth"))


def find_posts(ctx, sc):
    """작성자 페이지 → {글번호: 주소}. 로그인 페이지로 가면 None."""
    rx = re.compile(sc["post_regex"])
    page = ctx.new_page()
    api = []   # 글 목록 JSON API 후보 (check 진단용, 지시문 §7)

    def _resp(r):
        try:
            if "json" in (r.headers.get("content-type") or "") and len(api) < 12:
                api.append(r.url.split("?")[0])
        except Exception:
            pass
    page.on("response", _resp)
    try:
        page.goto(sc["author_url"], wait_until="domcontentloaded")
        _settle(page)
        posts, hrefs = {}, []
        for _ in range(6):          # JS 렌더링 대기 (최대 약 15초)
            if _looks_login(page.url):
                return None, {"url": page.url}
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            for h in hrefs:
                m = rx.match(h)
                if m:
                    posts[int(m.group(1))] = h.split("#")[0]
            if posts:
                break
            page.wait_for_timeout(2500)
        diag = {"url": page.url, "anchors": len(hrefs),
                "author_links": sorted({h for h in hrefs if "@laofus" in h})[:15],
                "json_api": sorted(set(api))}
        return posts, diag
    finally:
        page.close()


def largest_image(ctx, sc, post):
    page = ctx.new_page()
    try:
        page.goto(post, wait_until="domcontentloaded")
        _settle(page)
        if _looks_login(page.url):
            return None, "login"
        # lazy-load 이미지가 다 뜨도록 천천히 끝까지 스크롤한다.
        # (900px씩 250ms 간격은 느린 서버에서 이미지가 로딩을 시작하기 전에 지나쳐
        #  naturalWidth가 0으로 측정돼 표 이미지를 못 찾는 경우가 있다.)
        page.evaluate("""async () => {
            const H = document.body.scrollHeight;
            for (let y = 0; y < H; y += 500) {
                window.scrollTo(0, y);
                await new Promise(r => setTimeout(r, 400));
            }
            window.scrollTo(0, 0); }""")
        # 표 크기 이미지가 뜰 때까지 최대 20초 대기 (없으면 그대로 진행해 아래에서 오류 반환)
        for _ in range(40):
            has = page.evaluate(
                f"() => Array.from(document.images).some(i => i.complete && "
                f"i.naturalWidth * i.naturalHeight >= {sc['min_image_pixels']})")
            if has:
                break
            page.wait_for_timeout(500)
        page.wait_for_timeout(1000)
        imgs = page.evaluate("""() => Array.from(document.images).map(i => (
            {src: i.currentSrc || i.src, w: i.naturalWidth, h: i.naturalHeight}))""")
        cands = [i for i in imgs if str(i.get("src", "")).startswith("http")
                 and i["w"] * i["h"] >= sc["min_image_pixels"]]
        if not cands:
            return None, f"글 안에 표 크기 이미지가 없음 (이미지 {len(imgs)}개)"
        best = max(cands, key=lambda i: i["w"] * i["h"])
        resp = ctx.request.get(best["src"], headers={"Referer": post}, timeout=30000)
        if not resp.ok:
            return None, f"이미지 내려받기 실패 HTTP {resp.status}"
        data = resp.body()
        bad = image_ok(data)
        if bad:
            return None, f"이미지 형식/크기 불량({bad}, {len(data)}바이트, {best['w']}x{best['h']})"
        log(f"가장 큰 이미지 {best['w']}x{best['h']} {len(data)}바이트")
        return data, ""
    finally:
        page.close()


def fetch_once(known_id, sc=None):
    sc = sc or scfg()
    try:
        with browser(sc) as ctx:
            posts, diag = find_posts(ctx, sc)
            if posts is None:
                return {"kind": "logged_out", "detail": "로그인 페이지로 이동함"}
            if not posts:
                return {"kind": "logged_out", "detail": f"글 목록이 안 보임 (링크 {diag['anchors']}개)"}
            pid = max(posts)
            if known_id and pid <= int(known_id):
                return {"kind": "no_new"}
            data, err = largest_image(ctx, sc, posts[pid])
            if err == "login":
                return {"kind": "logged_out", "detail": "글 페이지에서 로그인으로 이동함"}
            if data is None:
                return {"kind": "error", "detail": err}
            return {"kind": "ok", "post": posts[pid], "post_id": pid, "data": data}
    except FetchError as e:
        return {"kind": "error", "detail": str(e)}
    except Exception as e:
        return {"kind": "error", "detail": f"브라우저 오류 {type(e).__name__}: {str(e)[:120]}"}


# ── 명령 ──
@contextlib.contextmanager
def single_instance():
    ft.HOME.mkdir(parents=True, exist_ok=True)
    fd = os.open(LOCK_F, os.O_CREAT | os.O_RDWR, 0o660)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("이미 실행 중 → 종료")
            sys.exit(0)
        yield
    finally:
        os.close(fd)


def cmd_run():
    sc = scfg()
    c = ft.cfg()
    with single_instance():
        st = load_state()
        n = ft.now_kst()
        res = routine(
            st, now=ft.now_kst, sleep=time.sleep, fetch=lambda k: fetch_once(k, sc),
            send=lambda p, d, e: deliver(p, d, e, sc), note=write_note, paused=gate_paused,
            expected=ft.last_session_date().isoformat(),
            deadline=kst_at(n, c.get("missing_alert_kst", "11:00")),
            retry_at=kst_at(n, c.get("diag_send_kst", "09:00")),
            poll_s=int(sc["poll_minutes"]) * 60)
        st["last_run"]["result"] = res
        save_state(st)
        log(f"결과: {res}")


def cmd_check():
    sc = scfg()
    st = load_state()
    print(f"버전 {VERSION} / expected {ft.last_session_date().isoformat()} / 처리한 글 {st.get('last_post_id')}")
    if gate_paused():
        print("스캔 게이트 멈춤 → 접속하지 않음")
        return
    with browser(sc) as ctx:
        posts, diag = find_posts(ctx, sc)
        print(json.dumps(diag, ensure_ascii=False, indent=1))
        if not posts:
            print("글 목록을 못 찾음 → 로그인 안 됨이거나 post_regex 가 안 맞음 (author_links 확인)")
            return
        pid = max(posts)
        print(f"찾은 글 {len(posts)}개, 최신 글 {pid}: {posts[pid]}")
        data, err = largest_image(ctx, sc, posts[pid])
        print("이미지:", err or f"OK {len(data)}바이트 (업로드 안 함)")


def _verify_login(ctx, sc):
    posts, diag = find_posts(ctx, sc)
    if posts:
        print(f"로그인 확인됨: 글 {len(posts)}개 보임, 최신 {max(posts)}")
        return True
    print("로그인 확인 실패:", json.dumps(diag, ensure_ascii=False))
    return False


def _after_login_ok():
    st = load_state()
    if (st.get("halted") or {}).get("reason") == "logged_out":
        st.pop("halted", None)
        save_state(st)
        print("로그인 풀림 중단을 해제했어요.")


def cmd_login():
    sc = scfg()
    ident = input("팬딩 아이디(이메일): ").strip()
    pw = getpass.getpass("비밀번호 (입력해도 화면에 안 보임): ")
    with browser(sc) as ctx:
        page = ctx.new_page()
        page.goto(sc["login_url"], wait_until="domcontentloaded")
        _settle(page, 10000)
        id_sel = ('input[type="email"], input[autocomplete="username"], '
                  'input[name*="email" i], input[name*="id" i], input[placeholder*="이메일"]')
        pw_sel = 'input[type="password"]'
        if page.locator(pw_sel).count() == 0 or page.locator(id_sel).count() == 0:
            page.screenshot(path=str(DEBUG_PNG))
            print(f"로그인 입력칸을 못 찾음. 화면 저장: {DEBUG_PNG}  (소셜 로그인 계정이면 login-cookies 사용)")
            return
        page.locator(id_sel).first.fill(ident)
        page.locator(pw_sel).first.fill(pw)
        pw = None
        page.locator(pw_sel).first.press("Enter")
        page.wait_for_timeout(8000)
        _settle(page, 10000)
        page.close()
        if _verify_login(ctx, sc):
            _after_login_ok()
        else:
            print("로그인이 안 된 것 같아요. 아이디·비밀번호를 확인하거나 login-cookies 를 쓰세요.")


def cmd_login_cookies(path, keep=False):
    sc = scfg()
    raw = json.loads(open(path, encoding="utf-8").read())
    if isinstance(raw, dict):
        raw = raw.get("cookies", [])
    ss = {"no_restriction": "None", "none": "None", "lax": "Lax", "strict": "Strict", "unspecified": "Lax"}
    cookies = []
    for c in raw:
        if "fanding" not in str(c.get("domain", "")):
            continue
        k = {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/"),
             "httpOnly": bool(c.get("httpOnly")), "secure": bool(c.get("secure")),
             "sameSite": ss.get(str(c.get("sameSite", "Lax")).lower(), "Lax")}
        exp = c.get("expires", c.get("expirationDate"))
        if exp and float(exp) > 0:
            k["expires"] = float(exp)
        cookies.append(k)
    if not cookies:
        print("fanding 쿠키가 파일에 없어요.")
        return
    with browser(sc) as ctx:
        ctx.add_cookies(cookies)
        ok = _verify_login(ctx, sc)
    if not keep:
        os.remove(path)
        print("쿠키 파일을 지웠어요.")
    if ok:
        _after_login_ok()


def cmd_init():
    sc = scfg()
    with browser(sc) as ctx:
        posts, diag = find_posts(ctx, sc)
    if not posts:
        print("글 목록을 못 찾아 init 못 함:", json.dumps(diag, ensure_ascii=False))
        return
    pid = max(posts)
    st = load_state()
    st["last_post_id"], st["last_post"] = pid, posts[pid]
    st["init_at"] = ft.now_kst().isoformat()
    save_state(st)
    print(f"기준 글을 {pid} 로 기록했어요. 이 글보다 새 글만 수집해요.")


def cmd_reset():
    st = load_state()
    print("해제:", st.pop("halted", None))
    save_state(st)


def main(argv=None):
    ap = argparse.ArgumentParser(description=f"팬딩 서버 직접 수집기 {VERSION}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("run", "check", "login", "init", "reset", "status"):
        sub.add_parser(c)
    lc = sub.add_parser("login-cookies")
    lc.add_argument("path")
    lc.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        cmd_run()
    elif a.cmd == "check":
        cmd_check()
    elif a.cmd == "login":
        cmd_login()
    elif a.cmd == "login-cookies":
        cmd_login_cookies(a.path, a.keep)
    elif a.cmd == "init":
        cmd_init()
    elif a.cmd == "reset":
        cmd_reset()
    else:
        print(json.dumps(load_state(), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
