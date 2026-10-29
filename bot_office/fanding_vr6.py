#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/fanding_vr6.py   (FANDING_VR6_V2.1.0)
# 팬딩 VR6기 (TQQQ) — 2주에 한 번 게시글의 표 이미지를 받아 판독 → 메리츠 VR6 계좌에 2주 기간잔량 지정가 예약
#
#  2.1.0 (2026-10-29) 환전 버튼 + 09:00 알림
#    - 주문표 알림은 KST 09:00 (메리츠 예약 접수·환전이 되는 시각). 표가 그 전에 오면 09:00 까지 모아 두었다가 보냄
#    - 보유 달러(예수금)가 매수 필요 달러보다 적으면 [💱 환전 금액 확인] 버튼 → 확인 화면 → [✅ 환전 실행]
#      (2차 확인 · 10분 안 · 실행 직전 환율이 1% 넘게 바뀌면 중단 · VR6 계좌 키로만). /vr6환전 · /vr6환전 300
#    - 밤 마감 30분 전 알림은 결정 대기(버튼 안 누름)이거나 달러가 부족할 때만. 자동환전은 없음
#    - 잔고가 표와 달라도 막지 않음: 매도 합계(표×배수) > 매도가능 → 가장 높은 매도가 줄부터 모자란 만큼 줄여 주문
#      (매도가능은 처음 접수 직전에 다시 조회) · 잔고 조회 실패 → 매도 표 수량 그대로 · 보유 수량 차이는 참고 표시만
#    - 거래소 번호를 한 번 알아내면 vr6_exch_seen.json 에 저장 (TQQQ 0주가 돼도 주문 가능)
#  2.0.0 (2026-10-29) 주문 단계 추가
#    - 글의 이미지 중 '매수계획/매도계획' 표를 AI 로 찾아 2번 교차 판독(fanding_trade.vision 사용, P 와 같은 AI)
#    - VR 검산: 매수점 = 최소값 ÷ (체결 전 개수), 매도점 = 최대값 ÷ (체결 전 개수), Pool 은 매수마다 빼고 매도마다 더함.
#      숫자가 하나라도 안 맞으면 '판독 의심' → 자동주문 안 함
#    - 배수: 표는 1배수(줄마다 1주). 배수 ×N 이면 줄마다 N주, 가격은 그대로
#    - 주문: 지정가("1") · 기간잔량("2") · 장개시 발주("0") · 시작일=표 기간 첫 거래일(마감 지난 날은 건너뜀) · 종료일=표 끝날
#      매수·매도 모두. 5번 봇 [✅ 주문]/[❌] · 안 누르면 첫 발주일 예약마감(08:30 ET) 10분 전에 자동주문(점검 모두 통과 시)
#    - 계좌: VR6 전용 키 /etc/bot-office/meritz_vr6.json (P 키와 별도, 토큰 파일도 별도). 키 없으면 주문 안 함
#    - 알림에 매수 필요 달러·보유 달러·부족액 표시 (환전은 사용자가 직접. 자동환전 없음)
#    - 이전 회차 주문은 기간이 끝나면 증권사에서 없어지므로 취소하지 않음
#    - 명령 추가: /vr6주문 · /vr6재판독 · /vr6자동켜기 · /vr6자동끄기
#  1.0.0 표 이미지를 받아 5번 봇에 보여 주는 단계 (진행 일정·배수 관리)
#
#  fanding_trade.py(기존 P 흐름)와 분리: 상태는 vr6.json 따로. fanding_trade.py 가 이 파일을 불러 쓰며,
#  이 파일이 오류가 나도 P 흐름이 멈추지 않도록 fanding_trade.py 쪽에서 예외를 막는다.
#  웹서버(bot-office 계정)는 INBOX 에 파일만 쓰고, 상태 저장·주문은 상시 프로그램(root)만 한다.
# ==========================================================
import fcntl, hashlib, html, json, os, re, tempfile, time, urllib.parse, uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = "2.1.0"
R = Path(os.environ.get("OFFICE_ROOT", "/"))
HOME = R / "var/lib/bot-office/fanding"
INBOX = HOME / "inbox"
VDIR = HOME / "vr6"
STATE, LOCKF = HOME / "vr6.json", HOME / ".vr6.lock"
KST, ET = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
KEYS_VR6 = R / "etc/bot-office/meritz_vr6.json"     # VR6 계좌 키 (P 의 meritz.json 과 별도, GitHub 에 올리지 않음)
TOKEN_VR6 = HOME / "meritz_vr6_token.json"
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
    # 2.0.0 주문 단계
    "auto_order": True,          # 버튼 안 누르면 첫 발주일 마감 10분 전 자동주문 (점검 모두 통과 시)
    "price_market": "OQ",        # 메리츠 시세 조회 거래소 (TQQQ = 나스닥 OQ)
    "exch_id": "",               # 예약주문 거래소 번호. 비우면 VR6 계좌 잔고에서 찾음
    "cutoff_et": "08:30",        # 예약 마감으로 보는 시각 (미국 동부, 정규장 1시간 전) — P 와 같은 기준
    "alarm_before_min": 30,
    "auto_before_min": 10,
    "submit_kst": "09:01",       # 메리츠 예약 접수는 한국시간 09:00 부터
    "notice_kst": "09:00",       # 주문표 알림 시각 (그 전에 받은 표는 이때 보냄)
    "plans": {},
}

MENU_LABEL, HOME_LABEL = "🅥 VR6 메뉴", "🏠 메인 메뉴"
BUTTONS = {"📝 VR6 주문": "/vr6주문", "📋 VR6 표": "/vr6표", "📐 VR6 배수": "/vr6배수", "📅 VR6 일정": "/vr6일정",
           "🔄 VR6 지금 진행": "/vr6지금", "🩺 VR6 진단": "/vr6진단", "❓ VR6 도움말": "/vr6도움말"}

HELP = ("▫️ <b>/vr6주문</b> 이번 회차 주문표·주문 상태 (버튼 다시 띄우기)\n"
        "▫️ <b>/vr6표</b> 최근에 받은 표 다시 보기 · <b>/vr6재판독</b> 받은 표를 다시 판독\n"
        "▫️ <b>/vr6배수</b> 현재 배수 · <b>/vr6배수 10</b> 바꾸기\n"
        "▫️ <b>/vr6일정</b> 다음 진행일 · <b>/vr6일정 2026-11-09</b> 날짜 바꾸기\n"
        "▫️ <b>/vr6지금</b> 일정과 상관없이 PC가 다음에 확인할 때 바로 진행\n"
        "▫️ <b>/vr6자동켜기</b> · <b>/vr6자동끄기</b> 버튼 안 누를 때 자동주문\n"
        "▫️ <b>/vr6환전</b> 부족 달러 환전 확인 · <b>/vr6환전 300</b> 금액 지정 (실행은 확인 버튼에서만)\n"
        "▫️ <b>/vr6진단</b> PC 연락·계좌 연결·마지막 진행 상태")


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
    """이미지는 조용히 저장만 (2.0.0). 글 전송이 끝나면(_handle_done) 주문표를 찾아 한 번에 알림"""
    sha = hashlib.sha256(data).hexdigest()
    ext = "png" if data[:4] == b"\x89PNG" else "jpg"
    with locked() as st:
        dup = sha in st["seen"] and not st["force"]
        cycle = st["next_due"]
    if dup:
        print("VR6 이미 받은 이미지 → 무시", flush=True)
        return "dup"
    VDIR.mkdir(parents=True, exist_ok=True)
    name = f"{cycle}_{sha[:8]}.{ext}"
    (VDIR / name).write_bytes(data)
    with locked() as st:
        st["seen"] = ([x for x in st["seen"] if x != sha] + [sha])[-80:]
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
    tail = (f"다음 진행 예정: <b>{nd.isoformat()}({_wd(nd)})</b>" if advanced
            else f"(일정 밖 수동 전송이라 다음 진행일은 그대로: {nd.isoformat()}({_wd(nd)}))")
    tg.send(f"✅ <b>VR6 표 수신 완료</b> · {sym} · 배수 ×{mult}\n받은 이미지 {len(images)}장 · 글 번호 {pid or '?'}\n{tail}\n"
            "🔎 주문표(매수계획·매도계획)를 찾아 판독할게요…")
    try:
        build_plan(tg, cycle, now=now)
    except Exception as e:      # 판독 오류로 '끝' 파일이 계속 남아 AI 를 반복 호출하지 않게, 알리고 끝낸다
        replay("vr6_plan_build", "failed", type(e).__name__, event_type="decision", cycle=cycle)
        tg.send(f"🚨 <b>VR6 주문표 판독 오류</b>\n{html.escape(str(e))[:300]}\n주문하지 않았어요. /vr6재판독 으로 다시 해 보세요.")


