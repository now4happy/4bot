import os, sys, time, json, glob, inspect, asyncio, requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from toss_api import TossApiClient
from dca_engine import DcaConfigManager, execute_stock_dca_step

BOT_VERSION = "v4.3.1"
KST_TZ, EST_TZ = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNIPER_DIR = "/home/gieokkim/toss_sniper"
VER_HISTORY_FILE = os.path.join(BASE_DIR, "update_history.json")

load_dotenv(os.path.join(BASE_DIR, ".env"))
TOSS_ID, TOSS_SECRET = os.getenv("TOSS_CLIENT_ID", "").strip(), os.getenv("TOSS_CLIENT_SECRET", "").strip()
TG_TOKEN, CHAT_ID = os.getenv("TELEGRAM_BOT_TOKEN", "").strip(), os.getenv("TELEGRAM_CHAT_ID", "").strip()
fail_reasons = {}

def tg_api(method, payload=None):
    if not TG_TOKEN: return None
    try: return requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/{method}", json=payload, timeout=10).json()
    except: return None

def send_panel(text, inline_kb, msg_id=None):
    payload = {"chat_id": CHAT_ID, "text": text, "reply_markup": {"inline_keyboard": inline_kb}}
    if msg_id:
        payload["message_id"] = msg_id
        res = tg_api("editMessageText", payload)
        if res and (res.get("ok") or "not modified" in str(res.get("description", ""))): return
    tg_api("sendMessage", payload)

def check_holiday():
    if datetime.now(KST_TZ).weekday() >= 5: return True, "주말 휴장 (Weekend)"
    return False, "정상 개장일 (시스템 대기 중)"

def get_sniper_seed() -> float:
    """2번 스나이퍼(인피니트 스노우볼, SOXL) 현 장부 기준 다음 1회 매수에 필요한 달러.
    1회분 = 코어자산 × 8% (코어자산 = max(기준시드, 가용현금 + 보유 원가)), 가용현금보다 많으면 가용현금까지.
    장부를 못 찾거나 가동 OFF 면 0 (예전처럼 아무 숫자나 추측하지 않음)."""
    best = None
    for p in glob.glob(os.path.join(SNIPER_DIR, "soxl_stratum_ledger*.json")):
        try:
            mt = os.path.getmtime(p)
            if best is None or mt > best[0]:
                best = (mt, p)
        except OSError:
            pass
    if not best:
        return 0.0
    try:
        with open(best[1], "r", encoding="utf-8") as f:
            d = json.load(f)
        st = d.get("SOXL", d) if isinstance(d, dict) else {}
        if not isinstance(st, dict) or st.get("is_active") is False:
            return 0.0
        num = lambda v: float(v) if isinstance(v, (int, float)) else float(str(v or 0).replace(",", "") or 0)
        seed, free = num(st.get("initial_seed_usd")), num(st.get("free_cash_usd"))
        invested = sum(num(b.get("actual_cost_usd")) for b in (st.get("buckets") or []) if isinstance(b, dict))
        portion = max(seed, free + invested) * 0.08
        return round(max(0.0, min(portion, free)), 2)
    except Exception:
        return 0.0

async def ensure_cycle_fields():
    cfg = await DcaConfigManager.load()
    changed = False
    for k, v in [("kr_exec_time","11:00"), ("us_exec_time","11:30"), ("cycle_mode","buy_1"), ("cycle_day",0), ("max_days",100), ("tp1_pct",10.0), ("sr_pct",20.0), ("last_fail_alert_kr",""), ("last_fail_alert_us","")]:
        if k not in cfg: cfg[k] = v; changed = True
    if changed: await DcaConfigManager.save(cfg)
    return cfg
async def sync_holdings_from_toss(client: TossApiClient):
    cfg = await ensure_cycle_fields()
    stocks = cfg.get("stocks", {})
    changed = False
    for m_name in ["get_all_holdings", "get_holdings", "get_account_holdings", "get_positions", "get_portfolio"]:
        fn = getattr(client, m_name, None)
        if fn:
            try:
                res = await asyncio.wait_for(fn(), timeout=4.0)
                items = res if isinstance(res, list) else (res.get("items", res.get("holdings", res.get("data", []))) if isinstance(res, dict) else [])
                if isinstance(items, list):
                    for it in items:
                        if not isinstance(it, dict): continue
                        sym = str(it.get("symbol", it.get("ticker", it.get("stock_code", "")))).upper().strip()
                        if not sym or sym in ["SOXS", "SOXL", "USD", "KRW"]: continue
                        q = sum(float(it[k]) for k in ["qty", "quantity", "holding_qty", "balance"] if it.get(k))
                        if q > 0 and sym not in stocks:
                            is_kr = sym.isdigit()
                            stocks[sym] = {"name": it.get("name", sym), "currency": "KRW" if is_kr else "USD", "market": "KR" if is_kr else "US", "base_amount": 100000.0 if is_kr else 40.0, "target_profit_pct": float(cfg.get("tp1_pct", 10.0)), "sell_ratio_pct": float(cfg.get("sr_pct", 20.0)), "enabled": False, "has_held": True}
                            changed = True
            except Exception: pass
            break
    if changed: await DcaConfigManager.save(cfg)
    return cfg

async def smart_us_buy(client: TossApiClient, sym: str, buy_amt: float, cur_p: float, ord_id: str):
    # 실제 존재하는 달러 금액 매수 함수만 호출. 오류를 삼키고 다른 방식으로 또 주문하면 중복 매수가 날 수 있어 그대로 올려보냄
    return await client.place_us_fractional_buy(sym, round(buy_amt, 2), ord_id)

async def auto_detect_cycle_days(client, sym: str, is_kr: bool, base_amt: float, avg_p: float, qty: float) -> int:
    # 1. 토스 API에서 체결/거래내역 조회 메서드가 있는지 탐색
    for m_name in ["get_order_history", "get_orders", "get_executions", "get_trade_history", "get_filled_orders"]:
        fn = getattr(client, m_name, None)
        if fn:
            try:
                res = await asyncio.wait_for(fn(sym), timeout=3.0) if len(inspect.signature(fn).parameters) >= 1 else await asyncio.wait_for(fn(), timeout=3.0)
                items = res if isinstance(res, list) else (res.get("items", res.get("orders", res.get("data", []))) if isinstance(res, dict) else [])
                buy_dates = set()
                for it in items:
                    if not isinstance(it, dict): continue
                    s_code = str(it.get("symbol", it.get("ticker", it.get("stock_code", sym)))).upper()
                    side = str(it.get("side", it.get("order_type", it.get("tr_type", "buy")))).lower()
                    status = str(it.get("status", it.get("state", "filled"))).lower()
                    if s_code == sym and ("buy" in side or "매수" in side) and ("fill" in status or "체결" in status or "완료" in status):
                        dt = str(it.get("date", it.get("filled_at", it.get("created_at", it.get("ord_dt", "")))))[:10]
                        if dt: buy_dates.add(dt)
                if len(buy_dates) > 0:
                    return min(99, len(buy_dates))
            except Exception: pass
    # 2. 보유 수량 * 평단가(총 매수원금)를 기준금액으로 나누어 매수 일수 자동 역산
    if qty > 0 and avg_p > 0 and base_amt > 0:
        invested = qty * avg_p
        est_days = int(round(invested / base_amt))
        return max(1, min(99, est_days))
    return 0

runtime_info = {"count": 0, "date": "", "last_retry_ts": 0.0}
