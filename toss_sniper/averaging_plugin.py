# =====================================================================
# FILE: averaging_plugin.py   (💧 물타기 플러그인 · 사용자 추가 모듈)
# 목적: 원작 '토스 듀얼 스나이퍼' 위에 사용자의 물타기(추가 매수) 매매를 얹는 독립 모듈
#
#  ▸ 원작 파일은 고치지 않고, averaging_merge.py 가 '# [💧물타기 HOOK]' 몇 줄만 자동으로 끼워 넣어 연결합니다.
#    원작자가 새 버전을 내면 → 업데이트 비서가 감지 → 원작 새 파일 + 이 파일 + HOOK 자동 재적용 → staging → 텔레그램 ✅
#
#  ▸ 물타기 규칙 (사용자가 운영하던 v1.0.4 규칙 그대로)
#    1) 원작 스나이퍼가 자동으로 산 포지션(PRE_SNIPER / PRE_SNIPER_REARM)만 대상 (수동 매수·1주 휩소는 제외)
#    2) 직전 매수 뒤 RSI가 35 이상으로 한 번 회복(재장전)했다가 다시 RSI ≤ 30
#       + 현재가가 직전 매수가보다 설정 % (0.3~1.0, 기본 0.7) 이상 싸면 → 1회 추가 매수 (1회 금액 = 통합 시드)
#    3) 최대 매수 횟수(첫 매수 포함 1·2·3·5·7·10회) 까지 · 추가 매수 시간은 원작 본진과 같은 04:07~08:14 EST
#    4) 추가 매수가 체결되면 → 전체 평단가 기준으로 +5% 안전캡 재장전, +1.00% 점화가도 새 평단 기준으로 자동 이동
#       (원작의 하이킨아시 트레일링·NQ 3단 방어·MOC 청산은 새 평단 기준으로 그대로 작동)
#    5) 손절 라인(0=끄기, 1.0~5.0%): 추가 매수가 끝난 뒤(최대 횟수 도달 또는 08:15 매수 마감 이후)
#       현재가가 평단 대비 설정 % 아래면 전량 매도 → 그날 신규 진입 중지
#    6) NQ=F 진폭 2.0% 이상이거나 트레일링이 점화된 상태에서는 추가 매수 안 함
# =====================================================================

import os
import json
import math
import time
import html
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import importlib

from quant_engine import AssassinLedger, MacroDataCache


def _pick(name, default=None):
    """원작이 함수를 다른 파일로 옮겨도 찾아 쓰도록 (원작 버전마다 파일 구성이 바뀜)"""
    for mod in ("defense_plugin", "defense_state_plugin", "sniper_plugin", "sniper_exit_plugin"):
        try:
            m = importlib.import_module(mod)
        except Exception:
            continue
        if hasattr(m, name):
            return getattr(m, name)
    if hasattr(AssassinLedger, name):
        return getattr(AssassinLedger, name)
    if default is not None:
        return default
    raise ImportError(f"[💧물타기] 원작에서 {name} 을(를) 찾지 못했습니다")


_cancel_open_orders_and_wait_sellable = _pick("_cancel_open_orders_and_wait_sellable")
get_trailing_runtime_status = _pick("get_trailing_runtime_status")
TRAIL_ARM_PROFIT_RATE = float(_pick("TRAIL_ARM_PROFIT_RATE", 1.00))
TRAIL_SAFETY_CAP_RATE = float(_pick("TRAIL_SAFETY_CAP_RATE", 5.00))

# ---------------------------------------------------------------- 버전 (봇 화면·부팅 메시지에 표시)
BOT_VERSION = "v1.0.5"          # 업데이트 비서가 적용할 때마다 자동으로 한 칸씩 올림 (CHANGELOG·태그와 같은 번호)
UPSTREAM_REPO = "https://github.com/pipios4006-boop/pipiosToss_bot"
UPSTREAM_COMMIT = "ef79f66d71b7558af19c90bf09f734def7c9f5cc"   # 지금 합쳐 둔 원작 커밋 (averaging_merge.py 가 갱신)
BASE_VERSION = "원작 토스 듀얼 스나이퍼 v58.0"                         # (averaging_merge.py 가 갱신)
VERSION_LABEL = f"{BOT_VERSION} · {BASE_VERSION} + 💧물타기"

EST_TZ = ZoneInfo("America/New_York")
_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(_DIR, "Averaging_settings.json")
STATE_FILE = os.path.join(_DIR, "Averaging_state.json")

AUTO_TAGS = ("PRE_SNIPER", "PRE_SNIPER_REARM")   # 원작이 자동으로 산 포지션 표식
SYMBOLS = ("SOXS", "SOXL")
ADD_REARM_RSI = 35.0          # 직전 매수 뒤 RSI 가 이 값 이상으로 회복해야 다음 추가 매수 준비
ADD_TRIGGER_RSI = 30.0        # 추가 매수 RSI 조건
ADD_ORDER_TIMEOUT_SEC = 60.0  # 추가 매수 지정가가 이 시간 안에 안 잡히면 취소 (다음 기회에 다시)
BUY_WIN_START, BUY_WIN_END = 407, 814   # 원작 본진과 같은 매수 시간 (EST)
SL_WIDE_SPREAD_PCT = 0.5      # 손절 시 호가 간격이 0.5% 넘게 벌어져 있으면
SL_MID_WAIT_SEC = 15.0        #   처음 15초는 중간 가격, 그 뒤 매수 1호가로 정정
ALLOWED_MAX_BUYS = (1, 2, 3, 5, 7, 10)
DEFAULT_SETTINGS = {"enabled": True, "max_buy_count": 5, "add_gap_pct": 0.7, "stop_loss_pct": 0.0}


