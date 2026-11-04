import os, sys, time, json, glob, inspect, asyncio, requests
import replay_log as RL   # v4.3.5: 재생 로그 (start.md 규칙) — 매매 동작은 바꾸지 않음
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from toss_api import TossApiClient
from dca_engine import DcaConfigManager, execute_stock_dca_step

BOT_VERSION = "v4.3.8"
# v4.3.8 (2026-11-05): 익절 단계 위로만(재도달 재매도 없음, 리셋=보유 0주·진행일수 0 입력) / 정지·결정 중 익절 구간 알림(자동 매도 없음)
#                     / 가격 0·조회 실패·거래정지면 그날 매수·익절 안 함 / N7 지수 200일선 매수 배수(기본 꺼짐)
# v4.3.5 (2026-10-28): 재생 로그 추가 — 버튼·명령(user_event) / 매매 판단(decision) / 주문·외부 호출(external_call)
#                     / 설정 변경(state_change) / 보낸 메시지(user_visible) 를 logs/ 에 한 줄 JSON 으로. 금액·종목은 감사 로그에만.
KST_TZ, EST_TZ = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNIPER_DIR = "/home/gieokkim/toss_sniper"
VER_HISTORY_FILE = os.path.join(BASE_DIR, "update_history.json")

load_dotenv(os.path.join(BASE_DIR, ".env"))
RL.setup("toss_dca", BOT_VERSION, BASE_DIR)
TOSS_ID, TOSS_SECRET = os.getenv("TOSS_CLIENT_ID", "").strip(), os.getenv("TOSS_CLIENT_SECRET", "").strip()
TG_TOKEN, CHAT_ID = os.getenv("TELEGRAM_BOT_TOKEN", "").strip(), os.getenv("TELEGRAM_CHAT_ID", "").strip()
fail_reasons = {}

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
    changed, added = False, []
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
                            changed = True; added.append(sym)
            except Exception as e: RL.err("holdings_sync", e)
            break
    if changed:
        aref = RL.audit("holdings_new_stocks", symbols=added)   # 토스 앱 보유종목이 '중지' 상태로 새로 등록됨
        RL.ev("state_change", "stock_auto_added", count=len(added), sym_refs=[RL.ref(x) for x in added][:10], enabled=False, audit_ref=aref)
        await DcaConfigManager.save(cfg)
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

# ---------------------------------------------------------------- v4.3.8 익절 단계 (위로만)
def tp_stage_reached(prof_pct: float, tp1: float) -> int:
    """수익률이 속한 구간: 0=1차 미만, 1=1차, 2=2차, 3=3차 이상(매도 없음 구간)"""
    if tp1 <= 0 or prof_pct < tp1: return 0
    if prof_pct < tp1 * 2: return 1
    if prof_pct < tp1 * 3: return 2
    return 3

def tp_sell_stage(prof_pct: float, tp1: float, sold_stage: int) -> int:
    """이번에 팔 단계(0=안 팖). 이미 판 단계 이하는 다시 팔지 않고, 여러 단계를 넘어도 가장 높은 새 단계 1회만. 3차 이상은 매도 없음."""
    r = tp_stage_reached(prof_pct, tp1)
    return r if r in (1, 2) and r > int(sold_stage or 0) else 0

def calc_buy_amount(base_amt: float, index_mult: float, half: bool) -> float:
    """최종 1회 매수금 = 기준금액 × 지수 배수 × (평단 대비 +1% 이상이면 ½). 달러 부족 검사와 실제 주문이 같은 값을 쓰도록 한 곳에서만 계산."""
    return float(base_amt) * float(index_mult or 1.0) * (0.5 if half else 1.0)

def stock_looks_halted(info) -> bool:
    """get_stock_info() 의 status 로 거래정지·상장폐지만 판단. 모르는 값은 정지로 보지 않음 (status 실제 값은 미확인)."""
    st = str((info or {}).get("status") or "").upper() if isinstance(info, dict) else ""
    return any(k in st for k in ("SUSPEND", "HALT", "DELIST"))

