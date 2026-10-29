import os, time, json, uuid, hashlib, jwt, requests, threading
import replay_log as RL   # v4.0.4: 재생 로그 (start.md 규칙) — 매매 동작은 바꾸지 않음
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from math import isfinite

BOT_VERSION = "v4.3.0"
# v4.2.0 (draft rework): unified SMA법; separate per-coin buy amount and explicit approval.
# v4.0.4 (2026-10-28): 재생 로그 추가 — 버튼·명령 / 매매 판단 / 빗썸 주문·조회 / 설정 변경 / 보낸 메시지를 logs/ 에 한 줄 JSON 으로.
#                     금액·코인·수량은 감사 로그(logs/audit-*, 권한 600)에만. 실패 시 이유 코드 필수.
# v4.1.0 (2026-10-29): 관찰 전용 BTC·ETH 추세 신호 추가 — 매수·매도 동작 변경 없음.
#                     일봉 종가 기준 BTC SMA100, ETH SMA200, 완성된 봉만 사용, 하루 1회 갱신, 상황판 표시만.
KST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE, STATE_FILE = os.path.join(BASE_DIR, "bot_config.json"), os.path.join(BASE_DIR, "bot_state.json")
HISTORY_FILE, VER_HISTORY_FILE = os.path.join(BASE_DIR, "trade_history.json"), os.path.join(BASE_DIR, "update_history.json")

ACCESS_KEY = os.environ.get("BITHUMB_ACCESS_KEY", "").strip()
SECRET_KEY = os.environ.get("BITHUMB_SECRET_KEY", "").strip()
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6979340028").strip()
RL.setup("bithumb_dca", BOT_VERSION, BASE_DIR)

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: pass
    return default

_SAVE_LOCK = threading.Lock()

def save_json(path, data):
    # 임시 파일에 다 쓴 뒤 한 번에 교체 → 저장 중 재시작·두 스레드 동시 저장으로 파일이 깨져 오늘 매수 기록이 사라지는 문제 방지
    tmp = path + ".tmp"
    with _SAVE_LOCK:
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2); f.flush(); os.fsync(f.fileno())
            os.replace(tmp, path)
        except:
            try: os.remove(tmp)
            except: pass

config = load_json(CONFIG_FILE, {"power": True, "coins": {"BTC": 10000, "ETH": 10000}, "target_profit_pct": 10.0, "sell_ratio_pct": 20.0, "buy_hour": 19})
state = load_json(STATE_FILE, {"last_action_date": {}, "last_action_type": {}, "last_low_bal_ts": 0, "sold_stage": {}})
for k in ["last_action_date", "last_action_type", "sold_stage", "buy_days"]:
    if k not in state or not isinstance(state[k], dict): state[k] = {}
# Method 2 is opt-in per coin; live execution remains LOCKED until all
# financial assumptions have been explicitly approved outside this draft.
# No existing config keys or trade settings are migrated or overwritten.

def coin_method(coin):
    value = config.get("coin_methods", {}).get(coin, 1)
    return 2 if value == 2 else 1

def method2_ratio(coin):
    try:
        value = float(config.get("method2_sell_ratios", {}).get(coin))
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) and 0 < value <= 100 else None

def sma_buy_amount(coin):
    """Only an explicitly saved SMA법 KRW amount; never derive from method-1 seed."""
    try:
        value = float(config.get("sma_buy_amounts", {}).get(coin))
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) and value >= 5000 else None

def method2_ready(coin):
    # Selecting SMA is approval; valid per-coin financial inputs are mandatory.
    return (coin_method(coin) == 2
            and coin in config.get("method2_sell_ratios", {})
            and method2_ratio(coin) is not None
            and coin in config.get("sma_buy_amounts", {})
            and sma_buy_amount(coin) is not None)

def daily_crossover(closes, period):
    """Completed daily close crossing its *own* SMA vs prior completed day.
    Never uses intraday ticker. Returns up/down/none/unknown.
    """
    if len(closes) < period + 1:
        return "unknown"
    prev_sma = compute_sma(closes[:-1], period)
    curr_sma = compute_sma(closes, period)
    if prev_sma is None or curr_sma is None:
        return "unknown"
    prev_side = 1 if closes[-2] > prev_sma else (-1 if closes[-2] < prev_sma else 0)
    curr_side = 1 if closes[-1] > curr_sma else (-1 if closes[-1] < curr_sma else 0)
    if not prev_side or not curr_side:
        return "none"  # equality is not a crossover
    if prev_side < 0 and curr_side > 0:
        return "up"
    if prev_side > 0 and curr_side < 0:
        return "down"
    return "none"

history = load_json(HISTORY_FILE, [])
def tg_api(method, payload=None):
    if not TG_TOKEN: return None
    t0 = time.time()
    try: res = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/{method}", json=payload, timeout=10).json()
    except Exception as e:
        RL.err("tg_" + method, e, reason="tg_no_response", event_type="user_visible"); res = None
    RL.tg_result(method, payload, res, int((time.time() - t0) * 1000))
    return res