def _empty_state() -> dict:
    return {
        "adds": 0,               # 이번 포지션에서 낸 추가 매수 횟수 (첫 매수 제외)
        "order_id": "",          # 진행 중인 추가 매수 주문
        "order_ts": 0.0,
        "order_qty": 0,
        "order_price": 0.0,
        "cancel_reason": "",
        "cancel_ts": 0.0,
        "sl_tick": 0.0,
        "last_buy_price": 0.0,   # 직전 매수가 (첫 매수는 체결 평단)
        "prev_buy_price": 0.0,   # 추가 주문이 한 주도 안 잡히고 취소되면 되돌릴 값
        "armed": False,          # RSI 35 회복 확인 여부
        "cap_resync": False,     # 추가 매수 체결 → 안전캡 재장전 필요
        "sl_active": False,      # 손절 진행 중
        "sl_info": None,
        "notes": {},
    }


_SETTINGS: dict = {}
_STATE: dict = {}
_QTY_CHECK_TS: dict = {}
_TG = {"admin_id": None, "wakeup": None}


# ---------------------------------------------------------------- 파일 저장/불러오기
def _atomic_write(path: str, data: dict):
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _normalize_settings(d: dict) -> dict:
    out = dict(DEFAULT_SETTINGS)
    try:
        out["enabled"] = bool(d.get("enabled", True))
    except Exception:
        pass
    try:
        out["max_buy_count"] = max(1, min(10, int(float(d.get("max_buy_count", 5)))))
    except Exception:
        pass
    try:
        g = round(float(d.get("add_gap_pct", 0.7)), 1)
        out["add_gap_pct"] = g if 0.3 <= g <= 1.0 else 0.7
    except Exception:
        pass
    try:
        s = round(float(d.get("stop_loss_pct", 0.0)), 1)
        out["stop_loss_pct"] = s if 1.0 <= s <= 5.0 else 0.0
    except Exception:
        pass
    return out


def get_settings() -> dict:
    """물타기 설정. 처음 실행 시 예전 봇(v1.0.4) 장부 AssassinLedger_SOXS.json 의 설정을 그대로 가져옴."""
    if _SETTINGS:
        return _SETTINGS
    data = None
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = None
    if not isinstance(data, dict):
        old = {}
        try:
            with open(os.path.join(_DIR, "AssassinLedger_SOXS.json"), "r", encoding="utf-8") as f:
                old = json.load(f) or {}
        except Exception:
            old = {}
        data = {k: old[k] for k in ("max_buy_count", "add_gap_pct", "stop_loss_pct") if k in old}
        data = _normalize_settings(data)
        try:
            _atomic_write(SETTINGS_FILE, data)
        except Exception as e:
            print(f"🚨 [물타기 설정 저장 실패] {e}", flush=True)
    _SETTINGS.update(_normalize_settings(data))
    return _SETTINGS


def save_settings(**kw):
    s = dict(get_settings())
    s.update(kw)
    s = _normalize_settings(s)
    _SETTINGS.clear()
    _SETTINGS.update(s)
    _atomic_write(SETTINGS_FILE, s)


def _load_state():
    if _STATE:
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    for sym in SYMBOLS:
        st = _empty_state()
        if isinstance(data, dict) and isinstance(data.get(sym), dict):
            st.update({k: v for k, v in data[sym].items() if k in st})
        _STATE[sym] = st


def _st(symbol: str) -> dict:
    _load_state()
    return _STATE.setdefault(symbol, _empty_state())


def _persist():
    try:
        _atomic_write(STATE_FILE, {k: v for k, v in _STATE.items()})
    except Exception as e:
        print(f"🚨 [물타기 상태 저장 실패] {e}", flush=True)


def reset_symbol(symbol: str = None):
    _load_state()
    for sym in ([symbol] if symbol else SYMBOLS):
        _STATE[sym] = _empty_state()
    _persist()


# /reset (원작 장부 초기화) 때 물타기 횟수·주문 기록도 함께 초기화 — 원작 파일을 고치지 않도록 여기서 감쌈
if not getattr(AssassinLedger.reset_all_ledgers, "_avg_wrapped", False):
    _orig_reset_all = AssassinLedger.reset_all_ledgers

    async def _reset_all_with_avg(*a, **k):
        res = await _orig_reset_all(*a, **k)
        reset_symbol()
        return res

    _reset_all_with_avg._avg_wrapped = True
    AssassinLedger.reset_all_ledgers = staticmethod(_reset_all_with_avg)


def get_status(symbol: str) -> dict:
    st = dict(_st(symbol))
    s = get_settings()
    st["buy_count"] = 1 + int(st.get("adds", 0))
    st["max_buy_count"] = s["max_buy_count"]
    ref = float(st.get("last_buy_price") or 0.0)
    st["next_add_price"] = (math.floor(ref * (1.0 - s["add_gap_pct"] / 100.0) * 100.0) / 100.0) if ref > 0.0 else 0.0
    return st


def _note_once(st: dict, key: str, val: str) -> bool:
    notes = st.setdefault("notes", {})
    if notes.get(key) == val:
        return False
    notes[key] = val
    return True


async def _nq_amp() -> float:
    try:
        _, h, l = await MacroDataCache.get_cached_nq_data()
        return ((h - l) / l * 100.0) if l > 0.0 else 0.0
    except Exception:
        return 0.0


async def _open_sell_left(ctx, symbol: str) -> tuple[int, bool]:
    """(열린 매도 주문의 남은 수량, 열린 매수 주문 존재 여부)"""
    left, has_buy = 0.0, False
    try:
        for o in await ctx.client.get_orders(status="OPEN", symbol=symbol):
            if o.get("side") == "BUY":
                has_buy = True
            elif o.get("side") == "SELL":
                q = float(o.get("quantity") or 0.0)
                fq = float((o.get("execution") or {}).get("filledQuantity") or 0.0)
                left += max(0.0, q - fq)
    except Exception:
        pass
    return int(math.floor(left)), has_buy


