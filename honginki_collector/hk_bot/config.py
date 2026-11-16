"""홍인기 단타 매매봇 설정 (단계 1: 백테스트 + 그림자 모드). 주문 실행 기능 없음.

등급 A = 책 확정(고정) / 등급 C = 책에 없음(탐색 축) / '미확인'·'임시값' = 근거 없는 시작값.
"""
import os


def _env(name, default):
    return os.environ.get(name, default)


BOT_DIR = os.path.expanduser(_env("HK_BOT_DIR", "~/honginki_bot_data"))

# --- 사용자 결정 게이트 ---
BOWL = 10_000_000            # 그릇 (원)
DAILY_LOSS_LIMIT = 300_000   # 일일 손실 한도 (그릇의 3%)

# --- 등급 A: 책 확정 규칙 (탐색 금지) ---
# Q6 결정 (2026-11-16, 사용자): 우선주·관리종목·투자경고 종목은 후보에서 제외.
# 구현은 hist.fetch_universe에서: ka10099 orderWarning != "0" 제외 + 이름이 "우"/"우B"로
# 끝나는 우선주 제외. 관리종목은 ka10099 응답 필드로 확인 필요 (fetch 때 원문 확인).
STOP_PCT = 0.03              # 매입 단가 대비 손절
GAP_PCT = 0.01               # 전일 종가 대비 (D+1 시초가, D+2 손절 라인)
D_MIN = 0.15                 # D 최소 상승률
D_MIN_LARGE = 0.10           # 시총 조 단위
LARGE_CAP = 1_000_000_000_000
HIGH_LOOKBACK = 120          # 6개월 내 전고점 = 120일봉 최고가
RANK_LIMITS = (15, 30)       # 거래대금 15위 → 없으면 30위
THEME_MIN_FLU = 5.0          # 상승률 5% 이상
ENTRY_START = "09:30"        # 09:30 이후 공략
TP_CUTOFF = "09:30"          # D+1 매도 기회: 09:30 이전 (D+2 '아침'에도 같은 시각 적용 = 가정)

# --- 미확인·임시값 ---
MA_SET = (5, 20, 60)         # 정배열 판정 이평선 묶음: 책 수치 미확인
D2_EXIT = "15:20"            # D+2 최종 청산 시각: 책에 시각 없음 (임시값)
COMMISSION = float(_env("HK_BOT_COMMISSION", "0.00015"))  # 편도 수수료율: 미확인
SLIPPAGE = float(_env("HK_BOT_SLIPPAGE", "0.001"))        # 시장가 체결 미끄러짐: 임시값
DAILY_PAGES = int(_env("HK_BOT_DAILY_PAGES", "1"))        # ka10081 연속조회 쪽수
MINUTE_PAGES = int(_env("HK_BOT_MINUTE_PAGES", "10"))     # ka10080 연속조회 쪽수
SESSION_OPEN, SESSION_CLOSE = "09:00", "15:30"

# 매도 시 거래세(농특세 포함) 연도별. 2026년 0.20%는 지시서 + 공개 기사 확인.
TAX = {2023: 0.0020, 2024: 0.0018, 2025: 0.0015, 2026: 0.0020}

# --- 등급 C: 탐색 축 (책에 없음, 독립 가설) ---
AXIS = {
    "bar_m": [1, 2, 3, 5],            # 2·3분 필수, 1·5분 대조군
    "confirm": ["touch", "close"],    # 돌파 확정: 장중 터치 / 분봉 종가
    "fail_stop": [False, True],       # 돌파 실패 손절: 분봉 종가가 전고점 아래
    "tp_pct": [5.0, 7.5, 10.0],       # +5~10% 매도 구간 안의 지점
    "last_entry": ["11:00", "14:30"], # 신규 진입 마감 시각
}

# 호가 단위 (2023년 개편 기준, 이번에 공식 문서 대조 안 함 = 미확인)
TICKS = ((2_000, 1), (5_000, 5), (20_000, 10), (50_000, 50), (200_000, 100),
         (500_000, 500), (float("inf"), 1_000))
PRICE_LIMIT = 0.30           # 가격제한폭

# 수집기 허용 목록에 더하는 조회 전용 TR (종목 분류). 주문 TR은 더하지 않는다.
EXTRA_QUERY_TR = {"ka10099": "/api/dostk/stkinfo"}
