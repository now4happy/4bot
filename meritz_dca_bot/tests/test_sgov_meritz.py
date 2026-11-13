#!/usr/bin/env python3
# =====================================================================
# FILE: meritz_dca_bot/tests/test_sgov_meritz.py   (MERITZ_DCA v1.1.0 검증용)
# 가짜 메리츠 클라이언트로 SGOV 회차 적립을 검증 (실제 메리츠·텔레그램·인터넷 호출 없음).
# 사용:
#   python3 -I test_sgov_meritz.py --bot <새 meritz_dca_bot 폴더> [--ref <v1.0.1 meritz_dca_bot 폴더>]
#   --ref 를 주면 시나리오 5(SGOV 꺼짐 = v1.0.1 과 같은 동작)를 두 버전을 따로 돌려 비교함
# =====================================================================
import argparse, asyncio, copy, json, os, py_compile, subprocess, sys, tempfile
from datetime import datetime, timedelta, date

AP = argparse.ArgumentParser()
AP.add_argument("--bot", required=True)
AP.add_argument("--ref")
AP.add_argument("--equiv-run", action="store_true", help="(내부용) 시나리오 5 한 버전 실행 → JSON 출력")
A = AP.parse_args()
BOT = os.path.abspath(A.bot)
sys.path.insert(0, BOT)

import t_core, dca_engine
import replay_log as RL
import main as M
try:
    import sgov as SG
except ImportError:
    SG = None                      # v1.0.1 (비교용 실행)

ET, KST = t_core.EST_TZ, t_core.KST_TZ
TODAY_ET = datetime.now(ET).strftime("%Y-%m-%d")
TODAY_KST = datetime.now(KST).strftime("%Y-%m-%d")
MSGS = []


def fake_tg(method, payload=None):
    if method in ("sendMessage", "editMessageText"):   # 본문 + 버튼 글자 (메뉴 라벨 확인용)
        btns = [b.get("text", "") for row in (payload.get("reply_markup") or {}).get("inline_keyboard", []) for b in row]
        MSGS.append(payload.get("text", "") + "\n[BUTTONS] " + " | ".join(btns))
    return {"ok": True}


t_core.tg_api = fake_tg
if SG: SG.is_trading_day = lambda d: True     # 테스트 날짜가 휴장일이어도 같은 결과가 나오게


class FakeApi:
    def __init__(self, c): self.c = c
    def fx_applied_rate(self, crcd="USD", mnec_clcd="1"):
        self.c.calls["fx_applied_rate"] += 1
        if self.c.rate is None: raise RuntimeError("rate down")
        return {"rate": str(self.c.rate), "exrt_stnd_time": "120000"}
    def fx_exchange(self, *a, **k):
        self.c.calls["fx_exchange"] += 1; return {}
    def usd_estimated(self): return self.c.usd
    def krw_cash(self): return 1e12


class FakeClient:
    def __init__(self, usd=5000.0, rate=1380.0, prices=None, broker=None):
        self.usd, self.rate = usd, rate
        self.prices = prices or {"NKE": 30.0, "QLD": 35.0, "SGOV": 100.5}   # 장부 평단보다 낮게 → 익절 없음, 1주 이상 매수
        self.broker = broker or {}
        self.calls = {k: 0 for k in ("market_order", "fx_exchange", "fx_applied_rate", "get_buying_power")}
        self.orders = []
        self.api = FakeApi(self)
        self.all_holdings = []
    async def get_buying_power(self, cur="USD"): self.calls["get_buying_power"] += 1; return self.usd
    async def get_current_price(self, sym): return self.prices.get(sym, 0.0)
    async def get_reference_price(self, sym):
        # 병합본: 실제 MeritzDcaClient 와 같은 계약 (라이브 > 0 이면 그대로, 아니면 없음).
        # 가짜 클라이언트에는 전일 종가 자료가 없어 fallback 은 (0.0, None) — 테스트 가격은 항상 > 0 이라 라이브 분기만 탐.
        p = float(self.prices.get(sym, 0.0) or 0.0)
        return (p, "live") if p > 0 else (0.0, None)
    async def get_symbol_holdings(self, sym):
        q = self.broker.get(sym, 0.0); return {"qty": q, "sellable": q, "exch_id": "0321", "broker_avg": 50.0, "name": sym}
    async def get_stock_info(self, sym): return {"symbol": sym, "name": sym, "status": ""}
    async def us_market_status(self): return "004"
    async def get_all_holdings(self): return list(self.all_holdings)
    async def fills(self, a, b): return {}
    async def market_order(self, side, sym, qty):
        self.calls["market_order"] += 1; self.orders.append((side, sym, qty))
        if side == "BUY": self.usd -= qty * self.prices[sym]
        return {"no": f"N{len(self.orders)}"}
    def cached_market(self, s): return (None, None)


