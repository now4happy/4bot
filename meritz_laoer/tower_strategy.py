# ==========================================================
# FILE: meritz_laoer/tower_strategy.py   (MERITZ_LAOER v2.2.2)
# v2.2.2 (2026-11-19, 판 14): 표시용 view_lines · floor_status 추가 (층 상태를 글자 줄로 바꾸는 순수 계산 — 상태·주문 계산은 안 건드림). 텔레그램 현상태(상황판)에서 tg_menu.py 가 부름
# v2.2.0 (2026-11-19, 판 13): 새 파일 — 탑쌓기(동적 층 시스템) 계산부. 순수 계산 (파일·네트워크·시계 없음). accum_strategy.py(사다리)는 안 건드림 (롤백용)
#   main.py 는 settings["strategy"] == "tower" 일 때만 이 모듈을 씀 (기본 "ladder")
# 설계 (판 13 지시):
#   - 10층 · 한 층 $15,000 · 총 $150,000 · 층 간격 $5 (조정 가능: settings tower_gap_usd / tower_floor_usd / tower_floors, 없으면 기본값)
#   - 한 층 = 간격(달러) 칸. 칸마다 1달러씩 내려가며 분산 매수. 칸당 금액 = 층 금액 ÷ 간격 (반올림). 주식수도 반올림(0.5 는 올림)
#   - 층은 동적: 층 투자금(실제 체결 수량×체결가)이 층 금액에서 TOL_USD 이내로 모자라거나 넘으면 완성. 그 층 평단(가중평균)이 기준 →
#     다음 층 첫 칸 = 기준 평단 − 간격 (이어서 1달러씩 아래로 간격 칸)
#   - 매도: 전체 평단 +10% 에 보유 50% (설정값 sell_profit_pct·sell_fraction_pct). 매도 수량은 층별로 보유 비율대로 나눠 뺌
#   - 탑업: 매도 뒤 각 층은 (남은 주식 원가 + 새로 사는 금액) = 층 금액 이 되도록 부족분을, 그 층 평단 −1 ~ −간격 달러 칸에 나눠 산다
#   - 층이 꼬이면(위 층보다 평단이 같거나 높음) 가중평균으로 합치고 평단 오름차순으로 재배치 (수량·투자금 보존)
#   - 슬리피지: 층 상태는 실제 체결로만 계산. 못 산 금액은 같은 층의 다음 칸에 더함. 매일 동기화 때 장부(실제 보유분)와 다르면 가장 최근 층이 차이를 흡수
#   - 바벨 모드·SGOV·현금 배분 없음
# 상태(state): {"version": 1, "floors": [ {id, qty, cost, target, done, closed, levels, settled, base_usd, carry_usd, kind} ... 평단 오름차순 ],
#               "next_id": int, "sell_block": bool}
#   id = 위에서부터 몇 층인지 (1 = 평단 가장 높은 층). 정리(normalize) 때마다 평단 순서로 다시 붙임
# ==========================================================
import math

FLOOR_USD = 15000.0        # 한 층 금액 (달러)
FLOORS = 10                # 층 수 → 총 한도 = FLOOR_USD × FLOORS = $150,000
GAP_USD = 5                # 층 간격 (달러) = 한 층의 칸 수
TOL_USD = 100.0            # 완성 허용 오차: 층 투자금이 목표에서 이만큼 이내로 모자라면 완성 (슬리피지·반올림)


def _f(v):
    try:
        x = float(str(v if v is not None else 0).replace(",", ""))
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def ceil2(x):
    return math.ceil(round(_f(x) * 100, 6)) / 100.0


def rnd(x):
    """반올림 (0.5 는 올림). 파이썬 round 는 0.5 를 짝수로 보내서 안 씀"""
    return int(math.floor(_f(x) + 0.5 + 1e-9))


