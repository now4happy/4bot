#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/office_secretary.py   (OFFICE_SECRETARY_V3)
# 사무실 v1.8.7 (2026-11-14): 웹 사무실 완전 제거에 맞춰 8번 비서를 SGOV 메뉴 전용으로 정리 — 🏢 사무실·/주소·🖥 PC 상태·💰 잔액·Update 안내 삭제
#                         (남김: SGOV 메뉴 office_sgov.py · 허브 신호 · 전략·종목·금액·enabled 변경 없음)
# 사무실 v1.8.6 (2026-11-14): 봇 이름·번호 새 1~9번 목록으로 표시 문자열만 정리 (전략·종목·금액·enabled 그대로)
# 사무실 v1.8.3 (2026-11-14): SGOV 메뉴 추가 — 하단 [📈 상황판 | ☰ 메뉴](SGOV) + [🏢 사무실 메뉴](예전 ☰ 메뉴 그대로). 화면·요청은 office_sgov.py
# 사무실 v1.5.0 (2026-11-09): 브리핑 버튼·명령 제거, 잔액·메뉴 유지
# 사무실 v1.4.4 (2026-11-07): 하단 메뉴 2개 [🗞 브리핑 | ☰ 메뉴] — 나머지는 ☰ 메뉴 안 · 📊 조회 글자도 메뉴를 보여 줌 (버튼 글자·명령 그대로)
# 사무실 v1.4.5 (2026-11-07): ① 🗞 브리핑 = 수동 브리핑(--manual, 주말에도 전송) ② ☰ 메뉴에서 🔗 사무실 주소 버튼 삭제 (🏢 사무실만 · /주소 글자 명령 그대로)
# 사무실 v1.0.57 (2026-10-28): ① 🏢 사무실 버튼 (지금 사무실 주소를 바로 여는 버튼) ② ✍️ 수정 요청·결재(옛 결재함)·📋 현황 기능 삭제
#                         ③ 📊 조회 → 💰 잔액 하나로 모으고 다음 단계에서 회사 선택 (한국투자·토스·메리츠·빗썸·전체)
# 사무실 v1.0.48 (2026-10-28): ① 🖥 PC 상태 메뉴·PC 끊김/매직스플릿 알림 복구 (10/27 '메리츠 잔액 표시' 업로드 때 지워졌던 것)
#                         ② 🔗 사무실 주소(/주소 · /주소변경) — 임시 터널 주소가 바뀌면 자동 알림 + 한국 PC 변경 한 줄 (office_url.py)
# V4 (2026-10-26): 비서봇에서 팬딩 모듈 import 및 팬딩 콜백 제거. 팬딩은 전용 봇에서만 처리.
# V3 (2026-10-26): 하단 메인 메뉴·하위 메뉴 정리
# 텔레그램 "사무실 비서" 대화 담당 (항상 실행: bot-office-secretary.service)
#  - 하단 메뉴: [📈 상황판 | ☰ 메뉴] = SGOV 메뉴 (office_sgov.py) 뿐
#  안전: 등록된 대표님 채팅방(chat_id)에서 온 것만 처리.
# ==========================================================
import html, json, os, re, sys, tempfile, time, urllib.parse, urllib.request, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- alert-hub: 기존 전송은 그대로, 자율 알림만 hub DB에 복사 (실패해도 봇은 계속) ---
try:
    import sys as _hub_sys
    _HUB_ROOT = "/home/gieokkim/alert-hub"
    if _HUB_ROOT not in _hub_sys.path:
        _hub_sys.path.insert(0, _HUB_ROOT)
    from alert_hub.notify import heartbeat as _hub_heartbeat, notify as _hub_notify
except Exception:
    _hub_heartbeat = None
    _hub_notify = None

def _hub_beat(bot):
    try:
        if _hub_heartbeat:
            _hub_heartbeat(bot)
    except Exception:
        pass

def _hub_alert(bot, level, text):
    try:
        if _hub_notify:
            import re as _hub_re
            _hub_notify(bot, level, _hub_re.sub(r"<[^>]+>", "", str(text)))
    except Exception:
        pass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(os.environ.get("OFFICE_ROOT", "/"))
TELEGRAM_CFG = R / "etc/bot-office/telegram.json"
STATE = R / "var/lib/bot-office/secretary.json"
TELEGRAM_API = os.environ.get("OFFICE_TELEGRAM_API", "https://api.telegram.org")
SYSTEMCTL = os.environ.get("OFFICE_SYSTEMCTL", "systemctl")
KST, EST = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")

