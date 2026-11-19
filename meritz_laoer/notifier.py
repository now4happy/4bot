# ==========================================================
# FILE: meritz_laoer/notifier.py   (MERITZ_LAOER v2.1.0)
# v2.1.0 (2026-11-19, 방 telegram-bot-menu-review 3차 v3): 텔레그램 메뉴 문구 정리를 v2.0.9(판 11) 기준 위에 다시 적용 — 이모티콘 제거(예전 이모티콘 키보드 글자도 같은 버튼으로 읽음)·값 설명(넣을 수 있는 값·뜻·바꾸면)·주식 넣기 확인 단계. 판 11 변경은 그대로 둠, 매매 동작 변경 없음
# v2.0.6 (2026-11-19, 판 8): 버전 표기만 올림 — staging 에 빠진 v2.0.4 파일(notifier·tg_menu·accum_strategy)을 v2.0.5 main·meritz_api 와 한 묶음으로 맞춤 (ImportError 해소). 코드 로직 변경 없음
# v2.0.4 (2026-11-19): _read_chat 추가 (main.check_identity 가 chat_id 가 비었거나 숫자가 아니면 막는 데 씀). 알림 보내기·문구는 그대로
# v2.0.3 (2026-11-18): to_korean() 추가 — 화면에 나가는 글자에서 영어 변수 이름·옵션 이름을 한국말로 바꾸고, 속쓸 가격이 아닌 달러 금액은 소수점을 없앰.
#   Notifier.send 가 보내기 직전에 한 번 거침 (표시만 바뀜 · 주문 계산·장부는 그대로). 텔레그램 메뉴(tg_menu.py)도 같은 함수를 씀
# 새 텔레그램 봇으로 알림만 보냄 (명령·버튼 없음). 토큰 파일: 설정 telegram_file {"token": "...", "chat_id": "..."}
# v2.0.0 (2026-11-18): 표시 이름 '🟦7번 메리츠 무매' → '🟦7번 메리츠 속쓸 적립봇' (노션 질문 Q8 ① Muse 확인 전 제안값)
# v1.0.4 (2026-11-14): 봇 번호 정리 — 알림 머리글 '🟦메리츠 무매 SOXL' → '🟦7번 메리츠 무매'
# v1.0.0 (2026-11-08): 첫 버전. 다른 봇 토큰 재사용 검사 함수 포함. 토큰 원문은 출력하지 않음
# ==========================================================
import hashlib
import json
import logging
import re
import urllib.parse
import urllib.request
from pathlib import Path


def _read_token(path):
    """JSON {"token": ...} 또는 토큰 한 줄짜리 파일 → 토큰 문자열 (없으면 "")"""
    try:
        raw = Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    try:
        d = json.loads(raw)
        if isinstance(d, dict):
            return str(d.get("token") or d.get("bot_token") or "").strip()
    except ValueError:
        pass
    return raw.splitlines()[0].strip() if raw else ""


def _read_chat(path):
    """JSON {"chat_id": ...} → chat_id 문자열 (없거나 형식이 다르면 ""). v2.0.4"""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str(d.get("chat_id") or "").strip() if isinstance(d, dict) else ""


def token_fp(tok):
    return hashlib.sha256(tok.encode()).hexdigest()[:12] if tok else ""


# ---------------------------------------------------------------- v2.0.3 화면 글자 정리 (표시 전용)
# 설정 이름 → 한국말. 화면에는 영어 변수 이름이 나오면 안 됨 (노션 지시 2026-11-18)
_NAME_KO = {
    "enabled": "봇", "dry_run": "모의 모드", "transfer_confirmed": "입고 확인",
    "toss_sniper_stopped_confirmed": "토스 스나이퍼 정지 확인", "key_file": "키 파일", "telegram_file": "텔레그램 설정 파일",
    "expected_key_fp": "키 지문 기대값", "forbid_key_files": "사용 금지 키 파일", "forbid_telegram_files": "사용 금지 텔레그램 파일",
    "state_dir": "장부 폴더", "symbol": "종목", "price_market": "시세 거래소", "exch_id": "거래소 번호",
    "split_count": "회차 수", "total_krw": "시드", "ladder_top_usd": "사다리 시작가", "ladder_step_usd": "사다리 간격",
    "rebuy_drop_usd": "재매수 하락폭", "sell_profit_pct": "목표 이익률", "sell_fraction_pct": "매도 비중",
    "unit_base": "재매수 기준", "first_buy_mode": "첫 매수 방식", "max_rounds_per_day": "하루 최대 회차",
    "order_type": "주문 방식", "allow_consecutive_sell": "연속 매도", "auto_fx_enabled": "자동환전",
    "auto_fx_buffer_pct": "환전 여유%", "auto_fx_max_usd_per_day": "환전 하루 상한",
    "intraday_sell_check_sec": "장중 매도 확인 간격", "order_time_et": "주문 시작 시각", "order_deadline_et": "주문 마감 시각",
    "sync_time_et": "체결 반영 시각", "seed_usd": "시드(달러)", "fee_pct": "수수료",
    "start.qty": "시작 수량", "start.principal_usd": "시작 원금", "start.avg_usd": "시작 평단",
    "start.filled_levels": "이미 산 회차", "start.mode": "시작 방식", "start.rebuy_anchor_usd": "재매수 기준 평단",
    "start.rebuy_k": "재매수 횟수", "start.first_round_credit_usd": "1회차 차감 금액", "make_plan": "계산",
}
# 참/거짓 값이 붙은 이름 → 한국말 문장
_BOOL_KO = {
    "enabled": ("봇 켜짐", "봇 꺼짐"), "dry_run": ("모의", "실거래"),
    "transfer_confirmed": ("입고 확인됨", "입고 확인 전"),
    "toss_sniper_stopped_confirmed": ("토스 스나이퍼 정지 확인됨", "토스 스나이퍼 정지 확인 전"),
    "auto_fx_enabled": ("자동환전 켜짐", "자동환전 꺼짐"), "allow_consecutive_sell": ("연속 매도 허용", "연속 매도 금지"),
}
_FLAG_KO = {"--inject-start": "장부 시작", "--clear-halt": "정지 해제", "--overwrite": "덮어쓰기", "--add-shares": "주식 넣기",
            "--credit": "차감", "--check": "점검", "--fingerprint": "키 확인", "--qty": "수량", "--avg": "평단"}
