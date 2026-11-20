# ==========================================================
# FILE: meritz_laoer/tower_strategy.py   (MERITZ_LAOER v2.2.6)
# v2.2.9 (2026-11-20, audit-fix 7-4·새 층 규칙, 3차): ① 1주 층은 자동 매도에서 뺌 (floor_sell_qty(1,·)=0, info["sell_excluded"]) — 풀이님 결정 10:03 ② 새 층을 못 만들면(총 한도 도달·가격 칸 없음) 만들지 않고 info["tower"]["new_floor_blocked"] 로 알림 — 자동으로 늘리거나 멈추지 않음 (풀이님 결정 09:59). 사다리(accum_strategy.py) 삭제로 탑쌓기 전용. 간격 기본값 GAP_USD=5 그대로
# v2.2.6 (2026-11-20, 판 16 본격): ① 층별 매도(각 층 자기 평단 +10% 에 그 층 50%, 주문마다 floor_id·floor_avg 기록, 1주 층은 1주) ② 전역 sell_block → 층별 rebuy_pending (그 층 매수 체결·층 닫힘 때 해제)
#   ③ 반영한 주문번호 맵(st["applied"]) — 같은 체결 두 번 반영 방지(누적 체결 기준 증분만 반영) ④ sort_fills: 시간순(없으면 매도 먼저)·새 층 계획 매수는 그날 매도 반영 뒤로 (B1)
#   ⑤ 새 층 계획 매수의 1층 빈칸 판정은 체결 평균가 기준 ±0.01 (B2) · closes 층은 건너뜀 (B3) · 층 시드 상한·base_usd 재계산 (B4) · 흡수한 가격은 새 층 settled (B5)
#   ⑥ add_holdings(토스 입고분을 1층 빈곳에 넣음) ⑦ view_lines: 반칸 표시·미완성 글자. 새 층 기준점은 아래층 평단 그대로 (Q4)
# v2.2.5 (2026-11-20, 판 16 1층 채우기 매수): apply_fill 매수 체결 때, 계획한 새 층이 아직 없는데 위에 미완성 층이 있고 그 층의 안 산 칸에 이 체결 가격이 있으면 그 층(1층 탑업)에 넣음. 아침에 1층 완성 상태로 2층을 계획했는데 장중 매도로 1층이 미완성이 된 경우(버그 2) — 매수가 2층이 아니라 1층 빈곳을 채움. 이월(carry)은 주문의 계획 금액 기준으로 계산 (마지막 칸이 남은 부족분을 전부 가져가서 스스로 바로잡힘)
# v2.2.4 (2026-11-19, 1층 시작가 메뉴): _topup_setup·apply_fill·apply_fill_to_state·normalize·reconcile 에 start_usd 전달 — 1층 시작가가 정해졌으면 1층 칸이 시작가 기준
# v2.2.3 (2026-11-19, 판 14 색상 고침): 층 칸을 층별 색상 네모로 바꿈 (1층 🟩 시작). 흰색 █ 한 가지라 층 구분이 안 된다는 사용자 지적. 완성/쌓는 중 구분은 상세 줄 글자로만.
# v2.2.2 (2026-11-19, 판 14): 표시용 view_lines · floor_status 추가 (층 상태를 글자 줄로 바꾸는 순수 계산 — 상태·주문 계산은 안 건드림). 텔레그램 현상태(상황판)에서 tg_menu.py 가 부름
# v2.2.0 (2026-11-19, 판 13): 새 파일 — 탑쌓기(동적 층 시스템) 계산부. 순수 계산 (파일·네트워크·시계 없음). 사다리는 v2.2.9 에서 삭제됨
#   (v2.2.9: 7번은 탑쌓기만 씀 — 전환 설정 strategy 없음)
# 설계 (판 13 지시):
#   - 10층 · 한 층 $15,000 · 총 $150,000 · 층 간격 $5 (조정 가능: settings tower_gap_usd / tower_floor_usd / tower_floors, 없으면 기본값)
#   - 한 층 = 간격(달러) 칸. 칸마다 1달러씩 내려가며 분산 매수. 칸당 금액 = 층 금액 ÷ 간격 (반올림). 주식수도 반올림(0.5 는 올림)
#   - 층은 동적: 층 투자금(실제 체결 수량×체결가)이 층 금액에서 TOL_USD 이내로 모자라거나 넘으면 완성. 그 층 평단(가중평균)이 기준 →
#     다음 층 첫 칸 = 기준 평단 − 간격 (이어서 1달러씩 아래로 간격 칸)
#   - 매도: (v2.2.6) 각 층이 자기 평단 +10% 에 닿으면 그 층 보유의 50% (설정값 sell_profit_pct·sell_fraction_pct). 예전(v2.2.5 까지)은 전체 평단 기준·층별 비례로 뺌
#   - 탑업: 매도 뒤 각 층은 (남은 주식 원가 + 새로 사는 금액) = 층 금액 이 되도록 부족분을, 그 층 평단 −1 ~ −간격 달러 칸에 나눠 산다
#   - 층이 꼬이면(위 층보다 평단이 같거나 높음) 가중평균으로 합치고 평단 오름차순으로 재배치 (수량·투자금 보존)
#   - 슬리피지: 층 상태는 실제 체결로만 계산. 못 산 금액은 같은 층의 다음 칸에 더함. 매일 동기화 때 장부(실제 보유분)와 다르면 가장 최근 층이 차이를 흡수
#   - 바벨 모드·SGOV·현금 배분 없음
# 상태(state): {"version": 1, "floors": [ {id, qty, cost, target, done, closed, levels, settled, base_usd, carry_usd, kind, rebuy_pending} ... 평단 오름차순 ],
#               "next_id": int, "applied": {주문번호: {"q": 반영한 누적 체결 수량, "amt": 누적 금액}}, "absorbed": {새 층 id: [1층에 흡수된 가격]}}
#   v2.2.6: 전역 sell_block 은 없어지고 층마다 rebuy_pending (예전 상태 파일의 sell_block=true 는 ensure_state 가 미완성 층의 rebuy_pending 으로 옮김)
#   id = 위에서부터 몇 층인지 (1 = 평단 가장 높은 층). 정리(normalize) 때마다 평단 순서로 다시 붙임
# ==========================================================
import copy
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