# ---------------------------------------------------------- 로그 (start.md 2절: 한 줄 JSON, 금액·식별자 없음)
def replay(event, outcome, reason="", event_type="decision", **fields):
    try:
        now = datetime.now(timezone.utc)
        print(json.dumps({"ts_utc": now.isoformat(timespec="seconds"),
                          "ts_kst": now.astimezone(KST).isoformat(timespec="seconds"),
                          "correlation_id": fields.pop("cid", ""), "service": "fanding-vr6", "actor": "scheduler",
                          "event_type": event_type, "event": event, "outcome": outcome, "reason": reason,
                          "version": VERSION, **fields}, ensure_ascii=False), flush=True)
    except Exception:
        pass


# ---------------------------------------------------------- 표 판독 (AI 는 fanding_trade.vision 사용)
_ROW = {"type": "OBJECT", "properties": {"qty": {"type": "INTEGER", "description": "잔여개수"},
                                          "price": {"type": "NUMBER", "description": "매수점/매도점"},
                                          "pool": {"type": "NUMBER", "description": "Pool"}},
        "required": ["qty", "price", "pool"]}
PLAN_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_vr_plan": {"type": "BOOLEAN"},
        "reason": {"type": "STRING"},
        "title": {"type": "STRING", "description": "맨 위 제목 (예: VR 6기 41주차)"},
        "start_md": {"type": "STRING", "description": "기간 시작 MM-DD (예: 10월 26일 → 10-26)"},
        "end_md": {"type": "STRING", "description": "기간 끝 MM-DD (예: 11월 6일 → 11-06)"},
        "min_value": {"type": "NUMBER", "description": "매수계획 표의 노란 칸 최소값"},
        "buy_base_qty": {"type": "INTEGER", "description": "매수계획 노란 줄 잔여개수"},
        "buy_base_pool": {"type": "NUMBER", "description": "매수계획 노란 줄 Pool"},
        "buys": {"type": "ARRAY", "items": _ROW},
        "max_value": {"type": "NUMBER", "description": "매도계획 표의 노란 칸 최대값"},
        "sell_base_qty": {"type": "INTEGER", "description": "매도계획 노란 줄 잔여개수"},
        "sell_base_pool": {"type": "NUMBER", "description": "매도계획 노란 줄 Pool"},
        "sells": {"type": "ARRAY", "items": _ROW},
    },
    "required": ["is_vr_plan", "start_md", "end_md", "min_value", "max_value", "buy_base_qty", "sell_base_qty",
                 "buys", "sells"],
}
PLAN_PROMPTS = [
    "이 이미지가 VR(밸류 리밸런싱) '매수계획 / 매도계획' 표인지 판단하고, 맞으면 숫자를 그대로 옮기세요. 계산·추측 금지.\n"
    "특징: 맨 위 'VR 6기 ○○주차 < ○월 ○일 ~ ○월 ○일 >' 제목, 왼쪽 '매수계획 2주간 기간잔량 지정가 예약매수' 표"
    "(칸: 최소값 | 잔여개수 | 매수점 | Pool), 오른쪽 '매도계획' 표(칸: 최대값 | 잔여개수 | 매도점 | Pool).\n"
    "맞으면 is_vr_plan=true. 각 표의 노란 첫 줄(최소값·최대값, 잔여개수, Pool)은 min_value/max_value, *_base_qty, *_base_pool 에,\n"
    "그 아래 줄(매수점·매도점이 빨간 숫자로 있는 줄)은 위에서 아래 순서로 buys / sells 에 {qty: 잔여개수, price: 매수점·매도점, pool: Pool}.\n"
    "기간은 start_md, end_md 를 MM-DD 로. 아니면 is_vr_plan=false 로 하고 숫자 칸은 0, 배열은 빈 배열.",
    "Transcribe this VR trading plan image exactly. Do not compute or guess. If it is not the two-table plan "
    "(left '매수계획' with columns 최소값/잔여개수/매수점/Pool, right '매도계획' with columns 최대값/잔여개수/매도점/Pool), "
    "set is_vr_plan=false. Otherwise: title = top title; start_md/end_md = the date range in the title as MM-DD; "
    "min_value, buy_base_qty, buy_base_pool = the yellow first row of the buy table; buys = each following row top to bottom "
    "as {qty: 잔여개수, price: 매수점, pool: Pool}; max_value, sell_base_qty, sell_base_pool and sells likewise for the sell table. "
    "Copy every decimal digit exactly.",
]


def _ft():
    import fanding_trade          # 같은 폴더. AI 판독 순서·키 설정을 P 와 함께 쓴다
    return fanding_trade


def _num(v, nd=2):
    try:
        x = float(str(v).replace(",", "").replace("$", ""))
        return round(x, nd) if x == x else None
    except (TypeError, ValueError):
        return None


def _md(v):
    m = re.search(r"(\d{1,2})\D+(\d{1,2})", str(v or ""))
    return f"{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def normalize(r):
    def rows(lst):
        out = []
        for x in lst or []:
            try:
                q = int(x.get("qty"))
            except (TypeError, ValueError, AttributeError):
                continue
            pr, pool = _num(x.get("price")), _num(x.get("pool"))
            if pr and pr > 0:
                out.append({"qty": q, "price": pr, "pool": pool})
        return out
    flag = r.get("is_vr_plan")
    flag = flag if isinstance(flag, bool) else str(flag).strip().lower() in ("true", "yes", "1")
    toint = lambda v: int(v) if str(v).strip().lstrip("-").isdigit() else None
    return {"is_plan": flag, "title": str(r.get("title") or "")[:60], "start_md": _md(r.get("start_md")),
            "end_md": _md(r.get("end_md")), "min_value": _num(r.get("min_value")), "max_value": _num(r.get("max_value")),
            "buy_base_qty": toint(r.get("buy_base_qty")), "buy_base_pool": _num(r.get("buy_base_pool")),
            "sell_base_qty": toint(r.get("sell_base_qty")), "sell_base_pool": _num(r.get("sell_base_pool")),
            "buys": rows(r.get("buys")), "sells": rows(r.get("sells"))}


def core(p):
    rows = lambda lst: tuple((x["qty"], x["price"], x["pool"]) for x in lst)
    return (p["start_md"], p["end_md"], p["min_value"], p["max_value"], p["buy_base_qty"], p["buy_base_pool"],
            p["sell_base_qty"], p["sell_base_pool"], rows(p["buys"]), rows(p["sells"]))


def read_plan(img, avoid=""):
    ft = _ft()
    p = normalize(ft.vision(img, PLAN_PROMPTS[1 if avoid else 0], PLAN_SCHEMA, 3072, avoid=avoid))
    return p, ft.LAST_PROVIDER.get("name", "")


