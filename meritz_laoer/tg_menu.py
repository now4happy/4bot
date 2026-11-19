# ==========================================================
# FILE: meritz_laoer/tg_menu.py   (MERITZ_LAOER v2.2.2)
# v2.2.2 (2026-11-19, 판 14): 현상태(상황판)에 탑쌓기 층 시각화 추가 — tower_lines (채워진 층 칸 + N/10층 + 층별 상세 줄). 층 상태 파일(tower_state.json)을 읽기만 함. 전략이 사다리면 안 보임. 기존 상황판 줄은 그대로
# v2.2.0 (2026-11-19, 판 13): 상황판·자금 현황에 현재 전략(사다리/탑쌓기) 표시 추가 — 탑쌓기면 상황판에 '채운 회차' 대신 층 수. 전략 이름은 한글로만 보임 (영어 변수 이름 금지 규칙). 메뉴 토글 버튼은 이번 판에 안 만듦. 매매 동작 변경 없음
# v2.1.0 (2026-11-19, 방 telegram-bot-menu-review 3차 v3): 텔레그램 메뉴 문구 정리를 v2.0.9(판 11) 기준 위에 다시 적용 — 이모티콘 제거(예전 이모티콘 키보드 글자도 같은 버튼으로 읽음)·값 설명(넣을 수 있는 값·뜻·바꾸면)·주식 넣기 확인 단계. 판 11 변경은 그대로 둠, 매매 동작 변경 없음
# v2.0.9 (2026-11-19, 판 11): 버전 표기만 올림 (usd_cash 고침은 meritz_api.py·main.py). 이전 v2.0.8 (2026-11-19, 판 10): 자동환전 창이 '한국시간 09:00~주문 시간(실시간 환전 시간 안에서만)'으로 바뀐 데 맞춰 안내 글자 3곳만 고침 (💰 자금의 '신청은 …' · 💱 화면 설명 · 켜기 확인 문구). 로직 변경 없음
# v2.0.7 (2026-11-19, 판 9): 자동환전 시간이 한국시간 오전 9시로 바뀐 데 맞춰 안내 글자 3곳만 고침 (💰 자금의 '신청은 주문 시간에만' · 💱 화면 설명 · 켜기 확인 문구). 로직 변경 없음
# v2.0.6 (2026-11-19, 판 8): 버전 표기만 올림 — staging 에 빠진 v2.0.4 파일(notifier·tg_menu·accum_strategy)을 v2.0.5 main·meritz_api 와 한 묶음으로 맞춤 (ImportError 해소). 코드 로직 변경 없음
# v2.0.4 (2026-11-19): 💰 자금 화면에 '현금 부족 → 부분 매수'(몇 회차 몇 주만, 원래 몇 주) 표시. 판 5 보완(메뉴가 멈추거나 메시지를 버리는 이유를 로그에 남김·오래된 메시지 안내) 포함
# v2.0.3 (2026-11-18): 지시 2026-11-18 — 자동환전 여유%·하루 상한은 사용자가 💱 안·⚙️ 설정 안에서 직접 입력(값은 클로드가 안 정함) → 그 뒤에 💱 켜기.
#   값 없이 켜면 '여유%와 하루 상한을 먼저 입력해 주세요' 만 알림. 시드는 '2억'·당일 시드는 '2,000만원'만 표시. 속쓸 가격만 소수점, 달러 금액·환율은 정수.
#   화면의 영어 변수 이름·옵션 이름·오류 문구는 한국말만(notifier.to_korean 이 보내기 직전에 정리). 글자를 짧고 쉽게, 버튼 이름 정리
#   (💸 매도 목표 퍼센트 변경 → 💸 매도 비중 변경 · ⚙️ 봇 상태 → 🤖 봇 상태(⚙️ 설정과 아이콘이 같아 헷갈림)). 상황판에 당일 매도 확인 표시. 매매 로직은 이 파일에서 안 바뀜
# v2.0.1 (2026-11-18): 메뉴 개편 — 맨밑 4개(💰 자금·📋 전술·📈 현상태·🛠 기타)가 메인, ☰ 메뉴·🏠·❓ 없앰. 이름 변경(거래 내역·봇 상태·주식 넣기·키 확인).
#   ⚙️ 설정(시드·회차·목표 이익률·매도 비중·사다리 시작가/간격·재매수 하락폭·하루 최대 회차·봇 켜기/끄기)과 💱 자동환전(켜기/끄기·여유%·하루 상한)은
#   설정 파일(config.update_settings) 값만 바꿈 — 입력 → 이전→새 값 확인 → [✅ 변경 확인]. 끄기(봇·자동환전)는 바로. 🛑 매매 정지 추가(정지 표시 켬). 상황판에 설정값 표시. 매매 로직 그대로
# v2.0.0 (2026-11-18): 적립봇 전환 — 표시 이름 '7번 메리츠 속쓸 적립봇', 상황판·계획·자금 표시를 새 계획(plan dict)에 맞춤,
#   ➕ 직접 산 주식 반영에 세 번째 글자 '차감' 추가 (예: 63 61.50 차감 = --add-shares --credit). 주문·설정 변경 기능은 그대로 없음
# 메리츠 무매 SOXL 텔레그램 메뉴: 📈 상황판 · ☰ 메뉴 · 🛠 도구 (맨밑 키보드만, 인라인 버튼 없음)
# v1.0.4 (2026-11-14): 봇 번호 정리 — 표시 이름 '메리츠 무매 SOXL' → '7번 메리츠 무매' (머리글·도움말·상황판)
# v1.0.3 (2026-11-14): 첫 버전.
#   - 토큰: 설정 telegram_file (notifier.py 와 같은 파일, 새 토큰 없음). 토큰 원문은 어디에도 출력·기록하지 않음 (지문 token_fp 만)
#   - check_identity() 가 '텔레그램 토큰이 다른 봇과 같음' 이면 폴링하지 않음 (forbid_telegram_files 검사 그대로)
#   - 등록된 chat_id 가 아닌 방의 글자·버튼은 조용히 무시 (알림 없음)
#   - 직렬화: main.idle() 안에서만 돎 = loop() 와 같은 스레드에서 순서대로. 별도 스레드·프로세스 없음.
#     장부·설정 쓰기는 기존 함수(cmd_add_shares → ConfigManager.add_shares, cmd_inject_start → inject_start,
#     clear_halt)만 부르며, 기존 GlobalThrottle.get_file_lock() 잠금을 그대로 씀
#   - 메뉴 동작은 기존 함수만 부름: cmd_check · build_plan+fmt_orders+plan_head · sell_target ·
#     cmd_add_shares · ConfigManager.clear_halt · cmd_inject_start(= --inject-start) · key_fingerprint
#   - 처음 시작 때 쌓여 있던 예전 업데이트는 건너뜀 (재시작으로 옛 버튼이 다시 실행되지 않게) · 2분 넘은 메시지 무시
# ==========================================================
import contextlib
import io
import json
import logging
import math
import os
import re
import time
import urllib.request