# =====================================================================
# 1) 메인 루프 매 틱 호출 — 추가 매수 주문 관리 · 체결 후 안전캡 재장전 · 추가 매수 발사
#    (main.py 에서 manage_mechanical_profit_trap_plugin 직전에 호출)
# =====================================================================
async def averaging_tick(
    ctx, symbol: str, now_est: datetime, *, is_active: bool, holdings_qty: int, holdings_detail: dict,
    current_price: float, live_rsi: float, budget: float, entry_session: str, sell_order_id: str,
) -> bool:
    """원작 장부(AssassinLedger)를 바꿨으면 True → main.py 가 장부를 다시 읽고 원작 익절 플러그인으로 넘김"""
    st = _st(symbol)
    s = get_settings()
    hm = now_est.hour * 100 + now_est.minute
    icon = "🐻" if symbol == "SOXS" else "🐂"

    # --- 0. 진행 중인 추가 매수 주문 상태 확인 (보유 0주여도 먼저 정리)
    if st.get("order_id"):
        await _track_add_order(ctx, symbol, st, hm, is_active, holdings_qty)
        if st.get("order_id"):
            return   # 아직 주문 진행 중이면 이번 틱은 여기까지

    # --- 1. 포지션이 없으면 물타기 상태 초기화 (손절 결과 보고 포함)
    if holdings_qty <= 0:
        if st.get("sl_active") or st.get("sl_info"):
            await _report_stop_loss_fill(ctx, symbol, st)
        if st.get("adds") or st.get("last_buy_price") or st.get("armed") or st.get("cap_resync"):
            reset_symbol(symbol)
        return

    if not is_active or ctx.in_memory_ordering_lock.get(symbol, False):
        return

    avg_price = float((holdings_detail or {}).get("avg_price") or 0.0)
    if avg_price <= 0.0:
        return
    if float(st.get("last_buy_price") or 0.0) <= 0.0:
        st["last_buy_price"] = avg_price      # 첫 매수 체결가 = 기준
        _persist()

    # --- 2-0. 안전망: 자동 진입 포지션인데 열린 매도(안전캡) 수량이 보유보다 적으면 재장전 예약 (체결 타이밍 어긋남 자가 치유)
    if (not st.get("cap_resync") and entry_session in AUTO_TAGS and not st.get("sl_active") and sell_order_id
            and not get_trailing_runtime_status(symbol).get("armed", False)
            and time.time() - float(_QTY_CHECK_TS.get(symbol, 0.0)) >= 5.0):
        _QTY_CHECK_TS[symbol] = time.time()
        sell_left, has_buy = await _open_sell_left(ctx, symbol)
        if not has_buy and 0 < sell_left < holdings_qty:
            st["cap_resync"] = True
            _persist()
            print(f"🩹 [💧물타기 {symbol}] 안전캡 수량 {sell_left}주 < 보유 {holdings_qty}주 → 재장전 예약", flush=True)

    # --- 2. 추가 매수 체결 뒤 안전캡(+5%) 을 전체 수량·새 평단으로 재장전
    if st.get("cap_resync"):
        return await _resync_cap(ctx, symbol, st, holdings_qty, avg_price, sell_order_id, icon)

    # --- 3. 추가 매수 판단
    if not s["enabled"] or s["max_buy_count"] <= 1 or entry_session not in AUTO_TAGS or st.get("sl_active"):
        return
    if live_rsi >= ADD_REARM_RSI and not st.get("armed"):
        st["armed"] = True
        _persist()
    if not (BUY_WIN_START <= hm <= BUY_WIN_END):
        return
    if not (0.0 < live_rsi <= ADD_TRIGGER_RSI) or not st.get("armed"):
        return
    if get_trailing_runtime_status(symbol).get("armed", False):
        return
    buy_count = 1 + int(st.get("adds", 0))
    if buy_count >= s["max_buy_count"]:
        if _note_once(st, "max", f"{now_est.strftime('%Y%m%d')}_{buy_count}"):
            _persist()
            await ctx.notify_tg(
                f"⏸️ <b>[💧물타기 {icon}{symbol}] 최대 매수 {s['max_buy_count']}회 도달</b>\n"
                f"▫️ RSI <code>{live_rsi:.1f}</code> 재포착했지만 더 사지 않고 평단 기준 트레일링 익절만 기다립니다."
            )
        return

    ref = float(st.get("last_buy_price") or avg_price)
    gap_line = math.floor(ref * (1.0 - s["add_gap_pct"] / 100.0) * 100.0) / 100.0
    if current_price <= 0.0 or current_price > gap_line:
        key = f"{buy_count}_{ref:.2f}"
        if _note_once(st, "gap", key):
            print(f"⏳ [💧물타기 대기 {symbol}] RSI {live_rsi:.1f} · 현재가 ${current_price:.2f} > 기준 ${gap_line:.2f} (직전 ${ref:.2f} -{s['add_gap_pct']}%)", flush=True)
        return

    if await _nq_amp() >= 2.0:
        if _note_once(st, "nq", now_est.strftime("%Y%m%d")):
            _persist()
            await ctx.notify_tg(f"🛑 <b>[💧물타기 {icon}{symbol}] 추가 매수 보류</b>\n▫️ NQ=F 당일 진폭 2.0% 이상 (과열) · 보유분 관리는 원작 방어망이 계속합니다.")
        return

    await _place_add_order(ctx, symbol, st, now_est, current_price, live_rsi, budget, buy_count, ref, holdings_qty, avg_price, icon)


