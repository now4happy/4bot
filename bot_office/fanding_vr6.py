#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/fanding_vr6.py   (FANDING_VR6_V1.0.0)
# 팬딩 VR6기 (TQQQ) — 2주에 한 번 게시글의 표 이미지를 받아 5번 팬딩 봇으로 보여 주는 단계
#
#  지금 되는 것 (1단계)
#    - 윈도우 PC(fanding_vr6.py)가 진행일에 최신 글의 이미지를 올림 → 5번 봇에 사진으로 알림 (배수 표시)
#    - 진행 일정(2주 주기)·배수는 서버가 관리. PC는 올리기 전에 서버에 '오늘 진행일인지' 물어봄
#    - 5번 봇 [🅥 VR6 메뉴]에서 배수·일정·표 보기·진단
#  아직 없는 것 (2단계, 표 형식 확인 후)
#    - 표 판독, 수량 계산, 메리츠 예약주문. 이 파일은 주문을 내지 않는다.
#
#  fanding_trade.py(기존 P 흐름)와 분리: 상태는 vr6.json 따로. fanding_trade.py 가 이 파일을 불러 쓰며,
#  이 파일이 오류가 나도 P 흐름이 멈추지 않도록 fanding_trade.py 쪽에서 예외를 막는다.
#  웹서버(bot-office 계정)는 INBOX 에 파일만 쓰고, 상태 저장은 상시 프로그램(root)만 한다.
# ==========================================================
import fcntl, hashlib, html, json, os, re, tempfile, time, urllib.parse, uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = "1.0.0"
R = Path(os.environ.get("OFFICE_ROOT", "/"))
HOME = R / "var/lib/bot-office/fanding"
INBOX = HOME / "inbox"
VDIR = HOME / "vr6"
STATE, LOCKF = HOME / "vr6.json", HOME / ".vr6.lock"
KST = ZoneInfo("Asia/Seoul")
WEEK = "월화수목금토일"

# 게시글 https://fanding.kr/@laofus/post/226323 은 2026-10-26(월)에 직접 진행한 회차 → 다음은 2주 뒤 월요일
DEFAULTS = {
    "symbol": "TQQQ",
    "multiplier": 2,
    "interval_days": 14,
    "next_due": "2026-11-09",
    "last_done": "2026-10-26",
    "last_post_id": 226323,
    "force": False,
    "seen": [],
    "cycles": {},
    "pc": {},
    "alerted": "",
}

MENU_LABEL, HOME_LABEL = "🅥 VR6 메뉴", "🏠 메인 메뉴"
BUTTONS = {"📋 VR6 표": "/vr6표", "📐 VR6 배수": "/vr6배수", "📅 VR6 일정": "/vr6일정",
           "🔄 VR6 지금 진행": "/vr6지금", "🩺 VR6 진단": "/vr6진단", "❓ VR6 도움말": "/vr6도움말"}

HELP = ("▫️ <b>/vr6표</b> 최근에 받은 표 다시 보기\n▫️ <b>/vr6배수</b> 현재 배수 · <b>/vr6배수 10</b> 바꾸기\n"
        "▫️ <b>/vr6일정</b> 다음 진행일 · <b>/vr6일정 2026-11-09</b> 날짜 바꾸기\n"
        "▫️ <b>/vr6지금</b> 일정과 상관없이 PC가 다음에 확인할 때 바로 진행\n▫️ <b>/vr6진단</b> PC 연락·마지막 진행 상태")
NOTE_NO_ORDER = "ℹ️ 지금은 표를 받아 보여 주는 단계예요. 표 판독·수량 계산·주문은 아직 없어요(주문 규칙 확정 전)."


