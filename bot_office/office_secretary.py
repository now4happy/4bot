#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/office_secretary.py   (OFFICE_SECRETARY_V3)
# 사무실 vNEXT (2026-10-28): ① 🏢 사무실 버튼 (지금 사무실 주소를 바로 여는 버튼) ② ✍️ 수정 요청·결재(옛 결재함)·📋 현황 기능 삭제
#                         ③ 📊 조회 → 💰 잔액 하나로 모으고 다음 단계에서 회사 선택 (한국투자·토스·메리츠·빗썸·전체)
# 사무실 v1.0.48 (2026-10-28): ① 🖥 PC 상태 메뉴·PC 끊김/매직스플릿 알림 복구 (10/27 '메리츠 잔액 표시' 업로드 때 지워졌던 것)
#                         ② 🔗 사무실 주소(/주소 · /주소변경) — 임시 터널 주소가 바뀌면 자동 알림 + 한국 PC 변경 한 줄 (office_url.py)
# V4 (2026-10-26): 비서봇에서 팬딩 모듈 import 및 팬딩 콜백 제거. 팬딩은 전용 봇에서만 처리.
# V3 (2026-10-26): 하단 메인 메뉴·하위 메뉴 정리
# 텔레그램 "사무실 비서" 대화 담당 (항상 실행: bot-office-secretary.service)
#  - 하단 메뉴: 📊 조회(브리핑·잔액·PC 상태·사무실 주소) · 💲 가격·비용 · 🏢 사무실 · ❓ 도움말
#  - 코드 수정은 GitHub staging → 6. Update 승인 방식만 씀 (이 비서는 수정 요청·결재를 받지 않음)
#  안전: 등록된 대표님 채팅방(chat_id)에서 온 것만 처리.
# ==========================================================
import html, json, os, re, subprocess, sys, tempfile, time, urllib.parse, urllib.request, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(os.environ.get("OFFICE_ROOT", "/"))
TELEGRAM_CFG = R / "etc/bot-office/telegram.json"
OFFICE_URL = R / "etc/bot-office/office_url"
STATE = R / "var/lib/bot-office/secretary.json"
TELEGRAM_API = os.environ.get("OFFICE_TELEGRAM_API", "https://api.telegram.org")
SYSTEMCTL = os.environ.get("OFFICE_SYSTEMCTL", "systemctl")
BRIEFING = os.environ.get("OFFICE_BRIEFING", "/opt/bot-office/office_briefing.py")
KST, EST = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")

HELP = ("🏢 <b>사무실 비서 사용법</b>\n"
        "▫️ <b>🏢 사무실</b> : 사무실 상황판을 바로 여는 버튼\n"
        "▫️ <b>브리핑</b> : 지금 바로 비서 브리핑 받기\n"
        "▫️ <b>📊 조회 → 💰 잔액</b> → 회사 선택(한국투자·토스·메리츠·빗썸·전체) : 계좌별 USD/KRW 잔액 (/잔액은 전체)\n"
        "▫️ <b>/가격도움말</b> : 한국 제품 가격 등록·조회·변동 알림\n"
        "▫️ <b>📊 조회 → 🖥 PC 상태</b> : 한국 PC 연결·매직스플릿 실행 확인\n"
        "▫️ <b>📊 조회 → 🔗 사무실 주소</b> : 지금 주소·한국 PC 주소 바꾸는 한 줄 (/주소변경 으로 고정 도메인 이동)\n"
        "▫️ 봇 코드 수정은 Claude·GPT 에게 맡겨 GitHub staging 에 올리고 6. Update 에서 승인해요.")


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


# ---------------------------------------------------------- 버튼 메뉴 (/start 로 하단 버튼이 뜬다)
# 버튼은 기존 글자 명령과 똑같이 처리된다. 글자를 꼭 입력해야 하는 기능(수정 내용·상품명·금액)은
# 버튼을 누르면 "다음 메시지로 보내 주세요" 안내가 뜨고, 그 다음 메시지를 알맞은 명령으로 처리한다(10분 안 · 취소는 아래 다른 버튼).
HOME = "🏠 메인 메뉴"
MAIN_LABELS = [["📊 조회", "💲 가격·비용"], ["🏢 사무실", "❓ 도움말"]]
SUB_LABELS = {
    "view": [["🗞 브리핑", "💰 잔액"], ["🖥 PC 상태", "🔗 사무실 주소"], [HOME]],
    "price": [["🔎 가격 목록", "🔄 가격 확인", "📊 가격 비교"], ["➕ 가격 등록", "🔀 웹·앱 비교 등록"],
              ["🤖 Gemini 사용량", "💵 Gemini 잔액 입력", "💲 Gemini 단가 입력"], [HOME]],
}
MENU_KB = [[{"text": t} for t in row] for row in MAIN_LABELS]
SUB_KB = {k: [[{"text": t} for t in row] for row in v] for k, v in SUB_LABELS.items()}
MENU_ALIAS = {"🗞 브리핑": "브리핑", "❓ 도움말": "/help", "🖥 PC 상태": "/pc_status", "🔗 사무실 주소": "/주소"}
BAL_ACTIONS = {"🏦 한국투자": "kis", "🔷 토스": "toss", "🏛 메리츠": "meritz", "🪙 빗썸": "bithumb", "🧾 전체": "all"}
BAL_ROWS = [[{"text": "🏦 한국투자", "callback_data": "bl:kis"}, {"text": "🔷 토스", "callback_data": "bl:toss"}],
            [{"text": "🏛 메리츠", "callback_data": "bl:meritz"}, {"text": "🪙 빗썸", "callback_data": "bl:bithumb"}],
            [{"text": "🧾 전체", "callback_data": "bl:all"}, {"text": "✖ 닫기", "callback_data": "mn:x"}]]
