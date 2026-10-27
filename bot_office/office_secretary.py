#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/office_secretary.py   (OFFICE_SECRETARY_V3)
# 사무실 vNEXT (2026-10-28): ① 🖥 PC 상태 메뉴·PC 끊김/매직스플릿 알림 복구 (10/27 '메리츠 잔액 표시' 업로드 때 지워졌던 것)
#                         ② 🔗 사무실 주소(/주소 · /주소변경) — 임시 터널 주소가 바뀌면 자동 알림 + 한국 PC 변경 한 줄 (office_url.py)
# V4 (2026-10-26): 비서봇에서 팬딩 모듈 import 및 팬딩 콜백 제거. 팬딩은 전용 봇에서만 처리.
# V3 (2026-10-26): 하단 메인 메뉴·하위 메뉴 정리
# 텔레그램 "사무실 비서" 대화 담당 (항상 실행: bot-office-secretary.service)
#  - 평소 말투로 보낸 메시지 → 어느 봇인지 확인 → 사무실 수정 요청으로 접수 (고칠 파일은 사무실이 자동으로 찾음)
#  - 결재 요청 메시지의 [✅ 승인] [❌ 반려] [🔍 바뀐 코드 보기] 버튼 처리 (승인은 확인 한 번 더)
#  - "브리핑", "현황", "도움말"
#  안전: 등록된 대표님 채팅방(chat_id)에서 온 것만 처리. 코드 변경은 승인 후 기존 적용 담당(deploy_worker)이 진행.
# ==========================================================
import hashlib, html, json, os, re, subprocess, sys, tempfile, time, urllib.parse, urllib.request, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(os.environ.get("OFFICE_ROOT", "/"))
TELEGRAM_CFG = R / "etc/bot-office/telegram.json"
OFFICE_URL = R / "etc/bot-office/office_url"
STATE = R / "var/lib/bot-office/secretary.json"
REQUESTS = R / "var/lib/bot-office/market-manual/pipeline-requests.json"
APPROVALS = R / "var/lib/bot-office/market-manual/deploy-approvals.json"
DEPLOY_PUBLIC = R / "var/lib/bot-office-deploy-public"
PIPE_PUBLIC = R / "var/lib/bot-office-pipeline-public/state.json"
TELEGRAM_API = os.environ.get("OFFICE_TELEGRAM_API", "https://api.telegram.org")
SYSTEMCTL = os.environ.get("OFFICE_SYSTEMCTL", "systemctl")
BRIEFING = os.environ.get("OFFICE_BRIEFING", "/opt/bot-office/office_briefing.py")
KST, EST = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")

BOTS = [
    ("han4384tubot.service", "1번 한투 라오어", r"1\s*번|한투|라오어|한국투자|kis"),
    ("toss_sniper.service", "2번 토스 스나이퍼", r"2\s*번|스나이퍼|soxs|sniper"),
    ("toss_dca.service", "3번 토스 적립", r"3\s*번|토스\s*(주식|적립)|토스적립|dca"),
    ("bithumb_bot.service", "4번 빗썸 적립", r"4\s*번|빗썸|bithumb|코인|비트코인"),
]
NAME = {u: n for u, n, _ in BOTS}
HELP = ("🏢 <b>사무실 비서 사용법</b>\n"
        "▫️ <b>고칠 내용을 평소 말투로</b> 보내세요. 예) <i>4번 봇 잔액 부족 알림을 1시간에 한 번만 보내줘</i>\n"
        "   → 어느 봇인지 확인 → 사무실이 고칠 파일을 스스로 찾아 수정안 작성 → 결재 요청이 오면 버튼으로 승인\n"
        "▫️ <b>브리핑</b> : 지금 바로 비서 브리핑 받기\n"
        "▫️ <b>📊 조회 → 한국투자·토스·메리츠·빗썸</b> : 계좌별 USD/KRW 잔액 (/잔액은 전체)\n"
        "▫️ <b>/가격도움말</b> : 한국 제품 가격 등록·조회·변동 알림\n"
        "▫️ <b>📊 조회 → 🖥 PC 상태</b> : 한국 PC 연결·매직스플릿 실행 확인\n"
        "▫️ <b>📊 조회 → 🔗 사무실 주소</b> : 지금 주소·한국 PC 주소 바꾸는 한 줄 (/주소변경 으로 고정 도메인 이동)\n"
        "▫️ <b>현황</b> : 결재 대기·진행 중인 안건 보기\n"
        "▫️ 큰 기능 추가나 매매 로직 변경은 Claude에게 요청하면 시뮬레이션까지 해서 결재함에 올려 드립니다.")


