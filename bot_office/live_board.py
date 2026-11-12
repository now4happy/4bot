#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/live_board.py   (사무실 vNEXT)
# 사무실 vNEXT
# vNEXT: 스나이퍼 현재가 스냅샷(sniper_snapshot.json)을 live_board 발행이 대신 써준다.
#  - 원작 스나이퍼 main.py에는 _write_picture_snapshot이 없어서, 원작 그대로 마이그레이션 뒤에는
#    사무실 그림(sniper_picture.py)이 읽는 현재가 스냅샷이 멈춘다. live_board가 매 실행마다
#    data["prices"]["soxl"]로 스냅샷을 써서 그림·원장 투영의 현재가를 유지한다.
#  - live_board 발행 여부와 무관하게 매 실행마다 쓴다 (SNAPSHOT_MAX_AGE 180초 — 가격이 안 바뀌어도
#    'at' 시각을 갱신해야 함). 장 닫힘·--check·--dry-run·--probe-krx에서는 쓰지 않는다.
#  - 쓰기 실패는 로그 없이 넘긴다 (live_board 발행·종료 코드에 영향 없음). 스나이퍼 폴더 파일과
#    같은 스키마 {"live_price", "at", "symbol": "SOXL"} · 원자적 쓰기 · 644.
# 사무실 v1.6.7
# v1.6.7: 한국만 열림 분기에도 시트 읽어 현금 갱신 (새로고침 시 현금 반영) + 한투 달러화 43행 포함
#  - 한국 장 열림·미국 장 닫힘 분기(elif _has_base)에서 시트를 다시 읽고 compute_sheet_only로 현금만 갱신.
#    미국 행은 마지막 값 그대로 동결. 시트 현금(B83)과 live_board 현금(totals.cash)이 낮에도 일치.
#  - 한투 달러화(43행, E43 = D43×환율)를 STATIC_E·합계(cash·api_ex41)에 포함.
# v1.6.2: 스나이퍼 원장 투영(sniper_tiers.json)을 live-board 작업트리에 함께 발행 — 최대 5분에 1번, 내용이 바뀐 때만.
#  - bot_updater.write_sniper_tiers() 와 같은 원천(sniper_picture.py 의 _find_ledger·_snapshot_price·build)·같은 스키마.
#    bot_updater 는 import 하지 않는다 (sniper_picture.py 만 importlib 으로 직접 읽음).
#  - 쓰는 곳은 작업트리(<WORKTREE>/sniper_tiers.json)뿐. 저장소 루트의 sniper_tiers.json 은 건드리지 않는다.
#  - 5분 경과는 작업트리 파일의 mtime 으로 판단 (다시 만들었는데 내용이 같으면 mtime 만 갱신 · 쓰기·커밋 없음).
#  - 바뀌면 live_board.json 과 같은 커밋·같은 푸시. 장이 둘 다 닫힌 시간 · --check · --dry-run · --probe-krx 에서는 건너뜀.
#  - 원장 단계의 어떤 실패도 로그만 남긴다 (live_board.json 발행·종료 코드 그대로).
# v1.6.1: 한국(KRX) 확장 — 키움 보유 32종목(KRX 상장·원화)의 현재가를 토스 /api/v1/prices 로 받아
#        krx 섹션 + E41(국내 주식) 실시간 합계를 만든다. 미국 장 로직·합계 정의·git/푸시 로직은 v1 그대로.
#  - 한국 장(KST 09:00–15:35, KR_CLOSED 제외 · KR_SPECIAL_HOURS 는 그날 시간)에는 KRX 시세만 받고 시트는 안 읽는다
#    (예외: 기존 JSON 에 base 가 없을 때 한 번만 — 첫 발행 · v1 JSON 에서 넘어올 때 · 실패 JSON 뒤).
#  - 종목별 실패는 마지막 발행값을 쓰고 krx.unavailable 에 적는다. 32개 전부 실패면 krx_price_unavailable.
#  - JSON 스키마는 추가만: market_open_us · market_open_kr · krx · krx_count · base · e41_source · rows["41"].
#  - 수량표(KRX_QTY)는 키움 캡처(2026-11-10 12:15 잔고 캡처 + 자동매매내역 2일치) 기준. 수량 변경 시 Muse가 캡처 기준으로 고침.
#  - 2026-11-10 수량 변경 4종목: NAVER 21→14, TIGER 코리아휴머노이드로봇산업 237→398, 에코프로비엠 49→67, 이수페타시스 60→82 (11-09 매수 3건 + 11-10 NAVER 매도 7주). 평단가는 매수 체결가 미확인이라 기존 유지.
#  - python3 live_board.py --probe-krx : 시트·git 안 건드리고 32개 코드의 토스 종목명·가격만 화면에 출력.
# v1: 시세 직접받기 — 토스 API(SOXL·TQQQ 현재가 + 환율)로 1분마다 자산 평가액을 계산해서
#       보드용 live_board.json 을 전용 브랜치 live-board 에 올린다 (main·staging 에는 절대 안 올림).
#  - 시트(26년 계획 · 입력정리)는 읽기만 한다 (spreadsheets.readonly · asset_board.py 의 서명·토큰 부품 재사용).
#  - 토스는 스나이퍼와 같은 TossApiClient(base_dir=/home/gieokkim/toss_sniper) 를 읽기 전용으로만 쓴다
#    (현재가 배치 1회 + 환율 1회 · 주문·계좌 호출 없음 · 스나이퍼 코드 수정 없음).
#  - 장 시간(ET 09:30–16:00, 휴장일 제외)에만 API 를 부른다. 장이 닫히면 market_open 만 한 번 false 로 바꾼다.
#  - JSON 에는 시세·환율·행별 평가액(만원)·합계만 넣는다. 키·토큰·계좌번호·원금은 넣지 않는다.
#  - 실패하면 {"ok": false, "error": 코드, "as_of_kst"} 를 원자적으로 쓰고 0 이 아닌 코드로 끝낸다.
#  - git: 작업트리 /var/lib/bot-office/live-board (브랜치 live-board) 에서만 커밋·푸시. force-push 없음.
#    저장소에 음수 refspec(^refs/heads/live-board)이 없으면 푸시하지 않는다
#    (업데이트 비서가 live-board 를 '새 업데이트'로 1분마다 알리는 것을 막기 위함 · VERIFY.md 참고).
# 사용:
#   python3 live_board.py             # 타이머가 부르는 것 (계산 → 쓰기 → 바뀌었으면 커밋+푸시)
#   python3 live_board.py --check     # 쓰지 않고 계산한 JSON 을 화면에만 출력 (푸시 없음)
#   python3 live_board.py --dry-run   # 쓰지 않고 한 줄 요약만 출력 (푸시 없음)
#   python3 live_board.py --probe-krx # 32개 코드 라이브 확인 (토스 종목명·가격 · 쓰기/푸시 없음)
# ==========================================================
import argparse, asyncio, json, os, pwd, re, subprocess, sys, tempfile, time, urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