def params(s):
    """(층 금액, 층 수, 간격=칸 수). 설정에 없거나 이상하면 기본값. 간격은 1 이상 정수만"""
    s = s or {}
    fu = _f(s.get("tower_floor_usd")) or FLOOR_USD
    fl = int(_f(s.get("tower_floors"))) or FLOORS
    g = _f(s.get("tower_gap_usd"))
    g = int(g) if g >= 1 and g == int(g) else GAP_USD
    return (fu if fu > 0 else FLOOR_USD), (fl if fl >= 1 else FLOORS), g


# ---------------------------------------------------------------- 상태 기본 동작
def new_state():
    return {"version": 1, "floors": [], "next_id": 1, "sell_block": False}


def floor_avg(f):
    q = int(_f(f.get("qty")))
    return round(_f(f.get("cost")) / q, 4) if q > 0 else 0.0


def is_complete(f, tol=TOL_USD):
    """완성된 층: 완성 표시(done)가 있거나, 투자금이 목표에서 tol 이내로 모자라거나 넘음"""
    return bool(f.get("done")) or _f(f.get("cost")) >= _f(f.get("target") or FLOOR_USD) - tol - 1e-9


def _floor(fid, qty, cost, target, kind):
    return {"id": int(fid), "qty": int(qty), "cost": round(_f(cost), 4), "target": float(target), "done": False, "closed": False,
            "levels": [], "settled": [], "base_usd": 0.0, "carry_usd": 0.0, "kind": kind}


def migrate_from_holdings(qty, principal, s=None):
    """지금 보유분(장부의 주식수·원금) → 1층. 숫자는 호출한 쪽이 장부에서 읽어 넘김 (여기서 정하지 않음).
    1층은 투자금이 층 금액보다 적어도 '완성된 층'으로 침. 보유 0주면 층 없음"""
    fu, _fl, _g = params(s)
    st = new_state()
    q, p = int(_f(qty)), _f(principal)
    if q > 0 and p > 0:
        f = _floor(1, q, p, fu, "migrated")
        f["done"] = True
        st["floors"] = [f]
        st["next_id"] = 2
    return st


def totals(st):
    fl = st.get("floors") or []
    return sum(int(_f(f.get("qty"))) for f in fl), round(sum(_f(f.get("cost")) for f in fl), 4)


def top_down(st):
    """위(평단 높은 층)부터. id 순서 (정리 뒤에는 평단 내림차순과 같음)"""
    return sorted(st.get("floors") or [], key=lambda f: int(_f(f.get("id"))))


def _topup_setup(f, gap):
    """매도·합병 뒤: 부족분(층 금액 − 남은 투자금)을 그 층 평단 −1 ~ −간격 달러 칸에 나눠 사도록 준비. 부족분이 tol 이하면 완성"""
    need = _f(f.get("target") or FLOOR_USD) - _f(f.get("cost"))
    f["settled"], f["carry_usd"], f["closed"] = [], 0.0, False
    avg = floor_avg(f)
    if need <= TOL_USD + 1e-9 or avg <= 0:
        f["done"], f["levels"], f["base_usd"] = True, [], 0.0
        return f
    f["done"] = False
    f["levels"] = [p for p in (round(avg - j, 2) for j in range(1, gap + 1)) if p > 0]
    f["base_usd"] = float(rnd(need / gap))
    return f


def _new_floor_band(anchor, gap, target):
    """새 층: 첫 칸 = 기준 평단 − 간격, 이어서 1달러씩 아래로 간격 칸"""
    return [p for p in (round(_f(anchor) - gap - i, 2) for i in range(gap)) if p > 0], float(rnd(target / gap))


