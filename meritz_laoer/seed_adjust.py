# seed_adjust.py — v2.9.0 6차 (2026-11-22, 판 33): 잔고 동기화의 둘째 일 = F 완성 기준 금액 조정
# 잔고 동기화 = (1) 잔고 대조(TW.reconcile) + (2) F 완성 기준 금액 조정(이 파일). 순수 계산 — 주문·API·파일을 안 만지고, F 상태(st)만 바꿈.
# 규칙 (판 33 지시):
#   · 시드가 커지면 다 채워졌던 F 도 새 시드까지 다시 채움 — 높은 F(평단 높은 F)부터 먼저. 모자란 만큼은 아래 F·미완성 F가 들고 있던 주식을 가져와 합침.
#   · 아래 F 가 합쳐도 안 차면 미완성 F 로 남음 (그때 매매 모드가 스나이퍼면 버킷으로, 탑쌓기면 탑쌓기 칸으로 이어감). 합쳐서 차면 완성으로 인식.
#   · 시드가 줄면 같은 보유 주식을 더 작은 F·더 작은 버킷(버킷 = 시드 8%)으로 다시 나눔 → F·버킷이 늘어남. 평단은 다시 계산.
# 주식 수·원금 합계는 절대 안 바뀜 (다시 나누기만 함). 합계가 어긋나면 아무것도 안 바꾸고 알림만.
# 기준 시드 기록: 상태(st)의 seed_sig = [F 완성 기준 금액, 버킷 시드]. 기록이 없으면(처음) 지금 값을 기록만 하고 안 바꿈 — 배포 순간 옛 F가 멋대로 다시 나뉘지 않게.
import tower_strategy as TW

TOL = TW.TOL_USD


def _f(v):
    return TW._f(v)


def sig_of(s):
    """(F 완성 기준 금액, 버킷 시드) — F 완성 기준 금액은 F 완성 기준(tower_floor_usd), 버킷 시드는 버킷 크기의 바탕(tower_box_seed_usd)"""
    return [float(TW.params(s)[0]), float(TW.box_seed(s))]


def _lots(st):
    """높은 F 부터 주식 덩어리 [(주, 원가)]. 미완성 F(버킷 있음)은 버킷 평단 높은 순, 완성 F는 F 전체 1덩어리"""
    out = []
    for f in TW.top_down(st):
        if int(_f(f.get("qty"))) <= 0:
            continue
        if TW.is_tower(f):
            out.append((int(f["qty"]), _f(f["cost"])))
        else:
            bs = sorted(TW.boxes_view(f), key=lambda b: -TW.box_avg(b))
            out += [(int(b["qty"]), _f(b["cost"])) for b in bs]
    return out


def _take(lots, need):
    """lots 맨 앞에서 원가 need 달러어치 주식을 가져옴 (정수 주). → (가져온 [(주, 원가)], 남은 lots)"""
    got, lots = [], list(lots)
    left = need
    while lots and left > TOL:
        q, c = lots[0]
        p = c / q
        n = min(q, max(1, int(round(left / p))))
        cost = c if n == q else round(c * n / q, 4)
        got.append((n, cost))
        left -= cost
        lots[0] = (q - n, round(c - cost, 4))
        if lots[0][0] <= 0:
            lots.pop(0)
    return got, lots


def _split_boxes(st, lots, portion):
    """미완성 F의 주식 덩어리들을 버킷으로 나눔: 버킷 하나 ≈ portion 달러 (마지막은 남은 몫)"""
    boxes, cur_q, cur_c = [], 0, 0.0
    for q, c in lots:
        p = c / q
        while q > 0:
            room = portion - cur_c
            n = q if room <= 0 else min(q, max(1, int(round(room / p))))
            cost = c if n == q else round(c * n / q, 4)
            cur_q, cur_c, q, c = cur_q + n, cur_c + cost, q - n, round(c - cost, 4)
            if cur_c >= portion - p / 2:
                boxes.append({"id": TW.next_box_id(st), "qty": cur_q, "cost": round(cur_c, 4), "ono": ""})
                cur_q, cur_c = 0, 0.0
    if cur_q > 0:
        boxes.append({"id": TW.next_box_id(st), "qty": cur_q, "cost": round(cur_c, 4), "ono": ""})
    return boxes


def _snapshot(st):
    return [(int(f["id"]), int(_f(f["qty"])), _f(f["cost"]), TW.floor_avg(f), TW.is_complete(f), len(TW.boxes_view(f)) if not TW.is_tower(f) else 0) for f in TW.top_down(st) if int(_f(f.get("qty"))) > 0]