KST, ET = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
WORKTREE = os.environ.get("LB_WORKTREE", "/var/lib/bot-office/live-board")
BRANCH = os.environ.get("LB_BRANCH", "live-board")
OUT_NAME = "live_board.json"
TOSS_DIR = os.environ.get("LB_TOSS_DIR", "/home/gieokkim/toss_sniper")
PUSHED_REF = f"refs/live-board/pushed"          # 마지막으로 푸시 성공한 커밋 (refs/remotes 밖이라 업데이트 비서가 안 봄)
SHEET_RANGE = "'입력정리'!A14:F55"
FIRST_ROW = 14
COLS = "ABCDEF"
TIME_KEYS = ("as_of_kst", "as_of_et")             # 내용 비교 때 빼는 칸 (시각만 바뀐 것은 '안 바뀜')
TIERS_NAME = "sniper_tiers.json"                  # v1.6.2: 스나이퍼 원장 투영 (작업트리에만 씀)
OFFICE_DIR = os.environ.get("LB_OFFICE_DIR", "/opt/bot-office")   # sniper_picture.py 가 있는 곳 (bot_updater 의 OFFICE_DIR 과 같은 기본값)
TIERS_INTERVAL = 300                              # 초 — 원장 투영은 최대 5분에 1번만 다시 만든다


# ---------------- 미국 휴장일 — fanding_trade.py 246·258행 발췌 그대로 (원본 sha256 8d8c3b3f0b50)
# 미국 정규장 휴장일 (조기 마감일은 장이 열린 날이라 넣지 않음)
# 출처: NYSE Group 2026·2027·2028 Holiday and Early Closings Calendar (2025-12-23 발표),
#       https://www.nyse.com/markets/hours-calendars — office_briefing.py 의 US_CLOSED 와 같은 표
# 2029년 이후는 표 확장이 필요하다 (표에 없는 연도는 주말만 건너뜀)
US_CLOSED = {
    2026: "01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25",
    2027: "01-01 01-18 02-15 03-26 05-31 06-18 07-05 09-06 11-25 12-24",
    2028: "01-17 02-21 04-14 05-29 06-19 07-04 09-04 11-23 12-25",
}


def is_trading_day(d):
    """미국 정규장이 열리는 날: 월~금이면서 휴장일 표에 없는 날"""
    if d.weekday() >= 5:
        return False
    return d.strftime("%m-%d") not in US_CLOSED.get(d.year, "").split()
# ---------------- 발췌 끝


# ---------------- 한국 휴장일 (KRX 유가증권·코스닥 정규장 · 주말 제외 평일만)
# 출처: 한국거래소 휴장일 조회 https://www.krx.co.kr (시장정보 > 증시일정 > 휴장일)
#       2026년 남은 휴장일 12-25 성탄절 · 12-31 연말 휴장 — 복수 출처 일치로 Muse 확인 (지시문 §2.5)
#       (11-10 이전 2026 휴장일은 이미 지난 날이라 넣지 않음)
# 2027년 표 미확정 — KRX 발표(매년 12월) 뒤 추가 필요. (2026-11-10 기준 KRX 연간 공고 없음 ·
#   민간 사이트끼리도 설 연휴 날짜가 서로 달라서 추측으로 넣지 않음.) 표에 없는 연도는 주말만 건너뜀.
KR_CLOSED = {
    2026: "12-25 12-31",
}
# 거래소가 따로 알린 정규장 시간 변경일 (KST · 시작 이상 끝 미만, 시각 HHMM)
# 2026-11-19 수능일: 10:00–16:30 (한국거래소 2026-11-05 발표 · SBS Biz·스마트투데이 2026-11-05 보도)
# 2027-01-04(새해 첫 거래일)은 보통 10:00 개장이지만 아직 공지 전 — 공지 뒤 추가 필요.
KR_SPECIAL_HOURS = {
    "2026-11-19": (1000, 1630),
}
KR_OPEN_HM, KR_CLOSE_HM = 900, 1535  # 15:35까지: 15:30에 나오는 종가를 받기 위함 (15:30까지면 15:20 무렵 가격이 마지막이 됨)


def is_kr_trading_day(d):
    if d.weekday() >= 5:
        return False
    return d.strftime("%m-%d") not in KR_CLOSED.get(d.year, "").split()


