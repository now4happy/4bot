# ==========================================================
# FILE: meritz_laoer/barbell_adapter.py   (MERITZ_LAOER v2.9.0 7차 — 판 34 1차·부분)
# 원작 바벨(orig_sniper/barbell_plugin.py)·암살자(orig_sniper/assassin_plugin.py) 복사본을 한 줄도 안 고치고 부르는 얇은 어댑터. 원작 로직은 여기서 다시 쓰지 않음.
# 판 34 2차(부분): context 모양 맞추기(shim) 추가 — SOXL 원장 shim(JSON 파일)·API shim·알림 수집기. 원작 함수는 그대로 부르고 여기서 로직을 다시 쓰지 않음.
#   [3차] 수익금은 금고 대신 SCHD 누적 매수(원작과 다름·풀이님 결정 Q7), free_cash 장부(켤 때 $9,000−미완성 F 원가), 수혈 워터폴 매수 직전 검문(원작 guard 그대로), SGOV 실주문(메리츠 api.order 경유), 30초 틱→1분 종가 봉·암살자 모의 지표.
#   (2차) 연결된 것: 수익금 금고 기록(SOXL 매도 체결 → record_barbell_realized_profit), SGOV 틱(모의 전용, 실주문 안 나감).  미연결: 수혈 워터폴(guard30/injection) — REPORT.md 참조
# 암살자: 모의(SIMULATED) 고정. 실전(LIVE)으로 바꾸는 코드 없음 (assassin_is_live 는 원작 함수 그대로 부르고, 실전이면 켜지 않음).
# ==========================================================
import asyncio
import datetime
import json
import os
import sys
import threading

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orig_sniper")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import barbell_plugin as BP          # noqa: E402  원작 복사본 (orig_sniper/)
import assassin_plugin as AP         # noqa: E402
import quant_indicators_plugin as QI  # noqa: E402  암살자 1분 지표 원작 함수

MODE_BARBELL = BP.PORTION_MODE_BARBELL


def seed_splits(seed_usd):
    """바벨 60/30/10 배분 — 원작 compute_barbell_seed_splits 그대로"""
    return BP.compute_barbell_seed_splits(seed_usd)


def in_sgov_window(now_est=None):
    """SGOV 매매 허용 시간창(평일 09:31~15:55 EST) — 원작 is_sgov_regular_trading_window 그대로"""
    return BP.is_sgov_regular_trading_window(now_est=now_est)


def sgov_sell_qty(seed_usd, sgov_price, held_qty):
    """현금 10% 상당 SGOV 정수 주(내림) — 원작 compute_sgov_10pct_sell_qty 그대로"""
    return BP.compute_sgov_10pct_sell_qty(seed_usd, sgov_price, held_qty)


def open_ledger(state_dir, seed_usd):
    """바벨 전용 원장(BarbellLedger)을 state_dir/data/barbell 안에 만들거나 읽음 (스나이퍼·탑쌓기 원장과 파일이 분리됨)"""
    d = os.path.join(state_dir, "data", "barbell")
    os.makedirs(d, exist_ok=True)
    return BP.BarbellLedger(base_dir=d, initial_seed_usd=seed_usd)


def assassin_is_live(state):
    """암살자 원장 상태가 실전(LIVE)인지 — 원작 is_assassin_live_mode_state 그대로"""
    return AP.is_assassin_live_mode_state(state)


def assassin_default_mode():
    """암살자 기본 모드 (모의 SIMULATED) — 원작 상수"""
    return AP.ASSASSIN_MODE_SIMULATED


