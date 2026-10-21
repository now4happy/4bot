# ==========================================
# Toss Smart 100-Day Cycle Bot - Version: v3.2
# ==========================================
import os, sys, time, json, glob, inspect, asyncio, requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from toss_api import TossApiClient
from dca_engine import DcaConfigManager, execute_stock_dca_step

BOT_VERSION = "v3.2"
KST_TZ = ZoneInfo("Asia/Seoul")
EST_TZ = ZoneInfo("America/New_York")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNIPER_DIR = "/home/gieokkim/toss_sniper"
VER_HISTORY_FILE = os.path.join(BASE_DIR, "update_history.json")

DEFAULT_VER_HISTORY = [
    {"ver": "v1.0", "date": "2026-10-16", "desc": "토스 스마트 적립 및 분할익절 봇 최초 구축"},
    {"ver": "v2.1", "date": "2026-10-18", "desc": "보유수량/수익률 계산 패치 및 당일 필요환전 달러 브리핑 추가"},
    {"ver": "v2.2", "date": "2026-10-18", "desc": "수익률 +1.0% 이상 시 1/2배(절반) 매수, 그 외 1배 매수 규칙 통일"},
    {"ver": "v2.3", "date": "2026-10-19", "desc": "한국시간 평일 정상 개장 판별 수정 및 10%·20%·30% 구간별 매도 계획 표시"},
    {"ver": "v3.0", "date": "2026-10-19", "desc": "관제탑 종목수 요약 경량화, 개장 2시간 뒤 매매, 100일 분할매수/매도 사이클 도입"},
    {"ver": "v3.1", "date": "2026-10-19", "desc": "텔레그램 코드업데이트 버튼 제거 및 다중종목(30~50개) 순차 매수 처리"},
    {"ver": "v3.2", "date": "2026-10-20", "desc": "미국주식 매수 호출 버그 수정, 1회 즉시매수 버튼 제거, 매매 미진행/실패 감시 알람 및 History 메뉴 추가"}
]

def load_ver_history():
    try:
        with open(VER_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_VER_HISTORY, f, ensure_ascii=False, indent=2)
    except: pass
    return DEFAULT_VER_HISTORY

load_dotenv(os.path.join(BASE_DIR, ".env"))
TOSS_ID = os.getenv("TOSS_CLIENT_ID", "").strip()
TOSS_SECRET = os.getenv("TOSS_CLIENT_SECRET", "").strip()
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
wait_state = {"mode": None}
fail_reasons = {}

def tg_api(method, payload=None):
    if not TG_TOKEN: return None
    try:
        return requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/{method}", json=payload, timeout=10).json()
    except: return None

def send_panel(text, inline_kb, msg_id=None):
    payload = {"chat_id": CHAT_ID, "text": text, "reply_markup": {"inline_keyboard": inline_kb}}
    if msg_id:
        payload["message_id"] = msg_id
        res = tg_api("editMessageText", payload)
        if res and res.get("ok"): return
    tg_api("sendMessage", payload)

def check_holiday():
    if datetime.now(KST_TZ).weekday() >= 5:
        return True, "주말 휴장 (Weekend)"
    return False, "정상 개장일 (시스템 대기 중)"

def get_sniper_seed() -> float:
    try:
        for pat in ["*.json", "data/*.json", "state/*.json"]:
            for p in glob.glob(os.path.join(SNIPER_DIR, pat)):
                try:
                    with open(p, "r", encoding="utf-8") as f: d = json.load(f)
                    if isinstance(d, dict):
                        for k, v in d.items():
                            if any(w in k.lower() for w in ["seed", "amount", "budget", "usd", "soxs"]):
                                if isinstance(v, (int, float)) and 10 <= v <= 50000: return float(v)
                except: pass
    except: pass
    return 105.00

async def ensure_cycle_fields():
    cfg = await DcaConfigManager.load()
    changed = False
    for k, v in [("kr_exec_time","11:00"), ("us_exec_time","11:30"), ("cycle_mode","buy_1"), ("cycle_day",0), ("max_days",100), ("tp1_pct",10.0), ("sr_pct",20.0), ("last_fail_alert_kr",""), ("last_fail_alert_us","")]:
        if k not in cfg: cfg[k] = v; changed = True
    if changed: await DcaConfigManager.save(cfg)
    return cfg

def build_ver_history_view():
    h_list = load_ver_history()
    lines = [f"📜 [토스 스마트 적립봇 업데이트 History ({BOT_VERSION})]", "─────────────────"]
    for item in h_list:
        lines.append(f"🔹 {item['ver']} ({item['date']})\n  └ {item['desc']}")
    lines.append("─────────────────")
    kb = [[{"text": "🔙 관제탑 메인으로 돌아가기", "callback_data": "panel"}]]
    return "\n".join(lines), kb

async def build_fx_view(client: TossApiClient):
    cfg = await ensure_cycle_fields()
    sniper_usd = get_sniper_seed()
    dca_usd_req, dca_krw_req, kr_cnt, us_cnt = 0.0, 0.0, 0, 0
    for sym, info in cfg.get("stocks", {}).items():
        if not info.get("enabled", True): continue
        amt = float(info.get("base_amount", 0))
        if info.get("currency") == "KRW":
            kr_cnt += 1
            if cfg["cycle_mode"] in ["buy_1", "buy_2"]: dca_krw_req += amt
        else:
            us_cnt += 1
            if cfg["cycle_mode"] in ["buy_1", "buy_2"]: dca_usd_req += amt

    cur_usd = 0.0
    try: cur_usd = float(await client.get_buying_power("USD") or 0.0)
    except: pass
    tot_req = sniper_usd + dca_usd_req
    final_need = max(0.0, tot_req - cur_usd)
    is_hol, hol_reason = check_holiday()
    now_str = datetime.now(KST_TZ).strftime("%m-%d %H:%M:%S KST")

    lines = [
        f"💱 [토스 당일 필요 달러 브리핑 ({BOT_VERSION})]",
        f"▫️ 시장 상태: {'🛑 ' if is_hol else '🟢 '}{hol_reason}",
        "─────────────────",
        f"🔫 [1] 토스 스나이퍼 시드: ${sniper_usd:,.2f}",
        f"📈 [2] 스마트 적립 ({us_cnt}개 미국종목): ${dca_usd_req:,.2f}",
    ]
    if kr_cnt > 0: lines.append(f"🇰🇷 [국내주식 {kr_cnt}개 종목]: {dca_krw_req:,.0f}원")
    lines.extend([
        "─────────────────",
        f"💵 현재 계좌 보유 달러: ${cur_usd:,.2f}",
        f"📊 당일 매매 총 소요액: ${tot_req:,.2f}",
        f"✅ 최종 추가 필요 달러: $0.00 (충분)" if final_need <= 0 else f"🚨 최종 추가 필요 달러: ${final_need:,.2f}",
        f"⏱ 갱신: {now_str}"
    ])
    kb = [[{"text": "🔄 새로고침", "callback_data": "fx"}], [{"text": "🔙 관제탑으로", "callback_data": "panel"}]]
    return "\n".join(lines), kb