# ---------------------------------------------------------- 저장
def load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save(p, data, mode=0o660):
    """원자적 저장. 이미 있는 파일이면 소유자·그룹·권한 유지 (웹서버가 읽을 수 있게)"""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        st = p.stat(); uid, gid, mode = st.st_uid, st.st_gid, st.st_mode & 0o777
    except FileNotFoundError:
        st = p.parent.stat(); uid, gid = st.st_uid, st.st_gid
    fd, tmp = tempfile.mkstemp(dir=p.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.flush(); os.fsync(f.fileno())
    try:
        os.chown(tmp, uid, gid)
    except PermissionError:
        pass
    os.chmod(tmp, mode)
    os.replace(tmp, p)


def _fill(st):
    for k, v in DEFAULTS.items():
        if k not in st:
            st[k] = json.loads(json.dumps(v))
    return st


@contextmanager
def locked():
    HOME.mkdir(parents=True, exist_ok=True)
    with open(LOCKF, "a") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        st = _fill(load(STATE, {}))
        yield st
        save(STATE, st)
        fcntl.flock(lf, fcntl.LOCK_UN)


def today_kst(now=None):
    return (now or datetime.now(KST)).date()


def _d(s):
    return date.fromisoformat(s)


def _wd(d):
    return WEEK[d.weekday()]


def _post_id(url):
    m = re.search(r"/(?:post|posts|p)/(\d+)", url or "")
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------- 웹 수신 (fanding_trade.http_upload 가 토큰 확인 뒤 넘김)
def status_reply(now=None):
    """윈도우 PC 가 '오늘 진행일인가?' 물어볼 때 답. 읽기만 한다."""
    readable = STATE.exists() and os.access(STATE, os.R_OK)
    st = _fill(load(STATE, {}))
    due = bool(st["force"]) or today_kst(now) >= _d(st["next_due"])
    return {"ok": True, "vr6": {"due": due, "cycle": st["next_due"], "last_post_id": int(st["last_post_id"]),
                                "multiplier": st["multiplier"], "symbol": st["symbol"], "force": bool(st["force"]),
                                "state_ok": bool(readable or not STATE.exists())}}


def http_upload(h):
    """X-Fanding-Kind: vr6-status(질문) · vr6(이미지) · vr6-done(한 글 전송 끝). 웹서버는 INBOX 에 파일만 쓴다."""
    kind = h.headers.get("X-Fanding-Kind", "")
    try:
        n = int(h.headers.get("Content-Length", "0"))
    except ValueError:
        n = 0
    stamp = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"
    try:
        INBOX.mkdir(parents=True, exist_ok=True)
        if kind == "vr6-status":
            if n:
                h.rfile.read(min(n, 4096))
            (INBOX / f"{stamp}.vr6ping").write_text(json.dumps(
                {"at": time.time(), "version": h.headers.get("X-Fanding-Version", "")[:20]}), encoding="utf-8")
            return h.send(200, status_reply())
        if kind == "vr6-done":
            if n:
                h.rfile.read(min(n, 4096))
            meta = {"post": h.headers.get("X-Fanding-Post", "")[:300], "count": h.headers.get("X-Fanding-Count", "")[:4],
                    "at": time.time()}
            (INBOX / f"{stamp}.vr6done").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            return h.send(200, {"ok": True})
        if kind == "vr6":
            if not 1000 < n <= 8_000_000:
                return h.send(400, {"error": "bad_size"})
            h.connection.settimeout(60)
            data = h.rfile.read(n)
            if not (data[:3] == b"\xff\xd8\xff" or data[:4] == b"\x89PNG" or data[:4] == b"RIFF"):
                return h.send(400, {"error": "not_image"})
            name = f"{int(time.time())}_{hashlib.sha256(data).hexdigest()[:10]}"
            meta = {"kind": "vr6", "post": h.headers.get("X-Fanding-Post", "")[:300],
                    "idx": h.headers.get("X-Fanding-Index", "")[:4], "count": h.headers.get("X-Fanding-Count", "")[:4]}
            (INBOX / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False))
            (INBOX / f"{name}.img").write_bytes(data)
            return h.send(200, {"ok": True})
    except OSError as e:
        return h.send(500, {"error": "save_failed", "detail": str(e)[:200]})
    return h.send(400, {"error": "bad_kind"})