def kr_hours(d):
    return KR_SPECIAL_HOURS.get(d.isoformat(), (KR_OPEN_HM, KR_CLOSE_HM))


def is_kr_open(now_utc):
    k = now_utc.astimezone(KST)
    hm = k.hour * 100 + k.minute
    lo, hi = kr_hours(k.date())
    return is_kr_trading_day(k.date()) and lo <= hm < hi


# ---------------- 한국 종목 32개 (키움 2026-11-06 16:29 캡처 기준 · KODEX 머니마켓액티브 488770 은 현금이라 제외)
# 수량 변경 시 Muse가 캡처 기준으로 고침. (코드, 종목명, 수량, 평단가 원) · 순서 = JSON krx.stocks 순서
# 코드는 웹 검증(네이버 금융 + 운용사 페이지) · 라이브 토스 확인은 --probe-krx 로 (VERIFY.md)
KRX_QTY = (
    ("411060", "ACE KRX금현물", 233, 29535),
    ("066570", "LG전자", 31, 166722),
    ("035420", "NAVER", 14, 194121),
    ("178920", "PI첨단소재", 281, 18940),
    ("449450", "PLUS K방산", 136, 43823),
    ("005490", "POSCO홀딩스", 12, 309197),
    ("148020", "RISE 200", 57, 96933),
    ("475350", "RISE 버크셔포트폴리오TOP10", 99, 14748),
    ("000660", "SK하이닉스", 4, 1393354),
    ("0080Y0", "SOL 조선TOP3플러스레버리지", 1370, 8089),
    ("462010", "TIGER 2차전지소재Fn", 1372, 5023),
    ("360750", "TIGER 미국S&P500", 251, 24271),
    ("371460", "TIGER 차이나전기차SOLACTIVE", 679, 10554),
    ("371160", "TIGER 차이나항셍테크", 1691, 6998),
    ("0148J0", "TIGER 코리아휴머노이드로봇산업", 398, 8561),
    ("0015G0", "그린광학", 648, 12160),
    ("281740", "레이크머티리얼즈", 463, 13104),
    ("005930", "삼성전자", 22, 220272),
    ("068270", "셀트리온", 5, 181962),
    ("450080", "에코프로머티", 170, 43138),
    ("247540", "에코프로비엠", 67, 124968),
    ("394280", "오픈엣지테크놀로지", 917, 8685),
    ("032820", "우리기술", 547, 10971),
    ("007660", "이수페타시스", 82, 84916),
    ("022100", "포스코DX", 249, 24125),
    ("352820", "하이브", 26, 158751),
    ("018880", "한온시스템", 1109, 3620),
    ("570100", "한투 일본종합상사TOP5 ETN", 416, 20472),
    ("272210", "한화시스템", 81, 62530),
    ("000720", "현대건설", 56, 96085),
    ("005380", "현대차", 12, 354000),
    ("145020", "휴젤", 19, 217610),
)
KRX_CODES = tuple(c for c, _, _, _ in KRX_QTY)
KRX_BATCH = 10          # /api/v1/prices 한 번에 최대 10개 (32개 한 번 호출은 미확인)


class LiveError(RuntimeError):
    """JSON error 칸에 들어가는 짧은 코드만 담는다 (비밀·식별자 없음)"""


def is_us_open(now_utc):
    e = now_utc.astimezone(ET)
    hm = e.hour * 100 + e.minute
    return is_trading_day(e.date()) and 930 <= hm < 1600


is_market_open = is_us_open   # v1 이름 (옛 테스트·호출용 별칭 · 동작 같음)


def stamps(now_utc):
    return (now_utc.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S"),
            now_utc.astimezone(ET).strftime("%Y-%m-%d %H:%M:%S"))


# ---------------- 시트 (읽기 전용)
def read_sheet_values(http=None):
    """입력정리!A14:F55 한 범위만 읽음 → [[칸...], ...] (asset_board.py 의 토큰·HTTP 부품 그대로)"""
    import asset_board as AB
    http = http or AB.urllib_http
    tok, _email = AB.google_token(AB.SA_FILE, http)
    q = [("ranges", SHEET_RANGE), ("valueRenderOption", "UNFORMATTED_VALUE"),
         ("dateTimeRenderOption", "FORMATTED_STRING")]
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{AB.SHEET_ID}/values:batchGet?"
           + urllib.parse.urlencode(q))
    st, _, d = http("GET", url, {"authorization": "Bearer " + tok}, None)
    if st != 200:
        raise LiveError(f"sheet_http_{st}")
    vr = d.get("valueRanges") or []
    if len(vr) != 1:
        raise LiveError("sheet_bad_response")
    return vr[0].get("values") or []


def cell(values, ref):
    """'D27' → 시트 원래 값 (비었으면 None)"""
    col, row = COLS.index(ref[0]), int(ref[1:])
    i = row - FIRST_ROW
    if i < 0 or i >= len(values) or col >= len(values[i]):
        return None
    v = values[i][col]
    return None if v is None or (isinstance(v, str) and not v.strip()) else v


def num(values, ref):
    """숫자 칸 → float · 빈칸 → None · 글자(#N/A 등) → 오류"""
    v = cell(values, ref)
    if v is None:
        return None
    if isinstance(v, bool):
        raise LiveError(f"sheet_not_number_{ref}")
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[,\s]", "", str(v))
    try:
        return float(s)
    except ValueError:
        raise LiveError(f"sheet_not_number_{ref}") from None


def num0(values, ref):
    v = num(values, ref)
    return 0.0 if v is None else v