def send_panel(text, inline_kb, msg_id=None):
    payload = {"chat_id": CHAT_ID, "text": text, "reply_markup": {"inline_keyboard": inline_kb}}
    if "<pre>" in text and "</pre>" in text:
        payload["parse_mode"] = "HTML"
    if msg_id:
        payload["message_id"] = msg_id
        res = tg_api("editMessageText", payload)
        if res and (res.get("ok") or "not modified" in str(res.get("description", ""))): return
    tg_api("sendMessage", payload)

def bithumb_headers(query_params=None):
    payload = {"access_key": ACCESS_KEY, "nonce": str(uuid.uuid4()), "timestamp": round(time.time() * 1000)}
    if query_params:
        m = hashlib.sha512(); m.update(urlencode(query_params).encode())
        payload["query_hash"], payload["query_hash_alg"] = m.hexdigest(), "SHA512"
    return {"Authorization": f"Bearer {jwt.encode(payload, SECRET_KEY, algorithm='HS256')}", "Content-Type": "application/json"}

def get_accounts():
    try:
        r = requests.get("https://api.bithumb.com/v1/accounts", headers=bithumb_headers(), timeout=10)
        if r.status_code == 200: RL.count("bithumb_accounts_ok"); return r.json()
        RL.err("bithumb_accounts", RuntimeError(f"HTTP {r.status_code}"), reason=f"bithumb_http_{r.status_code}")
    except Exception as e: RL.err("bithumb_accounts", e)
    return []

def get_ticker(coin):
    try:
        r = requests.get(f"https://api.bithumb.com/v1/ticker?markets=KRW-{coin}", timeout=10)
        if r.status_code == 200 and len(r.json()) > 0: RL.count("bithumb_ticker_ok"); return r.json()[0]
        RL.err("bithumb_ticker", RuntimeError(f"HTTP {r.status_code}"), reason=f"bithumb_http_{r.status_code}", coin_ref=RL.ref(coin))
    except Exception as e: RL.err("bithumb_ticker", e, coin_ref=RL.ref(coin))
    return None

# --- v4.1.0 관찰 전용 추세 신호 (매수·매도를 바꾸지 않음) ---
TREND_PERIOD = {"BTC": 100, "ETH": 200}
trend_signals = {}  # coin -> {signal: up|down|unknown, sma, close, date, reason}

def compute_sma(closes, period):
    """완성된 종가 배열(오래된 순)에서 SMA를 구한다. 봉이 부족하면 None."""
    if not isinstance(closes, (list, tuple)) or period <= 0 or len(closes) < period:
        return None
    return sum(float(x) for x in closes[-period:]) / period

def get_daily_closes(coin, period):
    """완성된 일봉 종가(오래된 순)를 period개 모은다. 실패·부족 시 빈 리스트.
    빗썸 일봉 API는 최신 봉부터 반환한다(공식 문서).
    09:00 KST에 끝나는 봉만 사용하고, `to`는 가장 오래된 봉의 KST 시각이다."""
    closes_newest = []
    seen_dates = set()
    to_param = None
    # Bithumb daily candles start at 09:00 KST; a candle is complete only
    # when its next 09:00 KST boundary has passed. `to` is KST, not UTC.
    now_kst = datetime.now(KST)
    for _ in range(3):
        url = "https://api.bithumb.com/v1/candles/days"
        params = {"market": f"KRW-{coin}", "count": 200}
        if to_param:
            params["to"] = to_param
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200:
                RL.err("bithumb_candles", RuntimeError(f"HTTP {r.status_code}"), reason=f"bithumb_http_{r.status_code}", coin_ref=RL.ref(coin))
                return []
            data = r.json()
        except Exception as e:
            RL.err("bithumb_candles", e, coin_ref=RL.ref(coin))
            return []
        if not isinstance(data, list) or not data:
            break
        for c in data:
            if not isinstance(c, dict):
                return []
            try:
                start = datetime.fromisoformat(c["candle_date_time_kst"]).replace(tzinfo=KST)
                # Fail closed if the API returns an unexpected candle boundary.
                if (start.hour, start.minute, start.second) != (9, 0, 0):
                    return []
                kst_date = start.date().isoformat()
                if start + timedelta(days=1) > now_kst or kst_date in seen_dates:
                    continue
                close = float(c["trade_price"])
                if not isfinite(close) or close <= 0:
                    return []
            except (KeyError, TypeError, ValueError, OverflowError):
                return []
            seen_dates.add(kst_date)
            closes_newest.append(close)
            if len(closes_newest) >= period:
                break
        if len(closes_newest) >= period:
            break
        oldest_kst = data[-1].get("candle_date_time_kst") if isinstance(data[-1], dict) else None
        if not oldest_kst or oldest_kst == to_param:
            break
        to_param = oldest_kst
    return list(reversed(closes_newest))

