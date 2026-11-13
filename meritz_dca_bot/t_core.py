# =====================================================================
# FILE: meritz_dca_bot/t_core.py   (MERITZ_DCA v1.1.1)
# 메리츠 적립 봇 공통 부품. 3번 toss_dca_bot/t_core.py(v4.3.8)에서 옮김.
# v1.0.0 (2026-11-08): 첫 버전.
#   - 그대로 옮김(바이트 동일): runtime_info, 익절 단계(tp_stage_reached·tp_sell_stage), calc_buy_amount,
#     stock_looks_halted, N7 지수 200일선 배수 전체(n7_*), n7_status_lines
#   - 바꿈: 토스 API → 메리츠(MeritzDcaClient) · 텔레그램 토큰은 3번 .env 를 읽기만 · 시간은 미국 동부 기준
#   - 뺌: 한국주식(국내 API 불필요) · 2번 스나이퍼 시드 계산 · 토스 주문내역 일차 추정(장부 원금으로만 추정)
#   - 더함: 봇 장부(수량·원금, 입고 평단 안 씀) · 정수 주문 수량 계산(이월/최소 1주) · 모의 표시
# v1.0.2 (2026-11-13): 낮 자동환전 참고가 fallback (BOT_VERSION만, 코드 변경은 main.py·meritz_api.py)
# v1.1.0 (2026-11-13): SGOV 회차 적립(sgov.py) — 잔고 자동 등록에서 SGOV(설정 sgov.symbol)는 일반 종목으로 넣지 않음
# v1.1.1 (2026-11-13): BOT_VERSION만 (버튼 무응답 수정은 main.py — 다른 모듈은 CHAT_ID 를 t_core.CHAT_ID 로 볼 것)
# v1.1.2 (2026-11-13): BOT_VERSION만 (SGOV FRED 자료 받기 urllib → requests, sgov.py HIST_FETCH)
# v1.2.0 (2026-11-13): 하단 고정 메뉴 추가
# v1.2.1 (2026-11-13): 하단 키보드는 3개(주식·SGOV·자금)만. 나머지 4개(보유종목·종목 추가·관제탑·설정)는
#   각 메뉴 안의 인라인 버튼으로 이동 (보유종목·종목 추가는 주식 패널, 설정은 자금 패널의 시드 설정,
#   관제탑은 모든 패널의 인라인 버튼). 입력 단어(보유종목·종목 추가·관제탑·설정)는 그대로 동작.
# v1.2.2 (2026-11-13): 시드 설정 2개 메뉴 분리 (적립 / SGOV) — BOT_VERSION만 올리고 내용은 main.py에.
# v1.2.3 (2026-11-13): 하단 키보드 3번째를 자금 → 관제탑으로. 자금은 관제탑 패널 안의 [💰 자금]으로 들어간다.
#   관제탑 패널에서 주식·SGOV로 옮길 수 있는 버튼(보유종목 리스트·종목 추가·SGOV 적립·익절/매도비율·지수 배수)은
#   주식/SGOV 패널로 이동 (내용은 t_ui.py·main.py에).
# v1.2.4 (2026-11-13): 관제탑 지금/완성 시 예상 토글 제거 — 진행률은 항상 지금 기준으로만 보여준다.
# =====================================================================
import os, sys, time, json, math, asyncio, requests
import replay_log as RL   # 3번과 같은 재생 로그 (state_dir/logs)
from datetime import datetime
from zoneinfo import ZoneInfo
from dca_engine import DcaConfigManager

BOT_VERSION = "v1.2.4"
BOT_TITLE = "🟦메리츠 적립"
HUB_NAME = "메리츠 적립"
KST_TZ, EST_TZ = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS = {}          # main 이 매 반복마다 다시 읽어 채움
RUN = {"dry": True, "gate": [], "key_ok": False}   # 화면·알림 표시용 현재 모드
TG_TOKEN, CHAT_ID = "", ""
fail_reasons = {}


def read_env_file(path):
    """KEY=VALUE 파일에서 값만 읽음 (출력하지 않음). 없으면 {}"""
    out = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip().removeprefix("export ").strip()
                out[k] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def load_telegram(env_path):
    global TG_TOKEN, CHAT_ID
    env = read_env_file(env_path)
    TG_TOKEN = env.get("TELEGRAM_BOT_TOKEN", "").strip()
    CHAT_ID = env.get("TELEGRAM_CHAT_ID", "").strip()
    return bool(TG_TOKEN and CHAT_ID)