# ---------------------------------------------------------------- 준비
def fresh_env(live=False):
    d = tempfile.mkdtemp(prefix="sgovt_")
    s = copy.deepcopy(dca_engine.SAFE_DEFAULTS)
    s.update(state_dir=d, enabled=True, dry_run=not live, transfer_confirmed=live, auto_fx={"on": True})
    if live:
        kf = os.path.join(d, "keys.json"); json.dump({"app_key": "TESTKEY", "app_secret": "x"}, open(kf, "w"))
        s.update(key_file=kf, expected_key_fp=M.key_fingerprint(kf), forbid_key_files=[])
    t_core.SETTINGS.clear(); t_core.SETTINGS.update(s)
    t_core.RUN.update(dry=not live, gate=[], key_ok=True)
    t_core.fail_reasons.clear(); MSGS.clear()
    M._MKT.update(ts=0.0, code="")
    if SG: SG._HIST.update(fail_ts=0.0, fail_day=""); SG._DAILY.update(day="")
    p = dca_engine.config_path(s)
    dca_engine.DcaConfigManager.use(p)
    RL.setup("meritz_dca_test", t_core.BOT_VERSION, d)
    return d, p


def stock(qty, principal):
    e = t_core.new_stock_entry("X", "X", qty, principal, "settings.start", 40.0, 10.0, 20.0)
    e.update(enabled=True, s_mode="buy_1", s_day=5, has_held=True, day_set=True); return e


def sgov_cfg(**kw):
    sg = {"enabled": True, "symbol": "SGOV", "target_usd_total": 13 * 300.0, "tranche_usd": 300.0,
          "first_tranche_usd": 250.0, "tranches_total": 13, "tranches_done": 0, "interval_days": 14,
          "next_due_date": TODAY_ET, "skip_jump_pct": 1.5, "skip_cap_mode": "review", "fx_avg_months": 36,
          "ledger": {"qty": 0.0, "principal": 0.0, "distributions_usd": 0.0}}
    sg.update(kw); return sg


def write_cfg(path, sgov=None, live=False):
    cfg = copy.deepcopy(dca_engine.DcaConfigManager.DEFAULT_CONFIG)
    cfg.update(is_master_active=True, start_injected="2026-11-08", tp1_pct=10.0, sr_pct=20.0, pending_orders=[],
               stocks={"NKE": stock(10, 600.0), "QLD": stock(5, 450.0)})
    if sgov is not None: cfg["sgov"] = sgov
    dca_engine.DcaConfigManager.write_sync(cfg, path)
    if live:  # 실주문 안전장치(live_gate)는 실주문 장부의 start_injected 를 봄
        dca_engine.DcaConfigManager.write_sync(cfg, dca_engine.config_path(t_core.SETTINGS, dry=False))
    return cfg


def history(level=1400.0):
    """3년치 넘는 가짜 USD/KRW 일별 종가 CSV (FRED 모양, 빈 값 '.' 포함)"""
    t = datetime.now(KST).date(); d = t - timedelta(days=37 * 31); rows = ["observation_date,DEXKOUS"]
    while d < t:
        if d.weekday() < 5: rows.append(f"{d.isoformat()},{'.' if d.day == 1 else level}")
        d += timedelta(days=1)
    return "\n".join(rows)


def set_hist(level=1400.0, fail=False):
    def f(url):
        if fail: raise OSError("network down")
        return history(level)
    SG.HIST_FETCH = f


def set_snapshot(state_dir, rate7):
    k = (datetime.now(KST).date() - timedelta(days=7)).isoformat()
    json.dump({k: rate7}, open(os.path.join(state_dir, "fx_applied_rates.json"), "w"))


def load(): return dca_engine.DcaConfigManager.read_sync()