# ---------------------------------------------------------------- v4.3.8 N7 지수 200일선 매수 배수 (기본 꺼짐)
N7_INDEX = {   # 기준 지수 키: (대용 ETF, 시장, 화면 이름)
    "KOSPI200": ("069500", "KR", "코스피200"),
    "KOSDAQ150": ("229200", "KR", "코스닥150"),
    "SP500": ("SPY", "US", "S&P500"),
    "NDX100": ("QQQ", "US", "나스닥100"),
}
N7_CHOICES = {"KR": ("KOSPI200", "KOSDAQ150"), "US": ("SP500", "NDX100")}
N7_SMA_DAYS, N7_CONFIRM_DAYS, N7_FORECAST_DAYS = 200, 3, 20
_N7_TODAY = {}   # 기준 지수별 {"day": 시장 현지 날짜, "eff": 오늘 쓸 배수} — 하루 첫 실행 때 1회만 계산 (메모리)

def n7_index_of(s: dict) -> str:
    """종목의 기준 지수 키. 설정 키 index_ref 가 없거나 시장과 안 맞으면 시장 기본값(한국=코스피200, 미국=S&P500)."""
    mk = "KR" if s.get("currency") == "KRW" else "US"
    v = s.get("index_ref")
    return v if v in N7_CHOICES[mk] else N7_CHOICES[mk][0]

def n7_base_mult(d) -> float:
    """완충 없이 거리 d 만으로 정한 배수: d≥-3% → 1.0, -10%≤d<-3% → 1.5, d<-10% → 2.0(최대). d 없음 → 1.0"""
    if d is None: return 1.0
    if d >= -0.03: return 1.0
    if d >= -0.10: return 1.5
    return 2.0

def n7_target_mult(d: float, cur: float) -> float:
    """완충(±1%p) 적용 목표 배수. 1.5→1.0 복귀는 d≥-2%, 2.0→1.5 복귀는 d≥-9% 일 때만."""
    cur = float(cur or 1.0)
    if cur >= 2.0:
        return 1.0 if d >= -0.02 else (1.5 if d >= -0.09 else 2.0)
    if cur >= 1.5:
        return 1.0 if d >= -0.02 else (2.0 if d < -0.10 else 1.5)
    return n7_base_mult(d)

def n7_step(state: dict, d: float, candle_date: str):
    """새 완성 일봉 하루마다 1번 진행. 목표 배수가 연속 3거래일 같아야 배수를 바꿈. 반환 (새 상태, 바뀌었는지, 이전 배수)."""
    st = dict(state or {}); cur = float(st.get("mult", 1.0))
    if candle_date and st.get("last_candle") == candle_date:
        return st, False, cur   # 새 거래일이 아님 (같은 전일 종가) → 3일 셈을 올리지 않음
    st["last_candle"], st["d"] = candle_date, round(float(d), 6)
    tgt = n7_target_mult(d, cur)
    if tgt == cur:
        st["cand"], st["cand_days"], st["mult"] = None, 0, cur
        return st, False, cur
    st["cand_days"] = int(st.get("cand_days", 0)) + 1 if st.get("cand") == tgt else 1
    st["cand"] = tgt
    if st["cand_days"] >= N7_CONFIRM_DAYS:
        st["mult"], st["cand"], st["cand_days"] = tgt, None, 0
        return st, True, cur
    st["mult"] = cur
    return st, False, cur

def _n7_candle_date(c: dict, tz):
    """봉 시각 → 시장 현지 날짜(YYYY-MM-DD). 못 읽으면 None."""
    v = None
    for k in ("timestamp", "dt", "dateTime", "time", "date"):
        if c.get(k) not in (None, ""): v = c.get(k); break
    if v is None: return None
    try:
        if isinstance(v, (int, float)) or str(v).strip().isdigit() and len(str(v).strip()) > 8:
            x = float(v); x = x / 1000.0 if x > 1e12 else x
            return datetime.fromtimestamp(x, tz).strftime("%Y-%m-%d")
        sv = str(v).strip()
        if len(sv) == 8 and sv.isdigit(): sv = f"{sv[:4]}-{sv[4:6]}-{sv[6:]}"
        dt = datetime.fromisoformat(sv.replace("Z", "+00:00"))
        return (dt.astimezone(tz) if dt.tzinfo else dt).strftime("%Y-%m-%d")
    except Exception:
        return None