def tg_api(method, payload=None):
    if not TG_TOKEN: return None
    t0 = time.time()
    try: res = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/{method}", json=payload, timeout=10).json()
    except Exception as e:
        RL.err("tg_" + method, e, reason="tg_no_response", event_type="user_visible"); res = None
    RL.tg_result(method, payload, res, int((time.time() - t0) * 1000))
    return res


def send_panel(text, inline_kb, msg_id=None):
    head = ("🧪[모의] " if RUN.get("dry", True) else "") + BOT_TITLE
    payload = {"chat_id": CHAT_ID, "text": head + "\n" + text, "reply_markup": {"inline_keyboard": inline_kb}}
    if msg_id:
        payload["message_id"] = msg_id
        res = tg_api("editMessageText", payload)
        if res and (res.get("ok") or "not modified" in str(res.get("description", ""))): return
    tg_api("sendMessage", payload)



# 하단 키보드는 인라인 키보드와 별도 메시지로 전송한다.
# v1.2.1: 하단에는 3개 메뉴(주식·SGOV·자금)만. 나머지 4개는 각 메뉴 안의 인라인 버튼으로.
def send_bottom_menu():
    return tg_api("sendMessage", {"chat_id": CHAT_ID, "text": "📌 메뉴", "reply_markup": {
        "keyboard": [[{"text": "주식"}, {"text": "SGOV"}, {"text": "관제탑"}]],
        "resize_keyboard": True, "is_persistent": True}})

def check_holiday():
    if datetime.now(EST_TZ).weekday() >= 5: return True, "주말 휴장 (Weekend, 미국 동부 기준)"
    return False, "평일 (휴장 여부는 장운영 코드로 확인)"


async def ensure_cycle_fields():
    cfg = await DcaConfigManager.load()
    changed = False
    for k, v in [("us_exec_time", SETTINGS.get("order_time_et", "10:05")), ("cycle_mode", "buy_1"), ("cycle_day", 0),
                 ("max_days", 100), ("tp1_pct", 10.0), ("sr_pct", 20.0), ("last_fail_alert_us", ""), ("pending_orders", [])]:
        if k not in cfg: cfg[k] = v; changed = True
    if changed: await DcaConfigManager.save(cfg)
    return cfg


def is_us_symbol(sym: str) -> bool:
    s = str(sym or "").strip().upper()
    return bool(s) and not s.isdigit() and len(s) <= 12 and all(ch.isalnum() or ch in ".-" for ch in s) and s[0].isalpha()


def new_stock_entry(sym, name, ledger_qty=0.0, ledger_principal=0.0, source="new", base_amount=40.0, tp1=10.0, sr=20.0):
    """3번 sync_holdings_from_toss 의 새 종목 기본값과 같음 (미국 $40, 중지 상태로 등록) + 봇 장부"""
    return {"name": name, "currency": "USD", "market": "US", "base_amount": float(base_amount),
            "target_profit_pct": float(tp1), "sell_ratio_pct": float(sr), "enabled": False,
            "has_held": ledger_qty > 0, "s_mode": "buy_1", "s_day": 0, "s_target_days": 100, "sold_stage": 0,
            "ledger": {"qty": round(float(ledger_qty), 6), "principal": round(float(ledger_principal), 4), "source": source},
            "buy_carry": 0.0}


async def sync_holdings_from_meritz(client):
    """3번 sync_holdings_from_toss 와 같은 일: 증권사에 있는데 목록에 없는 미국 종목을 '중지' 상태로 등록.
    다른 점: 시작 상태 주입(--inject-start) 전에는 아무것도 등록하지 않음 (입고 중인 종목이 증권사 평단으로 잡히지 않게)."""
    cfg = await ensure_cycle_fields()
    if not cfg.get("start_injected"):
        return cfg
    stocks = cfg.get("stocks", {})
    excl = {str(x).upper() for x in (SETTINGS.get("exclude_symbols") or [])}
    sg = cfg.get("sgov") if isinstance(cfg.get("sgov"), dict) else {}
    excl.add(str(sg.get("symbol") or "SGOV").strip().upper())   # v1.1.0: SGOV 는 별도 종류 (stocks 에 안 넣음)
    changed, added = False, []
    try:
        items = await asyncio.wait_for(client.get_all_holdings(), timeout=8.0)
        for it in items:
            sym = str(it.get("symbol", "")).upper().strip()
            if not is_us_symbol(sym) or sym in excl or sym in stocks: continue
            if float(it.get("qty") or 0) <= 0: continue
            try:
                h = await client.get_symbol_holdings(sym)
                q, bavg = float(h.get("qty") or 0), float(h.get("broker_avg") or 0)
            except Exception:
                continue
            stocks[sym] = new_stock_entry(sym, it.get("name", sym), q, q * bavg, "broker_avg",
                                          tp1=float(cfg.get("tp1_pct", 10.0)), sr=float(cfg.get("sr_pct", 20.0)))
            changed = True; added.append(sym)
    except Exception as e:
        RL.err("holdings_sync", e)
    if changed:
        aref = RL.audit("holdings_new_stocks", symbols=added)
        RL.ev("state_change", "stock_auto_added", count=len(added), sym_refs=[RL.ref(x) for x in added][:10], enabled=False, audit_ref=aref)
        fresh = await DcaConfigManager.load()
        for x in added:
            fresh.setdefault("stocks", {}).setdefault(x, stocks[x])
        await DcaConfigManager.save(fresh)
        return fresh
    return cfg