def floor_sell_qty(q, frac):
    """한 층의 매도 수량: 보유 q 의 frac% (반올림, 0.5 는 올림). 2주 이상이면 1주는 남김. 1주 층은 0주 — 자동 매도에서 빼고 보류 (v2.2.9 audit-fix 7-4, 풀이님 결정 2026-11-20 10:03: 1주 남으면 '1주 남음' 메시지만, 팔려면 직접 매도. v2.2.6 의 '1주 층 1주 판매' 를 되돌림)"""
    q = int(_f(q))
    if q <= 1 or _f(frac) <= 0:
        return 0
    return max(0, min(rnd(q * _f(frac) / 100.0), q - 1))


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
    return {"version": 1, "floors": [], "next_id": 1, "applied": {}, "absorbed": {}}


APPLIED_KEEP = 200          # 반영한 주문번호 맵에 남기는 최대 개수 (오래된 것부터 지움 — 하루 주문은 몇 건이라 충분)


def ensure_state(st):
    """상태 보정 (여러 번 불러도 같음, 모양만 맞춤): applied·absorbed 맵, 층마다 rebuy_pending.
    예전 상태의 전역 sell_block=true 는 '미완성인 층'의 rebuy_pending 으로 옮기고 sell_block 키는 지움 (v2.2.6). 이상한 입력이면 새 상태"""
    if not isinstance(st, dict) or not isinstance(st.get("floors"), list):
        return new_state()
    st.setdefault("version", 1)
    st.setdefault("next_id", 1)
    if not isinstance(st.get("applied"), dict):
        st["applied"] = {}
    if not isinstance(st.get("absorbed"), dict):
        st["absorbed"] = {}
    legacy = bool(st.pop("sell_block", False))
    for f in st["floors"]:
        if "rebuy_pending" not in f:
            f["rebuy_pending"] = bool(legacy and int(_f(f.get("qty"))) > 0 and not is_complete(f))
    return st


def floor_avg(f):
    q = int(_f(f.get("qty")))
    return round(_f(f.get("cost")) / q, 4) if q > 0 else 0.0


def is_complete(f, tol=TOL_USD):
    """완성된 층: 완성 표시(done)가 있거나, 투자금이 목표에서 tol 이내로 모자라거나 넘음"""
    return bool(f.get("done")) or _f(f.get("cost")) >= _f(f.get("target") or FLOOR_USD) - tol - 1e-9


def _floor(fid, qty, cost, target, kind):
    return {"id": int(fid), "qty": int(qty), "cost": round(_f(cost), 4), "target": float(target), "done": False, "closed": False,
            "levels": [], "settled": [], "base_usd": 0.0, "carry_usd": 0.0, "kind": kind, "rebuy_pending": False}


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


def _topup_setup(f, gap, start_usd=0.0):
    """매도·합병 뒤: 부족분(층 금액 − 남은 투자금)을 그 층 평단 −1 ~ −간격 달러 칸에 나눠 사도록 준비. 부족분이 tol 이하면 완성.
    v2.2.4: 1층 시작가가 정해졌으면(start_usd > 0) 1층은 평단 대신 시작가를 기준으로 칸을 정함 (보유 주식이 있어도 1층 가격 배정을 직접 정할 수 있게). 2층 이상은 평단 기준 그대로."""
    need = _f(f.get("target") or FLOOR_USD) - _f(f.get("cost"))
    f["settled"], f["carry_usd"], f["closed"] = [], 0.0, False
    avg = floor_avg(f)
    anchor = _f(start_usd) if int(_f(f.get("id"))) == 1 and _f(start_usd) > 0 else avg
    if need <= TOL_USD + 1e-9 or anchor <= 0:
        f["done"], f["levels"], f["base_usd"] = True, [], 0.0
        return f
    f["done"] = False
    f["levels"] = [p for p in (round(anchor - j, 2) for j in range(1, gap + 1)) if p > 0]
    f["base_usd"] = float(rnd(need / gap))
    return f


def _new_floor_band(anchor, gap, target):
    """새 층: 첫 칸 = 기준 평단 − 간격, 이어서 1달러씩 아래로 간격 칸"""
    return [p for p in (round(_f(anchor) - gap - i, 2) for i in range(gap)) if p > 0], float(rnd(target / gap))


