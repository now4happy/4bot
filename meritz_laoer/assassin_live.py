# ==========================================================
# FILE: meritz_laoer/assassin_live.py   (MERITZ_LAOER v2.15.0 · 판 41 할 일 1 — 암살자 실전 루프 연결)
# 원작 암살자(orig_sniper/assassin_plugin.py, 한 줄도 안 고침)의 틱 함수 execute_simulated_assassin_tick_plugin 을 메리츠 API 로 부르는 얇은 어댑터.
# 원작은 context.api(토스 API 모양)로 시세·주문·정정·취소·체결 조회를 한다 → 여기서 같은 모양의 async 메서드를 메리츠 API 위에 만든다. 원작 로직은 여기서 다시 쓰지 않음.
#
# 연결한 것: ① 1분봉 = 1분 폴링 누적(barbell_adapter.bars_add, 메리츠 1분봉 API 가 40봉 고정이라 직접 조회 불가 — 지시문) ② 지정가 주문 ③ 정정(modify, 본문 6필드 — 공식 스펙 확인됨, 수정 1차) ④ 취소 ⑤ 체결 조회
# 미확인(보고서에 같은 내용): LIMIT 주문 유효기간(공식 문서에 없음 — DAY 로 가정하지 않음: 주문 상태는 매번 조회해 확인하고 원작의 시간 제한·취소 로직이 처리) ·
#   주문일(oder_date)을 미국 동부 날짜로 보냄(기존 판 42 취소와 같은 방식 — 메리츠가 한국 날짜를 받는지 미확인) · 1분봉은 종가만 모은 근사(시·고·저=종가, 거래량 0 → VWAP 계열 지표는 원작 값과 다를 수 있음)
# 안전: SGOV(원작이 승격 때 SGOV 미체결을 정리하려 부름) 는 사용자 수동 매도에 위임하는 종목이라 이 어댑터에서 건드리지 않음. 모의(dry) 면 주문 없이 가짜 번호.
# ==========================================================
import asyncio
import logging
import os
import sys
import threading
import time

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orig_sniper")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import assassin_plugin as AP         # noqa: E402  원작 복사본 (orig_sniper/)
import quant_engine_core as QC       # noqa: E402

import barbell_adapter as BB         # noqa: E402  1분 봉 누적·암살자 원장(공유 1개)

TARGET = AP.TARGET_SYMBOL            # "SOXL"
MACRO = AP.MACRO_REF_SYMBOL          # "QQQ"
CLS_LIMIT = "01"                     # 메리츠 지정가 (main.ORDER_TYPES["LIMIT"] 와 같은 값 — 취소·정정 때 oder_cls_code)
IDLE_RESULTS = ("WEEKEND_CLOSED", "WAIT_0407_OPEN", "ASSASSIN_DISABLED", "NO_TRADE_OFFWORK_0815", "NO_LIVE_PRICE")      # 이 결과면 이번엔 할 일 없음 (틱 간격을 늘림)
_CTX = {"ctx": None, "key": None}


def _run(coro):
    return asyncio.run(coro)


