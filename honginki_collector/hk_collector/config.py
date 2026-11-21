"""홍인기 단타 수집기 설정. 주문 기능 없음.

'임시값' 표시는 근거 없는 시작값이다. 실측 뒤 Muse가 정한다.
"""
import os
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def _env(name, default):
    return os.environ.get(name, default)


UA = _env("HK_UA", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
REST_BASE = _env("HK_REST_BASE", "https://api.kiwoom.com")
WS_URL = _env("HK_WS_URL", "wss://api.kiwoom.com:10000/api/dostk/websocket")
KEY_FILE = os.path.expanduser(_env("HK_KEY_FILE", "~/kiwoom_key.json"))
DATA_DIR = os.path.expanduser(_env("HK_DATA_DIR", "~/honginki_data"))

# 조회 전용 TR 화이트리스트. 여기 없는 TR은 호출 자체를 거부한다 (주문 TR 차단).
ALLOWED_TR = {
    "au10001": "/oauth2/token",
    "ka10032": "/api/dostk/rkinfo",
    "ka90003": "/api/dostk/stkinfo",
    "ka10063": "/api/dostk/mrkcond",
    "ka10080": "/api/dostk/chart",
    "ka10081": "/api/dostk/chart",
}

# --- 임시값 (근거 없음) ---
REST_MIN_GAP_S = float(_env("HK_REST_MIN_GAP_S", "0.5"))  # REST 호출 사이 최소 간격
POLL_S = float(_env("HK_POLL_S", "60"))                   # REST 폴링 주기
TOP_N = int(_env("HK_TOP_N", "30"))                       # 실시간 구독할 거래대금 상위 수
MAX_SUBS = int(_env("HK_MAX_SUBS", "100"))                # 하루 누적 구독 상한
REG_CHUNK = int(_env("HK_REG_CHUNK", "20"))               # REG 1회당 종목 수
PAGES_10032 = int(_env("HK_PAGES_10032", "1"))
PAGES_10063 = int(_env("HK_PAGES_10063", "1"))
BAR_GRACE_S = float(_env("HK_BAR_GRACE_S", "3"))          # 봉 마감 유예
SESSION_START = _env("HK_SESSION_START", "08:30")         # KST, 평일
SESSION_END = _env("HK_SESSION_END", "15:40")
# --- 임시값 끝 ---

BAR_MINUTES = (1, 2, 3, 5)
RATE_CODES = {1700, 1701, 1702}
TOKEN_RETRY_CODES = {8005, 8003, 8103}