# ---------------------------------------------------------------- 계획
def make_plan(s, st, qty, principal, price, fx, usd_cash, sellable, ignore_auto_fx=False):
    """오늘 낼 주문 계산 → {"orders", "notes", "info"} (accum_strategy.make_plan 과 같은 모양). 상태·장부를 바꾸지 않음.
    s: 설정, st: 탑쌓기 상태, qty/principal: 장부(주·달러), price: 현재가, fx: 메리츠 적용환율(원/달러), usd_cash: USD 예수금, sellable: 매도가능 수량"""
    qty, principal, price = int(_f(qty)), _f(principal), _f(price)
    fu, nfl, gap = params(s)
    avg = round(principal / qty, 4) if qty > 0 else 0.0
    pct, frac = _f(s.get("sell_profit_pct")), _f(s.get("sell_fraction_pct"))
    otype, per_day = s.get("order_type"), int(_f(s.get("max_rounds_per_day")))
    st = st if isinstance(st, dict) and isinstance(st.get("floors"), list) else new_state()
    notes, orders = [], []
    target = ceil2(avg * (1 + pct / 100.0)) if qty > 0 else 0.0
    profit_pct = round((price / avg - 1) * 100, 2) if avg > 0 and price > 0 else None
    fl_qty, fl_cost = totals(st)
    info = {"mode": "tower", "avg": avg, "qty": qty, "price": price, "fx": fx, "sell_target": target, "profit_pct": profit_pct,
            "filled": [], "levels": [], "rebuy_anchor": None, "rebuy_k": 0,
            "profit_reached": bool(qty > 0 and target > 0 and price >= target), "credit_usd": 0.0}
    if qty > 0 and fl_qty != qty:
        notes.append(f"층 합계 {fl_qty}주 ≠ 장부 {qty}주 — 다음 주문일 동기화 때 가장 최근 층이 차이를 흡수해요")

    # ---------------- 매도: 전체 평단 +pct% 에 보유 frac% (반올림, 1주는 남김)
    if qty > 0:
        sell_qty = min(rnd(qty * frac / 100.0), qty - 1)
        if st.get("sell_block") and not s.get("allow_consecutive_sell"):
            notes.append("매도 보류: 직전 매도 뒤 재매수(탑업) 체결이 아직 없음 (allow_consecutive_sell=false)")
        elif sell_qty < 1:
            notes.append(f"매도 {frac:g}% = 0주 (보유 {qty}주) — 매도 안 함")
        elif sell_qty > min(int(_f(sellable)), qty):
            notes.append(f"매도 {sell_qty}주 > 매도가능 {int(_f(sellable))}/장부 {qty} — 매도 안 함")
        else:
            orders.append({"side": "SELL", "type": otype, "qty": sell_qty, "price": target, "kind": "sell", "level": None,
                           "desc": f"전체 평단 ${avg:.2f} +{pct:g}% 매도 {frac:g}%"})

    if not (fx and fx > 0):
        notes.append("환율 없음 — 매수 계획 불가 (매도만)")
        return {"orders": orders, "notes": notes, "info": info}

    # ---------------- 지금 채울 층 찾기 (위에서부터 처음 미완성 층). 범위를 벗어난 층은 닫힌 것으로 침
    cap_total = fu * nfl
    floors = top_down(st)
    closes, active = [], None
    for f in floors:
        if int(_f(f.get("qty"))) <= 0 or is_complete(f) or f.get("closed"):
            continue
        unset = [p for p in f.get("levels") or [] if p not in set(f.get("settled") or [])]
        if not unset:
            closes.append(f["id"])                                   # 칸을 다 썼는데 미완성 → 미완성 층으로 닫음 (부족분은 그대로)
            continue
        if _f(f.get("cost")) > 0 and price > 0 and price < min(f["levels"]) - gap:
            closes.append(f["id"])                                   # 가격이 층 범위를 한 간격 넘게 벗어남 → 미완성 층으로 닫음
            notes.append(f"{f['id']}층: 현재가 ${price:.2f} 가 층 범위(맨 아래 ${min(f['levels']):.2f})를 벗어나 미완성 층으로 둠 (부족분 ${max(_f(f['target']) - _f(f['cost']), 0):,.0f} 그대로)")
            continue
        active = f
        break
    new_floor = None
    room = cap_total - principal
    if active is None:
        have = [f for f in floors if int(_f(f.get("qty"))) > 0]
        if not have:
            notes.append("층 없음 (보유 0주) — 탑쌓기는 기존 보유분을 1층으로 시작해야 해요 (장부 시작 필요)")
        elif room < TOL_USD:
            notes.append(f"총 한도 ${cap_total:,.0f} 도달 (보유 원가 ${principal:,.0f}) — 새 층 없음")
        else:
            anchor = min(floor_avg(f) for f in have)
            tgt = min(fu, room)
            lv, base = _new_floor_band(anchor, gap, tgt)
            nid = max(int(_f(st.get("next_id"))), max(int(_f(f.get("id"))) for f in floors) + 1)
            new_floor = {"id": nid, "anchor": anchor, "levels": lv, "base_usd": base, "target": tgt}
            active = {"id": nid, "qty": 0, "cost": 0.0, "target": tgt, "levels": lv, "settled": [], "base_usd": base, "carry_usd": 0.0}
    cand = []
    if active is not None:
        settled = set(active.get("settled") or [])
        cand = [p for p in active["levels"] if p not in settled]
        info["levels"], info["filled"] = list(active["levels"]), sorted(settled, reverse=True)
        info["unit_usd"] = active["base_usd"]
    info["tower"] = {"gap": gap, "floor_usd": fu, "floors_max": nfl, "cap_usd": cap_total, "active": (active or {}).get("id"),
                     "new_floor": bool(new_floor), "floors": [{"id": f["id"], "qty": f["qty"], "cost": round(_f(f["cost"]), 2), "avg": floor_avg(f),
                                                              "complete": is_complete(f), "closed": bool(f.get("closed")) or f["id"] in closes} for f in floors]}

    # ---------------- 칸 금액 (칸당 금액 반올림 · 주식수 반올림 · 못 산 금액은 같은 층 다음 칸에 더함)
    auto_fx = bool(s.get("auto_fx_enabled")) and not ignore_auto_fx
    pool = max(0.0, room if auto_fx else min(_f(usd_cash), room))
    cash_binds = (not auto_fx) and _f(usd_cash) <= room + 1e-9
    info.update({"unit_usd": info.get("unit_usd", 0.0), "cap_usd": round(cap_total, 2), "pool_usd": round(pool, 2)})
    spent, planned, roll = 0.0, 0.0, 0.0
    tgt_active = _f((active or {}).get("target") or fu)
    for n, p in enumerate(cand[:per_day]):
        is_last = (p == cand[-1])
        carry = _f(active.get("carry_usd")) if n == 0 else 0.0
        if is_last:                                                  # 마지막 칸 = 층에 모자란 만큼 전부 (그날 앞 칸 계획분 제외)
            amount = max(0.0, tgt_active - _f(active.get("cost")) - planned)
        else:
            amount = max(0.0, _f(active["base_usd"]) + carry + roll)
        q = rnd(amount / p) if amount > 0 and p > 0 else 0
        if q < 1:
            notes.append(f"{active['id']}층 ${p:.2f} 칸 금액 ${amount:,.2f} < 0.5주 — 생략 (금액은 다음 칸으로 넘김)")
            roll += amount
            continue
        roll = 0.0
        cost = q * p
        desc = (f"탑쌓기 {active['id']}층 ${p:.2f} 칸 (칸당 ${_f(active['base_usd']):,.0f}"
                + (f" + 이월 ${carry:,.0f}" if carry > 0.5 else "") + (", 마지막 칸" if is_last else "") + ")")
        meta = {"floor_id": active["id"], "new_floor": new_floor, "closes": list(closes), "plan_usd": round(amount, 2), "carry_used": round(carry, 2)}
        if spent + cost > pool + 1e-9:
            left = pool - spent
            if cash_binds:                                           # 현금으로 살 수 있는 만큼만 (정수 주 내림) — v2.0.4 부분 매수와 같은 규칙
                pq = int(math.floor(left / p + 1e-9)) if left > 0 else 0
                if pq >= 1:
                    orders.append(dict({"side": "BUY", "type": otype, "qty": pq, "price": p, "kind": "buy_tower", "level": p, "idx": None, "credit": 0.0,
                                        "partial": True, "full_qty": q, "desc": desc + f" · 현금만큼 부분 매수 (원래 {q}주)"}, **meta))
                    spent += pq * p
                    info["partial"] = {"price": p, "qty": pq, "full_qty": q}
                    notes.append(f"현금 부족 — ${p:.2f} 칸 {q}주 중 {pq}주만 부분 매수 (필요 ${cost:,.2f} > 가용 ${left:,.2f}, 나머지는 다음 칸에 이월)")
                else:
                    notes.append(f"현금 부족 — 가용 ${max(left, 0):,.2f} < 1주(${p:.2f}) — 이 칸 안 삼")
            else:
                notes.append(f"{'한도' if auto_fx else '달러 또는 한도'} 부족 (필요 ${spent + cost:,.2f} > 가용 ${pool:,.2f}) — ${p:.2f} 칸부터 생략")
            break
        spent += cost
        planned += amount
        orders.append(dict({"side": "BUY", "type": otype, "qty": q, "price": p, "kind": "buy_tower", "level": p, "idx": None, "credit": 0.0, "desc": desc}, **meta))
    if not cand and active is None and not notes:
        notes.append("살 칸 없음")
    info["need_usd"] = round(spent, 2)
    info["usd_cash"] = round(_f(usd_cash), 2)
    info["shortfall_usd"] = round(max(0.0, spent - _f(usd_cash)), 2)
    info["auto_fx"] = auto_fx
    return {"orders": orders, "notes": notes, "info": info}