class MeritzAssassinApi:
    """원작 context.api 모양 (async) → 메리츠 API. read = 부른 쪽이 준 api(캐시 있는 래퍼 가능), 주문·취소·정정 = 원래 api(api.raw 가 있으면 그것).
    fills_fn() = {주문번호: {"qty","amt","side","sym","t"}} (main.fill_rows_for) · date_fn() = 주문일 'YYYYMMDD' (미국 동부 날짜) · status_fn() = 장운영 코드"""

    def __init__(self, api, settings, fills_fn, date_fn, dry=False, state_dir=""):
        self.api, self.raw = api, getattr(api, "raw", api)
        self.s, self.fills_fn, self.date_fn, self.dry, self.state_dir = settings or {}, fills_fn, date_fn, bool(dry), state_dir
        self.orders = {}                      # 주문번호 → {"side","qty","price","date","canceled"} (이 프로세스가 낸 주문. 재시작하면 사라짐 → 조회로 다시 구성)
        self.sim_seq = 0

    # ---- 시세
    def _px(self, symbol):
        return float(self.api.price(symbol, self.s["price_market"])["price"])

    async def get_current_price(self, symbol, **kw):
        return self._px(symbol)

    async def get_current_prices_batch(self, symbols):
        out = {}
        for sy in symbols:
            try:
                out[sy] = self._px(sy)
            except Exception as e:
                logging.warning(f"암살자 시세 조회 실패 {sy}: {type(e).__name__}")
        return out

    async def get_best_bid_price(self, symbol, fallback_price=0.0):
        """메리츠 호가 조회를 안 씀 → 현재가(없으면 fallback)"""
        try:
            return self._px(symbol)
        except Exception:
            return float(fallback_price or 0.0)

    # ---- 캔들 (1분 폴링 누적 — 메리츠 1분봉 API 가 40봉 고정이라 직접 못 받음)
    async def get_candles_1m(self, symbol, count=200, total_count=400):
        bars = BB._rw(os.path.join(self.state_dir, "data", "assassin", f"bars_{symbol}.json"), []) or []
        return BB.bars_candles(bars[-int(total_count or count):])

    async def get_candles_1d(self, symbol, count=10):
        """메리츠 일봉(종가만)을 원작 캔들 모양으로 (오래된 → 최신). 시·고·저=종가, 거래량 0"""
        rows = list(reversed(self.api.daily_closes(symbol, self.s["price_market"])[:int(count)]))
        out = []
        for d, c in rows:
            ts = f"{d[:4]}-{d[4:6]}-{d[6:8]}T00:00:00+00:00"
            out.append({"timestamp": ts, "openPrice": c, "highPrice": c, "lowPrice": c, "closePrice": c, "volume": 0.0, "currency": "USD"})
        return out

    # ---- 계좌
    async def get_buying_power_usd(self, safety_buffer_pct=0.0):
        """USD 예수금 × (1 − 안전여유%) — 안전여유 단위가 퍼센트(0.2 = 0.2%)라고 봄(미확인)"""
        return max(0.0, float(self.api.usd_cash()) * (1.0 - float(safety_buffer_pct or 0.0) / 100.0))

    async def get_holdings_map_with_status(self, symbol=None, **k):
        try:
            q = int(self.api.holding(symbol or TARGET)[0])
        except Exception:
            return {}, False
        return ({symbol or TARGET: {"qty": q}} if q > 0 else {}), True

    async def get_sellable_quantity(self, symbol, **kw):
        return int(self.raw.holding(symbol)[1])          # 캐시 말고 지금 값 (원작이 매도 직전 매도가능수량을 기다림)

    async def get_open_orders(self, symbol=None, **kw):
        return list(self.api.open_orders_today(symbol or TARGET))

    # ---- 주문
    def _exch(self, symbol):
        e = str(self.s.get("exch_id") or "")
        if e:
            return e
        h = self.raw.holding(symbol)
        return str(h[2] or "")

    async def place_limit_order(self, symbol=None, side="BUY", quantity=0, price=0.0, client_order_id=None, enforce_daymarket_block=False, **k):
        symbol, side, qty, px = symbol or TARGET, str(side).upper(), int(quantity), float(price)
        if symbol != TARGET:
            raise RuntimeError(f"암살자 어댑터는 {TARGET} 주문만 냄 ({symbol} 거절)")
        if qty < 1 or px <= 0:
            raise RuntimeError("주문 수량·가격 이상")
        if self.dry:
            self.sim_seq += 1
            oid = f"SIM-{symbol}-{self.sim_seq}"
        else:
            if enforce_daymarket_block and side == "BUY":          # 원작: 데이마켓(야간) 매수 금지 — 여기서는 매수 가능 장운영 코드(프리·정규)만
                import sniper_mode as SN
                st = str(self.api.us_market_status())
                if st not in SN.BUY_STATUS:
                    raise RuntimeError(f"장운영 코드 {st} — 매수 안 냄")
            exch = self._exch(symbol)
            if not exch:
                raise RuntimeError("거래소 번호를 알 수 없음 (설정 exch_id)")
            r = self.raw.order(side, symbol, exch, "LIMIT", qty, px)
            oid = str(r.get("no") or "").strip()
            if not oid:
                raise RuntimeError("주문 응답에 주문번호가 없음")
            self._drop_cache()
        self.orders[oid] = {"side": side, "qty": qty, "price": px, "date": self.date_fn(), "canceled": False, "ts": time.time()}
        return {"orderId": oid}

    def _drop_cache(self):
        c = getattr(self.api, "_c", None)
        if isinstance(c, dict):
            c.clear()

    def _remaining(self, oid):
        """주문의 남은 수량 = 낸 수량 − 체결 수량 (낸 수량을 모르면 미체결 조회의 잔량)"""
        meta = self.orders.get(str(oid)) or {}
        filled = int(((self.fills_fn() or {}).get(str(oid)) or {}).get("qty", 0)) if self.fills_fn else 0
        if meta.get("qty"):
            return max(0, int(meta["qty"]) - filled)
        for r in self.raw.open_orders_today(TARGET):
            if str(r.get("oder_no", "")).strip() == str(oid):
                return int(float(r.get("ncnt_qty") or 0))
        return 0

    async def cancel_order(self, order_id, *a, **k):
        oid = str(order_id)
        rem = self._remaining(oid)
        if self.dry:
            (self.orders.get(oid) or {}).update(canceled=True)
            return {"status": "CANCELED"}
        if rem < 1:
            return {"status": "ALREADY_DONE"}
        date = (self.orders.get(oid) or {}).get("date") or self.date_fn()
        self.raw.cancel_order(oder_date=date, orgl_oder_no=oid, oder_cls_code=CLS_LIMIT, odqt=rem)
        (self.orders.get(oid) or {}).update(canceled=True)
        self._drop_cache()
        return {"status": "CANCELED"}

    async def modify_order(self, order_id, new_price):
        """가격 정정 → {"orderId": 새 주문번호(없으면 원래 번호)}. 실패하면 예외 (원작이 잡고 취소 후 재주문 쪽으로 감). 요청 본문 필드명은 미확인 (meritz_api.modify_order 주석)"""
        oid = str(order_id)
        meta = self.orders.get(oid)
        if meta is None:
            raise RuntimeError(f"정정할 주문 {oid} 의 정보를 모름 (이 프로세스가 낸 주문이 아님)")
        rem = self._remaining(oid)
        if rem < 1:
            raise RuntimeError("남은 수량 없음 — 정정 안 함")
        px = float(new_price)
        if self.dry:
            meta["price"] = px
            return {"orderId": oid}
        r = self.raw.modify_order(oder_date=meta.get("date") or self.date_fn(), orgl_oder_no=oid, oder_cls_code=CLS_LIMIT, odqt=rem, price=px)
        new_no = str(r.get("no") or oid)
        self._drop_cache()
        if new_no != oid:
            self.orders[new_no] = dict(meta, price=px, qty=rem, ts=time.time())
            meta["canceled"] = True
        else:
            meta["price"] = px
        return {"orderId": new_no}

    async def cancel_all_open_orders(self, symbol=None, **k):
        """그 종목의 미체결을 모두 취소. SOXL 만 — SGOV 등 다른 종목은 건드리지 않음 (사용자 수동 관리)"""
        if (symbol or TARGET) != TARGET:
            return {"status": "SKIPPED_NOT_TARGET"}
        n = 0
        for r in list(self.raw.open_orders_today(TARGET)):
            no, rem = str(r.get("oder_no", "")).strip(), int(float(r.get("ncnt_qty") or 0))
            if not no or rem < 1:
                continue
            if not self.dry:
                self.raw.cancel_order(oder_date=(self.orders.get(no) or {}).get("date") or self.date_fn(), orgl_oder_no=no, oder_cls_code=CLS_LIMIT, odqt=rem)
            (self.orders.get(no) or {}).update(canceled=True)
            n += 1
        if n:
            self._drop_cache()
        return {"status": "CANCELED", "count": n}

    # ---- 체결 조회
    async def get_order_detail(self, oid):
        """원작 모양 {"status", "price", "execution": {"filledQuantity","averageFilledPrice"}}. status: FILLED · PARTIAL_FILLED · PENDING · CANCELED (닫혔는데 전량 체결 아님).
        LIMIT 유효기간이 미확인이라 '미체결 목록에 없고 체결도 없음'은 CANCELED 로 단정하지 않고 PENDING 으로 둠 (체결 조회 지연일 수 있음 — 원작의 대기 시간 제한이 처리)"""
        oid = str(oid)
        meta = self.orders.get(oid) or {}
        row = ((self.fills_fn() or {}).get(oid) or {}) if self.fills_fn else {}
        fq = int(row.get("qty", 0))
        amt = float(row.get("amt", 0.0))
        want = int(meta.get("qty") or 0)
        is_open = False
        if not self.dry:
            for r in self.raw.open_orders_today(TARGET):
                if str(r.get("oder_no", "")).strip() == oid and float(r.get("ncnt_qty") or 0) > 0:
                    is_open = True
                    break
        if want and fq >= want:
            st = "FILLED"
        elif meta.get("canceled") and not is_open:
            st = "CANCELED"
        elif fq > 0 and not is_open and not self.dry:
            st = "CANCELED"                         # 일부만 체결되고 닫힘 (취소·정정으로 새 번호가 됨 등)
        elif fq > 0:
            st = "PARTIAL_FILLED"
        else:
            st = "PENDING"
        return {"status": st, "price": float(meta.get("price") or 0.0), "execution": {"filledQuantity": fq, "averageFilledPrice": (amt / fq if fq else 0.0)}}

    async def probe_latest_manual_fill_price(self, side="SELL", target_qty=1, fallback_price=0.0, symbol=None, **k):
        """오늘 가장 최근 체결 중 방향·종목이 같은 것의 평균 체결가 → (가격, 수량). 못 찾으면 (0.0, 0) — 원작은 그때 fallback 을 씀"""
        try:
            rows = [r for r in (self.fills_fn() or {}).values() if r.get("side") == side and (not r.get("sym") or r.get("sym") == (symbol or TARGET)) and int(r.get("qty", 0)) > 0]
        except Exception:
            return 0.0, 0
        if not rows:
            return 0.0, 0
        r = sorted(rows, key=lambda x: str(x.get("t") or ""))[-1]
        return round(float(r["amt"]) / int(r["qty"]), 4), int(r["qty"])