def vr_math(p):
    """VR 표 검산. [(통과?, 설명)] — 표 숫자끼리 맞는지만 본다 (AI 오독 잡기)"""
    out = []
    add = lambda ok, msg: out.append({"ok": bool(ok), "msg": msg})
    mn, mx = p.get("min_value") or 0, p.get("max_value") or 0
    for side, base_q, base_pool, rows, lim in (("매수", p["buy_base_qty"], p["buy_base_pool"], p["buys"], mn),
                                               ("매도", p["sell_base_qty"], p["sell_base_pool"], p["sells"], mx)):
        if not rows:
            add(True, f"{side} 줄 없음 (표에 {side}이 없는 회차)"); continue
        if not base_q or not lim or base_pool is None:
            add(False, f"{side} 표 첫 줄(기준 개수·{'최소값' if side == '매수' else '최대값'}·Pool)을 못 읽음"); continue
        bad, q, pool = [], base_q, base_pool
        step = 1 if side == "매수" else -1
        for r in rows:
            exp_q = q + step
            exp_price = round(lim / q, 2)               # 체결 전 개수로 나눈 값
            exp_pool = round(pool - r["price"] if side == "매수" else pool + r["price"], 2)
            if r["qty"] != exp_q:
                bad.append(f"개수 {r['qty']}(기대 {exp_q})")
            if abs(r["price"] - exp_price) > 0.011:
                bad.append(f"{r['price']:g}(계산 {exp_price:g})")
            if r["pool"] is None or abs(r["pool"] - exp_pool) > 0.011:
                bad.append(f"Pool {r['pool']}(계산 {exp_pool:g})")
            if side == "매수" and exp_pool < -0.005:
                bad.append("Pool 이 0 아래")
            q, pool = exp_q, exp_pool if r["pool"] is None else r["pool"]
        add(not bad, f"{side} 검산 {len(rows)}줄 일치 ({'최소값' if side == '매수' else '최대값'}÷개수, Pool 누적)" if not bad
            else f"{side} 검산 불일치: " + ", ".join(bad[:6]))
    if p["buy_base_qty"] and p["sell_base_qty"]:
        add(p["buy_base_qty"] == p["sell_base_qty"], f"기준 보유 개수 매수표 {p['buy_base_qty']} / 매도표 {p['sell_base_qty']}")
    if p["buy_base_pool"] is not None and p["sell_base_pool"] is not None:
        add(abs(p["buy_base_pool"] - p["sell_base_pool"]) <= 0.011, "기준 Pool 매수표·매도표 같음")
    return out


def table_dates(p, ref):
    """표의 MM-DD 기간 → 실제 날짜 (연도는 진행일에 가장 가까운 해)"""
    try:
        sm, sd = map(int, p["start_md"].split("-")); em, ed = map(int, p["end_md"].split("-"))
        cands = [date(y, sm, sd) for y in (ref.year - 1, ref.year, ref.year + 1)]
        start = min(cands, key=lambda d: abs((d - ref).days))
        end = date(start.year, em, ed)
        if end < start:
            end = date(start.year + 1, em, ed)
        return start, end
    except (ValueError, AttributeError):
        return None, None


# ---------------------------------------------------------- 시간 계산
def _hm(s):
    h, m = str(s).split(":")
    return int(h), int(m)


def cutoff_kst(d, st):
    h, m = _hm(st["cutoff_et"])
    return datetime(d.year, d.month, d.day, h, m, tzinfo=ET).astimezone(KST)


def first_order_day(start, end, now, st):
    """표 기간 안에서 아직 예약 마감 전인 첫 평일 (휴장일은 고려 안 함 — 기간잔량이라 다음 날 다시 나감)"""
    d = start
    while d <= end:
        if d.weekday() < 5 and now < cutoff_kst(d, st):
            return d
        d += timedelta(days=1)
    return None


def deadlines(plan, st):
    cut = cutoff_kst(_d(plan["order_start"]), st)
    return cut - timedelta(minutes=int(st["alarm_before_min"])), cut - timedelta(minutes=int(st["auto_before_min"])), cut


# ---------------------------------------------------------- 메리츠 VR6 계좌 (조회는 읽기만)
def client():
    from meritz_client import Meritz
    return Meritz(KEYS_VR6, token_cache=TOKEN_VR6)


def account(st, m=None):
    snap = {"at": datetime.now(KST).isoformat(timespec="minutes"), "errors": []}
    if not KEYS_VR6.exists():
        snap["errors"].append("VR6 계좌 키 파일 없음 (/etc/bot-office/meritz_vr6.json)")
        return snap
    try:
        m = m or client()
    except Exception as e:
        snap["errors"].append(f"키 파일 읽기 오류: {type(e).__name__}"); return snap
    try:
        pr = m.price(st["symbol"], st["price_market"])
        snap.update(price=pr["price"], prev_close=pr["prev_close"])
    except Exception as e:
        snap["errors"].append(f"시세: {str(e)[:120]}")
    try:
        hold, sellable, exch, avg = m.holding(st["symbol"])
        snap.update(holding=hold, sellable=sellable, exch_id=exch)
        if exch and seen_exch(st["symbol"]) != exch:            # 0주가 돼도 쓰도록 저장
            d = load(EXCH_SEEN, {}); d[st["symbol"]] = exch; save(EXCH_SEEN, d, 0o600)
    except Exception as e:
        snap["errors"].append(f"잔고: {str(e)[:120]}")
    for k, fn in (("usd_cash", "usd_cash"), ("usd_est", "usd_estimated")):
        try:
            snap[k] = getattr(m, fn)()
        except Exception:
            pass
    return snap


# ---------------------------------------------------------- 주문표 만들기
def raw_lines(plan):
    """[(side, price, qty)] — 표의 줄마다 배수만큼"""
    k = int(plan["mult"])
    p = plan["parsed"]
    return [("buy", r["price"], k) for r in p["buys"]] + [("sell", r["price"], k) for r in p["sells"]]


def cap_sells(lines, sellable):
    """매도 합계가 매도가능보다 많으면 가장 높은 매도가 줄부터 모자란 만큼 줄임 (줄 순서·개수 그대로, 0 가능)"""
    if sellable is None:
        return list(lines), 0
    short = sum(q for s, _, q in lines if s == "sell") - int(sellable)
    out, cut = list(lines), 0
    for i in sorted((i for i, (s, _, _) in enumerate(out) if s == "sell"), key=lambda i: -out[i][1]):
        if short <= 0:
            break
        s, pr, q = out[i]
        d = min(q, short)
        out[i] = (s, pr, q - d)
        short -= d; cut += d
    return out, cut


def order_lines(plan, keep_zero=False):
    """실제로 넣을 주문 (매도가능이 모자라면 줄인 수량). keep_zero=True 면 표 줄 순서 그대로(0 포함)"""
    lines, _ = cap_sells(raw_lines(plan), (plan.get("account") or {}).get("sellable"))
    return lines if keep_zero else [x for x in lines if x[2] > 0]


EXCH_SEEN = HOME / "vr6_exch_seen.json"


def seen_exch(symbol):
    return load(EXCH_SEEN, {}).get(symbol)


def need_usd(plan):
    return round(sum(pr * q for s, pr, q in order_lines(plan) if s == "buy"), 2)


def run_checks(plan, st, now):
    p, acc, k = plan["parsed"], plan.get("account") or {}, int(plan["mult"])
    out = []
    add = lambda ok, msg: out.append({"ok": bool(ok), "msg": msg})
    add(plan.get("reads_agree"), "AI 두 번 판독 결과 일치" if plan.get("reads_agree")
        else "AI 두 번 판독 결과가 다르거나 확인 판독 실패 → 숫자 꼭 확인")
    out += vr_math(p)
    if not p["buys"] and not p["sells"]:
        add(False, "주문 줄을 하나도 못 읽음")
    s, e = plan.get("start"), plan.get("end")
    if not s:
        add(False, "표의 기간(시작~끝 날짜)을 못 읽음")
    else:
        ref = _d(plan["cycle"])
        gap = abs((_d(s) - ref).days)
        add(gap <= 7, f"표 기간 {s}~{e} · 진행일 {plan['cycle']} 과 {gap}일 차이" + ("" if gap <= 7 else " → 다른 회차 표?"))
        span = (_d(e) - _d(s)).days
        add(4 <= span <= 16, f"기간 길이 {span}일 (보통 11일: 월~다음 주 금)")
        add(bool(plan.get("order_start")), f"첫 발주일 {plan.get('order_start')} (미국 날짜)" if plan.get("order_start")
            else "표 기간 안에 예약 마감 전인 날이 남지 않음")
    add(1 <= k <= 50, f"배수 ×{k}")
    cur = acc.get("price")
    if cur:
        bad = [r["price"] for r in p["buys"] if not 0.5 * cur <= r["price"] <= 1.5 * cur] + \
              [r["price"] for r in p["sells"] if not 0.5 * cur <= r["price"] <= 2.0 * cur]
        add(not bad, f"가격 범위 정상 (현재가 {cur:g} 기준)" if not bad else f"현재가 {cur:g} 와 너무 먼 가격: {bad[:5]}")
    else:
        add(False, "메리츠 시세 확인 실패 → 가격 대조 못 함")
    sell_q = sum(q for sd, pr, q in raw_lines(plan) if sd == "sell")
    if sell_q:                                   # 잔고 차이로는 막지 않음 (사용자 결정 2026-10-29)
        sa = acc.get("sellable")
        if sa is None:
            add(True, "⚠️ 잔고 조회 실패 → 매도는 표 수량 그대로 (증권사가 거절하면 그 줄만 실패)")
        elif sell_q <= sa:
            add(True, f"매도 합계 {sell_q}주 ≤ 매도가능 {sa}주")
        else:
            add(True, f"⚠️ 매도가능 {sa}주 < 표 매도 {sell_q}주 → 가장 높은 매도가부터 {sell_q - sa}주 줄여 주문")
    if not (st.get("exch_id") or acc.get("exch_id") or seen_exch(st["symbol"])):
        add(False, "거래소 번호를 모름 (VR6 계좌 잔고에 TQQQ 가 없으면 vr6.json 에 exch_id 설정 필요)")
    if not KEYS_VR6.exists():
        add(False, "VR6 계좌 키 없음 (/etc/bot-office/meritz_vr6.json) → 주문 못 함")
    return out, all(x["ok"] for x in out)