async def one_pass(c):
    await M.execute_us_step(c)


def run(coro): return asyncio.run(coro)


RESULTS = []
def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail)); print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail else ""))


def dca_view(cfg):
    return {k: {kk: v.get(kk) for kk in ("ledger", "s_day", "s_mode", "last_exec_date", "buy_carry", "sold_stage")}
            for k, v in cfg["stocks"].items()}


# ---------------------------------------------------------------- 시나리오 5 (버전별 실행)
def equiv_run():
    d, p = fresh_env()
    write_cfg(p, sgov=(sgov_cfg(enabled=False) if SG else None))
    c = FakeClient()
    c.all_holdings = [{"symbol": "NKE", "qty": 10}, {"symbol": "QLD", "qty": 5}]
    out = {}
    out["fx_need"] = run(M.dca_fx_plan(c, load()))
    run(one_pass(c)); run(one_pass(c))
    cfg = load()
    out["dca"] = dca_view(cfg); out["pending"] = cfg.get("pending_orders")
    out["orders"] = c.orders; out["market_order"] = c.calls["market_order"]; out["fx_exchange"] = c.calls["fx_exchange"]
    out["fail_reasons"] = dict(t_core.fail_reasons)
    out["msgs"] = [m.replace(t_core.BOT_VERSION, "VER") for m in MSGS]
    out["stock_keys"] = sorted(cfg["stocks"])
    print("JSON:" + json.dumps(out, ensure_ascii=False, sort_keys=True))


if A.equiv_run:
    equiv_run(); sys.exit(0)


# ---------------------------------------------------------------- 시나리오
def t1_buy():
    d, p = fresh_env(); write_cfg(p, sgov_cfg()); set_hist(1400); set_snapshot(d, 1375.0)
    c = FakeClient(rate=1380.0)
    run(one_pass(c)); cfg = load(); sg = cfg["sgov"]
    # 비교: 같은 조건에서 SGOV 꺼짐 → NKE/QLD 결과가 같아야 함
    d2, p2 = fresh_env(); write_cfg(p2, sgov_cfg(enabled=False)); set_hist(1400); set_snapshot(d2, 1375.0)
    c2 = FakeClient(rate=1380.0); run(one_pass(c2)); cfg2 = load()
    check("1. 관문 통과 → SGOV 매수, SGOV 장부만 갱신",
          sg["tranches_done"] == 1 and sg["ledger"]["qty"] == 2 and sg["tranches_total"] == 13 and sg["next_due_date"] > TODAY_ET
          and c.calls["market_order"] == 0,
          f"done={sg['tranches_done']} ledger={sg['ledger']} wait={sg['wait_usd']} next={sg['next_due_date']}")
    check("1b. NKE/QLD 장부·일차는 SGOV 꺼짐 실행과 같음", dca_view(cfg) == dca_view(cfg2), "")
    check("1c. SGOV 가 stocks 에 안 들어감", "SGOV" not in cfg["stocks"], "")
    return cfg


def t1b_buy_qty():
    """회차 금액이 1주보다 큰 경우: 실제 주식 수 반영 확인 (첫 회차 = 64 < 100.5 이면 0주 → 대기로 넘김)"""
    d, p = fresh_env(); write_cfg(p, sgov_cfg(first_tranche_usd=250.0, tranche_usd=300.0, target_usd_total=13 * 300.0))
    set_hist(1400); set_snapshot(d, 1375.0); c = FakeClient(rate=1380.0)
    run(one_pass(c)); sg = load()["sgov"]
    check("1d. 첫 회차 $250 → 2주 매수(모의 체결), 남은 돈 대기 달러, 장부 원금 = 체결액",
          sg["ledger"]["qty"] == 2 and abs(sg["ledger"]["principal"] - 201.0) < 1e-6 and abs(sg["wait_usd"] - 49.0) < 1e-6
          and c.calls["market_order"] == 0,
          f"ledger={sg['ledger']} wait={sg['wait_usd']}")
    # 분배금 기록 → 다음 회차 예산에 더해짐
    run(SG.sgov_add_distribution(1.0 + 0.5)); sg = load()["sgov"]
    plan = SG.buy_plan(sg, 100.5, 1.0)
    check("1e. 분배금은 SGOV 장부·대기 달러에만 → 다음 회차 예산 = 회차 + 대기",
          abs(sg["ledger"]["distributions_usd"] - 1.5) < 1e-9 and abs(plan["budget"] - (300.0 + 49.0 + 1.5)) < 1e-6,
          f"dist={sg['ledger']['distributions_usd']} budget={plan['budget']}")


