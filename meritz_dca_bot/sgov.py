# =====================================================================
# FILE: meritz_dca_bot/sgov.py   (MERITZ_DCA v1.1.0)
# SGOV(미국 초단기 국채 ETF) 회차 적립 — NKE/QLD 적립과 같은 봇·같은 4번 계좌, 판단 공식은 완전히 따로.
# v1.1.0 (2026-11-13): 첫 버전.
#   - 설정: 상태 파일의 최상위 "sgov" 블록 (stocks 옆). stocks["SGOV"] 로 넣지 않음
#   - 모으기만: 익절·N7 배수·분할매도·½ 매수 없음
#   - 환율 관문 2개 (둘 다 통과해야 매수, 아니면 그 회차는 맨 뒤로 붙임 — 다음 회차에 몰아 사지 않음)
#     (a) 회차 날 메리츠 적용환율 < 최근 fx_avg_months(36)개월 USD/KRW 일별 종가 평균 (공개 자료, 하루 1번 받아 저장)
#         자료 받기 실패·기간 부족 → 그 회차 건너뜀 (안전 쪽: 매수 없음)
#     (b) 회차 날 환율이 7일 전보다 skip_jump_pct(기본 1.5)% 이상 오름 → 건너뜀
#   - 연속 건너뜀은 메뉴 설정(skip_cap_mode): review(기본) / proceed3
#   - 현금 분리: SGOV 대기 달러(wait_usd)·회차 예약분은 적립 매수가 쓰지 못함. 금액은 설정에만 (코드에 달러 금액 없음)
#   - 모의(dry_run): 주문·환전 API 를 부르지 않음 (주문은 main._order 의 모의 경로, 환전은 부르지 않음)
# =====================================================================
import calendar
import copy
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from t_core import *

SKIP_X_CHOICES = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
CAP_MODES = {
    "review": "3회 연속 건너뛰면 재점검 (강제 매수 없음)",
    "proceed3": "3회째는 절대 조건만 통과하면 진행",
}
FX_HISTORY_URL_DEFAULT = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXKOUS"   # FRED 공개 CSV (키 없음)
HIST_RETRY_SEC = 1800          # 받기 실패 뒤 다시 시도까지 (그동안 관문 (a) = 실패)
REF_TOLERANCE_DAYS = 3         # '7일 전' 환율이 그날 없으면 최대 3일 더 앞까지 찾음

SGOV_DEFAULTS = {
    "enabled": False, "symbol": "SGOV",
    "target_usd_total": 0.0, "tranche_usd": 0.0, "first_tranche_usd": 0.0,
    "tranches_total": 0, "tranches_done": 0, "interval_days": 0, "next_due_date": "",
    "skip_jump_pct": 1.5, "skip_cap_mode": "review", "fx_avg_months": 36,
    "wait_usd": 0.0,                       # SGOV 대기 달러 (분배금 + 정수 주문 남은 돈) — 적립 매수에 쓰지 않음
    "skip_streak": 0, "skip_streak_b": 0, "skips_total": 0, "review_hold": False,
    "last_exec_date": "", "last_decision": {},
    "ledger": {"qty": 0.0, "principal": 0.0, "distributions_usd": 0.0},
}
# 설치 때 settings.json 의 "sgov" 에서 처음 한 번만 가져오는 값 (enabled 는 가져오지 않음 → 메뉴에서 직접 켬)
SEED_KEYS = ("symbol", "target_usd_total", "tranche_usd", "first_tranche_usd", "tranches_total", "interval_days",
             "next_due_date", "skip_jump_pct", "skip_cap_mode", "fx_avg_months")
# 회차 판단이 저장하는 값 (메뉴에서 바꾸는 enabled·skip_jump_pct·skip_cap_mode 는 덮어쓰지 않음)
PROGRESS_KEYS = ("tranches_total", "tranches_done", "next_due_date", "wait_usd", "skip_streak", "skip_streak_b",
                 "skips_total", "review_hold", "last_exec_date", "last_decision")

_HIST = {"fail_ts": 0.0, "fail_day": ""}
_DAILY = {"day": ""}


def HIST_FETCH(url):
    """공개 환율 자료 받기 (테스트에서 바꿔 끼움). 실패하면 예외"""
    req = urllib.request.Request(url, headers={"User-Agent": "meritz-dca/" + BOT_VERSION})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", "replace")


# ---------------------------------------------------------------- 설정 블록
def sgov_block(cfg: dict) -> dict:
    """cfg["sgov"] 를 기본값으로 채워 돌려줌 (없으면 만들고 settings.sgov 에서 금액·일정만 처음 1번 가져옴)."""
    sg = cfg.get("sgov")
    if not isinstance(sg, dict):
        sg = copy.deepcopy(SGOV_DEFAULTS)
        seed = SETTINGS.get("sgov") if isinstance(SETTINGS.get("sgov"), dict) else {}
        for k in SEED_KEYS:
            if k in seed: sg[k] = copy.deepcopy(seed[k])
        cfg["sgov"] = sg
    for k, v in SGOV_DEFAULTS.items():
        if k not in sg: sg[k] = copy.deepcopy(v)
    if not isinstance(sg.get("ledger"), dict): sg["ledger"] = copy.deepcopy(SGOV_DEFAULTS["ledger"])
    for k, v in SGOV_DEFAULTS["ledger"].items():
        sg["ledger"].setdefault(k, v)
    sg["symbol"] = str(sg.get("symbol") or "SGOV").strip().upper()
    return sg