def n7_closes_from_candles(candles: list, today: str, tz) -> list:
    """완성된 일봉 종가만 [(날짜, 종가)] 오름차순. 오늘(미완성) 이후 봉 제외. 종가 필드는 첫 봉 dict 로 확정(closePrice → close),
    없거나 날짜를 못 읽는 봉이 있으면 [] (→ 배수 1.0)."""
    if not candles or not isinstance(candles[0], dict): return []
    first = candles[0]
    field = "closePrice" if "closePrice" in first else ("close" if "close" in first else None)
    if not field: return []
    by_day = {}
    for c in candles:
        if not isinstance(c, dict): continue
        day = _n7_candle_date(c, tz)
        if not day: return []
        if day >= today: continue
        try: px = float(c.get(field))
        except Exception: return []
        if px <= 0: return []
        by_day[day] = px
    return sorted(by_day.items())

def n7_distance(closes: list):
    """d = (전일 종가 ÷ 완성 200거래일 단순이동평균) − 1. 200개 미만이면 (None, None) — 부족한 데이터로 평균 내지 않음."""
    if len(closes) < N7_SMA_DAYS: return None, None
    last = closes[-N7_SMA_DAYS:]
    sma = sum(px for _, px in last) / N7_SMA_DAYS
    if sma <= 0: return None, None
    return last[-1][1] / sma - 1.0, last[-1][0]

async def n7_fetch_closes(client, etf: str, tz, today: str) -> list:
    """일봉을 nextBefore 로 최대 3페이지 받아 완성 종가 목록으로. 함수가 없으면 []."""
    fn = getattr(client, "get_candles_1d", None)
    if not fn: return []
    raw, before = [], None
    for _ in range(3):
        batch, nb = await fn(etf, 200, before)
        if not batch: break
        raw.extend(batch)
        closes = n7_closes_from_candles(raw, today, tz)
        if len(closes) >= N7_SMA_DAYS or not nb or nb == before: break
        before = nb
    return n7_closes_from_candles(raw, today, tz)

async def n7_save_state(states: dict):
    """N7 상태만 최신 설정 파일에 덮어씀 (종목·금액·enabled 는 건드리지 않음)."""
    fresh = await DcaConfigManager.load(); fresh["n7_state"] = states
    await DcaConfigManager.save(fresh)

def n7_forecast_text(cfg: dict, idx: str, mult: float) -> str:
    """배수>1.0 일 때 이 지수를 쓰는 매수 중 종목의 다음 20거래일 필요 금액(½ 규칙 미반영 최대치)."""
    mk = N7_INDEX[idx][1]; total = 0.0; n = 0
    for s in cfg.get("stocks", {}).values():
        if ("KR" if s.get("currency") == "KRW" else "US") != mk or not s.get("enabled", True): continue
        if s.get("s_mode") not in ("buy_1", "buy_2") or n7_index_of(s) != idx: continue
        days = max(0, min(N7_FORECAST_DAYS, int(s.get("s_target_days", 100)) - int(s.get("s_day", 0))))
        total += float(s.get("base_amount", 100000.0 if mk == "KR" else 40.0)) * mult * days; n += 1
    amt = f"{total:,.0f}원" if mk == "KR" else f"${total:,.2f}"
    return f"• 다음 {N7_FORECAST_DAYS}거래일 필요 {'원화' if mk == 'KR' else '달러'}: 약 {amt} ({n}종목, ½ 규칙 미반영 최대치)"