# ---------------------------------------------------------- 상시 프로그램이 INBOX 처리
def _vr6_images_waiting():
    for f in INBOX.glob("*.img"):
        if load(f.with_suffix(".json"), {}).get("kind") == "vr6":
            return True
    return False


def process_inbox(tg):
    INBOX.mkdir(parents=True, exist_ok=True)
    for f in sorted(INBOX.glob("*.vr6ping")):
        info = load(f, {})
        with locked() as st:
            st["pc"] = {"at": info.get("at", time.time()), "version": info.get("version", "")}
        f.unlink(missing_ok=True)
    for f in sorted(INBOX.glob("*.img")):
        mf = f.with_suffix(".json")
        meta = load(mf, {})
        if meta.get("kind") != "vr6":
            continue
        _handle_image(tg, f.read_bytes(), meta)      # 오류가 나면 파일을 지우지 않아 다음 순회에 다시 시도
        f.unlink(missing_ok=True)
        mf.unlink(missing_ok=True)
    if _vr6_images_waiting():
        return                                  # 이미지를 다 처리한 뒤에 '끝' 표시를 처리
    for f in sorted(INBOX.glob("*.vr6done")):
        _handle_done(tg, load(f, {}))
        f.unlink(missing_ok=True)


def _handle_image(tg, data, meta):
    sha = hashlib.sha256(data).hexdigest()
    ext = "png" if data[:4] == b"\x89PNG" else "jpg"
    with locked() as st:
        dup = sha in st["seen"] and not st["force"]
        cycle, mult, sym = st["next_due"], st["multiplier"], st["symbol"]
    if dup:
        print("VR6 이미 받은 이미지 → 무시", flush=True)
        return "dup"
    VDIR.mkdir(parents=True, exist_ok=True)
    name = f"{cycle}_{sha[:8]}.{ext}"
    path = VDIR / name
    path.write_bytes(data)
    idx, count = meta.get("idx") or "?", meta.get("count") or "?"
    tg.photo(path, f"🅥 <b>VR6 표</b> {idx}/{count} · {sym} · 배수 ×{mult}\n글: {html.escape(meta.get('post', ''))[:200]}")
    with locked() as st:
        st["seen"] = ([x for x in st["seen"] if x != sha] + [sha])[-80:]      # 사진 전송 뒤에 '받음' 기록
        cyc = st["cycles"].setdefault(cycle, {"images": [], "post": meta.get("post", "")})
        if name not in cyc["images"]:
            cyc["images"].append(name)
        for k in sorted(st["cycles"])[:-12]:
            st["cycles"].pop(k, None)
    return "ok"


def _handle_done(tg, meta, now=None):
    pid = _post_id(meta.get("post", ""))
    today = today_kst(now)
    with locked() as st:
        cycle = st["next_due"]
        images = st["cycles"].get(cycle, {}).get("images", [])
        advanced = today >= _d(cycle)
        if pid > int(st["last_post_id"]):
            st["last_post_id"] = pid
        if advanced:
            nxt = _d(cycle)
            while nxt <= today:
                nxt += timedelta(days=int(st["interval_days"]))
            st["next_due"] = nxt.isoformat()
            st["last_done"] = today.isoformat()
            st["alerted"] = ""
        st["force"] = False
        mult, sym, nd = st["multiplier"], st["symbol"], _d(st["next_due"])
    head = "✅ <b>VR6 표 수신 완료</b>"
    if advanced:
        tail = f"다음 진행 예정: <b>{nd.isoformat()}({_wd(nd)})</b>"
    else:
        tail = f"(일정 밖 수동 전송이라 다음 진행일은 그대로: {nd.isoformat()}({_wd(nd)}))"
    tg.send(f"{head} · {sym} · 배수 ×{mult}\n이번에 보여 드린 이미지 {len(images)}장 · 글 번호 {pid or '?'}\n{tail}\n{NOTE_NO_ORDER}")