def info_lines(plan):
    acc, p, k = plan.get("account") or {}, plan["parsed"], int(plan["mult"])
    need = need_usd(plan)
    L = ["\n💵 <b>매수 자금 (VR6 계좌)</b>", f"▫️ 매수 줄이 모두 체결될 때 필요한 달러: <b>${need:,.2f}</b>"]
    cash, est = acc.get("usd_cash"), acc.get("usd_est")
    L.append("▫️ 보유 달러(예수금): " + (f"${cash:,.2f}" if cash is not None else "조회 불가"))
    if est is not None:
        L.append(f"▫️ 외화 추정 예수금(미결제 포함): ${est:,.2f}")
    if cash is not None:
        gap = round(need - cash, 2)
        L.append(f"▫️ <b>부족: ${gap:,.2f} → 환전 필요</b>" if gap > 0 else f"▫️ 부족 없음 (여유 ${-gap:,.2f})")
    L.append("▫️ 부족하면 아래 [💱 환전 금액 확인] 버튼이나 <code>/vr6환전</code> 으로 환전할 수 있어요 (확인 후 실행 · 자동환전 없음).")
    base = p.get("buy_base_qty") or p.get("sell_base_qty")
    if base:
        L.append("\n📦 <b>보유 수량 비교</b>")
        exp = base * k
        if acc.get("holding") is not None:
            diff = acc["holding"] - exp
            L.append(f"▫️ 표 {base}주 × {k} = {exp}주 / VR6 계좌 {acc['holding']}주" + (" (일치)" if not diff else f" (차이 {diff:+d}주)"))
        else:
            L.append(f"▫️ 표 {base}주 × {k} = {exp}주 / VR6 계좌 조회 불가")
    cur = acc.get("price")
    if cur and any(r["price"] >= cur for r in p["buys"]):
        L.append(f"▫️ 참고: 현재가({cur:g})보다 높은 매수점이 있어 첫날 장 시작에 바로 체결될 수 있어요.")
    if acc.get("errors"):
        L.append("▫️ 조회 오류: " + html.escape(" / ".join(acc["errors"]))[:300])
    return L


def plan_text(plan, st, head="🅥 <b>VR6 주문표</b>"):
    p, k = plan["parsed"], int(plan["mult"])
    L = [f"{head} · {html.escape(p.get('title') or '')} · {st['symbol']} · 배수 ×{k}",
         f"기간 {plan.get('start') or '?'} ~ {plan.get('end') or '?'} · 첫 발주일 {plan.get('order_start') or '-'} (미국)",
         "주문 방식: 지정가 · 기간잔량 · 장개시 발주 (줄마다 " + f"{k}주)"]
    if p["buys"]:
        L.append(f"\n🔴 <b>매수 {len(p['buys'])}줄</b> (최소값 {p.get('min_value')})")
        L += [f"  {r['price']:g} × {k}주 → 보유 {r['qty'] * k}주" for r in p["buys"]]
    if p["sells"]:
        L.append(f"\n🔵 <b>매도 {len(p['sells'])}줄</b> (최대값 {p.get('max_value')})")
        capped = [q for sd, _, q in order_lines(plan, keep_zero=True) if sd == "sell"]
        for r, q in zip(p["sells"], capped):
            L.append(f"  {r['price']:g} × {q}주 → 보유 {r['qty'] * k}주" if q == k else
                     f"  {r['price']:g} × <b>{q}주</b> (표 {k}주 → 매도가능 부족으로 줄임)")
    L += info_lines(plan)
    bad = [x for x in plan["checks"] if not x["ok"]]
    L.append("\n🛡 <b>안전점검</b> " + ("모두 통과" if not bad else f"{len(bad)}건 미통과"))
    L += [("  ✅ " if x["ok"] else "  ❌ ") + html.escape(x["msg"]) for x in plan["checks"]]
    if plan["status"] == "pending" and plan.get("order_start"):
        _, auto, cut = deadlines(plan, st)
        if not st["auto_order"]:
            L.append(f"\n⏰ 자동주문 꺼짐 · 버튼으로 결정해 주세요 (마감 {cut:%m-%d %H:%M} KST)")
        elif plan["auto_ok"]:
            L.append(f"\n⏰ 버튼을 안 누르면 <b>{auto:%m-%d %H:%M} KST</b> 에 자동주문해요.")
        else:
            L.append("\n⛔ 점검 미통과라 자동주문 안 해요. 숫자를 확인하고 직접 [✅ 주문] 하거나 앱에서 주문해 주세요.")
    return "\n".join(L)


def usd_gap(plan, acc=None):
    """매수 필요 달러 - 보유 달러(예수금). 조회 못 하면 None"""
    cash = (acc if acc is not None else plan.get("account") or {}).get("usd_cash")
    return None if cash is None else round(need_usd(plan) - cash, 2)


def fx_row(plan, acc=None):
    gap = usd_gap(plan, acc)
    if gap is None or gap <= 0:
        return []
    return [[{"text": f"💱 환전 금액 확인 (부족 ${gap:,.2f})", "callback_data": f"vm:fc:{plan['cycle']}:{plan['ver']}"}]]


def plan_rows(plan, decide=True):
    key = f"{plan['cycle']}:{plan['ver']}"
    rows = [[{"text": "✅ 주문", "callback_data": f"vm:ok:{key}"}, {"text": "❌ 이번엔 안 함", "callback_data": f"vm:no:{key}"}]] if decide else []
    return rows + fx_row(plan)