BAL_NAME = {v: k for k, v in BAL_ACTIONS.items()}
PRICE_ACTIONS = {"🔎 가격 목록": "ls", "🔄 가격 확인": "ck", "📊 가격 비교": "cp", "➕ 가격 등록": "rg", "🔀 웹·앱 비교 등록": "rc"}
GEMINI_ACTIONS = {"🤖 Gemini 사용량": "v", "💵 Gemini 잔액 입력": "b", "💲 Gemini 단가 입력": "r"}
MENU_SPECIAL = tuple(["📊 조회", "💲 가격·비용", "🏢 사무실", "💰 잔액", HOME] + list(PRICE_ACTIONS) + list(GEMINI_ACTIONS))
CANCEL_WORDS = ("브리핑", "잔액", "도움말", "help", "?")
CANCEL_ROWS = [[{"text": "✖ 취소", "callback_data": "mn:x"}]]
AWAIT_PROMPTS = {
    "price_reg": "➕ <b>상품 등록</b>\n다음 메시지로 보내 주세요 (10분 안 · 취소는 아래 다른 버튼):\n<code>상품명 | 도메인(선택) | 연간·월간·일시불(선택)</code>\n예) <i>클로드 Pro 연간 구독</i>",
    "price_cmp": "🔀 <b>웹·앱 비교 등록</b>\n다음 메시지로 상품명을 보내 주세요 (10분 안 · 취소는 아래 다른 버튼). 예) <i>클로드 Pro 연간 구독</i>",
    "gem_bal": "💵 <b>Gemini 잔액 입력</b>\n다음 메시지로 보내 주세요 (10분 안 · 취소는 아래 다른 버튼):\n<code>달러금액 [화면집계일 YYYY-MM-DD]</code>\n예) <i>12.34</i>",
    "gem_rate": "💲 <b>Gemini 단가 입력</b>\n다음 메시지로 보내 주세요 (10분 안 · 취소는 아래 다른 버튼):\n<code>모델명 입력단가 출력단가</code>"}


def menu_inline(spec, prefix):
    return [[{"text": t, "callback_data": f"{prefix}:{k}"} for t, k in row] for row in spec]


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


def office_open(tg):
    """🏢 사무실: 지금 사무실 주소를 여는 버튼 (주소는 /etc/bot-office/office_url · 임시 터널이면 바뀔 때마다 자동 갱신)"""
    try:
        url = OFFICE_URL.read_text(encoding="utf-8").strip()
    except OSError:
        url = ""
    if not re.fullmatch(r"https://[A-Za-z0-9.-]+(:\d+)?/?", url):
        tg.send("🏢 사무실 주소를 아직 몰라요. 🔗 사무실 주소 (/주소) 로 확인해 주세요."); return
    tg.send("🏢 <b>사무실 상황판</b> · 아래 버튼을 누르면 열려요 (로그인 필요)",
            [[{"text": "🏢 사무실 열기", "url": url.rstrip("/") + "/"}]])


def balance(tg, key):
    tg.send(f"💰 {BAL_NAME.get(key, '전체')} 잔액을 조회하고 있어요…")
    subprocess.Popen([sys.executable, BRIEFING, "--balances", key], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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
    if raw == "🏢 사무실":
        office_open(tg); return
    if raw == "💰 잔액":
        tg.send("💰 <b>어느 회사 잔액을 볼까요?</b>", BAL_ROWS); return
    if raw in BAL_ACTIONS:   # 예전 하단 버튼이 남아 있을 때도 동작
        balance(tg, BAL_ACTIONS[raw]); return
    if raw in PRICE_ACTIONS:
        price_action(tg, st, PRICE_ACTIONS[raw]); return
    if raw in GEMINI_ACTIONS:
        gemini_action(tg, st, GEMINI_ACTIONS[raw]); return
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
        balance(tg, "all"); return
    if low in ("/사무실", "사무실", "/office"):
        office_open(tg); return
    if low in ("/brief", "브리핑", "/briefing"):
        tg.send("🗞 브리핑을 준비하고 있어요…")
        subprocess.Popen([sys.executable, BRIEFING], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return
    if text.startswith("/"):
        tg.send("모르는 명령이에요. <b>도움말</b>을 보내 보세요."); return
    tg.send("아래 버튼 메뉴로 써 주세요. 봇 코드 수정은 이제 GitHub staging → 6. Update 승인으로만 해요.", keyboard=MENU_KB)


def handle_callback(tg, st, cb):
    data, cb_id = cb.get("data", ""), cb.get("id")
    msg_id = (cb.get("message") or {}).get("message_id")
    if data == "mn:x":
        st.pop("await", None); tg.answer(cb_id, "취소했어요"); tg.buttons(msg_id, []); return
    if data.startswith("bl:"):
        key = data[3:]
        if key not in BAL_NAME:
            tg.answer(cb_id); return
        tg.answer(cb_id, BAL_NAME[key]); balance(tg, key); return
    if data.startswith(("mq:", "rb:", "ch:", "rq:", "cx:", "ap:", "apy:", "keep:", "rj:", "df:")):   # 삭제한 수정 요청·결재 버튼 (예전 메시지)
        tg.answer(cb_id, "수정 요청·결재 기능은 없어졌어요"); tg.buttons(msg_id, []); return
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
            st.pop("pending", None)   # 옛 수정 요청 대기 기록 정리
            st["offset"] = offset
            save_like(STATE, st)
        except Exception as e:
            print("텔레그램 연결 오류:", type(e).__name__, e, flush=True)
            time.sleep(5)
        if os.environ.get("OFFICE_SECRETARY_ONCE"):
            return


if __name__ == "__main__":
    main()
