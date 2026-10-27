#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/fanding_trade.py   (FANDING_TRADE_V1.8.2)
# 1.1.0: 글 안의 이미지 여러 장 중 가격표만 Gemini 로 골라냄 (순서 바뀌어도 OK) · 가격표 없으면 알림
#        · 이 파일이 바뀌면 상시 프로그램·비서가 스스로 새 코드로 다시 불러옴 (업데이트 비서 적용 후 재시작 불필요)
# 1.2.0: 매매 규칙 분석용 기록 시작 — 가격표의 모든 칸(잔금·사이클 시작$·실현수익 등)과 주문 결과를
#        /var/lib/bot-office/fanding/history.jsonl 에 하루 한 줄씩 영구 보관 (서버에만, GitHub 에 안 올라감)
# 1.3.0: 팬딩 전용 텔레그램 봇 지원(/etc/bot-office/telegram_fanding.json 이 있으면 그 봇으로 알림·버튼·명령)
#        · Gemini 바쁨(503)·시간초과 → 재시도·예비 모델, 실패한 이미지는 2분 뒤 다시 시도, 알림은 한 번만
#        · 과거 가격표 수집(윈도우가 하루 10개씩 보냄) → 알림·주문 없이 기록만
# 1.4.0: 이미지 판독 AI 2개 — Gemini 가 안 되면 DeepSeek(deepseek-flash)로 자동 전환, 그날 되는 쪽을 기억
#        (DeepSeek 키는 미팅룸과 같은 /etc/bot-office/ai.env 의 DEEPSEEK_API_KEY 사용) · /판독 명령으로 상태 확인
# 1.5.0: 가격표 판별을 '읽어보고 판단'으로 변경 — AI 가 아니라고 해도 날짜·종가가 메리츠 실제 종가와 맞으면 가격표로 인정
#        (AI 의 판별 실수로 가격표를 놓치는 문제 해결) · 판별 이유를 기록 · 처리 끝난 가격표 이미지는 서버에서 자동 삭제
# 1.5.1: 1.5.0 판독 형식이 비어 있던 오류 수정 · 없어진 예비 모델(gemini-2.5-flash) 대신 기본 모델 재시도 → DeepSeek
# 1.5.2: DeepSeek 를 먼저 사용(Gemini API 무료 한도 문제) · DeepSeek 답이 형식에 안 맞으면 한 번 더 요청
#        · Gemini 한도초과(429)는 기다리지 않고 바로 넘어감 · 확인용 두 번째 판독이 실패해도 가격표는 알림(자동주문만 막음)
# 1.6.0: 예약 발주 시간 설정(기본: 장마감 30분 전 = 30분 VWAP) · /재예약 (오늘 예약 취소 후 새 시간으로 다시)
#        · 확인용 두 번째 판독은 첫 번째와 다른 AI 로 (DeepSeek ↔ Gemini 교차 확인)
# 1.6.1: /재예약 때 메리츠 앱에서 이미 직접 취소한 예약은 건너뜀(살아 있는 예약 목록 확인) · /재예약강제 추가
# 1.6.2: 금요일 가격표는 월요일 아침에 받아도 됨 → '가격표 안 옴' 알림을 토요일이 아닌 월요일에 확인
# 1.0.1: 웹서버(bot-office 계정)가 텔레그램 키를 못 읽는 문제 → 윈도우 알림은 파일로 넘겨 이 프로그램이 전송 / 설정 저장 시 권한 유지
# 1.7.2: 하단 버튼 메뉴(/start)·배수/자동주문/발주시간 선택 버튼 — 기존 명령과 같은 기능을 버튼으로 (7번 비서의 팬딩 메뉴 공용)
# 1.8.0: 5번 봇 메뉴를 [🅿 P 메뉴](기존 가격표 매매 11버튼) · [🅥 VR6 메뉴](fanding_vr6.py, TQQQ 2주 1회 표 수신)로 분리
#        · 윈도우 업로드에 X-Fanding-Kind: vr6* 경로 추가(기존 P 업로드·판독·주문 흐름은 그대로)
# 팬딩 가격표 → 숫자 확인 → 메리츠 Limit VWAP 예약주문 (SOXL)
#
#  흐름
#   1) 윈도우 PC 가 가격표 이미지를 사무실 주소(/api/fanding/upload)로 올림 → inbox 에 저장
#   2) 이 프로그램(bot-office-fanding.service)이 Gemini 로 두 번 읽어 숫자가 같은지 확인 + 안전점검
#   3) 사무실 비서 봇으로 [✅ 주문] [❌ 이번엔 안 함] 알림 (원본 이미지 첨부)
#   4) 승인되면 한국시간 09:01 이후 메리츠 예약주문(Limit VWAP, 장개시 발주) 접수
#   5) 버튼을 안 누르면: 예약 마감 30분 전 알림 → 10분 전 자동주문 (안전점검 전부 통과한 경우만)
#
#  파일 (GitHub 에 올라가지 않는 곳)
#   /etc/bot-office/fanding.json       설정 (업로드 암호, 종목, 한도 등)
#   /etc/bot-office/meritz.json        메리츠 앱키
#   /var/lib/bot-office/fanding/       상태·이미지 (가격표는 서버에만 보관)
#
#  명령
#   python3 fanding_trade.py loop          서비스로 상시 실행
#   python3 fanding_trade.py check         메리츠 조회 테스트 (주문 안 함)
#   python3 fanding_trade.py parse 그림    Gemini 판독 + 점검만 (알림·주문 안 함)
#   python3 fanding_trade.py inject 그림   서버에서 직접 그림 넣기 (윈도우 없이 테스트)
#   python3 fanding_trade.py status        현재 상태 출력
# ==========================================================
import base64, fcntl, hashlib, hmac, html, json, os, re, sys, tempfile, time, urllib.error, urllib.parse, urllib.request, uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = "1.8.2"
R = Path(os.environ.get("OFFICE_ROOT", "/"))
CFG = R / "etc/bot-office/fanding.json"
GEMINI_CFG = R / "etc/bot-office/gemini.json"
AI_ENV = R / "etc/bot-office/ai.env"          # 미팅룸과 같은 키 파일 (DEEPSEEK_API_KEY=...)
TELEGRAM_CFG = R / "etc/bot-office/telegram.json"
FANDING_TG_CFG = R / "etc/bot-office/telegram_fanding.json"   # 팬딩 전용 봇 (있으면 이걸 씀)
HOME = R / "var/lib/bot-office/fanding"
INBOX, IMAGES = HOME / "inbox", HOME / "images"
HISTORY = HOME / "history.jsonl"
STATE, LOCKF = HOME / "state.json", HOME / ".lock"
TELEGRAM_API = os.environ.get("OFFICE_TELEGRAM_API", "https://api.telegram.org")
KST, ET = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
RESERVE_NAMES = {"0": "장개시", "1": "장마감 10분 전", "2": "장마감 30분 전", "3": "장개시 30분 후"}
LAST_PROVIDER = {"name": ""}

DEFAULTS = {
    "symbol": "SOXL",
    "price_market": "AX",        # 메리츠 현재가 조회용 거래소 구분 (SOXL: NYSE Arca → 보통 AX). check 명령으로 확인
    "exch_id": "",               # 예약주문용 거래소 번호. 비우면 잔고에서 자동으로 찾음
    "multiplier": 5,             # 처음 배수 (이후엔 비서 봇 /배수 로 변경)
    "max_buy_usd": 8000,         # 1회 매수 총액 한도(배수 적용 후). 넘으면 주문 막음
    "auto_order": True,          # 버튼 안 누르면 마감 10분 전 자동주문
    "submit_kst": "09:01",       # 예약주문 접수 시작 (한국시간)
    "reserve_time": "2",         # 예약 발주 시간: "2" 장마감 30분 전(30분 VWAP) · "1" 장마감 10분 전 · "0" 장개시 · "3" 장개시 30분 후
    "cutoff_et": "08:30",        # 예약 마감으로 보는 시각 (미국 동부시간, 정규장 9:30 1시간 전)
    "alarm_before_min": 30,
    "auto_before_min": 10,
    "missing_alert_kst": "11:00",  # 이 시각까지 가격표가 안 오면 알림
    "gemini_model": "gemini-3.8-flash",
    "gemini_fallback": "",                   # Gemini 예비 모델 (비우면 기본 모델로 재시도 → 그래도 안 되면 DeepSeek)
    "vision_order": ["gemini", "deepseek"],  # 이미지 판독 AI 순서 (앞에서 안 되면 다음)
    "deepseek_model": "deepseek-flash",
    "upload_token": "",
}


# ---------------------------------------------------------- 공통
def load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save(p, data, mode=0o600):
    """원자적 저장. 이미 있는 파일이면 소유자·그룹·권한을 그대로 유지 (웹서버가 계속 읽을 수 있게)"""
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


def cfg():
    c = dict(DEFAULTS)
    c.update(load(CFG, {}))
    return c


@contextmanager
def locked_state():
    """비서 봇(버튼)과 이 프로그램이 동시에 상태를 고치지 않도록 잠금"""
    HOME.mkdir(parents=True, exist_ok=True)
    with open(LOCKF, "a") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        st = load(STATE, {})
        st.setdefault("sheets", {})
        if "multiplier" not in st:
            st["multiplier"] = int(cfg()["multiplier"])
        yield st
        save(STATE, st)
        fcntl.flock(lf, fcntl.LOCK_UN)


def now_kst():
    return datetime.now(KST)


def hm(s):
    h, m = s.split(":")
    return int(h), int(m)


def last_session_date(now=None):
    """지금 기준 마지막으로 끝난 미국 정규장 날짜 (주말 제외, 휴장일은 고려 안 함)"""
    e = (now or now_kst()).astimezone(ET)
    d = e.date()
    if e.weekday() >= 5 or (e.hour, e.minute) < (16, 0):
        d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def next_session_date(sheet_date):
    d = sheet_date + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def fmt_money(x):
    return f"${x:,.2f}"