def next_layer_cells(active, tgt_active):
    """다음 회차(채우는 층)의 칸별 배정: [{price, amount, qty}] — 오늘 주문 수와 무관하게 전체 칸.
    금액은 칸당 base_usd(첫 칸은 이월 carry 더함), 마지막 칸은 층에 모자란 만큼 전부. 주식수는 반올림.
    0.5주 미만 칸은 금액이 다음 칸으로 넘어감 (주문 계산과 같은 규칙). 현금·한도 검사는 안 함 (배정 미리보기)."""
    if not active:
        return []
    cand = [p for p in active.get("levels") or [] if p not in set(active.get("settled") or [])]
    cells, planned, roll = [], 0.0, 0.0
    for n, p in enumerate(cand):
        is_last = (p == cand[-1])
        carry = _f(active.get("carry_usd")) if n == 0 else 0.0
        if is_last:
            amount = max(0.0, _f(tgt_active) - _f(active.get("cost")) - planned)
        else:
            amount = max(0.0, _f(active.get("base_usd")) + carry + roll)
            amount = min(amount, max(0.0, _f(tgt_active) - _f(active.get("cost")) - planned))      # v2.2.6 B4: 마지막이 아닌 칸도 층 목표를 못 넘게
        q = rnd(amount / p) if amount > 0 and p > 0 else 0
        if q < 1:
            roll += amount
            continue
        roll = 0.0
        cells.append({"price": round(_f(p), 2), "amount": round(amount, 2), "qty": q})
        planned += amount
    return cells


