# ==========================================================
# FILE: meritz_laoer/config.py   (MERITZ_LAOER v2.0.3)
# v2.0.3 (2026-11-18): 설정 intraday_sell_check_sec 추가(당일 매도 확인 간격 초, 기본 120, 0 이면 끔) + validate_settings 에 그 값 검사 한 줄. 나머지 검증·장부 함수는 그대로
# 메리츠 속쓸 적립봇(SOXL 분할매수·부분매도) — 설정·장부
# v2.0.1 (2026-11-18): update_settings 추가 (텔레그램 설정 메뉴용 — 설정 파일 일부 키만 바꿔 저장), _merge 분리. 검증·장부·기존 함수는 그대로
# v2.0.0 (2026-11-18): 적립봇 전환. 설정 키 추가(total_krw·ladder_*·sell_*·rebuy_drop_usd·unit_base·first_buy_mode·max_rounds_per_day·
#   order_type·allow_consecutive_sell, start.mode·filled_levels·rebuy_anchor_usd·rebuy_k), validate_settings 새로 씀,
#   적립 상태 파일 data/accum_state.json (get_accum/save_accum), inject_start 가 상태도 같이 시작.
#   장부(position·ledger)·apply_fill·add_shares·halt 와 V14 용 함수들은 그대로(V14 함수는 이제 안 불림)
# v1.0.2 (2026-11-08): add_shares 추가 — 사용자가 직접 산 주식을 지정 평단으로 장부에 더함 (기존 장부 형식 그대로)
# v1.0.0 (2026-11-08): 첫 버전. hantu_laoer/config.py 에서 V14 가 쓰는 함수만 같은 이름·같은 동작으로 옮김
#   - 옮긴 함수(동작 그대로): get_reverse_state, set_reverse_state, apply_reverse_daily_settlement,
#     increment_reverse_day, get_seed/set_seed, get_split_count, get_target_profit, get_fee, get_compound_rate
#   - 다른 점: 분할수·시드는 기본값 없음(설정 파일 필수). 시작 원금·수량·평단은 설정값으로 주입(입고 평단 안 믿음)
#   - hantu_laoer 는 수정하지 않음 (이 폴더는 독립)
# 설정 파일: /etc/meritz-laoer/settings.json (GitHub 에 올리지 않음, 예시는 settings.example.json)
# 장부 폴더: 설정 state_dir (기본 /var/lib/meritz-laoer) 아래 data/
# ==========================================================
import datetime
import json
import math
import os
import tempfile
from zoneinfo import ZoneInfo

from global_throttle import GlobalThrottle
from accum_strategy import CHOICES, ladder_levels, state_from_start

SETTINGS_PATH = os.environ.get("MERITZ_LAOER_SETTINGS", "/etc/meritz-laoer/settings.json")
EST = ZoneInfo("America/New_York")