def load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_like(p, data, mode=0o600):
    """원래 파일의 소유자를 그대로 유지하며 원자적으로 저장 (웹 서버가 계속 읽고 쓸 수 있게)"""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        st = p.stat(); uid, gid = st.st_uid, st.st_gid
    except FileNotFoundError:
        st = p.parent.stat(); uid, gid = st.st_uid, st.st_gid
    fd, tmp = tempfile.mkstemp(dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush(); os.fsync(f.fileno())
        try:
            os.chown(tmp, uid, gid)
        except PermissionError:
            pass
        os.chmod(tmp, mode)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class TG:
    def __init__(self):
        cfg = load(TELEGRAM_CFG, {})
        self.token, self.chat = cfg.get("token"), str(cfg.get("chat_id", ""))

    def call(self, method, payload, timeout=15):
        req = urllib.request.Request(f"{TELEGRAM_API}/bot{self.token}/{method}", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def send(self, text, rows=None, reply_to=None, keyboard=None):
        p = {"chat_id": self.chat, "text": text[:3900], "parse_mode": "HTML", "disable_web_page_preview": True}
        if rows:
            p["reply_markup"] = {"inline_keyboard": rows}
        elif keyboard:   # 채팅창 아래에 계속 떠 있는 버튼
            p["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True, "is_persistent": True}
        if reply_to:
            p["reply_to_message_id"] = reply_to
        try:
            return self.call("sendMessage", p).get("result", {})
        except Exception as e:
            print("send 실패:", e, flush=True); return {}

    def buttons(self, msg_id, rows):
        try:
            self.call("editMessageReplyMarkup", {"chat_id": self.chat, "message_id": msg_id,
                                                 "reply_markup": {"inline_keyboard": rows or []}})
        except Exception as e:
            print("버튼 변경 실패:", e, flush=True)

    def answer(self, cb_id, text=""):
        try:
            self.call("answerCallbackQuery", {"callback_query_id": cb_id, "text": text[:180]})
        except Exception:
            pass

    def document(self, name, data, caption=""):
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in (("chat_id", self.chat), ("caption", caption[:900])):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{name}"\r\n'
                     f'Content-Type: text/plain; charset=utf-8\r\n\r\n'.encode() + data + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        req = urllib.request.Request(f"{TELEGRAM_API}/bot{self.token}/sendDocument", data=b"".join(parts), method="POST",
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            urllib.request.urlopen(req, timeout=30).read()
        except Exception as e:
            print("파일 전송 실패:", e, flush=True)


def kick(unit):
    try:
        subprocess.run([SYSTEMCTL, "start", "--no-block", unit], capture_output=True, timeout=10)
    except Exception:
        pass


# ---------------------------------------------------------- 요청 접수
def detect(text):
    hits = [u for u, _, rx in BOTS if re.search(rx, text, re.I)]
    if len(hits) > 1 and "toss_dca.service" in hits and "toss_sniper.service" in hits:
        hits = [h for h in hits if h != "toss_dca.service"] if re.search(r"스나이퍼|soxs", text, re.I) else hits
    return hits[0] if len(hits) == 1 else None


def bot_rows(pid):
    return [[{"text": n, "callback_data": f"rb:{pid}:{i}"} for i, (_, n, _) in enumerate(BOTS[:2])],
            [{"text": n, "callback_data": f"rb:{pid}:{i + 2}"} for i, (_, n, _) in enumerate(BOTS[2:])],
            [{"text": "❌ 취소", "callback_data": f"cx:{pid}"}]]


def confirm_rows(pid):
    return [[{"text": "✅ 이대로 요청", "callback_data": f"rq:{pid}"}, {"text": "🔁 다른 봇", "callback_data": f"ch:{pid}"}],
            [{"text": "❌ 취소", "callback_data": f"cx:{pid}"}]]


def submit_request(unit, text):
    data = load(REQUESTS, {})
    items = data.get("items", []) if isinstance(data, dict) else []
    first = text.strip().splitlines()[0]
    title = (first[:60] + ("…" if len(first) > 60 else "")) if len(first) >= 2 else "텔레그램 요청"
    items.append({"id": uuid.uuid4().hex, "action": "request", "case": "", "at": datetime.now(timezone.utc).isoformat(),
                  "unit": unit, "file": "auto", "title": title, "body": text.strip()[:1500], "via": "telegram"})
    save_like(REQUESTS, {"items": items[-50:]})
    kick("bot-office-pipeline.service")
    return title


# ---------------------------------------------------------- 결재
def digest(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def find_package(key):
    if not re.fullmatch(r"[0-9a-f-]{8,36}", key or ""):
        return None
    p = DEPLOY_PUBLIC / f"{key}.json"
    if p.exists():
        return load(p, None)
    return None


def trading_warning(unit):
    k, e = datetime.now(KST), datetime.now(EST)
    hm_k, hm_e, wk_k, wk_e = k.strftime("%H:%M"), e.strftime("%H:%M"), k.weekday() < 5, e.weekday() < 5
    if unit == "toss_sniper.service" and wk_e and ("04:00" <= hm_e <= "09:30" or "15:55" <= hm_e <= "16:05"):
        return "⚠️ 지금은 스나이퍼 매매 시간(프리장/장마감 청산)입니다. 재시작 중 몇 초간 감시가 멈춥니다."
    if unit == "toss_dca.service" and ((wk_k and "11:00" <= hm_k <= "15:00") or (wk_e and "11:30" <= hm_e <= "15:50")):
        return "⚠️ 지금은 3번 봇 정기 매매 시간입니다."
    if unit == "bithumb_bot.service" and "19:00" <= hm_k <= "19:15":
        return "⚠️ 지금은 4번 빗썸 19:00 정기 매수 시간입니다."
    if unit == "han4384tubot.service" and wk_e and "04:00" <= hm_e <= "20:00":
        return "⚠️ 지금은 미국 주식 거래 시간대입니다. 1번 봇 주문 처리 중일 수 있습니다."
    return ""


def decide(dep, approve):
    m = find_package(dep)
    if not m:
        return False, "변경안을 찾지 못했습니다"
    records = load(APPROVALS, {})
    if dep in records:
        return False, f"이미 처리된 결재입니다 ({records[dep].get('decision')})"
    records[dep] = {"id": dep, "review_hash": digest(m), "decision": "승인" if approve else "반려",
                    "at": datetime.now(timezone.utc).isoformat(), "execution_authorized": bool(approve),
                    "execution": "처리 대기" if approve else "실행 제외", "via": "telegram"}
    save_like(APPROVALS, records)
    if approve:
        kick("bot-office-deploy.service")
    kick("bot-office-pipeline.service")
    return True, m


# ---------------------------------------------------------- 현황
def status_text():
    st = load(PIPE_PUBLIC, {})
    cases = st.get("cases") or []
    by = {}
    for c in cases:
        by.setdefault(c.get("stage"), []).append(c)
    lines = ["📋 <b>사무실 현황</b>"]
    for stg, label in (("awaiting_approval", "📝 결재 대기"), ("drafting", "✍️ 수정안 작성 중"), ("found", "🔎 접수·대기"),
                       ("applied", "⏫ 적용 완료·업로드 대기"), ("draft_failed", "⚠️ 수정안 실패"), ("verify_failed", "⚠️ 검증 탈락"),
                       ("apply_failed", "🚨 적용 실패"), ("push_failed", "🚨 업로드 실패")):
        for c in by.get(stg, [])[:5]:
            lines.append(f"{label} · {html.escape(c.get('bot', ''))} · {html.escape(str(c.get('title', ''))[:50])}")
    if len(lines) == 1:
        lines.append("▫️ 진행 중인 안건 없음 ✅")
    g = st.get("gemini") or {}
    lines.append(f"\n▫️ 오늘 Gemini 사용 {g.get('used', 0)}/{g.get('limit', '-')}회")
    return "\n".join(lines)


# ---------------------------------------------------------- 버튼 메뉴 (/start 로 하단 버튼이 뜬다)
# 버튼은 기존 글자 명령과 똑같이 처리된다. 글자를 꼭 입력해야 하는 기능(수정 내용·상품명·금액)은
# 버튼을 누르면 "다음 메시지로 보내 주세요" 안내가 뜨고, 그 다음 메시지를 알맞은 명령으로 처리한다(10분 안 · 취소는 아래 다른 버튼).
HOME = "🏠 메인 메뉴"
MAIN_LABELS = [["📊 조회", "💲 가격·비용"], ["✍️ 수정 요청", "❓ 도움말"]]
SUB_LABELS = {
    "view": [["🗞 브리핑", "📋 현황"], ["🖥 PC 상태", "🔗 사무실 주소"], ["🏦 한국투자", "🔷 토스"], ["🏛 메리츠", "🪙 빗썸"], ["🧾 전체 잔액", HOME]],
    "price": [["🔎 가격 목록", "🔄 가격 확인", "📊 가격 비교"], ["➕ 가격 등록", "🔀 웹·앱 비교 등록"],
              ["🤖 Gemini 사용량", "💵 Gemini 잔액 입력", "💲 Gemini 단가 입력"], [HOME]],
    "mq": [["🔧 " + n for _, n, _ in BOTS[:2]], ["🔧 " + n for _, n, _ in BOTS[2:]], ["🤔 내용으로 찾기", HOME]],
}
MENU_KB = [[{"text": t} for t in row] for row in MAIN_LABELS]
SUB_KB = {k: [[{"text": t} for t in row] for row in v] for k, v in SUB_LABELS.items()}
MENU_ALIAS = {"🗞 브리핑": "브리핑", "📋 현황": "현황", "❓ 도움말": "/help", "🖥 PC 상태": "/pc_status", "🔗 사무실 주소": "/주소"}
BAL_ACTIONS = {"🏦 한국투자": "kis", "🔷 토스": "toss", "🏛 메리츠": "meritz", "🪙 빗썸": "bithumb", "🧾 전체 잔액": "all"}
PRICE_ACTIONS = {"🔎 가격 목록": "ls", "🔄 가격 확인": "ck", "📊 가격 비교": "cp", "➕ 가격 등록": "rg", "🔀 웹·앱 비교 등록": "rc"}
GEMINI_ACTIONS = {"🤖 Gemini 사용량": "v", "💵 Gemini 잔액 입력": "b", "💲 Gemini 단가 입력": "r"}
MQ_LABELS = {"🔧 " + n: i for i, (_, n, _) in enumerate(BOTS)}
MENU_SPECIAL = tuple(["📊 조회", "💲 가격·비용", "✍️ 수정 요청", HOME, "🤔 내용으로 찾기"] + list(BAL_ACTIONS) + list(PRICE_ACTIONS) + list(GEMINI_ACTIONS) + list(MQ_LABELS))
CANCEL_WORDS = ("브리핑", "현황", "상태", "잔액", "도움말", "help", "?")
CANCEL_ROWS = [[{"text": "✖ 취소", "callback_data": "mn:x"}]]
AWAIT_PROMPTS = {
    "price_reg": "➕ <b>상품 등록</b>\n다음 메시지로 보내 주세요 (10분 안 · 취소는 아래 다른 버튼):\n<code>상품명 | 도메인(선택) | 연간·월간·일시불(선택)</code>\n예) <i>클로드 Pro 연간 구독</i>",
    "price_cmp": "🔀 <b>웹·앱 비교 등록</b>\n다음 메시지로 상품명을 보내 주세요 (10분 안 · 취소는 아래 다른 버튼). 예) <i>클로드 Pro 연간 구독</i>",
    "gem_bal": "💵 <b>Gemini 잔액 입력</b>\n다음 메시지로 보내 주세요 (10분 안 · 취소는 아래 다른 버튼):\n<code>달러금액 [화면집계일 YYYY-MM-DD]</code>\n예) <i>12.34</i>",
    "gem_rate": "💲 <b>Gemini 단가 입력</b>\n다음 메시지로 보내 주세요 (10분 안 · 취소는 아래 다른 버튼):\n<code>모델명 입력단가 출력단가</code>",
    "request": "✍️ <b>{who}</b> 수정 요청\n고칠 내용을 평소 말투로 다음 메시지에 적어 주세요 (10분 안 · 취소는 아래 다른 버튼).\n예) <i>잔액 부족 알림을 1시간에 한 번만 보내줘</i>"}


def menu_inline(spec, prefix):
    return [[{"text": t, "callback_data": f"{prefix}:{k}"} for t, k in row] for row in spec]


def mq_rows():
    return [[{"text": n, "callback_data": f"mq:{i}"} for i, (_, n, _) in enumerate(BOTS[:2])],
            [{"text": n, "callback_data": f"mq:{i + 2}"} for i, (_, n, _) in enumerate(BOTS[2:])],
            [{"text": "🤔 어느 봇인지 내용으로 찾기", "callback_data": "mq:a"}], CANCEL_ROWS[0]]


def run_price(tg, command):
    try:
        import price_watch
        price_watch.handle(tg, command)
    except Exception as e:
        tg.send("가격 추적을 불러오지 못했어요: " + html.escape(str(e)[:150]))


def price_list_rows():
    try:
        import price_watch
        with price_watch.state(write=False) as pdata:
            items = list(pdata["items"].items())
    except Exception:
        return None
    return [[{"text": f"{'⏸ 중지' if it.get('enabled') else '▶ 재개'} · {str(it.get('name', ''))[:16]}",
              "callback_data": f"pw:t:{ident}"}] for ident, it in items[:10]] or None


def price_action(tg, st, key):
    if key == "ls":
        run_price(tg, "/가격목록")
        rows = price_list_rows()
        if rows:
            tg.send("▫️ 눌러서 중지·재개", rows)
    elif key == "ck":
        run_price(tg, "/가격확인")
    elif key == "cp":
        run_price(tg, "/가격비교")
    elif key == "hp":
        run_price(tg, "/가격도움말")
    elif key in ("rg", "rc"):
        kind = "price_reg" if key == "rg" else "price_cmp"
        st["await"] = {"kind": kind, "at": time.time()}
        tg.send(AWAIT_PROMPTS[kind])


def gemini_action(tg, st, key):
    if key == "v":
        import gemini_usage
        gemini_usage.handle(tg, "/제미나이잔액")
    elif key in ("b", "r"):
        kind = "gem_bal" if key == "b" else "gem_rate"
        st["await"] = {"kind": kind, "at": time.time()}
        tg.send(AWAIT_PROMPTS[kind])


def request_target(tg, st, idx):
    """수정 요청: 대상 봇 선택(idx=None 이면 내용으로 찾기) 후 다음 메시지를 기다린다."""
    unit = None if idx is None else BOTS[idx][0]
    st["await"] = {"kind": "request", "unit": unit, "at": time.time()}
    tg.send(AWAIT_PROMPTS["request"].format(who=NAME[unit] if unit else "어느 봇인지 내용으로 찾는"))


def handle_await(tg, st, msg, aw, text):
    """버튼을 누른 뒤 보낸 다음 메시지를 알맞은 명령으로 처리"""
    kind = aw.get("kind")
    if kind == "price_reg":
        run_price(tg, "/가격등록 " + text)
    elif kind == "price_cmp":
        run_price(tg, "/가격비교등록 " + text)
    elif kind in ("gem_bal", "gem_rate"):
        import gemini_usage
        gemini_usage.handle(tg, ("/제미나이잔액 " if kind == "gem_bal" else "/제미나이단가 ") + text)
    elif kind == "request":
        if len(text) < 5:
            st["await"] = dict(aw, at=time.time())
            tg.send("고칠 내용을 조금 더 자세히 적어 주세요."); return
        pid = uuid.uuid4().hex[:10]
        unit = aw.get("unit") or detect(text)
        st.setdefault("pending", {})[pid] = {"text": text[:1500], "unit": unit, "at": time.time()}
        if unit:
            tg.send(f"📥 <b>수정 요청으로 접수할까요?</b>\n▫️ 대상: <b>{NAME[unit]}</b>\n▫️ 내용: {html.escape(text[:300])}\n\n"
                    "고칠 파일은 사무실이 스스로 찾아요.", confirm_rows(pid), reply_to=msg.get("message_id"))
        else:
            tg.send(f"📥 <b>어느 봇을 고칠까요?</b>\n▫️ 내용: {html.escape(text[:300])}", bot_rows(pid), reply_to=msg.get("message_id"))


# ---------------------------------------------------------- 메인 루프
def handle_message(tg, st, msg):
    text = (msg.get("text") or "").strip()
    if not text:
        return
    raw = text
    text = MENU_ALIAS.get(raw, raw)   # 하단 버튼 글자 → 같은 명령
    if text in ("/pc_status", "/PC상태", "PC 상태", "PC상태"):
        import pc_monitor
        tg.send(pc_monitor.status_text()); return
    if text in ("/주소", "주소", "/office_url", "/도메인안내", "도메인안내") or text.startswith("/주소변경"):
        import office_url
        if office_url.handle_text(tg, text):
            return
    aw = st.get("await")
    if aw and (time.time() - aw.get("at", 0) > 600 or raw.startswith("/") or raw in MENU_SPECIAL or raw in MENU_ALIAS
               or raw.lower() in CANCEL_WORDS):
        st.pop("await", None); aw = None
    if raw == HOME:
        tg.send("🏠 <b>메인 메뉴</b> · 아래 버튼을 눌러 주세요", keyboard=MENU_KB); return
    if raw == "📊 조회":
        tg.send("📊 <b>조회</b> · 아래 버튼을 눌러 주세요", keyboard=SUB_KB["view"]); return
    if raw == "💲 가격·비용":
        tg.send("💲 <b>가격·비용</b> · 아래 버튼을 눌러 주세요", keyboard=SUB_KB["price"]); return
    if raw == "✍️ 수정 요청":
        tg.send("✍️ <b>어느 봇을 고칠까요?</b> · 아래에서 골라 주세요", keyboard=SUB_KB["mq"]); return
    if raw in BAL_ACTIONS:
        tg.send(f"💰 {raw} 잔액을 조회하고 있어요…")
        subprocess.Popen([sys.executable, BRIEFING, "--balances", BAL_ACTIONS[raw]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return
    if raw in PRICE_ACTIONS:
        price_action(tg, st, PRICE_ACTIONS[raw]); return
    if raw in GEMINI_ACTIONS:
        gemini_action(tg, st, GEMINI_ACTIONS[raw]); return
    if raw in MQ_LABELS:
        request_target(tg, st, MQ_LABELS[raw]); return
    if raw == "🤔 내용으로 찾기":
        request_target(tg, st, None); return
    if aw:
        st.pop("await", None); handle_await(tg, st, msg, aw, text); return
    if text.split()[0] in ("/가격등록", "/가격목록", "/가격중지", "/가격재개", "/가격확인", "/가격도움말", "/가격비교등록", "/가격비교"):
        import price_watch
        if price_watch.handle(tg, text):
            return
    if text.split()[0] in ("/제미나이잔액", "/제미나이단가"):
        import gemini_usage
        if gemini_usage.handle(tg, text):
            return
    low = text.lower()
    if low in ("/start", "/help", "도움말", "help", "?"):
        tg.send(HELP + "\n▫️ 아래 버튼 메뉴로 모든 기능을 쓸 수 있어요.", keyboard=MENU_KB); return
    if low in ("/잔액", "잔액", "/balances"):
        tg.send("💰 계좌별 잔액을 조회하고 있어요…")
        subprocess.Popen([sys.executable, BRIEFING, "--balances"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return
    if low in ("/brief", "브리핑", "/briefing"):
        tg.send("🗞 브리핑을 준비하고 있어요…")
        subprocess.Popen([sys.executable, BRIEFING], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return
    if low in ("/status", "현황", "상태"):
        tg.send(status_text()); return
    if text.startswith("/"):
        tg.send("모르는 명령이에요. <b>도움말</b>을 보내 보세요."); return
    if len(text) < 5:
        tg.send("고칠 내용을 조금 더 자세히 적어 주세요. 예) <i>4번 봇 잔액 부족 알림을 1시간에 한 번만 보내줘</i>"); return
    pid = uuid.uuid4().hex[:10]
    unit = detect(text)
    st.setdefault("pending", {})[pid] = {"text": text[:1500], "unit": unit, "at": time.time()}
    if unit:
        tg.send(f"📥 <b>수정 요청으로 접수할까요?</b>\n▫️ 대상: <b>{NAME[unit]}</b>\n▫️ 내용: {html.escape(text[:300])}\n\n"
                "고칠 파일은 사무실이 스스로 찾아요.", confirm_rows(pid), reply_to=msg.get("message_id"))
    else:
        tg.send(f"📥 <b>어느 봇을 고칠까요?</b>\n▫️ 내용: {html.escape(text[:300])}", bot_rows(pid), reply_to=msg.get("message_id"))


def handle_callback(tg, st, cb):
    data, cb_id = cb.get("data", ""), cb.get("id")
    msg_id = (cb.get("message") or {}).get("message_id")
    if data == "mn:x":
        st.pop("await", None); tg.answer(cb_id, "취소했어요"); tg.buttons(msg_id, []); return
    if data.startswith("mq:"):
        tg.answer(cb_id)
        try:
            idx = None if data[3:] == "a" else int(data[3:])
            if idx is not None:
                BOTS[idx]
        except (ValueError, IndexError):
            return
        tg.buttons(msg_id, [])
        request_target(tg, st, idx); return
    if data.startswith("pw:"):
        tg.answer(cb_id)
        parts = data.split(":"); key = parts[1]
        if key == "t" and len(parts) > 2:
            ident = parts[2]
            try:
                import price_watch
                with price_watch.state(write=False) as pdata:
                    enabled = bool((pdata["items"].get(ident) or {}).get("enabled"))
            except Exception:
                tg.send("가격 추적 상태를 읽지 못했어요."); return
            run_price(tg, ("/가격중지 " if enabled else "/가격재개 ") + ident)
            rows = price_list_rows()
            if rows:
                tg.send("▫️ 현재 상태", rows)
        else:
            price_action(tg, st, key)
        return
    if data.startswith("gm:"):
        tg.answer(cb_id)
        gemini_action(tg, st, data[3:])
        return
    kind, _, rest = data.partition(":")
    pend = st.setdefault("pending", {})
    if kind in ("rb", "ch", "rq", "cx"):
        pid, _, idx = rest.partition(":")
        p = pend.get(pid)
        if not p:
            tg.answer(cb_id, "오래된 요청이에요. 다시 보내 주세요."); tg.buttons(msg_id, []); return
        if kind == "cx":
            pend.pop(pid, None); tg.answer(cb_id, "취소했어요"); tg.buttons(msg_id, []); return
        if kind == "ch":
            tg.answer(cb_id); tg.buttons(msg_id, bot_rows(pid)); return
        if kind == "rb":
            try:
                p["unit"] = BOTS[int(idx)][0]
            except (ValueError, IndexError):
                tg.answer(cb_id); return
            tg.answer(cb_id, NAME[p["unit"]])
            tg.buttons(msg_id, [])
            tg.send(f"📥 <b>{NAME[p['unit']]}</b> 수정 요청으로 접수할까요?\n▫️ 내용: {html.escape(p['text'][:300])}", confirm_rows(pid))
            return
        if kind == "rq":
            if not p.get("unit"):
                tg.answer(cb_id); tg.buttons(msg_id, bot_rows(pid)); return
            title = submit_request(p["unit"], p["text"])
            pend.pop(pid, None)
            tg.answer(cb_id, "접수했어요")
            tg.buttons(msg_id, [])
            tg.send(f"✅ <b>접수 완료</b> · {NAME[p['unit']]}\n▫️ 안건: {html.escape(title)}\n"
                    "▫️ 사무실이 고칠 파일을 찾아 수정안을 만들고 있어요. 보통 2~6분 뒤 결재 요청이 옵니다.")
            return
    if kind in ("ap", "apy", "keep", "rj", "df"):
        dep = rest
        m = find_package(dep)
        if not m:
            tg.answer(cb_id, "변경안을 찾지 못했어요"); return
        unit = m.get("unit", "")
        if kind == "df":
            tg.answer(cb_id, "바뀐 코드를 보내요")
            diff = m.get("diff", "") or "(차이 없음)"
            if len(diff) <= 3300:
                tg.send(f"🔍 <b>{html.escape(NAME.get(unit, unit))} · {html.escape(m.get('file', ''))}</b>\n<pre>{html.escape(diff)}</pre>")
            else:
                tg.document(f"change_{dep[:8]}.diff.txt", diff.encode(),
                            f"{NAME.get(unit, unit)} · {m.get('file', '')} 바뀐 코드 (- 지운 줄 / + 새 줄)")
            return
        if kind == "ap":
            tg.answer(cb_id)
            warn = trading_warning(unit)
            tg.buttons(msg_id, [[{"text": "⚠️ 네, 적용합니다", "callback_data": f"apy:{dep}"},
                                 {"text": "↩️ 취소", "callback_data": f"keep:{dep}"}]])
            tg.send(f"정말 승인할까요? <b>{html.escape(NAME.get(unit, unit))}</b> 봇이 잠깐 재시작됩니다.\n"
                    + (f"{warn}\n" if warn else "") + "위 메시지의 <b>⚠️ 네, 적용합니다</b>를 누르면 진행돼요.")
            return
        if kind == "keep":
            tg.answer(cb_id, "취소했어요")
            tg.buttons(msg_id, [[{"text": "✅ 승인", "callback_data": f"ap:{dep}"}, {"text": "❌ 반려", "callback_data": f"rj:{dep}"}],
                                [{"text": "🔍 바뀐 코드 보기", "callback_data": f"df:{dep}"}]])
            return
        ok, res = decide(dep, kind == "apy")
        tg.answer(cb_id, "처리했어요" if ok else str(res))
        tg.buttons(msg_id, [])
        if ok:
            if kind == "apy":
                tg.send(f"✅ <b>승인 완료</b> · {html.escape(NAME.get(unit, unit))} · {html.escape(m.get('file', ''))}\n"
                        "▫️ 적용 → 재시작 확인 → GitHub 업로드가 자동으로 진행됩니다. 끝나면 다시 알려 드릴게요.")
            else:
                tg.send(f"❌ <b>반려 완료</b> · {html.escape(NAME.get(unit, unit))} · 봇과 GitHub 모두 그대로입니다.")
        else:
            tg.send(f"ℹ️ {html.escape(str(res))}")


def main():
    tg = TG()
    if not tg.token or not tg.chat:
        print("사무실 비서 텔레그램 설정 없음 (/etc/bot-office/telegram.json)", flush=True)
        time.sleep(300); return
    st = load(STATE, {})
    offset = st.get("offset")
    print("사무실 비서 대화 담당 시작", flush=True)
    while True:
        try:
            import pc_monitor
            pc_monitor.tick(tg)
        except Exception as e:
            print("PC 감시 확인 오류:", type(e).__name__, flush=True)
        try:
            import office_url
            office_url.tick(tg)
        except Exception as e:
            print("사무실 주소 확인 오류:", type(e).__name__, flush=True)
        try:
            q = {"timeout": 30, "allowed_updates": json.dumps(["message", "callback_query"])}
            if offset:
                q["offset"] = offset
            url = f"{TELEGRAM_API}/bot{tg.token}/getUpdates?" + urllib.parse.urlencode(q)
            with urllib.request.urlopen(url, timeout=40) as r:
                res = json.load(r)
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                try:
                    if "message" in upd:
                        m = upd["message"]
                        if str((m.get("chat") or {}).get("id")) == tg.chat:
                            handle_message(tg, st, m)
                    elif "callback_query" in upd:
                        cb = upd["callback_query"]
                        if str(((cb.get("message") or {}).get("chat") or {}).get("id")) == tg.chat:
                            handle_callback(tg, st, cb)
                except Exception as e:
                    print("처리 오류:", type(e).__name__, e, flush=True)
            cutoff = time.time() - 86400
            st["pending"] = {k: v for k, v in st.get("pending", {}).items() if v.get("at", 0) > cutoff}
            st["offset"] = offset
            save_like(STATE, st)
        except Exception as e:
            print("텔레그램 연결 오류:", type(e).__name__, e, flush=True)
            time.sleep(5)
        if os.environ.get("OFFICE_SECRETARY_ONCE"):
            return


if __name__ == "__main__":
    main()