from config import update_settings
from global_throttle import GlobalThrottle
from notifier import Notifier, to_korean

# ---- v2.0.1 메뉴: 맨밑 4개가 곧 메인 (2x2). 카테고리 안 버튼은 카테고리마다 따로 보임
M_FUND, M_TACT, M_STAT, M_ETC = "자금", "전술", "현상태", "기타"
MAIN_ROWS = [[M_FUND, M_TACT], [M_STAT, M_ETC]]
BACK = "뒤로"
I_FUNDS, I_FX = "자금 현황", "자동환전"
I_PLAN, I_SET = "오늘 계획", "설정"
I_BOARD, I_LEDGER, I_POWER = "상황판", "거래 내역", "봇 상태"
T_CHECK, T_ADD, T_HALT, T_INJECT, T_FP = "점검", "주식 넣기", "정지 해제", "장부 시작", "키 확인"
T_STOP = "매매 정지"                               # v2.0.1 추가: 정지 표시를 켬 (정지 해제의 짝)
FUND_ROWS = [[I_FUNDS, I_FX], [BACK]]
TACT_ROWS = [[I_PLAN, I_SET], [BACK]]
STAT_ROWS = [[I_BOARD, I_LEDGER], [I_POWER, BACK]]
HALT_OK, INJECT_OK, INJECT_OVER = "정지 해제 확인", "장부 시작 확인", "장부 덮어쓰기 확인"
CHG_OK = "변경 확인"
ADD_OK = "주식 넣기 확인"                            # v2.1.0: 장부가 바뀌므로 수량·평단을 보여 준 뒤 확인
BOT_ON, BOT_OFF = "봇 켜기", "봇 끄기"
FX_ON, FX_OFF = "자동환전 켜기", "자동환전 끄기"

# 설정 변경 버튼 → 설정 키·이름·단위·종류. kind: krw(원, 억·만 가능) | int | num(소수 가능). lo/hi: 허용 범위 (lo_incl/hi_incl 로 경계 포함 여부)
SET_ITEMS = {
    "시드 변경": dict(key="total_krw", name="시드", unit="원", kind="krw", lo=0, lo_incl=False, ex="예: 2억, 20000000, 1억5000만"),
    "회차 변경": dict(key="split_count", name="회차 수", unit="회", kind="int", lo=2, hi=100, ex="예: 10"),
    "목표 이익률 변경": dict(key="sell_profit_pct", name="목표 이익률", unit="%", kind="num", lo=0, lo_incl=False, hi=500, ex="예: 10 (평단보다 10% 오르면 매도)"),
    "매도 비중 변경": dict(key="sell_fraction_pct", name="매도 비중", unit="%", kind="num", lo=0, lo_incl=False, hi=100, hi_incl=False, ex="예: 50 (보유의 절반을 매도)"),
    "사다리 시작가 변경": dict(key="ladder_top_usd", name="사다리 시작가", unit="$", kind="num", lo=0, lo_incl=False, ex="예: 50"),
    "사다리 간격 변경": dict(key="ladder_step_usd", name="사다리 간격", unit="$", kind="num", lo=0, lo_incl=False, ex="예: 5"),
    "재매수 하락폭 변경": dict(key="rebuy_drop_usd", name="재매수 하락폭", unit="$", kind="num", lo=0, lo_incl=False, ex="예: 5"),
    "하루 최대 회차 변경": dict(key="max_rounds_per_day", name="하루 최대 회차", unit="회", kind="int", lo=1, hi=100, ex="예: 1"),
    "환전 여유% 변경": dict(key="auto_fx_buffer_pct", name="환전 여유%", unit="%", kind="num", lo=0, hi=100, ex="예: 3 (모자란 달러보다 3% 더 환전)"),
    "환전 하루 상한 변경": dict(key="auto_fx_max_usd_per_day", name="환전 하루 상한", unit="$", kind="int", lo=0, lo_incl=False, ex="예: 5000 (달러, 정수)"),
}
KEY_ITEM = {i["key"]: i for i in SET_ITEMS.values()}
# v2.1.0 (2026-11-19): 값 바꾸기 화면에 '넣을 수 있는 값 · 무슨 뜻 · 바꾸면' 설명 추가 (값 범위·검사·확인 단계는 그대로, 어려운 말은 시드·사다리·평단·분할매도·자동환전·장부만 씀)
MEANS = {
    "total_krw": ("이 봇이 쓸 총 투자금(시드)이에요.", "회차 금액과 사다리 계산이 달라져요"),
    "split_count": ("총 투자금을 나눠 사는 횟수예요.", "1회 금액과 사다리 칸 수가 달라져요"),
    "sell_profit_pct": ("이익률이 이 %에 닿으면 파는 기준이에요.", "다음 판단부터 파는 시점이 달라져요"),
    "sell_fraction_pct": ("목표 이익률에 닿았을 때 가진 수량 중 파는 비중(분할매도)이에요.", "다음 매도부터 파는 양이 달라져요"),
    "ladder_top_usd": ("사다리(가격대별 매수 칸)의 맨 위 매수 가격이에요.", "사다리 칸 가격이 모두 달라져요"),
    "ladder_step_usd": ("사다리 칸과 칸 사이 가격 간격이에요.", "사다리 칸 가격이 달라져요"),
    "rebuy_drop_usd": ("판 뒤 다시 사려면 가격이 이만큼 내려와야 해요.", "다시 사는 시점이 달라져요"),
    "max_rounds_per_day": ("하루에 최대 몇 회차까지 살지 정해요.", "하루에 사는 횟수 상한이 달라져요"),
    "auto_fx_buffer_pct": ("자동환전 때 부족분에 더해 환전하는 여유 비율이에요.", "다음 자동환전 금액이 달라져요"),
    "auto_fx_max_usd_per_day": ("자동환전을 하루에 최대 얼마까지 할지 정한 상한이에요.", "하루 환전 한도가 달라져요"),
}
_EMOJI_RE = re.compile("(?:[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u25A0-\u25FF\u2300-\u23FF\u2900-\u297F\u2139\uFE0F\u200D])+ ?")   # 예전 이모티콘 키보드 글자를 새 버튼으로 읽는 데 씀
BOOL_NAME = {"enabled": "봇", "auto_fx_enabled": "자동환전"}
FX_NEED = "여유%와 하루 상한을 먼저 입력해 주세요"          # 값 없이 켜기를 눌렀을 때 이 글자만
SET_POWER = "봇 켜기/끄기"
SET_ROWS = [["시드 변경", "회차 변경"], ["목표 이익률 변경", "매도 비중 변경"],
            ["사다리 시작가 변경", "사다리 간격 변경"], ["재매수 하락폭 변경", "하루 최대 회차 변경"],
            ["환전 여유% 변경", "환전 하루 상한 변경"], [SET_POWER, BACK]]