# ---------------- 계산 (API 와 분리 · 시트 수식과 같은 식)
# 행 → (수량 칸, 시세 키) · 시세 키 None = 달러 그대로(환율만)
QTY_ROWS = {27: "tqqq", 28: "soxl", 29: "soxl", 30: "tqqq", 33: None, 34: "soxl", 35: None}
STATIC_C = (26, 31, 32, 36, 39, 40, 46, 47, 48, 49, 50, 54)       # 정적 값 (C열) · v1.5.9: 41 뺌 (E41 = KRX 합계)
STATIC_E = (37, 38, 43)                                                 # v1: 시트 E값 그대로 (BTC·ETH) · 43: 한투 달러화 (E43 = D43×환율)
OUT_ROWS = (27, 28, 29, 30, 33, 34, 35, 37, 38)
KRX_ROW = 41                                                        # E41 국내 주식 = krx 32종목 합계


def sums(E):
    """반올림 전 부분합 (E41 빼고) → JSON base 칸 · 한국만 열린 분에 시트 없이 합계를 다시 내는 데 씀"""
    return {"api_ex41": sum(E[r] for r in range(26, 41)) + E[43],                 # E42 - E41 = SUM(E26:E40,E43)
            "cash": sum(E[r] for r in (26, 39, 31, 32, 33, 36, 46, 40, 54, 43)),  # B83 (41행 없음)
            "manual": sum(E[r] for r in (46, 47, 48, 49, 50, 54))}           # E51 = SUM(E46:E50,E54)


def totals_from(base, e41):
    api_sum = base["api_ex41"] + e41                                            # E42 = SUM(E26:E41)
    return {"api_sum": r2(api_sum), "cash": r2(base["cash"]), "total_assets": r2(api_sum + base["manual"])}


def _e41(values, e41):
    # KRX 합계가 아직 한 번도 안 나왔을 때만 (배포 직후 미국 장) 시트 C41 정적값 = v1 과 같은 값
    return float(e41) if e41 is not None else num0(values, f"C{KRX_ROW}")


def compute(values, soxl, tqqq, fx, e41=None):
    """→ (E값 dict{행: 만원, 반올림 전}, rows{str행: 만원 2자리}, totals) · e41 = KRX 합계(반올림 전, 만원)"""
    for k, v in (("soxl", soxl), ("tqqq", tqqq), ("usdkrw", fx)):
        if not isinstance(v, (int, float)) or not v > 0:
            raise LiveError(f"bad_price_{k}")
    px = {"soxl": float(soxl), "tqqq": float(tqqq)}
    E = {r: num0(values, f"C{r}") for r in STATIC_C}
    for r in STATIC_E:
        E[r] = num0(values, f"E{r}")
    for r, key in QTY_ROWS.items():
        q = num(values, f"D{r}")
        if q is None:   # 시트 IF(D="",F,...) 와 같은 폴백: 시트 E값 → 없으면 F값
            fb = num(values, f"E{r}")
            E[r] = fb if fb is not None else num0(values, f"F{r}")
        elif key is None:
            E[r] = q * fx / 10000 + (num0(values, "C35") if r == 35 else 0.0)
        else:
            E[r] = q * px[key] * fx / 10000
    E[KRX_ROW] = _e41(values, e41)
    rows = {str(r): r2(E[r]) for r in OUT_ROWS}
    rows[str(KRX_ROW)] = r2(E[KRX_ROW])
    return E, rows, totals_from(sums(E), E[KRX_ROW])


def compute_sheet_only(values, e41, us_rows=None):
    """한국만 열렸는데 기존 JSON 에 base 가 없을 때 (첫 발행 예외 · 미국 API 안 부름)
    미국 행 = 기존 JSON rows 값 (있으면) → 없으면 시트 E열 값 (시트 자체 폴백과 같은 값)"""
    E = {r: num0(values, f"C{r}") for r in STATIC_C}
    for r in STATIC_E:
        E[r] = num0(values, f"E{r}")
    for r in QTY_ROWS:
        v = (us_rows or {}).get(str(r))
        E[r] = float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else num0(values, f"E{r}")
    E[KRX_ROW] = _e41(values, e41)
    rows = {str(r): r2(E[r]) for r in OUT_ROWS}
    rows[str(KRX_ROW)] = r2(E[KRX_ROW])
    return E, rows, totals_from(sums(E), E[KRX_ROW])


def pack_base(E, krx_total):
    b = {k: round(v, 6) for k, v in sums(E).items()}
    b["krx_total"] = None if krx_total is None else round(krx_total, 6)
    return b


def build_krx(now_utc, prices, prev_krx):
    """prices{코드: 원} (0 이하 = 실패) → (krx 섹션, 반올림 전 합계 만원)
    실패 종목은 마지막 발행 가격 × 현재 수량 · 32개 전부 실패 → krx_price_unavailable"""
    prev = {}
    for s in ((prev_krx or {}).get("stocks") or []):
        if isinstance(s, dict) and isinstance(s.get("price"), (int, float)) and s["price"] > 0:
            prev[s.get("code")] = float(s["price"])
    got = {c: float((prices or {}).get(c) or 0) for c in KRX_CODES}
    if all(v <= 0 for v in got.values()):
        raise LiveError("krx_price_unavailable")
    stocks, total, unavailable = [], 0.0, []
    for code, name, qty, avg in KRX_QTY:
        p = got[code]
        if p <= 0:
            unavailable.append(code)
            if code not in prev:
                raise LiveError("krx_no_last_value")   # 마지막 발행값도 없음 (첫 발행 · 실패 JSON 뒤) → 다음 분에 다시
            p = prev[code]
        v = p * qty / 10000
        total += v
        stocks.append({"code": code, "name": name, "qty": qty, "avg_price": avg,
                       "price": r2(p), "value_manw": r2(v)})
    return ({"as_of_kst": stamps(now_utc)[0], "stocks": stocks, "total_manw": r2(total),
             "unavailable": unavailable}, total)


