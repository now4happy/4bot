# -*- coding: utf-8 -*-
# ==========================================================
# FILE: meritz_laoer/grid_tiers.py   (v1.4.4 — 판 37 후속: 원작 Case 113 층 태그·7층 상한·합병 이식)
# 원작 quant_engine.vrev_add_quota_lot_and_merge_2tier · quant_engine_core.relabel_upper_grid_tiers (7718e29, L2_L7_MERGE_SORT) 를
# '합병 때 어느 버킷이 합쳐졌는지(members)'를 같이 들고 다니게 그대로 옮긴 순수 계산 모듈 (원작 import 없음 — 탑쌓기 장부(tower_strategy)가 불러 씀).
# 원작과 같은지는 test_hybrid_v370.py 가 원작 함수와 무작위 매수열로 대조함.
# 버킷(dict) = {"qty", "cost", "price"(= 원가/수량, 소수 4자리), "tag", "members"[장부 버킷 키 목록]}.  태그: GRID_L1 = 1층 · GRID_L2..GRID_L7 = 상단층 (7번째 칸에 합병분이 모임).
# 하이브리드 장부에는 합병된 버킷도 따로따로 남기고(주문 단위가 버킷이라서) 같은 태그(= 같은 층)를 달아 한 층으로 봄 (group_by_tag).
# ==========================================================
MAX_GRID_TIERS_7 = 7
L1_TAG = "GRID_L1"
EPS = 1e-6


def tier_no(tag):
    """GRID_L3 → 3. 알 수 없으면 0"""
    t = str(tag or "").upper().strip()
    if t.startswith("GRID_L") and t[6:].isdigit():
        return int(t[6:])
    return 0


def is_upper_tag(tag):
    """원작 is_upper_grid_tier (본 그리드): MERGED_UPPER 또는 GRID_L2 이상"""
    t = str(tag or "").upper().strip()
    return t == "MERGED_UPPER" or (t.startswith("GRID_L") and t != L1_TAG)


def has_l1(buckets):
    v = [b for b in buckets if b["qty"] > 0]
    return bool(v) and not is_upper_tag(v[0]["tag"])


def is_vacant_l2(uppers):
    """상단 목록 맨 앞이 GRID_L3~L7 이면 2층 공석 (원작 is_vacant_l2_upper_slice)"""
    v = [b for b in uppers if b["qty"] > 0]
    return bool(v) and str(v[0]["tag"]).upper().strip() in ("GRID_L3", "GRID_L4", "GRID_L5", "GRID_L6", "GRID_L7")


def mk(qty, cost, tag, members):
    qty = int(qty)
    cost = round(float(cost), 4)
    return {"qty": qty, "cost": cost, "price": round(cost / qty, 4) if qty > 0 else 0.0, "tag": tag, "members": list(members)}


def relabel(upper_buckets, max_tiers=MAX_GRID_TIERS_7, preserve_vacant_l2=None):
    """원작 relabel_upper_grid_tiers (merge_mode = L2_L7_MERGE_SORT). 입력은 평단 오름차순 상단 목록. 합병하면 members 가 합쳐짐"""
    valid = [dict(b) for b in upper_buckets if b["qty"] > 0]
    if not valid:
        return []
    eff = max(2, int(max_tiers))
    vacant = (is_vacant_l2(valid) and eff >= 3) if preserve_vacant_l2 is None else (bool(preserve_vacant_l2) and eff >= 3)
    start = 3 if vacant else 2
    max_upper = max(1, eff - (start - 1))
    while len(valid) > max_upper:
        if len(valid) >= 3:
            kept = [valid[0]]
            low_b, high_b = valid[1], valid[-1]
            mid = valid[2:-1]
            m_qty = low_b["qty"] + high_b["qty"]
            m_cost = round(low_b["cost"] + high_b["cost"], 4)
            overall = (low_b["qty"] * low_b["price"] + high_b["qty"] * high_b["price"]) / float(max(1, m_qty))
            raw = max(0.01, m_cost / float(max(1, m_qty)))
            capped = round(min(raw, overall), 4)
            merged = {"qty": m_qty, "cost": m_cost, "price": capped, "tag": f"GRID_L{eff}", "members": low_b["members"] + high_b["members"]}
            valid = kept + mid + [merged]
            valid.sort(key=lambda b: round(b["price"], 4))
        else:                                                   # 원작 else 가지 (len < 3): 넘친 칸을 전부 한 칸으로
            kept = valid[: max_upper - 1]
            over = valid[max_upper - 1:]
            t_q = sum(b["qty"] for b in over)
            t_c = round(sum(b["cost"] for b in over), 4)
            overall = sum(b["qty"] * b["price"] for b in over) / float(max(1, t_q))
            raw = max(0.01, t_c / float(max(1, t_q)))
            capped = round(min(raw, overall), 4)
            merged = {"qty": t_q, "cost": t_c, "price": capped, "tag": f"GRID_L{eff}", "members": [m for b in over for m in b["members"]]}
            valid = kept + [merged]
    out = []
    for idx, b in enumerate(valid):
        tno = min(eff, idx + start)
        pure_cost = round(max(0.01 * b["qty"], b["cost"]), 4)
        pure_p = round(max(0.01, pure_cost / b["qty"]), 4)
        out.append({"qty": b["qty"], "cost": pure_cost, "price": pure_p, "tag": f"GRID_L{tno}", "members": list(b["members"])})
    return out


