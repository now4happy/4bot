# ==========================================================
# FILE: meritz_laoer/accum_strategy.py   (MERITZ_LAOER v2.0.6)
# v2.0.6 (2026-11-19, 판 8): 버전 표기만 올림 — staging 에 빠진 v2.0.4 파일(notifier·tg_menu·accum_strategy)을 v2.0.5 main·meritz_api 와 한 묶음으로 맞춤 (ImportError 해소). 코드 로직 변경 없음
# v2.0.4 (2026-11-19): 현금 부분 매수 — 달러 예수금이 한 회차에 모자라면 그 회차를 통째로 건너뛰지 않고 현금으로 살 수 있는 만큼만(정수 주 내림, 0주면 안 삼) 매수.
#   총 투자금 한도가 막는 경우는 예전대로 건너뜀. 부분 매수한 회차는 체결되면 '채운 회차'로 침(남은 주수는 이월·재시도 없음).
# (v2.0.0 새 파일)
# 메리츠 속쓸 적립봇 — SOXL 분할매수·부분매도 계획 (순수 계산: 파일·네트워크·시계 없음)
# 규칙 (노션 작업 페이지 '메리츠 속쓸 적립봇', 2026-11-18):
#   매수 사다리: $50 부터 $5 내려갈 때마다 1/10 (회차당 총 투자금/10, 매수가 $50~$5 10회)
#   매도: 평단 대비 평가 이익 +10% 에 보유의 50% 매도
#   매도 뒤: 매도 시점 평단 대비 $5 내려갈 때마다 다시 1/10 씩 매수 (재매수 모드)
# 노션에서 아직 안 정해진 값은 기본값 없이 설정 필수 (CHOICES) → 비어 있으면 validate_settings 가 막음
# 상태(state): {"mode": "ladder"|"rebuy", "filled_levels": [..], "armed": bool,
#              "rebuy_anchor": float|None, "rebuy_k": int, "sell_block": bool,
#              "credit_usd": float}   # 1회차 매수 때 한 번 차감할 달러 (기존 보유분 — 사용자 요청 2026-11-18)
# ==========================================================
import math

# 사람이 정해야 하는 값 (노션 질문 Q1·Q2·Q5) — 허용 값 목록
CHOICES = {
    "unit_base": ("total", "cash"),          # Q2: 재매수 1/10 기준 (총 투자금 1/10 고정 | 남은 현금 ÷ 10)
    "first_buy_mode": ("now", "wait_top"),   # Q1: 시작가 아래에서 시작할 때 (바로 매수 | 맨 위 레벨을 본 뒤 매수)
    "order_type": ("LOC", "LIMIT"),          # Q5: 주문 방식 (종가 조건 | 당일 지정가)
}


def _f(v):
    try:
        x = float(str(v if v is not None else 0).replace(",", ""))
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def ceil2(x):
    return math.ceil(round(_f(x) * 100, 6)) / 100.0


def ladder_levels(top, step, rounds):
    """매수 사다리 가격 (큰 값부터). 0 이하는 만들지 않음"""
    out = []
    for i in range(int(rounds)):
        p = round(_f(top) - _f(step) * i, 2)
        if p > 0:
            out.append(p)
    return out


def state_from_start(start):
    """설정 start → 처음 상태. filled_levels·mode 는 사람이 정한 값 (추정하지 않음)"""
    st = start or {}
    mode = st.get("mode") if st.get("mode") in ("ladder", "rebuy") else "ladder"
    return {"mode": mode,
            "filled_levels": sorted({round(_f(x), 2) for x in (st.get("filled_levels") or [])}, reverse=True),
            "armed": False,
            "rebuy_anchor": (round(_f(st.get("rebuy_anchor_usd")), 4) if _f(st.get("rebuy_anchor_usd")) > 0 else None),
            "rebuy_k": int(_f(st.get("rebuy_k"))),
            "sell_block": False,
            "credit_usd": round(max(0.0, _f(st.get("first_round_credit_usd"))), 2)}