# ---------------------------------------------------------------- 봇 장부 (입고 평단을 믿지 않음)
def ledger_of(s: dict):
    lg = s.get("ledger") or {}
    q = float(lg.get("qty") or 0.0)
    p = float(lg.get("principal") or 0.0)
    return q, p


def ledger_avg(s: dict) -> float:
    q, p = ledger_of(s)
    return round(p / q, 6) if q > 1e-9 else 0.0


def ledger_apply_fill(s: dict, side: str, q: float, amt: float):
    """체결 1건(또는 늘어난 부분) 반영. 매수: 수량·원금 더함. 매도: 평단 그대로 두고 원금에서 수량×평단을 뺌."""
    lg = dict(s.get("ledger") or {"qty": 0.0, "principal": 0.0, "source": "fills"})
    qty, pr = float(lg.get("qty") or 0.0), float(lg.get("principal") or 0.0)
    q, amt = float(q), float(amt)
    if q <= 0: return
    if side == "BUY":
        qty, pr = qty + q, pr + amt
    else:
        avg = pr / qty if qty > 1e-9 else 0.0
        qty = max(0.0, qty - q)
        pr = 0.0 if qty <= 1e-9 else max(0.0, pr - q * avg)
    lg.update(qty=round(qty, 6), principal=round(pr, 4))
    s["ledger"] = lg


# ---------------------------------------------------------------- 정수 주문 수량 (메리츠는 1주 단위 주문)
def int_buy_qty(budget: float, carry: float, price: float, mode: str = "carry"):
    """(살 수량, 다음 날로 넘길 금액). carry: 오늘 금액+이월 금액으로 살 수 있는 만큼, 남은 돈은 이월 (100일 평균 = 기준금액).
    min1: 3번 한국주식과 같이 max(1, 금액 ÷ 가격) (금액이 1주보다 작아도 1주 — 기준금액보다 많이 쓸 수 있음)."""
    if price <= 0: return 0, float(carry or 0.0)
    if mode == "min1":
        return max(1, int(float(budget) // price)), 0.0
    pool = float(budget) + max(0.0, float(carry or 0.0))
    q = int(pool // price)
    return q, round(pool - q * price, 4)


def int_sell_qty(qty: float, ratio_pct: float) -> int:
    """3번 한국주식 익절 수량과 같음: 정수 보유의 ratio% 반올림, 최소 1주, 보유 이내"""
    iq = int(math.floor(float(qty) + 1e-9))
    if iq <= 0: return 0
    return min(iq, max(1, int(round(iq * (float(ratio_pct) / 100.0)))))


def int_split_sell_qty(qty: float, rem_days: int) -> int:
    """3번 한국주식 분할매도와 같음: 남은 일수로 나눈 반올림, 최소 1주, 보유 이내"""
    iq = int(math.floor(float(qty) + 1e-9))
    if iq <= 0: return 0
    return min(iq, max(1, int(round(iq / max(1, int(rem_days))))))


async def auto_detect_cycle_days(client, sym: str, is_kr: bool, base_amt: float, avg_p: float, qty: float) -> int:
    # 3번의 2번째 방법만: 보유 수량 × 평단(장부 원금) ÷ 기준금액으로 매수 일수 추정 (메리츠 주문내역 추정은 쓰지 않음)
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


# NYSE calendar, copied from fanding_trade.py (2026–2028).
US_CLOSED = {
    2026: "01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25",
    2027: "01-01 01-18 02-15 03-26 05-31 06-18 07-05 09-06 11-25 12-24",
    2028: "01-17 02-21 04-14 05-29 06-19 07-04 09-04 11-23 12-25",
}

def is_trading_day(d):
    if d.weekday() >= 5: return False
    return d.strftime("%m-%d") not in US_CLOSED.get(d.year, "").split()