# ---------------------------------------------------------------- 계획
def make_plan(s, st, qty, principal, price, fx, usd_cash, sellable, ignore_auto_fx=False):
    """오늘 낼 주문 계산 → {"orders", "notes", "info"}. 상태·장부를 바꾸지 않음.
    s: 설정, st: 탑쌓기 상태, qty/principal: 장부(주·달러), price: 현재가, fx: 메리츠 적용환율(원/달러), usd_cash: USD 예수금, sellable: 매도가능 수량"""
    qty, principal, price = int(_f(qty)), _f(principal), _f(price)
    fu, nfl, gap = params(s)
    avg = round(principal / qty, 4) if qty > 0 else 0.0
    pct, frac = _f(s.get("sell_profit_pct")), _f(s.get("sell_fraction_pct"))
    otype = s.get("order_type")   # v2.2.8: 탑쌓기는 하루에 한 층(안 산 칸 전부)을 삼 — max_rounds_per_day(사다리 회차)는 탑쌓기 매수 칸 수에 안 씀
    st = ensure_state(copy.deepcopy(st))                              # 상태·장부를 바꾸지 않음 (사본으로 계산)
    notes, orders = [], []
    profit_pct = round((price / avg - 1) * 100, 2) if avg > 0 and price > 0 else None
    fl_qty, fl_cost = totals(st)
    info = {"mode": "tower", "avg": avg, "qty": qty, "price": price, "fx": fx, "sell_target": 0.0, "profit_pct": profit_pct,
            "filled": [], "levels": [], "rebuy_anchor": None, "rebuy_k": 0,
            "profit_reached": False, "credit_usd": 0.0, "sells": []}
    if qty > 0 and fl_qty != qty:
        notes.append(f"층 합계 {fl_qty}주 ≠ 장부 {qty}주 — 다음 주문일 동기화 때 가장 최근 층이 차이를 흡수해요")

    # ---------------- 매도 (v2.2.6 층별): 각 층이 자기 평단 +pct% 에 닿으면 그 층 보유의 frac%. 여러 층이 같은 날 닿으면 모두 판다.
    # 주문마다 층 id(floor_id)·매도 시점 층 평단(floor_avg) 기록. 층당 하루 1건은 호출한 쪽(main)이 지킴. 총 매도가능 검사는 층 합계 기준
    one_floors = []
    if qty > 0:
        cap_q, taken = min(int(_f(sellable)), qty), 0
        for f in top_down(st):
            fq = int(_f(f.get("qty")))
            if fq <= 0:
                continue
            fa = floor_avg(f)
            tf = ceil2(fa * (1 + pct / 100.0))
            sq = floor_sell_qty(fq, frac)
            row = {"id": int(_f(f.get("id"))), "avg": fa, "target": tf, "qty": fq, "sell_qty": sq, "reached": bool(price > 0 and price >= tf),
                   "pending": bool(f.get("rebuy_pending")), "ordered": False}
            info["sells"].append(row)
            if f.get("rebuy_pending") and not s.get("allow_consecutive_sell"):
                notes.append(f"매도 보류: {row['id']}층은 직전 매도 뒤 이 층 재매수(탑업) 체결이 아직 없음 (allow_consecutive_sell=false)")
            elif fq == 1:                                                  # v2.2.9 audit-fix 7-4: 1주 층은 자동 매도 제외 (알림은 main 이 하루 한 번)
                row["held_one"] = True
                one_floors.append(row["id"])
                notes.append(f"매도 {row['id']}층 보유 1주 — 자동 매도 제외 (보류, 직접 매도해야 팔려요)")
            elif sq < 1:
                notes.append(f"매도 {row['id']}층 {frac:g}% = 0주 (층 보유 {fq}주) — 매도 안 함")
            elif taken + sq > cap_q:
                notes.append(f"매도 {row['id']}층 {sq}주 > 매도가능 {max(cap_q - taken, 0)}주 (총 매도가능 {int(_f(sellable))}/장부 {qty}) — 매도 안 함")
            else:
                taken += sq
                row["ordered"] = True
                orders.append({"side": "SELL", "type": otype, "qty": sq, "price": tf, "kind": "sell", "level": None, "floor_id": row["id"], "floor_avg": fa,
                               "reached": row["reached"], "desc": f"{row['id']}층 평단 ${fa:.2f} +{pct:g}% 매도 {frac:g}%"})
        if one_floors:
            info["sell_excluded"] = {"why": "one_share", "floors": list(one_floors), "qty": 1}
        if info["sells"]:
            info["sell_target"] = min(r["target"] for r in info["sells"])          # 가장 낮은 층의 목표 (제일 먼저 닿음)
            info["profit_reached"] = any(r["reached"] for r in info["sells"])

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
    new_floor, new_floor_blocked = None, None
    room = cap_total - principal
    if active is None:
        have = [f for f in floors if int(_f(f.get("qty"))) > 0]
        if not have:
            notes.append("층 없음 (보유 0주) — 탑쌓기는 기존 보유분을 1층으로 시작해야 해요 (장부 시작 필요)")
        elif room < TOL_USD:
            notes.append(f"총 한도 ${cap_total:,.0f} 도달 (보유 원가 ${principal:,.0f}) — 새 층 없음")
            new_floor_blocked = {"why": "limit", "text": f"총 한도 ${cap_total:,.0f} 에 닿았어요 (보유 원가 ${principal:,.0f})"}
        else:
            anchor = min(floor_avg(f) for f in have)
            tgt = min(fu, room)
            lv, base = _new_floor_band(anchor, gap, tgt)
            if not lv:                                                   # v2.2.9 (풀이님 결정 09:59): 새 층 가격 칸이 하나도 안 나오면 만들지 않고 멈춤 — 알아서 늘리거나 봇을 멈추지 않음
                notes.append(f"새 층을 만들 수 없음 — 기준 평단 ${anchor:.2f} − 간격 ${gap} 아래에 살 수 있는 가격(0 초과)이 없음")
                new_floor_blocked = {"why": "no_price", "text": f"새 층 가격 칸이 없어요 (기준 평단 ${anchor:.2f}, 간격 ${gap} — 모든 칸이 0달러 이하)"}
            else:
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
                     "new_floor": bool(new_floor), "new_floor_blocked": new_floor_blocked, "floors": [{"id": f["id"], "qty": f["qty"], "cost": round(_f(f["cost"]), 2), "avg": floor_avg(f),
                                                              "complete": is_complete(f), "closed": bool(f.get("closed")) or f["id"] in closes,
                                                              "rebuy_pending": bool(f.get("rebuy_pending"))} for f in floors]}

    # ---------------- 칸 금액 (칸당 금액 반올림 · 주식수 반올림 · 못 산 금액은 같은 층 다음 칸에 더함)
    auto_fx = bool(s.get("auto_fx_enabled")) and not ignore_auto_fx
    pool = max(0.0, room if auto_fx else min(_f(usd_cash), room))
    cash_binds = (not auto_fx) and _f(usd_cash) <= room + 1e-9
    info.update({"unit_usd": info.get("unit_usd", 0.0), "cap_usd": round(cap_total, 2), "pool_usd": round(pool, 2)})
    spent, planned, roll = 0.0, 0.0, 0.0
    tgt_active = _f((active or {}).get("target") or fu)
    if active is not None:
        info["tower"]["cells"] = next_layer_cells(active, tgt_active)   # v2.2.3: 다음 회차 가격별 배정 미리보기
    for n, p in enumerate(cand):   # v2.2.8: 안 산 칸 전부 (하루에 한 층)
        is_last = (p == cand[-1])
        carry = _f(active.get("carry_usd")) if n == 0 else 0.0
        if is_last:                                                  # 마지막 칸 = 층에 모자란 만큼 전부 (그날 앞 칸 계획분 제외)
            amount = max(0.0, tgt_active - _f(active.get("cost")) - planned)
        else:
            amount = max(0.0, _f(active["base_usd"]) + carry + roll)
            amount = min(amount, max(0.0, tgt_active - _f(active.get("cost")) - planned))     # v2.2.6 B4: 층 목표를 못 넘게
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


PRICE_TOL = 0.01            # B2: 체결 평균가와 1층 빈칸 가격을 맞춰 볼 때의 허용 오차 (달러)


def _unset_levels(f):
    return sorted(p for p in (f.get("levels") or []) if p not in set(f.get("settled") or []))


def _after_buy(f):
    """매수가 들어간 층의 완성·닫힘 정리 (이 층의 매도 금지는 매수 체결로 풀림 / 닫힐 때도 풂)"""
    f["rebuy_pending"] = False
    if is_complete(f):
        f["done"], f["closed"], f["levels"], f["settled"], f["carry_usd"] = True, False, [], [], 0.0
    elif f["levels"] and all(p in f["settled"] for p in f["levels"]):
        f["closed"] = True                                       # 칸을 다 썼는데 미완성: 부족분(carry_usd)은 그대로 두고 미완성 층으로