class SoxlShim:
    """원작 context.ledger 모양: 하이브리드 상태를 원작이 읽는 키로 보여 줌 (읽기 전용 — 원작이 쓰는 값은 메모리에만 두고 하이브리드 장부는 안 건드림).
    state_fn() = {"initial_seed_usd", "buckets"(StratumBucket dict 목록), "sub_buckets", "buy_order_id", "sell_order_id"}"""

    def __init__(self, state_fn):
        self.state_fn, self.extra = state_fn, {}

    def get_state(self, symbol=None):
        st = dict(self.state_fn())
        st.update(self.extra)
        return st

    async def update_state(self, symbol=None, **kw):
        self.extra.update(kw)
        return self.get_state()


class LiveContext:
    """원작 함수에 넘기는 context. alerts 에 원작 알림(title, body)이 쌓임 → 호출한 쪽이 텔레그램으로 보냄"""

    def __init__(self, api, settings, fills_fn, date_fn, state_fn, dry=False):
        sd = settings["state_dir"]
        self.state_dir = sd
        self.base_dir = BB.assassin_base_dir(sd)
        self.api = MeritzAssassinApi(api, settings, fills_fn, date_fn, dry=dry, state_dir=sd)
        self.ledger = SoxlShim(state_fn)
        self.assassin_ledger = BB.assassin_ledger(sd, float(state_fn().get("initial_seed_usd") or QC.DEFAULT_INITIAL_SEED_USD))
        self.alerts = []
        self.wakeup_event = threading.Event()
        self.assassin_high_freq_active = False
        self.latest_prices = {}
        self.candle_metrics_cache = {}
        self.exit_snapshot_cache = {}
        self.indexing_grace_cache = {}

    async def send_slim_alert(self, title, body=""):
        self.alerts.append((str(title), str(body)))