# ---------------------------------------------------------------- 체결 반영
def _by_id(st, fid):
    for f in st.get("floors") or []:
        if int(_f(f.get("id"))) == int(_f(fid)):
            return f
    return None


def _largest_remainder(total, weights):
    """total 개를 weights 비율로 정수로 나눔 (합계 보존). 각 몫은 weights(보유 주수)를 넘지 않음"""
    w = [max(0, int(x)) for x in weights]
    s = sum(w)
    if s <= 0 or total <= 0:
        return [0] * len(w)
    total = min(total, s)
    raw = [total * x / s for x in w]
    out = [int(math.floor(r + 1e-9)) for r in raw]
    rest = total - sum(out)
    order = sorted(range(len(w)), key=lambda i: (-(raw[i] - out[i]), i))
    for i in order:
        if rest <= 0:
            break
        if out[i] < w[i]:
            out[i] += 1
            rest -= 1
    return out


def apply_fill(st, order, fill_qty, fill_amount, gap=GAP_USD):
    """체결 1건 반영 (st 를 직접 바꿔 돌려줌). fill_qty = 실제 체결 수량, fill_amount = 실제 체결 금액(수량×체결가 합계). 계획 금액이 아니라 이 값만 씀"""
    q, amt = int(_f(fill_qty)), _f(fill_amount)
    kind = order.get("kind")
    if q <= 0 or amt <= 0:
        return st
    if kind == "buy_tower":
        f = _by_id(st, order.get("floor_id"))
        nf = order.get("new_floor")
        if f is None and isinstance(nf, dict):                       # 새 층의 첫 체결 때 층을 만듦 (같은 층의 다음 체결은 같은 id 로 찾음)
            f = _floor(nf["id"], 0, 0.0, nf["target"], "build")
            f["levels"], f["base_usd"] = list(nf["levels"]), float(nf["base_usd"])
            st["floors"].append(f)
            st["next_id"] = max(int(_f(st.get("next_id"))), int(nf["id"]) + 1)
        if f is None:
            return st
        f["qty"] = int(f["qty"]) + q
        f["cost"] = round(_f(f["cost"]) + amt, 4)
        lv = round(_f(order.get("level")), 2)
        if lv not in (f.get("settled") or []):
            f.setdefault("settled", []).append(lv)
        f["carry_usd"] = round(_f(f.get("carry_usd")) - _f(order.get("carry_used")) + (_f(order.get("plan_usd")) - amt), 2)   # 못 산 금액 이월
        for cid in order.get("closes") or []:
            c = _by_id(st, cid)
            if c is not None and c is not f:
                c["closed"] = True
        if is_complete(f):
            f["done"], f["closed"], f["levels"], f["settled"], f["carry_usd"] = True, False, [], [], 0.0
        elif f["levels"] and all(p in f["settled"] for p in f["levels"]):
            f["closed"] = True                                       # 칸을 다 썼는데 미완성: 부족분(carry_usd)은 그대로 두고 미완성 층으로
        st["sell_block"] = False
    elif kind == "sell":
        floors = top_down(st)
        qs = [int(_f(f.get("qty"))) for f in floors]
        tq = sum(qs)
        if tq <= 0:
            return st
        before_cost = sum(_f(f.get("cost")) for f in floors)
        cuts = _largest_remainder(q, qs)
        for f, a in zip(floors, cuts):                               # 층 평단은 그대로 두고 수량·투자금만 줄임
            if a > 0:
                avg0 = floor_avg(f)
                f["qty"] = int(f["qty"]) - a
                f["cost"] = round(max(0.0, _f(f["cost"]) - a * avg0), 4)
        left_q = tq - min(q, tq)
        want = round(before_cost * left_q / tq, 4)                   # 장부와 같은 규칙: 남은 원가 = 이전 원가 × 남은 수량 ÷ 이전 수량
        live = [f for f in floors if int(f["qty"]) > 0]
        if live:
            live[-1]["cost"] = round(_f(live[-1]["cost"]) + (want - sum(_f(f["cost"]) for f in live)), 4)   # 반올림 차이는 가장 최근 층이 흡수
        st["floors"] = live
        for f in live:
            _topup_setup(f, gap)
        st["sell_block"] = True
    return st


