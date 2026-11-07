#!/usr/bin/env python3
# ==========================================================
# FILE: meritz_laoer/main.py   (MERITZ_LAOER v1.0.0)
# 메리츠 SOXL 무한매수(V14) 새 봇 — 실행·안전장치
# v1.0.0 (2026-11-08): 첫 버전
#   - 전략: hantu_laoer/strategy_v14.py 를 그대로 복사해 씀 (분할 매수 · 평단 익절 후 처음부터 다시 시작)
#   - 주문: 메리츠 즉시주문 (LOC·MOC·지정가). 미국 동부 order_time_et~order_deadline_et 에 하루 1번
#   - 체결 반영: sync_time_et 이후 주문번호로 체결 내역을 읽어 봇 장부(원금·수량)를 갱신
#   - 안전장치: 기본 enabled=false · dry_run(모의) · 입고 확인 · 토스 스나이퍼 정지 확인 · 키 지문 일치
#     · P/VR6 키·다른 봇 텔레그램 토큰 재사용 금지 · 장부≠잔고면 정지(halt) · 하루 1회 표시 파일
# 사용:
#   python3 main.py --fingerprint      키 지문만 출력 (expected_key_fp 에 넣을 값)
#   python3 main.py --check            주문 없이 점검 + 오늘 주문 계획 미리보기 (enabled 와 무관)
#   python3 main.py --inject-start     입고 확인 뒤 장부 시작 (settings.start 로 원금·수량 덮어쓰기)
#   python3 main.py --clear-halt       정지 표시 해제 (원인 확인 후)
#   python3 main.py                    상시 실행 (서비스용)
# ==========================================================
import argparse
import contextlib
import datetime
import json
import logging
import os
import shutil
import sys
import time
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import config as cfgmod                      # noqa: E402
from config import ConfigManager, load_settings, validate_settings   # noqa: E402
from meritz_api import MeritzApi, MeritzError, WarnNeeded, key_fingerprint   # noqa: E402
from notifier import Notifier, _read_token, token_fp   # noqa: E402

BOT_VERSION = "v1.0.0"
EST = ZoneInfo("America/New_York")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def now_et():
    return datetime.datetime.now(EST)


def _hm(s, default):
    try:
        h, m = str(s).split(":")
        return datetime.time(int(h), int(m))
    except (ValueError, AttributeError):
        return default