def build_plan(tg, cycle, now=None):
    """받은 이미지 중 주문표를 찾아 판독·점검하고 5번 봇에 알림. 주문은 tick 이 낸다"""
    now = now or datetime.now(KST)
    st0 = _fill(load(STATE, {}))
    names = [n for n in st0["cycles"].get(cycle, {}).get("images", []) if (VDIR / n).exists()]
    old = st0["plans"].get(cycle)
    if old and old["status"] in ("submitting", "submitted", "partial", "retry", "retry_warn", "approved"):
        tg.send("⚠️ <b>VR6 이번 회차는 이미 주문을 진행했어요</b> · 새로 판독하지 않아요. 상태: /vr6주문")
        return None
    found = None
    for n in reversed(names):                 # 주문표는 보통 글의 마지막 이미지 → 뒤에서부터
        data = (VDIR / n).read_bytes()
        first, ai1 = read_plan(data)
        replay("vr6_image_judged", "ok", "plan" if first["is_plan"] else "not_plan", cycle=cycle, ai=ai1)
        if first["is_plan"] and (first["buys"] or first["sells"]):
            found = (n, data, first, ai1); break
    if not found:
        tg.send(f"❓ <b>VR6 주문표를 못 찾았어요</b> (이미지 {len(names)}장 확인)\n주문하지 않아요. 받은 표: /vr6표 · 다시: /vr6재판독")
        replay("vr6_plan_found", "skipped", "no_plan_image", event_type="user_visible", cycle=cycle)
        return None
    n, data, first, ai1 = found
    try:
        second, ai2 = read_plan(data, avoid=ai1)
    except Exception as e:
        print("VR6 확인 판독 실패:", e, flush=True)
        second, ai2 = None, ""
    agree = bool(second) and core(first) == core(second)
    with locked() as st:
        start, end = table_dates(first, _d(cycle))
        o_start = first_order_day(start, end, now, st) if start else None
        plan = {"cycle": cycle, "img": n, "parsed": first, "reads_agree": agree, "ai": [ai1, ai2],
                "mult": int(st["multiplier"]), "start": start.isoformat() if start else "",
                "end": end.isoformat() if end else "", "order_start": o_start.isoformat() if o_start else "",
                "status": "pending", "orders": [], "ver": int((old or {}).get("ver", 0)) + 1, "alarm_sent": False,
                "received": now.isoformat(timespec="minutes")}
    plan["account"] = account(st)
    head = "🅥 <b>VR6 주문표 도착</b>" if not old else "🅥 <b>VR6 주문표 (다시 판독)</b>"
    with locked() as st:
        plan["checks"], plan["auto_ok"] = run_checks(plan, st, now)
        if old and old.get("msg_id"):
            tg.clear_buttons(old["msg_id"])
        hold = now < notice_time(now, st)
        if hold:
            plan["notice_pending"], plan["notice_head"] = True, head
        st["plans"][cycle] = plan
        for k in sorted(st["plans"])[:-6]:
            st["plans"].pop(k, None)
    if hold:
        replay("vr6_plan_ready", "skipped", "held_until_notice_time", event_type="user_visible", cycle=cycle,
               reads_agree=agree, failed_checks=len([x for x in plan["checks"] if not x["ok"]]))
        print(f"VR6 주문표 준비 완료 → {_fill(load(STATE, {}))['notice_kst']} KST 에 알림", flush=True)
        return plan
    send_plan_notice(tg, cycle, head)
    return _fill(load(STATE, {}))["plans"].get(cycle)


def notice_time(now, st):
    h, m = _hm(st["notice_kst"])
    return now.replace(hour=h, minute=m, second=0, microsecond=0)


def send_plan_notice(tg, cycle, head, refresh=False):
    """주문표 사진 + 내용 + 버튼. refresh=True 면 (09:00 보류 뒤) 계좌·점검을 다시 보고 보냄"""
    st = _fill(load(STATE, {}))
    plan = st["plans"].get(cycle)
    if not plan:
        return
    if refresh:
        acc = account(st)
        with locked() as st:
            pl = st["plans"][cycle]
            pl["account"] = acc
            pl["checks"], pl["auto_ok"] = run_checks(pl, st, datetime.now(KST))
            plan = dict(pl)
    tg.photo(VDIR / plan["img"], f"🅥 VR6 주문표 · {html.escape(plan['parsed'].get('title') or cycle)}")
    r = tg.send(plan_text(plan, st, head), plan_rows(plan, decide=plan["status"] == "pending" and bool(plan["order_start"])) or None)
    with locked() as st:
        if cycle in st["plans"]:
            st["plans"][cycle]["msg_id"] = (r or {}).get("message_id")
            st["plans"][cycle].pop("notice_pending", None)
    replay("vr6_plan_ready", "ok" if plan["auto_ok"] else "partial", "" if plan["auto_ok"] else "checks_failed",
           event_type="user_visible", cycle=cycle, reads_agree=plan.get("reads_agree"),
           buy_rows=len(plan["parsed"]["buys"]), sell_rows=len(plan["parsed"]["sells"]), mult=plan["mult"],
           failed_checks=len([x for x in plan["checks"] if not x["ok"]]), message_id=(r or {}).get("message_id"))


# ---------------------------------------------------------- 주문 접수 (tick 에서만 호출)
def submit(tg, cycle, confirm_warn=False):
    from meritz_client import WarnNeeded
    st = _fill(load(STATE, {}))
    plan = st["plans"][cycle]
    m = client()
    if not plan["orders"]:          # 처음 접수에만 매도가능 다시 조회 (재시도 때는 수량 고정 → 중복 방지)
        acc0 = account(st, m)
        if acc0.get("sellable") is not None:
            with locked() as st2:
                st2["plans"][cycle]["account"] = acc0
                plan = st2["plans"][cycle]
    exch = st.get("exch_id") or (plan.get("account") or {}).get("exch_id") or seen_exch(st["symbol"])
    if not exch:
        exch = account(st, m).get("exch_id")
    if not exch:
        raise RuntimeError("거래소 번호(exch_id)를 몰라 주문 못 함")
    sd, ed = plan["order_start"].replace("-", ""), plan["end"].replace("-", "")
    done = {(o["side"], o["price"], o["i"]) for o in plan["orders"] if o.get("no")}
    orders = [o for o in plan["orders"] if o.get("no")]
    for i, (side, price, qty) in enumerate(order_lines(plan, keep_zero=True)):
        if qty <= 0 or (side, price, i) in done:
            continue
        o = {"side": side, "price": price, "qty": qty, "i": i, "at": datetime.now(KST).isoformat(timespec="seconds")}
        try:
            r = m.reserve(side, st["symbol"], exch, qty, price, sd, aspr="1", confirm_warn=confirm_warn,
                          hour_code="0", rsev_cls="2", date_end=ed)
            o["no"] = r["no"]
        except WarnNeeded as e:
            o["warn"] = str(e)
        except Exception as e:
            o["err"] = str(e)
        replay("vr6_reserve", "ok" if o.get("no") else "failed", "warn" if o.get("warn") else ("" if o.get("no") else "error"),
               event_type="external_call", cycle=cycle, side=side, line=i, broker_no=o.get("no"))
        orders.append(o)
        time.sleep(0.3)
    n_total = len(order_lines(plan))
    ok = len([o for o in orders if o.get("no")]) == n_total
    acc = account(st, m)
    with locked() as st2:
        pl = st2["plans"][cycle]
        pl["orders"], pl["status"] = sorted(orders, key=lambda o: o["i"]), "submitted" if ok else "partial"
        pl["account_after"] = acc
        plan = pl
    L = [f"{'✅' if ok else '⚠️'} <b>VR6 메리츠 예약주문 {'완료' if ok else '일부 실패'}</b> · {cycle} 회차 · "
         f"{'자동' if plan.get('approved_by') == 'auto' else '승인'}",
         f"기간잔량 지정가 · 장개시 발주 · {plan['order_start']} ~ {plan['end']} (미국)"]
    for o in plan["orders"]:
        tag = f"접수 #{o['no']}" if o.get("no") else (f"⚠️ 증권사 경고: {o['warn']}" if o.get("warn") else f"❌ {o.get('err')}")
        L.append(f"{'🔴 매수' if o['side'] == 'buy' else '🔵 매도'} {o['price']:g} × {o['qty']} → {html.escape(str(tag))[:160]}")
    rows = None
    key = f"{cycle}:{plan['ver']}"
    if any(o.get("warn") for o in plan["orders"]):
        L.append("\n증권사 '주문 착오 방지' 경고예요. 숫자가 맞으면 아래 버튼으로 경고 확인 후 다시 넣어요.")
        rows = [[{"text": "⚠️ 경고 확인하고 주문", "callback_data": f"vm:wy:{key}"}]]
    elif not ok:
        rows = [[{"text": "🔁 실패한 것만 다시", "callback_data": f"vm:re:{key}"}]]
    plan = dict(plan, account=acc)
    L += info_lines(plan)
    r = tg.send("\n".join(L), rows)
    replay("vr6_orders_result", "ok" if ok else "partial", event_type="user_visible", cycle=cycle,
           accepted=len([o for o in orders if o.get("no")]), total=n_total, message_id=(r or {}).get("message_id"))