LADDER_KEYS = ("total_krw", "split_count", "ladder_top_usd", "ladder_step_usd")   # 이미 채운 회차가 있으면 경고
PARENT = {"fund": "main", "tact": "main", "stat": "main", "etc": "main", "settings": "tact", "fx": "fund", "power": "settings"}
HEADS = {"main": "아래 버튼을 눌러 주세요", "fund": "자금", "tact": "전술", "stat": "현상태", "etc": "기타 · 가끔 쓰는 기능이에요",
         "settings": "설정 · 바꿀 값을 눌러 주세요 (값만 바뀌고 주문은 안 나가요)"}
CONFIRM_SEC = 60            # 제안값: 확인 버튼 유효 시간
WAIT_SEC = 300              # 제안값: 수량·평단 입력 기다림
MSG_MAX_AGE = 120           # 이보다 오래된 메시지는 처리하지 않음
HEAD = "7번 메리츠 속쓸 적립봇"
ALL_LABELS = ({M_FUND, M_TACT, M_STAT, M_ETC, BACK, I_FUNDS, I_FX, I_PLAN, I_SET, I_BOARD, I_LEDGER, I_POWER, T_CHECK, T_ADD, T_HALT, T_INJECT,
               T_FP, T_STOP, HALT_OK, INJECT_OK, INJECT_OVER, CHG_OK, ADD_OK, BOT_ON, BOT_OFF, FX_ON, FX_OFF, SET_POWER} | set(SET_ITEMS))


def fmt_krw(n):
    """원 금액을 짧게: 200000000 → '2억' · 20000000 → '2,000만원' · 150000000 → '1억 5,000만원' · 9500 → '9,500원' (앞에 긴 숫자 안 붙임)"""
    n = int(round(float(n)))
    if n < 10**4:
        return f"{n:,}원"
    e, m = divmod(int(round(n / 10**4)), 10**4)
    if e and not m:
        return f"{e:,}억"
    return (f"{e:,}억 " if e else "") + f"{m:,}만원"


def fmt_val(item, v, none="미정"):
    if v is None:
        return none
    if item["kind"] == "krw":
        return fmt_krw(v)
    if item["unit"] == "$":
        return f"${v:,}" if item["kind"] == "int" else f"${float(v):,.2f}"    # 달러 설정은 전부 속쓸 가격(사다리·재매수 하락폭) → 소수 2자리
    return f"{v:g}{item['unit']}"


def _num(v):
    try:
        return None if v is None or isinstance(v, bool) else float(str(v).replace(",", ""))
    except ValueError:
        return None


def fx_values_ready(s):
    """자동환전 여유%(0 이상)·하루 상한(0 초과)을 사용자가 입력했는지 (config.validate_settings 와 같은 조건)"""
    b, m = _num(s.get("auto_fx_buffer_pct")), _num(s.get("auto_fx_max_usd_per_day"))
    return b is not None and b >= 0 and m is not None and m > 0


def parse_value(item, text):
    """입력 글자 → (값, 오류 글자). 오류가 있으면 값은 None"""
    t = re.sub(r"[,\s$%원회]", "", text)
    if item["kind"] == "krw":
        m = re.fullmatch(r"(?:(\d+(?:\.\d+)?)억)?(?:(\d+(?:\.\d+)?)만)?(\d+)?", t)
        if not t or not m or not any(m.groups()):
            return None, "숫자로 보내 주세요. " + item["ex"]
        x = float(m.group(1) or 0) * 10**8 + float(m.group(2) or 0) * 10**4 + float(m.group(3) or 0)
        if abs(x - round(x)) > 1e-6:
            return None, "원 단위 정수로 환산되지 않아요. " + item["ex"]
        v = int(round(x))
    elif item["kind"] == "int":
        if not re.fullmatch(r"\d+", t):
            return None, "정수로 보내 주세요. " + item["ex"]
        v = int(t)
    else:
        if not re.fullmatch(r"\d+(?:\.\d+)?", t):
            return None, "숫자로 보내 주세요. " + item["ex"]
        x = float(t)
        v = int(x) if x == int(x) else x
    lo, hi = item.get("lo"), item.get("hi")
    if lo is not None and not (v >= lo if item.get("lo_incl", True) else v > lo):
        return None, (f"{lo} 이상이어야 해요" if item.get("lo_incl", True) else f"{lo}보다 커야 해요")
    if hi is not None and not (v <= hi if item.get("hi_incl", True) else v < hi):
        return None, (f"{hi} 이하여야 해요" if item.get("hi_incl", True) else f"{hi} 미만이어야 해요")
    return v, None


def kb(rows):
    return {"keyboard": [[{"text": t} for t in r] for r in rows], "resize_keyboard": True, "is_persistent": True}


