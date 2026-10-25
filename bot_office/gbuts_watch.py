import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta
import fcntl

STATE_DIR = "/var/lib/bot-office/gbuts-watch"
STATE_FILE = os.path.join(STATE_DIR, "state.json")
API_URL = "https://api.gbuts.com/api/common/post/pick?category=488&subcategory=519"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

KST = timezone(timedelta(hours=9))

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"seen_items": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            if "seen_seqs" in state:
                return {"seen_items": {}}
            return state
    except Exception:
        return {"seen_items": {}}

def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)

def send_telegram(msg):
    try:
        with open("/etc/bot-office/telegram.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        token = cfg.get("token") or cfg.get("U_TG_TOKEN") or cfg.get("TG_TOKEN")
        chat_id = cfg.get("chat_id") or cfg.get("U_TG_CHAT_ID") or cfg.get("CHAT_ID")
        if not token or not chat_id:
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def fetch_items():
    try:
        req = urllib.request.Request(API_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("success") and "response" in data:
                res = data["response"]
                # API가 리스트로 줄 때와 딕셔너리로 줄 때 모두 대응하도록 수정
                if isinstance(res, list):
                    return res
                elif isinstance(res, dict):
                    return res.get("items", [])
    except Exception as e:
        print(f"[gbuts] Fetch error: {e}")
    return []

def is_target_item(item):
    if not isinstance(item, dict): return False
    title = item.get("title", {}).get("ko", "").lower()
    keywords = ["claude", "클로드", "supergrok", "슈퍼그록", "슈퍼 그록", "grok", "그록"]
    if not any(k in title for k in keywords):
        return False
    
    if item.get("status") != "ON_SALE":
        return False
    member_count = item.get("memberCount", 0)
    member_limit = item.get("memberLimit", 0)
    if member_limit > 0 and member_count >= member_limit:
        return False

    end_str = item.get("subscriptionEndsAt")
    if not end_str:
        return False
    try:
        end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
        now = datetime.now(KST)
        remain_days = (end_dt - now).days
        if remain_days < 0 or remain_days > 31:
            return False
    except Exception:
        return False

    return True

def run_check():
    state = load_state()
    seen_items = state.get("seen_items", {})
    items = fetch_items()
    alerts = []

    for item in items:
        if not is_target_item(item):
            continue

        seq = str(item.get("seq"))
        price = item.get("price", 0)
        end_str = item.get("subscriptionEndsAt", "")
        member_count = item.get("memberCount", 0)
        
        current_info = {
            "price": price,
            "end_date": end_str,
            "member_count": member_count
        }

        if seq not in seen_items:
            alerts.append(f"🆕 <b>[신규]</b> {item['title']['ko']}\n  가격: {price:,.0f}원 (~{end_str[:10]})")
            seen_items[seq] = current_info
        else:
            old_info = seen_items[seq]
            changes = []
            if old_info.get("price") != price:
                changes.append(f"가격: {old_info.get('price', 0):,.0f}원 → {price:,.0f}원")
            if old_info.get("end_date") != end_str:
                changes.append(f"기간 변경: ~{end_str[:10]}")
            if old_info.get("member_count") != member_count:
                changes.append(f"인원: {old_info.get('member_count')}명 → {member_count}명")
            
            if changes:
                alerts.append(f"🔄 <b>[정보 변동]</b> {item['title']['ko']}\n  " + "\n  ".join(changes))
                seen_items[seq] = current_info

    state["seen_items"] = seen_items
    save_state(state)

    if alerts:
        msg = "🚨 <b>[Gbuts] 조건 충족 상품 알림</b>\n\n" + "\n\n".join(alerts)
        send_telegram(msg)
        print(f"[gbuts] 알림 전송 완료: {len(alerts)}건")
    else:
        print("[gbuts] 변동 사항 없음 (조용히 넘어감)")

if __name__ == "__main__":
    os.makedirs(STATE_DIR, exist_ok=True)
    lock_file = os.path.join(STATE_DIR, "lock")
    with open(lock_file, "w") as lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run_check()
        except BlockingIOError:
            print("[gbuts] 이미 실행 중입니다.")
