# ==========================================================
# FILE: meritz_laoer/sniper_mode.py   (MERITZ_LAOER v2.2.20)
# v2.2.20 (2026-11-21, 판 22 듀얼 모드): 새 파일 — 스나이퍼 모드 계산부. 순수 계산 + 상태 파일(data/sniper_state.json) 읽기·쓰기 도우미만 (네트워크·시계 없음, 시각은 호출한 쪽이 넘김).
#   toss_sniper(참조, 고치지 않음)에서 가져온 규칙:
#   - 채우기(층 사기): 직전 익절가(기준가) 대비 눌림목 또는 +1.0% 돌파 (quant_engine.evaluate_l2_only_hybrid_reentry_signal 규칙 — 돌파는 RSI(14) <= 50 필터·15:30~16:00 ET 돌파 차단·기준가의 2층 단가 상한 가드 Case 73).
#     눌림 깊이는 보유 층 수에 따라 1-4층 -1.0% · 5-8층 -2.0% · 9-10층 -3.5% (quant_engine.get_golden8_prog_thresholds).
#   - 비우기(층 팔기): 층 평단 + 익절% 에 닿으면 그 층 전량 (quant_engine.evaluate_multi_grid_sell_targets 의 1층 +1.5% · 상단층 +1.0% 개별 판정만. 2~7층 통합이평 졸업(WMA) 판정은 판 22 지시에 없어 안 가져옴).
#   빼거나 바꾼 것(판 22 지시): 바벨·암살자·서브 그리드·지하층·복리(자산 % 회차 크기)·24시간 매도 창·1.5초 간격. 회차 크기는 자산 % 가 아니라 층 시드(tower_floor_usd, 기본 $15,000).
#   층은 탑쌓기와 같은 층(tower_state.json)을 공유. 스나이퍼의 '1층' = 가장 아래 활성 층(평단이 가장 낮은 층 = 가장 최근에 채운 공격 층), 나머지는 상단층.
#   RSI(14): 메리츠 분봉 API 는 근거 파일에 없어 미확인 → 봇이 시세를 읽을 때마다 1분 단위로 모은 종가(series)로 Wilder RSI(14)를 계산. 15개가 안 모이면 RSI 를 모른다고 보고 돌파는 막음(눌림은 RSI 무관).
# 상태 파일: {"version": 1, "anchor": 기준가, "anchor_kind": "exit"|"buy"|"avg"|"", "anchor_at": ISO, "last_order_ts": 에포크초, "buy_block_until": 에포크초(매수 거절 뒤 쉬는 시각), "series": [[분 에포크, 종가], ...]}
# ==========================================================
import copy
import datetime
import math

import tower_strategy as TW
from tower_strategy import ceil2

MODE_SNIPER, MODE_TOWER = "sniper", "tower"
MODE_KO = {MODE_SNIPER: "스나이퍼", MODE_TOWER: "탑쌓기"}

TP_L1_DEFAULT = 1.5            # 스나이퍼 1층(공격 층) 익절 % — 설정 sniper_tp_l1_pct (지금 스나이퍼 세팅 그대로)
TP_UPPER_DEFAULT = 1.0         # 상단층 익절 % — 설정 sniper_tp_upper_pct
PULLBACK_TIERS = ((4, -1.00), (8, -2.00), (10, -3.50))      # (보유 층 수 이하, 눌림 %) — 그 위는 PULLBACK_DEEP (참조 get_golden8_prog_thresholds)
PULLBACK_DEEP = -5.50
BREAKOUT_RISE_PCT = 1.00       # 돌파 % (참조 REENTRY_BREAKOUT_RISE_PCT)
BREAKOUT_MAX_RSI = 50.0        # 돌파 때 RSI(14) 상한 (참조 REENTRY_BREAKOUT_MAX_RSI_50)
RSI_PERIOD = 14
LATE_CUTOFF = datetime.time(15, 30)      # 15:30~16:00 ET 돌파 차단 (참조 NEW_CYCLE_BUY_CUTOFF_HM 1530, Case 84)
BUY_CHECK_SEC = 60             # 재장전 감시 주기 (판 22: 60초)
ORDER_SHIELD_SEC = 60          # 주문 낸 뒤 이 시간 동안 새 매수 안 함 (참조 매수·매도 후 60초 타임쉴드)
SERIES_KEEP = 120              # 분 단위 종가 보관 개수
SERIES_MAX_AGE_SEC = 90 * 60   # RSI 에 쓰는 종가는 이보다 오래되면 버림 (봇이 오래 꺼져 있었던 구간을 이어 붙이지 않게)
SNIPER_FILE = "data/sniper_state.json"