# 기본값은 안전한 쪽만 둔다. 금액·분할수는 기본값 없음(설정 필수).
SAFE_DEFAULTS = {
    "enabled": False,                      # 기본 꺼짐. 토스 전량 입고 확인 뒤 승인하고 켬
    "dry_run": True,                       # 모의 실행 (주문 API 를 부르지 않음)
    "transfer_confirmed": False,           # 입고 확인 (사람이 확인 후 true)
    "toss_sniper_stopped_confirmed": False,  # 토스 스나이퍼 정지·미체결 0건 확인 (사람이 확인 후 true)
    "symbol": "SOXL",
    "price_market": "AX",                  # 메리츠 시세 조회용 거래소 구분 (bot_office/fanding_trade.py 와 같음)
    "exch_id": "",                         # 주문용 거래소 번호. 비우면 잔고 행에서 찾음
    "split_count": None,                   # 적립봇: 10 (총 투자금을 10 등분). 비어 있으면 주문 안 함
    "seed_usd": None,                      # (V14 용, 적립봇은 안 씀)
    # ---- 적립봇 (노션 '메리츠 속쓸 적립봇' 2026-11-18)
    "total_krw": None,                     # 총 투자금(원). 금액은 기본값 없음 — 설정 필수
    "ladder_top_usd": 50,                  # 매수 시작가
    "ladder_step_usd": 5,                  # 내려갈 때마다 1회차 ($50~$5 10회)
    "sell_profit_pct": 10,                 # 평단 대비 평가 이익 이 % 에 매도
    "sell_fraction_pct": 50,               # 보유의 이 % 매도 (정수 주 내림)
    "rebuy_drop_usd": 5,                   # 매도 뒤 평단 대비 이만큼 내려갈 때마다 재매수
    "unit_base": None,                     # 노션 Q2: total | cash — 비어 있으면 주문 안 함
    "first_buy_mode": None,                # 노션 Q1: now | wait_top — 비어 있으면 주문 안 함
    "max_rounds_per_day": None,            # 노션 Q4: 하루 최대 회차 수(정수 1 이상) — 비어 있으면 주문 안 함
    "order_type": None,                    # 노션 Q5: LOC | LIMIT — 비어 있으면 주문 안 함
    "allow_consecutive_sell": None,        # 노션 Q6: true | false — 비어 있으면 주문 안 함
    "intraday_sell_check_sec": 120,        # v2.0.3 당일 매도: 장중 이 간격(초)마다 매도 조건 확인. 0 이면 끄고 예전처럼 아침 주문만. LIMIT 주문일 때만 동작
    # ---- 자동환전 (사용자 요청 2026-11-18). 기본 꺼짐. 켜려면 아래 두 값도 설정 필수 (노션 Q11)
    "auto_fx_enabled": False,              # true 면 오늘 매수에 달러가 모자랄 때 원화→달러 환전 신청 (실주문 모드에서만)
    "auto_fx_buffer_pct": None,            # 부족 달러에 더할 여유 % (환율·체결가 변동 대비)
    "auto_fx_max_usd_per_day": None,       # 하루 환전 상한 (달러, 정수)
    # 익절 %: hantu_laoer/config.py DEFAULT_TARGET["SOXL"] (main c53f8d4 기준). 서버 data/profit_config.json 값은 확인 필요
    "target_profit_pct": 12.0,
    # 복리 %: hantu_laoer/config.py DEFAULT_COMPOUND["SOXL"] (익절 이익 중 다음 시드에 더하는 비율)
    "compound_rate_pct": 70.0,
    "fee_pct": 0.07,                       # Super365 미국주식 0.07%
    "start": {"qty": None, "principal_usd": None, "avg_usd": None,
              "mode": None, "filled_levels": None, "rebuy_anchor_usd": None, "rebuy_k": 0,
              "first_round_credit_usd": None},   # 노션 Q3: 기존 보유를 사다리에 어떻게 칠지 (사람이 정함)
    "key_file": "/etc/meritz-laoer/meritz_keys.json",      # 새 메리츠 3번 계좌 키 (P·VR6 키 재사용 금지)
    "expected_key_fp": "",                 # main.py --fingerprint 로 확인한 지문. 다르면 정지
    "forbid_key_files": ["/etc/bot-office/meritz.json", "/etc/bot-office/meritz_vr6.json"],
    "telegram_file": "/etc/meritz-laoer/telegram.json",    # 새 텔레그램 봇 토큰 {"token":..., "chat_id":...}
    "forbid_telegram_files": [],           # 다른 봇 토큰 파일 경로(같은 토큰이면 정지)
    "state_dir": "/var/lib/meritz-laoer",
    "order_time_et": "10:05",              # 주문 시각 (미국 동부). 이 시각~order_deadline_et 사이 1회
    "order_deadline_et": "15:40",          # LOC 접수 마감(15:50) 전
    "sync_time_et": "16:10",               # 체결 확인 시각 (미국 동부)
}


def _merge(user):
    """설정 파일 내용(user) 위에 기본값을 깐 전체 설정"""
    s = json.loads(json.dumps(SAFE_DEFAULTS))
    for k, v in user.items():
        if k == "start" and isinstance(v, dict):
            s["start"].update(v)
        else:
            s[k] = v
    return s


def load_settings(path=None):
    p = path or SETTINGS_PATH
    with open(p, "r", encoding="utf-8") as f:
        user = json.load(f)
    if not isinstance(user, dict):
        raise ValueError("설정 파일 형식 오류 (JSON 객체 아님)")
    return _merge(user)