def add_lot(queue, new_key, qty, cost, max_tiers=MAX_GRID_TIERS_7):
    """원작 vrev_add_quota_lot_and_merge_2tier (lot_type='QUOTA_L1' 새 매수, 마중물·탑업 가지 없음) → 새 큐 (앞 = 1층, 뒤 = 상단층 평단 오름차순).
    queue = 지금 큐(원작 순서) 버킷 목록, new_key = 새 장부 버킷 키"""
    q = max(1, int(qty))
    spent = round(max(0.01, float(cost)), 4)
    pure_p = round(max(0.0001, spent / q), 4)
    new_l1 = {"qty": q, "cost": spent, "price": pure_p, "tag": L1_TAG, "members": [new_key]}
    existing = [dict(b) for b in queue if b["qty"] > 0]
    if not existing:
        return [new_l1]
    eff = max(2, int(max_tiers))
    if not has_l1(existing):
        if pure_p <= existing[0]["price"] + EPS:
            return [new_l1] + relabel(existing, eff)
        comb = existing + [new_l1]
        comb.sort(key=lambda b: round(b["price"], 4))
        return relabel(comb, eff)
    if eff <= 2:                                                # 원작: 2층 한도면 기존 전부 한 칸으로 (하이브리드는 7 고정이라 안 탐 — 원작 그대로 둠)
        t_q = sum(b["qty"] for b in existing)
        t_c = round(sum(b["cost"] for b in existing), 4)
        overall = sum(b["qty"] * b["price"] for b in existing) / float(t_q)
        capped = round(min(t_c / float(t_q), overall), 4)
        return [new_l1, {"qty": t_q, "cost": t_c, "price": capped, "tag": "GRID_L2", "members": [m for b in existing for m in b["members"]]}]
    if pure_p > existing[0]["price"] + EPS:
        comb = existing + [new_l1]
        comb.sort(key=lambda b: round(b["price"], 4))
        lowest = dict(comb[0])
        if is_upper_tag(lowest["tag"]):
            lowest["tag"] = L1_TAG
        return [lowest] + relabel(comb[1:], eff)
    return [new_l1] + relabel(existing, eff, preserve_vacant_l2=False)


def group_by_tag(items):
    """장부 버킷 목록 [{"key", "qty", "cost", "lot_type"}] (큐 순서 아님) → 큐 순서 버킷 목록 (태그 번호 순, 같은 태그 = 합병된 한 층). 태그 없는/모르는 게 하나라도 있으면 None"""
    rows = [x for x in items if int(x["qty"]) > 0]
    if not rows or any(tier_no(x.get("lot_type")) <= 0 for x in rows):
        return None
    groups = {}
    for x in rows:
        groups.setdefault(tier_no(x["lot_type"]), []).append(x)
    out = []
    for n in sorted(groups):
        g = sorted(groups[n], key=lambda x: (round(float(x["cost"]) / int(x["qty"]), 4), str(x["key"])))
        out.append(mk(sum(int(x["qty"]) for x in g), sum(float(x["cost"]) for x in g), f"GRID_L{n}", [x["key"] for x in g]))
    return out


def bootstrap(items):
    """태그 없는 예전 버킷 → 지금 동적 규칙(평단 오름차순, 가장 싼 것 = 1층)으로 처음 태그를 붙인 큐"""
    rows = sorted((x for x in items if int(x["qty"]) > 0), key=lambda x: (round(float(x["cost"]) / int(x["qty"]), 4), str(x["key"])))
    bs = [mk(x["qty"], x["cost"], "GRID_L2", [x["key"]]) for x in rows]
    if not bs:
        return []
    return [dict(bs[0], tag=L1_TAG)] + relabel(bs[1:])


def tags_on_buy(existing_items, new_key, qty, cost, max_tiers=MAX_GRID_TIERS_7):
    """새 매수 한 건이 들어올 때 모든 버킷의 새 태그 {키: 태그}. existing_items = 지금 큐 안 장부 버킷 [{"key","qty","cost","lot_type"}] (태그 없는 게 있으면 bootstrap)"""
    q = group_by_tag(existing_items)
    if q is None:
        q = bootstrap(existing_items)
    out = {}
    for b in add_lot(q, new_key, qty, cost, max_tiers):
        for k in b["members"]:
            out[k] = b["tag"]
    return out
