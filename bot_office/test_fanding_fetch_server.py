#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fanding_fetch_server.py 검증 스크립트 (로컬)

사용법:  python3 test_fanding_fetch_server.py /경로/fanding_fetch_server.py [--browser]
  - 진짜 fanding_trade.py 대신, 참조 MD 발췌(http_upload·last_session_date·bridge_state·
    fanding_scan_paused)를 그대로 옮긴 스텁을 임시 폴더에 만들어 쓴다.
  - --browser : Playwright+Chromium 이 있으면 로컬 가짜 팬딩 페이지(JS 렌더링 목록)로 실제 수집 시험.
"""
import hashlib, importlib, json, os, py_compile, re, shutil, sys, tempfile, threading, time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SRC = Path(sys.argv[1]).resolve()
WANT_BROWSER = "--browser" in sys.argv
TMP = Path(tempfile.mkdtemp(prefix="ffs_test_"))
RESULTS = []


def check(name, cond, info=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  ({info})" if info and not cond else ""))


# ── 1. 스텁 fanding_trade (참조 MD §4·§5·§10 발췌를 그대로) ──
STUB = r'''
import contextlib, hashlib, hmac, json, os, re, time, uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
KST, ET = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
R = Path(os.environ["FFS_ROOT"])
HOME = R / "var/lib/bot-office/fanding"
INBOX, IMAGES = HOME / "inbox", HOME / "images"
BRIDGE = HOME / "bridge.json"; BRIDGE_LOCK = HOME / ".bridge.lock"
_CFG = {"upload_token": "T" * 32, "missing_alert_kst": "11:00", "diag_send_kst": "09:00"}
def cfg(): return dict(_CFG)
def now_kst(): return datetime.now(KST)
def is_trading_day(d): return d.weekday() < 5
def last_session_date(now=None):
    e = (now or now_kst()).astimezone(ET)
    d = e.date()
    if e.weekday() >= 5 or (e.hour, e.minute) < (16, 0):
        d -= timedelta(days=1)
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d
@contextlib.contextmanager
def bridge_state():
    HOME.mkdir(parents=True, exist_ok=True)
    b = json.loads(BRIDGE.read_text()) if BRIDGE.exists() else {}
    yield b
    BRIDGE.write_text(json.dumps(b))
def fanding_scan_paused(bridge):
    return (bridge.get("scan_gate") or {}).get("policy") in ("waiting_09", "retry_09", "stopped")
def http_upload(h):
    c = cfg()
    token = c.get("upload_token") or ""
    given = h.headers.get("X-Fanding-Token", "")
    if len(token) < 20 or not hmac.compare_digest(given.encode(), token.encode()):
        return h.send(403, {"error": "bad_token"})
    if h.headers.get("X-Fanding-Kind", "").startswith("vr6"):
        return h.send(200, {"ok": True, "vr6": True})
    note = h.headers.get("X-Fanding-Note", "")
    if note:
        (INBOX / f"{int(time.time())}_{uuid.uuid4().hex[:6]}.note").write_text(note, encoding="utf-8")
        return h.send(200, {"ok": True})
    n = int(h.headers.get("Content-Length", "0"))
    if not 1000 < n <= 8_000_000:
        return h.send(400, {"error": "bad_size"})
    data = h.rfile.read(n)
    if not (data[:3] == b"\xff\xd8\xff" or data[:4] == b"\x89PNG" or data[:4] == b"RIFF"):
        return h.send(400, {"error": "not_image"})
    name = f"{int(time.time())}_{hashlib.sha256(data).hexdigest()[:10]}"
    meta = {"post": h.headers.get("X-Fanding-Post", "")[:300], "at": now_kst().isoformat(),
            "batch": re.sub(r"[^0-9a-f]", "", h.headers.get("X-Fanding-Batch", ""))[:16],
            "idx": h.headers.get("X-Fanding-Index", ""), "count": h.headers.get("X-Fanding-Count", ""),
            "mode": "history" if h.headers.get("X-Fanding-Mode") == "history" else "live",
            "request_id": re.sub(r"[^0-9a-f]", "", h.headers.get("X-Fanding-Request", ""))[:32],
            "expected": h.headers.get("X-Fanding-Expected", "")[:10]}
    INBOX.mkdir(parents=True, exist_ok=True)
    (INBOX / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False))
    (INBOX / f"{name}.img").write_bytes(data)
    with bridge_state() as b:
        b["last_received"] = {"at": now_kst().isoformat(), "mode": meta["mode"]}
    return h.send(200, {"ok": True})
'''
mod_dir = TMP / "mod"
mod_dir.mkdir()
(mod_dir / "fanding_trade.py").write_text(STUB)
shutil.copy(SRC, mod_dir / "fanding_fetch_server.py")
os.environ["FFS_ROOT"] = str(TMP / "root")
sys.path.insert(0, str(mod_dir))
import fanding_trade as ft  # noqa: E402

# ── 2. 문법 ──
try:
    py_compile.compile(str(SRC), doraise=True)
    check("py_compile 통과", True)
except py_compile.PyCompileError as e:
    check("py_compile 통과", False, str(e))

ffs = importlib.import_module("fanding_fetch_server")
check("모듈 import 시 playwright 를 부르지 않음(지연 import)", "playwright" not in sys.modules)

# ── 3. 이미지 검사 = http_upload 조건 ──
PNG = b"\x89PNG\r\n\x1a\n" + os.urandom(5000)
JPG = b"\xff\xd8\xff" + os.urandom(5000)
WEBP = b"RIFF" + os.urandom(5000)
check("이미지 PNG/JPG/WebP 통과", all(ffs.image_ok(x) == "" for x in (PNG, JPG, WEBP)))
check("1000바이트 이하 거절", ffs.image_ok(b"\x89PNG" + b"0" * 996) == "bad_size")
check("8MB 초과 거절", ffs.image_ok(b"\x89PNG" + b"0" * 8_000_000) == "bad_size")
check("GIF 거절", ffs.image_ok(b"GIF89a" + b"0" * 5000) == "not_image")


# ── 4. 업로드: 발췌 http_upload 를 돌리는 가짜 사무실 서버로 POST ──
class H(BaseHTTPRequestHandler):
    def send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        if self.path == "/api/fanding/upload":
            return ft.http_upload(self)
        self.send(404, {})

    def log_message(self, *a):
        pass


srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
sc = dict(ffs.DEFAULTS, upload_url=f"http://127.0.0.1:{srv.server_address[1]}/api/fanding/upload")
exp = ft.last_session_date().isoformat()
post = "https://fanding.kr/@laofus/post/123456"
ffs.deliver(post, PNG, exp, sc)
files = sorted(p.name for p in ft.INBOX.iterdir())
imgs = [f for f in files if f.endswith(".img")]
jsons = [f for f in files if f.endswith(".json")]
check("inbox 에 .img 1개 + .json 1개", len(imgs) == 1 and len(jsons) == 1, str(files))
stem = imgs[0][:-4]
check("이름 형식 {unix시간}_{sha10}", re.fullmatch(r"\d{10}_[0-9a-f]{10}", stem)
      and stem.split("_")[1] == hashlib.sha256(PNG).hexdigest()[:10], stem)
check(".img 바이트가 원본과 동일", (ft.INBOX / imgs[0]).read_bytes() == PNG)
meta = json.loads((ft.INBOX / jsons[0]).read_text())
check("메타 키 8개 일치", set(meta) == {"post", "at", "batch", "idx", "count", "mode", "request_id", "expected"},
      str(meta))
check("mode=live (history 아님)", meta["mode"] == "live")
check("expected = last_session_date()", meta["expected"] == exp, meta["expected"])
check("post = 실제 글 주소", meta["post"] == post)
check("batch 16자리 hex, 글+날짜로 고정", re.fullmatch(r"[0-9a-f]{16}", meta["batch"])
      and meta["batch"] == hashlib.sha256(f"{post}|{exp}".encode()).hexdigest()[:16])
check("idx=0, count=1", meta["idx"] == "0" and meta["count"] == "1")
check("VR6 헤더 안 보냄 (P 업로드로 들어감)", True)  # 위에서 .img 가 생긴 것 자체가 VR6 분기를 안 탄 증거
check("last_received 기록됨(기존 http_upload 동작)",
      json.loads(ft.BRIDGE.read_text()).get("last_received", {}).get("mode") == "live")
try:
    ffs.deliver(post, b"GIF89a" + b"0" * 5000, exp, sc)
    check("불량 이미지는 업로드 전에 거절", False)
except ffs.FetchError:
    check("불량 이미지는 업로드 전에 거절", True)
for p in ft.INBOX.iterdir():
    p.unlink()

# ── 5. note: 기존 note 이름 형식·UTF-8 ──
ffs.write_note("로그인 필요 시험")
notes = list(ft.INBOX.glob("*.note"))
check("note 이름 {unix시간}_{hex6}.note", len(notes) == 1 and re.fullmatch(r"\d{10}_[0-9a-f]{6}\.note", notes[0].name))
check("note UTF-8 한글", notes[0].read_text(encoding="utf-8") == ffs.NOTE_PREFIX + "로그인 필요 시험")
check("임시 파일 남지 않음", not list(ft.INBOX.glob(".*.tmp")))
notes[0].unlink()


# ── 6. 아침 루틴 (가짜 시계) ──
class Clock:
    def __init__(self, hhmm):
        h, m = map(int, hhmm.split(":"))
        self.t = datetime(2026, 11, 13, h, m, tzinfo=timezone(timedelta(hours=9)))
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s); self.t += timedelta(seconds=s)


def run(start, results, st=None, paused=False):
    ck = Clock(start)
    calls, notes, sent = [], [], []
    seq = list(results)

    def fetch(k):
        calls.append((ck.t.strftime("%H:%M"), k))
        ck.t += timedelta(seconds=20)
        return seq.pop(0) if seq else {"kind": "no_new"}
    st = {"last_post_id": 100} if st is None else st
    res = ffs.routine(st, now=ck.now, sleep=ck.sleep, fetch=fetch,
                      send=lambda p, d, e: sent.append((p, e)), note=notes.append,
                      paused=lambda: paused, expected="2026-11-12",
                      deadline=ck.t.replace(hour=11, minute=0), retry_at=ck.t.replace(hour=9, minute=0),
                      poll_s=300)
    return res, st, calls, notes, sent, ck


OK = {"kind": "ok", "post": "https://fanding.kr/@laofus/post/101", "post_id": 101, "data": PNG}
ERR = {"kind": "error", "detail": "시험 오류"}

r, st, calls, notes, sent, ck = run("07:50", [OK])
check("A 첫 확인에 새 글 → 보냄, 1회 접속", r == "sent" and len(calls) == 1 and sent == [(OK["post"], "2026-11-12")])
check("A 상태에 done_expected·last_post_id 기록", st["done_expected"] == "2026-11-12" and st["last_post_id"] == 101)

r, st, calls, notes, sent, ck = run("07:50", [{"kind": "no_new"}] * 3 + [OK])
check("B 새 글 없으면 5분 간격 확인", r == "sent" and len(calls) == 4 and ck.slept == [300, 300, 300] and not notes)

r, st, calls, notes, sent, ck = run("08:00", [ERR, ERR])
check("C 08:00 1차 실패 → 진단 1회 + 09:00 재시도 1회 → 진단 1회 + 중단",
      r == "stopped" and len(calls) == 2 and calls[1][0] == "09:00" and len(notes) == 2 and st.get("halted"),
      f"{r} {calls} {notes}")

r, st, calls, notes, sent, ck = run("09:30", [ERR])
check("D 09:00 이후 1차 실패 → 진단 1회 + 바로 중단 (사이트 다시 안 두드림)",
      r == "stopped" and len(calls) == 1 and len(notes) == 1)

r, st, calls, notes, sent, ck = run("08:00", [ERR, OK])
check("E 1차 실패 후 09:00 재시도 성공 → 보냄", r == "sent" and len(calls) == 2 and len(notes) == 1)

r, st, calls, notes, sent, ck = run("07:50", [{"kind": "logged_out", "detail": "x"}])
check("F 로그인 풀림 → note '로그인' + 중단, 1회 접속",
      r == "logged_out" and len(calls) == 1 and "로그인" in notes[0] and st["halted"]["reason"] == "logged_out")

r, st, calls, notes, sent, ck = run("07:50", [OK], paused=True)
check("G 스캔 게이트 멈춤 → 접속 0회", r == "gate_paused" and not calls)

r, st, calls, notes, sent, ck = run("07:50", [OK], st={"last_post_id": 100, "halted": {"reason": "x"}})
check("H 자동 중단 상태 → 접속 0회", r == "halted" and not calls)

r, st, calls, notes, sent, ck = run("07:50", [OK], st={"last_post_id": 100, "done_expected": "2026-11-12"})
check("I 이미 보낸 날(주말·휴장 포함) → 접속 0회", r == "already" and not calls)

r, st, calls, notes, sent, ck = run("07:50", [{"kind": "no_new"}] * 100)
check("J 11:00 까지 새 글 없음 → 종료, 알림 안 보냄(기존 미도착 알림에 맡김)",
      r == "deadline" and not notes and ck.t >= ck.t.replace(hour=11, minute=0) and len(calls) <= 39, len(calls))

r, st, calls, notes, sent, ck = run("07:50", [OK], st={})
r2 = ffs.routine(st, now=ck.now, sleep=ck.sleep, fetch=lambda k: OK, send=lambda *a: None, note=notes.append,
                 paused=lambda: False, expected="2026-11-12", deadline=ck.t.replace(hour=11),
                 retry_at=ck.t.replace(hour=9), poll_s=300)
check("K init 전 → 접속 0회, note 는 하루 한 번만", r == "no_baseline" and r2 == "no_baseline" and not calls
      and len(notes) == 1)


def bad_send(p, d, e):
    raise ffs.FetchError("업로드 연결 실패")


ck = Clock("09:10")
notes = []
st = {"last_post_id": 100}
r = ffs.routine(st, now=ck.now, sleep=ck.sleep, fetch=lambda k: OK, send=bad_send, note=notes.append,
                paused=lambda: False, expected="2026-11-12", deadline=ck.t.replace(hour=11),
                retry_at=ck.t.replace(hour=9), poll_s=300)
check("L 업로드 실패도 오류로 처리 → 중단, done_expected 안 남김",
      r == "stopped" and "done_expected" not in st and len(notes) == 1)

# 실제 게이트 함수
ft.BRIDGE.write_text(json.dumps({"scan_gate": {"policy": "stopped"}}))
check("게이트 stopped → gate_paused() 참", ffs.gate_paused() is True)
ft.BRIDGE.write_text(json.dumps({"scan_gate": {"policy": "ready"}}))
check("게이트 ready → gate_paused() 거짓", ffs.gate_paused() is False)
check("gate_paused() 가 게이트 값을 바꾸지 않음",
      json.loads(ft.BRIDGE.read_text()) == {"scan_gate": {"policy": "ready"}})

# ── 7. 정적 검사: 비밀·금지 동작 ──
src = SRC.read_text(encoding="utf-8")
check("토큰·비밀번호 값 없음 (긴 비밀 문자열 0건)",
      not re.search(r"(token|password|passwd|secret|api_key)\s*[=:]\s*['\"][^'\"]{6,}", src, re.I))
check("비밀번호는 getpass 로만 받음", "getpass.getpass(" in src and "argparse" in src
      and "add_argument(\"--password" not in src)
check("토큰을 로그에 찍지 않음", not re.search(r"log\([^)]*token", src))
forbidden = ["vision(", "process_inbox(", "handle_image(", "handle_history_image(", "request_scan(",
             "ft.STATE", "ft.LOCKF", "ft.IMAGES", "ft.GEMINI_CFG", "scan_gate\"] =", "fanding_vr6", "X-Fanding-Kind", "X-Fanding-Mode\": \"history"]
hits = [f for f in forbidden if f in src]
check("판독·판정·주문·state.json·게이트 쓰기·VR6·history 를 건드리지 않음", not hits, str(hits))
check("버전 v1.7.0", 'VERSION = "v1.7.0"' in src)

# ── 8. 실제 브라우저 (가짜 팬딩 페이지) ──
if WANT_BROWSER:
    try:
        import playwright  # noqa: F401
        site = TMP / "site"
        (site / "@laofus/post/201").mkdir(parents=True)
        (site / "@laofus/post/202").mkdir(parents=True)
        (site / "login").mkdir()
        from zlib import compress, crc32
        import struct

        def png(w, h):
            raw = b"".join(b"\x00" + bytes([(x * 7 + y) % 256 for x in range(w)]) * 3 for y in range(h))
            def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", crc32(t + d))
            return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                    + ch(b"IDAT", compress(raw)) + ch(b"IEND", b""))
        big, small = png(900, 700), png(120, 120)
        (site / "big.png").write_bytes(big)
        (site / "small.png").write_bytes(small)
        (site / "@laofus/index.html").write_text("""<html><body><div id=list>로딩…</div><script>