def _f(v):
    return TW._f(v)


# ---------------------------------------------------------------- 설정
def get_mode(s):
    """trading_mode → 'sniper' | 'tower'. 없거나 이상한 값이면 'tower' (예전 동작 그대로)"""
    v = str((s or {}).get("trading_mode") or MODE_TOWER).strip().lower()
    return MODE_SNIPER if v == MODE_SNIPER else MODE_TOWER


def mode_ko(s):
    return MODE_KO[get_mode(s)]


def tp_pcts(s):
    """(1층 익절 %, 상단층 익절 %). 설정에 없거나 0 이하면 기본값 (1.5, 1.0)"""
    a, b = _f((s or {}).get("sniper_tp_l1_pct")), _f((s or {}).get("sniper_tp_upper_pct"))
    return (a if a > 0 else TP_L1_DEFAULT), (b if b > 0 else TP_UPPER_DEFAULT)


# ---------------------------------------------------------------- 층 매핑
def active_floors(st):
    """수량이 있는 층, 위(탑쌓기 번호 1 = 평단 가장 높은 층)부터"""
    return [f for f in TW.top_down(st if isinstance(st, dict) else {}) if int(_f(f.get("qty"))) > 0]


def attack_id(st):
    """스나이퍼 '1층'(공격 층) = 활성 층 중 평단이 가장 낮은 층 (같으면 번호가 큰 층). 활성 층이 없으면 None"""
    fl = active_floors(st)
    if not fl:
        return None
    return int(_f(min(fl, key=lambda f: (TW.floor_avg(f), -int(_f(f.get("id"))))).get("id")))


# ---------------------------------------------------------------- 비우기 (익절)
def sniper_numbers(st):
    """{탑쌓기 층 id: 스나이퍼 층 번호} — 번호는 평단 낮은 층부터 1, 2, 3 … (1 = 공격 층). 표시·알림 글자용 (주문·장부는 탑쌓기 id 그대로)"""
    order = sorted(active_floors(st), key=lambda f: (TW.floor_avg(f), -int(_f(f.get("id")))))
    return {int(_f(f.get("id"))): i + 1 for i, f in enumerate(order)}


def sell_rows(st, s, price):
    """층마다 스나이퍼 익절 행: id(탑쌓기 층 번호)·no(스나이퍼 층 번호 — 평단 낮은 층이 1)·qty·avg·pct(그 층 익절 %)·target(올림 2자리)·reached·gain_pct(현재가 대비 평단 %)·role(L1|upper)"""
    tp1, tpu = tp_pcts(s)
    aid = attack_id(st)
    nos = sniper_numbers(st)
    px = _f(price)
    rows = []
    for f in active_floors(st):
        fid, fa = int(_f(f.get("id"))), TW.floor_avg(f)
        role = "L1" if fid == aid else "upper"
        pct = tp1 if role == "L1" else tpu
        tg = ceil2(fa * (1 + pct / 100.0))
        rows.append({"id": fid, "no": nos.get(fid, fid), "qty": int(_f(f.get("qty"))), "avg": fa, "pct": pct, "target": tg, "role": role,
                     "reached": bool(px > 0 and px >= tg), "gain_pct": (round((px / fa - 1) * 100, 2) if px > 0 and fa > 0 else None),
                     "complete": TW.is_complete(f), "cost": round(_f(f.get("cost")), 2), "tgt_usd": _f(f.get("target") or TW.FLOOR_USD)})
    return rows