def r2(x):
    v = round(float(x) + 0.0, 2)
    return int(v) if v.is_integer() else v


def build_ok(now_utc, soxl, tqqq, fx, rows, totals):
    k, e = stamps(now_utc)
    return {"ok": True, "as_of_kst": k, "as_of_et": e, "market_open": True, "source": "toss",
            "prices": {"soxl": soxl, "tqqq": tqqq, "btc": None, "eth": None, "usdkrw": fx},
            "rows": rows, "totals": totals}


def build_fail(now_utc, code):
    return {"ok": False, "error": str(code)[:80], "as_of_kst": stamps(now_utc)[0]}


# ---------------- 토스 (읽기 전용 2회)
def _load_toss():
    if TOSS_DIR not in sys.path:
        sys.path.insert(0, TOSS_DIR)
    import toss_api
    if os.path.dirname(os.path.abspath(toss_api.__file__)) != os.path.abspath(TOSS_DIR):
        raise LiveError("toss_module_path")
    return toss_api


async def _quotes(client, default_fx=None):
    p = await client.get_current_prices_batch(("SOXL", "TQQQ"))
    fx = await client.get_usd_krw_rate()
    soxl, tqqq = float((p or {}).get("SOXL") or 0), float((p or {}).get("TQQQ") or 0)
    if soxl <= 0 or tqqq <= 0:
        raise LiveError("price_unavailable")   # 클라이언트는 실패하면 0.0 을 돌려줌
    # 클라이언트는 환율 실패 때 기본값(KRW_PER_USD_DEFAULT)을 조용히 돌려줌 → 성공 표시(_fx_cache_mono)로 구분
    fx = float(fx or 0)
    if fx <= 100 or getattr(client, "_fx_cache_mono", 1.0) <= 0 or (default_fx and fx == default_fx):
        raise LiveError("fx_unavailable")
    return soxl, tqqq, fx


def fetch_quotes():
    mod = _load_toss()
    client = mod.TossApiClient(base_dir=TOSS_DIR)

    async def run():
        try:
            return await asyncio.wait_for(_quotes(client, getattr(mod, "KRW_PER_USD_DEFAULT", None)), 40)
        except asyncio.TimeoutError:
            raise LiveError("toss_timeout") from None
        finally:
            try:
                await client.close()
            except Exception:
                pass
    return asyncio.run(run())


def chunks(seq, size=KRX_BATCH):
    seq = list(seq)
    return [seq[i:i + size] for i in range(0, len(seq), size)]


async def _krx_prices(client, codes=KRX_CODES):
    """10개씩 나눠 get_current_prices_batch (읽기 전용 GET /api/v1/prices) → {코드: 원, 실패 0.0}
    한 묶음이 통째로 0 인데 다른 묶음은 받혔으면 (코드 하나가 묶음 전체를 막는 경우 대비)
    그 묶음만 1개씩 다시 부른다 · 전부 0 이면 (토스 장애) 다시 부르지 않는다"""
    out, dead = {}, []
    for ch in chunks(codes):
        p = await client.get_current_prices_batch(tuple(ch)) or {}
        got = {c: float(p.get(c) or 0) for c in ch}
        out.update(got)
        if len(ch) > 1 and all(v <= 0 for v in got.values()):
            dead.append(ch)
    if dead and any(v > 0 for v in out.values()):
        for ch in dead:
            for c in ch:
                p = await client.get_current_prices_batch((c,)) or {}
                out[c] = float(p.get(c) or 0)
    return out


def _with_client(coro_fn, timeout):
    mod = _load_toss()
    client = mod.TossApiClient(base_dir=TOSS_DIR)

    async def run():
        try:
            return await asyncio.wait_for(coro_fn(client), timeout)
        except asyncio.TimeoutError:
            raise LiveError("toss_timeout") from None
        finally:
            try:
                await client.close()
            except Exception:
                pass
    return asyncio.run(run())


def fetch_krx():
    return _with_client(_krx_prices, 45)


async def _probe(client):
    """종목명(/api/v1/stocks) + 가격(/api/v1/prices) · 둘 다 10개씩 · 읽기 전용 GET 만"""
    names = {}
    for ch in chunks(KRX_CODES):
        try:
            res = await client._request(method="GET", path="/api/v1/stocks",
                                        params={"symbols": ",".join(ch)},
                                        require_account=False, rate_group="MARKET_DATA")
        except Exception as exc:
            res = {}
            print("  /api/v1/stocks 묶음 실패:", type(exc).__name__, flush=True)
        for it in ((res.get("result") if isinstance(res, dict) else None) or []):
            if isinstance(it, dict):
                names[str(it.get("symbol") or "").upper().strip()] = str(it.get("name") or "")
    prices = {}
    for ch in chunks(KRX_CODES):
        p = await client.get_current_prices_batch(tuple(ch)) or {}
        prices.update({c: float(p.get(c) or 0) for c in ch})
    return names, prices


def _norm(s):
    return re.sub(r"\s+", "", str(s or "")).upper()