# ---------------------------------------------------------- 텔레그램
class TG:
    def __init__(self):
        own = load(FANDING_TG_CFG, {})
        c = own if own.get("token") else load(TELEGRAM_CFG, {})
        self.own = bool(own.get("token"))        # 팬딩 전용 봇이면 이 프로그램이 직접 메시지를 받음
        self.token, self.chat = c.get("token"), str(c.get("chat_id", ""))

    def buttons(self, msg_id, rows):
        if not msg_id:
            return
        try:
            self._post("editMessageReplyMarkup", {"chat_id": self.chat, "message_id": msg_id,
                                                  "reply_markup": {"inline_keyboard": rows or []}})
        except Exception:
            pass

    def answer(self, cb_id, text=""):
        try:
            self._post("answerCallbackQuery", {"callback_query_id": cb_id, "text": text[:180]})
        except Exception:
            pass

    def updates(self, offset, timeout=15):
        q = {"timeout": timeout, "allowed_updates": json.dumps(["message", "callback_query"])}
        if offset:
            q["offset"] = offset
        url = f"{TELEGRAM_API}/bot{self.token}/getUpdates?" + urllib.parse.urlencode(q)
        with urllib.request.urlopen(url, timeout=timeout + 10) as r:
            return json.load(r).get("result", [])

    def _post(self, method, payload):
        req = urllib.request.Request(f"{TELEGRAM_API}/bot{self.token}/{method}", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r).get("result", {})

    def send(self, text, rows=None, keyboard=None):
        p = {"chat_id": self.chat, "text": text[:3900], "parse_mode": "HTML", "disable_web_page_preview": True}
        if rows:
            p["reply_markup"] = {"inline_keyboard": rows}
        elif keyboard:   # 채팅창 아래에 계속 떠 있는 버튼
            p["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True, "is_persistent": True}
        try:
            return self._post("sendMessage", p)
        except Exception as e:
            print("텔레그램 전송 실패:", e, flush=True); return {}

    def photo(self, path, caption, rows=None):
        b = uuid.uuid4().hex
        fields = {"chat_id": self.chat, "caption": caption[:1000], "parse_mode": "HTML"}
        if rows:
            fields["reply_markup"] = json.dumps({"inline_keyboard": rows})
        parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="photo"; filename="sheet.jpg"\r\n'
                     f'Content-Type: image/jpeg\r\n\r\n'.encode() + Path(path).read_bytes() + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        req = urllib.request.Request(f"{TELEGRAM_API}/bot{self.token}/sendPhoto", data=b"".join(parts), method="POST",
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r).get("result", {})
        except Exception as e:
            print("사진 전송 실패:", e, flush=True)
            return self.send(caption, rows)

    def clear_buttons(self, msg_id):
        if not msg_id:
            return
        try:
            self._post("editMessageReplyMarkup", {"chat_id": self.chat, "message_id": msg_id,
                                                  "reply_markup": {"inline_keyboard": []}})
        except Exception:
            pass


# ---------------------------------------------------------- Gemini 판독
SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "close_date": {"type": "STRING", "description": "종가날짜 YYYY-MM-DD"},
        "close": {"type": "NUMBER", "description": "종가"},
        "avg_price": {"type": "NUMBER", "description": "보유 평단"},
        "holding_qty": {"type": "INTEGER", "description": "현재 보유 개수"},
        "cycle": {"type": "STRING", "description": "현사이클 차수 (예: 33차)"},
        "cycle_start_date": {"type": "STRING", "description": "현사이클시작 날짜 (예: 10/2)"},
        "prev_trade_qty": {"type": "INTEGER", "description": "직전 매매 개수"},
        "cycle_start_usd": {"type": "NUMBER", "description": "현사이클 시작 $"},
        "cash_usd": {"type": "NUMBER", "description": "잔금 $"},
        "realized_today_usd": {"type": "NUMBER", "description": "당일실현 $ (비어 있으면 생략)"},
        "cycle_realized_usd": {"type": "NUMBER", "description": "현사이클 실현수익 $ (음수 가능)"},
        "total_return_pct": {"type": "NUMBER", "description": "올해 총 수익률 % 숫자만"},
        "total_realized_usd": {"type": "NUMBER", "description": "올해 누적실현수익"},
        "buys": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "price": {"type": "NUMBER"}, "qty": {"type": "INTEGER"}}, "required": ["price", "qty"]}},
        "sells": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "price": {"type": "NUMBER"}, "qty": {"type": "INTEGER"}}, "required": ["price", "qty"]}},
    },
    "required": ["close_date", "close", "buys", "sells"],
}
COMBINED_SCHEMA = {"type": "OBJECT", "properties": dict(SCHEMA["properties"], is_price_sheet={"type": "BOOLEAN"},
                                                        reason={"type": "STRING"}),
                   "required": ["is_price_sheet", "close_date", "close", "buys", "sells"]}

PROMPTS = [
    "이 이미지는 미국주식 매매 가격표(표)입니다. 표에 적힌 숫자만 그대로 옮겨 적으세요. 추측하지 마세요.\n"
    "- 'Limit Vwap 매수가 / 개수' 칸의 각 줄 → buys (비어 있는 줄은 넣지 않음)\n"
    "- 'Limit Vwap 매도가 / 개수' 칸의 각 줄 → sells (위에서 아래 순서, 비어 있는 줄은 넣지 않음)\n"
    "- 종가날짜(예: 2026. 10. 22 → 2026-10-22), 종가, 보유 평단, 현재 보유 개수, 현사이클 차수\n"
    "- 현사이클시작 날짜, 직전 매매 개수, 현사이클 시작 $, 잔금 $, 당일실현 $, 현사이클 실현수익 $, 총 수익률 %, 누적실현수익 (있는 것만)\n"
    "가격은 소수점까지 정확히, 개수는 정수로 적으세요.",
    "Transcribe this trading price sheet exactly. Do not guess or compute anything.\n"
    "buys = every filled row under the BUY table (매수가, 개수). sells = every filled row under the SELL table "
    "(매도가, 개수), top to bottom. Skip empty rows. close_date = 종가날짜 as YYYY-MM-DD. close = 종가. "
    "avg_price = 보유 평단. holding_qty = 현재 보유 개수. cycle = 현사이클 차수. Copy every decimal digit exactly.",
]


CLASSIFY_SCHEMA = {"type": "OBJECT", "properties": {
    "is_price_sheet": {"type": "BOOLEAN"}, "reason": {"type": "STRING"}}, "required": ["is_price_sheet"]}
CLASSIFY_PROMPT = ("이 이미지가 미국주식 매매 '가격표'인지 판단하세요. 가격표의 특징: 'Limit Vwap' 제목 아래 "
                   "'매수가/개수' 표와 '매도가/개수' 표, 그리고 '종가날짜', '종가', '보유 평단' 칸이 숫자와 함께 있음. "
                   "안내문·공지·차트·광고·설명 이미지는 가격표가 아닙니다.")