def _absorb_into_open_floor(st, order, q, amt):
    """새 층 계획 매수 체결을, 위에 있는 미완성 층(1층)의 안 산 칸에 넣음 → (남은 수량, 남은 금액).
    Muse 검증 고침: 칸 판정은 주문 지정가(order["level"]) 기준 ±0.01 (반올림 허용). 체결 평균가(amt/q)는 원가 계산에만 씀.
    이유: 체결 평균가만으로 칸을 찾으면 지정가 이하로 체결된 주문이 엉뚱한 칸에 들어감 (예: 2층 $42.59 주문이 $42.59에 체결됐는데 1층 $43.59 칸으로 감 — 주문이 노린 칸이 아님).
    지정가 $43.59 주문이 $43.00에 체결돼도 $43.59 칸으로 감 (주문이 노린 칸). B3: 닫으라는 층(closes)은 건너뜀. B4: 층 원가가 목표를 넘지 않게 정수 주 내림으로 상한 — 넘치는 주식은 남은 수량으로 돌려줘 새 층이 받음.
    넣은 직후 칸 금액(base_usd)을 (목표 − 원가) ÷ 안 산 칸 수 로 다시 계산 (B4). B5: 흡수한 가격은 새 층의 settled 가 되도록 st["absorbed"] 에 적어 둠"""
    nf = order.get("new_floor") or {}
    closes = {int(_f(c)) for c in (order.get("closes") or [])}
    lv = round(_f(order.get("level")), 2)
    px = amt / q
    for cand in top_down(st):
        if q <= 0:
            break
        if int(_f(cand.get("qty"))) <= 0 or is_complete(cand) or cand.get("closed") or int(_f(cand.get("id"))) in closes:
            continue
        hit = next((p for p in _unset_levels(cand) if abs(p - lv) <= PRICE_TOL + 1e-9 and px <= p + PRICE_TOL + 1e-9), None)
        if hit is None:
            continue
        n = min(q, int(math.floor((_f(cand.get("target") or FLOOR_USD) - _f(cand.get("cost"))) / px + 1e-9)))
        if n < 1:
            continue
        part = amt if n == q else round(amt * n / q, 4)
        cand["qty"] = int(cand["qty"]) + n
        cand["cost"] = round(_f(cand["cost"]) + part, 4)
        cand.setdefault("settled", []).append(hit)
        _after_buy(cand)
        if not cand.get("done") and not cand.get("closed"):
            left = _unset_levels(cand)
            if left:
                cand["base_usd"] = float(rnd((_f(cand.get("target") or FLOOR_USD) - _f(cand["cost"])) / len(left)))
                cand["carry_usd"] = 0.0
        ab = st.setdefault("absorbed", {}).setdefault(str(int(_f(nf.get("id")))), [])
        if lv not in ab:
            ab.append(lv)
        q -= n
        amt = round(amt - part, 4)
    return q, amt


def _apply_buy(st, order, q, amt):
    f = _by_id(st, order.get("floor_id"))
    nf = order.get("new_floor")
    amt0 = amt
    if f is None and isinstance(nf, dict):                           # 새 층 계획 (그 층은 아직 없음)
        q, amt = _absorb_into_open_floor(st, order, q, amt)          # v2.2.5·v2.2.6: 위에 미완성 층이 있으면 그 층 빈칸 먼저
        if q <= 0:
            return
        f = _floor(nf["id"], 0, 0.0, nf["target"], "build")
        f["levels"], f["base_usd"] = list(nf["levels"]), float(nf["base_usd"])
        f["settled"] = [p for p in (st.get("absorbed") or {}).get(str(int(_f(nf["id"]))), []) if p in f["levels"]]     # B5
        st["floors"].append(f)
        st["next_id"] = max(int(_f(st.get("next_id"))), int(nf["id"]) + 1)
    if f is None:
        return
    f["qty"] = int(f["qty"]) + q
    f["cost"] = round(_f(f["cost"]) + amt, 4)
    lv = round(_f(order.get("level")), 2)
    if lv not in (f.get("settled") or []):
        f.setdefault("settled", []).append(lv)
    f["carry_usd"] = round(_f(f.get("carry_usd")) - _f(order.get("carry_used")) + (_f(order.get("plan_usd")) - amt0), 2)   # 못 산 금액 이월 (계획 대비 — 1층으로 나눠 들어간 몫도 산 것으로 침)
    for cid in order.get("closes") or []:
        c = _by_id(st, cid)
        if c is not None and c is not f:
            c["closed"], c["rebuy_pending"] = True, False            # 닫힌 층의 매도 금지는 닫을 때 전부 푼다 (사용자 결정)
    _after_buy(f)