async def _place_add_order(ctx, symbol, st, now_est, current_price, live_rsi, budget, buy_count, ref, holdings_qty, avg_price, icon):
    s = get_settings()
    async with ctx.dual_strike_mutex:
        if ctx.in_memory_ordering_lock.get(symbol, False):
            return
        ctx.in_memory_ordering_lock[symbol] = True
        try:
            _, has_buy = await _open_sell_left(ctx, symbol)
            if has_buy:
                return
            st["armed"] = False          # 같은 과매도 구간 중복 주문 방지 (다시 RSI 35 회복 후 재장전)
            latest = await ctx.client.get_current_price(symbol) or current_price
            price = math.floor(latest * 100.0) / 100.0
            gap_line = math.floor(ref * (1.0 - s["add_gap_pct"] / 100.0) * 100.0) / 100.0
            if price <= 0.0 or price > gap_line:
                st["armed"] = True       # 주문 직전에 다시 올랐으면 쉬고 다음 기회
                return
            bp = -1.0
            try:
                bp = await ctx.client.get_usd_buying_power()
                use = min(float(budget), bp * 0.990)
            except Exception:
                use = float(budget)
            qty = int(math.floor(use / price)) if price > 0.0 else 0
            if qty <= 0:
                if _note_once(st, "qty0", f"{now_est.strftime('%Y%m%d')}_{buy_count}"):
                    await ctx.notify_tg(
                        f"⚠️ <b>[💧물타기 {icon}{symbol}] 추가 매수 보류 — 주문 수량 0주</b>\n"
                        f"▫️ 현재가 <code>${price:.2f}</code> | 1회 시드 <code>${float(budget):,.2f}</code> | USD 가능금액 "
                        f"<code>{('$' + format(bp, ',.2f')) if bp >= 0 else '조회실패'}</code>"
                    )
                return
            res = await ctx.client.create_order(
                symbol=symbol, side="BUY", order_type="LIMIT", quantity=qty, price=f"{price:.2f}",
                client_order_id=f"AVG_{symbol}_{now_est.strftime('%H%M%S')}_{buy_count + 1}"[:36],
            )
            oid = str(((res or {}).get("result") or {}).get("orderId") or "") if isinstance(res, dict) else ""
            if not oid:
                st["armed"] = True
                return
            st.update({"order_id": oid, "order_ts": time.time(), "order_qty": qty, "order_price": price,
                       "adds": int(st.get("adds", 0)) + 1, "prev_buy_price": ref, "last_buy_price": price, "cancel_reason": ""})
            ctx.wakeup_event.set()
            await ctx.notify_tg(
                f"💧 <b>[물타기 {icon}{symbol}] RSI≤30 재포착 ➡️ 추가 매수 ({buy_count + 1}/{s['max_buy_count']}회)</b>\n"
                f"▫️ RSI <code>{live_rsi:.1f}</code> (35 회복 뒤 재하락) · 직전 매수가 <code>${ref:.2f}</code> 대비 <code>{(price / ref - 1) * 100:+.2f}%</code>\n"
                f"▫️ 추가 지정가: <code>${price:.2f}</code> × <code>{qty}주</code> (60초 안에 안 잡히면 취소 후 다음 기회)\n"
                f"▫️ 기존 <code>{holdings_qty}주</code> · 평단 <code>${avg_price:.2f}</code> ➡️ 체결 후 새 평단 기준으로 +5% 안전캡 · +1.00% 점화가 재장전"
            )
        except Exception as e:
            st["armed"] = False
            print(f"🚨 [💧물타기 주문 에러 {symbol}] {e}", flush=True)
            if _note_once(st, "err", str(e)[:80]):
                await ctx.notify_tg(f"🚨 <b>[💧물타기 주문 에러 {icon}{symbol}]</b>\n▫️ <code>{html.escape(str(e))}</code>\n▫️ RSI 35 회복 뒤 다시 시도합니다.")
        finally:
            _persist()
            ctx.in_memory_ordering_lock[symbol] = False


async def _track_add_order(ctx, symbol, st, hm, is_active, holdings_qty):
    oid = st["order_id"]
    try:
        od = await ctx.client.get_order_detail(oid)
    except Exception as e:
        if "404" in str(e) or "not-found" in str(e).lower():
            st["order_id"] = ""
            _persist()
        return
    status = str(od.get("status") or "")
    filled = float((od.get("execution") or {}).get("filledQuantity") or 0.0)
    avg_fill = float((od.get("execution") or {}).get("averageFilledPrice") or 0.0)
    icon = "🐻" if symbol == "SOXS" else "🐂"

    if status == "FILLED":
        st.update({"order_id": "", "cap_resync": True})
        if avg_fill > 0.0:
            st["last_buy_price"] = avg_fill
        _persist()
        ctx.wakeup_event.set()
        await ctx.notify_tg(f"✅ <b>[💧물타기 {icon}{symbol}] 추가 매수 체결</b> · <code>{int(filled)}주</code> @ <code>${avg_fill:.2f}</code>\n▫️ 새 평단 기준으로 안전캡·트레일링을 다시 겁니다.")
        return
    if status in ("CANCELED", "REJECTED", "EXPIRED"):
        reason = st.get("cancel_reason") or status
        st["order_id"] = ""
        if filled > 0.0:
            st["cap_resync"] = True
            if avg_fill > 0.0:
                st["last_buy_price"] = avg_fill
        else:
            st["adds"] = max(0, int(st.get("adds", 0)) - 1)   # 한 주도 안 샀으면 횟수·직전 매수가 되돌림
            if float(st.get("prev_buy_price") or 0.0) > 0.0:
                st["last_buy_price"] = float(st["prev_buy_price"])
            st["armed"] = (reason == "timeout")               # 시간 초과만 바로 재시도 허용
        _persist()
        print(f"🧹 [💧물타기 {symbol}] 추가 매수 주문 종료 ({reason}) · 체결 {filled:g}주", flush=True)
        return

    # 아직 미체결 → 취소 사유 확인
    why = ""
    if not is_active:
        why = "off"
    elif time.time() - float(st.get("order_ts") or 0.0) >= ADD_ORDER_TIMEOUT_SEC:
        why = "timeout"
    elif not (BUY_WIN_START <= hm <= BUY_WIN_END):
        why = "window"
    elif holdings_qty <= 0:
        why = "flat"
    elif get_trailing_runtime_status(symbol).get("armed", False):
        why = "trail"
    elif await _nq_amp() >= 2.0:
        why = "nq"
    if why and not ctx.in_memory_ordering_lock.get(symbol, False):
        if time.time() - float(st.get("cancel_ts") or 0.0) < 5.0:
            return   # 방금 취소 요청함 → 체결/취소 확정 대기
        st["cancel_reason"] = why
        st["cancel_ts"] = time.time()
        _persist()
        try:
            await ctx.client.cancel_order(oid)
        except Exception as e:
            if "already-filled" in str(e).lower():
                return
            if "404" in str(e) or "already-canceled" in str(e).lower():
                st["order_id"] = ""
                st["adds"] = max(0, int(st.get("adds", 0)) - 1)
                if float(st.get("prev_buy_price") or 0.0) > 0.0:
                    st["last_buy_price"] = float(st["prev_buy_price"])
                _persist()


