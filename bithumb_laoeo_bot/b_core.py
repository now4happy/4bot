import os, time, json, uuid, hashlib, jwt, requests, threading
import replay_log as RL   # v4.0.4: 재생 로그 (start.md 규칙) — 매매 동작은 바꾸지 않음
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta

BOT_VERSION = "v4.0.4"
# v4.0.4 (2026-10-28): 재생 로그 추가 — 버튼·명령 / 매매 판단 / 빗썸 주문·조회 / 설정 변경 / 보낸 메시지를 logs/ 에 한 줄 JSON 으로.
#                     금액·코인·수량은 감사 로그(logs/audit-*, 권한 600)에만. 실패 시 이유 코드 필수.
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