# ---------------------------------------------------------------- 판 34 2차: 원작 async 함수가 요구하는 context 모양 shim
class _SoxlLedgerShim:
    """원작 context.ledger 모양 (get_state 동기, update_state 비동기). 하이브리드 장부와 분리된 JSON 파일(state_dir/data/barbell/soxl_shim.json)에 저장"""
    def __init__(self, state_dir, seed_usd):
        self.path = os.path.join(state_dir, "data", "barbell", "soxl_shim.json")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._lock = threading.Lock()
        self.st = {"initial_seed_usd": float(seed_usd), "portion_mode": MODE_BARBELL, "is_active": True, "free_cash_usd": 0.0,
                   "injected_reserve_usd": 0.0, "buckets": [], "sub_buckets": [], "buy_order_id": "", "sell_order_id": "", "logical_date": ""}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.st.update(json.load(f))
        except (OSError, ValueError):
            pass
        self.st["initial_seed_usd"] = float(seed_usd)
        self.st["portion_mode"] = MODE_BARBELL

    def get_state(self, symbol=None):
        return dict(self.st)

    async def update_state(self, symbol=None, **kw):
        with self._lock:
            self.st.update(kw)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.st, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
            return dict(self.st)

    async def rollover_daily_counters_if_needed(self, sess_date):
        return await self.update_state(logical_date=str(sess_date))


class _ApiShim:
    """원작 context.api 모양 → 메리츠 API. dry=True 면 주문 안 나감(가짜 주문번호). dry=False 면 meritz.order(side, 종목, 거래소, "LIMIT", 수량, 가격) 로 실주문 (SOXL 과 같은 방식).
    거래소: 그 종목 보유 조회의 거래소 값 → 없으면 설정 sgov_exch_id → exch_id. 체결 조회: fills_fn() = {주문번호: {side,qty,amt}}. 취소: meritz 에 cancel 함수가 있을 때만 (없으면 미확인 → 원작이 DAY 주문으로 그냥 둠)"""
    def __init__(self, price_fn, dry=True, meritz=None, settings=None, fills_fn=None):
        self.price_fn, self.dry, self.orders = price_fn, bool(dry), []
        self.m, self.s, self.fills_fn, self.ordered = meritz, settings or {}, fills_fn, {}

    async def get_current_price(self, symbol, **kw):
        return float(self.price_fn(symbol))

    async def get_best_bid_price(self, symbol, fallback_price=0.0):
        return float(fallback_price or self.price_fn(symbol))

    async def get_best_ask_price(self, symbol, fallback_price=0.0):
        return float(fallback_price or self.price_fn(symbol))

    def _hold(self, symbol):
        if self.m is None:
            return 0, 0, ""
        h = self.m.holding(symbol)
        return int(h[0]), int(h[1]), str(h[2] or "")

    async def get_sellable_quantity(self, symbol, **kw):
        return self._hold(symbol)[1]

    async def get_holdings_map_with_status(self, symbol=None, **k):
        if self.m is None or self.dry:
            return {}, False
        q = self._hold(symbol)[0]
        return ({symbol: {"qty": q}} if q > 0 else {}), True

    async def create_order(self, symbol=None, side="BUY", quantity=0, price=0.0, order_type="LIMIT", **k):
        if self.dry or self.m is None:
            self.orders.append((symbol, side, quantity, price))
            oid = f"SIM-{symbol}-{len(self.orders)}"
            self.ordered[oid] = (side, int(quantity))
            return {"orderId": oid}
        exch = self._hold(symbol)[2] or str(self.s.get("sgov_exch_id") or self.s.get("exch_id") or "")
        r = self.m.order(side, symbol, exch, "LIMIT", int(quantity), float(price))
        oid = str(r.get("no") or "").strip()
        if not oid:
            raise RuntimeError("주문 응답에 주문번호가 없음")
        self.ordered[oid] = (side, int(quantity))
        return {"orderId": oid}

    async def get_order_detail(self, oid):
        if self.dry or self.fills_fn is None:
            return {"status": "PENDING", "execution": {"filledQuantity": 0, "averageFilledPrice": 0.0}}
        r = (self.fills_fn() or {}).get(str(oid))
        q = int(r["qty"]) if r else 0
        amt = float(r["amt"]) if r else 0.0
        want = self.ordered.get(str(oid), ("", 0))[1]
        st = "FILLED" if (q > 0 and want and q >= want) else ("PARTIAL_FILLED" if q > 0 else "PENDING")
        return {"status": st, "execution": {"filledQuantity": q, "averageFilledPrice": (amt / q if q else 0.0)}}

    async def cancel_order(self, oid, *a, **k):
        fn = getattr(self.m, "cancel", None) if self.m is not None else None
        if self.dry or fn is None:
            return {"status": "CANCEL_UNSUPPORTED"}
        fn(str(oid))
        return {"status": "CANCELED"}