def probe_report(names, prices, out=print):
    """→ 0 = 32개 전부 이름 일치 + 가격>0 · 1 = 하나라도 아님 (그 코드는 적용 전에 고쳐야 함)"""
    out("코드 | 기대 종목명 | 토스 종목명 | 일치 여부 | 가격>0 여부")
    bad, alpha = [], []
    for code, name, _, _ in KRX_QTY:
        tn = names.get(code, "")
        same = bool(tn) and _norm(tn) == _norm(name)
        pok = prices.get(code, 0) > 0
        line = (f"{code} | {name} | {tn or '(없음)'} | {'일치' if same else '다름'} | "
                f"{'O' if pok else 'X'} ({prices.get(code, 0):g})")
        out(line)
        if not code.isdigit():
            alpha.append(line)
        if not (same and pok):
            bad.append(code)
    out("--- 영문자 포함 코드 3개")
    for line in alpha:
        out(line)
    out(f"--- 결과: {len(KRX_QTY) - len(bad)}/{len(KRX_QTY)} 통과"
        + (f" · 확인 필요: {' '.join(bad)} (이름이 '다름'이면 공백·표기 차이인지 눈으로 확인)" if bad else ""))
    return 1 if bad else 0


def token_share_active():
    try:
        return getattr(_load_toss(), "_TTS", None) is not None
    except Exception:
        return False


# ---------------- 파일 · git
def owner():
    return pwd.getpwuid(os.stat(WORKTREE).st_uid)


def git(*a, timeout=60):
    """bot_updater.py git() 과 같은 방식 (root 면 저장소 주인으로 · -C 작업트리) · 환경변수는 최소만 넘김"""
    o = owner()
    cmd = ["env", f"HOME={o.pw_dir}", "GIT_TERMINAL_PROMPT=0", "git", "-c", "core.quotepath=false", "-C", WORKTREE, *a]
    if os.geteuid() == 0 and o.pw_uid != 0:
        cmd = ["runuser", "-u", o.pw_name, "--"] + cmd
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"}   # .env 에서 읽힌 키가 git 으로 안 넘어가게
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, "시간 초과"


def out_path():
    return os.path.join(WORKTREE, OUT_NAME)


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def load_current():
    return _load_json(out_path())


def same_content(a, b):
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    def strip(d):
        o = {k: v for k, v in d.items() if k not in TIME_KEYS}
        if isinstance(o.get("krx"), dict):   # v1.5.9: krx 섹션 시각도 같은 취급
            o["krx"] = {k: v for k, v in o["krx"].items() if k != "as_of_kst"}
        return o
    return strip(a) == strip(b)


def write_atomic(data, name=OUT_NAME):
    """임시 파일 + os.replace · 0644 · 저장소 주인 소유 (bot_updater.write_sniper_tiers 와 같은 방식)"""
    path, tmp = os.path.join(WORKTREE, name), None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=WORKTREE,
                                         prefix=f".{name.rsplit('.', 1)[0]}_", suffix=".tmp", delete=False) as out:
            tmp = out.name
            json.dump(data, out, ensure_ascii=False, allow_nan=False, indent=2)
            out.write("\n")
        os.chmod(tmp, 0o644)
        try:
            o = owner()
            os.chown(tmp, o.pw_uid, o.pw_gid)
        except OSError:
            pass
        os.replace(tmp, path)
        tmp = None
        return True
    except Exception as exc:
        print(f"{name} 기록 실패:", type(exc).__name__, str(exc)[:120], flush=True)
        return False
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def commit(msg):
    # v1.6.2: 원장 파일이 작업트리에 있으면 같은 커밋에 넣는다 (안 바뀐 파일은 add 해도 커밋에 안 잡힘)
    names = [OUT_NAME] + ([TIERS_NAME] if os.path.isfile(tiers_path()) else [])
    rc, out = git("add", "--", *names)
    if rc:
        print("git add 실패:", out[-200:], flush=True)
        return False
    if git("diff", "--cached", "--quiet", "--", *names)[0] == 0:
        return True   # 바뀐 것 없음
    rc, out = git("-c", "user.name=bot-office live-board", "-c", "user.email=live-board@localhost",
                  "commit", "-q", "-m", msg, "--", *names)
    if rc:
        print("git commit 실패:", out[-200:], flush=True)
    return rc == 0


def refspec_guard_ok():
    """저장소 remote.origin.fetch 에 ^refs/heads/<브랜치> 가 있어야 푸시 (업데이트 비서 알림 폭주 방지)"""
    _, out = git("config", "--get-all", "remote.origin.fetch")
    return f"^refs/heads/{BRANCH}" in out.split()


def push_if_needed():
    """푸시 안 된 커밋이 있으면 푸시 · 실패는 로그만 (다음 분에 다시) · force 없음 → 0=정상, 2=설정 안 됨"""
    rc, head = git("rev-parse", "-q", "--verify", "HEAD")
    if rc or not head:
        return 0   # 아직 커밋 없음
    _, pushed = git("rev-parse", "-q", "--verify", PUSHED_REF)
    if pushed == head:
        return 0
    if not refspec_guard_ok():
        print(f"푸시 안 함: remote.origin.fetch 에 ^refs/heads/{BRANCH} 없음 (VERIFY.md 설치 2단계)", flush=True)
        return 2
    rc, out = git("push", "-q", "origin", f"HEAD:refs/heads/{BRANCH}", timeout=60)
    if rc:
        print("git push 실패 (다음 분에 다시):", out[-200:], flush=True)
        return 0
    git("update-ref", PUSHED_REF, head)
    # 혹시 남은 추적 ref 가 있으면 지움 (업데이트 비서는 refs/remotes/origin 만 봄)
    if git("rev-parse", "-q", "--verify", f"refs/remotes/origin/{BRANCH}")[0] == 0:
        git("update-ref", "-d", f"refs/remotes/origin/{BRANCH}")
    return 0


def publish(data, msg):
    if not write_atomic(data):
        return False
    commit(msg)
    return True