def _apply_sell(st, order, q, amt, gap, start_usd):
    """매도 체결 반영. 주문에 floor_id 가 있으면 그 층만 (v2.2.6 층별 매도). 없으면(예전 주문) 예전처럼 층별 보유 비율대로.
    잔여 원가 계산에 쓴 '뺀 원가'는 st["_cost_removed"] 에 임시로 둠 (main 이 장부에 같은 값을 쓰고 지움 — 파일에 저장하지 않음)"""
    floors = top_down(st)
    removed, sold = 0.0, []
    tf = _by_id(st, order.get("floor_id")) if order.get("floor_id") is not None else None
    if tf is not None:
        a = min(q, int(_f(tf.get("qty"))))
        if a > 0:
            c = _f(tf.get("cost")) if a == int(tf["qty"]) else _f(tf.get("cost")) * a / int(tf["qty"])
            tf["qty"] = int(tf["qty"]) - a
            tf["cost"] = round(max(0.0, _f(tf["cost"]) - c), 4)
            removed = round(c, 4)
            sold = [tf]
    else:
        qs = [int(_f(f.get("qty"))) for f in floors]
        tq = sum(qs)
        if tq <= 0:
            st["_cost_removed"] = 0.0
            return
        before_cost = sum(_f(f.get("cost")) for f in floors)
        cuts = _largest_remainder(q, qs)
        for f, a in zip(floors, cuts):                               # 층 평단은 그대로 두고 수량·투자금만 줄임
            if a > 0:
                f["qty"] = int(f["qty"]) - a
                f["cost"] = round(max(0.0, _f(f["cost"]) - a * floor_avg_before(f, a)), 4)
                sold.append(f)
        left_q = tq - min(q, tq)
        want = round(before_cost * left_q / tq, 4)                   # 장부와 같은 규칙: 남은 원가 = 이전 원가 × 남은 수량 ÷ 이전 수량
        live = [f for f in floors if int(f["qty"]) > 0]
        if live:
            live[-1]["cost"] = round(_f(live[-1]["cost"]) + (want - sum(_f(f["cost"]) for f in live)), 4)   # 반올림 차이는 가장 최근 층이 흡수
        removed = round(before_cost - want, 4)
    st["floors"] = [f for f in st["floors"] if int(_f(f.get("qty"))) > 0]
    for f in sold:
        if int(_f(f.get("qty"))) > 0:
            _topup_setup(f, gap, start_usd)                          # 팔린 층만 탑업 준비 (v2.2.6)
            f["rebuy_pending"] = not f.get("done")                   # 다시 살 게 없는(완성) 층은 매도 금지를 걸지 않음 — 걸면 풀 매수가 영영 없음
    st["_cost_removed"] = removed


def floor_avg_before(f, a):
    """(예전 주문용 비례 매도) 이미 수량을 줄인 층의 '줄이기 전 평단' = 원가 ÷ (남은 수량 + a)"""
    q = int(_f(f.get("qty"))) + int(a)
    return _f(f.get("cost")) / q if q > 0 else 0.0


def apply_fill(st, order, fill_qty, fill_amount, gap=GAP_USD, start_usd=0.0):
    """체결 1건 반영 (st 를 직접 바꿔 돌려줌). fill_qty = 실제 체결 수량, fill_amount = 실제 체결 금액(수량×체결가 합계). 계획 금액이 아니라 이 값만 씀.
    같은 체결을 또 반영하지 않게 하려면 주문번호 기준인 apply_fill_delta 를 쓸 것 (이 함수는 부른 만큼 그대로 반영)"""
    q, amt = int(_f(fill_qty)), _f(fill_amount)
    kind = order.get("kind")
    if q <= 0 or amt <= 0:
        return st
    ensure_state(st)
    if kind == "buy_tower":
        _apply_buy(st, order, q, amt)
    elif kind == "sell":
        _apply_sell(st, order, q, amt, gap, start_usd)
    return st


def apply_fill_delta(st, order, cum_qty, cum_amount, gap=GAP_USD, start_usd=0.0):
    """v2.2.6 두 번 반영 방지: 주문번호(order["no"]) 별로 '반영한 누적 체결'(st["applied"])을 두고, 누적 체결 중 아직 안 반영한 증분만 반영 → (반영한 수량, 증분 금액).
    같은 누적 체결을 다시 넣으면 (0, 0.0). 부분 체결이 이어서 체결돼 누적이 늘면 늘어난 만큼만. 주문번호가 없으면 중복 방지 불가라 그대로 반영"""
    ensure_state(st)
    no = str(order.get("no") or "").strip()
    cq, ca = int(_f(cum_qty)), _f(cum_amount)
    prev = st["applied"].get(no) if no else None
    pq = int(_f(prev.get("q"))) if isinstance(prev, dict) else 0
    pa = _f(prev.get("amt")) if isinstance(prev, dict) else 0.0
    dq, da = cq - pq, round(ca - pa, 4)
    if dq <= 0 or da <= 0:
        return 0, 0.0
    apply_fill(st, order, dq, da, gap, start_usd)
    if no:
        st["applied"][no] = {"q": cq, "amt": round(ca, 4)}
        while len(st["applied"]) > APPLIED_KEEP:
            st["applied"].pop(next(iter(st["applied"])))
    return dq, da


def applied_qty(st, order):
    """이 주문에서 상태에 이미 반영한 누적 수량 (없으면 0)"""
    prev = (st.get("applied") or {}).get(str(order.get("no") or "").strip())
    return int(_f(prev.get("q"))) if isinstance(prev, dict) else 0


def sort_fills(st, items):
    """v2.2.6 체결 반영 순서 (버그 1·B1). items = [{"o": 주문, "side": "BUY"|"SELL", "t": 체결 시각 글자 또는 None, ...}] → 반영할 순서의 새 목록.
    ① 체결 시각이 전부 있으면 시간순 (같은 시각이면 매도 먼저), 하나라도 없으면 매도를 먼저 (안에서는 원래 순서 유지)
    ② 새 층 계획 매수(그 층이 아직 없는 buy_tower)는 같은 날 매도를 다 반영한 뒤로 미룸 — 매도로 1층이 미완성이 되면 그 매수가 1층 빈칸으로 들어가게 (B1)"""
    ensure_state(st)

    def new_floor_buy(it):
        o = it["o"]
        return o.get("kind") == "buy_tower" and isinstance(o.get("new_floor"), dict) and _by_id(st, o.get("floor_id")) is None

    def order_by(lst):
        if lst and all(str(it.get("t") or "").strip() for it in lst):
            return sorted(lst, key=lambda it: (str(it["t"]).strip(), 0 if it["side"] == "SELL" else 1))
        return sorted(lst, key=lambda it: 0 if it["side"] == "SELL" else 1)

    late = [it for it in items if new_floor_buy(it)]
    return order_by([it for it in items if not new_floor_buy(it)]) + order_by(late)