setTimeout(()=>{document.getElementById('list').innerHTML=
'<a href="/@laofus/post/201/">어제 표</a><a href="/@laofus/post/202/">오늘 표</a><a href="/@laofus/membership/">멤버십</a>'},1200)
</script></body></html>""")
        (site / "@laofus/post/202/index.html").write_text(
            '<html><body><img src="/small.png"><div style="height:2500px"></div>'
            '<img loading="lazy" src="/big.png"></body></html>')
        (site / "login/index.html").write_text("<html><body>login</body></html>")
        (site / "out/@laofus").mkdir(parents=True)
        (site / "out/@laofus/index.html").write_text(
            "<html><script>location.href='/login/?next=/@laofus/'</script></html>")

        from http.server import SimpleHTTPRequestHandler
        from functools import partial

        class Q(SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
        ws = ThreadingHTTPServer(("127.0.0.1", 0), partial(Q, directory=str(site)))
        threading.Thread(target=ws.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{ws.server_address[1]}"
        bsc = dict(ffs.DEFAULTS, author_url=base + "/@laofus/",
                   post_regex=r"^http://127\.0\.0\.1:\d+/@laofus/post/(\d+)")
        t0 = time.time()
        r = ffs.fetch_once(201, bsc)
        check("브라우저: JS 렌더링 목록에서 최신 글(202) 찾음 + 가장 큰 이미지(지연 로딩) 받음",
              r.get("kind") == "ok" and r.get("post_id") == 202 and r.get("data") == big,
              str({k: v for k, v in r.items() if k != "data"}))
        check("브라우저: 이미 처리한 글이면 no_new", ffs.fetch_once(202, bsc).get("kind") == "no_new")
        r = ffs.fetch_once(201, dict(bsc, author_url=base + "/out/@laofus/"))
        check("브라우저: 로그인 페이지로 이동 → logged_out", r.get("kind") == "logged_out", str(r))
        r = ffs.fetch_once(201, dict(bsc, post_regex=r"^nomatch/(\d+)"))
        check("브라우저: 글 목록 안 보임 → logged_out", r.get("kind") == "logged_out", str(r))
        check("브라우저: 프로필 폴더 권한 700", oct(ffs.PROFILE.stat().st_mode & 0o777) == "0o700")
        print(f"     (브라우저 시험 {time.time() - t0:.1f}초)")
    except ImportError:
        print("SKIP 브라우저 시험: playwright 없음 (서버 확인 필요)")

srv.shutdown()
shutil.rmtree(TMP, ignore_errors=True)
fails = [n for n, ok in RESULTS if not ok]
print(f"\n합계 {len(RESULTS)}개 중 통과 {len(RESULTS) - len(fails)}개, 실패 {len(fails)}개")
sys.exit(1 if fails else 0)