# ---------------- 스나이퍼 현재가 스냅샷 (vNEXT · 원작 스나이퍼에는 없는 기능)
def _write_sniper_snapshot(data):
    """사무실 그림(sniper_picture.py)이 읽는 sniper_snapshot.json을 쓴다.
    원작 스나이퍼 main.py에는 _write_picture_snapshot이 없어서, 원작 그대로
    마이그레이션 뒤에는 이 live_board 발행이 스냅샷을 대신 써준다.
    실패해도 예외를 삼켜 live_board 발행·종료 코드에 영향을 주지 않는다."""
    try:
        prices = data.get("prices") if isinstance(data, dict) else None
        p = float(prices.get("soxl")) if isinstance(prices, dict) else 0.0
        if not (p > 0.0):
            return
        path = os.path.join(TOSS_DIR, "sniper_snapshot.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"live_price": round(p, 4), "at": time.time(), "symbol": "SOXL"}, f, ensure_ascii=False)
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o644)
        except OSError:
            pass
    except Exception:
        pass


# ---------------- 스나이퍼 원장 투영 (v1.6.2 · sniper_tiers.json · 작업트리에만 씀)
def tiers_path():
    return os.path.join(WORKTREE, TIERS_NAME)


def tiers_due(now_ts):
    """작업트리 파일 mtime 기준 5분 지났는가 (매 실행이 새 프로세스라 파일 시각으로 판단) · 파일 없으면 True"""
    try:
        age = now_ts - os.stat(tiers_path()).st_mtime
    except OSError:
        return True
    return age >= TIERS_INTERVAL or age < 0   # 미래 시각(시계 되돌림)이면 다시 만든다


def _tiers_touch():
    """다시 만들었지만 쓰지 않은 때: mtime 만 갱신해 다음 5분까지 쉬게 한다 (내용 그대로 → git 변경 없음)"""
    try:
        os.utime(tiers_path(), None)
    except OSError:
        pass