def sgov_symbol(cfg: dict) -> str:
    sg = cfg.get("sgov") if isinstance(cfg.get("sgov"), dict) else {}
    return str(sg.get("symbol") or "SGOV").strip().upper()


def _f(v, d=0.0):
    try: return float(v)
    except (TypeError, ValueError): return d


def _d(s):
    try: return date.fromisoformat(str(s))
    except (TypeError, ValueError): return None


def sgov_problems(sg: dict) -> list:
    """켜져 있을 때 설정 검사 → 문제 목록 (빈 목록 = 통과). 문제가 있으면 회차 판단·주문 안 함"""
    if not sg.get("enabled"): return []
    bad = []
    tot, tr, fst = _f(sg.get("target_usd_total")), _f(sg.get("tranche_usd")), _f(sg.get("first_tranche_usd"))
    n = int(_f(sg.get("tranches_total")))
    if tot <= 0: bad.append("target_usd_total 없음")
    if tr <= 0: bad.append("tranche_usd 없음")
    if fst <= 0: bad.append("first_tranche_usd 없음")
    elif tr > 0 and fst > tr: bad.append("first_tranche_usd 가 tranche_usd 보다 큼 (첫 회차는 작게)")
    if n < 1: bad.append("tranches_total 1 이상")
    if int(_f(sg.get("interval_days"))) < 1: bad.append("interval_days 1 이상")
    if not _d(sg.get("next_due_date")): bad.append("next_due_date 날짜 아님 (YYYY-MM-DD, 미국 동부)")
    if _f(sg.get("skip_jump_pct")) <= 0: bad.append("skip_jump_pct 0 이하")
    if sg.get("skip_cap_mode") not in CAP_MODES: bad.append("skip_cap_mode 는 review / proceed3")
    if int(_f(sg.get("fx_avg_months"))) < 1: bad.append("fx_avg_months 1 이상")
    if tot > 0 and tr > 0 and fst > 0 and n >= 1 and fst + tr * (n - 1 - int(_f(sg.get("skips_total")))) > tot * 1.01:
        bad.append("회차 금액 합계가 target_usd_total 보다 큼")
    return bad


def tranche_amount(sg: dict) -> float:
    """이번 회차 금액: 첫 매수는 first_tranche_usd, 그 뒤는 tranche_usd (건너뛴 회차는 맨 뒤로 붙어 같은 금액)"""
    return _f(sg.get("first_tranche_usd")) if int(_f(sg.get("tranches_done"))) == 0 else _f(sg.get("tranche_usd"))


def next_due_after(due_str: str, interval: int, today_str: str) -> str:
    """다음 회차 날짜 = 이번 예정일 + 간격 (오늘보다 뒤가 될 때까지) → 미국 거래일로 맞춤"""
    d = _d(due_str) or _d(today_str); t = _d(today_str); step = timedelta(days=max(1, int(interval)))
    d = d + step
    while d <= t: d += step
    while not is_trading_day(d): d += timedelta(days=1)
    return d.isoformat()


# ---------------------------------------------------------------- 환율 자료 (공개 일별 종가 + 메리츠 적용환율 기록)
def _state(name):
    return Path(SETTINGS.get("state_dir") or ".") / name


def parse_history_csv(text: str) -> list:
    """FRED CSV(날짜,값 / 빈 값 '.') → [(YYYY-MM-DD, 값)] 오름차순"""
    out = {}
    for line in str(text or "").splitlines():
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) < 2 or not _d(parts[0]): continue
        try: v = float(parts[1])
        except ValueError: continue
        if v > 0: out[parts[0]] = v
    return sorted(out.items())


def _read_json(p, default):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return default