def _f(v):
    try:
        x = float(str(v if v is not None else 0).replace(",", ""))
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def update_settings(changes, path=None, dry=False):
    """v2.0.1 텔레그램 메뉴용: 설정 파일(JSON)에서 changes 의 키만 바꿔 저장 → {키: (이전 값, 새 값)}.
    - 파일에 적힌 키만 건드림 (기본값을 섞어 쓰지 않음). 바꾼 뒤 validate_settings 에 '새로 생기는' 문제가 있으면 ValueError (저장 안 함)
    - dry=True 면 검사만 하고 쓰지 않음
    - 원자적 저장(같은 폴더 임시 파일 → replace, 권한 유지). 폴더 쓰기 권한이 없으면 파일 자체에 덮어씀. 둘 다 안 되면 OSError
    - 저장 전 원본을 state_dir/data/settings_before_change.json 에 복사, 바꾼 내용을 data/settings_change_log.json 에 기록 (실패해도 무시)"""
    p = path or SETTINGS_PATH
    with GlobalThrottle.get_file_lock(p):
        with open(p, "r", encoding="utf-8") as f:
            text = f.read()
        raw = json.loads(text)
        if not isinstance(raw, dict):
            raise ValueError("설정 파일 형식 오류 (JSON 객체 아님)")
        before = _merge(raw)
        new_raw = dict(raw)
        new_raw.update(changes)
        after = _merge(new_raw)
        old_bad = validate_settings(before)
        new_bad = [b for b in validate_settings(after) if b not in old_bad]
        if new_bad:
            raise ValueError("; ".join(new_bad))
        result = {k: (before.get(k), after.get(k)) for k in changes}
        if dry:
            return result
        data = json.dumps(new_raw, ensure_ascii=False, indent=2) + "\n"
        sd = str(after.get("state_dir") or "")
        try:
            os.makedirs(os.path.join(sd, "data"), exist_ok=True)
            with open(os.path.join(sd, "data", "settings_before_change.json"), "w", encoding="utf-8") as f:
                f.write(text)
            lp = os.path.join(sd, "data", "settings_change_log.json")
            try:
                with open(lp, "r", encoding="utf-8") as f:
                    log = json.load(f)
                if not isinstance(log, list):
                    log = []
            except (OSError, ValueError):
                log = []
            log.append({"at": datetime.datetime.now(EST).isoformat(), "changes": {k: {"old": o, "new": n} for k, (o, n) in result.items()}})
            with open(lp, "w", encoding="utf-8") as f:
                json.dump(log[-200:], f, ensure_ascii=False, indent=2)
        except (OSError, ValueError):
            pass
        try:
            d = os.path.dirname(os.path.abspath(p))
            fd, tmp = tempfile.mkstemp(dir=d, text=True)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                st = os.stat(p)
                os.chmod(tmp, st.st_mode & 0o7777)
                try:
                    os.chown(tmp, st.st_uid, st.st_gid)
                except OSError:
                    pass
                os.replace(tmp, p)
            except Exception:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                raise
        except PermissionError:
            with open(p, "w", encoding="utf-8") as f:     # 폴더는 못 써도 파일은 쓸 수 있는 경우
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        return result