def _vision_json(text, schema):
    """Only accept a complete final JSON object with the required fields."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I).strip()
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        raise RuntimeError("최종 JSON이 비었거나 불완전함") from None
    if not isinstance(value, dict) or any(k not in value for k in schema.get("required", [])):
        raise RuntimeError("최종 JSON 필수 항목 누락")
    return value


def _vision_error(exc):
    # Never expose provider response bodies, credentials or input image data.
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code} (모델·키·권한·한도 확인)"
    if isinstance(exc, (TimeoutError, OSError)):
        return "연결 오류 또는 시간 초과"
    return str(exc)[:120] if isinstance(exc, RuntimeError) else type(exc).__name__


def _gemini(img_bytes, prompt, schema, max_tokens=2048):
    g = load(GEMINI_CFG, {})
    key = g.get("api_key")
    if not key:
        raise RuntimeError("Gemini 키 없음 (/etc/bot-office/gemini.json)")
    mime = "image/png" if img_bytes[:4] == b"\x89PNG" else ("image/webp" if img_bytes[:4] == b"RIFF" else "image/jpeg")
    payload = {
        "contents": [{"parts": [{"inline_data": {"mime_type": mime, "data": base64.b64encode(img_bytes).decode()}},
                                {"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                             "responseSchema": schema, "maxOutputTokens": max(max_tokens, 8192)},
    }
    c = cfg()
    tries = [c["gemini_model"], c.get("gemini_fallback") or c["gemini_model"], c.get("gemini_fallback") or c["gemini_model"]]
    last = None
    for i, model in enumerate(tries):
        gc = payload["generationConfig"]
        if model.startswith("gemini-3"):
            gc["thinkingConfig"] = {"thinkingLevel": "low"}
        else:
            gc.pop("thinkingConfig", None)
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                     data=json.dumps(payload).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.load(r)
            try:
                import gemini_usage
                gemini_usage.record(d, model)
            except Exception as usage_error:
                print("Gemini usage record failed:", type(usage_error).__name__, flush=True)
            cand = (d.get("candidates") or [{}])[0]
            finish = cand.get("finishReason", "UNKNOWN")
            if finish not in ("STOP",):
                raise RuntimeError(f"Gemini 판독 중단 ({finish})")
            text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []) if not p.get("thought"))
            try:
                return _vision_json(text, schema)
            except RuntimeError:
                raise RuntimeError("Gemini 최종 JSON이 비었거나 불완전함") from None
        except RuntimeError as e:
            last = e
            if "MAX_TOKENS" in str(e):
                gc["maxOutputTokens"] = min(16384, gc["maxOutputTokens"] * 2)
            elif "JSON" not in str(e):
                raise
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:
                raise RuntimeError("Gemini API 사용 한도 초과(429) — 앱 요금제와 API 한도는 별개")
            if e.code not in (500, 502, 503, 504):
                raise
        except (TimeoutError, OSError) as e:      # 시간초과·연결 끊김
            last = e
        print(f"Gemini 바쁨({type(last).__name__}) → {[5, 15, 0][i]}초 뒤 다시 ({model})", flush=True)
        time.sleep([5, 15, 0][i])
    else:
        raise RuntimeError("Gemini 응답 실패: " + _vision_error(last))


def _env_key(name):
    try:
        for line in AI_ENV.read_text(encoding="utf-8").splitlines():
            k, _, v = line.strip().partition("=")
            if k.strip() == name:
                return v.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def _schema_hint(schema):
    props = schema.get("properties", {})
    return "{" + ", ".join(f'"{k}": {v.get("type", "").lower()}' for k, v in props.items()) + "}"


def _deepseek(img_bytes, prompt, schema, max_tokens=2048, _again=False):
    key = _env_key("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DeepSeek 키 없음 (/etc/bot-office/ai.env 의 DEEPSEEK_API_KEY)")
    mime = "image/png" if img_bytes[:4] == b"\x89PNG" else ("image/webp" if img_bytes[:4] == b"RIFF" else "image/jpeg")
    text = (prompt + "\n\n반드시 아래 형식의 JSON 객체 하나만 출력하세요. 설명·코드블록 없이.\n" + _schema_hint(schema)
            + "\nbuys/sells 는 [{\"price\": 숫자, \"qty\": 정수}] 배열입니다." * ("buys" in schema.get("properties", {})))
    if _again:
        text = "중요: 이번에는 설명 없이 JSON 객체 하나만, 반드시 { 로 시작해서 } 로 끝나게 출력하세요.\n\n" + text
    body = {"model": cfg()["deepseek_model"], "temperature": 0, "max_tokens": max(max_tokens, 6000),
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64," + base64.b64encode(img_bytes).decode()}}]}]}
    last = None
    for i in range(3):
        req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            break
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"DeepSeek 오류 HTTP {e.code}")
        except (TimeoutError, OSError) as e:
            last = e
        time.sleep([5, 15, 0][i])
    else:
        raise RuntimeError(f"DeepSeek 응답 없음: {last}")
    msg = (d.get("choices") or [{}])[0].get("message") or {}
    finish = (d.get("choices") or [{}])[0].get("finish_reason")
    try:
        if finish != "stop":
            raise RuntimeError("DeepSeek 판독 중단")
        return _vision_json(msg.get("content") or "", schema)
    except RuntimeError:
        if not _again:
            return _deepseek(img_bytes, prompt, schema, max_tokens, _again=True)
        raise RuntimeError("DeepSeek 최종 JSON이 비었거나 불완전함 (추론 내용은 주문값으로 사용 안 함)") from None


PROVIDERS = {"gemini": _gemini, "deepseek": _deepseek}


def vision(img_bytes, prompt, schema, max_tokens=2048, avoid=""):
    """그날 되는 AI 로 이미지 판독. 실패하면 다음 AI 로 넘어가고, 성공한 AI 를 오늘 먼저 쓰도록 기억"""
    order = [p for p in cfg().get("vision_order", ["gemini", "deepseek"]) if p in PROVIDERS]
    today = now_kst().date().isoformat()
    st = load(STATE, {})
    best = (st.get("vision_today") or {})
    if best.get("date") == today and best.get("provider") in order:
        order.remove(best["provider"]); order.insert(0, best["provider"])
    if "gemini" in order:
        order.remove("gemini"); order.insert(0, "gemini")
    if avoid in order and len(order) > 1:          # 교차 확인: 방금 쓴 AI 는 맨 뒤로
        order.remove(avoid); order.append(avoid)
    errors = []
    for prov in order:
        try:
            r = PROVIDERS[prov](img_bytes, prompt, schema, max_tokens)
        except Exception as e:
            errors.append(f"{prov}: {_vision_error(e)}")
            print("판독 AI 실패 →", prov, e, flush=True)
            continue
        with locked_state() as s2:
            s2["vision_last_attempt"] = {"date": today, "at": now_kst().isoformat(), "ok": True,
                                         "provider": prov, "errors": errors}
        if not avoid:
            with locked_state() as s2:
                s2["vision_today"] = {"date": today, "provider": prov, "errors": errors}
        LAST_PROVIDER["name"] = prov
        return r
    with locked_state() as s2:
        s2["vision_last_attempt"] = {"date": today, "at": now_kst().isoformat(), "ok": False, "errors": errors}
    raise RuntimeError("판독 AI 모두 실패 · " + " / ".join(errors))


BRIDGE = HOME / "windows-control.json"
BRIDGE_LOCK = HOME / ".windows-control.lock"


@contextmanager
def bridge_state():
    HOME.mkdir(parents=True, exist_ok=True)
    fd = os.open(BRIDGE_LOCK, os.O_CREAT | os.O_RDWR, 0o660)
    try:
        parent = HOME.stat()
        try:
            os.fchown(fd, parent.st_uid, parent.st_gid)
            os.fchmod(fd, 0o660)
        except PermissionError:
            pass
        with os.fdopen(fd, "a") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            st = load(BRIDGE, {})
            yield st
            save(BRIDGE, st, 0o660)
    finally:
        pass


def request_scan(reason="manual"):
    now = time.time()
    expected = last_session_date().isoformat()
    with bridge_state() as b:
        req = b.get("request") or {}
        if now - req.get("at", 0) < 300:
            return "최근 요청이 대기/처리 중입니다. /진단 으로 확인하세요."
        b["request"] = {"id": uuid.uuid4().hex, "at": now, "expected": expected, "reason": reason}
    return f"윈도우 PC에 사이트 재접속·최신 자료 재판독 요청을 등록했습니다.\n필요 종가일: {expected} (게시일과 다름)\nPC 대기 프로그램 실행 중이면 약30초 내 확인합니다."


def sheet_ready(sheet):
    return bool(sheet and (sheet.get("reads_agree") or sheet.get("status") in
                          ("submitted", "partial", "submitting")))


def pending_live_images():
    """P 수집은 VR6/과거 자료의 판독 대기 때문에 막지 않는다."""
    return sum(1 for image in INBOX.glob("*.img")
               if (lambda meta: meta.get("kind") != "vr6" and meta.get("mode") != "history")(
                   load(image.with_suffix(".json"), {})))


def http_control(h):
    token = cfg().get("upload_token") or ""
    if len(token) < 20 or not hmac.compare_digest(h.headers.get("X-Fanding-Token", "").encode(), token.encode()):
        return h.send(403, {"error": "bad_token"})
    try:
        expected = last_session_date().isoformat()
        ready = sheet_ready(load(STATE, {}).get("sheets", {}).get(expected))
        if h.command == "POST":
            n = int(h.headers.get("Content-Length", "0"))
            if not 0 < n <= 4096:
                return h.send(400, {"error": "bad_size"})
            d = json.loads(h.rfile.read(n))
            stages = {"idle", "connecting", "listing", "images", "uploading", "parsing", "history", "sent", "daily_done", "daily_stopped", "logged_out", "no_posts", "no_image", "error", "server_error"}
            if not isinstance(d, dict) or d.get("stage") not in stages:
                return h.send(400, {"error": "bad_stage"})
            with bridge_state() as b:
                b["pc"] = {"at": time.time(), "stage": d["stage"], "version": str(d.get("version", ""))[:20],
                           "request_id": str(d.get("request_id", ""))[:32],
                           "mode": str(d.get("mode", ""))[:10],
                           "run_path": str(d.get("run_path", ""))[:240]}
                req = b.get("request") or {}
                # A PC started after the morning request expired must not idle forever.
                if (d.get("want_scan") is True and not ready
                        and (req.get("expected") != expected or time.time() - req.get("at", 0) > 1800)):
                    b["request"] = {"id": uuid.uuid4().hex, "at": time.time(),
                                    "expected": expected, "reason": "pc_start"}
        with bridge_state() as b:
            req = b.get("request") or {}
            active = req if time.time() - req.get("at", 0) <= 1800 else None
        expected = last_session_date().isoformat()
        sheet = load(STATE, {}).get("sheets", {}).get(expected) or {}
        ready = sheet_ready(sheet)
        return h.send(200, {"ok": True, "request": active, "expected": expected,
                            "ready": ready, "pending_images": pending_live_images()})
    except (ValueError, TypeError):
        return h.send(400, {"error": "bad_json"})
    except OSError:
        return h.send(500, {"error": "control_storage_failed"})


def diagnosis():
    b, st = load(BRIDGE, {}), load(STATE, {})
    pc = b.get("pc") or {}
    age = max(0, int(time.time() - pc.get("at", 0))) if pc.get("at") else None
    expected = last_session_date().isoformat()
    sh = st.get("sheets", {}).get(expected)
    stages = {"idle":"대기", "connecting":"사이트 접속", "listing":"글 목록 탐색", "images":"이미지 다운로드", "uploading":"서버 전송", "parsing":"서버 판독 대기", "history":"과거 자료 수집", "daily_done":"하루 작업 완료·PC 수집기 종료", "daily_stopped":"종료 시각 도달·자료 확인 필요", "sent":"전송 완료", "logged_out":"로그인 필요", "no_posts":"글 목록 없음", "no_image":"이미지 없음", "error":"PC 수집 오류", "server_error":"서버 연결/전송 오류"}
    lines = [f"🩺 팬딩 연결 진단 · v{VERSION}", f"필요 종가일: {expected} (월요일은 금요일 종가, 토요일 게시 가능)",
             "윈도우 연결: " + (f"{age}초 전" if age is not None else "새 수집기 연결 기록 없음"),
             "PC 단계: " + stages.get(pc.get("stage"), "미확인"),
             "PC 수집기 버전: " + str(pc.get("version") or "미확인"),
             "PC 실행 파일: " + str(pc.get("run_path") or "미확인(구버전 또는 미연결)"),
             "당일분 가격표: " + (str(sh.get("status")) if sh else "미확보"),
             f"수신함 대기: {len(list(INBOX.glob('*.img')))}장",
             "최근 서버 수신: " + str((b.get("last_received") or {}).get("at", "미확인"))]
    if age is None or age > 180:
        lines.append("확인 위치: 한국 PC 전원·작업 스케줄러·run.bat·서버 control 경로/통신")
        if age is None:
            lines.append("연결 기록이 없으면 구형 수집기 또는 /api/fanding/control 미연결 가능. PC 꺼짐으로 단정할 수 없습니다.")
    lines.append("재접속 요청: /재판독 · 서버는 PC 전원을 켜거나 로그인을 대신할 수 없습니다.")
    return "\n".join(lines)


def recovery_tick(tg):
    now = now_kst()
    auto_window = now.weekday() < 5 and 8 <= now.hour < 12
    latest_request = load(BRIDGE, {}).get("request") or {}
    manual = latest_request.get("reason") == "manual" and time.time() - latest_request.get("at", 0) < 1800
    if not auto_window and not manual:
        return
    expected = last_session_date(now).isoformat()
    st = load(STATE, {})
    sheet = st.get("sheets", {}).get(expected)
    missing = not sheet_ready(sheet)
    b = load(BRIDGE, {})
    pc = b.get("pc") or {}
    req = b.get("request") or {}
    if auto_window and missing and time.time() - req.get("at", 0) >= 1800:
        request_scan("missing")
    problem = None
    active_limit = 900 if pc.get("stage") in ("connecting", "listing", "images", "uploading", "history", "parsing") else 180
    if not pc.get("at") or time.time() - pc["at"] > active_limit:
        problem = "PC 연결 확인 안 됨: run.bat·스케줄러·서버 control 경로/통신 확인 (PC 전원 꺼짐으로 단정하지 않음)"
    elif pc.get("stage") in ("logged_out", "no_posts", "no_image", "error", "server_error", "daily_stopped"):
        problem = "윈도우 단계 실패: " + pc["stage"] + " · /진단 확인"
    attempt = st.get("vision_last_attempt") or {}
    if missing and attempt.get("date") == now.date().isoformat() and not attempt.get("ok"):
        problem = "서버 AI 판독 실패: /판독 에서 제공자별 오류 확인"
    if (missing or manual) and problem:
        key = now.date().isoformat() + ":" + problem
        with bridge_state() as control:
            if control.get("alert_key") == key:
                return
            control["alert_key"] = key
        tg.send("⚠️ <b>팬딩 자료 누락 진단</b>\n" + html.escape(problem) + "\n필요 종가일: " + expected + "\n재접속·재수집 요청은 자동 등록됩니다. /재판독 으로도 요청 가능")


def vision_status():
    st = load(STATE, {})
    today = now_kst().date().isoformat()
    v, attempt = st.get("vision_today") or {}, st.get("vision_last_attempt") or {}
    names = {"gemini": "Gemini", "deepseek": "DeepSeek"}
    lines = [f"🔎 팬딩 판독 상태 · v{VERSION}"]
    if v.get("date") == today:
        lines.append("오늘 1차 판독 성공: " + names.get(v.get("provider"), "확인 필요"))
    else:
        lines.append("오늘 1차 판독 성공 기록 없음 (이미지 미수신·중복·실패 가능)")
    if attempt.get("date") == today:
        lines.append("최근 시도: " + str(attempt.get("at", "")) + (" · 성공" if attempt.get("ok") else " · 실패"))
        if attempt.get("errors"):
            lines.append("최근 시도 오류: " + html.escape(" / ".join(attempt["errors"])))
    elif v.get("date"):
        lines.append("마지막 1차 성공일: " + html.escape(str(v["date"])))
    pending = list(INBOX.glob("*.img"))
    lines.append(f"수신함 대기: {len(pending)}장")
    lines.append("기본 순서: " + " → ".join(names.get(p, p) for p in cfg()["vision_order"]))
    return "\n".join(lines)


def read_and_judge(img_bytes):
    """한 번에 '가격표인지 + 숫자 읽기'. (AI판정, 읽은 값, 이유)"""
    prompt = (CLASSIFY_PROMPT + "\n\n가격표가 맞으면 is_price_sheet=true 로 하고 아래 지시대로 숫자를 옮기세요. "
              "아니면 is_price_sheet=false, 숫자 칸은 0 이나 빈 배열로 두세요.\n\n" + PROMPTS[0])
    r = vision(img_bytes, prompt, COMBINED_SCHEMA)
    flag = r.get("is_price_sheet")
    flag = flag if isinstance(flag, bool) else str(flag).strip().lower() in ("true", "yes", "1")
    return flag, normalize(r), str(r.get("reason") or "")[:120]


def judge_sheet(flag, parsed, market=None):
    """가격표로 인정할지. AI 판정 + 숫자 모양 + (있으면) 메리츠 종가 대조"""
    looks = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", parsed.get("close_date") or "")) and (parsed.get("close") or 0) > 0 \
        and bool(parsed.get("buys") or parsed.get("sells"))
    strong = False
    if looks and market and market.get("price"):
        refs = [x for x in (market.get("price"), market.get("prev_close")) if x]
        strong = parsed["close_date"] == last_session_date().isoformat() and \
            any(abs(parsed["close"] - x) / x <= 0.005 for x in refs)
    return (flag and looks) or strong, strong


def is_price_sheet(img_bytes):
    r = vision(img_bytes, CLASSIFY_PROMPT, CLASSIFY_SCHEMA, 512)
    return bool(r.get("is_price_sheet")), str(r.get("reason") or "")[:120]


def gemini_read(img_bytes, prompt, avoid=""):
    return normalize(vision(img_bytes, prompt, SCHEMA, avoid=avoid))


def normalize(p):
    def rows(lst):
        out = []
        for r in lst or []:
            try:
                price, qty = round(float(r["price"]), 4), int(r["qty"])
            except (KeyError, TypeError, ValueError):
                continue
            if price > 0 and qty > 0:
                out.append({"price": price, "qty": qty})
        return out
    date = str(p.get("close_date", "")).strip()
    m = re.search(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", date)
    date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else date
    num = lambda k: round(float(p[k]), 4) if p.get(k) not in (None, "") else None
    return {"close_date": date, "close": num("close"), "avg_price": num("avg_price"),
            "holding_qty": int(p["holding_qty"]) if p.get("holding_qty") not in (None, "") else None,
            "cycle": str(p.get("cycle") or ""), "buys": rows(p.get("buys")), "sells": rows(p.get("sells")),
            "extra": {k: p.get(k) for k in ("cycle_start_date", "prev_trade_qty", "cycle_start_usd", "cash_usd",
                                            "realized_today_usd", "cycle_realized_usd", "total_return_pct",
                                            "total_realized_usd") if p.get(k) not in (None, "")}}


def log_history(kind, data):
    """매매 규칙 분석용 영구 기록 (한 줄 = 한 사건). 실패해도 매매에는 영향 없음"""
    try:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY, "a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": kind, "at": now_kst().isoformat(), **data}, ensure_ascii=False) + "\n")
    except Exception as e:
        print("기록 실패:", e, flush=True)


def core(p):
    return (p["close_date"], p["close"], tuple((r["price"], r["qty"]) for r in p["buys"]),
            tuple((r["price"], r["qty"]) for r in p["sells"]))


# ---------------------------------------------------------- 안전점검
def run_checks(sheet, mult, market=None):
    """[(통과?, 설명)] 과 자동주문 가능 여부. market = {'price','prev_close','holding','sellable','exch_id'}"""
    c = cfg()
    p = sheet["parsed"]
    out = []
    add = lambda ok, msg: out.append({"ok": bool(ok), "msg": msg})

    add(sheet.get("reads_agree"), "AI 두 번 판독 결과 일치" if sheet.get("reads_agree")
        else "AI 두 번 판독 결과가 다르거나 확인 판독 실패 → 숫자 꼭 확인")
    exp = last_session_date().isoformat()
    add(p["close_date"] == exp, f"종가날짜 {p['close_date']} (오늘 기대값 {exp})")
    if not p["buys"] and not p["sells"]:
        add(False, "주문 줄을 하나도 못 읽음")
    close = p.get("close") or 0
    if market and market.get("price"):
        refs = [x for x in (market["price"], market.get("prev_close")) if x]
        ok = close and any(abs(close - x) / x <= 0.003 for x in refs)
        add(ok, f"표의 종가 {close} ↔ 메리츠 시세 {' / '.join(str(x) for x in refs)}")
    else:
        add(False, "메리츠 시세 확인 실패 → 종가 대조 못 함")
    if close:
        bad_b = [r for r in p["buys"] if not 0.80 * close <= r["price"] <= 1.10 * close]
        bad_s = [r for r in p["sells"] if not 0.90 * close <= r["price"] <= 2.0 * close]
        add(not bad_b, "매수가 범위 정상 (종가 -20%~+10%)" if not bad_b else f"이상한 매수가: {bad_b}")
        add(not bad_s, "매도가 범위 정상 (종가 -10%~+100%)" if not bad_s else f"이상한 매도가: {bad_s}")
    bad_q = [r for r in p["buys"] + p["sells"] if not 1 <= r["qty"] <= 500]
    add(not bad_q, "개수 범위 정상" if not bad_q else f"이상한 개수: {bad_q}")
    buy_total = sum(r["price"] * r["qty"] * mult for r in p["buys"])
    add(buy_total <= float(c["max_buy_usd"]), f"매수 총액 {fmt_money(buy_total)} (한도 {fmt_money(float(c['max_buy_usd']))})")
    sell_qty = sum(r["qty"] * mult for r in p["sells"])
    if market and market.get("sellable") is not None:
        add(sell_qty <= market["sellable"], f"매도 합계 {sell_qty}주 ≤ 매도가능 {market['sellable']}주")
    elif sell_qty:
        add(False, "메리츠 잔고 확인 실패 → 매도 수량 대조 못 함")
    if market and market.get("holding") is not None and p.get("holding_qty"):
        add(True, f"참고: 표 보유 {p['holding_qty']}×{mult}={p['holding_qty'] * mult}주 / 내 계좌 {market['holding']}주")
    if not (cfg().get("exch_id") or (market or {}).get("exch_id")):
        add(False, "거래소 번호를 모름 (설정 exch_id 필요)")
    auto_ok = all(x["ok"] for x in out)
    return out, auto_ok


def account_snapshot(client=None):
    snap = {"account_at": now_kst().isoformat()}
    try:
        if client is None:
            from meritz_client import Meritz
            client = Meritz()
    except Exception:
        return snap
    try:
        hold, sellable, exch, avg = client.holding(cfg()["symbol"])
        snap.update(holding=hold, sellable=sellable, exch_id=exch, avg=avg)
    except Exception:
        pass
    try:
        snap["usd_cash"] = client.usd_cash()
    except Exception:
        pass
    return snap


def account_lines(sheet, snapshot=None):
    from decimal import Decimal, InvalidOperation
    market = (sheet.get("market") or {}) if snapshot is None else snapshot
    def number(value):
        try:
            if value is None or isinstance(value, bool): return None
            n = Decimal(str(value))
            return n if n.is_finite() else None
        except (InvalidOperation, ValueError):
            return None
    mult = number(sheet.get("mult"))
    need = sum((Decimal(str(price)) * qty for side, price, qty in order_lines(sheet) if side == "buy"), Decimal(0))
    cash = number(market.get("usd_cash"))
    gap = max(Decimal(0), need - cash) if cash is not None else None
    lines = ["\n💵 <b>매수 자금 참고</b>",
             "▫️ 보유 달러(예수금): " + (f"${cash:,.2f}" if cash is not None else "조회 불가"),
             f"▫️ 표 매수 필요 달러: ${need:,.2f}",
             "▫️ 환전 필요 달러(부족 추정): " + (f"${gap:,.2f}" if gap is not None else "계산 보류"),
             "▫️ 표의 매수 총액 기준·수수료 별도·예약/체결 후 추가 환전액 아님"]
    if market.get("account_at"):
        lines.append("▫️ 계좌 조회: " + html.escape(str(market["account_at"])))
    target = number(sheet["parsed"].get("holding_qty"))
    actual = number(market.get("holding"))
    lines.append("\n📦 <b>보유 수량 비교</b> (표 기준·계좌 조회 시점)")
    if target is None or mult is None or actual is None:
        lines.append("▫️ 차이 계산 보류: 표 보유 개수 또는 계좌 수량 확인 필요")
    else:
        expected = target * mult
        difference = actual - expected
        lines.append(f"▫️ 표 {target:g}주 × {mult:g} = {expected:g}주 / 실제 {actual:g}주")
        lines.append("▫️ 차이: " + (f"{difference:+g}주 (실제 보유가 {abs(difference):g}주 {'많음' if difference > 0 else '적음'})" if difference else "0주 (일치)"))
    return lines


def market_snapshot():
    """메리츠에서 시세·잔고. 실패해도 None 대신 부분 정보"""
    c = cfg()
    snap = {}
    try:
        from meritz_client import Meritz
        m = Meritz()
    except Exception as e:
        snap["error"] = f"메리츠 설정 오류: {e}"; return snap
    try:
        pr = m.price(c["symbol"], c["price_market"])
        snap.update(price=pr["price"], prev_close=pr["prev_close"])
    except Exception as e:
        snap["error"] = f"시세: {e}"
    try:
        hold, sellable, exch, avg = m.holding(c["symbol"])
        snap.update(holding=hold, sellable=sellable, exch_id=exch, avg=avg)
    except Exception as e:
        snap["error"] = (snap.get("error", "") + f" / 잔고: {e}").strip(" /")
    try:
        snap["usd_cash"] = m.usd_cash()
    except Exception:
        pass
    snap["account_at"] = now_kst().isoformat()
    return snap


# ---------------------------------------------------------- 알림 만들기
def deadlines(sheet):
    c = cfg()
    us = datetime.strptime(sheet["us_date"], "%Y%m%d").date()
    h, m = hm(c["cutoff_et"])
    cutoff = datetime(us.year, us.month, us.day, h, m, tzinfo=ET).astimezone(KST)
    return (cutoff - timedelta(minutes=int(c["alarm_before_min"])),
            cutoff - timedelta(minutes=int(c["auto_before_min"])), cutoff)


def order_lines(sheet):
    mult = sheet["mult"]
    p = sheet["parsed"]
    return ([("buy", r["price"], r["qty"] * mult) for r in p["buys"]] +
            [("sell", r["price"], r["qty"] * mult) for r in p["sells"]])


def sheet_text(sheet, head="📋 <b>팬딩 가격표 도착</b>"):
    c = cfg()
    p, mult = sheet["parsed"], sheet["mult"]
    alarm, auto, cutoff = deadlines(sheet)
    us = datetime.strptime(sheet["us_date"], "%Y%m%d")
    L = [head, f"▫️ {c['symbol']} · {html.escape(p['close_date'])} 종가 {p['close']} · {html.escape(p.get('cycle') or '')}",
         f"▫️ 배수 <b>×{mult}</b> · 주문일(미국) {us:%m/%d} · Limit VWAP 예약 · <b>{RESERVE_NAMES.get(str(c.get('reserve_time', '2')), '')} 발주</b>"]
    for side, price, qty in order_lines(sheet):
        L.append(f"{'🔴 매수' if side == 'buy' else '🔵 매도'} <b>{price:g} × {qty}</b>"
                 f"  <i>(표 {qty // mult})</i>  {fmt_money(price * qty)}")
    bad = [x for x in sheet["checks"] if not x["ok"]]
    if bad:
        L.append("\n⚠️ <b>확인 필요</b>")
        L += [f"  · {html.escape(x['msg'])}" for x in bad]
    else:
        L.append("\n✅ 안전점검 모두 통과")
    sub = datetime(*now_kst().timetuple()[:3], *hm(c["submit_kst"]), tzinfo=KST)
    L.append(f"\n⏱ 주문 접수: 승인 후 {('지금 바로' if now_kst() >= sub else c['submit_kst'] + ' 이후')}")
    if c["auto_order"]:
        L.append(f"⏰ 마감 {alarm:%m/%d %H:%M} 알림 → {auto:%H:%M} " +
                 ("자동주문" if sheet["auto_ok"] else "<b>자동주문 안 함</b>(점검 미통과)"))
    else:
        L.append(f"⏰ 마감 {cutoff:%m/%d %H:%M} (자동주문 꺼짐)")
    L += account_lines(sheet)
    return "\n".join(L)


def sheet_rows(sheet):
    k = f"{sheet['date']}:{sheet['ver']}"
    return [[{"text": "✅ 주문", "callback_data": f"fd:ok:{k}"}, {"text": "❌ 이번엔 안 함", "callback_data": f"fd:no:{k}"}]]


def sheet_notice_time(sheet):
    """판독 결과와 주문 버튼은 해당 주문일 한국시간 09:00부터 발송."""
    day = datetime.strptime(sheet["us_date"], "%Y%m%d")
    return day.replace(hour=9, minute=0, second=0, microsecond=0, tzinfo=KST)


def send_sheet_alert(tg, sheet, head="📋 <b>팬딩 가격표 도착</b>"):
    sheet["notice_not_before"] = sheet_notice_time(sheet).isoformat()
    sheet["notice_head"] = head
    if now_kst() < sheet_notice_time(sheet):
        # 원본 이미지·판독 결과·점검·배수는 기존 state에 저장한다.
        # tick에서 발송하므로 PC가 작업을 마치거나 서버가 재시작해도 유지된다.
        sheet["notice_pending"] = True
        return False
    tg.clear_buttons(sheet.get("msg_id"))
    img = IMAGES / (sheet.get("img") or "_none_")
    text = sheet_text(sheet, head)
    if img.is_file() and len(text.encode("utf-16-le")) // 2 > 950:
        tg.photo(img, head)
        res = tg.send(text, sheet_rows(sheet))
    else:
        res = tg.photo(img, text, sheet_rows(sheet)) if img.is_file() else tg.send(text, sheet_rows(sheet))
    sheet["msg_id"] = (res or {}).get("message_id")
    sheet["notice_pending"] = not bool(sheet["msg_id"])
    if not sheet["notice_pending"]:
        sheet["notice_sent_at"] = now_kst().isoformat()
    return not sheet["notice_pending"]


# ---------------------------------------------------------- 새 가격표 처리
def process_inbox(tg):
    INBOX.mkdir(parents=True, exist_ok=True)
    try:   # VR6 자료는 따로 처리 (오류가 나도 P 가격표 처리는 계속)
        import fanding_vr6
        fanding_vr6.process_inbox(tg)
    except Exception as e:
        print("VR6 수신 처리 오류:", type(e).__name__, e, flush=True)
    for f in sorted(INBOX.glob("*.note")):
        tg.send("🖥 <b>윈도우 PC (팬딩)</b>\n" + html.escape(f.read_text(encoding="utf-8", errors="replace")[:300]))
        f.unlink(missing_ok=True)
    for f in sorted(INBOX.glob("*.img")):
        mf = f.with_suffix(".json")
        meta = load(mf, {})
        if meta.get("kind") == "vr6":
            continue                                  # VR6 이미지는 fanding_vr6 가 처리 (P 판독 대상 아님)
        if meta.get("retry_at", 0) > time.time():
            continue                                  # 잠시 뒤 다시 시도할 이미지
        data = f.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        try:
            kind = handle_history_image(data, sha, meta) if meta.get("mode") == "history" else handle_image(tg, data, sha, meta)
        except Exception as e:
            n = int(meta.get("tries", 0)) + 1
            print(f"가격표 처리 오류({n}번째):", type(e).__name__, e, flush=True)
            if n == 1 and meta.get("mode") != "history":
                tg.send("⚠️ <b>팬딩 서버 판독 단계 실패</b>\n이미지 수신은 완료됐지만 AI 처리 실패. 2분 뒤 재시도합니다. /판독 · /진단 확인")
            if n < 5:                                 # 2분 뒤 다시 (Gemini 일시 장애 대비)
                meta.update(tries=n, retry_at=time.time() + 120, last_error=str(e)[:200])
                mf.write_text(json.dumps(meta, ensure_ascii=False))
                continue
            kind = "error"
            if meta.get("mode") != "history":
                tg.send(f"🚨 <b>팬딩 가격표 처리 실패</b> (5번 시도)\n{html.escape(str(e))[:300]}\n"
                        "윈도우 PC에서 <code>py fanding_fetch.py send</code> 로 다시 보내거나 가격표를 직접 확인해 주세요.")
        f.unlink(missing_ok=True)
        mf.unlink(missing_ok=True)
        if meta.get("mode") != "history":
            batch_done(tg, meta, kind)


def handle_history_image(data, sha, meta):
    """과거 가격표: 알림·주문 없이 기록만 (Gemini 판독 1번)"""
    with locked_state() as st:
        known = st.setdefault("kinds2", {})
        if known.get(sha):
            return known[sha]
    flag, parsed, why = read_and_judge(data)
    ok, _ = judge_sheet(flag, parsed)
    kind = "sheet" if ok else "other"
    if ok:
        log_history("past_sheet", {"date": parsed.get("close_date"), "parsed": parsed, "post": meta.get("post", "")})
    with locked_state() as st:
        st["kinds2"][sha] = kind
        st["kinds2"] = dict(list(st["kinds2"].items())[-800:])
        if ok:
            st["past_count"] = int(st.get("past_count", 0)) + 1
    return kind


def batch_done(tg, meta, kind):
    """윈도우가 한 글의 이미지 n장을 묶어 보냄 → 다 처리했는데 가격표가 없으면 알림"""
    bid, n = meta.get("batch"), int(meta.get("count") or 0)
    if not bid or n <= 0:
        return
    with locked_state() as st:
        b = st.setdefault("batches", {}).setdefault(bid, {"n": n, "done": 0, "kinds": [], "at": time.time()})
        b["done"] += 1
        b["kinds"].append(kind)
        if b["done"] >= b["n"]:
            st["batches"].pop(bid, None)
            if "wrong_date" in b["kinds"] and not any(k in ("sheet", "sheet_dup") for k in b["kinds"]):
                tg.send("⚠️ 최근 글 판독 완료: 필요한 종가일의 가격표를 아직 찾지 못했습니다. /진단 확인 · 다음 자동 재접속에서 재확인합니다.")
            elif not any(k in ("sheet", "sheet_dup", "error") for k in b["kinds"]):
                tg.send(f"❓ <b>팬딩 글에서 가격표를 못 찾았어요</b>\n이미지 {b['n']}장을 확인했지만 모두 가격표가 아니었어요."
                        f"\n글: {html.escape(meta.get('post', ''))[:200]}\n가격표가 다른 글에 올라왔는지 확인해 주세요.")
        for k in [k for k, v in st["batches"].items() if time.time() - v.get("at", 0) > 86400]:
            st["batches"].pop(k, None)


def handle_image(tg, data, sha, meta):
    """돌려주는 값: sheet(새 가격표) / sheet_dup(이미 받은 가격표) / other(가격표 아님)"""
    with locked_state() as st:
        known = st.setdefault("kinds2", {})
        recorded = next((sh for sh in st["sheets"].values() if sh.get("sha") == sha), None)
        retry_incomplete = bool(meta.get("request_id") and recorded and recorded.get("status") == "pending"
                                and recorded.get("reads_agree") is False)
        if (sha in st.get("seen", []) or known.get(sha) == "sheet") and not retry_incomplete:
            print("이미 받은 가격표 → 무시", flush=True); return "sheet_dup"
        if known.get(sha) == "other" and not meta.get("request_id"):
            return "other"
    market = market_snapshot()
    flag, first, why = read_and_judge(data)
    first_ai = LAST_PROVIDER["name"]
    ok, strong = judge_sheet(flag, first, market)
    print(f"판별: AI={flag} 날짜·종가일치={strong} → {'가격표' if ok else '아님'} ({why})", flush=True)
    if not ok:
        with locked_state() as st:
            st["kinds2"][sha] = "other"
            st["kinds2"] = dict(list(st["kinds2"].items())[-500:])
        return "other"
    expected = meta.get("expected")
    if expected and first.get("close_date") != expected:
        tg.send("ℹ️ 재수집 이미지 종가일 불일치: " + html.escape(str(first.get("close_date"))) + " / 필요 " + html.escape(expected) + " · 주문에 사용하지 않음")
        return "wrong_date"
    try:
        second = gemini_read(data, PROMPTS[1], avoid=first_ai)
        print(f"교차 확인: 1차 {first_ai} · 2차 {LAST_PROVIDER['name']}", flush=True)
    except Exception as e:          # 확인용 판독 실패 → 가격표는 알리되 자동주문은 막음
        print("확인용 두 번째 판독 실패:", e, flush=True)
        second = dict(first, close=-1)
    reads = [first, second]
    agree = core(reads[0]) == core(reads[1])
    parsed = reads[0]
    IMAGES.mkdir(parents=True, exist_ok=True)
    img_name = f"{parsed['close_date'] or 'unknown'}_{sha[:8]}.jpg"
    (IMAGES / img_name).write_bytes(data)
    with locked_state() as st:
        st["seen"] = (st.get("seen", []) + [sha])[-60:]
        st.setdefault("kinds2", {})[sha] = "sheet"
        date = parsed["close_date"]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date or ""):
            tg.send("🚨 가격표에서 날짜를 못 읽었어요. 주문하지 않습니다. 직접 확인해 주세요.")
            return "sheet"
        old = st["sheets"].get(date)
        if old and old["status"] in ("submitted", "partial", "submitting"):
            tg.send(f"⚠️ <b>{date} 가격표가 바뀐 것 같아요</b> (이미 주문 접수 후)\n자동으로 고치지 않았어요. 앱에서 직접 확인해 주세요.")
            return "sheet"
        sd = datetime.strptime(date, "%Y-%m-%d").date()
        sheet = {"date": date, "img": img_name, "sha": sha, "parsed": parsed, "reads": reads, "reads_agree": agree,
                 "market": market, "mult": int(st["multiplier"]), "status": "pending", "ver": (old or {}).get("ver", 0) + 1,
                 "us_date": next_session_date(sd).strftime("%Y%m%d"), "received": now_kst().isoformat(),
                 "post": meta.get("post", ""), "orders": [], "alarm_sent": False, "msg_id": (old or {}).get("msg_id")}
        sheet["checks"], sheet["auto_ok"] = run_checks(sheet, sheet["mult"], market)
        log_history("sheet", {"date": date, "parsed": parsed, "reads_agree": agree, "market": market,
                              "mult": sheet["mult"], "us_date": sheet["us_date"], "post": sheet["post"], "img": img_name})
        if old and old["status"] == "cancelled":
            sheet["status"] = "cancelled"
        st["sheets"][date] = sheet
        for k in sorted(st["sheets"])[:-20]:
            st["sheets"].pop(k, None)
        head = "📋 <b>팬딩 가격표가 바뀌었어요 (새 숫자)</b>" if old else "📋 <b>팬딩 가격표 도착</b>"
        if sheet["status"] == "pending":
            send_sheet_alert(tg, sheet, head)
    return "sheet"


# ---------------------------------------------------------- 주문 접수
def submit(tg, sheet, confirm_warn=False):
    from meritz_client import Meritz, WarnNeeded
    c = cfg()
    m = Meritz()
    exch = c.get("exch_id") or (sheet.get("market") or {}).get("exch_id")
    if not exch:
        exch = market_snapshot().get("exch_id")
    if not exch:
        raise RuntimeError("거래소 번호(exch_id)를 몰라 주문 못 함 → /etc/bot-office/fanding.json 에 exch_id 설정")
    done = {(o["side"], o["price"], o["qty"]) for o in sheet["orders"] if o.get("no")}
    results = []
    for side, price, qty in order_lines(sheet):
        if (side, price, qty) in done:
            continue
        o = {"side": side, "price": price, "qty": qty, "at": now_kst().isoformat()}
        try:
            r = m.reserve(side, c["symbol"], exch, qty, price, sheet["us_date"], confirm_warn=confirm_warn,
                          hour_code=str(c.get("reserve_time", "2")))
            o["no"] = r["no"]
            o["rsv_date"] = now_kst().strftime("%Y%m%d")
            o["hour"] = str(c.get("reserve_time", "2"))
        except WarnNeeded as e:
            o["warn"] = str(e)
        except Exception as e:
            o["err"] = str(e)
        sheet["orders"] = [x for x in sheet["orders"] if (x["side"], x["price"], x["qty"]) != (side, price, qty)] + [o]
        results.append(o)
        time.sleep(0.3)
    ok = all(o.get("no") for o in sheet["orders"]) and len(sheet["orders"]) == len(order_lines(sheet))
    sheet["status"] = "submitted" if ok else "partial"
    log_history("orders", {"date": sheet["date"], "us_date": sheet["us_date"], "mult": sheet["mult"],
                           "by": sheet.get("approved_by"), "orders": sheet["orders"]})
    L = [f"{'✅' if ok else '⚠️'} <b>메리츠 예약주문 {'완료' if ok else '일부 실패'}</b> · {sheet['date']} 가격표"
         f" · {'자동' if sheet.get('approved_by') == 'auto' else '승인'}"]
    for o in sheet["orders"]:
        tag = f"접수 #{o['no']}" if o.get("no") else (f"⚠️ 증권사 경고: {o['warn']}" if o.get("warn") else f"❌ {o.get('err')}")
        L.append(f"{'🔴 매수' if o['side'] == 'buy' else '🔵 매도'} {o['price']:g} × {o['qty']} → {html.escape(str(tag))[:200]}")
    rows = None
    if any(o.get("warn") for o in sheet["orders"]):
        L.append("\n증권사 '주문 착오 방지' 경고예요. 숫자가 맞으면 아래 버튼으로 경고 확인 후 다시 넣어요.")
        rows = [[{"text": "⚠️ 경고 확인하고 주문", "callback_data": f"fd:wy:{sheet['date']}:{sheet['ver']}"}]]
    elif not ok:
        rows = [[{"text": "🔁 실패한 것만 다시", "callback_data": f"fd:re:{sheet['date']}:{sheet['ver']}"}]]
    L += account_lines(sheet, account_snapshot(m))
    tg.send("\n".join(L), rows)


# ---------------------------------------------------------- 시간표 처리
def cleanup_images(st):
    """처리가 끝난 가격표 이미지는 서버에서 지움 (텔레그램 알림에 원본이 남아 있음). 남은 것도 3일 지나면 삭제"""
    done = ("submitted", "cancelled", "skipped", "expired")
    for sh in st["sheets"].values():
        if sh.get("img") and sh["status"] in done:
            (IMAGES / sh["img"]).unlink(missing_ok=True)
            sh["img"] = ""
    if IMAGES.exists():
        for f in IMAGES.glob("*"):
            if time.time() - f.stat().st_mtime > 3 * 86400:
                f.unlink(missing_ok=True)


def tick(tg):
    c = cfg()
    now = now_kst()
    sub_h, sub_m = hm(c["submit_kst"])
    with locked_state() as st:
        for date, sh in st["sheets"].items():
            if sh["status"] not in ("pending", "approved", "retry", "retry_warn"):
                continue
            alarm, auto, cutoff = deadlines(sh)
            if now >= cutoff:
                if sh["status"] != "pending":
                    tg.send(f"❌ {date} 가격표: 예약 마감({cutoff:%H:%M})이 지나 주문을 못 넣었어요.")
                else:
                    tg.send(f"ℹ️ {date} 가격표: 마감이 지나 이번 주문은 넘어갑니다.")
                tg.clear_buttons(sh.get("msg_id"))
                sh["status"] = "expired"
                continue
            if sh["status"] == "pending" and sh.get("notice_pending") and now >= sheet_notice_time(sh):
                send_sheet_alert(tg, sh, sh.get("notice_head") or "📋 <b>팬딩 가격표 도착</b>")
            if sh["status"] == "pending" and c["auto_order"]:
                if now >= auto:
                    tg.clear_buttons(sh.get("msg_id"))
                    if sh["auto_ok"]:
                        sh["status"], sh["approved_by"] = "approved", "auto"
                        tg.send(f"🤖 <b>버튼이 안 눌려 자동주문 진행</b> · {date} 가격표 (점검 모두 통과)")
                    else:
                        sh["status"] = "skipped"
                        bad = "\n".join("  · " + html.escape(x["msg"]) for x in sh["checks"] if not x["ok"])
                        tg.send(f"⛔ <b>자동주문 안 함</b> · {date} 가격표\n안전점검을 통과 못 했어요:\n{bad}\n"
                                "필요하면 메리츠 앱에서 직접 주문해 주세요.")
                    continue
                if now >= alarm and not sh.get("alarm_sent"):
                    sh["alarm_sent"] = True
                    left = int((auto - now).total_seconds() // 60)
                    tg.send(f"⏰ <b>주문 확인 마감 30분 전</b> · {date} 가격표\n"
                            f"{left}분 뒤({auto:%H:%M}) " + ("자동주문합니다." if sh["auto_ok"] else "점검 미통과라 자동주문 안 합니다.")
                            + "\n지금 결정하려면 아래 버튼을 눌러 주세요.", sheet_rows(sh))
                    continue
            if sh["status"] in ("approved", "retry", "retry_warn") and (now.hour, now.minute) >= (sub_h, sub_m):
                warn = sh["status"] == "retry_warn"
                sh["status"] = "submitting"
                save(STATE, st)
                try:
                    submit(tg, sh, confirm_warn=warn)
                except Exception as e:
                    sh["status"] = "partial"
                    tg.send(f"🚨 <b>주문 접수 오류</b> · {date}\n{html.escape(str(e))[:400]}",
                            [[{"text": "🔁 다시 시도", "callback_data": f"fd:re:{date}:{sh['ver']}"}]])
        # 가격표가 안 오는 날 알림: 미국 장 다음 날 한국 오전, 정해진 시각까지 안 오면 1번만
        exp = last_session_date(now)
        key = f"missing:{exp.isoformat()}"
        due = exp + timedelta(days=3 if exp.weekday() == 4 else 1)   # 금요일 가격표는 월요일 아침에 받음
        if (exp.isoformat() not in st["sheets"] and now.date() == due
                and (now.hour, now.minute) >= hm(c["missing_alert_kst"]) and not st.get(key)):
            st[key] = True
            tg.send(f"❓ <b>{exp.isoformat()} 가격표가 아직 안 왔어요</b> ({c['missing_alert_kst']} 기준)\n"
                    "윈도우 PC가 켜져 있는지, 팬딩 로그인이 풀리지 않았는지 확인해 주세요. (휴장일이면 무시)")
        for k in sorted(k for k in st if k.startswith("missing:"))[:-10]:
            st.pop(k, None)
        cleanup_images(st)


def loop():
    tg = TG()
    print(f"팬딩 가격표 담당 v{VERSION} 시작", flush=True)
    with locked_state() as st:   # 접수 도중 꺼졌던 건은 '일부 실패'로 돌려 다시 시도 버튼이 보이게
        for d, sh in st["sheets"].items():
            if sh["status"] == "submitting":
                sh["status"] = "partial"
                tg.send(f"⚠️ {d} 가격표 주문 접수 도중 프로그램이 다시 켜졌어요. 메리츠 앱에서 접수 여부를 확인해 주세요.",
                        [[{"text": "🔁 빠진 것만 다시", "callback_data": f"fd:re:{d}:{sh['ver']}"}]])
    if tg.own:
        print("팬딩 전용 텔레그램 봇 사용 (버튼·명령을 직접 받음)", flush=True)
        if not load(HOME / "tg_offset.json", {}).get("hello"):
            tg.send(f"👋 <b>팬딩 봇 연결 완료</b> (v{VERSION})\n앞으로 팬딩 가격표 알림·주문 버튼은 여기로 와요.\n" + HELP_TEXT)
            save(HOME / "tg_offset.json", {"hello": True})
    while True:
        try:
            process_inbox(tg)
            recovery_tick(tg)
            tick(tg)
        except Exception as e:
            print("루프 오류:", type(e).__name__, e, flush=True)
        try:
            import fanding_vr6
            fanding_vr6.tick(tg)
        except Exception as e:
            print("VR6 점검 오류:", type(e).__name__, e, flush=True)
        if tg.own:
            poll_own_bot(tg)          # 약 15초 동안 버튼·명령 기다림
        else:
            time.sleep(20)
        if _file_changed():   # 업데이트 비서가 새 코드를 넣으면 스스로 다시 시작
            print("새 코드 감지 → 다시 시작", flush=True)
            os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)] + sys.argv[1:])


HELP_TEXT = ("▫️ <b>/가격표</b> 최근 가격표·주문 상태\n▫️ <b>/배수</b> 현재 배수 · <b>/배수 6</b> 배수 바꾸기\n"
             "▫️ <b>/자동</b> 자동주문 상태 · <b>/자동켜기</b> · <b>/자동끄기</b>\n▫️ <b>/과거</b> 과거 가격표 수집 현황\n"
             "▫️ <b>/재판독</b> PC 사이트 재접속·최신 자료 요청 · <b>/진단</b> 단계별 상태\n"
             "▫️ <b>/판독</b> 오늘 쓰는 이미지 판독 AI (Gemini·DeepSeek)\n"
             "▫️ <b>/발주시간</b> 예약 발주 시간 보기·바꾸기 · <b>/재예약</b> 오늘 예약을 새 시간으로 다시\n"
             "▫️ <b>/재예약강제</b> 앱에서 직접 다 취소했을 때 취소 없이 새로 넣기")

# ---------------------------------------------------------- 버튼 메뉴 (5번 하단 버튼 · 7번 팬딩 메뉴 공용)
# 버튼은 기존 명령 글자와 똑같이 처리된다(새 기능이 아니라 같은 기능을 버튼으로 누르는 것).
MENU_ITEMS = [("pr", "📋 가격표", "/가격표"), ("mt", "📐 배수", "/배수"), ("au", "🤖 자동주문", "/자동"),
              ("rt", "⏱ 발주시간", "/발주시간"), ("rr", "🔁 재예약", "/재예약"), ("rs", "🔄 재판독", "/재판독"),
              ("dg", "🩺 진단", "/진단"), ("vi", "🧠 판독 AI", "/판독"), ("ps", "🗂 과거 수집", "/과거"),
              ("rf", "⚠️ 재예약 강제", "/재예약강제"), ("hp", "❓ 도움말", "/help")]
MENU_ALIAS = {label: cmd for _, label, cmd in MENU_ITEMS}
MENU_CMD = {key: cmd for key, _, cmd in MENU_ITEMS}


P_LABEL, VR6_LABEL, HOME_LABEL, ALL_HELP_LABEL = "🅿 P 메뉴", "🅥 VR6 메뉴", "🏠 메인 메뉴", "❓ 전체 도움말"


def main_keyboard():
    """/start 로 뜨는 첫 화면: P(기존 가격표 매매) / VR6(2주 1회)"""
    return [[{"text": P_LABEL}, {"text": VR6_LABEL}], [{"text": ALL_HELP_LABEL}]]


def menu_keyboard():
    """P 메뉴: 기존 11개 버튼 + 메인으로"""
    labels = [label for _, label, _ in MENU_ITEMS]
    return [[{"text": t} for t in labels[i:i + 3]] for i in range(0, len(labels), 3)] + [[{"text": HOME_LABEL}]]


def main_menu_text():
    return ("📋 <b>팬딩 봇</b>\n🅿 <b>P 메뉴</b> — 기존 가격표 자동 매매 (SOXL, 매일 가격표)\n"
            "🅥 <b>VR6 메뉴</b> — VR6기 (TQQQ, 2주에 한 번 표 수신)\n아래 버튼에서 골라 주세요.")


def _vr6_text(tg, t):
    """VR6 메뉴 글자·명령 처리. 오류가 나도 P 흐름은 계속"""
    try:
        import fanding_vr6
        return fanding_vr6.handle_text(tg, t)
    except Exception as e:
        print("VR6 명령 오류:", type(e).__name__, e, flush=True)
        tg.send("⚠️ VR6 처리 중 오류가 났어요. /vr6진단 으로 확인해 주세요.")
        return True


def menu_rows():
    return [[{"text": label, "callback_data": f"fm:{key}"} for key, label, _ in MENU_ITEMS[i:i + 2]]
            for i in range(0, len(MENU_ITEMS), 2)]


def mult_rows(cur):
    cb = lambda n: {"text": f"×{n}", "callback_data": f"fm:mt:{n}"}
    return [[{"text": "➖ 1", "callback_data": f"fm:mt:{max(1, cur - 1)}"}, {"text": f"현재 ×{cur}", "callback_data": "fm:noop"},
             {"text": "➕ 1", "callback_data": f"fm:mt:{min(50, cur + 1)}"}],
            [cb(n) for n in (1, 2, 3, 4, 5)], [cb(n) for n in (6, 7, 8, 10, 12)]]


def auto_rows(on):
    return [[{"text": ("✅ " if on else "") + "🟢 켜기", "callback_data": "fm:au:1"},
             {"text": ("" if on else "✅ ") + "🔴 끄기", "callback_data": "fm:au:0"}]]


def rt_rows(cur):
    btn = lambda k: {"text": ("✅ " if str(k) == str(cur) else "") + RESERVE_NAMES[str(k)], "callback_data": f"fm:rt:{k}"}
    return [[btn(0), btn(3)], [btn(2), btn(1)]]


def menu_text(tg_s, t):
    """버튼이 가리키는 명령 하나를 명령 글자와 똑같이 처리. 처리했으면 True"""
    if t in ("/판독", "판독"):
        tg_s.send(vision_status()); return True
    if t in ("/과거", "과거"):
        st = load(STATE, {})
        tg_s.send(f"🗂 과거 가격표 수집: <b>{st.get('past_count', 0)}개</b> 기록됨 (윈도우 PC가 하루 10개씩 보내요)"); return True
    if t in ("/help", "도움말"):
        tg_s.send("📋 <b>팬딩 봇 사용법</b>\n" + HELP_TEXT); return True
    return secretary_message(tg_s, t)


def poll_own_bot(tg):
    """팬딩 전용 봇의 버튼·명령 처리 (이 봇은 이 프로그램만 받으므로 충돌 없음)"""
    off = load(HOME / "tg_offset.json", {})
    try:
        ups = tg.updates(off.get("offset"))
    except Exception as e:
        print("텔레그램 받기 오류:", type(e).__name__, e, flush=True)
        time.sleep(5); return
    for u in ups:
        off["offset"] = u["update_id"] + 1
        try:
            if "callback_query" in u:
                cb = u["callback_query"]
                if str(((cb.get("message") or {}).get("chat") or {}).get("id")) == tg.chat:
                    secretary_callback(tg, cb)
            elif "message" in u:
                m = u["message"]
                if str((m.get("chat") or {}).get("id")) != tg.chat:
                    continue
                t = (m.get("text") or "").strip()
                t = MENU_ALIAS.get(t, t)   # 하단 버튼 글자 → 같은 명령
                if t.lower() in ("/start", "?", "메뉴", "/menu") or t in (HOME_LABEL, ALL_HELP_LABEL):
                    tg.send(main_menu_text(), keyboard=main_keyboard())
                elif t == P_LABEL or t.lower() == "/p":
                    tg.send("🅿 <b>P 메뉴</b> — 기존 가격표 자동 매매\n" + HELP_TEXT + "\n\n▫️ 아래 버튼으로도 모든 기능을 쓸 수 있어요.",
                            keyboard=menu_keyboard())
                elif t.lower() in ("/help", "도움말"):
                    tg.send("📋 <b>팬딩 봇 사용법 (P)</b>\n" + HELP_TEXT + "\n\n▫️ VR6 는 <b>/vr6</b> · 첫 화면은 <b>/start</b>",
                            keyboard=menu_keyboard())
                elif t in ("/판독", "판독"):
                    tg.send(vision_status())
                elif t in ("/재판독", "재판독", "/판독요청"):
                    tg.send(request_scan())
                elif t in ("/진단", "진단"):
                    tg.send(diagnosis())
                elif t in ("/과거", "과거"):
                    st = load(STATE, {})
                    tg.send(f"🗂 과거 가격표 수집: <b>{st.get('past_count', 0)}개</b> 기록됨 (윈도우 PC가 하루 10개씩 보내요)")
                elif _vr6_text(tg, t):
                    pass
                elif not secretary_message(tg, t):
                    tg.send("모르는 명령이에요. <b>/start</b> 로 메뉴를 열어 보세요.")
        except Exception as e:
            print("버튼·명령 처리 오류:", type(e).__name__, e, flush=True)
    if ups:
        save(HOME / "tg_offset.json", off)


_VR6_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fanding_vr6.py")


def _mtimes():
    out = []
    for f in (os.path.abspath(__file__), _VR6_FILE):
        try:
            out.append(os.path.getmtime(f))
        except OSError:
            out.append(0)
    return out


_LOADED_MTIME = _mtimes()


def _file_changed():
    return _mtimes() != _LOADED_MTIME


def _reload_if_changed():
    """비서 봇이 오래 켜져 있어도 이 파일이 바뀌었으면 새 코드로 다시 불러옴. 바뀌었으면 새 모듈, 아니면 None"""
    if _file_changed():
        import importlib
        return importlib.reload(sys.modules[__name__])
    return None


# ---------------------------------------------------------- 비서 봇 연결 (office_secretary 에서 호출)
def _pending_sheet(st):
    for d in sorted(st["sheets"], reverse=True):
        if st["sheets"][d]["status"] in ("pending",):
            return st["sheets"][d]
    return None


def secretary_message(tg_s, text, _reloaded=False):
    """처리했으면 True. tg_s 는 비서 봇의 TG 객체"""
    mod = None if _reloaded else _reload_if_changed()
    if mod:
        return mod.secretary_message(tg_s, text, True)
    t = text.strip()
    low = t.lower()
    if t in ("/재판독", "재판독", "/판독요청"):
        tg_s.send(request_scan()); return True
    if t in ("/진단", "진단"):
        tg_s.send(diagnosis()); return True
    m = re.fullmatch(r"(?:/배수|배수|/mult)\s*(\d+)?", t)
    if m:
        with locked_state() as st:
            if not m.group(1):
                tg_s.send(f"📐 지금 배수는 <b>×{st['multiplier']}</b> 예요. 아래 버튼으로 바꾸세요. (글자로는 <code>/배수 6</code>)",
                          mult_rows(st['multiplier'])); return True
            n = int(m.group(1))
            if not 1 <= n <= 50:
                tg_s.send("배수는 1~50 사이로 적어 주세요."); return True
            old = st["multiplier"]
            st["multiplier"] = n
            sh = _pending_sheet(st)
            msg = f"📐 배수 변경 ×{old} → <b>×{n}</b>"
            if sh:
                sh["mult"], sh["ver"] = n, sh["ver"] + 1
                sh["checks"], sh["auto_ok"] = run_checks(sh, n, sh.get("market"))
                tg_s.send(msg + "\n대기 중인 오늘 가격표에도 바로 적용했어요. 새 알림의 버튼으로 결정해 주세요.")
                send_sheet_alert(TG(), sh, "📋 <b>배수 바뀐 가격표</b>")
            else:
                tg_s.send(msg + "\n다음 가격표부터 적용돼요.", mult_rows(n))
        return True
    if low in ("/자동", "자동", "/자동켜기", "/자동끄기") or low.startswith("/자동 "):
        c = load(CFG, {})
        if low in ("/자동켜기", "/자동 켜기", "/자동 on"):
            c["auto_order"] = True
        elif low in ("/자동끄기", "/자동 끄기", "/자동 off"):
            c["auto_order"] = False
        else:
            tg_s.send(f"🤖 자동주문은 지금 <b>{'켜짐' if cfg()['auto_order'] else '꺼짐'}</b>.\n"
                      "아래 버튼으로 바꾸세요. (글자로는 <code>/자동켜기</code> · <code>/자동끄기</code>)",
                      auto_rows(cfg()['auto_order'])); return True
        save(CFG, c)
        tg_s.send(f"🤖 자동주문 <b>{'켜짐' if c['auto_order'] else '꺼짐'}</b>", auto_rows(c['auto_order'])); return True
    if low in ("/재예약강제", "재예약강제"):
        with locked_state() as st:
            sh = st["sheets"].get(sorted(st["sheets"])[-1]) if st["sheets"] else None
            if not sh or sh["status"] not in ("submitted", "partial") or now_kst() >= deadlines(sh)[2]:
                tg_s.send("다시 넣을 수 있는 주문이 없거나 마감이 지났어요."); return True
            tg_s.send(f"⚠️ <b>{sh['date']} 가격표를 취소 없이 새로 넣을까요?</b>\n메리츠 앱에서 기존 SOXL 예약을 <b>모두 직접 취소한 경우에만</b> 누르세요. "
                      "하나라도 남아 있으면 주문이 두 번 나가요.",
                      [[{"text": "✅ 모두 취소했어요 · 새로 넣기", "callback_data": f"fd:rf:{sh['date']}:{sh['ver']}"},
                        {"text": "↩️ 그만", "callback_data": f"fd:rx:{sh['date']}:{sh['ver']}"}]])
        return True
    if low in ("/재예약", "재예약"):
        with locked_state() as st:
            sh = st["sheets"].get(sorted(st["sheets"])[-1]) if st["sheets"] else None
            if not sh or sh["status"] not in ("submitted", "partial"):
                tg_s.send("다시 예약할 접수 완료 주문이 없어요."); return True
            if now_kst() >= deadlines(sh)[2]:
                tg_s.send("예약 마감이 지나 다시 예약할 수 없어요. 메리츠 앱에서 확인해 주세요."); return True
            new = RESERVE_NAMES.get(str(cfg().get("reserve_time", "2")))
            olds = sorted({RESERVE_NAMES.get(o.get("hour", "0"), "장개시") for o in sh["orders"] if o.get("no")})
            tg_s.send(f"🔁 <b>{sh['date']} 가격표 예약을 다시 넣을까요?</b>\n지금 예약({', '.join(olds)} 발주)을 모두 취소하고 "
                      f"<b>{new} 발주</b>로 같은 주문을 다시 넣어요.",
                      [[{"text": "✅ 취소하고 다시 예약", "callback_data": f"fd:rr:{sh['date']}:{sh['ver']}"},
                        {"text": "↩️ 그대로 두기", "callback_data": f"fd:rx:{sh['date']}:{sh['ver']}"}]])
        return True
    m2 = re.fullmatch(r"/발주시간\s*([0-3])?", t)
    if m2:
        c = load(CFG, {})
        if m2.group(1):
            c["reserve_time"] = m2.group(1); save(CFG, c)
        cur = str(cfg().get("reserve_time", "2"))
        tg_s.send(f"⏱ 예약 발주 시간: <b>{RESERVE_NAMES[cur]}</b>\n바꾸기: <code>/발주시간 2</code> 장마감 30분 전 · "
                  "<code>/발주시간 1</code> 장마감 10분 전 · <code>/발주시간 0</code> 장개시 · <code>/발주시간 3</code> 장개시 30분 후\n"
                  "(이미 접수된 주문은 <b>/재예약</b> 으로 바꿔요)", rt_rows(cur))
        return True
    if low in ("/가격표", "가격표", "/팬딩", "팬딩"):
        current_account = account_snapshot()
        with locked_state() as st:
            if not st["sheets"]:
                tg_s.send("아직 받은 가격표가 없어요."); return True
            d = sorted(st["sheets"])[-1]
            sh = st["sheets"][d]
            label = {"pending": "결정 대기", "approved": "승인됨·접수 대기", "submitting": "접수 중", "submitted": "접수 완료",
                     "partial": "일부 실패", "cancelled": "안 함", "skipped": "자동주문 안 함", "expired": "마감 지남"}
            view = dict(sh, market=current_account)
            tg_s.send(sheet_text(view, f"📋 <b>최근 가격표</b> · 상태: {label.get(sh['status'], sh['status'])}"),
                      sheet_rows(sh) if sh["status"] == "pending" else None)
        return True
    return False


def secretary_callback(tg_s, cb, _reloaded=False):
    mod = None if _reloaded else _reload_if_changed()
    if mod:
        return mod.secretary_callback(tg_s, cb, True)
    data = cb.get("data", "")
    if data.startswith("vm:"):   # VR6 메뉴 안의 선택 버튼(배수·일정)
        try:
            import fanding_vr6
            return fanding_vr6.callback(tg_s, cb)
        except Exception as e:
            print("VR6 버튼 오류:", type(e).__name__, e, flush=True)
            tg_s.answer(cb.get("id"), "VR6 처리 오류")
            return True
    if data.startswith("fm:"):   # 메뉴 버튼: 같은 이름의 명령 글자를 보낸 것과 똑같이 처리
        parts = data.split(":")
        key, arg = parts[1], (parts[2] if len(parts) > 2 else "")
        tg_s.answer(cb.get("id"))
        if key == "noop":
            return True
        cmd = {"mt": f"/배수 {arg}" if arg.isdigit() else "/배수",
               "au": {"1": "/자동켜기", "0": "/자동끄기"}.get(arg, "/자동"),
               "rt": f"/발주시간 {arg}" if arg in ("0", "1", "2", "3") else "/발주시간"}.get(key, MENU_CMD.get(key))
        if cmd:
            menu_text(tg_s, cmd)
        return True
    if not data.startswith("fd:"):
        return False
    _, kind, rest = data.split(":", 2)
    date, _, ver = rest.rpartition(":")
    cb_id = cb.get("id")
    msg_id = (cb.get("message") or {}).get("message_id")
    with locked_state() as st:
        sh = st["sheets"].get(date)
        if not sh or str(sh["ver"]) != ver:
            tg_s.answer(cb_id, "예전 알림이에요. 최신 알림의 버튼을 눌러 주세요."); tg_s.buttons(msg_id, []); return True
        if kind == "ok":
            if sh["status"] != "pending":
                tg_s.answer(cb_id, "이미 처리됐어요"); tg_s.buttons(msg_id, []); return True
            _, _, cutoff = deadlines(sh)
            if now_kst() >= cutoff:
                tg_s.answer(cb_id, "마감이 지났어요"); return True
            sh["status"], sh["approved_by"] = "approved", "button"
            tg_s.answer(cb_id, "승인했어요")
            tg_s.buttons(msg_id, [])
            c = cfg()
            when = "곧" if (now_kst().hour, now_kst().minute) >= hm(c["submit_kst"]) else f"{c['submit_kst']}에"
            tg_s.send(f"✅ <b>주문 승인</b> · {date} 가격표 ×{sh['mult']}\n{when} 메리츠 예약주문을 넣고 결과를 알려 드릴게요.")
        elif kind == "no":
            if sh["status"] != "pending":
                tg_s.answer(cb_id, "이미 처리됐어요"); tg_s.buttons(msg_id, []); return True
            sh["status"] = "cancelled"
            tg_s.answer(cb_id, "이번엔 주문 안 해요"); tg_s.buttons(msg_id, [])
            tg_s.send(f"❌ {date} 가격표: 이번엔 주문하지 않아요. (자동주문도 안 함)")
        elif kind == "rx":
            tg_s.answer(cb_id, "그대로 둘게요"); tg_s.buttons(msg_id, [])
        elif kind == "rr":
            tg_s.buttons(msg_id, [])
            if sh["status"] not in ("submitted", "partial") or now_kst() >= deadlines(sh)[2]:
                tg_s.answer(cb_id, "다시 예약할 수 없는 상태예요"); return True
            tg_s.answer(cb_id, "취소 중…")
            from meritz_client import Meritz
            m = Meritz()
            fails, skipped = [], 0
            dates = sorted({o.get("rsv_date") or datetime.fromisoformat(o["at"]).strftime("%Y%m%d") for o in sh["orders"] if o.get("no")})
            try:
                alive = m.reserved_active(dates[0], now_kst().strftime("%Y%m%d")) if dates else []
                alive_nos = {str(int(float(r.get("rsev_acpt_srno") or 0))) for r in alive}
            except Exception as e:
                alive_nos = None
                print("예약 목록 조회 실패 (전부 취소 시도):", e, flush=True)
            for o in sh["orders"]:
                if not o.get("no"):
                    continue
                if alive_nos is not None and str(int(float(o["no"]))) not in alive_nos:
                    skipped += 1; continue           # 이미 앱에서 취소된 예약
                try:
                    m.reserve_cancel(o.get("rsv_date") or datetime.fromisoformat(o["at"]).strftime("%Y%m%d"), o["no"])
                except Exception as e:
                    fails.append(f"{o['side']} {o['price']:g}×{o['qty']}: {str(e)[:80]}")
            if fails:
                tg_s.send("🚨 <b>예약 취소 일부 실패</b> — 새로 넣지 않았어요 (중복 방지).\n" + html.escape("\n".join(fails))
                          + "\n메리츠 앱에서 예약 내역을 확인해 주세요.")
                return True
            sh["orders"], sh["status"] = [], "approved"
            tg_s.send(f"✅ 기존 예약 정리 완료" + (f" (이미 취소돼 있던 {skipped}건은 건너뜀)" if skipped else "")
                      + f" → <b>{RESERVE_NAMES.get(str(cfg().get('reserve_time', '2')))} 발주</b>로 1분 안에 다시 넣을게요.")
        elif kind == "rf":
            tg_s.buttons(msg_id, [])
            if sh["status"] not in ("submitted", "partial") or now_kst() >= deadlines(sh)[2]:
                tg_s.answer(cb_id, "다시 넣을 수 없는 상태예요"); return True
            sh["orders"], sh["status"] = [], "approved"
            tg_s.answer(cb_id, "새로 넣을게요")
            tg_s.send(f"✅ <b>{RESERVE_NAMES.get(str(cfg().get('reserve_time', '2')))} 발주</b>로 1분 안에 새로 넣을게요.")
        elif kind in ("wy", "re"):
            if sh["status"] != "partial":
                tg_s.answer(cb_id, "다시 넣을 주문이 없어요"); tg_s.buttons(msg_id, []); return True
            sh["status"] = "retry_warn" if kind == "wy" else "retry"
            tg_s.answer(cb_id, "다시 넣을게요"); tg_s.buttons(msg_id, [])
            tg_s.send("🔁 남은 주문을 다시 넣을게요. (1분 안에 결과 알림)")
    return True


# ---------------------------------------------------------- 웹 업로드 (server.py 에서 호출)
def http_upload(h):
    c = cfg()
    token = c.get("upload_token") or ""
    given = h.headers.get("X-Fanding-Token", "")
    if len(token) < 20 or not hmac.compare_digest(given.encode(), token.encode()):
        return h.send(403, {"error": "bad_token"})
    if h.headers.get("X-Fanding-Kind", "").startswith("vr6"):   # VR6 는 따로 처리 (P 업로드와 섞지 않음)
        try:
            import fanding_vr6
        except Exception as e:
            return h.send(500, {"error": "vr6_module", "detail": f"{type(e).__name__}"[:80]})
        return fanding_vr6.http_upload(h)
    try:
        n = int(h.headers.get("Content-Length", "0"))
    except ValueError:
        n = 0
    note = h.headers.get("X-Fanding-Note", "")
    if note:  # 윈도우 PC 상태 알림 (로그인 풀림 등) → 비서 봇으로 전달
        if n:
            h.rfile.read(min(n, 4096))
        try:
            note = urllib.parse.unquote(note)[:300]
        except Exception:
            note = note[:300]
        try:   # 전송은 상시 프로그램(root)이 함
            INBOX.mkdir(parents=True, exist_ok=True)
            (INBOX / f"{int(time.time())}_{uuid.uuid4().hex[:6]}.note").write_text(note, encoding="utf-8")
        except OSError as e:
            return h.send(500, {"error": "save_failed", "detail": str(e)[:200]})
        return h.send(200, {"ok": True})
    if not 1000 < n <= 8_000_000:
        return h.send(400, {"error": "bad_size"})
    h.connection.settimeout(60)
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
    try:
        INBOX.mkdir(parents=True, exist_ok=True)
        (INBOX / f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False))
        (INBOX / f"{name}.img").write_bytes(data)
        with bridge_state() as b:
            b["last_received"] = {"at": now_kst().isoformat(), "mode": meta["mode"]}
    except OSError as e:
        return h.send(500, {"error": "save_failed", "detail": str(e)[:200]})
    return h.send(200, {"ok": True})


# ---------------------------------------------------------- 명령줄
def cmd_check():
    from meritz_client import Meritz
    c = cfg()
    m = Meritz()
    print("1) 토큰:", m.token()[:10] + "…  OK")
    for mk in (c["price_market"], "AX", "NY", "OQ"):
        try:
            p = m.price(c["symbol"], mk)
            print(f"2) {c['symbol']} 시세 [{mk}] 현재가 {p['price']} / 전일종가 {p['prev_close']}  OK")
            break
        except Exception as e:
            print(f"   시세 [{mk}] 실패: {e}")
    hold, sellable, exch, avg = m.holding(c["symbol"])
    print(f"3) 잔고 {c['symbol']}: 보유 {hold}주 · 매도가능 {sellable}주 · 평단 {avg} · 거래소번호 {exch}")
    try:
        for e in m.exchanges():
            if any(x in json.dumps(e, ensure_ascii=False) for x in ("아멕스", "AMEX", "NYSE", "뉴욕", "ARCA", "아카")):
                print("   거래소:", {k: e[k] for k in list(e)[:6]})
    except Exception as e:
        print("   거래소 목록 실패:", e)
    try:
        print("4) 미국 장운영:", m.market_hours())
    except Exception as e:
        print("4) 장운영 조회 실패:", e)
    print(f"5) 다음 주문일(미국): {next_session_date(last_session_date()).strftime('%Y%m%d')}, "
          f"예약 마감(한국): {deadlines({'us_date': next_session_date(last_session_date()).strftime('%Y%m%d')})[2]:%m/%d %H:%M}")
    print("조회만 했어요. 주문은 넣지 않았습니다.")


def cmd_parse(path):
    data = Path(path).read_bytes()
    reads = [gemini_read(data, PROMPTS[0]), gemini_read(data, PROMPTS[1])]
    print("판독1:", json.dumps(reads[0], ensure_ascii=False))
    print("판독2:", json.dumps(reads[1], ensure_ascii=False))
    st = load(STATE, {})
    mult = int(st.get("multiplier", cfg()["multiplier"]))
    sheet = {"parsed": reads[0], "reads_agree": core(reads[0]) == core(reads[1]), "mult": mult,
             "date": reads[0]["close_date"], "ver": 1, "us_date": next_session_date(last_session_date()).strftime("%Y%m%d")}
    market = market_snapshot()
    sheet["checks"], sheet["auto_ok"] = run_checks(sheet, mult, market)
    print("\n" + re.sub(r"<[^>]+>", "", sheet_text(sheet)))


def cmd_inject(path):
    INBOX.mkdir(parents=True, exist_ok=True)
    data = Path(path).read_bytes()
    name = f"{int(time.time())}_{hashlib.sha256(data).hexdigest()[:10]}"
    (INBOX / f"{name}.json").write_text(json.dumps({"post": "manual", "at": now_kst().isoformat()}))
    (INBOX / f"{name}.img").write_bytes(data)
    print("넣었어요. 20초 안에 비서 봇 알림이 와요.")


if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    if a[0] == "loop":
        loop()
    elif a[0] == "check":
        cmd_check()
    elif a[0] == "parse" and len(a) > 1:
        cmd_parse(a[1])
    elif a[0] == "inject" and len(a) > 1:
        cmd_inject(a[1])
    else:
        st = load(STATE, {})
        print(f"v{VERSION} 배수 ×{st.get('multiplier', cfg()['multiplier'])} 자동주문 {cfg()['auto_order']}")
        for d, sh in sorted(st.get("sheets", {}).items())[-5:]:
            print(d, sh["status"], [(o["side"], o["price"], o["qty"], o.get("no") or o.get("err") or o.get("warn")) for o in sh["orders"]])