def tick(tg, now=None):
    """진행일이 지났는데 표가 안 왔으면 한 번만 알림 (PC 꺼짐·로그인 풀림 대비)"""
    now = now or datetime.now(KST)
    with locked() as st:
        due = _d(st["next_due"])
        late = (today_kst(now) > due) or (today_kst(now) == due and now.hour >= 18)
        if not late or st["alerted"] == st["next_due"]:
            return
        st["alerted"] = st["next_due"]
        pc = st.get("pc") or {}
    seen = datetime.fromtimestamp(pc["at"], KST).strftime("%m-%d %H:%M") if pc.get("at") else "기록 없음"
    tg.send(f"⚠️ <b>VR6 진행일({due.isoformat()}, {_wd(due)})이 지났는데 아직 표를 못 받았어요</b>\n"
            f"PC가 마지막으로 서버에 물어본 때: {seen}\nWindows PC가 켜져 있는지, 팬딩 로그인이 풀리지 않았는지 확인하고 "
            "PC에서 <code>py fanding_vr6.py run</code> 을 실행하세요. 상태는 /vr6진단")


# ---------------------------------------------------------- 5번 봇 메뉴·명령
def keyboard():
    labels = list(BUTTONS)
    rows = [[{"text": t} for t in labels[i:i + 2]] for i in range(0, len(labels), 2)]
    rows.append([{"text": HOME_LABEL}])
    return rows


def alias(t):
    return BUTTONS.get(t, t)


def _mult_rows(cur):
    cb = lambda n: {"text": f"×{n}", "callback_data": f"vm:mt:{n}"}
    return [[{"text": "➖ 1", "callback_data": f"vm:mt:{max(1, cur - 1)}"}, {"text": f"현재 ×{cur}", "callback_data": "vm:noop"},
             {"text": "➕ 1", "callback_data": f"vm:mt:{min(50, cur + 1)}"}],
            [cb(n) for n in (1, 2, 3, 4, 5)], [cb(n) for n in (6, 7, 8, 10, 12)]]


def summary_text(now=None):
    st = _fill(load(STATE, {}))
    nd = _d(st["next_due"])
    return (f"🅥 <b>VR6 메뉴</b> · {st['symbol']}\n배수 <b>×{st['multiplier']}</b> · 다음 진행 <b>{nd.isoformat()}({_wd(nd)})</b> "
            f"· 주기 {st['interval_days']}일\n{NOTE_NO_ORDER}")


def diagnosis(now=None):
    st = _fill(load(STATE, {}))
    pc = st.get("pc") or {}
    seen = datetime.fromtimestamp(pc["at"], KST).strftime("%Y-%m-%d %H:%M") if pc.get("at") else "아직 없음"
    cyc = st["cycles"].get(max(st["cycles"])) if st["cycles"] else None
    nd = _d(st["next_due"])
    return ("🩺 <b>VR6 진단</b>\n"
            f"• PC가 마지막으로 서버에 물어본 때: {seen}" + (f" (프로그램 v{html.escape(str(pc.get('version')))})" if pc.get("version") else "") + "\n"
            f"• 다음 진행일: {nd.isoformat()}({_wd(nd)}) · 지금 진행 요청: {'켜짐' if st['force'] else '꺼짐'}\n"
            f"• 마지막 완료: {st['last_done']} · 마지막으로 처리한 글 번호: {st['last_post_id']}\n"
            f"• 최근 받은 표: {len(cyc['images']) if cyc else 0}장\n"
            f"• 상태 파일: {'있음' if STATE.exists() else '아직 없음(기본값 사용)'}")


def _set_mult(tg, n):
    if not 1 <= n <= 50:
        tg.send("배수는 1~50 사이로 적어 주세요."); return
    with locked() as st:
        old = st["multiplier"]; st["multiplier"] = n
    tg.send(f"📐 VR6 배수 ×{old} → <b>×{n}</b>\n다음에 받는 표부터 알림에 표시돼요.", _mult_rows(n))


