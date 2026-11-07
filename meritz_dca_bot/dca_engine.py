# =====================================================================
# FILE: meritz_dca_bot/dca_engine.py   (MERITZ_DCA v1.0.0)
# 목적: 설정 파일(서버 /etc/meritz-accum/settings.json) 읽기 + 종목 상태 저장(DcaConfigManager)
# v1.0.0 (2026-11-08): 첫 버전.
#   - DcaConfigManager.load/save 는 3번 toss_dca_bot/dca_engine.py 와 같은 동작 (원자적 os.replace 저장)
#   - 다른 점: 상태 파일은 봇 폴더가 아니라 settings.state_dir 아래 (GitHub 폴더에 장부를 두지 않음)
#     · 실주문: dca_config.json  · 모의(dry_run): dca_config.dry.json (실제 장부는 바뀌지 않음)
#   - 3번의 evaluate_dca_decision·execute_stock_dca_step 은 3번 main.py 스케줄러가 쓰지 않는 옛 경로라 옮기지 않음
#   - 금액·분할·시드는 하드코딩하지 않음: 시작 상태는 settings.start 에서만 들어옴 (--inject-start)
# =====================================================================
import asyncio
import copy
import json
import os

SETTINGS_PATH = os.environ.get("MERITZ_DCA_SETTINGS", "/etc/meritz-accum/settings.json")

# 기본값은 안전한 쪽만. 금액·수량·평단·지문은 기본값 없음 (설정 필수)
SAFE_DEFAULTS = {
    "enabled": False,                    # 기본 꺼짐: 매매 판단·주문 모두 안 함 (조작판은 동작)
    "dry_run": True,                     # 모의 실행: 주문 API 를 부르지 않음, 모의 장부에만 기록
    "transfer_confirmed": False,         # 메리츠 4번 입고 확인 (사람이 확인 후 true). false 면 실주문 없음
    "key_file": "/etc/meritz-accum/meritz_keys.json",
    "expected_key_fp": "",               # main.py --fingerprint 값. 다르면 정지
    "forbid_key_fps": [],                # P·VR6·3번 SOXL 키 지문(앞 12자리). 같으면 정지
    "forbid_key_files": ["/etc/bot-office/meritz.json", "/etc/bot-office/meritz_vr6.json",
                         "/etc/meritz-laoer/meritz_keys.json"],
    "telegram_env_file": "/home/gieokkim/toss_dca_bot/.env",   # 3번 기존 토큰 재사용 (새 봇 없음)
    "poll_block_service": "toss_dca",    # 이 서비스가 살아 있으면 텔레그램 폴링을 하지 않음 (같은 토큰 충돌 방지)
    "state_dir": "/var/lib/meritz-dca",
    "order_time_et": "10:05",            # 미국 동부. 이 시각~order_deadline_et 사이 하루 1번
    "order_deadline_et": "15:40",
    "missed_alert_et": "10:20",          # 이 시각 뒤에도 안 된 종목이 있으면 미진행 알림 (하루 1번)
    "sync_time_et": "16:10",             # 이 시각까지 체결이 안 보이면 체결 없음으로 정리
    "buy_cash_buffer_pct": 1.0,          # 시장가 매수 달러 검사 여유 (현재가 × 수량 × (1+여유%))
    "us_int_buy_mode": "carry",          # 정수 주문: carry=남은 금액 다음 날로 이월 / min1=3번 한국주식처럼 최소 1주
    "exclude_symbols": ["SOXL", "SOXS", "TQQQ", "SQQQ"],       # 잔고 자동 등록에서 뺄 심볼
    "markets": {},                       # {"NKE": {"mrkt": "NY", "exch_id": "0321"}} 비우면 자동으로 찾음
    "start": {},                         # --inject-start 로 넣을 시작 상태 (README 참고)
}


def load_settings(path=None):
    p = path or SETTINGS_PATH
    with open(p, "r", encoding="utf-8") as f:
        user = json.load(f)
    if not isinstance(user, dict):
        raise ValueError("설정 파일 형식 오류 (JSON 객체 아님)")
    s = copy.deepcopy(SAFE_DEFAULTS)
    s.update(user)
    return s


def config_path(settings, dry=None):
    dry = settings.get("dry_run", True) if dry is None else dry
    return os.path.join(settings["state_dir"], "dca_config.dry.json" if dry else "dca_config.json")


class DcaConfigManager:
    """종목별 설정·진행 상태·장부를 원자적으로 저장. 경로는 main 이 use() 로 정함 (실주문/모의 분리)."""

    CONFIG_FILE = ""
    _locks = {}
    DEFAULT_CONFIG = {
        "is_master_active": False,
        "us_exec_time": "10:05",
        "active_symbol": "",
        "stocks": {},
    }

    @classmethod
    def use(cls, path):
        cls.CONFIG_FILE = path

    @classmethod
    def _lock(cls):
        lk = cls._locks.get(cls.CONFIG_FILE)
        if lk is None:
            lk = cls._locks[cls.CONFIG_FILE] = asyncio.Lock()
        return lk

    @classmethod
    def read_sync(cls, path=None):
        p = path or cls.CONFIG_FILE
        if not p or not os.path.exists(p):
            return copy.deepcopy(cls.DEFAULT_CONFIG)
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return copy.deepcopy(cls.DEFAULT_CONFIG)
            merged = copy.deepcopy(cls.DEFAULT_CONFIG)
            merged.update(data)
            if not isinstance(merged.get("stocks"), dict):
                merged["stocks"] = {}
            return merged
        except Exception:
            return copy.deepcopy(cls.DEFAULT_CONFIG)

    @classmethod
    def write_sync(cls, config_data, path=None):
        p = path or cls.CONFIG_FILE
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        tmp = f"{p}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, p)

    @classmethod
    async def load(cls) -> dict:
        async with cls._lock():
            return await asyncio.to_thread(cls.read_sync)

    @classmethod
    async def save(cls, config_data: dict):
        async with cls._lock():
            await asyncio.to_thread(cls.write_sync, config_data)