def make_plan(s, st, qty, principal, price, fx, usd_cash, sellable, ignore_auto_fx=False):
    """오늘 낼 주문 계산 → {"orders": [...], "notes": [...], "info": {...}}. 상태·장부를 바꾸지 않음.
    s: 설정, st: 상태, qty/principal: 장부(주·달러), price: 현재가, fx: 메리츠 적용환율(매수, 원/달러),
    usd_cash: USD 예수금, sellable: 매도가능 수량.
    자동환전이 켜져 있으면(ignore_auto_fx=False) 달러 예수금이 아니라 한도(총 투자금)까지 계획하고, 필요달러·부족달러를 info 에 담는다"""
    qty, principal, price = int(_f(qty)), _f(principal), _f(price)
    avg = round(principal / qty, 4) if qty > 0 else 0.0
    rounds = int(_f(s.get("split_count")))
    top, step, drop = _f(s.get("ladder_top_usd")), _f(s.get("ladder_step_usd")), _f(s.get("rebuy_drop_usd"))
    pct, frac = _f(s.get("sell_profit_pct")), _f(s.get("sell_fraction_pct"))
    otype, per_day = s.get("order_type"), int(_f(s.get("max_rounds_per_day")))
    levels = ladder_levels(top, step, rounds)
    notes, orders = [], []
    mode = st.get("mode", "ladder")
    filled = {round(_f(x), 2) for x in st.get("filled_levels") or []}
    target = ceil2(avg * (1 + pct / 100.0)) if qty > 0 else 0.0
    profit_pct = round((price / avg - 1) * 100, 2) if avg > 0 and price > 0 else None
    info = {"mode": mode, "avg": avg, "qty": qty, "price": price, "fx": fx, "sell_target": target,
            "profit_pct": profit_pct, "filled": sorted(filled, reverse=True), "levels": levels,
            "rebuy_anchor": st.get("rebuy_anchor"), "rebuy_k": int(_f(st.get("rebuy_k"))),
            "profit_reached": bool(qty > 0 and target > 0 and price >= target)}

    # ---------------- 매도: 평단 +pct% 에 보유 frac% (정수 주 내림)
    if qty > 0:
        sell_qty = int(math.floor(qty * frac / 100.0 + 1e-9))
        if st.get("sell_block") and not s.get("allow_consecutive_sell"):
            notes.append("매도 보류: 직전 매도 뒤 재매수 체결이 아직 없음 (allow_consecutive_sell=false)")
        elif sell_qty < 1:
            notes.append(f"매도 {frac:g}% = 0주 (보유 {qty}주) — 매도 안 함")
        elif sell_qty > min(int(_f(sellable)), qty):
            notes.append(f"매도 {sell_qty}주 > 매도가능 {int(_f(sellable))}/장부 {qty} — 매도 안 함")
        else:
            orders.append({"side": "SELL", "type": otype, "qty": sell_qty, "price": target, "kind": "sell", "level": None,
                           "desc": f"평단 ${avg:.2f} +{pct:g}% 매도 {frac:g}%"})

    # ---------------- 매수 후보 가격
    if not (fx and fx > 0):
        notes.append("환율 없음 — 매수 계획 불가 (매도만)")
        return {"orders": orders, "notes": notes, "info": info}
    armed = bool(st.get("armed")) or price >= top
    if mode == "rebuy":
        anchor, k = _f(st.get("rebuy_anchor")), int(_f(st.get("rebuy_k")))
        if anchor <= 0:
            notes.append("재매수 기준 평단(rebuy_anchor) 없음 — 매수 안 함")
            cand = []
        else:
            cand = [(round(anchor - drop * (k + 1 + i), 2), k + 1 + i) for i in range(per_day)]
            cand = [(p, j) for p, j in cand if p > 0]
    else:
        cand = [(p, None) for p in levels if p not in filled]
        if s.get("first_buy_mode") == "wait_top" and not filled and not armed:
            notes.append(f"시작 대기: 현재가 ${price:.2f} < 맨 위 ${top:g} — ${top:g} 이상을 본 뒤부터 매수 (first_buy_mode=wait_top)")
            cand = []
        cand = cand[:per_day]
    if not cand and mode == "ladder" and levels and all(p in filled for p in levels):
        notes.append(f"사다리 {len(levels)}회차 모두 체결 — 매수 없음")

    # ---------------- 회차 금액 (정수 주 내림, 남는 돈 이월 없음)
    cap_usd = _f(s.get("total_krw")) / fx                       # 총 투자금 한도 (달러 환산, 주문 시점 환율)
    auto_fx = bool(s.get("auto_fx_enabled")) and not ignore_auto_fx
    cap_room = cap_usd - principal
    pool = max(0.0, cap_room if auto_fx else min(_f(usd_cash), cap_room))   # 이번에 쓸 수 있는 달러
    cash_binds = (not auto_fx) and _f(usd_cash) <= cap_room + 1e-9         # 모자란 쪽이 한도가 아니라 현금이면 부분 매수 (v2.0.4)
    if mode == "rebuy" and s.get("unit_base") == "cash":
        unit = pool / rounds
    else:
        unit = (_f(s.get("total_krw")) / rounds) / fx
    credit = max(0.0, _f(st.get("credit_usd"))) if mode == "ladder" else 0.0
    info.update({"unit_usd": round(unit, 2), "cap_usd": round(cap_usd, 2), "pool_usd": round(pool, 2), "credit_usd": round(credit, 2)})
    spent = 0.0
    for n, (p, j) in enumerate(cand):
        use_credit = credit if (n == 0 and credit > 0) else 0.0     # 1회차(첫 사다리 매수) 한 번만 차감
        amount = unit - use_credit
        q = int(math.floor(amount / p + 1e-9)) if amount > 0 else 0
        if q < 1:
            notes.append(f"회차 금액 ${unit:,.2f}" + (f" − 기존 보유 차감 ${use_credit:,.2f}" if use_credit else "")
                         + f" = ${max(amount, 0):,.2f} < 1주(${p:.2f}) — 생략" + (" (차감액은 그대로 남음)" if use_credit else ""))
            continue
        cost = q * p
        if spent + cost > pool + 1e-9:
            room = pool - spent
            if cash_binds:                                      # v2.0.4 부분 매수: 현금으로 살 수 있는 만큼만 (정수 주 내림)
                pq = int(math.floor(room / p + 1e-9)) if room > 0 else 0
                if pq >= 1:
                    orders.append({"side": "BUY", "type": otype, "qty": pq, "price": p, "kind": "buy_rebuy" if mode == "rebuy" else "buy_ladder",
                                   "level": p if mode == "ladder" else None, "idx": j, "credit": round(use_credit, 2),
                                   "partial": True, "full_qty": q,
                                   "desc": (f"재매수 {j}번째 (평단 ${_f(st.get('rebuy_anchor')):.2f} −${drop * j:g})" if mode == "rebuy"
                                            else f"사다리 ${p:g} 회차" + (f" (기존 보유 −${use_credit:,.2f} 차감)" if use_credit else ""))
                                   + f" · 현금만큼 부분 매수 (원래 {q}주)"})
                    spent += pq * p
                    info["partial"] = {"price": p, "qty": pq, "full_qty": q}
                    notes.append(f"현금 부족 — ${p:.2f} 회차 {q}주 중 {pq}주만 부분 매수 (필요 ${cost:,.2f} > 가용 ${room:,.2f}, "
                                 f"나머지 {q - pq}주는 이월·재시도 없음)")
                else:
                    notes.append(f"현금 부족 — 가용 ${max(room, 0):,.2f} < 1주(${p:.2f}) — 이 회차 안 삼")
            else:
                notes.append(f"{'한도' if auto_fx else '달러 또는 한도'} 부족 (필요 ${spent + cost:,.2f} > 가용 ${pool:,.2f}) — ${p:.2f} 회차부터 생략")
            break
        spent += cost
        orders.append({"side": "BUY", "type": otype, "qty": q, "price": p, "kind": "buy_rebuy" if mode == "rebuy" else "buy_ladder",
                       "level": p if mode == "ladder" else None, "idx": j, "credit": round(use_credit, 2),
                       "desc": (f"재매수 {j}번째 (평단 ${_f(st.get('rebuy_anchor')):.2f} −${drop * j:g})" if mode == "rebuy"
                                else f"사다리 ${p:g} 회차" + (f" (기존 보유 −${use_credit:,.2f} 차감)" if use_credit else ""))})
    info["need_usd"] = round(spent, 2)                              # 오늘 매수 주문이 다 체결될 때 드는 달러 (한도가 아니라 주문가 기준 최대치)
    info["usd_cash"] = round(_f(usd_cash), 2)
    info["shortfall_usd"] = round(max(0.0, spent - _f(usd_cash)), 2)
    info["auto_fx"] = auto_fx
    return {"orders": orders, "notes": notes, "info": info}


def apply_fill_to_state(st, order, avg_before, allow_consecutive_sell=False):
    """체결 1건 뒤 상태 갱신 (st 를 직접 바꿔 돌려줌). avg_before = 이 체결을 장부에 넣기 전 평단"""
    kind = order.get("kind")
    if kind == "buy_ladder":
        lv = round(_f(order.get("level")), 2)
        fl = {round(_f(x), 2) for x in st.get("filled_levels") or []}
        fl.add(lv)
        st["filled_levels"] = sorted(fl, reverse=True)
        st["armed"] = True
        st["sell_block"] = False
        if _f(order.get("credit")) > 0:                  # 차감은 1회차 체결 때 한 번만 쓰고 지움
            st["credit_usd"] = 0.0
    elif kind == "buy_rebuy":
        st["rebuy_k"] = max(int(_f(st.get("rebuy_k"))), int(_f(order.get("idx"))))
        st["sell_block"] = False
    elif kind == "sell":
        st["mode"] = "rebuy"
        st["rebuy_anchor"] = round(_f(avg_before), 4)
        st["rebuy_k"] = 0
        st["sell_block"] = True
    return st