def apply_fill_to_state(st, order, avg_before=0.0, allow_consecutive_sell=False, fill=None, gap=GAP_USD, start_usd=0.0):
    """반영 입구. fill = (체결 수량, 체결 금액). fill 이 없으면 반영 안 함 (탑쌓기는 실제 체결로만 계산).
    (v2.2.6: 주문번호가 있으면 누적 체결 기준으로 증분만 반영 — 같은 체결을 두 번 넣어도 층이 안 바뀜)"""
    if fill is None:
        return st
    if str(order.get("no") or "").strip():
        apply_fill_delta(st, order, fill[0], fill[1], gap, start_usd)
        return st
    return apply_fill(st, order, fill[0], fill[1], gap, start_usd)


def add_holdings(st, qty, avg, s=None):
    """v2.2.6 (사용자 결정): 토스 등에서 들어온 N주(평단 avg)는 '1층 빈곳'에 넣고, 그 층의 새 평단 기준으로 탑쌓기 로직대로 나머지 빈칸을 채운다.
    위에서부터 처음 미완성 층에 수량·원가를 더함 (미완성 층이 없으면 가장 아래 층 — 매일 동기화가 하는 것과 같음). 층이 없으면 1층을 새로 만듦.
    층이 목표 안에 들어오면 완성, 아니면 탑업 칸(그 층 평단 −1 ~ −간격)·칸 금액을 새 평단으로 다시 정함. → (층 id, 알림 글자 목록)"""
    ensure_state(st)
    fu, _fl, gap = params(s)
    start_usd = _f((s or {}).get("tower_floor1_start_usd"))
    q, a = int(_f(qty)), _f(avg)
    if q < 1 or a <= 0:
        return None, []
    live = [f for f in top_down(st) if int(_f(f.get("qty"))) > 0]
    if not live:
        f = _floor(1, q, q * a, fu, "migrated")
        f["done"] = True
        st["floors"], st["next_id"] = [f], 2
        return 1, [f"층 없음 → 입고 {q}주를 1층으로 만듦 (평단 ${a:.2f})"]
    f = next((x for x in live if not is_complete(x)), live[-1])
    f["qty"] = int(f["qty"]) + q
    f["cost"] = round(_f(f["cost"]) + q * a, 4)
    if is_complete(f):
        f["done"], f["closed"], f["levels"], f["settled"], f["carry_usd"] = True, False, [], [], 0.0
        f["rebuy_pending"] = False
        tail = "1층이 완성돼요" if int(_f(f["id"])) == 1 else "이 층이 완성돼요"
    else:
        _topup_setup(f, gap, start_usd)
        tail = f"남은 빈칸 ${max(_f(f.get('target') or fu) - _f(f['cost']), 0):,.0f} 는 탑쌓기로 매수 (칸 {len(f['levels'])}개)"
    fid = int(_f(f["id"]))
    return fid, [f"입고 {q}주를 {fid}층 빈곳에 넣음 → {fid}층 {int(f['qty'])}주 · 평단 ${floor_avg(f):.2f} · {tail}"]


# ---------------------------------------------------------------- 동기화 · 정리
def _merge(a, b, gap, start_usd=0.0):
    m = _floor(min(int(a["id"]), int(b["id"])), int(a["qty"]) + int(b["qty"]), _f(a["cost"]) + _f(b["cost"]), max(_f(a["target"]), _f(b["target"])), "merged")
    _topup_setup(m, gap, start_usd)
    m["rebuy_pending"] = bool((a.get("rebuy_pending") or b.get("rebuy_pending")) and not m["done"])      # 합쳐도 금지는 이어짐 (다시 살 게 없으면 풂)
    return m


def normalize(st, gap=GAP_USD, start_usd=0.0):
    """수량 0 인 층 정리 → 꼬인 층 합병(위 층보다 평단이 같거나 높으면 가중평균으로 합침) → 평단 오름차순 재배치(id 는 위에서부터 다시 붙임). → 알림 글자 목록"""
    notes = []
    ensure_state(st)
    st["absorbed"] = {}                                              # 새 층 id 는 매일 정리 때 다시 붙으니 하루 지나면 비움 (B5)
    fl = [f for f in top_down(st) if int(_f(f.get("qty"))) > 0]
    out = []
    for f in fl:
        cur = f
        while out and floor_avg(cur) >= floor_avg(out[-1]) - 1e-9:
            top = out.pop()
            notes.append(f"층 합병: {top['id']}층(평단 ${floor_avg(top):.2f}) + {cur['id']}층(평단 ${floor_avg(cur):.2f}) → 수량 {int(top['qty']) + int(cur['qty'])}주")
            cur = _merge(top, cur, gap, start_usd)
        out.append(cur)
    out.sort(key=lambda f: -floor_avg(f))                            # 위(평단 높은 층)부터 번호를 다시 붙임
    for i, f in enumerate(out, 1):
        f["id"] = i
    st["floors"] = sorted(out, key=floor_avg)                        # 저장은 평단 오름차순 (수량·투자금 보존)
    st["next_id"] = len(out) + 1
    return notes