class MenuBot:
    @staticmethod
    def range_text(it):
        """값 설명 화면의 '넣을 수 있는 값' 글자 (범위·단위는 SET_ITEMS 의 lo/hi/unit 그대로)"""
        lo, hi = it.get("lo"), it.get("hi")
        u = {"krw": "원 (억·만 표기 가능)", "int": it["unit"] + " 정수", "num": it["unit"]}[it["kind"]]
        if it["unit"] == "$" and it["kind"] == "num":
            u = "달러"
        a = "" if lo is None else (f"{lo} 이상" if it.get("lo_incl", True) else f"{lo} 초과")
        b = "" if hi is None else (f"{hi} 이하" if it.get("hi_incl", True) else f"{hi} 미만")
        return (a + (" ~ " if a and b else "") + b + " · " if (a or b) else "") + u

    def __init__(self, ops):
        self.o = ops                 # meritz_laoer/main.py 모듈 (기존 함수를 그대로 부름)
        self.offset = None
        self.primed = False
        self.wait = None             # {"kind": "add"|"set", "ts", "label"}
        self.pending = None          # 변경 확인 대기: {"changes", "desc", "ts"}
        self.in_prompt = False       # 입력·확인 화면이 떠 있는 동안 True (뒤로 = 그 화면 취소하고 같은 메뉴로)
        self.nav = "main"            # 지금 보이는 화면 (main|fund|tact|stat|etc|settings|fx) — 뒤로 와 기본 버튼줄이 따라감
        self.confirm = {}            # 확인 버튼 글자 → 누를 수 있는 마지막 시각
        self._cred = (0.0, None)     # (확인 시각, (토큰, chat_id) 또는 None) — 60초마다 다시 확인
        self._warn_at = {}           # 판 5 보완: 조용히 무시하던 이유별 마지막 로그 시각 (같은 이유는 10분에 한 번만)

    # ---------------------------------------------------------- 텔레그램
    def creds(self, s):
        """notifier 와 같은 telegram_file. check_identity 가 '다른 봇 토큰과 같음'이면 None (폴링 안 함)"""
        now = time.time()
        if now - self._cred[0] > 60:
            c = None
            n = Notifier(s.get("telegram_file") or "")
            if not n.ok:
                self._why("nocred", "메뉴 멈춤: 텔레그램 파일에 토큰 또는 chat_id 가 없음")
            elif any("텔레그램 토큰이 다른 봇과 같음" in b for b in self.o.check_identity(s)[0]):
                self._why("dup", "메뉴 멈춤: 텔레그램 토큰이 다른 봇과 같음 (forbid_telegram_files)")
            else:
                c = (n.token, n.chat_id)
            self._cred = (now, c)
        return self._cred[1]

    def _why(self, key, text, every=600):
        """메뉴가 메시지를 조용히 버리거나 멈추는 이유를 로그에 남김 (같은 이유는 every 초에 한 번)"""
        now = time.time()
        if now - self._warn_at.get(key, 0.0) > every:
            self._warn_at[key] = now
            logging.warning("텔레그램 " + text)

    def _call(self, tok, method, payload, timeout):
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{method}", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def send(self, c, text, rows=None, dry=True):
        tok, chat = c
        msg = (("[모의] " if dry else "") + HEAD + "\n" + to_korean(text)).replace(tok, "***")[:3900]
        try:
            self._call(tok, "sendMessage", {"chat_id": chat, "text": msg, "reply_markup": kb(rows or MAIN_ROWS)}, 15)
        except Exception as e:
            logging.warning(f"텔레그램 메뉴 전송 실패: {type(e).__name__}")

    def idle(self, s, t_end):
        """t_end 까지 getUpdates → 받은 것을 순서대로 처리 (이 스레드에서만)"""
        c = self.creds(s)
        if not c:
            return
        tok, chat = c
        if not self.primed:          # 쌓인 옛 업데이트 건너뜀
            r = self._call(tok, "getUpdates", {"offset": -1, "timeout": 0}, 10)
            res = r.get("result") or []
            self.offset = (res[-1]["update_id"] + 1) if res else None
            self.primed = True
        while True:
            left = t_end - time.time()
            if left < 1:
                return
            q = {"timeout": int(min(25, max(0, left - 1))), "allowed_updates": ["message"]}
            if self.offset is not None:
                q["offset"] = self.offset
            r = self._call(tok, "getUpdates", q, q["timeout"] + 10)
            stale = False
            for upd in r.get("result") or []:
                self.offset = upd["update_id"] + 1
                m = upd.get("message")
                if not isinstance(m, dict):
                    continue
                if str((m.get("chat") or {}).get("id", "")).strip() != str(chat):
                    self._why("chat", f"메뉴: 등록된 방이 아닌 곳({(m.get('chat') or {}).get('type')})의 메시지는 무시 — telegram 파일 chat_id 확인", 60)
                    continue          # 다른 방은 무시 (이유는 로그에만)
                age = time.time() - float(m.get("date") or 0)
                if age > MSG_MAX_AGE:
                    self._why("stale", f"메뉴: {int(age)}초 지난 메시지는 처리 안 함 (서버 시계 어긋남이나 긴 대기 확인)", 60)
                    stale = True
                    continue
                try:
                    try:
                        s = self.o.load_settings()
                    except Exception:
                        pass                      # 못 읽으면 직전 값으로
                    self.handle(s, c, (m.get("text") or "").strip())
                except Exception as e:
                    logging.warning(f"텔레그램 메뉴 처리 실패: {type(e).__name__}")
                    self.send(c, "처리 중 오류가 났어요. 다시 눌러 주세요.", dry=s.get("dry_run", True))
            if stale:                 # 오래된 메시지를 말없이 버리지 않고 한 번 알림
                self.send(c, "메시지가 늦게 도착해서(2분 넘음) 처리하지 않았어요. 버튼을 다시 눌러 주세요.", dry=s.get("dry_run", True))

    # ---------------------------------------------------------- 기존 함수 부르기
    def _out(self, fn, *a, **k):
        """기존 CLI 함수(print 출력)를 그대로 부르고 출력만 받아 옴 → (반환값, 출력 글자)"""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = fn(*a, **k)
        return rc, buf.getvalue().strip()

    def _api(self, s):
        o = self.o
        return o.MeritzApi(s["key_file"], os.path.join(s["state_dir"], "data", "meritz_token.json"))

    def _local(self, s):
        o = self.o
        os.makedirs(os.path.join(s["state_dir"], "data"), exist_ok=True)
        with o.in_dir(s["state_dir"]):
            cfg = o.ConfigManager(s)
            pos, halt = cfg.get_position(), cfg.get_halt()
            avg = cfg.avg_price(pos) if pos else 0.0
            tv, tgt = o.sell_target(s, cfg, pos) if pos else (None, None)
        return pos, halt, avg, tv, tgt

    def _api_ok(self, s):
        """cmd_check 와 같은 조건: 설정 문제·키 파일 없음·키 형식 오류면 메리츠 조회 안 함 → 문제 목록"""
        bad = self.o.validate_settings(s)
        idb, _ = self.o.check_identity(s)
        return bad + [b for b in idb if b in ("새 메리츠 키 파일 없음 (key_file)", "키 파일 형식 오류 (app_key/app_secret)")]

    def board(self, s):
        """B1 상황판 값 (조회만 — 주문·장부·설정을 바꾸지 않음). cmd_check 와 같은 입력으로 오늘 계획 미리보기"""
        o = self.o
        d = {"pos": None, "halt": None, "avg": 0.0, "t": None, "target": None, "api_bad": [], "hold": None, "sellable": None,
             "price": None, "prev": None, "fx": None, "cash": None, "plan": None, "orders": [], "notes": [], "plan_err": None}
        d["pos"], d["halt"], d["avg"], d["t"], d["target"] = self._local(s)
        d["api_bad"] = self._api_ok(s)
        if d["api_bad"]:
            return d
        api = self._api(s)
        d["hold"], d["sellable"], _ = api.holding(s["symbol"])
        d["price"], d["prev"], d["fx"] = o.market_inputs(s, api)
        d["cash"] = api.usd_cash()
        try:
            pos, st = d["pos"], s["start"]
            q = int(pos["qty"]) if pos else int(float(st["qty"]))
            principal = float(pos["principal"]) if pos else float(st["principal_usd"])
            with o.in_dir(s["state_dir"]):
                d["plan"] = o.build_plan(s, o.ConfigManager(s), d["price"], d["fx"], d["cash"], q, principal, d["sellable"])
            d["orders"], d["notes"] = d["plan"]["orders"], d["plan"]["notes"]
        except Exception as e:
            d["plan_err"] = type(e).__name__
        return d

    def plan_lines(self, s, d):
        if d["api_bad"]:
            return ["오늘 계획: 미확인 (" + "; ".join(d["api_bad"][:3]) + ")"]
        if d["plan"] is None:
            return [f"오늘 계획: 미확인 ({d['plan_err']})"]
        return ["오늘 계획 (미리보기 · 주문 안 냄)", self.o.plan_head(d["plan"], s), self.o.fmt_orders(d["orders"])] + \
               ["· " + n for n in d["notes"]]

    def mode_line(self, s, halt):
        return (f"· 봇 {'켜짐' if s.get('enabled') else '꺼짐'} · {'모의' if s.get('dry_run', True) else '실거래'}\n"
                f"· 정지 표시: {(halt or {}).get('reason') if halt else '없음'}")

    def strategy_text(self, s):
        """v2.2.0: 현재 전략 글자 (사다리 | 탑쌓기). 전환 설정은 설정 파일의 strategy 값 — 메뉴 버튼은 아직 없음"""
        fn = getattr(self.o, "strategy_ko", None)
        return fn(s) if fn else "사다리"

    def tower_lines(self, s, d):
        """v2.2.2 (판 14): 탑쌓기면 층 시각화 줄 (층 칸 + N/10층 + 층별 상세). 층 상태 파일을 읽기만 함 — 파일이 없으면 지금 장부를 1층으로 본 값(저장 안 함). 사다리면 빈 목록"""
        if self.strategy_text(s) != "탑쌓기":
            return []
        o, pos = self.o, d.get("pos")
        try:
            with o.in_dir(s["state_dir"]):
                tst, _ = o.tower_state_for(o.ConfigManager(s), int(pos["qty"]) if pos else 0, float(pos["principal"]) if pos else 0.0, s)
            return o.TW.view_lines(tst, s)
        except Exception:
            return ["탑: 층 상태 미확인"]

    def intraday_text(self, s):
        """당일 매도 확인 상태 글자"""
        sec = _num(s.get("intraday_sell_check_sec")) or 0
        if sec <= 0:
            return "꺼짐"
        if s.get("order_type") != "LIMIT":
            return "꺼짐 (지정가 주문일 때만 켜져요)"
        return f"{int(sec // 60)}분마다" if sec % 60 == 0 else f"{int(sec)}초마다"

    def settings_lines(self, s):
        """v2.0.1 상황판에 보이는 현재 설정값 (설정 파일 값 그대로 표시)"""
        v = lambda k: fmt_val(KEY_ITEM[k], s.get(k), "입력 전")
        fx = "켜짐" if s.get("auto_fx_enabled") else "꺼짐"
        fx += f" (여유 {v('auto_fx_buffer_pct')} · 하루 상한 {v('auto_fx_max_usd_per_day')})" if fx_values_ready(s) else " (여유%·하루 상한 입력 전)"
        return ["설정값",
                f"· 시드 {v('total_krw')} · 회차 {v('split_count')}",
                f"· 목표 이익률 {v('sell_profit_pct')} · 매도 비중 {v('sell_fraction_pct')}",
                f"· 사다리 시작가 {v('ladder_top_usd')} · 간격 {v('ladder_step_usd')} · 재매수 하락폭 {v('rebuy_drop_usd')}",
                f"· 하루 최대 회차 {v('max_rounds_per_day')} · 당일 매도 확인 {self.intraday_text(s)}",
                f"· 자동환전 {fx}"]

    def board_text(self, s):
        d = self.board(s)
        pos = d["pos"]
        lines = [f"[7번 메리츠 속쓸 적립봇 상황판 ({self.o.BOT_VERSION})]", self.mode_line(s, d["halt"])]
        lines.append(f"· 전략: {self.strategy_text(s)}")
        if pos:
            tw = ((d.get("plan") or {}).get("info") or {}).get("tower")
            fill_txt = (f"층 {len(tw['floors'])}개" if tw else "층 미확인") if self.strategy_text(s) == "탑쌓기" else f"채운 회차 {d['t']}"
            lines.append(f"· 장부: {pos['qty']}주 · 평단 ${d['avg']:.2f} · {fill_txt} · 매도 목표 ${d['target']:.2f}")
        else:
            lines.append("· 장부: 시작 전 (기타 → 장부 시작)")
        lines += self.tower_lines(s, d)
        if d["api_bad"]:
            lines.append("· 메리츠 조회: 미확인 (" + "; ".join(d["api_bad"][:3]) + ")")
        else:
            lq = int(pos["qty"]) if pos else None
            lines.append(f"· 메리츠 잔고: {d['hold']}주 (매도가능 {d['sellable']}) · 장부 {lq if lq is not None else '시작 전'}주"
                         + (" · 잔고 ≠ 장부" if lq is not None and d["hold"] != lq else ""))
            lines.append(f"· 현재가 ${d['price']:.2f} · 전일종가 ${d['prev']:.2f} · 적용환율 {('{:,.0f}'.format(d['fx'])) if d['fx'] else '미확인'}")
            lines.append(f"· 달러 예수금 ${d['cash']:,.0f}")
            pi = (d["plan"] or {}).get("info") or {}
            lines.append(f"· 시드 {fmt_krw(s['total_krw']) if s.get('total_krw') else '미정'} · 당일 시드 "
                         + (fmt_krw(pi["unit_usd"] * pi["fx"]) if pi.get("fx") and pi.get("unit_usd") is not None else "미확인"))
        lines += self.settings_lines(s)
        lines.append("─────────────────")
        lines += self.plan_lines(s, d)
        return "\n".join(lines)

    def ledger_text(self, s):
        o = self.o
        pos, halt, avg, _, _ = self._local(s)
        lines = ["[거래 내역 — 조회만]"]
        lines.append(f"· 장부: {pos['qty']}주 · 원금 ${float(pos['principal']):,.0f} · 평단 ${avg:.2f}" if pos else "· 장부: 시작 전")
        lines.append(f"· 정지 표시: {halt.get('reason') if halt else '없음'}")
        with o.in_dir(s["state_dir"]):
            cfg = o.ConfigManager(s)
            hist = cfg._load_json("data/add_shares_log.json", None)
            d = o.now_et().strftime("%Y-%m-%d")
            marks = [(n, cfg._load_json(f"data/{n}_{d}.json", None)) for n in ("orders", "dry_orders")]
        if isinstance(hist, list) and hist:
            h = hist[-1]
            lines.append(f"· 직접 산 주식 반영 기록: {len(hist)}건 · 최근 {str(h.get('at', ''))[:16]} {h.get('qty')}주 @ ${float(h.get('avg') or 0):.2f}"
                         f" ({(h.get('before') or {}).get('qty')}→{(h.get('after') or {}).get('qty')}주)")
        else:
            lines.append("· 직접 산 주식 반영 기록: 없음")
        shown = [(n, m) for n, m in marks if m is not None]
        if not shown:
            lines.append("· 오늘 주문 기록: 없음")
        for n, m in shown:
            label = "주문" if n == "orders" else "모의 주문"
            if m.get("skipped"):
                lines.append(f"· 오늘 {label}: 안 냄 — {str(m.get('skipped'))[:160]}")
                continue
            lines.append(f"· 오늘 {label}: {len(m.get('orders') or [])}건 · 오류 {len(m.get('errors') or [])}건 · 체결 반영 {'됨' if m.get('synced') else '전'}")
            lines += ["   " + x for x in self.o.fmt_orders(m.get("orders") or []).split("\n")]
            if m.get("sell_deferred"):
                lines.append("   오늘 산 주식이 체결되면 평단이 바뀌어서, 매도는 장중에 확인해서 내요")
            if m.get("sell_attempt"):
                lines.append("   당일 매도: " + str(m["sell_attempt"].get("status")))
        return "\n".join(lines)

    def funds_text(self, s):
        d = self.board(s)
        seed = fmt_krw(s["total_krw"]) if s.get("total_krw") else "미정"
        lines = ["[자금 현황 — 조회만 · 환전 신청은 메뉴에서 안 해요]", f"· 전략: {self.strategy_text(s)}"]
        if d["api_bad"]:
            return "\n".join(lines + [f"· 시드 {seed}", "· 메리츠 조회: 미확인 (" + "; ".join(d["api_bad"][:3]) + ")"])
        lq = int(d["pos"]["qty"]) if d["pos"] else None
        plan = d["plan"]
        if plan is not None:
            i = plan["info"]
            today = fmt_krw(i["unit_usd"] * i["fx"]) if i.get("fx") else "미확인"
            need = (f"· 오늘 필요 달러 ${i['need_usd']:,.0f} · " + (f"부족 ${math.ceil(i['shortfall_usd']):,}" if i.get("shortfall_usd") else "부족 없음")
                    + f" · 자동환전 {'켜짐 (한국시간 09:00~주문 시간, 환전 시간 안에서만)' if i.get('auto_fx') else '꺼짐'}"
                    + (f"\n· 현금 부족 → ${i['partial']['price']:.2f} 회차 {i['partial']['qty']}주만 부분 매수 (원래 {i['partial']['full_qty']}주)" if i.get("partial") else ""))
        else:
            today, need = "미확인", f"· 오늘 필요 달러: 미확인 ({d['plan_err']})"
        lines += [f"· 시드 {seed} · 당일 시드 {today}",
                  f"· 달러 예수금 ${d['cash']:,.0f}",
                  need,
                  f"· 보유 주수: 메리츠 {d['hold']}주 · 장부 {lq if lq is not None else '시작 전'}"
                  + (" · 잔고 ≠ 장부" if lq is not None and d["hold"] != lq else "")]
        return "\n".join(lines)

    def power_text(self, s):
        idb, fp = self.o.check_identity(s)
        exp = str(s.get("expected_key_fp") or "").strip()
        _, halt, _, _, _ = self._local(s)
        fp_txt = ("없음" if not fp else "있음 · " + ("기대값과 일치" if exp and fp == exp else ("기대값 없음" if not exp else "기대값과 다름")))
        return "\n".join(["[봇 상태 — 표시만]",
                          f"· 봇 {'켜짐' if s.get('enabled') else '꺼짐'} · {'모의' if s.get('dry_run', True) else '실거래'}",
                          f"· 입고 확인 {'됨' if s.get('transfer_confirmed') else '전'} · 토스 스나이퍼 정지 확인 {'됨' if s.get('toss_sniper_stopped_confirmed') else '전'}",
                          f"· 키 지문: {fp_txt}",
                          f"· 정지 표시: {halt.get('reason') if halt else '없음'}",
                          "· 봇 켜기/끄기: 전술 → 설정 → 봇 켜기/끄기 · 매매 정지: 기타. 모의/실거래 전환은 메뉴에서 안 바꿔요 (서버 설정·기존 안전 절차 그대로)."])


    # ---------------------------------------------------------- v2.0.1 화면 (카테고리별 버튼줄)
    def tools_rows(self, s):
        pos = self._local(s)[0]
        rows = [[T_CHECK, T_ADD], [T_STOP, T_HALT]]
        return rows + ([[T_INJECT, T_FP], [BACK]] if not pos else [[T_FP, BACK]])

    def fx_rows(self, s):
        return [[FX_OFF if s.get("auto_fx_enabled") else FX_ON], ["환전 여유% 변경", "환전 하루 상한 변경"], [BACK]]

    def rows(self, s):
        n = self.nav
        return {"fund": FUND_ROWS, "tact": TACT_ROWS, "stat": STAT_ROWS, "settings": SET_ROWS}.get(n) or \
            (self.tools_rows(s) if n == "etc" else self.fx_rows(s) if n == "fx" else
             [[BOT_OFF if s.get("enabled") else BOT_ON], [BACK]] if n == "power" else MAIN_ROWS)

    def fx_text(self, s):
        k = lambda key: fmt_val(KEY_ITEM[key], s.get(key), "입력 전")
        on = bool(s.get("auto_fx_enabled"))
        return "\n".join(["[자동환전]", f"· 지금: {'켜짐' if on else '꺼짐'}",
                          f"· 여유 {k('auto_fx_buffer_pct')} · 하루 상한 {k('auto_fx_max_usd_per_day')}",
                          "· 켜기 전에 여유%와 하루 상한을 직접 입력해 주세요 (아래 두 버튼, 설정에도 있어요)."
                          if not fx_values_ready(s) else "· 값이 입력돼 있어요. 켤 수 있어요.",
                          "· 켜면: 실거래 모드에서 한국시간 09:00부터 주문 시간 전까지(실시간 환전 시간 안에서만, 시간외·주말·공휴일 제외) 하루 한 번, 다음 한 회차에 모자란 달러 + 여유%를 하루 상한 안에서 환전 신청해요. 휴장 전날엔 미리 알려 주고 휴장 중 주문일 몫도 함께 환전해요.",
                          "· 이 메뉴에서는 환전 신청을 하지 않아요 (설정 값만 바뀜)."]
                         + (["· 지금은 모의 모드라 켜 둬도 환전 신청은 안 나가요."] if s.get("dry_run", True) else []))

    def power_bot_text(self, s):
        on = bool(s.get("enabled"))
        return (f"[봇 켜기/끄기]\n· 지금: {'켜짐' if on else '꺼짐'} · {'모의' if s.get('dry_run', True) else '실거래'}\n"
                "· 끄면 바로 적용, 켜면 확인 버튼이 한 번 더 나와요. 모의/실거래 전환은 여기서 안 바꿔요.")

    def show(self, name, s, say, text=None):
        self.nav, self.in_prompt = name, False
        say(text or (self.fx_text(s) if name == "fx" else self.power_bot_text(s) if name == "power" else HEADS.get(name, HEADS["main"])))

    # ---------------------------------------------------------- 설정 변경 (설정 파일 값만 바꿈)
    def _desc(self, changes, res):
        out = []
        for k, (old, new) in res.items():
            if k in BOOL_NAME:
                out.append(f"{BOOL_NAME[k]}: {'켜짐' if old else '꺼짐'} → {'켜짐' if new else '꺼짐'}")
            else:
                out.append(f"{KEY_ITEM[k]['name']}: {fmt_val(KEY_ITEM[k], old)} → {fmt_val(KEY_ITEM[k], new)}")
        return "\n".join("· " + x for x in out)

    def fill_warn(self, s, changes):
        """사다리 값을 바꾸는데 이미 장부·채운 회차가 있으면 경고 글자"""
        if not any(k in LADDER_KEYS for k in changes):
            return ""
        pos = self._local(s)[0]
        with self.o.in_dir(s["state_dir"]):
            n = len((self.o.ConfigManager(s).get_accum() or {}).get("filled_levels") or [])
        if pos or n:
            return (f"\n이미 장부 {pos['qty'] if pos else 0}주 · 채운 회차 {n}개가 있어요. "
                    "사다리 값을 바꾸면 이미 채운 회차와 어긋날 수 있어요.")
        return ""

    def propose(self, s, say, changes, extra=""):
        """검사만 하고(쓰지 않음) 이전 → 새 값을 보여 준 뒤 [변경 확인] 을 기다림"""
        try:
            res = update_settings(changes, dry=True)
        except ValueError as e:
            self.in_prompt = False
            return say(f"바꿀 수 없어요: {e}")
        except OSError as e:
            self.in_prompt = False
            return say("설정 파일을 읽지 못했어요. 서버 파일 권한을 확인해 주세요.")
        self.pending = {"changes": changes}
        self.confirm[CHG_OK] = time.time() + CONFIRM_SEC
        self.in_prompt = True
        return say(self._desc(changes, res) + self.fill_warn(s, changes) + (("\n" + extra) if extra else "")
                   + f"\n{CONFIRM_SEC}초 안에 [{CHG_OK}] 를 눌러 주세요. 주문은 안 나가고 값만 바뀌어요.", [[CHG_OK, BACK]])

    def apply(self, s, say, changes):
        try:
            res = update_settings(changes)
        except ValueError as e:
            return say(f"바꾸지 못했어요: {e}")
        except OSError as e:
            return say("설정 파일을 쓰지 못했어요 — 바뀐 것 없음. 서버 파일 쓰기 권한을 확인해 주세요.")
        try:
            self._s = self.o.load_settings()
        except Exception:
            pass
        self.in_prompt = False
        hint = ""
        if any(k in ("auto_fx_buffer_pct", "auto_fx_max_usd_per_day") for k in changes) and not (self._s or {}).get("auto_fx_enabled"):
            hint = ("\n· 이제 자금 → 자동환전 에서 [자동환전 켜기] 를 눌러 주세요." if fx_values_ready(self._s)
                    else "\n· 아직 " + ("하루 상한" if _num(self._s.get("auto_fx_buffer_pct")) is not None else "여유%") + "을 입력하지 않았어요.")
        return say("변경됨 (다음 주문 시간부터 적용)\n" + self._desc(changes, res) + hint)

    # ---------------------------------------------------------- 글자 처리
    def _ok_confirm(self, label):
        until = self.confirm.pop(label, 0)
        return time.time() <= until

    def handle(self, s, c, text):
        if not text:
            return
        text = _EMOJI_RE.sub("", text or "").strip()   # 예전 키보드(이모티콘 글자)가 폰에 남아 있어도 같은 버튼으로 읽음
        if not text:
            return
        self._s = s
        dry = s.get("dry_run", True)
        say = lambda t, rows=None: self.send(c, t, rows if rows is not None else self.rows(self._s), dry)
        if self.wait and text not in ALL_LABELS:
            w, self.wait = self.wait, None
            self.in_prompt = False
            if time.time() - w["ts"] > WAIT_SEC:
                return say("입력 시간이 지났어요. 버튼을 다시 눌러 주세요.")
            if w["kind"] == "set":
                item = SET_ITEMS[w["label"]]
                v, err = parse_value(item, text)
                if err:
                    self.wait, self.in_prompt = {**w, "ts": time.time()}, True
                    return say(f"{err}", [[BACK]])
                return self.propose(s, say, {item["key"]: v})
            parts = text.replace(",", " ").split()
            qty = int(parts[0]) if len(parts) >= 1 and parts[0].isdigit() else None
            try:
                avg = float(parts[1]) if len(parts) >= 2 else None
            except ValueError:
                avg = None
            credit = len(parts) >= 3 and parts[2] in ("차감", "credit")
            if qty is None or qty < 1 or avg is None or not (avg > 0) or avg == float("inf"):
                self.wait, self.in_prompt = {"kind": "add", "ts": time.time()}, True
                return say("수량은 1 이상 정수, 평단은 0보다 큰 달러 숫자로 띄어 써 주세요. 예: 3 52.10", [[BACK]])
            self.add_args = (qty, avg, credit)
            self.confirm[ADD_OK], self.in_prompt = time.time() + CONFIRM_SEC, True
            return say(f"장부에 넣을까요?\n지금 값 → 새 값\n· 장부 추가: 없음 → {qty}주 · 평단 ${avg:g}" + (" · 1회차 매수 때 원가 한 번 차감" if credit else "") +
                       f"\n{CONFIRM_SEC}초 안에 [{ADD_OK}] 를 눌러 주세요. 주문은 안 나가요 (장부만 바뀌고, 메리츠 잔고가 장부 + 수량과 같을 때만 반영돼요).", [[ADD_OK, BACK]])
        if text not in ALL_LABELS:                      # 모르는 글자·/start·예전 버튼(메뉴 등) → 새 메인 메뉴
            return self.show("main", s, say, "메뉴가 바뀌었어요. 아래 4개 버튼으로 써 주세요.")
        active, self.in_prompt, self.wait = self.in_prompt, False, None
        if text != CHG_OK:
            self.pending = None
        if text == BACK:
            return self.show(self.nav if active else PARENT.get(self.nav, "main"), s, say)
        cat = {M_FUND: "fund", M_TACT: "tact", M_STAT: "stat", M_ETC: "etc"}
        if text in cat:
            return self.show(cat[text], s, say)
        # ---- 💰 자금
        if text == I_FUNDS:
            self.nav = "fund"
            return say(self.funds_text(s))
        if text == I_FX:
            return self.show("fx", s, say)
        if text in (FX_ON, FX_OFF):
            self.nav = "fx"
        if text == FX_ON:
            if not fx_values_ready(s):
                return say(FX_NEED)
            return self.propose(s, say, {"auto_fx_enabled": True},
                                "켜면 실거래 모드에서만, 한국시간 09:00부터 주문 시간 전까지(실시간 환전 시간 안에서만) 하루 한 번, 하루 상한 안에서 환전을 신청해요. 실제 환전은 아직 시험 전이라 첫 환전은 꼭 확인해 주세요.")
        if text == FX_OFF:
            return self.apply(s, say, {"auto_fx_enabled": False})
        # ---- 📋 전술
        if text == I_PLAN:
            self.nav = "tact"
            return say("\n".join(self.plan_lines(s, self.board(s))))
        if text == I_SET:
            return self.show("settings", s, say)
        if text == SET_POWER:
            return self.show("power", s, say)
        if text == BOT_OFF:
            self.nav = "power"
            return self.apply(s, say, {"enabled": False})
        if text == BOT_ON:
            self.nav = "power"
            bad = self.o.validate_settings(s)
            return self.propose(s, say, {"enabled": True},
                                f"켜면 다음 주문 시간부터 동작해요. 지금 {'모의' if dry else '실거래'}예요. 입고 확인·토스 정지 확인·키 지문 등 기존 안전 조건은 그대로 먼저 통과해야 해요."
                                + (f"\n설정 문제 {len(bad)}건 (켜도 주문은 막혀요): " + "; ".join(bad[:3]) if bad else ""))
        if text in SET_ITEMS:
            it = SET_ITEMS[text]
            self.nav = self.nav if self.nav in ("settings", "fx") else ("fx" if it["key"].startswith("auto_fx") else "settings")
            self.wait, self.in_prompt = {"kind": "set", "label": text, "ts": time.time()}, True
            return say(f"{text}\n· 지금: {fmt_val(it, s.get(it['key']))}\n· 넣을 수 있는 값: {self.range_text(it)}\n"
                       f"· 무슨 뜻: {MEANS.get(it['key'], ('', ''))[0]}\n· 바꾸면: {MEANS.get(it['key'], ('', ''))[1]} (주문은 바로 나가지 않아요)\n"
                       f"· 새 값을 숫자로 보내 주세요. {it['ex']}"
                       + self.fill_warn(s, {it["key"]: None}), [[BACK]])
        if text == ADD_OK:
            a, self.add_args = getattr(self, "add_args", None), None
            if not a or not self._ok_confirm(ADD_OK):
                return say("확인 시간이 지났거나 넣을 주식이 없어요. 주식 넣기를 다시 눌러 주세요.")
            rc, out = self._out(self.o.cmd_add_shares, s, a[0], a[1], None, a[2])
            return say(("완료 · " if rc == 0 else "") + (out or "결과 없음"))
        if text == CHG_OK:
            p, self.pending = self.pending, None
            if not p or not self._ok_confirm(CHG_OK):
                return say("확인 시간이 지났거나 바꿀 값이 없어요. 다시 눌러 주세요.")
            return self.apply(s, say, p["changes"])
        # ---- 📈 현상태
        if text in (I_BOARD, I_LEDGER, I_POWER):
            self.nav = "stat"
            return say(self.board_text(s) if text == I_BOARD else self.ledger_text(s) if text == I_LEDGER else self.power_text(s))
        # ---- 🛠 기타
        self.nav = "etc"
        if text == T_CHECK:
            _, out = self._out(self.o.cmd_check, s)
            return say(out or "점검 결과 없음")
        if text == T_ADD:
            self.wait, self.in_prompt = {"kind": "add", "ts": time.time()}, True
            return say("직접 산 주식 수량과 평단(달러)을 띄어 써서 보내 주세요. 예: 3 52.10\n"
                       "• 1회차 매수 때 이 주식 원가를 한 번 차감하려면 끝에 '차감' 을 붙여요. 예: 63 61.50 차감\n"
                       "• 메리츠 잔고가 (장부 + 수량)과 같을 때만 반영돼요 · 봇이 켜져 있거나 미국장 주문 시간(미 동부 "
                       f"{s.get('order_time_et')}~{s.get('order_deadline_et')})이면 거부 · 주문은 안 나가요", [[BACK]])
        if text == T_STOP:
            with self.o.in_dir(s["state_dir"]):
                cfg = self.o.ConfigManager(s)
                with GlobalThrottle.get_file_lock(cfg.FILES["HALT"]):
                    cur = cfg.get_halt()
                    if not cur:
                        cfg.halt("텔레그램 수동 정지 (매매 정지)")
            if cur:
                return say(f"이미 정지 표시가 있어요: {cur.get('reason')}")
            return say("매매 정지 표시를 켰어요.\n· 실거래 모드에서는 정지 표시가 있는 동안 새 주문이 안 나가요 (이미 낸 주문의 취소는 안 하고, 체결 반영은 그대로).\n"
                       "· 오늘 이미 주문 시간이 지나 '주문 안 함'으로 기록됐다면 정지를 풀어도 오늘은 다시 안 내요.\n· 풀려면 정지 해제.")
        if text == T_HALT:
            halt = self._local(s)[1]
            if not halt:
                return say("정지 표시가 없어요. 해제할 것이 없습니다.")
            self.confirm[HALT_OK], self.in_prompt = time.time() + CONFIRM_SEC, True
            return say(f"정지 표시: {halt.get('reason')}\n원인을 확인한 뒤에 쓰는 기능이에요.\n"
                       f"확인했으면 {CONFIRM_SEC}초 안에 [{HALT_OK}] 를 눌러 주세요.", [[HALT_OK, BACK]])
        if text == HALT_OK:
            if not self._ok_confirm(HALT_OK):
                return say("확인 시간이 지났어요. 정지 해제를 다시 눌러 주세요.")
            with self.o.in_dir(s["state_dir"]):
                cfg = self.o.ConfigManager(s)
                with GlobalThrottle.get_file_lock(cfg.FILES["HALT"]):
                    cfg.clear_halt()
            return say("정지 표시 해제")
        if text == T_INJECT:
            pos = self._local(s)[0]
            label = INJECT_OVER if pos else INJECT_OK
            self.confirm[label], self.in_prompt = time.time() + CONFIRM_SEC, True
            if pos:
                return say(f"이미 장부가 있어요 ({pos['qty']}주). 덮어쓰려면 한 번 더 확인이 필요해요.\n"
                           f"{CONFIRM_SEC}초 안에 [{INJECT_OVER}] 를 누르면 같은 검사(설정·키·입고 확인·잔고가 시작 수량과 같은지) 뒤 덮어써요.",
                           [[INJECT_OVER, BACK]])
            return say("장부 시작: 설정·키 점검 · 입고 확인 · 메리츠 잔고가 시작 수량과 같을 때만 시작해요.\n"
                       f"{CONFIRM_SEC}초 안에 [{INJECT_OK}] 를 눌러 주세요.", [[INJECT_OK, BACK]])
        if text in (INJECT_OK, INJECT_OVER):
            if not self._ok_confirm(text):
                return say("확인 시간이 지났어요. 장부 시작을 다시 눌러 주세요.")
            rc, out = self._out(self.o.cmd_inject_start, s, text == INJECT_OVER)
            return say(out or ("완료" if rc == 0 else "실패"))
        if text == T_FP:
            try:
                fp = self.o.key_fingerprint(s["key_file"])
            except Exception as e:
                return say("키 지문: 읽지 못함 (키 파일을 확인해 주세요)")
            exp = str(s.get("expected_key_fp") or "").strip()
            return say(f"키 지문 (앞 12자리, 키 원문 아님): {fp}\n기대값: "
                       + ("일치" if exp and exp == fp else ("없음" if not exp else "다름")))
        return say("아래 버튼으로 써 주세요.")