def t2_gate_a():
    d, p = fresh_env(); write_cfg(p, sgov_cfg(first_tranche_usd=250.0, tranche_usd=300.0, target_usd_total=3900.0))
    set_hist(1400); set_snapshot(d, 1440.0); c = FakeClient(rate=1450.0)
    run(one_pass(c)); cfg = load(); sg = cfg["sgov"]
    no_sgov_order = not [x for x in cfg.get("pending_orders", []) if x.get("kind") == "sgov"] and sg["ledger"]["qty"] == 0
    check("2. 관문 (a) 실패 → 건너뜀, SGOV 주문 0건, 맨 뒤로 붙임",
          no_sgov_order and sg["tranches_total"] == 14 and sg["tranches_done"] == 0 and sg["next_due_date"] > TODAY_ET
          and sg["skip_streak"] == 1 and sg["skip_streak_b"] == 0 and c.calls["market_order"] == 0,
          f"total={sg['tranches_total']} next={sg['next_due_date']} why={sg['last_decision'].get('why')}")
    nke_ok = cfg["stocks"]["NKE"]["last_exec_date"] == TODAY_ET and cfg["stocks"]["QLD"]["last_exec_date"] == TODAY_ET
    check("2b. SGOV 건너뜀이 NKE/QLD 매수를 막지 않음", nke_ok, "")
    run(one_pass(c)); sg2 = load()["sgov"]
    check("2c. 같은 날 다시 돌아도 두 번 건너뛰지 않음", sg2["tranches_total"] == 14 and sg2["skips_total"] == 1, "")
    # 환율 자료 받기 실패 → 안전하게 건너뜀
    d, p = fresh_env(); write_cfg(p, sgov_cfg()); set_hist(fail=True); set_snapshot(d, 1375.0); c = FakeClient(rate=1380.0)
    run(one_pass(c)); sg = load()["sgov"]
    check("2d. 환율 자료 받기 실패 → 건너뜀(매수 없음)", sg["ledger"]["qty"] == 0 and sg["skips_total"] == 1
          and sg["last_decision"].get("why") == "fetch_failed", f"why={sg['last_decision'].get('why')}")


def t3_gate_b():
    d, p = fresh_env(); write_cfg(p, sgov_cfg(first_tranche_usd=250.0, tranche_usd=300.0, target_usd_total=3900.0))
    set_hist(1400); set_snapshot(d, 1340.0); c = FakeClient(rate=1380.0)     # +2.99% ≥ 1.5%
    run(one_pass(c)); cfg = load(); sg = cfg["sgov"]
    check("3. 관문 (b) 실패 → 건너뜀, SGOV 주문 0건",
          sg["ledger"]["qty"] == 0 and sg["tranches_total"] == 14 and sg["skip_streak_b"] == 1 and c.calls["market_order"] == 0
          and not [x for x in cfg.get("pending_orders", []) if x.get("kind") == "sgov"],
          f"jump={sg['last_decision'].get('jump')} basis={sg['last_decision'].get('basis')}")


def t4_usd_short():
    d, p = fresh_env(live=True); write_cfg(p, sgov_cfg(first_tranche_usd=250.0, tranche_usd=300.0, target_usd_total=3900.0), live=True)
    set_hist(1400); set_snapshot(d, 1375.0)
    c = FakeClient(usd=200.0, rate=1380.0, broker={"NKE": 10, "QLD": 5, "SGOV": 0})
    run(one_pass(c)); run(one_pass(c))
    cfg = load(); sg = cfg["sgov"]
    check("4. 달러 부족(가짜 실주문 모드) → SGOV 미룸, 적립 쉼, 주문 0건",
          c.calls["market_order"] == 0 and sg["tranches_done"] == 0 and sg["tranches_total"] == 13 and sg["next_due_date"] == TODAY_ET
          and cfg["stocks"]["NKE"].get("last_exec_date") != TODAY_ET and cfg["stocks"]["QLD"].get("last_exec_date") != TODAY_ET,
          f"orders={c.orders} reasons={t_core.fail_reasons}")
    c.usd = 5000.0
    for _ in range(3): run(one_pass(c))
    sg_orders = [o for o in c.orders if o[1] == "SGOV"]
    cfg = load()
    check("4b. 달러 들어온 뒤 SGOV 1번만 주문 (중복 없음), NKE/QLD 도 1번씩",
          len(sg_orders) == 1 and sg_orders[0][2] == 2 and len([o for o in c.orders if o[1] == "NKE"]) == 1
          and len([o for o in c.orders if o[1] == "QLD"]) == 1 and cfg["sgov"]["tranches_done"] == 1,
          f"orders={c.orders}")