@contextlib.contextmanager
def in_dir(path):
    old = os.getcwd()
    os.makedirs(path, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def sandbox_dir(state_dir):
    """모의·미리보기용: 실제 장부(data/)를 복사한 임시 폴더. 실제 장부는 바뀌지 않음"""
    sb = os.path.join(state_dir, "_sandbox")
    shutil.rmtree(sb, ignore_errors=True)
    src = os.path.join(state_dir, "data")
    if os.path.isdir(src):
        shutil.copytree(src, os.path.join(sb, "data"), ignore=shutil.ignore_patterns("meritz_token.json"))
    else:
        os.makedirs(os.path.join(sb, "data"), exist_ok=True)
    return sb


# ---------------------------------------------------------------- 점검 (주문 없음)
def check_identity(s):
    """키·토큰 점검 → (문제 목록, 키 지문)"""
    bad, fp = [], ""
    kf = s.get("key_file")
    if not kf or not os.path.isfile(kf):
        bad.append("새 메리츠 키 파일 없음 (key_file)")
    else:
        try:
            fp = key_fingerprint(kf)
        except Exception:
            bad.append("키 파일 형식 오류 (app_key/app_secret)")
        for other in s.get("forbid_key_files") or []:
            if os.path.realpath(other) == os.path.realpath(kf):
                bad.append("key_file 이 P/VR6 키 파일과 같은 경로 — 재사용 금지")
            elif fp and os.path.isfile(other):
                try:
                    if key_fingerprint(other) == fp:
                        bad.append("새 키가 P/VR6 키와 같음 — 재사용 금지")
                except Exception:
                    pass
        exp = str(s.get("expected_key_fp") or "").strip()
        if not exp:
            bad.append("expected_key_fp 비어 있음 (--fingerprint 값 입력 필요)")
        elif fp and fp != exp:
            bad.append("키 지문 불일치 — 3번 계좌 키가 아님 (정지)")
    tf = s.get("telegram_file")
    tok = _read_token(tf) if tf else ""
    if not tok:
        bad.append("새 텔레그램 토큰 파일 없음 (telegram_file)")
    else:
        for other in s.get("forbid_telegram_files") or []:
            if os.path.realpath(other) == os.path.realpath(tf) or token_fp(_read_token(other)) == token_fp(tok):
                bad.append("텔레그램 토큰이 다른 봇과 같음 — 재사용 금지")
    return bad, fp


def gate_problems(s, cfg, live):
    """실주문 전 통과해야 하는 조건 → 문제 목록"""
    bad = validate_settings(s)
    bad += check_identity(s)[0]
    if not s.get("transfer_confirmed"):
        bad.append("입고 확인 전 (transfer_confirmed=false)")
    if not s.get("toss_sniper_stopped_confirmed"):
        bad.append("토스 스나이퍼 정지·미체결 0건 확인 전 (toss_sniper_stopped_confirmed=false)")
    if cfg.get_halt():
        bad.append(f"정지 상태: {cfg.get_halt().get('reason')}")
    if live and not cfg.get_position():
        bad.append("장부 시작 전 (--inject-start 필요)")
    return bad


def market_inputs(s, api):
    sym, mk = s["symbol"], s["price_market"]
    p = api.price(sym, mk)
    today = now_et().strftime("%Y%m%d")
    closes = [c for d, c in api.daily_closes(sym, mk) if d < today][:5]    # 당일 미확정 봉 제외 (hantu get_5day_ma 와 같은 기준)
    ma5 = sum(closes) / 5 if len(closes) == 5 else 0.0
    return p["price"], p["prev_close"], ma5


def build_plan(s, cfg, prev_close, ma5, cash, qty, avg, snapshot):
    from strategy_v14 import V14Strategy
    st = V14Strategy(cfg)
    # 현재가 자리에 전일 종가를 넣음: hantu 는 16:05 종가 시점에 다음 날 계획을 박제하므로 같은 입력이 됨
    return st.get_plan(ticker=s["symbol"], current_price=prev_close, avg_price=avg, qty=qty, prev_close=prev_close,
                       ma_5day=ma5, market_type="REG", available_cash=cash, is_snapshot_mode=snapshot)


def fit_orders(plan, cash, sellable, ledger_qty):
    """달러·매도가능 수량에 맞춰 주문 정리 → (주문 목록, 메모 목록)"""
    core, bonus, notes = list(plan.get("core_orders") or []), list(plan.get("bonus_orders") or []), []
    cost = lambda lst: sum(int(o["qty"]) * float(o["price"]) for o in lst if o.get("side") == "BUY" and o.get("type") != "MOC")
    if cost(core) > cash:
        core = [o for o in core if o.get("side") != "BUY"]
        bonus = []
        notes.append(f"달러 부족 ${cash:,.2f} — 오늘 매수 생략")
    elif cost(core) + cost(bonus) > cash:
        bonus = []
        notes.append("달러가 줍줍까지는 부족 — 줍줍 생략")
    orders = core + bonus
    sell_q = sum(int(o["qty"]) for o in orders if o.get("side") == "SELL")
    if sell_q > min(sellable, ledger_qty):
        return [], notes + [f"매도 {sell_q}주 > 매도가능 {sellable}/장부 {ledger_qty} — 주문 안 함"]
    return orders, notes


def fmt_orders(orders):
    return "\n".join(f"- {o['side']} {o['type']} {o['qty']}주 @ {'시장가' if o['type'] == 'MOC' else '$%.2f' % float(o['price'])} {o.get('desc', '')}"
                     for o in orders) or "- (주문 없음)"


def plan_head(plan, s):
    return (f"분할 {int(float(s['split_count'] or 0))} · T {plan.get('t_val', 0):.2f} · 1회 ${plan.get('one_portion', 0):,.2f} · "
            f"{plan.get('process_status', '')}\n별값 ${plan.get('star_price', 0):.2f} · 목표 ${plan.get('target_price', 0):.2f}")


# ---------------------------------------------------------------- 하루 주문
def run_order_day(s, api, note, live):
    state = s["state_dir"]
    d = now_et().strftime("%Y-%m-%d")
    mark = os.path.join(state, "data", f"{'orders' if live else 'dry_orders'}_{d}.json")
    if os.path.exists(mark):
        return "이미 함"
    cfg = ConfigManager(s)
    if live:
        bad = gate_problems(s, cfg, live=True)
        if bad:
            note.send("⛔ 오늘 주문 안 함\n" + "\n".join("- " + b for b in bad))
            cfg._save_json(mark, {"skipped": bad})
            return "차단"
    status = api.us_market_status()
    if status != "004":
        cfg._save_json(mark, {"skipped": f"장운영 코드 {status} (휴장 또는 정규장 아님)"})
        note.send(f"오늘은 정규장 아님 (코드 {status}) — 주문 없음")
        return "휴장"
    hold, sellable, exch_vid = api.holding(s["symbol"])
    exch = str(s.get("exch_id") or exch_vid or "")
    pos = cfg.get_position()
    if not pos and not live:     # 모의: 장부 시작 전이면 설정 start 로 가정
        st = s["start"]
        pos = {"qty": int(float(st.get("qty") or 0)), "principal": float(st.get("principal_usd") or 0)}
    qty = int(pos["qty"])
    avg = cfg.avg_price(pos)
    warn = []
    if hold != qty:
        warn.append(f"잔고 {hold}주 ≠ 장부 {qty}주")
        if live:
            cfg.halt(warn[-1])
            note.send("⛔ 정지: " + warn[-1] + "\n확인 후 --clear-halt")
            cfg._save_json(mark, {"skipped": warn})
            return "정지"
    if live and api.open_orders_today(s["symbol"]):
        note.send("⛔ 이 계좌에 SOXL 미체결 주문이 이미 있음 — 오늘 주문 안 함 (수동 확인)")
        cfg._save_json(mark, {"skipped": "기존 미체결 있음"})
        return "미체결"
    if live and not exch:
        note.send("⛔ 거래소 번호 모름 (exch_id 설정 필요)")
        cfg._save_json(mark, {"skipped": "exch_id 없음"})
        return "거래소"
    _, prev_close, ma5 = market_inputs(s, api)
    cash = api.usd_cash()
    if live:
        cfg.increment_reverse_day(s["symbol"])
        plan = build_plan(s, cfg, prev_close, ma5, cash, qty, avg, snapshot=True)
    else:
        with in_dir(sandbox_dir(state)):
            c2 = ConfigManager(s)
            c2.increment_reverse_day(s["symbol"])
            plan = build_plan(s, c2, prev_close, ma5, cash, qty, avg, snapshot=True)
    orders, notes = fit_orders(plan, cash, sellable if live else qty, qty)
    placed, errors = [], []
    if live:
        for o in orders:
            try:
                r = api.order(o["side"], s["symbol"], exch, o["type"], o["qty"], o["price"])
                placed.append(dict(o, no=r["no"]))
            except WarnNeeded as e:
                errors.append(f"{o.get('desc')}: 증권사 경고(자동 확인 안 함) {e}")
            except MeritzError as e:
                errors.append(f"{o.get('desc')}: {e}")
            time.sleep(0.3)
    cfg._save_json(mark, {"date": d, "is_reverse": bool(plan.get("is_reverse")), "prev_close": prev_close,
                          "qty": qty, "avg": avg, "cash": round(cash, 2), "orders": placed if live else orders,
                          "errors": errors, "synced": False if live else True})
    note.send(f"{d} 주문 {'접수' if live else '계획'} · 보유 {qty}주 평단 ${avg:.2f}\n{plan_head(plan, s)}\n"
              + fmt_orders(placed if live else orders)
              + ("\n" + "\n".join("ℹ️ " + n for n in notes + warn) if notes or warn else "")
              + ("\n⚠️ 실패\n" + "\n".join("- " + e for e in errors) if errors else ""))
    return "완료"


# ---------------------------------------------------------------- 체결 반영
def run_sync(s, api, note, mark_path):
    cfg = ConfigManager(s)
    m = cfg._load_json(mark_path, {})
    if m.get("synced", True) or not m.get("orders"):
        if m and not m.get("synced", True):
            m["synced"] = True
            cfg._save_json(mark_path, m)
        return "없음"
    d = m["date"]
    dt = datetime.date.fromisoformat(d)
    fills = api.fills((dt - datetime.timedelta(days=1)).strftime("%Y%m%d"), (dt + datetime.timedelta(days=2)).strftime("%Y%m%d"))
    lines, done = [], None
    for o in m["orders"]:
        f = fills.get(str(o.get("no")))
        if not f:
            continue
        side, q, amt = f
        px = amt / q if q else 0.0
        pos, closed = cfg.apply_fill(side, q, px, d, m.get("is_reverse"), f"{d}_{o['no']}")
        lines.append(f"- {side} {q}주 @ ${px:.2f} ({o.get('desc', '')})")
        done = closed or done
    hold, _, _ = api.holding(s["symbol"])
    pos = cfg.get_position()
    m["synced"] = True
    cfg._save_json(mark_path, m)
    msg = f"{d} 체결 반영\n" + ("\n".join(lines) if lines else "- 체결 없음") + f"\n장부 {pos['qty']}주 평단 ${cfg.avg_price(pos):.2f}"
    if done:
        msg += f"\n🎉 사이클 종료: 이익 ${done['profit']:,.2f} ({done['yield']:.2f}%) · 시드 +${done['added_seed']:,} → 새출발"
    if hold != pos["qty"]:
        cfg.halt(f"체결 반영 뒤 잔고 {hold}주 ≠ 장부 {pos['qty']}주")
        msg += f"\n⛔ 정지: 잔고 {hold}주 ≠ 장부 {pos['qty']}주 (확인 후 --clear-halt)"
    note.send(msg)
    return "완료"


def pending_syncs(state):
    dd = os.path.join(state, "data")
    try:
        names = sorted(n for n in os.listdir(dd) if n.startswith("orders_") and n.endswith(".json"))
    except OSError:
        return []
    return [os.path.join(dd, n) for n in names]


# ---------------------------------------------------------------- 상시 실행
def loop():
    last_idle = 0
    while True:
        try:
            s = load_settings()
            state = s["state_dir"]
            os.makedirs(os.path.join(state, "data"), exist_ok=True)
            os.chdir(state)
            if not s.get("enabled"):
                if time.time() - last_idle > 3600:
                    logging.info("enabled=false — 대기 (주문 없음)")
                    last_idle = time.time()
                time.sleep(60)
                continue
            live = not s.get("dry_run", True)
            if not os.path.isfile(str(s.get("key_file") or "")):
                if time.time() - last_idle > 3600:
                    logging.warning("새 메리츠 키 파일 없음 — 대기 (주문 없음)")
                    last_idle = time.time()
                time.sleep(60)
                continue
            note = Notifier(s["telegram_file"], dry_run=not live)
            n = now_et()
            api = None
            if n.weekday() < 5 and _hm(s["order_time_et"], datetime.time(10, 5)) <= n.time() <= _hm(s["order_deadline_et"], datetime.time(15, 40)):
                api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
                run_order_day(s, api, note, live)
            if live:
                today = n.strftime("%Y-%m-%d")
                for mp in pending_syncs(state):
                    md = os.path.basename(mp)[7:17]
                    if md < today or n.time() >= _hm(s["sync_time_et"], datetime.time(16, 10)):
                        m = ConfigManager(s)._load_json(mp, {})
                        if m.get("orders") and not m.get("synced", True):
                            api = api or MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
                            run_sync(s, api, note, mp)
        except Exception as e:
            logging.exception(f"반복 중 오류: {type(e).__name__}")
            try:
                Notifier(load_settings()["telegram_file"]).send(f"⚠️ 오류 {type(e).__name__}: {str(e)[:200]}")
            except Exception:
                pass
            time.sleep(120)
        time.sleep(30)


def cmd_check(s):
    print(f"MERITZ_LAOER {BOT_VERSION} 점검 (주문 없음)")
    bad = validate_settings(s)
    idb, fp = check_identity(s)
    print(f"- enabled={s.get('enabled')} dry_run={s.get('dry_run')} transfer_confirmed={s.get('transfer_confirmed')} "
          f"toss_sniper_stopped_confirmed={s.get('toss_sniper_stopped_confirmed')}")
    print(f"- 키 지문: {fp or '-'} (기대값 {'있음' if s.get('expected_key_fp') else '없음'})")
    for b in bad + idb:
        print("  ✗", b)
    state = s["state_dir"]
    os.makedirs(os.path.join(state, "data"), exist_ok=True)
    with in_dir(state):
        cfg = ConfigManager(s)
        pos = cfg.get_position()
        print(f"- 장부: {('%d주 원금 $%.2f 평단 $%.4f' % (pos['qty'], pos['principal'], cfg.avg_price(pos))) if pos else '시작 전'}")
        print(f"- 정지 표시: {cfg.get_halt() or '없음'}")
    if bad or "새 메리츠 키 파일 없음 (key_file)" in idb or "키 파일 형식 오류 (app_key/app_secret)" in idb:
        print("→ 설정을 채운 뒤 다시 --check")
        return 1
    api = MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
    hold, sellable, exch = api.holding(s["symbol"])
    price, prev_close, ma5 = market_inputs(s, api)
    cash = api.usd_cash()
    print(f"- 메리츠 잔고 {s['symbol']} {hold}주 (매도가능 {sellable}) 거래소번호 {exch or '-'} · USD 예수금 ${cash:,.2f}")
    print(f"- 현재가 ${price:.2f} 전일종가 ${prev_close:.2f} 5일선 ${ma5:.2f} · 장운영 {api.us_market_status()}")
    st = s["start"]
    q = int(pos["qty"]) if pos else int(float(st["qty"]))
    principal = float(pos["principal"]) if pos else float(st["principal_usd"])
    avg = round(principal / q, 4) if q else 0.0
    with in_dir(sandbox_dir(state)):
        plan = build_plan(s, ConfigManager(s), prev_close, ma5, cash, q, avg, snapshot=True)
    orders, notes = fit_orders(plan, cash, sellable, q)
    print("- 오늘 계획 (미리보기·주문 안 냄):\n  " + plan_head(plan, s).replace("\n", "\n  "))
    print("  " + fmt_orders(orders).replace("\n", "\n  "))
    for n in notes:
        print("  ℹ️", n)
    if hold != q:
        print(f"  ⚠️ 잔고 {hold}주 ≠ 장부/시작 {q}주 → 입고 전이거나 다른 계좌")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="메리츠 SOXL 무한매수 봇")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fingerprint", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--inject-start", action="store_true")
    g.add_argument("--clear-halt", action="store_true")
    ap.add_argument("--overwrite", action="store_true", help="--inject-start 때 기존 장부 덮어쓰기")
    a = ap.parse_args(argv)
    s = load_settings()
    if a.fingerprint:
        print(key_fingerprint(s["key_file"]))
        return 0
    if a.check:
        return cmd_check(s)
    state = s["state_dir"]
    os.makedirs(os.path.join(state, "data"), exist_ok=True)
    if a.clear_halt:
        with in_dir(state):
            ConfigManager(s).clear_halt()
        print("정지 표시 해제")
        return 0
    if a.inject_start:
        bad = validate_settings(s) + check_identity(s)[0]
        if not s.get("transfer_confirmed"):
            bad.append("transfer_confirmed=false (입고 확인 먼저)")
        if bad:
            print("✗ 주입 안 함:\n" + "\n".join("- " + b for b in bad))
            return 1
        api = MeritzApi(s["key_file"], os.path.join(state, "data", "meritz_token.json"))
        hold, _, _ = api.holding(s["symbol"])
        want = int(float(s["start"]["qty"]))
        if hold != want:
            print(f"✗ 메리츠 잔고 {hold}주 ≠ 시작 수량 {want}주 — 입고 미완료 또는 다른 계좌")
            return 1
        with in_dir(state):
            cfg = ConfigManager(s)
            pos, wrote = cfg.inject_start(overwrite=a.overwrite)
            print(("장부 시작: " if wrote else "이미 장부 있음(덮어쓰려면 --overwrite): ")
                  + f"{pos['qty']}주 원금 ${pos['principal']:.2f} 평단 ${cfg.avg_price(pos):.4f}")
        return 0
    loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