def validate_settings(s):
    """주문 전에 꼭 있어야 하는 값 검사 → 문제 목록 (빈 목록이면 통과)"""
    bad = []
    sc = s.get("split_count")
    if sc is None or _f(sc) < 2 or _f(sc) != int(_f(sc)):
        bad.append("split_count 없음 또는 정수 아님 (적립봇은 10)")
    if s.get("total_krw") is None or _f(s.get("total_krw")) <= 0:
        bad.append("total_krw 없음 (총 투자금, 원)")
    for k in ("ladder_top_usd", "ladder_step_usd", "rebuy_drop_usd", "sell_profit_pct"):
        if _f(s.get(k)) <= 0:
            bad.append(f"{k} 0 이하 또는 없음")
    if not (0 < _f(s.get("sell_fraction_pct")) < 100):
        bad.append("sell_fraction_pct 는 0 초과 100 미만")
    if sc is not None and _f(sc) >= 2 and len(ladder_levels(s.get("ladder_top_usd"), s.get("ladder_step_usd"), _f(sc))) != int(_f(sc)):
        bad.append("사다리 가격이 0 이하로 내려감 — ladder_top_usd·ladder_step_usd·split_count 확인")
    for k, opts in CHOICES.items():
        if s.get(k) not in opts:
            bad.append(f"{k} 미정 ({' | '.join(opts)} 중 Muse 결정 필요 — 노션 질문)")
    mr = s.get("max_rounds_per_day")
    if mr is None or isinstance(mr, bool) or _f(mr) < 1 or _f(mr) != int(_f(mr)):
        bad.append("max_rounds_per_day 미정 (1 이상 정수, Muse 결정 필요 — 노션 질문)")
    if not isinstance(s.get("allow_consecutive_sell"), bool):
        bad.append("allow_consecutive_sell 미정 (true | false, Muse 결정 필요 — 노션 질문)")
    isec = s.get("intraday_sell_check_sec")
    if isinstance(isec, bool) or not isinstance(isec, (int, float)) or not (isec == 0 or 30 <= isec <= 3600):
        bad.append("intraday_sell_check_sec 는 0(끔) 또는 30~3600 (초)")
    if not isinstance(s.get("auto_fx_enabled"), bool):
        bad.append("auto_fx_enabled 는 true | false")
    elif s.get("auto_fx_enabled"):
        if s.get("auto_fx_buffer_pct") is None or _f(s.get("auto_fx_buffer_pct")) < 0:
            bad.append("auto_fx_enabled=true 인데 auto_fx_buffer_pct 없음 (0 이상, 노션 질문 Q11)")
        if s.get("auto_fx_max_usd_per_day") is None or _f(s.get("auto_fx_max_usd_per_day")) <= 0:
            bad.append("auto_fx_enabled=true 인데 auto_fx_max_usd_per_day 없음 (0 초과, 노션 질문 Q11)")
    st = s.get("start") or {}
    q, pr, av = st.get("qty"), st.get("principal_usd"), st.get("avg_usd")
    if q is None or int(_f(q)) < 0 or _f(q) != int(_f(q)):
        bad.append("start.qty 없음 (0 이상 정수)")
    if pr is None or _f(pr) < 0:
        bad.append("start.principal_usd 없음 (0 이상)")
    if q is not None and int(_f(q)) > 0 and (pr is None or _f(pr) <= 0):
        bad.append("start.qty > 0 인데 principal_usd 가 0 이하")
    if q and pr and av is not None and _f(av) > 0 and int(_f(q)) > 0:
        if abs(_f(pr) / int(_f(q)) - _f(av)) > 0.01:
            bad.append("start.avg_usd 가 principal_usd ÷ qty 와 0.01 넘게 다름 — 숫자 확인")
    if not isinstance(st.get("filled_levels"), list):
        bad.append("start.filled_levels 없음 (이미 산 걸로 칠 회차 목록, 없으면 [] — 노션 질문 Q3)")
    if st.get("mode") not in ("ladder", "rebuy"):
        bad.append("start.mode 미정 (ladder | rebuy — 노션 질문 Q3)")
    elif st.get("mode") == "rebuy" and _f(st.get("rebuy_anchor_usd")) <= 0:
        bad.append("start.mode=rebuy 인데 start.rebuy_anchor_usd 없음")
    if st.get("first_round_credit_usd") is not None and _f(st.get("first_round_credit_usd")) < 0:
        bad.append("start.first_round_credit_usd 는 0 이상 (1회차 매수 때 한 번 차감할 달러, 없으면 생략)")
    if str(s.get("symbol", "")).upper() != "SOXL":
        bad.append("이 봇은 SOXL 전용")
    return bad