def t4c_reserve_math():
    """예약이 적립 달러 검사에 들어가는지: SGOV 는 살 수 있지만 남은 달러로는 NKE 가 못 삼"""
    d, p = fresh_env(); write_cfg(p, sgov_cfg(first_tranche_usd=250.0, tranche_usd=300.0, target_usd_total=3900.0))
    set_hist(1400); set_snapshot(d, 1375.0); c = FakeClient(usd=260.0, rate=1380.0)
    run(one_pass(c)); cfg = load()
    check("4c. SGOV 몫 먼저 예약 → 남은 달러 부족한 적립은 그날 쉼 (모의: 예수금이 안 줄어도 예약으로 막음)",
          cfg["sgov"]["ledger"]["qty"] == 2 and cfg["stocks"]["NKE"].get("last_exec_date") != TODAY_ET
          and "SGOV 몫" in t_core.fail_reasons.get("NKE", ""), f"reasons={t_core.fail_reasons}")


def t5_equiv():
    if not A.ref:
        check("5. SGOV 꺼짐 = v1.0.1 동작", False, "--ref 없음"); return
    def go(path):
        r = subprocess.run([sys.executable, "-I", os.path.abspath(__file__), "--bot", path, "--equiv-run"],
                           capture_output=True, text=True, timeout=120)
        line = [l for l in r.stdout.splitlines() if l.startswith("JSON:")]
        if not line: raise RuntimeError(r.stdout[-800:] + r.stderr[-800:])
        return json.loads(line[-1][5:])
    old, new = go(A.ref), go(BOT)
    diff = [k for k in old if old[k] != new.get(k)]
    check("5. SGOV 꺼짐 → NKE/QLD 주문·장부·일차·알림·환전 금액이 v1.0.1 과 같음", not diff,
          f"다른 항목={diff}" if diff else f"orders(모의)={len(new['pending'] or [])}건 대기·fx_need={new['fx_need']}")


def t6_dry_fx():
    d, p = fresh_env(); write_cfg(p, sgov_cfg(first_tranche_usd=250.0, tranche_usd=300.0, target_usd_total=3900.0))
    set_hist(1400); set_snapshot(d, 1375.0); c = FakeClient(usd=0.0, rate=1380.0)
    need_on = run(M.dca_fx_plan(c, load()))
    write_cfg(p, sgov_cfg(enabled=False)); need_off = run(M.dca_fx_plan(c, load()))
    write_cfg(p, sgov_cfg(first_tranche_usd=250.0, tranche_usd=300.0, target_usd_total=3900.0))
    now = datetime.now(KST).replace(hour=10, minute=0)
    while now.weekday() >= 5: now += timedelta(days=1)
    M.is_trading_day = lambda dd: True
    r = run(M.maybe_auto_fx(c, now))
    for _ in range(2): run(one_pass(c))
    check("6. 모의: 아침 환전 금액에 SGOV 몫 포함, fx_exchange·주문 API 0건",
          abs(need_on - need_off - 250.0) < 1e-6 and r == "dry_run" and c.calls["fx_exchange"] == 0 and c.calls["market_order"] == 0,
          f"need_on={need_on} need_off={need_off} auto_fx={r} fx_exchange={c.calls['fx_exchange']} market_order={c.calls['market_order']}")


def t7_compile():
    files = ["main.py", "t_core.py", "t_ui.py", "sgov.py"]
    ok = True
    for f in files:
        try: py_compile.compile(os.path.join(BOT, f), doraise=True)
        except Exception as e: ok = False; print(e)
    check("7. py_compile (바뀐 파일 4개)", ok, ", ".join(files))