def apply_fill_to_state(st, order, avg_before=0.0, allow_consecutive_sell=False, fill=None, gap=GAP_USD):
    """accum_strategy.apply_fill_to_state 와 같은 모양의 입구. fill = (체결 수량, 체결 금액). fill 이 없으면 반영 안 함 (탑쌓기는 실제 체결로만 계산)"""
    if fill is None:
        return st
    return apply_fill(st, order, fill[0], fill[1], gap)


# ---------------------------------------------------------------- 동기화 · 정리
def _merge(a, b, gap):
    m = _floor(min(int(a["id"]), int(b["id"])), int(a["qty"]) + int(b["qty"]), _f(a["cost"]) + _f(b["cost"]), max(_f(a["target"]), _f(b["target"])), "merged")
    return _topup_setup(m, gap)


def normalize(st, gap=GAP_USD):
    """수량 0 인 층 정리 → 꼬인 층 합병(위 층보다 평단이 같거나 높으면 가중평균으로 합침) → 평단 오름차순 재배치(id 는 위에서부터 다시 붙임). → 알림 글자 목록"""
    notes = []
    fl = [f for f in top_down(st) if int(_f(f.get("qty"))) > 0]
    out = []
    for f in fl:
        cur = f
        while out and floor_avg(cur) >= floor_avg(out[-1]) - 1e-9:
            top = out.pop()
            notes.append(f"층 합병: {top['id']}층(평단 ${floor_avg(top):.2f}) + {cur['id']}층(평단 ${floor_avg(cur):.2f}) → 수량 {int(top['qty']) + int(cur['qty'])}주")
            cur = _merge(top, cur, gap)
        out.append(cur)
    out.sort(key=lambda f: -floor_avg(f))                            # 위(평단 높은 층)부터 번호를 다시 붙임
    for i, f in enumerate(out, 1):
        f["id"] = i
    st["floors"] = sorted(out, key=floor_avg)                        # 저장은 평단 오름차순 (수량·투자금 보존)
    st["next_id"] = len(out) + 1
    return notes