def reconcile(st, qty, principal, gap=GAP_USD, s=None):
    """v2.2.4: 1층 시작가(tower_floor1_start_usd)가 정해졌으면 normalize(합병)에도 넘김"""
    start_usd = _f((s or {}).get("tower_floor1_start_usd"))
    """매일 동기화: 층 합계가 장부(실제 보유분)와 다르면 장부에 맞춤 — 차이는 가장 최근 층(가장 아래 층)이 흡수. 그 뒤 꼬인 층 정리.
    → (st, 알림 글자 목록). 장부가 0주면 층을 비움"""
    fu, _fl, _g = params(s)
    ensure_state(st)
    qty, principal = int(_f(qty)), _f(principal)
    notes = []
    if qty <= 0:
        if st.get("floors"):
            notes.append("장부 0주 — 층 상태를 비움")
        st["floors"], st["next_id"] = [], 1
        return st, notes
    if not st.get("floors"):
        keep = st.get("applied") or {}
        st.update(migrate_from_holdings(qty, principal, s))
        st["applied"] = keep                                          # 반영한 주문번호 기록은 지키지 않으면 같은 체결을 다시 넣을 수 있음
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
    notes += normalize(st, gap, start_usd)
    return st, notes


# ---------------------------------------------------------------- 표시 (v2.2.2, 판 14; v2.2.3 색상 고침)
# 층별 색상 칸: 1층은 초록(🟩)으로 시작, 층마다 다른 색. 10층까지 색이 9개라 10층은 초록으로 돌아감.
# (흰색 █ 한 가지라 층 구분이 안 된다는 사용자 지적 — 텔레그램 글자 색은 이모티콘 네모로만 낼 수 있음.
#  test_v3 의 "코드 안 이모티콘 0줄" 검사는 tg_menu.py·main.py·notifier.py만 보라 tower_strategy.py는 안 건드림.)
LAYER_COLORS = ("🟩", "🟦", "🟨", "🟧", "🟥", "🟪", "🟫", "⬛", "⬜")


def layer_block(f):
    """층 칸 색상: 층 번호로 정함 (1층 🟩)."""
    return LAYER_COLORS[(int(_f(f.get("id"))) - 1) % len(LAYER_COLORS)]


def fill_ratio(f):
    """층 채움 비율 = 원가 ÷ 목표 (0~1)"""
    tg = _f(f.get("target") or FLOOR_USD)
    return min(1.0, max(0.0, _f(f.get("cost")) / tg)) if tg > 0 else 0.0


DIAG_HALF = "◧"           # 미완성 층 한 칸에 그리는 사선 (반만 찬 표시, v2.2.7)


def layer_marker(f):
    """v2.2.7 반칸 표시 (사용자 결정: 2칸 중 1칸이 아니라 한 칸에 사선). 층 하나 = 한 칸.
    완성 → 층 색 (🟩) · 미완성 → 사선 한 칸 (◧)"""
    if is_complete(f):
        return layer_block(f)
    return DIAG_HALF


def floor_status(f):
    """층 상태 글자: 완성 | 미완성 (v2.2.6 — 완성이 아니면 전부 미완성. 예전의 '쌓는 중'은 없앰)"""
    return "완성" if is_complete(f) else "미완성"


def _fmt_layers(total):
    """층 수 표시: 완성 층 1 + 미완성 층은 채움 비율만큼 (v2.2.7). 0.48 → '0.48', 1.5 → '1.5', 2.0 → '2'."""
    s = f"{total:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def view_lines(st, s=None):
    """탑쌓기 층 시각화 글자 줄. 채워진 층(수량 > 0)만 보임 — 비어 있는 층은 안 보임.
    첫 줄: 층마다 한 칸 마커(완성 🟩 · 미완성 ◧ 사선, 색은 1층 🟩 · 2층 🟦 · 3층 🟨 · 4층 🟧 · 5층 🟥 · 6층 🟪 · 7층 🟫 · 8층 ⬛ · 9층 ⬜ · 10층 🟩) + 'N/최대층' (N은 채움 비율 합계, 1층 48%면 0.48).
    다음 줄들: 층별 '1층 · 평단 $48.59 · 149주 · 미완성 (48%)' (위에서부터, % = 원가 ÷ 층 목표).
    평단 = 층 투자금(실제 체결 합계) ÷ 수량 = 가중평균. 상태가 비었거나 이상하면 0층"""
    _fu, nfl, _g = params(s)
    fl = [f for f in top_down(st if isinstance(st, dict) else {}) if int(_f(f.get("qty"))) > 0]
    if not fl:
        return [f"탑: 0/{nfl}층 (채운 층 없음)"]
    total = sum(1.0 if is_complete(f) else fill_ratio(f) for f in fl)
    lines = [f"탑: {' '.join(layer_marker(f) for f in fl)}  {_fmt_layers(total)}/{nfl}층"]
    for f in fl:
        lines.append(f"{int(_f(f.get('id')))}층 · 평단 ${floor_avg(f):.2f} · {int(_f(f.get('qty')))}주 · {floor_status(f)}"
                     + ("" if is_complete(f) else f" ({int(round(fill_ratio(f) * 100))}%)"))
    return lines