HELP = ("🤖 <b>8번 비서 사용법</b> (SGOV 메뉴)\n"
        "▫️ <b>📈 상황판</b> : SGOV 상황판\n"
        "▫️ <b>☰ 메뉴</b> : 🪙 SGOV 현황 · 💰 자금·SGOV · ⚙️ 시드·SGOV · 💵 분배금 기록 · 🛠 도구 · ❓ 도움말")


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
HOME = "🏠 메인 메뉴"   # 예전 하단 버튼이 남아 있을 때도 처음 화면으로
MENU_OPEN = "☰ 메뉴"
# v1.8.7: 처음 화면은 SGOV 진입 버튼 2개뿐 [📈 상황판, ☰ 메뉴] (office_sgov.py 가 받아서 SGOV 상황판·SGOV 메뉴로)
SGOV_CHART = "📈 상황판"
SGOV_HOME = "🏠 처음 화면"
MAIN_LABELS = [[SGOV_CHART, MENU_OPEN]]
MENU_KB = [[{"text": t} for t in row] for row in MAIN_LABELS]
CANCEL_ROWS = [[{"text": "✖ 취소", "callback_data": "mn:x"}]]
OFFICE_LABELS = {HOME, "❓ 도움말"}   # office_sgov.handle 에 넘기는 '비서봇 버튼 글자' (숫자 입력 대기 해제용)
try:
    import office_sgov   # v1.8.3: SGOV 메뉴 (없으면 예전 메뉴만 동작)
except Exception as _e:
    office_sgov = None
    print("SGOV 메뉴 불러오기 실패:", type(_e).__name__, flush=True)


# ---------------------------------------------------------- 메인 루프
def handle_message(tg, st, msg):
    text = (msg.get("text") or "").strip()
    if not text:
        return
    raw = text
    if office_sgov and office_sgov.handle(tg, st, raw, OFFICE_LABELS):   # SGOV 메뉴 글자 (📈 상황판·☰ 메뉴 포함)
        return
    if raw in (HOME, SGOV_HOME):
        tg.send("🏠 <b>처음 화면</b> · 아래 버튼을 눌러 주세요", keyboard=MENU_KB); return
    low = text.lower()
    if low in ("/start", "/help", "도움말", "help", "?") or raw == "❓ 도움말":
        tg.send(HELP, keyboard=MENU_KB); return
    tg.send("모르는 명령이에요. 아래 버튼(📈 상황판 · ☰ 메뉴)으로 써 주세요.", keyboard=MENU_KB)


def handle_callback(tg, st, cb):
    data, cb_id = cb.get("data", ""), cb.get("id")
    msg_id = (cb.get("message") or {}).get("message_id")
    if data == "mn:x":
        st.pop("await", None); tg.answer(cb_id, "취소했어요"); tg.buttons(msg_id, []); return
    if data.startswith(("mq:", "rb:", "ch:", "rq:", "cx:", "ap:", "apy:", "keep:", "rj:", "df:")):   # 삭제한 수정 요청·결재 버튼 (예전 메시지)
        tg.answer(cb_id, "수정 요청·결재 기능은 없어졌어요"); tg.buttons(msg_id, []); return
    tg.answer(cb_id, "없어진 버튼이에요"); tg.buttons(msg_id, [])   # v1.8.7: 예전 메시지의 삭제된 버튼(옛 잔액 회사 선택 등) — 버튼만 지움


def main():
    tg = TG()
    if not tg.token or not tg.chat:
        print("사무실 비서 텔레그램 설정 없음 (/etc/bot-office/telegram.json)", flush=True)
        time.sleep(300); return
    st = load(STATE, {})
    offset = st.get("offset")
    print("사무실 비서 대화 담당 시작", flush=True)
    while True:
        _hub_beat('8번 비서')
        waiting = 0
        try:
            waiting = office_sgov.tick(tg, st) if office_sgov else 0   # v1.8.3: SGOV 요청 결과 확인 (meritz_dca_bot 이 쓴 결과 파일 읽기만)
        except Exception as e:
            print("SGOV 결과 확인 오류:", type(e).__name__, flush=True)
        try:
            q = {"timeout": 5 if waiting else 30, "allowed_updates": json.dumps(["message", "callback_query"])}
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