def reconcile(st, qty, principal, gap=GAP_USD, s=None):
    """매일 동기화: 층 합계가 장부(실제 보유분)와 다르면 장부에 맞춤 — 차이는 가장 최근 층(가장 아래 층)이 흡수. 그 뒤 꼬인 층 정리.
    → (st, 알림 글자 목록). 장부가 0주면 층을 비움"""
    fu, _fl, _g = params(s)
    qty, principal = int(_f(qty)), _f(principal)
    notes = []
    if qty <= 0:
        if st.get("floors"):
            notes.append("장부 0주 — 층 상태를 비움")
        st["floors"], st["next_id"] = [], 1
        return st, notes
    if not st.get("floors"):
        st.update(migrate_from_holdings(qty, principal, s))
        notes.append(f"층 없음 → 현재 보유분 {qty}주를 1층으로 만듦")
        return st, notes
    tq, tc = totals(st)
    dq, dc = qty - tq, round(principal - tc, 4)
    if dq != 0 or abs(dc) > 0.01:
        notes.append(f"층 상태 조정: 층 합계 {tq}주·${tc:,.2f} → 장부 {qty}주·${principal:,.2f} (차이 {dq:+d}주·${dc:+,.2f}를 가장 최근 층이 흡수)")
        fl = sorted(st["floors"], key=lambda f: -int(_f(f.get("id"))))      # 가장 아래(최근) 층부터
        rest_q, rest_c = dq, dc
        for f in fl:
            take_q = max(rest_q, -int(f["qty"])) if rest_q < 0 else rest_q
            f["qty"] = int(f["qty"]) + take_q
            rest_q -= take_q
            take_c = max(rest_c, -_f(f["cost"])) if rest_c < 0 else rest_c
            f["cost"] = round(_f(f["cost"]) + take_c, 4)
            rest_c = round(rest_c - take_c, 4)
            if rest_q == 0 and abs(rest_c) <= 0.01:
                break
        if rest_q > 0 and fl:
            fl[0]["qty"] = int(fl[0]["qty"]) + rest_q
        if rest_c > 0.01 and fl:
            fl[0]["cost"] = round(_f(fl[0]["cost"]) + rest_c, 4)
    notes += normalize(st, gap)
    return st, notes