def plan_sells(s, st, price, sellable, skip_ids=(), otype="LIMIT"):
    """목표에 닿은 층마다 그 층 전량(100%) 지정가 매도 주문 → (주문 목록, 알림 글자 목록). skip_ids = 이미 이 층 주문이 나가 있거나 오늘 거절된 층.
    매도가능 수량(sellable)이 모자라면 아래층(번호 큰 층)부터 우선하고 나머지는 보류. 계산만 함 (상태 안 바꿈)"""
    rows = sell_rows(st, s, price)
    notes, orders, taken = [], [], 0
    cap = max(0, int(_f(sellable)))
    skip = {int(x) for x in skip_ids}
    for r in sorted((r for r in rows if r["reached"]), key=lambda r: -r["id"]):
        if r["id"] in skip:
            continue
        if taken + r["qty"] > cap:
            notes.append(f"매도 {r['no']}층 {r['qty']}주 > 매도가능 {max(cap - taken, 0)}주 — 보류")
            continue
        taken += r["qty"]
        orders.append({"side": "SELL", "type": otype, "qty": r["qty"], "price": r["target"], "kind": "sell", "mode": MODE_SNIPER, "level": None,
                       "floor_id": r["id"], "floor_avg": r["avg"], "reached": True,
                       "desc": f"스나이퍼 {r['no']}층 평단 ${r['avg']:.2f} +{r['pct']:g}% 전량 매도"})
    return orders, notes


# ---------------------------------------------------------------- 채우기 (층 사기)
def drop_pct(n_layers):
    """보유 층 수에 따른 눌림 % (음수). 참조 get_golden8_prog_thresholds: 1-4층 -1.0 · 5-8층 -2.0 · 9-10층 -3.5 · 그 위 -5.5"""
    lots = max(1, int(n_layers))
    for hi, pct in PULLBACK_TIERS:
        if lots <= hi:
            return pct
    return PULLBACK_DEEP


def rsi14(closes):
    """Wilder RSI(14) — 종가 15개 이상 필요 (없으면 None). 오른쪽이 최신"""
    c = [float(x) for x in closes if _f(x) > 0]
    if len(c) < RSI_PERIOD + 1:
        return None
    gains = [max(c[i] - c[i - 1], 0.0) for i in range(1, len(c))]
    losses = [max(c[i - 1] - c[i], 0.0) for i in range(1, len(c))]
    ag = sum(gains[:RSI_PERIOD]) / RSI_PERIOD
    al = sum(losses[:RSI_PERIOD]) / RSI_PERIOD
    for g, l in zip(gains[RSI_PERIOD:], losses[RSI_PERIOD:]):
        ag = (ag * (RSI_PERIOD - 1) + g) / RSI_PERIOD
        al = (al * (RSI_PERIOD - 1) + l) / RSI_PERIOD
    if al <= 0:
        return 100.0 if ag > 0 else 50.0
    return round(100.0 - 100.0 / (1.0 + ag / al), 2)


