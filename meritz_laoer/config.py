# ==========================================================
# FILE: meritz_laoer/config.py   (MERITZ_LAOER v1.0.0)
# 메리츠 SOXL 무한매수(V14) 새 봇 — 설정·장부
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
    "split_count": None,                   # 20/40/80 — 이체 후 결정. 비어 있으면 주문 안 함
    "seed_usd": None,                      # 총 시드(USD). 실제 환전 USD 로 확정. 비어 있으면 주문 안 함
    # 익절 %: hantu_laoer/config.py DEFAULT_TARGET["SOXL"] (main c53f8d4 기준). 서버 data/profit_config.json 값은 확인 필요
    "target_profit_pct": 12.0,
    # 복리 %: hantu_laoer/config.py DEFAULT_COMPOUND["SOXL"] (익절 이익 중 다음 시드에 더하는 비율)
    "compound_rate_pct": 70.0,
    "fee_pct": 0.07,                       # Super365 미국주식 0.07%
    "start": {"qty": None, "principal_usd": None, "avg_usd": None},
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


def load_settings(path=None):
    p = path or SETTINGS_PATH
    with open(p, "r", encoding="utf-8") as f:
        user = json.load(f)
    if not isinstance(user, dict):
        raise ValueError("설정 파일 형식 오류 (JSON 객체 아님)")
    s = json.loads(json.dumps(SAFE_DEFAULTS))
    for k, v in user.items():
        if k == "start" and isinstance(v, dict):
            s["start"].update(v)
        else:
            s[k] = v
    return s


def _f(v):
    try:
        x = float(str(v if v is not None else 0).replace(",", ""))
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def validate_settings(s):
    """주문 전에 꼭 있어야 하는 값 검사 → 문제 목록 (빈 목록이면 통과)"""
    bad = []
    sc = s.get("split_count")
    if sc is None or _f(sc) < 2 or _f(sc) != int(_f(sc)):
        bad.append("split_count 없음 또는 정수 아님 (20/40/80 중 결정 후 입력)")
    if s.get("seed_usd") is None or _f(s.get("seed_usd")) <= 0:
        bad.append("seed_usd 없음 (실제 환전 USD 로 확정 후 입력)")
    st = s.get("start") or {}
    q, pr, av = st.get("qty"), st.get("principal_usd"), st.get("avg_usd")
    if q is None or int(_f(q)) <= 0 or _f(q) != int(_f(q)):
        bad.append("start.qty 없음")
    if pr is None or _f(pr) <= 0:
        bad.append("start.principal_usd 없음")
    if q and pr and av is not None and _f(av) > 0 and int(_f(q)) > 0:
        if abs(_f(pr) / int(_f(q)) - _f(av)) > 0.01:
            bad.append("start.avg_usd 가 principal_usd ÷ qty 와 0.01 넘게 다름 — 숫자 확인")
    if _f(s.get("target_profit_pct")) <= 0:
        bad.append("target_profit_pct 0 이하")
    if str(s.get("symbol", "")).upper() != "SOXL":
        bad.append("이 봇은 SOXL 전용 (TQQQ 는 나중에 별도)")
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
            return pos, True

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