def _write_json(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


async def get_history(today_kst: str):
    """(종가 목록 또는 None, 이유). 하루 1번만 받음. 오늘 받기 실패면 None (옛 자료로 판단하지 않음 — 안전 쪽)"""
    p = _state("fx_usdkrw_history.json")
    c = _read_json(p, {})
    if c.get("fetched_kst") == today_kst and c.get("closes"):
        return [tuple(x) for x in c["closes"]], "cache_today"
    if _HIST["fail_day"] == today_kst and time.time() - _HIST["fail_ts"] < HIST_RETRY_SEC:
        return None, "fetch_failed_recently"
    url = str(SETTINGS.get("sgov_fx_history_url") or FX_HISTORY_URL_DEFAULT)
    try:
        closes = parse_history_csv(await asyncio.to_thread(HIST_FETCH, url))
        if len(closes) < 100: raise ValueError(f"자료 너무 적음 ({len(closes)}행)")
    except Exception as e:
        _HIST.update(fail_ts=time.time(), fail_day=today_kst)
        RL.err("sgov_fx_history", e, event_type="external_call")
        return None, "fetch_failed"
    _write_json(p, {"fetched_kst": today_kst, "source": url.split("?")[0], "closes": closes})
    RL.ev("external_call", "sgov_fx_history", "ok", None, actor="scheduler", rows=len(closes), last=closes[-1][0])
    return closes, "fetched"


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    y += d.year; m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def avg_months(closes, today_str: str, months: int):
    """(평균, 개수, 이유). 기간이 모자라거나 최근 자료가 없으면 (None, n, 이유) — 모자란 자료로 평균 내지 않음"""
    if not closes: return None, 0, "no_history"
    t = _d(today_str); start = _add_months(t, -int(months))
    win = [(d, v) for d, v in closes if start.isoformat() <= d <= today_str]
    n = len(win)
    if n < int(months) * 15: return None, n, "history_short"
    if _d(win[0][0]) > start + timedelta(days=31): return None, n, "history_start_late"
    if _d(win[-1][0]) < t - timedelta(days=14): return None, n, "history_stale"
    return sum(v for _, v in win) / n, n, None


def record_rate(day: str, rate: float):
    """메리츠 적용환율을 날짜별로 남김 (관문 (b) 7일 전 비교용, 최근 60일만)"""
    p = _state("fx_applied_rates.json")
    d = _read_json(p, {})
    if not isinstance(d, dict): d = {}
    d[day] = round(float(rate), 4)
    keep = sorted(d)[-60:]
    _write_json(p, {k: d[k] for k in keep})


def _on_or_before(pairs: dict, target: date, tol: int):
    for i in range(tol + 1):
        k = (target - timedelta(days=i)).isoformat()
        if k in pairs: return k, float(pairs[k])
    return None, None


def weekly_jump(rate_today: float, today_kst: str, closes):
    """(오른 %, 기준, 비교 날짜). 1순위: 메리츠 적용환율 기록(같은 기준). 2순위: 공개 종가끼리 (최근 종가 vs 그 7일 전).
    둘 다 없으면 (None, "no_reference", None) → 관문 (b) 실패"""
    t = _d(today_kst)
    snaps = _read_json(_state("fx_applied_rates.json"), {})
    k, r = _on_or_before(snaps if isinstance(snaps, dict) else {}, t - timedelta(days=7), REF_TOLERANCE_DAYS)
    if r and r > 0:
        return (rate_today - r) / r * 100.0, "meritz", k
    if closes:
        hist = dict(closes)
        last = [d for d, _ in closes if d <= today_kst]
        if last and _d(last[-1]) >= t - timedelta(days=10):
            lk = last[-1]; k2, r2 = _on_or_before(hist, _d(lk) - timedelta(days=7), REF_TOLERANCE_DAYS)
            if r2 and r2 > 0:
                return (hist[lk] - r2) / r2 * 100.0, "history", f"{k2}→{lk}"
    return None, "no_reference", None


async def gate_inputs(client, sg: dict, today_kst: str) -> dict:
    """관문 판단에 쓰는 값 모으기 (조회만). 어떤 실패도 예외 대신 값 None 으로 → 관문 실패 = 매수 없음"""
    out = {"rate": None, "avg": None, "avg_n": 0, "avg_why": None, "jump": None, "jump_basis": None, "jump_ref": None}
    closes, hwhy = await get_history(today_kst)
    try:
        r = await asyncio.to_thread(client.api.fx_applied_rate)
        rate = float(r.get("rate"))
        if not math.isfinite(rate) or rate <= 0: raise ValueError("rate<=0")
        out["rate"] = rate; record_rate(today_kst, rate)
    except Exception as e:
        RL.err("sgov_fx_rate", e, event_type="external_call"); out["rate_why"] = "rate_error"
    if closes is None:
        out["avg_why"] = hwhy
    else:
        out["avg"], out["avg_n"], out["avg_why"] = avg_months(closes, today_kst, int(_f(sg.get("fx_avg_months"), 36)))
    if out["rate"]:
        out["jump"], out["jump_basis"], out["jump_ref"] = weekly_jump(out["rate"], today_kst, closes)
    return out


def eval_gates(gi: dict, x_pct: float) -> dict:
    """관문 (a)(b) 결과. 값이 없으면 그 관문은 실패 (안전 쪽)"""
    rate, avg, jump = gi.get("rate"), gi.get("avg"), gi.get("jump")
    a_ok = bool(rate and avg and rate < avg)
    b_ok = bool(jump is not None and jump < float(x_pct))
    a_why = None if a_ok else ("rate_error" if not rate else (gi.get("avg_why") or "no_avg") if not avg else "rate_not_below_avg")
    b_why = None if b_ok else ("no_reference" if jump is None else "weekly_jump")
    return {"a_ok": a_ok, "b_ok": b_ok, "a_why": a_why, "b_why": b_why}


# ---------------------------------------------------------------- 회차 판단 (적립 판단과 별개의 순수 함수)
def sgov_precheck(sg: dict, today_str: str):
    """관문 전에 걸러지는 경우 → 이유 문자열, 판단할 차례면 None"""
    if not sg.get("enabled"): return "disabled"
    if sgov_problems(sg): return "config_problem"
    if int(_f(sg.get("tranches_done"))) >= int(_f(sg.get("tranches_total"))): return "complete"
    if sg.get("last_exec_date") == today_str: return "done_today"
    due = _d(sg.get("next_due_date"))
    if not due or _d(today_str) < due: return "not_due"
    if not is_trading_day(_d(today_str)): return "not_trading_day"
    if sg.get("review_hold"): return "review_hold"
    return None


def sgov_decide(sg: dict, gates: dict) -> dict:
    """관문 결과 + 연속 건너뜀 설정 → {"action": buy/skip_a/skip_b, "override_b": bool}"""
    if not gates["a_ok"]: return {"action": "skip_a", "override_b": False, "why": gates["a_why"]}
    if gates["b_ok"]: return {"action": "buy", "override_b": False, "why": None}
    if sg.get("skip_cap_mode") == "proceed3" and int(_f(sg.get("skip_streak_b"))) >= 2:
        return {"action": "buy", "override_b": True, "why": "proceed3_third"}
    return {"action": "skip_b", "override_b": False, "why": gates["b_why"]}


def apply_skip(sg: dict, kind: str, today_str: str):
    """건너뜀: 그 회차를 맨 뒤에 붙임 (tranches_total +1), 다음 예정일은 원래 간격대로 — 다음 회차에 몰아 사지 않음"""
    sg["tranches_total"] = int(_f(sg.get("tranches_total"))) + 1
    sg["skips_total"] = int(_f(sg.get("skips_total"))) + 1
    sg["skip_streak"] = int(_f(sg.get("skip_streak"))) + 1
    if kind == "b": sg["skip_streak_b"] = int(_f(sg.get("skip_streak_b"))) + 1   # (a) 건너뜀은 proceed3 횟수에 안 셈
    sg["next_due_date"] = next_due_after(sg.get("next_due_date"), int(_f(sg.get("interval_days"), 1)), today_str)
    sg["last_exec_date"] = today_str
    if sg.get("skip_cap_mode", "review") == "review" and sg["skip_streak"] >= 3:
        sg["review_hold"] = True


def buy_plan(sg: dict, price: float, buffer_pct: float) -> dict:
    """정수 주 수량 + 1% 여유 포함 필요 달러 (적립 매수와 같은 계산). 남은 돈은 SGOV 대기 달러로 넘김"""
    budget = round(tranche_amount(sg) + max(0.0, _f(sg.get("wait_usd"))), 4)
    q = int(budget // price) if price > 0 else 0
    need = round(q * price * (1 + float(buffer_pct) / 100.0), 2)
    return {"budget": budget, "qty": q, "need": need, "left": round(budget - q * price, 4)}


def apply_buy(sg: dict, plan: dict, today_str: str):
    sg["tranches_done"] = int(_f(sg.get("tranches_done"))) + 1
    sg["wait_usd"] = max(0.0, plan["left"])
    sg["skip_streak"] = 0; sg["skip_streak_b"] = 0
    sg["next_due_date"] = next_due_after(sg.get("next_due_date"), int(_f(sg.get("interval_days"), 1)), today_str)
    sg["last_exec_date"] = today_str


async def save_sgov_progress(sg: dict):
    """회차 판단 결과만 최신 설정에 씀 (메뉴에서 바꾼 X·모드·켜짐은 그대로, 장부는 체결 반영이 씀)"""
    fresh = await DcaConfigManager.load(); fsg = sgov_block(fresh)
    for k in PROGRESS_KEYS:
        if k in sg: fsg[k] = copy.deepcopy(sg[k])
    await DcaConfigManager.save(fresh)


def _kst_day():
    return datetime.now(KST_TZ).strftime("%Y-%m-%d")


def _gate_txt(gi, g, x, months=36):
    a = f"(a) 적용환율 {gi['rate']:.2f} {'<' if g['a_ok'] else '≥'} {int(months)}개월 평균 {gi['avg']:.2f}" if gi.get("rate") and gi.get("avg") \
        else f"(a) 자료 없음 ({g['a_why']}) → 안전하게 건너뜀"
    b = f"(b) 7일 전 대비 {gi['jump']:+.2f}% ({'기준 미만' if g['b_ok'] else f'{x:g}% 이상'}, {gi.get('jump_basis')})" if gi.get("jump") is not None \
        else "(b) 7일 전 환율 없음 → 건너뜀"
    return a, b


# ---------------------------------------------------------------- 하루 단계 (main.execute_us_step 이 적립 매수 전에 부름)
async def sgov_step(client, order_fn, today_str: str, live: bool) -> dict:
    """SGOV 회차 1번 판단·주문. 돌려줌 {"reserve": 적립 매수가 쓰면 안 되는 달러, "logs": [...]}.
    어떤 예외도 밖으로 내보내지 않음 → SGOV 문제로 NKE/QLD 매수가 멈추지 않음."""
    out = {"reserve": 0.0, "logs": []}
    try:
        cfg = await DcaConfigManager.load()
        raw = json.dumps(cfg.get("sgov"), sort_keys=True, ensure_ascii=False)
        sg = sgov_block(cfg)
        if json.dumps(sg, sort_keys=True, ensure_ascii=False) != raw: await DcaConfigManager.save(cfg)   # 빠진 기본값만 채워 저장
        sym = sg["symbol"]
        out["reserve"] = max(0.0, _f(sg.get("wait_usd")))          # (i) 대기 달러는 늘 SGOV 몫
        pre = sgov_precheck(sg, today_str)
        if pre:
            if pre == "config_problem" and RL.once("sgov|config_problem"):
                RL.ev("decision", "sgov_tranche", "skipped", "config_problem", actor="scheduler", n=len(sgov_problems(sg)))
                send_panel("⛔ [SGOV 설정 확인 필요 — 회차 판단 안 함]\n" + "\n".join("• " + b for b in sgov_problems(sg)),
                           [[{"text": "🪙 SGOV 적립", "callback_data": "sgov"}]])
            elif pre == "review_hold" and RL.once("sgov|review_hold"):
                RL.ev("decision", "sgov_tranche", "skipped", "review_hold", actor="scheduler", streak=sg.get("skip_streak"))
                send_panel("🛑 [SGOV 재점검 대기 — 매수 안 함]\n• 3회 연속 건너뛰어 회차를 멈췄습니다 (강제 매수 없음).\n"
                           "• 규칙·환율 자료·남은 일정을 확인한 뒤 SGOV 메뉴에서 '재점검 완료'를 눌러 주세요.",
                           [[{"text": "🪙 SGOV 적립", "callback_data": "sgov"}]])
            elif pre not in ("disabled", "not_due", "done_today", "complete"):
                RL.count("sgov_skip:" + pre)
            return out
        n_now = int(_f(sg.get("tranches_done"))) + 1; n_tot = int(_f(sg.get("tranches_total")))
        x = _f(sg.get("skip_jump_pct"), 1.5)
        gi = await gate_inputs(client, sg, _kst_day())
        g = eval_gates(gi, x)
        dec = sgov_decide(sg, g)
        a_txt, b_txt = _gate_txt(gi, g, x, _f(sg.get("fx_avg_months"), 36))
        sg["last_decision"] = {"date": today_str, "action": dec["action"], "why": dec.get("why"), "rate": gi.get("rate"),
                               "avg": round(gi["avg"], 4) if gi.get("avg") else None,
                               "jump": round(gi["jump"], 4) if gi.get("jump") is not None else None, "basis": gi.get("jump_basis")}
        aref = RL.audit("sgov_decision_input", sym=sym, n=n_now, total=n_tot, x=x, mode=sg.get("skip_cap_mode"),
                        streak=sg.get("skip_streak"), streak_b=sg.get("skip_streak_b"), **{k: v for k, v in gi.items() if k != "closes"})
        if dec["action"] in ("skip_a", "skip_b"):
            kind = "a" if dec["action"] == "skip_a" else "b"
            apply_skip(sg, kind, today_str)
            await save_sgov_progress(sg)
            RL.ev("decision", "sgov_tranche", "skipped", f"gate_{kind}:{dec.get('why')}", actor="scheduler", audit_ref=aref,
                  streak=sg["skip_streak"], hold=sg.get("review_hold"))
            msg = (f"⏭ [SGOV {n_now}회차 건너뜀 — 매수 없음]\n• {a_txt}\n• {b_txt}\n"
                   f"• 이 회차는 맨 뒤로 붙였습니다 (전체 {sg['tranches_total']}회). 다음 회차에 몰아 사지 않습니다.\n"
                   f"• 다음 예정일: {sg['next_due_date']} (미국 동부) · 연속 건너뜀 {sg['skip_streak']}회")
            if sg.get("review_hold"): msg += "\n🛑 3회 연속 → 재점검 대기로 멈춤 (SGOV 메뉴에서 '재점검 완료')"
            send_panel(msg, [[{"text": "🪙 SGOV 적립", "callback_data": "sgov"}, {"text": "🎛 관제탑", "callback_data": "panel"}]])
            return out
        # ---- 관문 통과 → (ii) 이 회차 달러를 먼저 예약
        buf = float(SETTINGS.get("buy_cash_buffer_pct", 1.0))
        try: price = float(await client.get_current_price(sym) or 0.0)
        except Exception as pe: price = 0.0; RL.err("sgov_price", pe, event_type="external_call")
        out["reserve"] = round(tranche_amount(sg) + max(0.0, _f(sg.get("wait_usd"))) + tranche_amount(sg) * buf / 100.0, 2)
        if price <= 0:
            if RL.once("sgov|price"):
                RL.ev("decision", "sgov_tranche", "skipped", "price_zero_deferred", actor="scheduler")
                send_panel(f"⚠️ [SGOV {n_now}회차 미룸]\n• 현재가 조회 실패 — 오늘은 주문 안 함, 다음 거래일 다시 확인 (건너뜀 아님)",
                           [[{"text": "🪙 SGOV 적립", "callback_data": "sgov"}]])
            return out
        plan = buy_plan(sg, price, buf)
        out["reserve"] = round(plan["need"] + plan["left"], 2)
        if live:
            try: bq = float((await client.get_symbol_holdings(sym)).get("qty") or 0.0)
            except Exception: bq = None
            lq = _f(sg["ledger"].get("qty"))
            if bq is None or abs(bq - lq) > 1e-6:
                fail_reasons[sym] = f"SGOV 장부 {lq:g}주 ≠ 메리츠 {bq if bq is not None else '?'}주"
                if RL.once("sgov|ledger_mismatch"):
                    RL.ev("decision", "sgov_tranche", "skipped", "ledger_mismatch", actor="scheduler", audit_ref=aref)
                    send_panel(f"⛔ [SGOV 오늘 주문 안 함]\n• {fail_reasons[sym]}\n• 입고·수동 매매·체결 누락을 확인해 주세요. (건너뜀 아님, 회차 그대로)",
                               [[{"text": "🪙 SGOV 적립", "callback_data": "sgov"}]])
                return out
        if plan["qty"] <= 0:
            apply_buy(sg, plan, today_str); await save_sgov_progress(sg)
            RL.ev("decision", "sgov_tranche", "ok", "carry_no_order", actor="scheduler", audit_ref=aref)
            out["logs"].append(f"↪️ SGOV {n_now}회차: 1주(${price:.2f})보다 적어 주문 없이 대기 달러 ${sg['wait_usd']:.2f} 로 넘김")
            out["reserve"] = round(_f(sg["wait_usd"]), 2)
            return out
        usd_before = float(await client.get_buying_power("USD") or 0.0)
        if usd_before < plan["need"]:
            # 달러 부족: SGOV 는 미룸(건너뜀 아님, 예정일 그대로). 예약은 유지 → 적립 매수는 남은 달러로만 (부족하면 그날 쉼)
            fail_reasons[sym] = f"SGOV 달러 부족 (필요 ${plan['need']:.2f} / 보유 ${usd_before:.2f})"
            if RL.once("sgov|usd_insufficient"):
                RL.ev("decision", "sgov_tranche", "skipped", "usd_insufficient_deferred", actor="scheduler", audit_ref=aref)
                send_panel(f"⚠️ [SGOV {n_now}회차 미룸 — 달러 부족]\n• 필요 ${plan['need']:.2f} / 보유 ${usd_before:.2f}\n"
                           f"• 건너뜀이 아니라 미룸입니다 (예정일 그대로, 다음 거래일 다시 확인).\n• SGOV 몫을 먼저 떼어 두어 적립 매수는 남은 달러로만 합니다.",
                           [[{"text": "🪙 SGOV 적립", "callback_data": "sgov"}, {"text": "🎛 관제탑", "callback_data": "panel"}]])
            return out
        if not (await DcaConfigManager.load()).get("is_master_active", False):
            RL.ev("decision", "sgov_tranche", "skipped", "master_turned_off", actor="scheduler"); return out
        RL.ev("decision", "sgov_tranche", "ok", "override_b" if dec["override_b"] else None, actor="scheduler", audit_ref=aref,
              qty=plan["qty"], n=n_now)
        try:
            await order_fn("sgov", sym, "buy", plan["qty"], f"sg_{today_str}_{n_now}", client, price)
        except Exception as oe:
            sg2 = sgov_block(await DcaConfigManager.load()); sg2["last_exec_date"] = today_str
            await save_sgov_progress(sg2)            # 거절·응답 없음 모두 오늘은 다시 주문하지 않음 (회차·예정일 그대로)
            send_panel(f"⚠️ [SGOV {n_now}회차 주문 안 됨]\n• {str(oe)[:160]}\n• 오늘은 다시 주문하지 않습니다. 응답이 끊긴 경우 체결됐을 수 있으니 메리츠 앱에서 확인해 주세요.",
                       [[{"text": "🪙 SGOV 적립", "callback_data": "sgov"}]])
            return out
        spent = round(plan["qty"] * price * (1 + buf / 100.0), 2)
        apply_buy(sg, plan, today_str); await save_sgov_progress(sg); fail_reasons.pop(sym, None)
        try: usd_after = float(await client.get_buying_power("USD") or 0.0)
        except Exception: usd_after = usd_before
        already = min(spent, max(0.0, usd_before - usd_after))     # 증권사가 이미 뺀 만큼은 예약에서 뺌 (두 번 막지 않게)
        out["reserve"] = round(max(0.0, spent - already) + _f(sg["wait_usd"]), 2)
        out["logs"].append(f"🪙 SGOV {n_now}/{sg['tranches_total']}회차: {plan['qty']}주 시장가 매수 (회차 예산 ${plan['budget']:.2f}"
                           f"{' · 7일 상승 기준 무시(3회째 진행)' if dec['override_b'] else ''}) · 다음 {sg['next_due_date']}")
    except Exception as e:
        RL.err("sgov_step", e, event_type="decision")
    return out


# ---------------------------------------------------------------- 아침 환전 금액에 SGOV 몫 더하기 (main.dca_fx_plan 이 부름)
async def sgov_fx_need(client, cfg: dict, kst_day: str) -> float:
    """오늘 밤 미국장에 SGOV 회차가 있고 관문을 지금 통과하면 회차 금액 + 대기 달러. 아니면 0. 예외는 0 (환전 쪽을 막지 않음)"""
    try:
        sg = sgov_block(copy.deepcopy(cfg))
        if sgov_precheck(sg, kst_day): return 0.0
        g = eval_gates(await gate_inputs(client, sg, kst_day), _f(sg.get("skip_jump_pct"), 1.5))
        if sgov_decide(sg, g)["action"] != "buy": return 0.0
        return round(tranche_amount(sg) + max(0.0, _f(sg.get("wait_usd"))), 2)
    except Exception as e:
        RL.err("sgov_fx_need", e, event_type="decision"); return 0.0


async def sgov_daily_refresh(client, now_kst=None):
    """낮(한국 09:00~15:30 평일) 하루 1번: 공개 환율 자료 받기 + 메리츠 적용환율 기록 (조회만, 주문·환전 없음)"""
    now = (now_kst or datetime.now(KST_TZ)).astimezone(KST_TZ)
    day, hm = now.strftime("%Y-%m-%d"), now.strftime("%H:%M")
    if now.weekday() >= 5 or not ("09:00" <= hm <= "15:30") or _DAILY["day"] == day: return
    cfg = DcaConfigManager.read_sync()
    if not (cfg.get("sgov") or {}).get("enabled"): return
    _DAILY["day"] = day
    try: await gate_inputs(client, sgov_block(cfg), day)
    except Exception as e: RL.err("sgov_daily_refresh", e, event_type="external_call")


# ---------------------------------------------------------------- 화면 (텔레그램 조작판)
def sgov_panel_line(cfg: dict) -> str:
    sg = cfg.get("sgov") if isinstance(cfg.get("sgov"), dict) else {}
    if not sg.get("enabled"): return " • 🪙 SGOV 회차 적립: ⚪ 꺼짐"
    lg = sg.get("ledger") or {}
    return (f" • 🪙 SGOV 회차 적립: 🟢 {int(_f(sg.get('tranches_done')))}/{int(_f(sg.get('tranches_total')))}회 · 다음 {sg.get('next_due_date') or '-'}"
            f" · 보유 {_f(lg.get('qty')):g}주" + (" · 🛑 재점검 대기" if sg.get("review_hold") else ""))


def build_sgov_view(cfg: dict, notice: str = ""):
    sg = sgov_block(copy.deepcopy(cfg)); lg = sg["ledger"]
    x, mode = _f(sg.get("skip_jump_pct"), 1.5), sg.get("skip_cap_mode", "review")
    q, pr = _f(lg.get("qty")), _f(lg.get("principal"))
    ld = sg.get("last_decision") or {}
    act = {"buy": "매수", "skip_a": "건너뜀 (a 평균 환율)", "skip_b": "건너뜀 (b 7일 상승)"}.get(ld.get("action"), "-")
    probs = sgov_problems(sg)
    lines = [
        f"🪙 [SGOV 달러 단기 회차 적립 ({BOT_VERSION})]",
        f"▫️ 상태: {'🟢 켜짐' if sg.get('enabled') else '⚪ 꺼짐'}" + (" · 🛑 재점검 대기 (매수 멈춤)" if sg.get("review_hold") else ""),
        f"▫️ 회차: {int(_f(sg.get('tranches_done')))}/{int(_f(sg.get('tranches_total')))}회 완료 · 간격 {int(_f(sg.get('interval_days')))}일 · 건너뜀 누적 {int(_f(sg.get('skips_total')))}회",
        f"▫️ 다음 예정일: {sg.get('next_due_date') or '-'} (미국 동부) · 이번 회차 ${tranche_amount(sg):,.2f}",
        f"▫️ 연속 건너뜀: {int(_f(sg.get('skip_streak')))}회 (7일 상승 연속 {int(_f(sg.get('skip_streak_b')))}회)",
        "─────────────────",
        "⚙️ [건너뜀 규칙 — 다음 회차 판단부터 적용, 바꿔도 바로 사지 않음]",
        f" • (a) 회차 날 적용환율이 최근 {int(_f(sg.get('fx_avg_months'), 36))}개월 평균보다 낮아야 매수",
        f" • (b) 7일 전보다 {x:g}% 이상 오르면 건너뜀 (X = {x:g}%)",
        f" • 연속 건너뜀: {CAP_MODES.get(mode, mode)}",
        " • 건너뛴 회차는 맨 뒤로 붙임 (다음 회차에 몰아 사지 않음)",
        "─────────────────",
        "📒 [SGOV 장부 — NKE/QLD 적립과 따로]",
        f" • 보유 {q:g}주 · 원금 ${pr:,.2f} · 평단 ${(pr / q if q > 1e-9 else 0):.4f}",
        f" • 분배금 누적 ${_f(lg.get('distributions_usd')):,.2f} · SGOV 대기 달러 ${_f(sg.get('wait_usd')):,.2f} (다음 회차에 재투자)",
        f" • 최근 판단: {ld.get('date') or '-'} {act}" + (f" · 환율 {ld['rate']:.2f} / 평균 {ld['avg']:.2f}" if ld.get("rate") and ld.get("avg") else "")
        + (f" · 7일 {ld['jump']:+.2f}%" if ld.get("jump") is not None else ""),
    ]
    if probs: lines += ["⛔ 설정 확인 필요:"] + ["   · " + p for p in probs[:5]]
    if notice: lines = [notice, ""] + lines
    kb = [[{"text": ("✅ " if abs(v - x) < 1e-9 else "") + f"X {v:g}%", "callback_data": f"sgovx_{v:g}"} for v in SKIP_X_CHOICES[:3]],
          [{"text": ("✅ " if abs(v - x) < 1e-9 else "") + f"X {v:g}%", "callback_data": f"sgovx_{v:g}"} for v in SKIP_X_CHOICES[3:]]]
    for m, label in CAP_MODES.items():
        kb.append([{"text": ("✅ " if m == mode else "") + label, "callback_data": f"sgovmode_{m}"}])
    if sg.get("review_hold"):
        kb.append([{"text": "✅ 재점검 완료 · 다음 회차부터 다시 판단", "callback_data": "sgov_review_ok"}])
    kb.append([{"text": "💵 분배금 기록", "callback_data": "sgov_dist"},
               {"text": "⏸ SGOV 끄기" if sg.get("enabled") else "▶️ SGOV 켜기", "callback_data": "sgov_toggle"}])
    kb.append([{"text": "🔄 새로고침", "callback_data": "sgov"}, {"text": "🔙 관제탑", "callback_data": "panel"}])
    return "\n".join(lines), kb


async def sgov_menu_set(key: str, value):
    """메뉴에서 바꾸는 값만 저장 (주문·판단 없음)"""
    fresh = await DcaConfigManager.load(); sg = sgov_block(fresh)
    before = sg.get(key); sg[key] = value
    if key == "review_hold" and value is False: sg["skip_streak"] = 0; sg["skip_streak_b"] = 0
    await DcaConfigManager.save(fresh)
    RL.ev("state_change", "sgov_" + key, "ok", None, actor="user", before=before, after=value)
    return fresh


async def sgov_add_distribution(amount: float):
    """분배금(달러) 기록 → SGOV 장부 분배금 누적 + SGOV 대기 달러 (다음 회차에 재투자). 적립 쪽 달러가 아님"""
    fresh = await DcaConfigManager.load(); sg = sgov_block(fresh)
    sg["ledger"]["distributions_usd"] = round(_f(sg["ledger"].get("distributions_usd")) + amount, 4)
    sg["wait_usd"] = round(_f(sg.get("wait_usd")) + amount, 4)
    await DcaConfigManager.save(fresh)
    RL.ev("state_change", "sgov_distribution", "ok", None, actor="user", audit_ref=RL.audit("sgov_distribution", usd=amount))
    return fresh


async def sgov_preview_lines(client, cfg: dict, today_et: str) -> list:
    """--check 용 미리보기 (조회만, 저장·주문 없음)"""
    sg = sgov_block(copy.deepcopy(cfg)); sym = sg["symbol"]
    out = [f"- SGOV 회차 적립: {'켜짐' if sg.get('enabled') else '꺼짐'} · {int(_f(sg.get('tranches_done')))}/{int(_f(sg.get('tranches_total')))}회"
           f" · 다음 {sg.get('next_due_date') or '-'} · X {_f(sg.get('skip_jump_pct'), 1.5):g}% · {sg.get('skip_cap_mode')}"
           f" · 장부 {_f(sg['ledger'].get('qty')):g}주 · 대기 ${_f(sg.get('wait_usd')):.2f}"]
    for p in sgov_problems(sg): out.append("  ✗ " + p)
    pre = sgov_precheck(sg, today_et)
    gi = await gate_inputs(client, sg, _kst_day())
    g = eval_gates(gi, _f(sg.get("skip_jump_pct"), 1.5))
    a, b = _gate_txt(gi, g, _f(sg.get("skip_jump_pct"), 1.5), _f(sg.get("fx_avg_months"), 36))
    out += ["  " + a, "  " + b]
    if pre:
        out.append(f"  → 오늘 계획: 판단 없음 ({pre})")
        return out
    dec = sgov_decide(sg, g)
    if dec["action"] != "buy":
        out.append(f"  → 오늘 계획: 건너뜀 {dec['action']} ({dec.get('why')}) — 맨 뒤로 붙임, 주문 없음")
        return out
    try:
        p = float(await client.get_current_price(sym) or 0)
        plan = buy_plan(sg, p, float(SETTINGS.get("buy_cash_buffer_pct", 1.0)))
        out.append(f"  → 오늘 계획: {sym} {plan['qty']}주 매수 (회차 ${plan['budget']:.2f}, 필요 ${plan['need']:.2f}, 남은 ${plan['left']:.2f} 대기)"
                   + (" · 7일 상승 기준 무시(3회째)" if dec["override_b"] else ""))
    except Exception as e:
        out.append(f"  ✗ {sym} 시세 조회 실패 {e}")
    return out
