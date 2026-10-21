import os, time, json, uuid, hashlib, jwt, requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta

BOT_VERSION = "v4.0"
KST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE, STATE_FILE = os.path.join(BASE_DIR, "bot_config.json"), os.path.join(BASE_DIR, "bot_state.json")
HISTORY_FILE, VER_HISTORY_FILE = os.path.join(BASE_DIR, "trade_history.json"), os.path.join(BASE_DIR, "update_history.json")

ACCESS_KEY = os.environ.get("BITHUMB_ACCESS_KEY", "").strip()
SECRET_KEY = os.environ.get("BITHUMB_SECRET_KEY", "").strip()
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6979340028").strip()

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: pass
    return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

config = load_json(CONFIG_FILE, {"power": True, "coins": {"BTC": 10000, "ETH": 10000}, "target_profit_pct": 10.0, "sell_ratio_pct": 20.0, "buy_hour": 19})
state = load_json(STATE_FILE, {"last_action_date": {}, "last_action_type": {}, "last_low_bal_ts": 0, "sold_stage": {}})
for k in ["last_action_date", "last_action_type", "sold_stage", "buy_days"]:
    if k not in state or not isinstance(state[k], dict): state[k] = {}
history = load_json(HISTORY_FILE, [])
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

def bithumb_headers(query_params=None):
    payload = {"access_key": ACCESS_KEY, "nonce": str(uuid.uuid4()), "timestamp": round(time.time() * 1000)}
    if query_params:
        m = hashlib.sha512(); m.update(urlencode(query_params).encode())
        payload["query_hash"], payload["query_hash_alg"] = m.hexdigest(), "SHA512"
    return {"Authorization": f"Bearer {jwt.encode(payload, SECRET_KEY, algorithm='HS256')}", "Content-Type": "application/json"}

def get_accounts():
    try:
        r = requests.get("https://api.bithumb.com/v1/accounts", headers=bithumb_headers(), timeout=10)
        if r.status_code == 200: return r.json()
    except: pass
    return []

def get_ticker(coin):
    try:
        r = requests.get(f"https://api.bithumb.com/v1/ticker?markets=KRW-{coin}", timeout=10)
        if r.status_code == 200 and len(r.json()) > 0: return r.json()[0]
    except: pass
    return None

def place_order(coin, side, price_or_vol, ord_type):
    try:
        body = {"market": f"KRW-{coin}", "side": side, "ord_type": ord_type}
        body["price" if ord_type == "price" else "volume"] = str(int(price_or_vol) if ord_type == "price" else price_or_vol)
        r = requests.post("https://api.bithumb.com/v1/orders", headers=bithumb_headers(body), data=json.dumps(body), timeout=10)
        return r.status_code in [200, 201], r.json()
    except Exception as e: return False, str(e)

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