class ConfigManager:
    """strategy_v14.V14Strategy 가 부르는 함수만 제공. 파일은 현재 작업 폴더 기준 data/ (main 이 state_dir 로 chdir)"""

    def __init__(self, settings):
        self.s = settings
        self.FILES = {
            "SEED_CFG": "data/seed_config.json",
            "REVERSE_CFG": "data/reverse_config.json",
            "LEDGER": "data/manual_ledger.json",
            "HISTORY": "data/manual_history.json",
            "POSITION": "data/position.json",
            "HALT": "data/halt.json",
            "ACCUM": "data/accum_state.json",
        }
        os.makedirs("data", exist_ok=True)

    # ---------------- 파일 입출력 (원자적 저장)
    def _safe_float(self, v):
        return _f(v)

    def _load_json(self, path, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return json.loads(json.dumps(default))

    def _save_json(self, path, data):
        d = os.path.dirname(path) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except Exception:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise

    # ---------------- 설정값 (분할수·익절·수수료·복리)
    def get_split_count(self, t):
        return _f(self.s.get("split_count"))          # 하드코딩 없음 — 설정값만

    def get_target_profit(self, t):
        return _f(self.s.get("target_profit_pct"))

    def get_fee(self, t):
        return _f(self.s.get("fee_pct"))

    def get_compound_rate(self, t):
        return _f(self.s.get("compound_rate_pct"))

    def get_version(self, t):
        return "V14"

    def get_manual_vwap_mode(self, t):
        return False

    # ---------------- 시드: 처음엔 설정 seed_usd, 익절 뒤 복리로 늘어난 값은 장부에 저장
    def get_seed(self, t):
        with GlobalThrottle.get_file_lock(self.FILES["SEED_CFG"]):
            d = self._load_json(self.FILES["SEED_CFG"], {})
            if t in d:
                return _f(d[t])
            return _f(self.s.get("seed_usd"))

    def set_seed(self, t, v):
        with GlobalThrottle.get_file_lock(self.FILES["SEED_CFG"]):
            d = self._load_json(self.FILES["SEED_CFG"], {})
            d[t] = _f(v)
            self._save_json(self.FILES["SEED_CFG"], d)

    # ---------------- 리버스 상태 (hantu_laoer/config.py 와 같은 동작)
    def get_reverse_state(self, ticker):
        with GlobalThrottle.get_file_lock(self.FILES["REVERSE_CFG"]):
            d = self._load_json(self.FILES["REVERSE_CFG"], {})
            val = d.get(ticker)
            if not isinstance(val, dict):
                return {
                    "is_active": False, "day_count": 0, "exit_target": 0.0,
                    "last_update_date": "", "dynamic_t": 0.0, "rem_cash": 0.0, "is_day_one": True,
                    "last_t_update_date": ""
                }
            val.setdefault("dynamic_t", 0.0)
            val.setdefault("rem_cash", 0.0)
            val.setdefault("is_day_one", val.get("day_count", 0) == 0)
            val.setdefault("last_t_update_date", val.get("last_update_date", ""))
            return val

    def set_reverse_state(self, ticker, is_active, day_count, exit_target=0.0, last_update_date=None, dynamic_t=0.0, rem_cash=0.0, is_day_one=None):
        with GlobalThrottle.get_file_lock(self.FILES["REVERSE_CFG"]):
            if last_update_date is None:
                last_update_date = datetime.datetime.now(EST).strftime('%Y-%m-%d')
            d = self._load_json(self.FILES["REVERSE_CFG"], {})
            d[ticker] = {
                "is_active": is_active,
                "day_count": day_count,
                "exit_target": _f(exit_target),
                "last_update_date": last_update_date,
                "last_t_update_date": last_update_date,
                "dynamic_t": _f(dynamic_t),
                "rem_cash": _f(rem_cash),
                "is_day_one": (day_count == 0) if is_day_one is None else bool(is_day_one)
            }
            self._save_json(self.FILES["REVERSE_CFG"], d)

    def apply_reverse_daily_settlement(self, ticker):
        with GlobalThrottle.get_file_lock(self.FILES["REVERSE_CFG"]):
            d = self._load_json(self.FILES["REVERSE_CFG"], {})
            state = d.get(ticker)
            if not isinstance(state, dict) or not state.get("is_active", False):
                return
            today_str = datetime.datetime.now(EST).strftime('%Y-%m-%d')
            last_t_update_date = state.get("last_t_update_date", "") or state.get("last_update_date", "")
            if last_t_update_date == today_str:
                return
            split = self.get_split_count(ticker)
            dynamic_t = _f(state.get("dynamic_t", 0.0))
            rem_cash = _f(state.get("rem_cash", 0.0))
            with GlobalThrottle.get_file_lock(self.FILES["LEDGER"]):
                ledger = self._load_json(self.FILES["LEDGER"], [])
            if not isinstance(ledger, list):
                ledger = []
            target_recs = [
                r for r in ledger
                if isinstance(r, dict) and r.get("ticker") == ticker and r.get("is_reverse", False)
                and last_t_update_date <= str(r.get("date", ""))[:10] < today_str
            ]
            buy_sum = sell_sum = 0.0
            had_buy = had_sell = False
            for r in target_recs:
                amt = int(_f(r.get("qty", 0))) * _f(r.get("price", 0.0))
                if r.get("side") == "BUY":
                    buy_sum += amt
                    had_buy = True
                elif r.get("side") == "SELL":
                    sell_sum += amt
                    had_sell = True
            if had_buy or had_sell:
                rem_cash = max(0.0, rem_cash + sell_sum - buy_sum)
                if had_sell:
                    if split <= 20:
                        dynamic_t *= 0.9
                    else:
                        dynamic_t *= 0.95
                if had_buy:
                    dynamic_t += (split - dynamic_t) * 0.25
            state["rem_cash"] = round(rem_cash, 2)
            state["dynamic_t"] = round(dynamic_t, 4)
            state["last_t_update_date"] = today_str
            d[ticker] = state
            self._save_json(self.FILES["REVERSE_CFG"], d)

    def increment_reverse_day(self, ticker):
        with GlobalThrottle.get_file_lock(self.FILES["REVERSE_CFG"]):
            d = self._load_json(self.FILES["REVERSE_CFG"], {})
            state = d.get(ticker)
            if not isinstance(state, dict):
                return False
            if state.get("is_active"):
                today_est_str = datetime.datetime.now(EST).strftime('%Y-%m-%d')
                if state.get("last_update_date") != today_est_str:
                    state["day_count"] = state.get("day_count", 0) + 1
                    state["last_update_date"] = today_est_str
                    state["is_day_one"] = False
                    d[ticker] = state
                    self._save_json(self.FILES["REVERSE_CFG"], d)
                    return True
        return False

    # ---------------- 보유 장부 (원금·수량은 봇 장부가 기준. 메리츠 입고 평단은 쓰지 않음)
    def get_position(self):
        return self._load_json(self.FILES["POSITION"], None)

    def inject_start(self, overwrite=False):
        """설정 start 값으로 장부 시작 (입고 평단 덮어쓰기). 이미 있으면 overwrite=True 일 때만"""
        with GlobalThrottle.get_file_lock(self.FILES["POSITION"]):
            cur = self.get_position()
            if cur and not overwrite:
                return cur, False
            st = self.s["start"]
            qty, principal = int(_f(st["qty"])), round(_f(st["principal_usd"]), 2)
            pos = {"ticker": self.s["symbol"], "qty": qty, "principal": principal,
                   "cycle_buy_total": principal, "cycle_sell_total": 0.0, "cycle_start": datetime.datetime.now(EST).strftime('%Y-%m-%d'),
                   "source": "settings.start (입고 평단 미사용)"}
            self._save_json(self.FILES["POSITION"], pos)
            self._save_json(self.FILES["ACCUM"], state_from_start(st))
            return pos, True

    # ---------------- 적립 상태 (모드·채운 회차·재매수 기준). 장부와 별도 파일
    def get_accum(self):
        """저장된 적립 상태. 없으면 None"""
        d = self._load_json(self.FILES["ACCUM"], None)
        return d if isinstance(d, dict) else None

    def save_accum(self, st):
        with GlobalThrottle.get_file_lock(self.FILES["ACCUM"]):
            self._save_json(self.FILES["ACCUM"], st)

    def accum_or_start(self):
        """저장된 상태, 없으면 설정 start 로 만든 값(저장하지 않음 — 모의·미리보기용)"""
        return self.get_accum() or state_from_start(self.s.get("start"))

    def add_shares(self, qty, avg, date_et):
        """사용자가 직접 추가한 주식을 지정 평단으로 장부에 더함 → (변경 전, 변경 후).
        수량 += qty, 원금 += qty × avg, 평단 = 원금 ÷ 수량 (avg_price 와 같은 4자리 규칙). 입고 평단은 쓰지 않음"""
        qty, avg = int(qty), _f(avg)
        if qty < 1 or avg <= 0:
            raise ValueError("qty 는 1 이상 정수, avg 는 0 보다 커야 함")
        with GlobalThrottle.get_file_lock(self.FILES["POSITION"]):
            pos = self.get_position()
            if not pos:
                raise RuntimeError("장부 없음 (start 주입 전)")
            before = dict(pos)
            amt = qty * avg
            pos["qty"] = int(pos["qty"]) + qty
            pos["principal"] = round(_f(pos["principal"]) + amt, 4)
            pos["cycle_buy_total"] = round(_f(pos.get("cycle_buy_total")) + amt, 4)
            ledger = self._load_json(self.FILES["LEDGER"], [])
            ledger.append({"id": len(ledger) + 1, "date": date_et, "ticker": pos["ticker"], "side": "BUY",
                           "price": avg, "qty": qty, "avg_price": self.avg_price(before),
                           "exec_id": f"add_{datetime.datetime.now(EST).strftime('%Y%m%dT%H%M%S')}",
                           "is_reverse": bool(self.get_reverse_state(pos["ticker"]).get("is_active"))})
            self._save_json(self.FILES["LEDGER"], ledger)
            self._save_json(self.FILES["POSITION"], pos)
            return before, pos

    def avg_price(self, pos):
        q = int(_f((pos or {}).get("qty")))
        return round(_f(pos.get("principal")) / q, 4) if q > 0 else 0.0

    def apply_fill(self, side, qty, price, date_et, is_reverse, exec_id):
        """체결 1건 반영 → (새 장부, 끝난 사이클 기록 또는 None). 같은 exec_id 는 한 번만"""
        with GlobalThrottle.get_file_lock(self.FILES["POSITION"]):
            pos = self.get_position()
            if not pos:
                raise RuntimeError("장부 없음 (start 주입 전)")
            ledger = self._load_json(self.FILES["LEDGER"], [])
            if any(isinstance(r, dict) and r.get("exec_id") == exec_id for r in ledger):
                return pos, None
            qty, price = int(qty), _f(price)
            if qty <= 0 or price <= 0:
                return pos, None
            avg = self.avg_price(pos)
            if side == "BUY":
                pos["qty"] += qty
                pos["principal"] = round(pos["principal"] + qty * price, 4)
                pos["cycle_buy_total"] = round(pos["cycle_buy_total"] + qty * price, 4)
            else:
                if qty > pos["qty"]:
                    raise RuntimeError(f"매도 체결 {qty}주가 장부 {pos['qty']}주보다 많음")
                pos["qty"] -= qty
                pos["principal"] = round(max(0.0, pos["principal"] - qty * avg), 4) if pos["qty"] > 0 else 0.0
                pos["cycle_sell_total"] = round(pos["cycle_sell_total"] + qty * price, 4)
            ledger.append({"id": len(ledger) + 1, "date": date_et, "ticker": pos["ticker"], "side": side,
                           "price": price, "qty": qty, "avg_price": avg, "exec_id": exec_id, "is_reverse": bool(is_reverse)})
            self._save_json(self.FILES["LEDGER"], ledger)
            done = None
            if pos["qty"] == 0:
                done = self._close_cycle(pos, date_et)
                pos = {"ticker": pos["ticker"], "qty": 0, "principal": 0.0, "cycle_buy_total": 0.0,
                       "cycle_sell_total": 0.0, "cycle_start": date_et, "source": "새출발"}
            self._save_json(self.FILES["POSITION"], pos)
            return pos, done

    def _close_cycle(self, pos, end_date):
        """hantu_laoer/config.py 졸업 정산과 같은 계산: 수수료 반영 이익 × 복리% 를 시드에 더함"""
        t = pos["ticker"]
        fee = self.get_fee(t) / 100.0
        net_in = pos["cycle_buy_total"] * (1.0 + fee)
        net_out = pos["cycle_sell_total"] * (1.0 - fee)
        profit = math.ceil((net_out - net_in) * 100) / 100.0
        yld = math.ceil(((profit / net_in * 100) if net_in > 0 else 0.0) * 100) / 100.0
        rate = self.get_compound_rate(t) / 100.0
        added = 0
        if profit > 0 and rate > 0:
            added = math.floor(profit * rate)
            self.set_seed(t, self.get_seed(t) + added)
        self.set_reverse_state(t, False, 0, 0.0)
        hist = self._load_json(self.FILES["HISTORY"], [])
        rec = {"id": len(hist) + 1, "ticker": t, "start_date": pos.get("cycle_start"), "end_date": end_date,
               "invested": net_in, "revenue": net_out, "profit": profit, "yield": yld, "added_seed": added}
        hist.append(rec)
        self._save_json(self.FILES["HISTORY"], hist)
        return rec

    # ---------------- 정지 표시 (장부·잔고 불일치 등). 사람이 --clear-halt 로 풂
    def halt(self, reason):
        self._save_json(self.FILES["HALT"], {"reason": str(reason), "at": datetime.datetime.now(EST).isoformat()})

    def get_halt(self):
        return self._load_json(self.FILES["HALT"], None)

    def clear_halt(self):
        try:
            os.remove(self.FILES["HALT"])
        except OSError:
            pass