# ---------------------------------------------------------- 시간표 처리 (fanding_trade.loop 이 20초마다 부름)
def tick(tg, now=None):
    now = now or datetime.now(KST)
    with locked() as st:
        due = _d(st["next_due"])
        late = (today_kst(now) > due) or (today_kst(now) == due and now.hour >= 18)
        send_late = late and st["alerted"] != st["next_due"]
        if send_late:
            st["alerted"] = st["next_due"]
        pc = st.get("pc") or {}
    if send_late:
        seen = datetime.fromtimestamp(pc["at"], KST).strftime("%m-%d %H:%M") if pc.get("at") else "기록 없음"
        tg.send(f"⚠️ <b>VR6 진행일({due.isoformat()}, {_wd(due)})이 지났는데 아직 표를 못 받았어요</b>\n"
                f"PC가 마지막으로 서버에 물어본 때: {seen}\nWindows PC가 켜져 있는지, 팬딩 로그인이 풀리지 않았는지 확인하고 "
                "PC에서 <code>py fanding_vr6.py run</code> 을 실행하세요. 상태는 /vr6진단")
    todo, notices, fx_check = [], [], []
    with locked() as st:
        for cycle, pl in st["plans"].items():
            if pl.get("notice_pending") and now >= notice_time(now, st):
                notices.append((cycle, pl.get("notice_head") or "🅥 <b>VR6 주문표 도착</b>"))
                pl["notice_pending"] = False
            # 밤 마감 30분 전: 이미 승인·접수된 회차는 달러가 모자랄 때만 알림 (결정 대기는 아래에서 따로)
            if (pl["status"] in ("approved", "submitting", "submitted", "partial", "retry", "retry_warn")
                    and pl.get("order_start") and not pl.get("alarm_sent")):
                alarm, _, cut = deadlines(pl, st)
                if alarm <= now < cut:
                    pl["alarm_sent"] = True
                    fx_check.append(cycle)
            if pl["status"] == "submitting" and time.time() - pl.get("submit_t", 0) > 600:
                pl["status"] = "partial"
                tg.send(f"⚠️ VR6 {cycle} 회차 주문 접수 도중 프로그램이 다시 켜졌어요. 메리츠 앱에서 접수 여부를 확인해 주세요.",
                        [[{"text": "🔁 빠진 것만 다시", "callback_data": f"vm:re:{cycle}:{pl['ver']}"}]])
            if pl["status"] not in ("pending", "approved", "retry", "retry_warn") or not pl.get("order_start"):
                continue
            alarm, auto, cut = deadlines(pl, st)
            if now >= cut:                       # 첫 발주일 마감이 지남 → 기간 안의 다음 평일로 미룸
                nxt = first_order_day(_d(pl["order_start"]) + timedelta(days=1), _d(pl["end"]), now, st)
                tg.clear_buttons(pl.get("msg_id"))
                if not nxt:
                    pl["status"] = "expired"
                    tg.send(f"ℹ️ VR6 {cycle} 회차: 표 기간 안에 예약 마감 전인 날이 남지 않아 이번 주문은 넘어갑니다.")
                    continue
                pl["order_start"], pl["alarm_sent"] = nxt.isoformat(), False
                alarm, auto, cut = deadlines(pl, st)
                r = tg.send(f"ℹ️ VR6 {cycle} 회차: 마감이 지나 첫 발주일을 <b>{nxt.isoformat()}</b>(미국)로 미뤘어요. "
                            f"새 마감 {cut:%m-%d %H:%M} KST", plan_rows(pl) if pl["status"] == "pending" else None)
                if pl["status"] == "pending":
                    pl["msg_id"] = (r or {}).get("message_id")
            if pl["status"] == "pending" and st["auto_order"]:
                if now >= auto:
                    tg.clear_buttons(pl.get("msg_id"))
                    if pl["auto_ok"]:
                        pl["status"], pl["approved_by"] = "approved", "auto"
                        tg.send(f"🤖 <b>버튼이 안 눌려 VR6 자동주문 진행</b> · {cycle} 회차 (점검 모두 통과)")
                    else:
                        pl["status"] = "skipped"
                        bad = "\n".join("  · " + html.escape(x["msg"]) for x in pl["checks"] if not x["ok"])
                        tg.send(f"⛔ <b>VR6 자동주문 안 함</b> · {cycle} 회차\n안전점검을 통과 못 했어요:\n{bad}\n"
                                "필요하면 메리츠 앱에서 직접 주문해 주세요.")
                    replay("vr6_auto_decision", "ok" if pl["auto_ok"] else "skipped",
                           "" if pl["auto_ok"] else "checks_failed", cycle=cycle)
                    continue
                if now >= alarm and not pl.get("alarm_sent"):
                    pl["alarm_sent"] = True
                    tg.send(f"⏰ <b>VR6 주문 확인 마감 30분 전</b> · {cycle} 회차\n{auto:%H:%M} 에 "
                            + ("자동주문합니다." if pl["auto_ok"] else "점검 미통과라 자동주문 안 합니다.")
                            + f"\n매수 필요 달러 ${need_usd(pl):,.2f} — 부족하면 아래 버튼으로 환전할 수 있어요.", plan_rows(pl))
                    continue
            if pl["status"] == "pending" and not st["auto_order"] and now >= alarm and not pl.get("alarm_sent"):
                pl["alarm_sent"] = True
                tg.send(f"⏰ <b>VR6 결정 대기 · 마감 30분 전</b> · {cycle} 회차\n자동주문이 꺼져 있어요. 주문하려면 아래 [✅ 주문]을 "
                        f"눌러 주세요 (마감 {cut:%H:%M} KST, 지나면 다음 거래일로 미뤄요).", plan_rows(pl))
                continue
            if pl["status"] in ("approved", "retry", "retry_warn") and (now.hour, now.minute) >= _hm(st["submit_kst"]):
                todo.append((cycle, pl["status"] == "retry_warn"))
                pl["status"], pl["submit_t"] = "submitting", time.time()
    for cycle, head in notices:
        try:
            send_plan_notice(tg, cycle, head, refresh=True)
        except Exception as e:
            print("VR6 09:00 알림 오류:", type(e).__name__, e, flush=True)
    for cycle in fx_check:
        try:
            st = _fill(load(STATE, {}))
            pl = st["plans"][cycle]
            acc = account(st)
            gap = usd_gap(pl, acc)
            if gap is not None and gap > 0:
                tg.send(f"💱 <b>VR6 달러 부족</b> · {cycle} 회차\n매수 줄이 모두 체결되려면 ${need_usd(pl):,.2f} 필요 · "
                        f"보유 달러 ${acc['usd_cash']:,.2f} → <b>${gap:,.2f} 부족</b>\n"
                        "예약은 걸려 있지만 달러가 없으면 매수가 거절될 수 있어요.", fx_row(pl, acc))
            replay("vr6_night_fx_check", "ok" if gap is not None else "failed",
                   "short" if (gap or 0) > 0 else ("enough" if gap is not None else "account_error"),
                   event_type="user_visible", cycle=cycle)
        except Exception as e:
            print("VR6 달러 확인 오류:", type(e).__name__, e, flush=True)
    for cycle, warn in todo:
        try:
            submit(tg, cycle, confirm_warn=warn)
        except Exception as e:
            with locked() as st:
                pl = st["plans"][cycle]; pl["status"] = "partial"; ver = pl["ver"]
            replay("vr6_submit", "failed", type(e).__name__, event_type="external_call", cycle=cycle)
            tg.send(f"🚨 <b>VR6 주문 접수 오류</b> · {cycle}\n{html.escape(str(e))[:400]}",
                    [[{"text": "🔁 다시 시도", "callback_data": f"vm:re:{cycle}:{ver}"}]])


# ---------------------------------------------------------- 환전 (사용자 버튼에서만 실행 · 자동환전 없음)
FX_TTL_MINUTES = 10