# ---------------------------------------------------------------- 표시 (v2.2.2, 판 14)
BLOCK_DONE, BLOCK_BUILD = "█", "▒"      # 층 칸 글자: 완성 층 / 쌓는 중·미완성 층 (이모티콘 아님 — 코드 안 이모티콘 금지 규칙)


def floor_status(f):
    """층 상태 글자: 완성 | 쌓는 중 | 미완성 (칸을 다 썼는데 부족분이 남아 닫힌 층)"""
    if is_complete(f):
        return "완성"
    return "미완성" if f.get("closed") else "쌓는 중"


def view_lines(st, s=None):
    """탑쌓기 층 시각화 글자 줄. 채워진 층(수량 > 0)만 보임 — 비어 있는 층은 안 보임.
    첫 줄: 층마다 칸 1개(완성 █ · 쌓는 중/미완성 ▒) + 'N/최대층'. 다음 줄들: 층별 '1층 · 평단 $48.59 · 299주 · 완성' (위에서부터).
    평단 = 층 투자금(실제 체결 합계) ÷ 수량 = 가중평균. 상태가 비었거나 이상하면 0층"""
    _fu, nfl, _g = params(s)
    fl = [f for f in top_down(st if isinstance(st, dict) else {}) if int(_f(f.get("qty"))) > 0]
    if not fl:
        return [f"탑: 0/{nfl}층 (채운 층 없음)"]
    lines = [f"탑: {' '.join(BLOCK_DONE if is_complete(f) else BLOCK_BUILD for f in fl)}  {len(fl)}/{nfl}층"]
    for f in fl:
        lines.append(f"{int(_f(f.get('id')))}층 · 평단 ${floor_avg(f):.2f} · {int(_f(f.get('qty')))}주 · {floor_status(f)}")
    return lines