async def n7_market_multipliers(client, cfg: dict, is_kr_market: bool) -> dict:
    """시장별 그날 첫 실행 때 기준 지수마다 1번 계산 → {기준 지수 키: 오늘 배수}. 꺼짐이면 {} (= 모두 1.0, 기존 금액 그대로).
    데이터 실패·200일 부족·종가 필드 없음 → 그날 배수 1.0 + 재생 로그 하루 1번. 어떤 예외도 매매를 막지 않음."""
    if not cfg.get("n7_enabled", False): return {}
    out = {}
    try:
        mk = "KR" if is_kr_market else "US"; tz = KST_TZ if is_kr_market else EST_TZ
        today = datetime.now(tz).strftime("%Y-%m-%d")
        used = {n7_index_of(s) for s in cfg.get("stocks", {}).values()
                if ("KR" if s.get("currency") == "KRW" else "US") == mk and s.get("enabled", True)}
        states = dict(cfg.get("n7_state") or {}); dirty = False
        for idx in sorted(used):
            mem = _N7_TODAY.get(idx)
            if mem and mem["day"] == today: out[idx] = mem["eff"]; continue
            etf, _, name = N7_INDEX[idx]; d, cdate, why = None, None, None
            try:
                closes = await n7_fetch_closes(client, etf, tz, today)
                d, cdate = n7_distance(closes)
                if d is None: why = "candles_short_or_no_close_field"
            except Exception as e:
                why = "candle_fetch_error"; RL.err("n7_candles", e, event_type="external_call", index=idx)
            if d is None:
                _N7_TODAY[idx] = {"day": today, "eff": 1.0}; out[idx] = 1.0
                if RL.once(f"n7|{idx}|{why}"):
                    RL.ev("decision", "n7_multiplier", "skipped", why, actor="scheduler", index=idx, mult=1.0)
                continue
            st, changed, before = n7_step(states.get(idx, {}), d, cdate)
            states[idx] = st; dirty = True
            eff = float(st.get("mult", 1.0)); _N7_TODAY[idx] = {"day": today, "eff": eff}; out[idx] = eff
            RL.ev("decision", "n7_multiplier", "ok", None, actor="scheduler", index=idx, d=round(d, 4), mult=eff,
                  cand=st.get("cand"), cand_days=st.get("cand_days"), changed=changed)
            if changed:
                msg = (f"📐 [지수 연동 배수 변경 · {name} ({etf})]\n• 200일선 대비 {d*100:+.1f}% (전일 {cdate} 종가 기준)\n"
                       f"• 매수 배수: {before:.1f}배 → {eff:.1f}배 (연속 {N7_CONFIRM_DAYS}거래일 확인)")
                if eff > 1.0: msg += "\n" + n7_forecast_text(cfg, idx, eff)
                send_panel(msg, [[{"text": "🎛 관제탑", "callback_data": "panel"}]])
        if dirty:
            cfg["n7_state"] = states; await n7_save_state(states)
    except Exception as e:
        RL.err("n7_market", e, event_type="decision")
        return {k: 1.0 for k in out} if out else {}
    return out

def n7_status_lines(cfg: dict) -> list:
    """관제탑 표시용: 켜짐/꺼짐 + 기준 지수별 현재 배수·거리·후보 일수."""
    if not cfg.get("n7_enabled", False):
        return [" • 지수 연동 배수(N7): ⚪ 꺼짐 — 기존 금액 그대로"]
    lines = [" • 지수 연동 배수(N7): 🟢 켜짐 (200일선 기준, 최대 2.0배)"]
    states = cfg.get("n7_state") or {}
    for idx, (etf, _, name) in N7_INDEX.items():
        st = states.get(idx)
        if not st: continue
        cand = f", 후보 {st.get('cand'):.1f}배 {st.get('cand_days')}/{N7_CONFIRM_DAYS}일" if st.get("cand") else ""
        lines.append(f"   - {name}({etf}): {float(st.get('mult', 1.0)):.1f}배 (200일선 {float(st.get('d', 0))*100:+.1f}%, {st.get('last_candle')}{cand})")
    return lines