async def _resync_cap(ctx, symbol, st, holdings_qty, avg_price, sell_order_id, icon):
    """추가 매수 체결 뒤: 기존 +5% 안전캡(옛 수량)을 취소 → 원작 manage_mechanical_profit_trap_plugin 이
    전체 수량·새 평단 기준 +5% 캡을 다시 장전하도록 장부를 맞춰 둠 (NQ 3차 방어 기준점은 첫 진입 그대로 유지)."""
    if get_trailing_runtime_status(symbol).get("armed", False):
        st["cap_resync"] = False
        _persist()
        return False
    sell_left, has_buy = await _open_sell_left(ctx, symbol)
    if has_buy:
        return False
    try:   # 루프 맨 앞에서 읽은 잔고는 체결 전 값일 수 있으니 새로 조회
        fresh = await ctx.client.get_symbol_holdings_detail(symbol)
        holdings_qty = int(math.floor(float(fresh.get("qty") or 0.0)))
        avg_price = float(fresh.get("avg_price") or 0.0) or avg_price
    except Exception:
        return False
    if holdings_qty <= 0:
        return False
    arm_p = math.ceil(avg_price * (1.0 + TRAIL_ARM_PROFIT_RATE / 100.0) * 100.0) / 100.0
    cap_p = math.ceil(avg_price * (1.0 + TRAIL_SAFETY_CAP_RATE / 100.0) * 100.0) / 100.0
    ctx.in_memory_ordering_lock[symbol] = True
    try:
        if sell_left < holdings_qty or not sell_order_id:
            await _cancel_open_orders_and_wait_sellable(ctx=ctx, symbol=symbol, sell_order_id=sell_order_id, cancel_all_sides=False)
            await AssassinLedger.save_state(symbol, price=avg_price, target_sell_price=arm_p, sell_order_id="")
            ctx.idempotency_keys[symbol]["TRAP"] = None
        else:
            await AssassinLedger.save_state(symbol, price=avg_price, target_sell_price=arm_p)
        st["cap_resync"] = False
        _persist()
        ctx.wakeup_event.set()
        s = get_settings()
        await ctx.notify_tg(
            f"🔄 <b>[💧물타기 {icon}{symbol}] 평단 갱신 ➡️ 안전캡 재장전</b>\n"
            f"▫️ 보유 <code>{holdings_qty}주</code> · 새 평단 <code>${avg_price:.2f}</code> ({1 + int(st.get('adds', 0))}/{s['max_buy_count']}회)\n"
            f"▫️ +1.00% 점화가 <code>${arm_p:.2f}</code> · +5% 안전캡 <code>${cap_p:.2f}</code> (원작 트레일링·NQ 방어 그대로)"
        )
        return True
    except Exception as e:
        print(f"🚨 [💧물타기 안전캡 재장전 {symbol}] {e}", flush=True)
        return False
    finally:
        ctx.in_memory_ordering_lock[symbol] = False