def update_trend_signal(coin):
    """하루 1회 호출용. 신호를 trend_signals에 저장하고, SMA·종가는 감사 로그에만 남긴다.
    조회 실패·봉 부족이면 신호를 unknown으로 남기고, 매수·매도 쪽에는 아무 영향도 주지 않는다."""
    period = TREND_PERIOD.get(coin)
    today = datetime.now(KST).strftime("%Y-%m-%d")
    if not period:
        return None
    closes = get_daily_closes(coin, period)
    if len(closes) < period:
        trend_signals[coin] = {"signal": "unknown", "sma": None, "close": None, "date": today, "reason": "insufficient_candles"}
        RL.ev("decision", "trend_signal", "skipped", "insufficient_candles", actor="scheduler", coin_ref=RL.ref(coin))
        return trend_signals[coin]
    sma = compute_sma(closes, period)
    close = closes[-1]
    prev = trend_signals.get(coin, {}).get("signal")
    if close > sma:
        signal = "up"
    elif close < sma:
        signal = "down"
    else:
        signal = prev if prev in ("up", "down") else "unknown"
    trend_signals[coin] = {"signal": signal, "sma": sma, "close": close, "date": today, "reason": None}
    RL.ev("decision", "trend_signal", "ok", None, actor="scheduler", coin_ref=RL.ref(coin),
          audit_ref=RL.audit("trend_signal", coin=coin, signal=signal, sma=sma, close=close, period=period, date=today))
    return trend_signals[coin]

def trend_line():
    """상황판 표시용 한 줄. 가격·SMA 수치는 표시하지 않고 신호 단어만 쓴다."""
    parts = []
    for coin in ("BTC", "ETH"):
        sig = trend_signals.get(coin, {}).get("signal")
        period = TREND_PERIOD.get(coin)
        if sig == "up":
            parts.append(f"{coin} 상승(SMA{period} 위)")
        elif sig == "down":
            parts.append(f"{coin} 하락(SMA{period} 아래)")
        else:
            parts.append(f"{coin} 확인불가")
    return " · ".join(parts)

def place_order(coin, side, price_or_vol, ord_type):
    t0 = time.time(); chain = "ord-" + (RL.ref(f"{coin}|{side}|{t0}") or "x")
    try:
        body = {"market": f"KRW-{coin}", "side": side, "ord_type": ord_type}
        body["price" if ord_type == "price" else "volume"] = str(int(price_or_vol) if ord_type == "price" else price_or_vol)
        r = requests.post("https://api.bithumb.com/v1/orders", headers=bithumb_headers(body), data=json.dumps(body), timeout=10)
        out = (r.status_code in [200, 201], r.json())
        _order_log(chain, coin, side, ord_type, price_or_vol, out[0], r.status_code, out[1], t0)
        return out
    except Exception as e:
        _order_log(chain, coin, side, ord_type, price_or_vol, False, None, str(e), t0)
        return False, str(e)

def _order_log(chain, coin, side, ord_type, size, ok, status, res, t0):
    """주문 1건 기록: 일반 로그엔 결과·이유·참조값만, 금액·코인·응답은 감사 로그에"""
    bid = res.get("uuid") if isinstance(res, dict) else None
    aref = RL.audit("order_submit", chain=chain, coin=coin, side=side, ord_type=ord_type, size=size, http=status, broker_order_id=bid,
                    response=res if isinstance(res, dict) else str(res)[:300])
    reason = None if ok else ("no_response_maybe_filled" if status is None else f"bithumb_http_{status}")
    RL.ev("external_call", "order_submit", "ok" if ok else "failed", reason, actor="scheduler", level="INFO" if ok else "ERROR",
          chain=chain, side=side, coin_ref=RL.ref(coin), broker_ref=RL.ref(bid), broker_id_found=bool(bid), fill_check="not_available",
          ms=int((time.time() - t0) * 1000), audit_ref=aref)

def add_history(coin, action, detail):
    history.append(f"[{datetime.now(KST).strftime('%m-%d %H:%M')}] {coin} {action}: {detail}")
    if len(history) > 100: history.pop(0)
    save_json(HISTORY_FILE, history)

def get_coin_cycle_day(coin: str, avg_p: float, bal: float, base_amt: int) -> int:
    s_days = state.get("cycle_days", {})
    if not isinstance(s_days, dict): s_days = {}
    d = s_days.get(coin, 0)
    if d == 0 and bal > 0 and avg_p > 0 and base_amt > 0:
        invested = bal * avg_p
        est = int(round(invested / base_amt))
        d = max(1, min(100, est))
        s_days[coin] = d; state["cycle_days"] = s_days; save_json(STATE_FILE, state)
    return d

runtime_info = {"count": 0, "date": ""}