def t8_menu():
    d, p = fresh_env(); write_cfg(p, sgov_cfg(ledger={"qty": 3.0, "principal": 301.5, "distributions_usd": 0.9}))
    c = FakeClient()
    before = dca_view(load())
    def cb(data): return {"id": "1", "data": data, "message": {"chat": {"id": t_core.CHAT_ID}, "message_id": 7}}
    MSGS.clear(); run(M.handle_callback(cb("sgovx_2"), c)); s1 = load()["sgov"]; v1 = MSGS[-1]

    run(M.handle_callback(cb("sgovmode_proceed3"), c)); s2 = load()["sgov"]; v2 = MSGS[-1]
    run(M.handle_callback(cb("panel"), c)); pv = MSGS[-1]
    banned = any(w in (v1 + v2 + pv) for w in ("GPT", "클로드", "Claude"))
    check("8. 메뉴에서 X·모드 변경 → 설정 반영·화면 표시, 주문 0건",
          s1["skip_jump_pct"] == 2.0 and s2["skip_cap_mode"] == "proceed3" and "X = 2%" in v1
          and "✅ 3회째는 절대 조건만 통과하면 진행" in v2 and "3회 연속 건너뛰면 재점검 (강제 매수 없음)" in v2
          and c.calls["market_order"] == 0 and not load().get("pending_orders") and s2["tranches_done"] == 0 and not banned,
          f"x={s1['skip_jump_pct']} mode={s2['skip_cap_mode']}")
    check("8b. SGOV 장부가 NKE/QLD 와 따로 표시, NKE/QLD 그대로",
          "📒 [SGOV 장부 — NKE/QLD 적립과 따로]" in v2 and "보유 3주" in v2 and "분배금 누적 $0.90" in v2
          and dca_view(load()) == before and "🪙 SGOV 회차 적립" in pv, "")
    run(M.handle_callback(cb("sgov_dist"), c))
    run(M.handle_message({"chat": {"id": t_core.CHAT_ID}, "text": "2.5"}, c))
    check("8c. 분배금 입력 → SGOV 장부·대기 달러만 늘어남", abs(load()["sgov"]["ledger"]["distributions_usd"] - 3.4) < 1e-9
          and abs(load()["sgov"]["wait_usd"] - 2.5) < 1e-9 and dca_view(load()) == before, "")


def t9_cap_modes():
    # review: 3회 연속 건너뜀 → 재점검 대기, 그 뒤 회차는 판단 안 함
    sg = sgov_cfg(); bad = {"a_ok": True, "b_ok": False, "a_why": None, "b_why": "weekly_jump"}
    for i in range(3):
        dec = SG.sgov_decide(sg, bad); SG.apply_skip(sg, "b", f"2026-11-{13 + i * 14 if i == 0 else 13:02d}")
    check("9. review: 3회 연속 건너뜀 → 재점검 대기 (강제 매수 없음)",
          sg["review_hold"] is True and SG.sgov_precheck(dict(sg, next_due_date="2000-01-01", last_exec_date=""), TODAY_ET) == "review_hold", "")
    sg = sgov_cfg(skip_cap_mode="proceed3")
    acts = []
    for i in range(3):
        dec = SG.sgov_decide(sg, bad); acts.append(dec["action"])
        if dec["action"] != "buy": SG.apply_skip(sg, "b", TODAY_ET)
    check("9b. proceed3: (b) 2회 연속 건너뜀 → 3회째는 (a) 통과면 진행", acts == ["skip_b", "skip_b", "buy"], f"{acts}")
    sg = sgov_cfg(skip_cap_mode="proceed3", skip_streak_b=2)
    check("9c. proceed3 라도 (a) 실패면 매수 안 함, (a) 건너뜀은 횟수에 안 셈",
          SG.sgov_decide(sg, {"a_ok": False, "b_ok": False, "a_why": "rate_not_below_avg", "b_why": "weekly_jump"})["action"] == "skip_a"
          and (SG.apply_skip(sg, "a", TODAY_ET) or sg["skip_streak_b"] == 2), "")