def get_context(api, settings, fills_fn, date_fn, state_fn, dry=False):
    """프로세스 안에서 한 개만 유지 (원작 지표 캐시·암살자 원장이 틱 사이에 이어져야 함). api 가 바뀌어도(캐시 래퍼 새로 만듦) 같은 context 에 새 api 만 꽂음"""
    key = (settings["state_dir"], bool(dry))
    if _CTX["ctx"] is None or _CTX["key"] != key:
        _CTX["ctx"], _CTX["key"] = LiveContext(api, settings, fills_fn, date_fn, state_fn, dry=dry), key
    ctx = _CTX["ctx"]
    ctx.api.api, ctx.api.raw = api, getattr(api, "raw", api)
    ctx.api.s, ctx.api.fills_fn, ctx.api.date_fn = settings, fills_fn, date_fn
    ctx.ledger.state_fn = state_fn
    return ctx


def tick(ctx, now_est):
    """원작 암살자 틱 한 번 (모의⇄0주예약⇄실전 통합 상태 머신). 결과 글자(원작 반환값)를 돌려줌. 알림은 ctx.alerts 에 쌓임"""
    return _run(AP.execute_simulated_assassin_tick_plugin(ctx, now_est=now_est))


def promote(ctx, want_live):
    """원작 toggle_assassin_live_promotion 그대로 (승격·0주 예약·복귀) → 원작 반환 dict"""
    return _run(AP.toggle_assassin_live_promotion(ctx, target_live=bool(want_live)))