def adjust(st, s):
    """F 완성 기준 금액 조정. 시드(sig)가 안 바뀌었으면 아무것도 안 함. → (st, 알림 글자 목록)"""
    TW.ensure_state(st)
    cur = sig_of(s)
    old = st.get("seed_sig")
    if not (isinstance(old, list) and len(old) == 2):
        st["seed_sig"] = cur                                  # 처음: 기록만
        return st, []
    if [float(old[0]), float(old[1])] == cur:
        return st, []
    tq, tc = TW.totals(st)
    if tq <= 0:
        st["seed_sig"] = cur
        return st, []
    fu, _nfl, gap = TW.params(s)
    portion = TW.portion_usd(s)
    tower_mode = TW.trade_mode(s) == "tower"
    start_usd = _f((s or {}).get("tower_floor1_start_usd"))
    before = _snapshot(st)
    lots = _lots(st)
    new = []
    while lots:
        got, lots = _take(lots, fu)
        if not got:
            break
        new.append(got)
    # 새 F 만들기 (높은 F 부터 번호). 마지막 F 가 시드에 못 미치면 미완성
    floors = []
    for i, got in enumerate(new, 1):
        q, c = sum(g[0] for g in got), sum(g[1] for g in got)
        f = TW._floor(i, q, c, fu, "seed_adjust")
        if c >= fu - TOL:
            f["done"] = True
        else:
            TW._topup_setup(f, gap, start_usd)                # 탑쌓기 칸(levels·base_usd) — 탑쌓기 매매면 이 칸으로 이어서 채움
            if not tower_mode:
                f["boxes"] = _split_boxes(st, got, portion)    # 스나이퍼 매매면 버킷으로 이어감
        floors.append(f)
    nq, nc = sum(f["qty"] for f in floors), round(sum(f["cost"] for f in floors), 4)
    if nq != tq or abs(nc - tc) > 0.05:
        return st, [f"F 완성 기준 금액 조정 중단: 다시 나눈 합계({nq}주·${nc:,.2f})가 장부 합계({tq}주·${tc:,.2f})와 달라 아무것도 안 바꿨어요 (확인 필요)"]
    floors.sort(key=TW.floor_avg)
    st["floors"] = floors
    st["next_id"] = len(floors) + 1
    for i, f in enumerate(sorted(floors, key=lambda x: -TW.floor_avg(x)), 1):
        f["id"] = i
    st["seed_sig"] = cur
    return st, report(before, _snapshot(st), old, cur, portion, tower_mode)


def report(before, after, old, cur, portion, tower_mode):
    """텔레그램 글자: 시드·F 크기 변화, F 별 평단 변화, 늘어난 버킷"""
    lines = [f"F 완성 기준 금액 조정: F 완성 기준 금액 ${old[0]:,.0f} → ${cur[0]:,.0f} · 버킷 시드 ${old[1]:,.0f} → ${cur[1]:,.0f} (버킷 시드의 8% = ${portion:,.0f})"]
    lines.append(f"F 개수 {len(before)}개 → {len(after)}개 (주식 {sum(b[1] for b in before)}주 그대로)")
    rank = {b[0]: n + 1 for n, b in enumerate(sorted(after, key=lambda b: (b[3], -b[0])))}  # 스나이퍼 번호 (평단 오름차순)
    for fid, q, c, a, done, nb in after:
        was = next((b for b in before if b[0] == fid), None)
        tail = f"(전 {was[1]}주 · 평단 ${was[3]:,.2f})" if was else "(새 F)"
        state = "완성" if done else f"미완성 · 채움 ${c:,.0f} · " + (f"버킷 {nb}개" if not tower_mode else "탑쌓기 칸으로 이어감")
        lines.append(f"· {int(a)}F{rank[fid]} {q}주 · 평단 ${a:,.2f} {tail} · {state}")
    added = [b for b in after if not any(b[0] == x[0] for x in before)]
    if len(after) > len(before):
        lines.append(f"늘어난 F: {', '.join(f'{int(b[3])}F{rank[b[0]]}' for b in added)}")
    bn_old = sum(b[5] for b in before)
    bn_new = sum(b[5] for b in after)
    if bn_new != bn_old:
        lines.append(f"미완성 F 의 버킷: {bn_old}개 → {bn_new}개 ({bn_new - bn_old:+d})")
    return lines