def _shift(tg, days):
    with locked() as st:
        nd = _d(st["next_due"]) + timedelta(days=days)
        st["next_due"] = nd.isoformat(); st["alerted"] = ""
    tg.send(f"📅 다음 진행일을 <b>{nd.isoformat()}({_wd(nd)})</b> 로 바꿨어요.")


def handle_text(tg, text):
    """처리했으면 True"""
    t = alias(text.strip())
    low = t.lower()
    if t == MENU_LABEL or low in ("/vr6", "vr6"):
        tg.send(summary_text() + "\n\n" + HELP, keyboard=keyboard()); return True
    if low in ("/vr6도움말", "vr6도움말"):
        tg.send("🅥 <b>VR6 사용법</b>\n" + HELP, keyboard=keyboard()); return True
    m = re.fullmatch(r"(?:/vr6배수|vr6배수)\s*(\d+)?", t, re.I)
    if m:
        if m.group(1):
            _set_mult(tg, int(m.group(1)))
        else:
            cur = _fill(load(STATE, {}))["multiplier"]
            tg.send(f"📐 VR6 지금 배수는 <b>×{cur}</b> 예요. 아래 버튼으로 바꾸세요. (글자로는 <code>/vr6배수 10</code>)", _mult_rows(cur))
        return True
    m = re.fullmatch(r"(?:/vr6일정|vr6일정)\s*(\d{4}-\d{2}-\d{2})?", t, re.I)
    if m:
        if m.group(1):
            try:
                nd = date.fromisoformat(m.group(1))
            except ValueError:
                tg.send("날짜를 <code>2026-11-09</code> 모양으로 적어 주세요."); return True
            with locked() as st:
                st["next_due"] = nd.isoformat(); st["alerted"] = ""
            note = "" if nd.weekday() == 0 else f"\n(참고: {_wd(nd)}요일이에요. 보통은 월요일이에요.)"
            tg.send(f"📅 다음 진행일을 <b>{nd.isoformat()}({_wd(nd)})</b> 로 바꿨어요.{note}")
        else:
            st = _fill(load(STATE, {})); nd = _d(st["next_due"])
            tg.send(f"📅 다음 진행일: <b>{nd.isoformat()}({_wd(nd)})</b> · 주기 {st['interval_days']}일\n"
                    f"마지막 완료: {st['last_done']}\n날짜 바꾸기: <code>/vr6일정 2026-11-09</code>",
                    [[{"text": "➕ 2주 뒤로 미루기", "callback_data": "vm:sh:14"}]])
        return True
    if low in ("/vr6지금", "vr6지금"):
        with locked() as st:
            st["force"] = True
        tg.send("🔄 <b>VR6 지금 진행</b> 요청을 켰어요.\nWindows PC에서 <code>py fanding_vr6.py run</code> (또는 run.bat)을 실행하면 "
                "오늘이 진행일이 아니어도 최신 글의 표를 가져와요. 끝나면 요청은 꺼져요."); return True
    if low in ("/vr6표", "vr6표"):
        st = _fill(load(STATE, {}))
        cyc = st["cycles"].get(max(st["cycles"])) if st["cycles"] else None
        names = [n for n in (cyc or {}).get("images", []) if (VDIR / n).exists()][:8]
        if not names:
            tg.send("아직 받은 VR6 표가 없어요."); return True
        for i, n in enumerate(names, 1):
            tg.photo(VDIR / n, f"🅥 <b>VR6 표</b> {i}/{len(names)} · {st['symbol']} · 현재 배수 ×{st['multiplier']}")
        return True
    if low in ("/vr6진단", "vr6진단"):
        tg.send(diagnosis()); return True
    return False


def callback(tg, cb):
    data = cb.get("data", "")
    if not data.startswith("vm:"):
        return False
    parts = data.split(":")
    tg.answer(cb.get("id"))
    if parts[1] == "mt" and len(parts) > 2 and parts[2].isdigit():
        _set_mult(tg, int(parts[2]))
    elif parts[1] == "sh" and len(parts) > 2 and parts[2].lstrip("-").isdigit():
        _shift(tg, int(parts[2]))
    return True