class Context:
    """원작 함수에 넘기는 context. alerts 에 원작 알림(title, body)이 쌓임 → 호출한 쪽이 텔레그램으로 보냄"""
    def __init__(self, state_dir, seed_usd, price_fn, dry=True, meritz=None, settings=None, fills_fn=None):
        self.state_dir = state_dir
        self.base_dir = os.path.join(state_dir, "data", "barbell")
        self.ledger = _SoxlLedgerShim(state_dir, seed_usd)
        self.api = _ApiShim(price_fn, dry, meritz, settings, fills_fn)
        self.alerts = []
        self.barbell_ledger = open_ledger(state_dir, seed_usd)
        self.wakeup_event = threading.Event()

    async def send_slim_alert(self, title, body=""):
        self.alerts.append((str(title), str(body)))


def _run(coro):
    """동기 코드(main.py)에서 원작 async 함수 부르기"""
    return asyncio.run(coro)


def record_profit(ctx, net_pnl_usd):
    """SOXL 매도 체결 순이익 → 수익금 금고 기록 (원작 record_barbell_realized_profit 그대로, 원장 파일에만 기록·API 호출 없음)"""
    return _run(BP.record_barbell_realized_profit(ctx, float(net_pnl_usd)))


def sgov_tick(ctx, now_est=None):
    """SGOV 틱 (원작 execute_barbell_sgov_tick_plugin 그대로). 정규장 09:31~15:55 EST 밖이면 원작이 알아서 건너뜀"""
    return _run(BP.execute_barbell_sgov_tick_plugin(ctx, now_est=now_est))


# ---------------------------------------------------------------- 판 34 3차
def _rw(path, default=None, data=None):
    """작은 JSON 파일 읽기/쓰기 (원자적)"""
    if data is None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return default
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return data


def free_cash_init_once(ctx, incomplete_f_cost):
    """Q6: 바벨을 켠 뒤 처음 한 번 free_cash = 총 SOXL 몫(원작 60%) − 미완성 F 원가 (0 아래로 안 내려감). 이미 했으면 그대로"""
    st = ctx.ledger.get_state()
    if st.get("free_init"):
        return st["free_cash_usd"]
    base = seed_splits(st["initial_seed_usd"])["soxl_seed_60_usd"]
    v = round(max(0.0, base - float(incomplete_f_cost or 0.0)), 4)
    _run(ctx.ledger.update_state(free_cash_usd=v, free_init=True))
    return v


def free_cash_add(ctx, delta):
    """Q6: 매수 체결 −, 매도 체결 + (수혈은 원작 guard 가 shim 원장에 직접 +)"""
    cur = float(ctx.ledger.get_state().get("free_cash_usd") or 0.0)
    _run(ctx.ledger.update_state(free_cash_usd=round(max(0.0, cur + float(delta)), 4)))
    return ctx.ledger.get_state()["free_cash_usd"]


def buy_gate(ctx, raw_bp_usd, px, portion_budget, cost_usd, trigger="hybrid_buy", target_qty=0):
    """SOXL 매수 직전 4단계 수혈 검문 = 원작 evaluate_and_execute_barbell_guard30_or_injection 그대로 → (진행 여부, 설명 dict). 암살자가 실전이면 새 매매 막음"""
    if assassin_blocks(ctx.state_dir):
        return False, {"action": "ASSASSIN_LIVE_BLOCK"}
    ok, _free, _bp, info = _run(BP.evaluate_and_execute_barbell_guard30_or_injection(
        ctx, ctx.ledger.get_state(), float(raw_bp_usd), float(px), float(portion_budget), float(cost_usd), False, trigger, int(target_qty)))
    return bool(ok), info


def assassin_blocks(state_dir):
    """암살자 상태가 실전(LIVE)이면 새 스나이퍼·바벨 매매 막음 (원작 is_assassin_live_mode_state). 모의 고정이라 지금은 항상 False"""
    st = _rw(os.path.join(state_dir, "data", "barbell", "assassin_sim.json"), {}) or {}
    return bool(assassin_is_live({"execution_mode": st.get("execution_mode", assassin_default_mode())}))


# ---- Q7: 실현수익 → SCHD 누적 매수 (원작 금고와 다름)
SCHD = "SCHD"