def build_tiers(now_utc):
    """bot_updater.write_sniper_tiers() 와 같은 원천·같은 스키마 (bot_updater import 없음) → dict · 실패는 예외"""
    import importlib.util
    source = os.path.join(OFFICE_DIR, "sniper_picture.py")
    spec = importlib.util.spec_from_file_location("office_sniper_picture_export", source)
    if not spec or not spec.loader:
        raise RuntimeError("sniper_picture_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    found, err = module._find_ledger()
    if not found:
        raise RuntimeError(str(err or "ledger_unavailable"))
    _, state = found
    live, note = module._snapshot_price(time.time())
    data = module.build(state, live_price=live, price_note=note)
    if not data.get("ok"):
        raise RuntimeError(str(data.get("error") or "build_failed"))
    holding = data.get("holding") or {}
    return {
        "ok": True, "as_of_kst": stamps(now_utc)[0], "symbol": "SOXL",
        "live_price": (data.get("price") or {}).get("live"),
        "price_note": (data.get("price") or {}).get("note", ""),
        "tiers": data.get("tiers") or [], "targets": data.get("targets") or [],
        "sub_tiers": data.get("sub_tiers") or [], "sub_targets": data.get("sub_targets") or [],
        "holding": {k: holding.get(k, 0) for k in ("shares", "sub_shares", "basement_shares", "total_shares")},
        "basement": data.get("basement"),
    }


def tiers_step(now_utc, now_ts=None):
    """5분 지났고 내용이 바뀌었으면 작업트리에 쓴다 → True = 새로 씀 (커밋 대상).
    어떤 실패도 로그만 남기고 False (live_board.json 발행·종료 코드에 영향 없음 · 마지막 정상 파일 유지)."""
    try:
        if not tiers_due(time.time() if now_ts is None else now_ts):
            return False
        try:
            new = build_tiers(now_utc)
        except Exception as exc:   # 원장 없음·build 실패 등 — 코드만 남김 (RuntimeError 는 짧은 오류 코드)
            print("sniper_tiers 건너뜀:", type(exc).__name__,
                  (str(exc)[:80] if type(exc) is RuntimeError else ""), flush=True)
            _tiers_touch()
            return False
        if same_content(_load_json(tiers_path()), new):
            _tiers_touch()
            return False
        return write_atomic(new, TIERS_NAME)
    except Exception as exc:
        print("sniper_tiers 단계 실패:", type(exc).__name__, flush=True)
        return False


# ---------------- 실행
FLAGS = ("market_open", "market_open_us", "market_open_kr")


def _ok_prev(cur):
    return cur if isinstance(cur, dict) and cur.get("ok") is True else None


def _prev_krx_total(prev):
    """마지막 발행 KRX 합계 (반올림 전) · 아직 한 번도 없으면 None (→ E41 = 시트 C41)"""
    if not prev or not isinstance(prev.get("krx"), dict):
        return None
    b = prev.get("base") if isinstance(prev.get("base"), dict) else {}
    v = b.get("krx_total")
    if not isinstance(v, (int, float)):
        v = prev["krx"].get("total_manw")
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _has_base(prev):
    b = prev.get("base") if prev else None
    return (isinstance(b, dict) and all(isinstance(b.get(k), (int, float)) for k in ("api_ex41", "cash", "manual"))
            and isinstance(prev.get("rows"), dict) and isinstance(prev.get("prices"), dict))


def build_v2(now_utc, cur, us_open, kr_open, sheet_reader, quote_fetcher, krx_fetcher):
    """열린 장만 부른다 · 닫힌 장 섹션은 마지막 발행값 그대로 → 완성된 JSON (실패는 LiveError)"""
    prev = _ok_prev(cur)
    krx, krx_total = (prev or {}).get("krx"), _prev_krx_total(prev)
    if kr_open:
        krx, krx_total = build_krx(now_utc, krx_fetcher(), krx)
    if us_open:                                      # v1 그대로 (시트 + SOXL·TQQQ·환율)
        values = sheet_reader()
        soxl, tqqq, fx = quote_fetcher()
        E, rows, totals = compute(values, soxl, tqqq, fx, e41=krx_total)
        base = pack_base(E, krx_total)
    elif _has_base(prev):                            # 한국만 열림 · 시트 읽어 현금만 갱신 · 미국 행은 마지막 값
        values = sheet_reader()
        p = prev["prices"]
        soxl, tqqq, fx = p.get("soxl"), p.get("tqqq"), p.get("usdkrw")
        E, rows, totals = compute_sheet_only(values, krx_total, prev.get("rows"))
        base = pack_base(E, krx_total)
    else:                                            # 한국만 열림 · 첫 발행 예외 (이때만 시트 읽음)
        values = sheet_reader()
        p = (prev or {}).get("prices") or {}
        soxl, tqqq, fx = p.get("soxl"), p.get("tqqq"), p.get("usdkrw")
        E, rows, totals = compute_sheet_only(values, krx_total, (prev or {}).get("rows"))
        base = pack_base(E, krx_total)
    data = build_ok(now_utc, soxl, tqqq, fx, rows, totals)
    data.update({"market_open": bool(us_open or kr_open), "market_open_us": bool(us_open),
                 "market_open_kr": bool(kr_open), "krx_count": len(KRX_QTY),
                 "e41_source": "krx" if krx_total is not None else "sheet_c41", "base": base})
    if krx is not None:
        data["krx"] = krx
    return data


def run(argv=None, now=None, sheet_reader=None, quote_fetcher=None, out=print, krx_fetcher=None):
    ap = argparse.ArgumentParser(description="토스 시세 → live_board.json (live-board 브랜치)")
    ap.add_argument("--check", action="store_true", help="쓰지 않고 계산한 JSON 출력")
    ap.add_argument("--dry-run", action="store_true", help="쓰지 않고 한 줄 요약만")
    ap.add_argument("--probe-krx", action="store_true", help="32개 코드 토스 종목명·가격 확인 (쓰기 없음)")
    a = ap.parse_args(argv)
    if a.probe_krx:
        try:
            names, prices = _with_client(_probe, 90)
        except LiveError as exc:
            out("probe 실패: " + str(exc))
            return 1
        return probe_report(names, prices, out)
    readonly = a.check or a.dry_run
    now_utc = (now or (lambda: datetime.now(ZoneInfo("UTC"))))()
    sheet_reader = sheet_reader or read_sheet_values
    quote_fetcher = quote_fetcher or fetch_quotes
    krx_fetcher = krx_fetcher or fetch_krx

    if not readonly and not os.path.isdir(WORKTREE):
        out(f"작업트리 없음: {WORKTREE} (VERIFY.md 설치 3단계)")
        return 3

    us_open, kr_open = is_us_open(now_utc), is_kr_open(now_utc)
    if not us_open and not kr_open:
        cur = None if readonly else load_current()
        if readonly:
            out(json.dumps({"market_open": False, "market_open_us": False, "market_open_kr": False,
                            "note": "장 닫힘 — API 안 부름 · 기존 JSON 의 market_open 세 칸만 false 로"},
                           ensure_ascii=False))
            return 0
        if isinstance(cur, dict) and any(cur.get(k) is True for k in FLAGS):
            for k in FLAGS:
                cur[k] = False   # 시세·행·합계·krx 는 마지막 장중 값 그대로
            publish(cur, f"live_board: 장 마감 {stamps(now_utc)[0]} KST")
        return push_if_needed()

    try:
        data, code = build_v2(now_utc, load_current(), us_open, kr_open,
                              sheet_reader, quote_fetcher, krx_fetcher), 0
    except LiveError as exc:
        data, code = build_fail(now_utc, str(exc)), 1
    except Exception as exc:   # 시트 토큰·네트워크 등 — 코드만 남김 (메시지에 계정 이메일이 들어갈 수 있음)
        name = type(exc).__name__
        data, code = build_fail(now_utc, ("sheet_error" if name == "SheetError" else "error_" + name)), 1

    if a.check:
        out(json.dumps(data, ensure_ascii=False, indent=2))
        out(f"(토큰 공유 hook: {'켜짐' if token_share_active() else '꺼짐/미확인'})")
        return code
    if a.dry_run:
        out(("ok" if data["ok"] else "실패 " + data["error"]) + " · 쓰지 않음")
        return code

    if data.get("ok"):
        _write_sniper_snapshot(data)   # vNEXT: 스냅샷 — live_board 발행 여부와 무관하게 매 실행마다
    tiers_new = tiers_step(now_utc)   # v1.6.2: 실패해도 False 만 (아래 발행·종료 코드 그대로)
    if not same_content(load_current(), data):
        publish(data, f"live_board {data['as_of_kst']} KST" + ("" if data["ok"] else " (실패)"))   # 원장 파일도 같은 커밋
    elif tiers_new:                   # live_board 는 그대로인데 원장만 바뀐 드문 경우
        try:
            commit(f"sniper_tiers {data['as_of_kst']} KST")
        except Exception as exc:
            print("sniper_tiers 커밋 실패:", type(exc).__name__, flush=True)
    print(("ok" if data["ok"] else "실패 " + data["error"]), flush=True)
    rc = push_if_needed()
    return code or rc


if __name__ == "__main__":
    sys.exit(run())