# =====================================================================
# 2) 손절 라인 — 추가 매수가 끝난 뒤(최대 횟수 도달 또는 08:15 이후) 평단 대비 -N% 이하면 전량 매도
#    (main.py 에서 execute_macro_defense_plugin 바로 뒤에 호출 · True 를 돌려주면 이번 틱 종료)
# =====================================================================
async def averaging_stop_loss_tick(
    ctx, symbol: str, now_est: datetime, *, is_active: bool, holdings_qty: int, current_price: float,
    avg_price: float, sell_order_id: str, entry_session: str, current_session_id: str = None,
) -> bool:
    st = _st(symbol)
    if holdings_qty <= 0 or not is_active or ctx.in_memory_ordering_lock.get(symbol, False):
        return False
    s = get_settings()
    icon = "🐻" if symbol == "SOXS" else "🐂"
    triggered = bool(st.get("sl_active"))
    if not triggered:
        sl = float(s["stop_loss_pct"])
        if not s["enabled"] or sl <= 0.0 or entry_session not in AUTO_TAGS or avg_price <= 0.0 or current_price <= 0.0 or st.get("order_id"):
            return False
        hm = now_est.hour * 100 + now_est.minute
        buy_count = 1 + int(st.get("adds", 0))
        finished = (buy_count >= s["max_buy_count"]) or not (BUY_WIN_START <= hm <= BUY_WIN_END)
        if not finished:
            return False
        line = avg_price * (1.0 - sl / 100.0)
        if current_price > line:
            return False
    if time.time() - float(st.get("sl_tick", 0.0) or 0.0) < 3.0:
        return True
    st["sl_tick"] = time.time()

    ctx.in_memory_ordering_lock[symbol] = True
    try:
        if not triggered:
            sl = float(s["stop_loss_pct"])
            st["sl_active"] = True
            st["sl_info"] = {"line": avg_price * (1.0 - sl / 100.0), "avg": avg_price, "pct": sl,
                             "qty": holdings_qty, "ids": [], "since": time.time()}
            _persist()
            # 그날 신규 진입 중지: 원작의 '과열 차단(CANCELED_MACRO)' 표식을 이 종목에 붙여 정산 뒤 자동 재출동을 막음
            # (buy_order_id 는 지우지 않음 → 원작이 수동 매수로 오인하지 않도록)
            await AssassinLedger.save_state(symbol, is_session_done=True, entry_session="CANCELED_MACRO")
            opp = "SOXL" if symbol == "SOXS" else "SOXS"
            opp_st = await AssassinLedger.get_state(opp)
            if int(ctx.shared_holdings.get(opp, 0)) <= 0 and str(opp_st[8] or "") in ("", "CANCELED_MACRO"):
                await AssassinLedger.save_state(opp, is_session_done=True, entry_session="CANCELED_MACRO")
        info = st.get("sl_info") or {"line": 0.0, "avg": avg_price, "pct": s["stop_loss_pct"], "qty": holdings_qty, "ids": [], "since": time.time()}
        st["sl_info"] = info

        sellable, surviving = await _cancel_open_orders_and_wait_sellable(ctx=ctx, symbol=symbol, sell_order_id=sell_order_id, cancel_all_sides=True)
        ob = await ctx.client.get_orderbook(symbol)
        bids, asks = ob.get("bids", []), ob.get("asks", [])
        bid1 = float(bids[0]["price"]) if bids and float(bids[0]["price"]) > 0.0 else current_price
        ask1 = float(asks[0]["price"]) if asks and float(asks[0]["price"]) > 0.0 else 0.0
        if bid1 <= 0.0:
            return True
        px, wide = bid1, False
        if ask1 > bid1 > 0.0 and (ask1 - bid1) / ask1 * 100.0 > SL_WIDE_SPREAD_PCT:
            wide = True
            if time.time() - float(info.get("since", 0.0)) < SL_MID_WAIT_SEC:
                px = max(bid1, math.floor((bid1 + ask1) / 2.0 * 100.0) / 100.0)
        new_id = ""
        if sellable > 0:
            res = await asyncio.wait_for(ctx.client.create_order(
                symbol=symbol, side="SELL", order_type="LIMIT", quantity=min(holdings_qty, sellable), price=f"{px:.2f}",
                client_order_id=f"AVSL_{symbol}_{now_est.strftime('%H%M%S')}_{int(time.time() * 10) % 100}"[:36]), timeout=4.0)
            new_id = str(((res or {}).get("result") or {}).get("orderId") or "") if isinstance(res, dict) else ""
        elif surviving:
            new_id = surviving[0]
            await asyncio.wait_for(ctx.client.modify_order(order_id=new_id, price=f"{px:.2f}", order_type="LIMIT", market_country="US"), timeout=4.0)
        if new_id:
            if new_id not in info["ids"]:
                info["ids"].append(new_id)
            # 원작 장부의 sell_order_id/target_sell_price 는 비워 둠 → 원작 정산이 이 손절을 '익절'로 착각하지 않게
            await AssassinLedger.save_state(symbol, sell_order_id="", target_sell_price=0.0, is_session_done=True, entry_session="CANCELED_MACRO")
        _persist()
        if not triggered:
            buy_count = 1 + int(st.get("adds", 0))
            why = f"최대 {s['max_buy_count']}회 매수 완료" if buy_count >= s["max_buy_count"] else f"08:15 매수 마감 ({buy_count}/{s['max_buy_count']}회)"
            await ctx.notify_tg(
                f"🛑 <b>[💧물타기 손절 {icon}{symbol}] {why} 후 손절 라인 -{info['pct']:.1f}% 도달 ➡️ 전량 매도</b>\n"
                f"▫️ 평단 <code>${avg_price:.2f}</code> | 현재가 <code>${current_price:.2f}</code> (손절선 <code>${info['line']:.2f}</code>)\n"
                + (f"▫️ 호가 간격 넓음(매수 <code>${bid1:.2f}</code> / 매도 <code>${ask1:.2f}</code>) → 15초간 중간가 <code>${px:.2f}</code> 먼저 시도\n" if wide and px > bid1 else "")
                + f"▫️ 안전캡 취소 후 <code>{holdings_qty}주</code> 지정가 <code>${px:.2f}</code> 매도 · 체결될 때까지 정정\n"
                "▫️ 오늘 신규 진입은 멈춥니다 (17:00 EST 정리 후 다음 날 다시 감시)"
            )
    except Exception as e:
        print(f"🚨 [💧물타기 손절 {symbol}] {e}", flush=True)
    finally:
        ctx.in_memory_ordering_lock[symbol] = False
    return True


async def _report_stop_loss_fill(ctx, symbol: str, st: dict):
    info = st.get("sl_info") if isinstance(st.get("sl_info"), dict) else {}
    tq = tv = 0.0
    for oid in info.get("ids", []):
        try:
            ex = (await ctx.client.get_order_detail(oid)).get("execution") or {}
            q, p = float(ex.get("filledQuantity") or 0.0), float(ex.get("averageFilledPrice") or 0.0)
            if q > 0.0 and p > 0.0:
                tq += q
                tv += q * p
        except Exception:
            pass
    icon = "🐻" if symbol == "SOXS" else "🐂"
    if tq <= 0.0:
        await ctx.notify_tg(f"ℹ️ <b>[💧물타기 {icon}{symbol}] 손절 매도 완료</b>\n▫️ 체결 가격은 토스 앱 거래내역에서 확인해 주세요.")
    else:
        fill = tv / tq
        line, avg = float(info.get("line") or 0.0), float(info.get("avg") or 0.0)
        await ctx.notify_tg(
            f"🧾 <b>[💧물타기 {icon}{symbol}] 손절 체결 결과</b>\n"
            + (f"▫️ 손절선 <code>${line:.2f}</code> (평단 <code>${avg:.2f}</code>의 -{float(info.get('pct') or 0):.1f}%)\n" if line > 0 else "")
            + f"▫️ 실제 체결 <code>${fill:.2f}</code> × <code>{tq:g}주</code>\n"
            + (f"▫️ 슬리피지: 손절선보다 <code>{(fill / line - 1) * 100:+.2f}%</code>\n" if line > 0 else "")
            + (f"▫️ 평단 대비 <code>{(fill / avg - 1) * 100:+.2f}%</code>" if avg > 0 else "")
        )
    st["sl_active"] = False
    st["sl_info"] = None
    _persist()