def _fx_amount(s):
    from decimal import Decimal, InvalidOperation
    try:
        v = Decimal(str(s).replace("$", "").replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return v if v.is_finite() and v > 0 else None


def fx_show(tg, amount=None, plan=None):
    """환전 확인 화면 (실행 안 함). 기본 금액 = 이번 회차 매수 필요 달러 - 보유 달러(예수금)"""
    from decimal import Decimal
    st = _fill(load(STATE, {}))
    plan = plan or _latest_plan(st)
    if not KEYS_VR6.exists():
        tg.send("💱 VR6 계좌 키가 없어 환전할 수 없어요 (/etc/bot-office/meritz_vr6.json)."); return
    try:
        m = client()
    except Exception as e:
        tg.send(f"💱 VR6 계좌 연결 오류 ({html.escape(type(e).__name__)})"); return
    acc = account(st, m)
    need = Decimal(str(need_usd(plan))) if plan else None
    cash = Decimal(str(acc["usd_cash"])) if acc.get("usd_cash") is not None else None
    gap = max(Decimal(0), need - cash) if (need is not None and cash is not None) else None
    if amount is None:
        amount = gap
    head = ["💱 <b>VR6 환전 확인</b> — 아직 실행하지 않았어요",
            "▫️ 보유 달러(예수금): " + (f"${cash:,.2f}" if cash is not None else "조회 불가"),
            "▫️ 이번 회차 매수 필요 달러: " + (f"${need:,.2f} ({plan['cycle']} 회차)" if need is not None else "주문표 없음"),
            "▫️ 부족: " + (f"${gap:,.2f}" if gap is not None else "계산 보류")]
    if amount is None or amount <= 0:
        tg.send("\n".join(head + ["환전이 필요 없어요. 금액을 직접 정하려면 <code>/vr6환전 300</code> 처럼 적어 주세요."])); return
    amount = amount.quantize(Decimal("0.01"))
    try:
        info = m.fx_applied_rate()
        rate, rtime = Decimal(str(info["rate"])), str(info.get("exrt_stnd_time") or "")
    except Exception as e:
        tg.send(f"💱 적용환율을 못 가져왔어요 ({html.escape(type(e).__name__)}). 환전 가능 시간(평일 낮)인지 확인하고 다시 해 주세요."); return
    try:
        krw = Decimal(str(m.krw_cash()))
    except Exception:
        krw = None
    krw_need = amount * rate
    with locked() as st2:
        st2["fx_pending"] = {"amount": f"{amount:.2f}", "rate": str(rate), "time": rtime,
                             "created_at": datetime.now(KST).isoformat(), "cycle": (plan or {}).get("cycle")}
    L = head[:1] + [f"▫️ 환전할 달러: <b>${amount:,.2f}</b>" + (" (부족액보다 많아요)" if gap is not None and amount > gap else ""),
                    f"▫️ 적용환율: {rate:,.4f} (기준 {html.escape(rtime)})",
                    f"▫️ 필요 원화(추정): 약 {krw_need:,.0f}원 (수수료 별도 · 실제 금액은 실행 결과 기준)",
                    "▫️ VR6 계좌 원화 예수금: " + (f"{krw:,.0f}원" if krw is not None else "조회 불가")] + head[1:]
    if krw is not None and krw < krw_need:
        L.append("⚠️ 원화가 부족해 실행 버튼을 안 띄웠어요. 원화를 먼저 넣거나 <code>/vr6환전 금액</code> 으로 줄여 주세요.")
        tg.send("\n".join(L), [[{"text": "❌ 취소", "callback_data": "vm:fn"}]]); return
    L.append(f"실행 버튼은 {FX_TTL_MINUTES}분 동안 유효해요. 누르면 그때 환율을 다시 보고, 1% 넘게 바뀌었으면 실행하지 않아요.")
    tg.send("\n".join(L), [[{"text": "✅ 환전 실행", "callback_data": f"vm:fx:{amount:.2f}"},
                            {"text": "❌ 취소", "callback_data": "vm:fn"}]])
    replay("vr6_fx_quote", "ok", event_type="user_visible", cycle=(plan or {}).get("cycle"))


def fx_exec(tg, cb, amount_str):
    from decimal import Decimal, InvalidOperation
    msg_id = (cb.get("message") or {}).get("message_id")
    tg.answer(cb.get("id"), "환전을 확인할게요")
    tg.clear_buttons(msg_id)
    with locked() as st:
        pend = st.pop("fx_pending", None)
    try:
        amount = Decimal(amount_str)
    except (InvalidOperation, ValueError):
        tg.send("환전 금액이 이상해요. 다시 /vr6환전 으로 열어 주세요."); return
    if not pend or pend.get("amount") != f"{amount:.2f}":
        tg.send("환전 확인 정보가 없거나 금액이 달라요. /vr6환전 으로 다시 열어 주세요. (실행 안 함)"); return
    try:
        age = (datetime.now(KST) - datetime.fromisoformat(pend["created_at"])).total_seconds() / 60
    except (KeyError, ValueError):
        age = 999
    if age > FX_TTL_MINUTES:
        tg.send(f"환전 확인 후 {FX_TTL_MINUTES}분이 지났어요. 환율이 바뀔 수 있어 실행하지 않았어요. /vr6환전 으로 다시 열어 주세요."); return
    try:
        m = client()
        info = m.fx_applied_rate()
        new_rate, new_time = Decimal(str(info["rate"])), str(info.get("exrt_stnd_time") or "")
        old_rate = Decimal(pend["rate"])
    except Exception as e:
        tg.send(f"환전 중단: 실행 직전 환율 조회 실패 ({html.escape(type(e).__name__)}). 돈은 움직이지 않았어요."); return
    if old_rate and abs(new_rate - old_rate) / old_rate > Decimal("0.01"):
        tg.send(f"환율이 {old_rate:,.4f} → {new_rate:,.4f} 로 1% 넘게 바뀌어 실행하지 않았어요. 새 환율로 다시 보여 드릴게요.")
        return fx_show(tg, amount=amount)
    try:
        res = m.fx_exchange(f"{amount:.2f}", str(new_rate), new_time)      # 이 줄만 실제 돈이 움직인다
    except Exception as e:
        replay("vr6_fx_exchange", "failed", type(e).__name__, event_type="external_call")
        tg.send(f"⚠️ 환전 결과를 확인하지 못했어요 ({html.escape(type(e).__name__)}: {html.escape(str(e))[:150]}).\n"
                "환전이 됐을 수도 있어 다시 실행하지 않았어요. 메리츠 앱의 환전 내역을 먼저 확인해 주세요."); return
    replay("vr6_fx_exchange", "ok", event_type="external_call", broker_no=res.get("tr_srno"))
    acc = account(_fill(load(STATE, {})), m)
    L = ["✅ <b>VR6 환전 완료</b>", f"▫️ 환전한 달러: ${amount:,.2f}",
         f"▫️ 적용환율: {html.escape(str(res.get('aply_exrt') or new_rate))}"]
    if res.get("tr_amt") is not None:
        L.append(f"▫️ 차감된 원화: {html.escape(str(res['tr_amt']))}원")
    L.append("▫️ 환전 후 보유 달러(예수금): " + (f"${acc['usd_cash']:,.2f}" if acc.get("usd_cash") is not None else "조회 불가"))
    pl = _latest_plan(_fill(load(STATE, {})))
    if pl and acc.get("usd_cash") is not None:
        gap = usd_gap(pl, acc)
        L.append(f"▫️ {pl['cycle']} 회차 매수 필요 ${need_usd(pl):,.2f} → " + (f"아직 ${gap:,.2f} 부족" if gap > 0 else "충분해요"))
    tg.send("\n".join(L))


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


STATUS_NAMES = {"pending": "결정 대기", "approved": "주문 대기(곧 접수)", "submitting": "접수 중", "submitted": "접수 완료",
                "partial": "일부 실패", "retry": "다시 접수 대기", "retry_warn": "경고 확인 후 접수 대기",
                "cancelled": "이번엔 안 함", "skipped": "자동주문 안 함(점검 미통과)", "expired": "기간 지남"}


def _latest_plan(st):
    return st["plans"][max(st["plans"])] if st["plans"] else None


def summary_text(now=None):
    st = _fill(load(STATE, {}))
    nd = _d(st["next_due"])
    pl = _latest_plan(st)
    last = f"\n최근 주문표: {pl['cycle']} 회차 · {STATUS_NAMES.get(pl['status'], pl['status'])}" if pl else "\n최근 주문표: 없음"
    return (f"🅥 <b>VR6 메뉴</b> · {st['symbol']}\n배수 <b>×{st['multiplier']}</b> · 다음 진행 <b>{nd.isoformat()}({_wd(nd)})</b> "
            f"· 주기 {st['interval_days']}일 · 자동주문 {'켜짐' if st['auto_order'] else '꺼짐'}{last}")


def diagnosis(now=None):
    st = _fill(load(STATE, {}))
    pc = st.get("pc") or {}
    seen = datetime.fromtimestamp(pc["at"], KST).strftime("%Y-%m-%d %H:%M") if pc.get("at") else "아직 없음"
    cyc = st["cycles"].get(max(st["cycles"])) if st["cycles"] else None
    nd = _d(st["next_due"])
    acc = account(st)
    if acc["errors"]:
        conn = "❌ " + html.escape(" / ".join(acc["errors"]))[:300]
    else:
        conn = (f"✅ 연결됨 · TQQQ 보유 {acc.get('holding', '?')}주(매도가능 {acc.get('sellable', '?')}) · "
                f"현재가 {acc.get('price', '?')}" + (f" · 보유 달러 ${acc['usd_cash']:,.2f}" if acc.get("usd_cash") is not None else ""))
    pl = _latest_plan(st)
    return ("🩺 <b>VR6 진단</b>\n"
            f"• PC가 마지막으로 서버에 물어본 때: {seen}" + (f" (프로그램 v{html.escape(str(pc.get('version')))})" if pc.get("version") else "") + "\n"
            f"• 다음 진행일: {nd.isoformat()}({_wd(nd)}) · 지금 진행 요청: {'켜짐' if st['force'] else '꺼짐'}\n"
            f"• 마지막 완료: {st['last_done']} · 마지막으로 처리한 글 번호: {st['last_post_id']}\n"
            f"• 최근 받은 표: {len(cyc['images']) if cyc else 0}장\n"
            f"• 최근 주문표: " + (f"{pl['cycle']} · {STATUS_NAMES.get(pl['status'], pl['status'])}" if pl else "없음") + "\n"
            f"• VR6 계좌(조회만): {conn}\n"
            f"• 자동주문: {'켜짐' if st['auto_order'] else '꺼짐'} · 상태 파일: {'있음' if STATE.exists() else '아직 없음(기본값 사용)'}")


def _set_mult(tg, n):
    if not 1 <= n <= 50:
        tg.send("배수는 1~50 사이로 적어 주세요."); return
    with locked() as st:
        old = st["multiplier"]; st["multiplier"] = n
        pl = _latest_plan(st)
        pending = pl and pl["status"] == "pending"
    note = "\n이미 받은 주문표(결정 대기)는 그때 배수 그대로예요. 새 배수로 하려면 /vr6재판독" if pending else ""
    tg.send(f"📐 VR6 배수 ×{old} → <b>×{n}</b>\n다음에 받는 주문표부터 적용돼요.{note}", _mult_rows(n))


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
        names = [n for n in (cyc or {}).get("images", []) if (VDIR / n).exists()][:10]
        if not names:
            tg.send("아직 받은 VR6 표가 없어요."); return True
        for i, n in enumerate(names, 1):
            tg.photo(VDIR / n, f"🅥 <b>VR6 표</b> {i}/{len(names)} · {st['symbol']} · 현재 배수 ×{st['multiplier']}")
        return True
    if low in ("/vr6주문", "vr6주문"):
        st = _fill(load(STATE, {}))
        pl = _latest_plan(st)
        if not pl:
            tg.send("아직 VR6 주문표가 없어요. 표를 받으면 자동으로 판독해서 알려 드려요."); return True
        head = f"🅥 <b>VR6 주문표</b> [{STATUS_NAMES.get(pl['status'], pl['status'])}]"
        r = tg.send(plan_text(pl, st, head), plan_rows(pl, decide=pl["status"] == "pending" and bool(pl.get("order_start"))) or None)
        if pl["status"] == "pending" and (r or {}).get("message_id"):
            with locked() as st2:
                old = st2["plans"][pl["cycle"]].get("msg_id")
                st2["plans"][pl["cycle"]]["msg_id"] = r["message_id"]
            tg.clear_buttons(old)
        if pl.get("orders"):
            tg.send("📄 접수 기록\n" + "\n".join(
                f"{'🔴 매수' if o['side'] == 'buy' else '🔵 매도'} {o['price']:g} × {o['qty']} → "
                + (f"#{o['no']}" if o.get("no") else html.escape(str(o.get("warn") or o.get("err")))[:100]) for o in pl["orders"]))
        return True
    if low in ("/vr6재판독", "vr6재판독"):
        st = _fill(load(STATE, {}))
        if not st["cycles"]:
            tg.send("다시 판독할 VR6 표가 없어요."); return True
        cycle = max(st["cycles"])
        tg.send(f"🔎 VR6 {cycle} 회차 표를 다시 판독할게요 (배수 ×{st['multiplier']})…")
        try:
            build_plan(tg, cycle)
        except Exception as e:
            tg.send(f"🚨 VR6 재판독 오류: {html.escape(str(e))[:300]}")
        return True
    if low in ("/vr6자동켜기", "vr6자동켜기", "/vr6자동끄기", "vr6자동끄기"):
        on = "켜기" in low
        with locked() as st:
            st["auto_order"] = on
        tg.send(f"🤖 VR6 자동주문 <b>{'켜짐' if on else '꺼짐'}</b> — 버튼을 안 누르면 "
                + ("첫 발주일 마감 10분 전에 자동주문해요 (점검 모두 통과 시)." if on else "주문하지 않아요."))
        return True
    m = re.fullmatch(r"(?:/vr6환전|vr6환전)\s*([\d,.$]+)?", t, re.I)
    if m:
        amt = None
        if m.group(1):
            amt = _fx_amount(m.group(1))
            if amt is None:
                tg.send("금액을 <code>/vr6환전 300</code> 처럼 적어 주세요."); return True
        fx_show(tg, amount=amt)
        return True
    if low in ("/vr6진단", "vr6진단"):
        tg.send(diagnosis()); return True
    return False


def _plan_action(tg, cb, act, cycle, ver):
    with locked() as st:
        pl = st["plans"].get(cycle)
        if not pl or str(pl["ver"]) != ver:
            tg.answer(cb.get("id"), "예전 주문표 버튼이에요"); return
        msg_id = (cb.get("message") or {}).get("message_id")
        if act in ("ok", "no"):
            if pl["status"] != "pending":
                tg.answer(cb.get("id"), f"이미 처리됨: {STATUS_NAMES.get(pl['status'], pl['status'])}"); return
            pl["status"] = "approved" if act == "ok" else "cancelled"
            pl["approved_by"] = "button"
            msg = ("✅ VR6 주문 승인 — 곧(한국시간 09:00 이후) 메리츠에 접수해요." if act == "ok"
                   else "❌ VR6 이번 회차는 주문하지 않아요.")
        else:
            if pl["status"] != "partial":
                tg.answer(cb.get("id"), f"지금 상태: {STATUS_NAMES.get(pl['status'], pl['status'])}"); return
            pl["status"] = "retry_warn" if act == "wy" else "retry"
            msg = "🔁 실패한 줄만 다시 접수할게요." + (" (증권사 경고 확인)" if act == "wy" else "")
    tg.answer(cb.get("id"))
    tg.clear_buttons(msg_id)
    tg.send(msg)
    replay("vr6_button", "ok", act, event_type="user_event", cycle=cycle, message_id=msg_id)


def callback(tg, cb):
    data = cb.get("data", "")
    if not data.startswith("vm:"):
        return False
    parts = data.split(":")
    if parts[1] in ("ok", "no", "re", "wy") and len(parts) == 4:
        _plan_action(tg, cb, parts[1], parts[2], parts[3])
        return True
    if parts[1] == "fc" and len(parts) == 4:          # 주문표의 [💱 환전 금액 확인]
        tg.answer(cb.get("id"), "환전 금액을 계산할게요")
        st = _fill(load(STATE, {}))
        pl = st["plans"].get(parts[2])
        fx_show(tg, plan=pl if pl and str(pl["ver"]) == parts[3] else None)
        return True
    if parts[1] == "fx" and len(parts) == 3:          # [✅ 환전 실행]
        fx_exec(tg, cb, parts[2])
        return True
    if parts[1] == "fn":                               # [❌ 취소]
        with locked() as st:
            st.pop("fx_pending", None)
        tg.answer(cb.get("id"), "취소했어요")
        tg.clear_buttons((cb.get("message") or {}).get("message_id"))
        tg.send("❌ 환전 취소 · 실행하지 않았어요.")
        return True
    tg.answer(cb.get("id"))
    if parts[1] == "mt" and len(parts) > 2 and parts[2].isdigit():
        _set_mult(tg, int(parts[2]))
    elif parts[1] == "sh" and len(parts) > 2 and parts[2].lstrip("-").isdigit():
        _shift(tg, int(parts[2]))
    return True