def t10_sync_exclude_and_errors():
    d, p = fresh_env(); write_cfg(p, sgov_cfg()); set_hist(1400); set_snapshot(d, 1375.0)
    c = FakeClient(); c.all_holdings = [{"symbol": "SGOV", "qty": 3, "name": "SGOV"}]
    run(t_core.sync_holdings_from_meritz(c))
    check("10. 잔고 자동 등록에서 SGOV 제외", "SGOV" not in load()["stocks"], "")
    # SGOV 쪽 예외 → 적립 매수는 계속
    orig = SG.gate_inputs
    async def boom(*a, **k): raise RuntimeError("boom")
    SG.gate_inputs = boom
    run(one_pass(c)); cfg = load(); SG.gate_inputs = orig
    check("10b. SGOV 판단 중 예외 → NKE/QLD 매수는 그대로", cfg["stocks"]["NKE"]["last_exec_date"] == TODAY_ET
          and cfg["stocks"]["QLD"]["last_exec_date"] == TODAY_ET and cfg["sgov"]["ledger"]["qty"] == 0, "")
    # 적용환율 조회 실패 → 건너뜀 (매수 없음)
    d, p = fresh_env(); write_cfg(p, sgov_cfg()); set_hist(1400); c = FakeClient(rate=None)
    run(one_pass(c)); sg = load()["sgov"]
    check("10c. 적용환율 조회 실패 → 건너뜀 (매수 없음)", sg["ledger"]["qty"] == 0 and sg["skips_total"] == 1, f"why={sg['last_decision'].get('why')}")
    # 금액 하드코딩 없음: 기본값은 0
    check("10d. 코드 기본 금액 0 (금액은 설정에만)", SG.SGOV_DEFAULTS["tranche_usd"] == 0 and SG.SGOV_DEFAULTS["target_usd_total"] == 0
          and SG.SGOV_DEFAULTS["enabled"] is False and dca_engine.SAFE_DEFAULTS["dry_run"] is True, "")
    # 설정 문제(켜짐 + 금액 없음) → 판단 안 함
    d, p = fresh_env(); write_cfg(p, {"enabled": True}); c = FakeClient()
    run(one_pass(c)); sg = load()["sgov"]
    check("10e. 켜짐인데 금액·일정 없음 → 판단·주문 안 함", sg["ledger"]["qty"] == 0 and sg.get("skips_total", 0) == 0
          and c.calls["fx_applied_rate"] == 0, "")


def t11_history_basis():
    d, p = fresh_env(); set_hist(1400)
    closes = SG.parse_history_csv(history(1400))
    avg, n, why = SG.avg_months(closes, TODAY_KST, 36)
    j, basis, ref = SG.weekly_jump(1380.0, TODAY_KST, closes)
    check("11. 36개월 평균 계산·7일 기준(기록 없으면 공개 종가끼리)", why is None and abs(avg - 1400) < 1e-9 and n > 700 and basis == "history" and abs(j) < 1e-9,
          f"avg={avg} n={n} basis={basis}")
    a2, _, w2 = SG.avg_months(closes[-300:], TODAY_KST, 36)
    check("11b. 자료 기간 부족 → 평균 없음(건너뜀)", a2 is None and w2 in ("history_short", "history_start_late"), f"{w2}")


def t12_check_preview():
    d, p = fresh_env(); write_cfg(p, sgov_cfg()); set_hist(1400); set_snapshot(d, 1375.0); c = FakeClient(rate=1380.0)
    before = open(p).read()
    lines = run(SG.sgov_preview_lines(c, load(), TODAY_ET))
    check("12. --check SGOV 미리보기: 오늘 계획 표시, 저장·주문 없음",
          any("오늘 계획: SGOV 2주 매수" in l for l in lines) and open(p).read() == before and c.calls["market_order"] == 0,
          " / ".join(lines)[-160:])


for t in (t12_check_preview, t1_buy, t1b_buy_qty, t2_gate_a, t3_gate_b, t4_usd_short, t4c_reserve_math, t5_equiv, t6_dry_fx, t7_compile, t8_menu,
          t9_cap_modes, t10_sync_exclude_and_errors, t11_history_basis):
    try: t()
    except Exception as e:
        import traceback; traceback.print_exc(); check(t.__name__, False, f"예외 {e}")

n_ok = sum(1 for _, ok, _ in RESULTS if ok)
print(f"\nRESULT {n_ok}/{len(RESULTS)} PASS")
sys.exit(0 if n_ok == len(RESULTS) else 1)