def schd_path(state_dir):
    return os.path.join(state_dir, "data", "barbell", "schd.json")


def schd_add(state_dir, pnl):
    """실현수익(양수만)을 SCHD 매수 대기금에 더함 → 대기금 반환"""
    p = schd_path(state_dir)
    d = _rw(p, {"pending_usd": 0.0, "bought_qty": 0, "spent_usd": 0.0}) or {}
    if float(pnl) > 0:
        d["pending_usd"] = round(float(d.get("pending_usd") or 0.0) + float(pnl), 4)
        _rw(p, data=d)
    return d.get("pending_usd", 0.0)


def schd_try_buy(state_dir, price, buy_fn):
    """대기금으로 살 수 있는 만큼(정수 주)만 지정가 매수. 1주 값에 못 미치면 안 사고 모음. buy_fn(수량, 가격)→주문번호(없으면 예외). 실패하면 대기금 그대로"""
    p = schd_path(state_dir)
    d = _rw(p, {"pending_usd": 0.0, "bought_qty": 0, "spent_usd": 0.0}) or {}
    price = float(price)
    if price <= 0:
        return {"status": "NO_PRICE"}
    qty = int(float(d.get("pending_usd") or 0.0) // price)
    if qty < 1:
        return {"status": "WAIT_MORE", "pending_usd": d.get("pending_usd", 0.0)}
    oid = buy_fn(qty, price)
    cost = round(qty * price, 4)
    d["pending_usd"] = round(max(0.0, float(d["pending_usd"]) - cost), 4)
    d["bought_qty"] = int(d.get("bought_qty") or 0) + qty
    d["spent_usd"] = round(float(d.get("spent_usd") or 0.0) + cost, 4)
    d["last_order"] = str(oid)
    _rw(p, data=d)
    return {"status": "ORDERED", "qty": qty, "price": price, "order": str(oid)}


# ---- Q9: 30초 틱 → 1분 종가 봉 (VWAP 안 만듦, 시가·고가·저가도 종가와 같게)
def bars_add(state_dir, symbol, price, now=None, keep=400):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    key = now.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:00+00:00")
    p = os.path.join(state_dir, "data", "barbell", f"bars_{symbol}.json")
    bars = _rw(p, []) or []
    if bars and bars[-1]["timestamp"] == key:
        bars[-1]["closePrice"] = round(float(price), 4)
    else:
        bars.append({"timestamp": key, "closePrice": round(float(price), 4)})
    bars = bars[-keep:]
    _rw(p, data=bars)
    return bars


def bars_candles(bars):
    """원작 지표 함수가 읽는 모양(open=high=low=close, 거래량 0)"""
    return [{"timestamp": b["timestamp"], "openPrice": b["closePrice"], "highPrice": b["closePrice"], "lowPrice": b["closePrice"],
             "closePrice": b["closePrice"], "volume": 0.0, "currency": "USD"} for b in bars]


def assassin_sim_metrics(state_dir, soxl_bars, qqq_bars, soxl_px, qqq_px, now_est=None):
    """암살자 모의 지표 = 원작 quant_indicators_plugin 의 1분 지표 함수 그대로. 결과는 assassin_sim.json 에 기록 (모의, 주문 없음)"""
    sm = QI.compute_soxl_quant_metrics_1m(bars_candles(soxl_bars), live_price=float(soxl_px), now_est=now_est)
    qm = QI.compute_qqq_macro_metrics_1m(bars_candles(qqq_bars), live_price=float(qqq_px), now_est=now_est)
    keep = {k: sm.get(k) for k in ("vel_1m_pct", "vel_3m_pct", "vel_5m_pct", "rsi_14", "live_price")}
    keep.update({k: qm.get(k) for k in ("qqq_vel_1m_pct", "qqq_vel_3m_pct", "qqq_vel_5m_pct")})
    _rw(os.path.join(state_dir, "data", "barbell", "assassin_sim.json"),
        data={"execution_mode": assassin_default_mode(), "bars_soxl": len(soxl_bars), "bars_qqq": len(qqq_bars), "metrics": keep,
              "at": datetime.datetime.now().isoformat()})
    return keep