def series_add(state, price, now_ts):
    """시세를 1분 단위 종가로 모음: 같은 분이면 마지막 값으로 덮어쓰고, 새 분이면 추가"""
    px = _f(price)
    if px <= 0:
        return state
    minute = int(now_ts // 60)
    ser = state.setdefault("series", [])
    if ser and int(ser[-1][0]) == minute:
        ser[-1][1] = round(px, 4)
    else:
        ser.append([minute, round(px, 4)])
    del ser[:-SERIES_KEEP]
    return state


def rsi_from_state(state, now_ts):
    """(RSI, 쓴 종가 개수). 너무 오래된 종가는 버림. 15개 미만이면 (None, 개수)"""
    ser = [x for x in (state or {}).get("series") or [] if isinstance(x, (list, tuple)) and len(x) == 2 and now_ts - int(x[0]) * 60 <= SERIES_MAX_AGE_SEC]
    return rsi14([x[1] for x in ser]), len(ser)


def is_late_cutoff(now_et):
    """15:30 ~ 16:00 ET 인가 (돌파 차단 구간)"""
    t = now_et.time()
    return LATE_CUTOFF <= t < datetime.time(16, 0)


def anchor_info(st, state):
    """(기준가, 종류). 저장된 직전 익절/매수가가 있으면 그것, 없으면 가장 아래 활성 층 평단('avg' — 참조에서 직전 익절가가 없을 때 2층 단가로 대신하던 것). 둘 다 없으면 (0.0, '')"""
    a = _f((state or {}).get("anchor"))
    if a > 0:
        return a, str((state or {}).get("anchor_kind") or "exit")
    fl = active_floors(st)
    if fl:
        return min(TW.floor_avg(f) for f in fl), "avg"
    return 0.0, ""


def buy_signal(price, anchor, kind, cap_price, n_layers, rsi, late_cutoff):
    """재장전 신호 판정 (참조 evaluate_l2_only_hybrid_reentry_signal 규칙, 순수 계산) → dict(should_buy, signal_type, pullback_price, breakout_price, ...).
    signal_type: NO_PRICE · NO_ANCHOR · HOLD_PREVENT_INVERSION(현재가 > 평단 가장 낮은 층 평단 = Case 73 상한) · PULLBACK_RELOAD · BREAKOUT_RELOAD ·
    HOLD_LATE_SESSION_BREAKOUT_CUTOFF · HOLD_BREAKOUT_RSI_OVER_50 · HOLD_BREAKOUT_RSI_UNKNOWN · HOLD_WAIT_GATE.
    돌파는 기준가가 익절가('exit')이거나 평단 대신 쓴 값('avg')일 때만 (직전 매수가 기준이면 눌림만 — 추가 매수는 더 눌려야 함)"""
    lp, anc, cap = _f(price), _f(anchor), _f(cap_price)
    drop = drop_pct(n_layers)
    pull = round(anc * (1.0 + drop / 100.0), 2) if anc > 0 else 0.0
    brk = round(anc * (1.0 + BREAKOUT_RISE_PCT / 100.0), 2) if anc > 0 and kind in ("exit", "avg") else 0.0
    base = {"should_buy": False, "signal_type": "", "anchor": round(anc, 4), "anchor_kind": kind, "drop_pct": drop, "pullback_price": pull,
            "breakout_price": brk, "cap_price": round(cap, 4), "rsi": rsi, "chg_pct": (round((lp / anc - 1) * 100, 2) if lp > 0 and anc > 0 else 0.0)}
    if lp <= 0:
        return dict(base, signal_type="NO_PRICE")
    if anc <= 0:
        return dict(base, signal_type="NO_ANCHOR")
    if cap > 0 and lp > cap + 1e-6:
        return dict(base, signal_type="HOLD_PREVENT_INVERSION")
    if lp <= pull + 1e-9:
        return dict(base, should_buy=True, signal_type="PULLBACK_RELOAD")
    if brk > 0 and lp >= brk - 1e-9:
        if late_cutoff:
            return dict(base, signal_type="HOLD_LATE_SESSION_BREAKOUT_CUTOFF")
        if rsi is None:
            return dict(base, signal_type="HOLD_BREAKOUT_RSI_UNKNOWN")
        if rsi > BREAKOUT_MAX_RSI + 1e-6:
            return dict(base, signal_type="HOLD_BREAKOUT_RSI_OVER_50")
        return dict(base, should_buy=True, signal_type="BREAKOUT_RELOAD")
    return dict(base, signal_type="HOLD_WAIT_GATE")


SIGNAL_KO = {"NO_PRICE": "시세 없음", "NO_ANCHOR": "기준가 없음 (직전 익절가 대기)", "HOLD_PREVENT_INVERSION": "상한 가드 (가장 아래 층 평단 초과)",
             "PULLBACK_RELOAD": "눌림 재장전", "BREAKOUT_RELOAD": "돌파 재장전", "HOLD_LATE_SESSION_BREAKOUT_CUTOFF": "돌파 차단 (15:30~16:00)",
             "HOLD_BREAKOUT_RSI_OVER_50": "돌파 보류 (RSI 50 초과)", "HOLD_BREAKOUT_RSI_UNKNOWN": "돌파 보류 (RSI 모으는 중)", "HOLD_WAIT_GATE": "대기 (눌림·돌파 전)"}


def plan_buy(s, st, price, state, rsi, usd_cash, now_et, otype="LIMIT"):
    """오늘 재장전 매수 계획 → {"order": 주문 또는 None, "notes", "signal", "target"}. 상태·장부를 바꾸지 않음.
    사는 금액 = 그 층의 남은 시드 (미완성 층이 있으면 위에서부터 첫 미완성 층의 (목표 − 원가), 없으면 새 층 = min(층 시드, 총 한도 남은 몫)). 최대 층 시드(기본 $15,000).
    주식수는 정수 내림(시드를 안 넘김), 달러 예수금이 모자라면 살 수 있는 만큼만. 주문 가격 = 현재가 (지정가)"""
    fu, nfl, _gap = TW.params(s)
    fl = active_floors(st)
    n = len(fl)
    px = _f(price)
    anchor, kind = anchor_info(st, state)
    cap = min((TW.floor_avg(f) for f in fl), default=0.0)
    sig = buy_signal(px, anchor, kind, cap, n, rsi, is_late_cutoff(now_et))
    out = {"order": None, "notes": [], "signal": sig, "target": None}
    if not sig["should_buy"]:
        return out
    _q, principal = TW.totals(st)
    inc = next((f for f in fl if not TW.is_complete(f)), None)
    if inc is not None:
        fid, amount, nf = int(_f(inc.get("id"))), max(0.0, _f(inc.get("target") or fu) - _f(inc.get("cost"))), None
        label = f"{fid}층 남은 시드"
    else:
        room = fu * nfl - principal
        if n >= nfl or room < TW.TOL_USD:
            out["notes"].append(f"새 층 없음 — 총 한도 ${fu * nfl:,.0f} (보유 원가 ${principal:,.0f}, {n}/{nfl}층)")
            return out
        nid = max(int(_f(st.get("next_id"))), max((int(_f(f.get("id"))) for f in TW.top_down(st)), default=0) + 1)
        amount = min(fu, room)
        fid, nf, label = nid, {"id": nid, "target": round(amount, 2)}, f"새 {nid}층 시드"
    q = int(math.floor(amount / px + 1e-9)) if px > 0 else 0
    cash = _f(usd_cash)
    if q * px > cash + 1e-9:
        q = int(math.floor(cash / px + 1e-9)) if cash > 0 else 0
        out["notes"].append(f"달러 예수금 ${cash:,.0f} 만큼만 매수 (필요 ${amount:,.0f})")
    if q < 1:
        out["notes"].append(f"매수 못 함 — {label} ${amount:,.0f} 로 1주(${px:.2f})도 못 삼 (예수금 ${cash:,.0f})")
        return out
    out["target"] = {"floor_id": fid, "amount": round(amount, 2), "label": label}
    out["order"] = {"side": "BUY", "type": otype, "qty": q, "price": round(px, 2), "kind": "buy_sniper", "mode": MODE_SNIPER, "level": None,
                    "floor_id": fid, "new_floor": nf, "plan_usd": round(amount, 2), "signal": sig["signal_type"],
                    "desc": f"스나이퍼 {SIGNAL_KO.get(sig['signal_type'], sig['signal_type'])} · {label} ${amount:,.0f} (기준 ${sig['anchor']:.2f} {sig['chg_pct']:+.2f}%)"}
    return out


def make_plan(s, st, price, state, rsi, usd_cash, sellable, now_et, otype=None):
    """오늘(지금) 스나이퍼 계획 미리보기 — 탑쌓기 make_plan 과 같은 모양 {"orders","notes","info"}. 상태·장부를 바꾸지 않음. 상황판·--check·텔레그램 오늘 계획용"""
    otype = otype or s.get("order_type") or "LIMIT"
    sells, snotes = plan_sells(s, st, price, sellable, otype=otype)
    buy = plan_buy(s, st, price, state, rsi, usd_cash, now_et, otype=otype)
    orders = list(sells) + ([buy["order"]] if buy["order"] else [])
    fl = active_floors(st)
    q, principal = TW.totals(st)
    avg = round(principal / q, 4) if q > 0 else 0.0
    rows = sell_rows(st, s, price)
    fu, nfl, _g = TW.params(s)
    info = {"mode": MODE_SNIPER, "price": _f(price), "avg": avg, "qty": q, "profit_pct": (round((_f(price) / avg - 1) * 100, 2) if avg > 0 and _f(price) > 0 else None),
            "sells": rows, "sell_target": min((r["target"] for r in rows), default=0.0), "profit_reached": any(r["reached"] for r in rows),
            "signal": buy["signal"], "buy_target": buy["target"], "n_layers": len(fl), "floors_max": nfl, "floor_usd": fu, "cap_usd": fu * nfl,
            "tp_l1": tp_pcts(s)[0], "tp_upper": tp_pcts(s)[1], "attack_id": attack_id(st), "rsi": rsi, "usd_cash": round(_f(usd_cash), 2),
            "need_usd": round(buy["order"]["qty"] * buy["order"]["price"], 2) if buy["order"] else 0.0}
    return {"orders": orders, "notes": snotes + buy["notes"], "info": info}


# ---------------------------------------------------------------- 체결 뒤 기준가 갱신
def note_fills(state, done, now_iso=""):
    """체결 반영 결과(done = apply_tower_fills 가 돌려준 목록)로 기준가를 갱신: 매도 체결 → 그 체결 평균가(직전 익절가, 'exit'), 매수 체결 → 그 체결 평균가('buy').
    done 은 반영한 순서 그대로라 마지막 체결이 기준이 됨. 바뀌었으면 True"""
    changed = False
    for a in done or []:
        dq, da = int(_f(a.get("dq"))), _f(a.get("da"))
        if dq <= 0 or da <= 0:
            continue
        if a.get("side") != "SELL" and (a.get("o") or {}).get("kind") != "buy_sniper":
            continue                                             # 탑쌓기 매수는 스나이퍼 기준가를 안 바꿈 (직전 익절가 유지)
        state["anchor"] = round(da / dq, 4)
        state["anchor_kind"] = "exit" if a.get("side") == "SELL" else "buy"
        state["anchor_at"] = now_iso
        changed = True
    return changed


def trigger_lines(s, st, state, now_et=None):
    """체결 알림·상황판용 '다음 매매' 글자: 층별 다음 매도(목표가·수량) + 다음 매수 타점(눌림/돌파·기준·상한). 상태는 안 바꿈"""
    lines = []
    for r in sorted(sell_rows(st, s, 0.0), key=lambda r: r["no"])[:6]:
        lines.append(f"다음 매도: {r['no']}층 평단 ${r['avg']:.2f} → 목표가 ${r['target']:.2f} 에 {r['qty']}주 전량 (+{r['pct']:g}%{' · 공격 층' if r['role'] == 'L1' else ''})")
    fl = active_floors(st)
    anchor, kind = anchor_info(st, state)
    cap = min((TW.floor_avg(f) for f in fl), default=0.0)
    if anchor > 0:
        sig = buy_signal(0.0, anchor, kind, cap, len(fl), None, False)
        lines.append(f"다음 매수: 눌림 ${sig['pullback_price']:.2f} ({sig['drop_pct']:+.1f}%)" + (f" / 돌파 ${sig['breakout_price']:.2f} (RSI {BREAKOUT_MAX_RSI:g} 이하)" if sig["breakout_price"] > 0 else "")
                     + f" · 기준 ${anchor:.2f}" + (f" · 상한 ${cap:.2f}" if cap > 0 else ""))
    else:
        lines.append("다음 매수: 기준가 없음 (직전 익절가 대기)")
    return lines


# ---------------------------------------------------------------- 상태 파일 (cfg = ConfigManager: _load_json·_save_json 재사용)
def new_state():
    return {"version": 1, "anchor": 0.0, "anchor_kind": "", "anchor_at": "", "last_order_ts": 0.0, "buy_block_until": 0.0, "series": []}


def load_state(cfg):
    d = cfg._load_json(SNIPER_FILE, None)
    if not isinstance(d, dict):
        return new_state()
    base = new_state()
    base.update({k: v for k, v in d.items() if k in base})
    if not isinstance(base.get("series"), list):
        base["series"] = []
    return base


def save_state(cfg, state):
    cfg._save_json(SNIPER_FILE, state)


def gauge(complete_cost, partial_cost, cash):
    """시드 배분 10칸 게이지 (참조 quant_engine 게이지 규칙: 🟦 완성 층 · 🟨 채우는 중인 층 · 🟩 남은 시드(현금)). 있는 영역은 최소 1칸, 합계 10칸 → (막대, 완성%, 진행%, 현금%)"""
    a, b, c = max(0.0, _f(complete_cost)), max(0.0, _f(partial_cost)), max(0.0, _f(cash))
    tot = a + b + c
    if tot <= 0:
        return "🟩" * 10, 0.0, 0.0, 100.0
    pa, pb = round(a / tot * 100, 1), round(b / tot * 100, 1)
    na, nb, nc = int(round(a / tot * 10)), int(round(b / tot * 10)), int(round(c / tot * 10))
    if a > 0 and na == 0:
        na = 1
    if b > 0 and nb == 0:
        nb = 1
    if c > 0 and nc == 0:
        nc = 1
    while na + nb + nc > 10:
        if na >= nb and na >= nc and na > 1:
            na -= 1
        elif nc >= na and nc >= nb and nc > 1:
            nc -= 1
        elif nb > 1:
            nb -= 1
        else:
            break
    while na + nb + nc < 10:
        if a >= c and a >= b:
            na += 1
        elif c >= a and c >= b:
            nc += 1
        else:
            nb += 1
    return "🟦" * na + "🟨" * nb + "🟩" * nc, pa, pb, round(max(0.0, 100.0 - pa - pb), 1)