_WORD_KO = {"BUY": "매수", "SELL": "매도", "LIMIT": "지정가", "LOC": "종가 조건", "MOC": "종가 시장가", "USD": "달러",
            "ladder": "사다리", "rebuy": "재매수", "wait_top": "맨 위 확인 뒤", "total": "총 투자금", "cash": "남은 현금"}
_NAME_RE = re.compile(r"(?<![A-Za-z0-9_.])(" + "|".join(sorted((re.escape(k) for k in _NAME_KO), key=len, reverse=True)) + r")(?![A-Za-z0-9_])")
_BOOL_RE = re.compile(r"(?<![A-Za-z0-9_.])(" + "|".join(_BOOL_KO) + r")\s*=\s*(true|false)\b", re.I)
_FLAG_RE = re.compile("|".join(re.escape(k) for k in sorted(_FLAG_KO, key=len, reverse=True)) + r"(?![A-Za-z-])")
_WORD_RE = re.compile(r"(?<![A-Za-z0-9_.$])(" + "|".join(sorted(_WORD_KO, key=len, reverse=True)) + r")(?![A-Za-z0-9_])")
_IDENT_RE = re.compile(r"(?<![A-Za-z0-9_.])[A-Za-z]+(?:_[A-Za-z0-9]+)+(?![A-Za-z0-9_])")
# 속쓸 가격이 아닌 달러 금액(회차 금액·차감·필요·가용·부족…)은 소수점 없이. 가격(현재가·평단·1주·@)은 그대로 둠
_AMT_RE = re.compile(r"(회차 금액 |차감 |= |필요 |가용 |부족 |예수금 |원금 |기존 보유 \u2212)\$([\d,]+(?:\.\d+)?)(?![\d,])")


def _int_amt(m):
    return m.group(1) + "$" + format(int(round(float(m.group(2).replace(",", "")))), ",")


def to_korean(text):
    """화면에 나갈 글자 정리 (표시 전용·같은 글자를 두 번 넣어도 결과가 같음).
    영어 변수 이름·옵션 이름 → 한국말, '(이름=값)' 설명 괄호 삭제, 달러 금액(가격 제외) 소수점 삭제"""
    t = str(text)
    t = re.sub(r"\s*\(\s*[A-Za-z_.]+\s*=\s*[^()]*\)", "", t)                       # (enabled=True · dry_run=False) 같은 괄호 통째로 삭제
    t = re.sub(r"\s*\(\s*[a-z_.]+(?:\s*/\s*[a-z_.]+)*\s*\)", "", t)                 # (key_file) · (app_key/app_secret) 같은 이름만 든 괄호 삭제
    t = re.sub(r"(?:,\s*)?(?:\u2014\s*)?노션 질문(?: Q\d+)?", "", t)                       # '노션 질문 Q11' 같은 내부 표시 삭제
    t = re.sub(r"\s*\([^()]*Muse[^()]*\)", " (아직 정해지지 않음)", t)
    t = re.sub(r"\s*\([^()]*\|[^()]*\)", "", t)                                         # (total | cash) 같은 선택지 괄호 삭제
    t = _BOOL_RE.sub(lambda m: _BOOL_KO[m.group(1)][0 if m.group(2).lower() == "true" else 1], t)
    t = _FLAG_RE.sub(lambda m: _FLAG_KO[m.group(0)], t)
    t = _NAME_RE.sub(lambda m: _NAME_KO[m.group(1)], t)
    t = _WORD_RE.sub(lambda m: _WORD_KO[m.group(1)], t)
    t = _AMT_RE.sub(_int_amt, t)
    t = _IDENT_RE.sub("설정값", t)                                                        # 그래도 남은 영어 변수 이름
    t = re.sub(r"\b(true|false)\b", lambda m: "켜짐" if m.group(1) == "true" else "꺼짐", t)
    return re.sub(r"[ \t]{2,}", " ", t)


class Notifier:
    def __init__(self, telegram_file, dry_run=True):
        self.ok = False
        self.dry_run = dry_run
        try:
            d = json.loads(Path(telegram_file).read_text(encoding="utf-8"))
            self.token, self.chat_id = str(d["token"]).strip(), str(d["chat_id"]).strip()
            self.ok = bool(self.token and self.chat_id)
        except (OSError, ValueError, KeyError) as e:
            logging.warning(f"텔레그램 설정 없음/오류 → 로그로만 남김: {type(e).__name__}")

    def send(self, text):
        msg = ("[모의] " if self.dry_run else "") + "7번 메리츠 속쓸 적립봇\n" + to_korean(text)
        logging.info(msg.replace("\n", " | "))
        if not self.ok:
            return False
        try:
            body = urllib.parse.urlencode({"chat_id": self.chat_id, "text": msg[:3900]}).encode()
            req = urllib.request.Request(f"https://api.telegram.org/bot{self.token}/sendMessage", data=body, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status == 200
        except Exception as e:   # 알림 실패로 봇이 멈추지 않게
            logging.warning(f"텔레그램 전송 실패: {type(e).__name__}")
            return False