# =====================================================================
# 3) 텔레그램 화면 — 제어반 요약 줄 · /sync 줄 · 💧 물타기 설정 화면
# =====================================================================
def build_averaging_summary() -> str:
    s = get_settings()
    if not s["enabled"]:
        return "\n▫️ 💧 물타기: <code>꺼짐 (원작 그대로 · 손절 라인도 꺼짐)</code>"
    if s["max_buy_count"] <= 1:
        head = "1회 매수 (추가 매수 없음)"
    else:
        head = f"최대 {s['max_buy_count']}회 · 간격 -{s['add_gap_pct']:.1f}%"
    sl = f"-{s['stop_loss_pct']:.1f}%" if s["stop_loss_pct"] > 0 else "꺼짐"
    return f"\n▫️ 💧 물타기: <code>{head} · 손절 라인 {sl}</code>"


def build_averaging_position_line(symbol: str) -> str:
    st = get_status(symbol)
    if float(st.get("last_buy_price") or 0.0) <= 0.0 and not st.get("order_id"):
        return ""
    parts = [f"{st['buy_count']}/{st['max_buy_count']}회"]
    if st.get("order_id"):
        parts.append(f"추가 주문 대기 ${float(st.get('order_price') or 0):.2f}")
    elif st["buy_count"] < st["max_buy_count"] and get_settings()["enabled"]:
        parts.append(f"다음 추가 ≤ ${st['next_add_price']:.2f}")
        parts.append("RSI 재장전 ✅" if st.get("armed") else "RSI 35 회복 대기")
    if st.get("sl_active"):
        parts.append("손절 진행 중")
    return f"\n▫️ 💧 물타기: <code>{' · '.join(parts)}</code>"


def install_ui_wrappers(g: dict):
    """tg_ui_plugin.py 맨 끝에서 한 번 호출 — 원작 화면 함수를 감싸 버전·물타기 줄과 💧 버튼을 덧붙임.
    (원작 화면 코드가 바뀌어도 함수 이름만 같으면 그대로 작동)"""
    menu, settle, sync = g.get("get_main_menu_text"), g.get("build_settlement_board"), g.get("build_sync_board")

    if menu and not getattr(menu, "_avg_wrapped", False):
        async def get_main_menu_text(*a, **k):
            text = await menu(*a, **k)
            return f"{text}\n\n▫️ 버전: <code>{VERSION_LABEL}</code>{build_averaging_summary()}\n▶️ /avg : 💧 물타기 설정"
        get_main_menu_text._avg_wrapped = True
        g["get_main_menu_text"] = get_main_menu_text

    if settle and not getattr(settle, "_avg_wrapped", False):
        async def build_settlement_board(*a, **k):
            text, kb = await settle(*a, **k)
            try:
                rows = list(kb.inline_keyboard)
                rows.insert(max(0, len(rows) - 1), [InlineKeyboardButton(text="💧 물타기 설정", callback_data="avg_panel")])
                kb = InlineKeyboardMarkup(inline_keyboard=rows)
            except Exception:
                pass
            return f"{text}{build_averaging_summary()}", kb
        build_settlement_board._avg_wrapped = True
        g["build_settlement_board"] = build_settlement_board

    if sync and not getattr(sync, "_avg_wrapped", False):
        async def build_sync_board(*a, **k):
            text = await sync(*a, **k)
            extra = "".join(f"\n{'🐻' if s_ == 'SOXS' else '🐂'} {s_}{ln}" for s_ in SYMBOLS if (ln := build_averaging_position_line(s_)))
            return f"{text}\n{extra}" if extra else text
        build_sync_board._avg_wrapped = True
        g["build_sync_board"] = build_sync_board


def inject_averaging_tg(admin_id, wakeup_event):
    _TG["admin_id"] = admin_id
    _TG["wakeup"] = wakeup_event


def _is_admin(obj) -> bool:
    user = getattr(obj, "from_user", None)
    return bool(user and _TG["admin_id"] is not None and getattr(user, "id", None) == _TG["admin_id"])


averaging_router = Router()


class _AvgInput(StatesGroup):
    gap = State()
    stop_loss = State()


def _panel() -> tuple[str, InlineKeyboardMarkup]:
    s = get_settings()
    lines = [
        f"💧 <b>[물타기 설정]</b>  <code>{VERSION_LABEL}</code>",
        "➖➖➖➖➖➖➖➖➖➖➖➖➖➖",
        f"▫️ 상태: <code>{'🟢 켜짐' if s['enabled'] else '🔴 꺼짐 (원작 그대로 · 추가 매수·손절 라인 모두 정지)'}</code>",
        f"▫️ 최대 매수: <code>{s['max_buy_count']}회 (첫 매수 포함 · 1회 금액 = 통합 시드)</code>",
        f"▫️ 추가 규칙: <code>RSI 35 회복 뒤 RSI≤30 재포착 + 직전 매수가보다 -{s['add_gap_pct']:.1f}% 이상 하락 · 04:07~08:14 EST</code>",
        f"▫️ 손절 라인: <code>{('추가 매수 종료(최대 횟수 또는 08:15 마감) 후 평단 -' + format(s['stop_loss_pct'], '.1f') + '% 도달 시 전량 매도') if s['stop_loss_pct'] > 0 else '꺼짐'}</code>",
        "▫️ 익절·방어: <code>원작 그대로 (새 평단 +1.00% 점화 HA 트레일링 · NQ 3단 방어 · 15:59 청산)</code>",
    ]
    for sym in SYMBOLS:
        pl = build_averaging_position_line(sym)
        if pl:
            lines.append(f"{'🐻' if sym == 'SOXS' else '🐂'} {sym}{pl}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=("🔴 물타기 끄기" if s["enabled"] else "🟢 물타기 켜기"), callback_data="avg_toggle")],
        [InlineKeyboardButton(text=(f"✅ {n}회" if n == s["max_buy_count"] else f"{n}회"), callback_data=f"avg_max_{n}") for n in ALLOWED_MAX_BUYS],
        [InlineKeyboardButton(text=f"📉 추가 매수 간격 -{s['add_gap_pct']:.1f}% 변경", callback_data="avg_gap")],
        [InlineKeyboardButton(text=(f"🛑 손절 라인 -{s['stop_loss_pct']:.1f}% 변경" if s["stop_loss_pct"] > 0 else "🛑 손절 라인 설정 (꺼짐)"), callback_data="avg_sl")],
        [InlineKeyboardButton(text="⚙️ 전술 제어반", callback_data="open_settlement"),
         InlineKeyboardButton(text="🔙 메인 메뉴", callback_data="back_to_main")],
    ])
    return "\n".join(lines), kb


async def _refresh(cq: types.CallbackQuery, toast: str = ""):
    text, kb = _panel()
    try:
        await cq.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    try:
        await cq.answer(toast)
    except Exception:
        pass


@averaging_router.message(Command("avg"))
async def _cmd_avg(message: types.Message, state: FSMContext):
    if not _is_admin(message):
        return
    await state.clear()
    text, kb = _panel()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@averaging_router.callback_query(F.data == "avg_panel")
async def _cb_panel(cq: types.CallbackQuery, state: FSMContext):
    if not _is_admin(cq):
        return
    await state.clear()
    await _refresh(cq)


@averaging_router.callback_query(F.data == "avg_toggle")
async def _cb_toggle(cq: types.CallbackQuery, state: FSMContext):
    if not _is_admin(cq):
        return
    save_settings(enabled=not get_settings()["enabled"])
    await _refresh(cq, "💧 물타기 " + ("켜짐" if get_settings()["enabled"] else "꺼짐"))


@averaging_router.callback_query(F.data.startswith("avg_max_"))
async def _cb_max(cq: types.CallbackQuery, state: FSMContext):
    if not _is_admin(cq):
        return
    try:
        n = int(cq.data.replace("avg_max_", ""))
    except Exception:
        n = 5
    save_settings(max_buy_count=n)
    await _refresh(cq, f"🔁 최대 매수 {get_settings()['max_buy_count']}회")


@averaging_router.callback_query(F.data == "avg_gap")
async def _cb_gap(cq: types.CallbackQuery, state: FSMContext):
    if not _is_admin(cq):
        return
    await state.set_state(_AvgInput.gap)
    try:
        await cq.message.edit_text(
            "⌨️ <b>추가 매수 간격 설정</b>\n\n"
            "▫️ RSI 35 회복 뒤 다시 RSI≤30이 됐을 때, 현재가가 <b>직전 매수가보다 몇 % 이상 싸야</b> 추가 매수할지 숫자로 보내 주세요.\n"
            "▫️ <b>0.3 ~ 1.0</b> 사이, 소수점 첫째 자리까지 (예: <code>0.7</code>)\n"
            f"▫️ 현재: <code>-{get_settings()['add_gap_pct']:.1f}%</code>", parse_mode="HTML")
    except Exception:
        pass


@averaging_router.message(_AvgInput.gap)
async def _in_gap(message: types.Message, state: FSMContext):
    if not _is_admin(message):
        return
    raw = (message.text or "").strip().replace("%", "").replace("-", "")
    try:
        v = float(raw)
        if round(v, 1) != v or not 0.3 <= v <= 1.0:
            raise ValueError()
    except Exception:
        await message.answer("🚨 <b>0.3 ~ 1.0</b> 사이 숫자(소수점 첫째 자리까지)를 보내 주세요. 예: <code>0.7</code>", parse_mode="HTML")
        return
    save_settings(add_gap_pct=v)
    await state.clear()
    text, kb = _panel()
    await message.answer(f"✅ <b>추가 매수 간격 -{v:.1f}% 설정 완료</b>\n\n" + text, reply_markup=kb, parse_mode="HTML")


@averaging_router.callback_query(F.data == "avg_sl")
async def _cb_sl(cq: types.CallbackQuery, state: FSMContext):
    if not _is_admin(cq):
        return
    await state.set_state(_AvgInput.stop_loss)
    s = get_settings()
    try:
        await cq.message.edit_text(
            "⌨️ <b>손절 라인 설정</b>\n\n"
            f"▫️ 추가 매수가 끝난 뒤(최대 {s['max_buy_count']}회 도달 또는 08:15 매수 마감), 현재가가 <b>전체 평단 대비 몇 % 아래</b>면 전량 매도할지 보내 주세요.\n"
            "▫️ <b>1.0 ~ 5.0</b> (소수점 첫째 자리) · <code>0</code> = 끄기\n"
            f"▫️ 현재: <code>{('-' + format(s['stop_loss_pct'], '.1f') + '%') if s['stop_loss_pct'] > 0 else '꺼짐'}</code>", parse_mode="HTML")
    except Exception:
        pass


@averaging_router.message(_AvgInput.stop_loss)
async def _in_sl(message: types.Message, state: FSMContext):
    if not _is_admin(message):
        return
    raw = (message.text or "").strip().replace("%", "").replace("-", "")
    try:
        v = float(raw)
        if v != 0.0 and (round(v, 1) != v or not 1.0 <= v <= 5.0):
            raise ValueError()
    except Exception:
        await message.answer("🚨 <b>1.0 ~ 5.0</b> 사이 숫자나 <code>0</code>(끄기)을 보내 주세요. 예: <code>2.5</code>", parse_mode="HTML")
        return
    save_settings(stop_loss_pct=v)
    await state.clear()
    text, kb = _panel()
    await message.answer((f"✅ <b>손절 라인 -{v:.1f}% 설정 완료</b>\n\n" if v > 0 else "✅ <b>손절 라인을 껐습니다</b>\n\n") + text,
                         reply_markup=kb, parse_mode="HTML")
