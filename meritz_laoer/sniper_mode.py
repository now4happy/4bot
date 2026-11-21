# ==========================================================
# FILE: meritz_laoer/sniper_mode.py   (MERITZ_LAOER v2.7.0)
# v2.7.0 (2026-11-21, 판 27): 층 간격 설정 제거 — make_plan info에서 'gap' 키 삭제 (계획 미리보기 '새 층 가격' 줄이 없어져서 안 씀). 간격은 내부 고정값 GAP_USD=5로만 씀 (tower_strategy.params).
# v2.6.0 (2026-11-21, 판 26): ① 박스별 매도 — box_rows(박스마다 평단 +1.5%(그 층 안 최저 평단 L1) / +1.0%) · plan_sells 가 닿은 박스만 그 박스 전량 주문(floor_id + box_id) · sell_rows 층 행에 boxes 추가 ② 눌림 매수% = TW.portion_pct(s) (설정 sniper_portion_pct, 기본 8) ③ trigger_lines 박스별 줄 · make_plan info['boxes']
# v2.5.0 (2026-11-21, 판 25 하이브리드 박스·층 — 토스 스나이퍼 이식): ① 매수 = 신호 1번에 박스 시드의 8%(단리 고정, plan_buy: min(8%, 박스 남은 시드) → 13번째가 나머지) ② 새 박스 가격은 신호가 뜰 때 정해짐 — 층 간격(tower_gap_usd)·'새 층 보류' 규칙 삭제, 시초가 상한은 호출한 쪽(main)이 그대로
#   ③ 박스 안 매도(미완성 층 +1.5% 공격 박스 / +1.0% 위 박스, 박스 전체 전량)는 다시 자동 매도 — 판 24 선택 대기(pick_scan·pick_resolve) 코드는 그대로 두고 부르지 않음, plan_buy 도 선택 대기 층을 안 봄
#   ④ 서브 그리드(Case 88) 4% 매수 plan_sub — sub_grid.py ⑤ 첫 기준가 sniper_first_anchor_usd(기준가·층이 없을 때만) ⑥ 지하층 → 공사중 이름 ⑦ 층 표현 = 평단 정수 달러(row["label"])
#   수정1: 돌파 매수액 별도 설정 sniper_breakout_portion_pct(기본 16%, 눌림 8% 그대로).
#   신호 숫자·돌파 RSI·15:30~16:00 돌파 차단·상한 가드(buy_signal)는 그대로.
# v2.4.0 (2026-11-21, 판 24): ① 잠긴 층(locked)은 스나이퍼 매도 안 함 — 탑 매도만 ② 스나이퍼 목표가에 닿아도 자동 매도 안 함: 층마다 선택 대기(picks) → 텔레그램 버튼 '스나이퍼/탑쌓기'(탑쌓기=잠금, 스나이퍼=층 그대로 + 닿은 목표가를 기준가로 하는 새 빈 층). 무응답=대기(탑쌓기 기본), 대기 중 매수 신호가 오면 바로 새 층 매수(다시 안 물음).
#   ③ 지하층(빈 층, 0주·$0) = st["empty"]: 다음 스나이퍼 매수는 빈 층부터 채움.
# v2.3.0 (2026-11-21, 판 23 하이브리드): 모드 선택 없음(trading_mode·get_mode·mode_ko 삭제) — 항상 하이브리드. 사기=스나이퍼만(눌림·돌파), 팔기: 완성 층(층 시드 도달)은 탑 매도(층 평단 +10% → 50%), 미완성 층(재매수 대기 포함)만 스나이퍼 매도.
#   총 시드·층 수 한도 없음. 새 층은 '가장 낮은 층 평단 − 층 간격(tower_gap_usd, 기본 5)' 이하일 때만 만듦. 탑 매도 체결도 스나이퍼 기준가(직전 익절)를 갱신(note_fills 가 모든 SELL 체결을 받음 — 원래부터).
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

import sub_grid as SG
import tower_strategy as TW
from tower_strategy import ceil2

MODE_SNIPER = "sniper"          # 주문 'mode' 표시 글자 (체결 반영이 스나이퍼 매도를 알아봄). 설정으로 고르는 모드는 없음 (v2.3.0)

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


def box_rows(st, s, price):
    """v2.6.0 박스별 익절 행 (미완성 층의 박스만 — 완성·잠긴 층은 탑 매도라 박스별 매도 없음): floor_id·box_id·label(층 표현)·qty·avg(박스 평단)·cost·pct·target(올림 2자리)·role·reached·gain_pct.
    L1(공격 박스) = 그 미완성 층 안에서 평단이 가장 낮은 박스 (같으면 번호가 큰 = 나중에 산 박스) → 평단 +1.5% · 나머지 박스(상단) +1.0%. 층끼리는 비교하지 않음. 계산만 함 (상태 안 바꿈)"""
    tp1, tpu = tp_pcts(s)
    labs = TW.floor_labels(st)
    px = _f(price)
    rows = []
    for f in active_floors(st):
        if TW.is_tower(f):
            continue
        fid = int(_f(f.get("id")))
        bs = sorted(TW.boxes_view(f), key=lambda b: (TW.box_avg(b), -int(b["id"])))
        for i, b in enumerate(bs):
            ba = TW.box_avg(b)
            role = "L1" if i == 0 else "upper"
            pct = tp1 if role == "L1" else tpu
            tg = ceil2(ba * (1 + pct / 100.0))
            rows.append({"floor_id": fid, "box_id": int(b["id"]), "label": labs.get(fid, TW.price_label(TW.floor_avg(f))), "qty": int(b["qty"]), "avg": ba, "cost": round(_f(b["cost"]), 2),
                         "pct": pct, "target": tg, "role": role, "reached": bool(px > 0 and px >= tg), "gain_pct": (round((px / ba - 1) * 100, 2) if px > 0 and ba > 0 else None),
                         "floor_avg": TW.floor_avg(f)})
    return rows


def sell_rows(st, s, price):
    """층마다 익절 행 (미완성 층 = 스나이퍼 익절 %, 완성 층 = 탑 매도 %): id(탑쌓기 층 번호)·no(스나이퍼 층 번호 — 평단 낮은 층이 1)·qty·avg·pct(그 층 익절 %)·target(올림 2자리)·reached·gain_pct(현재가 대비 평단 %)·role(L1|upper)"""
    tp1, tpu = tp_pcts(s)
    aid = attack_id(st)
    nos = sniper_numbers(st)
    labs = TW.floor_labels(st)                                                   # v2.5.0: 층 표현 = 평단 정수 달러
    px = _f(price)
    rows = []
    brows = {}
    for br in box_rows(st, s, price):                                            # v2.6.0: 미완성 층은 박스별 목표 (층 행의 목표·도달 = 그 층 박스 중 가장 먼저 닿는 L1 박스 기준, 도달 = 하나라도 닿음)
        brows.setdefault(br["floor_id"], []).append(br)
    for f in active_floors(st):
        fid, fa = int(_f(f.get("id"))), TW.floor_avg(f)
        role = "L1" if fid == aid else "upper"
        pct = tp1 if role == "L1" else tpu
        if brows.get(fid):
            role, pct = "L1", brows[fid][0]["pct"]
        if TW.is_tower(f):                # v2.4.0: 잠긴 층도 탑 매도 층. 판 23 수정1: 완성 층의 목표는 탑 매도 목표(평단 +sell_profit_pct%) — 스나이퍼 목표가를 '+10% 목표'로 적던 라벨 오류 고침. pct 도 탑 % 로
            pct = _f(s.get("sell_profit_pct"))
        tg = ceil2(fa * (1 + pct / 100.0))
        if brows.get(fid):
            tg = min(r["target"] for r in brows[fid])
        rows.append({"id": fid, "no": nos.get(fid, fid), "label": labs.get(fid, TW.price_label(fa)), "qty": int(_f(f.get("qty"))), "avg": fa, "pct": pct, "target": tg, "role": role,
                     "boxes": brows.get(fid) or [],
                     "reached": bool(px > 0 and px >= tg), "gain_pct": (round((px / fa - 1) * 100, 2) if px > 0 and fa > 0 else None),
                     "complete": TW.is_tower(f), "locked": bool(f.get("locked")), "rebuy": bool(f.get("rebuy_pending")), "cost": round(_f(f.get("cost")), 2), "tgt_usd": _f(f.get("target") or TW.FLOOR_USD)})
    return rows


# ---------------------------------------------------------------- v2.4.0 스나이퍼 가격 선택 (자동 매도 대신 물어봄)
def pick_key(avg):
    return f"{_f(avg):.4f}"


def pick_scan(state, st, s, price):
    """스나이퍼 목표(1층 +1.5% · 상단 +1.0%)에 닿은 '잠기지 않은 미완성 층'을 찾아 선택 대기(picks)에 올림 → 새로 물어볼 층 목록(dict: key·no·avg·qty·target·pct).
    이미 대기 중이면 다시 안 물음. 스나이퍼를 골랐던 층은 현재가가 목표 아래로 내려갔다가 다시 닿을 때만 다시 물음(무장). 없어진 층의 기록은 지움. state 를 바꿈(저장은 호출한 쪽)"""
    picks = state.setdefault("picks", {})
    rows = [r for r in sell_rows(st, s, price) if not r["complete"]]
    live = {pick_key(r["avg"]): r for r in rows}
    for k in [k for k in picks if k not in live]:
        del picks[k]
    asks = []
    px = _f(price)
    for k, r in live.items():
        e = picks.get(k)
        if e is not None and e.get("status") == "sniper" and px > 0 and px < r["target"] - 1e-9:
            del picks[k]
            e = None
        if e is None and r["reached"]:
            picks[k] = {"status": "pending", "target": r["target"], "avg": r["avg"], "qty": r["qty"], "no": r["no"]}
            asks.append({"key": k, "no": r["no"], "avg": r["avg"], "qty": r["qty"], "target": r["target"], "pct": r["pct"], "price": px})
    return asks


def pick_resolve(state, st, key, choice, fu):
    """선택 반영 (버튼). choice='t'(탑쌓기) → 그 층 잠금, 기록 'tower'. choice='s'(스나이퍼) → 층은 그대로, 닿은 목표가를 기준가로 하는 빈 층을 st['empty'] 에 추가, 기록 'sniper'.
    대기 중이 아니면(이미 처리·없어진 층) None. → 알림 글자 또는 None. state(스나이퍼 상태)·st(탑쌓기 상태) 둘 다 바꿈"""
    e = (state.get("picks") or {}).get(key)
    if not isinstance(e, dict) or e.get("status") != "pending":
        return None
    f = next((x for x in TW.top_down(st) if int(_f(x.get("qty"))) > 0 and pick_key(TW.floor_avg(x)) == key), None)
    if f is None:
        state["picks"].pop(key, None)
        return None
    tgt = _f(e.get("target"))
    if choice == "t":
        f["locked"] = True
        e["status"] = "tower"
        return f"탑쌓기 선택 — 평단 ${TW.floor_avg(f):.2f} 층을 잠가 탑 매도(평단 +10% → 50%)로 넘겼어요"
    e["status"] = "sniper"
    st.setdefault("empty", []).append({"kind": "pick", "ref_px": round(tgt, 2), "id": "p" + key})
    return f"스나이퍼 선택 — 평단 ${TW.floor_avg(f):.2f} 층은 그대로 두고, 목표가 ${tgt:.2f} 를 기준가로 하는 새 층을 만들어 스나이퍼 매매를 해요"


def plan_sells(s, st, price, sellable, skip_ids=(), otype="LIMIT", skip_boxes=()):
    """v2.6.0 박스별 매도: 미완성 층의 박스마다 자기 목표(L1 평단 +1.5% · 나머지 +1.0%)에 닿은 박스만 그 박스 전량(100%) 지정가 매도 주문 → (주문 목록, 알림 글자 목록). 완성·잠긴 층은 탑 매도 몫이라 안 냄.
    skip_ids = 이 층 전체를 건너뜀(층 단위 주문이 나가 있음) · skip_boxes = {(층 id, 박스 id)} 이미 이 박스 주문이 나가 있거나 오늘 거절된 박스만 건너뜀.
    매도가능 수량(sellable)이 모자라면 아래층(번호 큰 층)·평단 낮은 박스부터 우선하고 나머지는 보류. 계산만 함 (상태 안 바꿈)"""
    notes, orders, taken = [], [], 0
    cap = max(0, int(_f(sellable)))
    skip = {int(x) for x in skip_ids}
    skipb = {(int(a), int(b)) for a, b in skip_boxes}
    for r in sorted((r for r in box_rows(st, s, price) if r["reached"]), key=lambda r: (-r["floor_id"], r["avg"], -r["box_id"])):
        if r["floor_id"] in skip or (r["floor_id"], r["box_id"]) in skipb:
            continue
        if taken + r["qty"] > cap:
            notes.append(f"매도 {r['label']} 박스 ${r['avg']:.2f} {r['qty']}주 > 매도가능 {max(cap - taken, 0)}주 — 보류")
            continue
        taken += r["qty"]
        orders.append({"side": "SELL", "type": otype, "qty": r["qty"], "price": r["target"], "kind": "sell", "mode": MODE_SNIPER, "level": None,
                       "floor_id": r["floor_id"], "box_id": r["box_id"], "floor_avg": r["floor_avg"], "box_avg": r["avg"], "reached": True,
                       "desc": f"스나이퍼 {r['label']} 박스 평단 ${r['avg']:.2f} +{r['pct']:g}% 전량 매도 (박스별 매도{' · 공격 박스' if r['role'] == 'L1' else ''})"})
    return orders, notes


# ---------------------------------------------------------------- 채우기 (층 사기)
def drop_pct(n_layers):
    """보유 층 수에 따른 눌림 % (음수). 참조 get_golden8_prog_thresholds: 1-4층 -1.0 · 5-8층 -2.0 · 9-10층 -3.5 · 그 위 -5.5"""
    lots = max(1, int(n_layers))
    for hi, pct in PULLBACK_TIERS:
        if lots <= hi:
            return pct
    return PULLBACK_DEEP


def depth_layers(state, n_layers):
    """판 23 수정1 S3: 눌림 깊이를 정할 층 수 = max(지금 층 수, 이번 사이클 최고 층수). 층이 줄어도 눌림 깊이가 완화되지 않음"""
    return max(int(n_layers), int(_f((state or {}).get("peak_layers"))))


def update_peak(state, n_layers, qty):
    """사이클 최고 층수 갱신 (상태 dict 를 바꿈) — 보유 0주(전량 매도로 사이클 끝)면 0 으로 새로 시작, 아니면 최고값만 올림. 바뀌었으면 True"""
    old = int(_f(state.get("peak_layers")))
    new = 0 if int(qty) <= 0 else max(old, int(n_layers))
    state["peak_layers"] = new
    return new != old


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


def anchor_info(st, state, s=None):
    """(기준가, 종류). 저장된 직전 익절/매수가가 있으면 그것, 없으면 가장 아래 활성 층 평단('avg'). 기준가도 층도 없을 때만(v2.5.0) 설정 sniper_first_anchor_usd('first' — 풀이님이 텔레그램 설정에서 정한 첫 기준가).
    첫 매매 체결이 생기면 체결가가 기준가가 됨(note_fills — 토스 anchor_price = fill_p). 모두 없으면 (0.0, '')"""
    a = _f((state or {}).get("anchor"))
    if a > 0:
        return a, str((state or {}).get("anchor_kind") or "exit")
    fl = active_floors(st)
    if fl:
        return min(TW.floor_avg(f) for f in fl), "avg"
    fa = _f((s or {}).get("sniper_first_anchor_usd"))
    if fa > 0:
        return fa, "first"
    return 0.0, ""


def buy_signal(price, anchor, kind, cap_price, n_layers, rsi, late_cutoff):
    """재장전 신호 판정 (참조 evaluate_l2_only_hybrid_reentry_signal 규칙, 순수 계산) → dict(should_buy, signal_type, pullback_price, breakout_price, ...).
    signal_type: NO_PRICE · NO_ANCHOR · HOLD_PREVENT_INVERSION(현재가 > 평단 가장 낮은 층 평단 = Case 73 상한) · PULLBACK_RELOAD · BREAKOUT_RELOAD ·
    HOLD_LATE_SESSION_BREAKOUT_CUTOFF · HOLD_BREAKOUT_RSI_OVER_50 · HOLD_BREAKOUT_RSI_UNKNOWN · HOLD_WAIT_GATE.
    돌파는 기준가가 익절가('exit')이거나 평단 대신 쓴 값('avg')·풀이님이 정한 첫 기준가('first', v2.5.0 — Muse 확인 필요)일 때만 (직전 매수가 기준이면 눌림만 — 추가 매수는 더 눌려야 함)"""
    lp, anc, cap = _f(price), _f(anchor), _f(cap_price)
    drop = drop_pct(n_layers)
    pull = round(anc * (1.0 + drop / 100.0), 2) if anc > 0 else 0.0
    brk = round(anc * (1.0 + BREAKOUT_RISE_PCT / 100.0), 2) if anc > 0 and kind in ("exit", "avg", "first") else 0.0
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


SIGNAL_KO = {"NO_PRICE": "시세 없음", "NO_ANCHOR": "기준가 없음 (텔레그램 설정에서 첫 기준가를 정해 주세요)", "HOLD_PREVENT_INVERSION": "상한 가드 (가장 아래 층 평단 초과)",
             "PULLBACK_RELOAD": "눌림 재장전", "BREAKOUT_RELOAD": "돌파 재장전", "HOLD_LATE_SESSION_BREAKOUT_CUTOFF": "돌파 차단 (15:30~16:00)",
             "HOLD_BREAKOUT_RSI_OVER_50": "돌파 보류 (RSI 50 초과)", "HOLD_BREAKOUT_RSI_UNKNOWN": "돌파 보류 (RSI 모으는 중)", "HOLD_WAIT_GATE": "대기 (눌림·돌파 전)"}


def plan_sub(s, st, price, state, usd_cash, now_et, is_trading_day=None):
    """v2.5.0 서브 그리드(Case 88) 매수 판정 — 본 신호가 없을 때만 부름. 상태·장부를 바꾸지 않음. → {"buy": bool, "tag": 글자, "gate": 열렸으면 {"bucket","date"}(호출한 쪽이 sub 상태에 저장), "info": dict}.
    가동 조건: 층이 있고 (본 그리드 5영업일 무매매 또는 서브 버킷이 이미 있음). 서브 0주 = 첫 진입(15:30~16:00 차단 · 유휴 달러 ≥ max(현재가, 서브 1회 × 0.30)), 서브 있음 = 10분 게이트 · 한도 4회분 · 서브 추매 신호(SG.evaluate_dip).
    유휴 달러 = 예수금 − 본 1회분 × 0.5 (보호예수금). 서브 1회 = 박스 시드 × 4%"""
    sub = SG.norm((state or {}).get("sub"))
    fl = active_floors(st)
    px = _f(price)
    today = now_et.strftime("%Y-%m-%d")
    lots = SG.total_lots(sub["buckets"])
    info = {"lots": lots, "max_lots": SG.SUB_MAX_TOTAL_LOTS, "buckets": [dict(b) for b in sub["buckets"]], "main_frozen_days": SG.business_days_since(sub["last_main_day"], today, is_trading_day),
            "sub_frozen_days": SG.business_days_since(sub["last_sub_day"], today, is_trading_day), "tag": ""}
    out = {"buy": False, "tag": "", "gate": None, "info": info}
    if not fl or px <= 0:
        return dict(out, tag="NO_ACTIVE_SUB_L1", info=dict(info, tag="NO_ACTIVE_SUB_L1"))
    active = bool(sub["buckets"])
    if not active and info["main_frozen_days"] < SG.SUB_FROZEN_DAYS_TRIGGER:
        return dict(out, tag="NO_ACTIVE_SUB_L1", info=dict(info, tag="NO_ACTIVE_SUB_L1"))
    sub_p = TW.sub_portion_usd(s)
    avail = SG.avail_idle_cash(usd_cash, TW.portion_usd(s))
    info["avail_idle_usd"] = avail
    if not active:                                                           # S-A: 서브 0주 첫 진입
        if is_late_cutoff(now_et):
            return dict(out, tag="HOLD_SUB_LATE_SESSION_NEW_CYCLE_CUTOFF", info=dict(info, tag="HOLD_SUB_LATE_SESSION_NEW_CYCLE_CUTOFF"))
        if avail < max(px, sub_p * SG.MIN_DIP_BUDGET_RATIO):
            return dict(out, tag="HOLD_SUB_INSUFFICIENT_IDLE_CASH", info=dict(info, tag="HOLD_SUB_INSUFFICIENT_IDLE_CASH"))
        return dict(out, buy=True, tag="SUB_FIRST_ENTRY", info=dict(info, tag="SUB_FIRST_ENTRY"))
    if lots >= SG.SUB_MAX_TOTAL_LOTS:                                        # S-B2: 한도 4회분
        return dict(out, tag="HOLD_SUB_CAP_4_LOTS_REACHED", info=dict(info, tag="HOLD_SUB_CAP_4_LOTS_REACHED"))
    gate_open, bucket, gday = SG.gate_status(now_et, sub["gate_bucket"], sub["gate_date"])
    if not gate_open:
        return dict(out, tag="HOLD_SUB_GATE", info=dict(info, tag="HOLD_SUB_GATE", gate_open=False))
    gate = {"bucket": bucket, "date": gday}
    drop = drop_pct(max(lots, int(_f(sub.get("ratchet_lots")))))
    ev = SG.evaluate_dip(px, sub["buckets"], sub["anchor"], sub["cycle_min"], drop, info["sub_frozen_days"])
    info.update(eval=ev, gate_open=True, tag=ev["trigger_tag"])
    if not ev["should_buy"]:
        return dict(out, tag="HOLD_SUB_GATE_PASSED", gate=gate, info=info)
    if avail < px:
        return dict(out, tag="HOLD_SUB_INSUFFICIENT_IDLE_CASH", gate=gate, info=dict(info, tag="HOLD_SUB_INSUFFICIENT_IDLE_CASH"))
    return dict(out, buy=True, tag=ev["trigger_tag"], gate=gate, info=info)


def plan_buy(s, st, price, state, rsi, usd_cash, now_et, otype="LIMIT", is_trading_day=None):
    """오늘 재장전 매수 계획 → {"order": 주문 또는 None, "notes", "signal", "target", "sub", "sub_gate"}. 상태·장부를 바꾸지 않음.
    v2.5.0 사는 금액 = min(신호 1번 몫, 그 박스의 남은 시드): 몫 = 박스 시드(tower_box_seed_usd, 기본 $15,000)의 8% (돌파 신호는 sniper_breakout_portion_pct, 기본 16%=$2,400 · 서브 신호는 4%) — 단리 고정. 시드 $15,000 이면 $1,200씩 12번, 13번째에 남은 $600 (13번은 정한 횟수가 아니라 계산 결과).
    채울 박스 = 빈 층(공사중, st["empty"]) → 위에서부터 첫 미완성 층(공사중) → 새 박스(시드 = 박스 시드). 새 박스 가격은 신호 가격 (층 간격 규칙 없음). 신호 한 번에 1회분만 (여러 회분 한 번에 안 삼).
    주식수는 정수 내림(시드를 안 넘김), 달러 예수금이 모자라면 살 수 있는 만큼만. 주문 가격 = 현재가 (지정가). 본 신호가 없고 서브 신호가 나면 서브 4% (out["sub"])"""
    fu, _nfl, _gap = TW.params(s)
    box, portion = TW.box_seed(s), TW.portion_usd(s)
    fl = active_floors(st)
    n = len(fl)
    px = _f(price)
    labs = TW.floor_labels(st)
    anchor, kind = anchor_info(st, state, s)
    cap = min((TW.floor_avg(f) for f in fl), default=0.0)
    sig = buy_signal(px, anchor, kind, cap, depth_layers(state, n), rsi, is_late_cutoff(now_et))
    out = {"order": None, "notes": [], "signal": sig, "target": None, "sub": None, "sub_gate": None}
    chosen = None
    cands = [{"empty_id": e.get("id"), "ref": _f(e.get("ref_px")), "kind": e.get("kind")} for e in (st.get("empty") or []) if isinstance(e, dict)]      # 판 24 선택 대기(picks)는 v2.5.0 에서 안 봄
    for c in cands:
        sg = buy_signal(px, c["ref"], "exit", 0.0, depth_layers(state, n), rsi, is_late_cutoff(now_et)) if c["ref"] > 0 else sig
        if not sg["should_buy"]:
            continue
        chosen, sig = c, sg
        out["signal"] = sg
        break
    is_sub, per, per_pct, tag = False, portion, TW.portion_pct(s), sig["signal_type"]
    if tag == "BREAKOUT_RELOAD":                                               # v2.5.0 수정1: 돌파 매수액은 별도 설정 (기본 16%), 눌림은 설정 sniper_portion_pct (v2.6.0, 기본 8%)
        per, per_pct = TW.breakout_portion_usd(s), TW.breakout_portion_pct(s)
    if chosen is None and not sig["should_buy"]:
        sp = plan_sub(s, st, px, state, usd_cash, now_et, is_trading_day)
        out["sub"], out["sub_gate"] = sp, sp.get("gate")
        if not sp["buy"]:
            return out
        is_sub, per, per_pct, tag = True, TW.sub_portion_usd(s), TW.SUB_PORTION_PCT, sp["tag"]
    inc = next((f for f in fl if not TW.is_complete(f)), None) if chosen is None else None
    if chosen is not None or inc is None:
        nid = max(int(_f(st.get("next_id"))), max((int(_f(f.get("id"))) for f in TW.top_down(st)), default=0) + 1)
        remaining = box
        fid, nf = nid, {"id": nid, "target": round(box, 2), "indep": bool(chosen and chosen["ref"] > 0)}
        label = "공사중 박스" if chosen is not None else "새 박스"
    else:
        fid, nf = int(_f(inc.get("id"))), None
        remaining = max(0.0, _f(inc.get("target") or fu) - _f(inc.get("cost")))
        label = f"{labs.get(fid, TW.price_label(TW.floor_avg(inc)))} 공사중"
    amount = round(min(per, remaining), 2)
    q = int(math.floor(amount / px + 1e-9)) if px > 0 else 0
    cash = _f(usd_cash)
    if q * px > cash + 1e-9:
        q = int(math.floor(cash / px + 1e-9)) if cash > 0 else 0
        out["notes"].append(f"달러 예수금 ${cash:,.0f} 만큼만 매수 (필요 ${amount:,.0f})")
    if q < 1:
        out["notes"].append(f"매수 못 함 — {label} ${amount:,.0f} 로 1주(${px:.2f})도 못 삼 (예수금 ${cash:,.0f})")
        return out
    out["target"] = {"floor_id": fid, "amount": round(amount, 2), "label": label, "remaining": round(remaining, 2), "last_portion": bool(amount >= remaining - 1e-9), "portion_pct": per_pct}
    desc = (f"서브 그리드 {SG.SUB_TAG_KO.get(tag, tag)} · {label} ${amount:,.0f} (박스 시드 {per_pct:g}%)" if is_sub
            else f"스나이퍼 {SIGNAL_KO.get(tag, tag)} · {label} ${amount:,.0f} (박스 시드 {per_pct:g}%{' · 마지막 회차(남은 시드)' if amount >= remaining - 1e-9 and remaining < per - 1e-9 else ''} · 기준 ${sig['anchor']:.2f} {sig['chg_pct']:+.2f}%)")
    out["order"] = {"side": "BUY", "type": otype, "qty": q, "price": round(px, 2), "kind": "buy_sniper", "mode": MODE_SNIPER, "level": None,
                    "floor_id": fid, "new_floor": nf, "plan_usd": round(amount, 2), "signal": tag, "sub": bool(is_sub), "portion_pct": per_pct, "box_seed": round(box, 2),
                    "empty_id": (chosen or {}).get("empty_id"), "pick_key": None, "desc": desc}
    return out


def tower_sells(s, st, price, sellable, skip_ids=()):
    """v2.3.0 탑 매도: 완성 층만, 층 평단 +sell_profit_pct%(기본 10) 에 닿으면 그 층 보유의 sell_fraction_pct%(기본 50, 1주 층 제외). 목표에 닿은 층만 주문 → (주문 목록, 알림 글자 목록, 층별 행).
    TW.make_plan(sell_only, complete_only) 의 매도 계산을 그대로 씀 (계산만 — 상태 안 바꿈)"""
    q, _p = TW.totals(st)
    plan = TW.make_plan(s, st, q, _p, _f(price), 0.0, 0.0, sellable, complete_only=True, sell_only=True)
    skip = {int(x) for x in skip_ids}
    nos = sniper_numbers(st)
    tpp, tfr = _f(s.get("sell_profit_pct")), _f(s.get("sell_fraction_pct"))
    orders = [dict(o, mode="tower", desc=f"탑 매도 {nos.get(int(o['floor_id']), o['floor_id'])}층(완성) 평단 ${o['floor_avg']:.2f} +{tpp:g}% → 보유의 {tfr:g}%")
              for o in plan["orders"] if o.get("reached") and int(o["floor_id"]) not in skip]
    return orders, plan["notes"], plan["info"].get("sells") or []


def make_plan(s, st, price, state, rsi, usd_cash, sellable, now_et, otype=None, is_trading_day=None, skip_sell_ids=(), skip_sell_boxes=()):
    """오늘(지금) 하이브리드 계획 미리보기 — {"orders","notes","info"}. 상태·장부를 바꾸지 않음. 상황판·--check·텔레그램 오늘 계획용.
    주문 = 박스 안 매도(미완성 층, v2.5.0 자동) + 탑 매도(완성 층) + 스나이퍼 매수(본 8% 또는 서브 4%)"""
    otype = otype or s.get("order_type") or "LIMIT"
    sells, snotes = plan_sells(s, st, price, max(0, int(_f(sellable))), skip_ids=skip_sell_ids, otype=otype, skip_boxes=skip_sell_boxes)     # v2.6.0: 박스별 매도 자동 (판 24 선택 대기 폐기)
    taken = sum(int(o["qty"]) for o in sells)
    tsells, tnotes, trows = tower_sells(s, st, price, max(0, int(_f(sellable)) - taken), skip_ids=skip_sell_ids)
    buy = plan_buy(s, st, price, state, rsi, usd_cash, now_et, otype=otype, is_trading_day=is_trading_day)
    orders = list(sells) + [dict(o, type=otype) for o in tsells] + ([buy["order"]] if buy["order"] else [])
    fl = active_floors(st)
    q, principal = TW.totals(st)
    avg = round(principal / q, 4) if q > 0 else 0.0
    rows = sell_rows(st, s, price)
    fu, _nfl, _gap = TW.params(s)
    info = {"mode": MODE_SNIPER, "price": _f(price), "avg": avg, "qty": q, "profit_pct": (round((_f(price) / avg - 1) * 100, 2) if avg > 0 and _f(price) > 0 else None),
            "sells": rows, "boxes": box_rows(st, s, price), "sell_target": min((r["target"] for r in rows), default=0.0), "profit_reached": any(r["reached"] for r in rows),
            "signal": buy["signal"], "buy_target": buy["target"], "n_layers": len(fl), "depth_layers": depth_layers(state, len(fl)), "floor_usd": fu, "tower_sells": trows,
            "tower_pct": [_f(s.get("sell_profit_pct")), _f(s.get("sell_fraction_pct"))],
            "hits": [{"no": r["no"], "avg": r["avg"], "target": r["target"], "pending": (((state or {}).get("picks") or {}).get(pick_key(r["avg"])) or {}).get("status") == "pending"}
                     for r in rows if r["reached"] and not r["complete"]],                       # v2.4.0: 목표에 닿은 스나이퍼 층 (자동 매도 없음 — 선택 대기 중이면 pending)
            "empty": [dict(e) for e in (st.get("empty") or []) if isinstance(e, dict)],
            "sub": (buy.get("sub") or {}).get("info"), "sub_buy": bool(buy["order"] and buy["order"].get("sub")), "box_seed": TW.box_seed(s), "portion_usd": TW.portion_usd(s), "sub_portion_usd": TW.sub_portion_usd(s),
            "fill": next(({"no": r["no"], "label": r["label"], "ratio": round(r["cost"] / r["tgt_usd"], 4) if r["tgt_usd"] else 0.0, "cost": r["cost"], "target": r["tgt_usd"], "rebuy": r["rebuy"]}
                          for r in sorted(rows, key=lambda r: r["id"]) if not r["complete"]), None),      # 채우는 층(위에서부터 첫 미완성 층)의 채움률 = 원가 ÷ 층 시드 (총 시드가 아니라 층 시드 기준)
            "tp_l1": tp_pcts(s)[0], "tp_upper": tp_pcts(s)[1], "attack_id": attack_id(st), "rsi": rsi, "usd_cash": round(_f(usd_cash), 2),
            "need_usd": round(buy["order"]["qty"] * buy["order"]["price"], 2) if buy["order"] else 0.0}
    return {"orders": orders, "notes": snotes + tnotes + buy["notes"], "info": info}


# ---------------------------------------------------------------- 체결 뒤 기준가 갱신
def note_fills(state, done, now_iso=""):
    """체결 반영 결과(done = apply_tower_fills 가 돌려준 목록)로 기준가를 갱신: 매도 체결 → 스나이퍼 매도는 그 체결 평균가, 탑 매도(mode tower)는 매도한 층의 평단 (직전 익절가, 'exit'), 매수(본) 체결 → 그 체결 평균가('buy').
    v2.5.0: 서브 그리드 매수(o["sub"]) 체결은 기준가를 안 바꾸고 서브 버킷에만 넣음(last_sub_day). 본 매수·매도 체결은 last_main_day 를 오늘로(서브 가동 '5영업일 무매매' 기준).
    done 은 반영한 순서 그대로라 마지막 체결이 기준이 됨. 바뀌었으면 True"""
    changed = False
    day = str(now_iso or "")[:10]
    for a in done or []:
        dq, da = int(_f(a.get("dq"))), _f(a.get("da"))
        if dq <= 0 or da <= 0:
            continue
        if a.get("side") != "SELL" and (a.get("o") or {}).get("kind") != "buy_sniper":
            continue                                             # 탑쌓기 매수는 스나이퍼 기준가를 안 바꿈 (직전 익절가 유지)
        o = a.get("o") or {}
        if a.get("side") != "SELL" and o.get("sub"):             # v2.5.0 서브 그리드 매수: 기준가·본 무매매 날짜는 그대로
            sub = SG.norm(state.get("sub"))
            sub["buckets"], _m = SG.add_lot(sub["buckets"], dq, da)
            px = da / dq
            sub["anchor"] = round(min(_f(sub["anchor"]) or px, px), 4)
            sub["cycle_min"] = round(min(_f(sub["cycle_min"]) or px, px), 4)
            sub["last_sub_day"] = day or sub["last_sub_day"]
            sub["ratchet_lots"] = max(int(_f(sub.get("ratchet_lots"))), SG.total_lots(sub["buckets"]))
            state["sub"] = sub
            changed = True
            continue
        if day:
            sub = SG.norm(state.get("sub"))
            sub["last_main_day"] = day
            state["sub"] = sub
        if a.get("side") == "SELL" and o.get("mode") == "tower" and _f(o.get("floor_avg")) > 0:
            state["anchor"] = round(_f(o.get("floor_avg")), 4)           # v2.3.0 판 23: 탑 매도 체결 → 매도한 층의 평단(주문에 적힌 매도 시점 층 평단)이 기준가
        else:
            state["anchor"] = round(da / dq, 4)                          # 스나이퍼 매도·매수 체결은 그대로: 그 체결 평균가
        state["anchor_kind"] = "exit" if a.get("side") == "SELL" else "buy"
        state["anchor_at"] = now_iso
        changed = True
    return changed


def mark_sub_gate(state, plan_sub_result):
    """서브 주문을 낸 틱의 10분 게이트 기록 (같은 10분 구간 재주문 방지). 바뀌었으면 True"""
    g = (plan_sub_result or {}).get("gate")
    if not g:
        return False
    sub = SG.norm(state.get("sub"))
    sub["gate_bucket"], sub["gate_date"] = g["bucket"], g["date"]
    state["sub"] = sub
    return True


def sync_sub(state, held_qty):
    """서브 버킷 수량을 실제 보유 주수에 맞춤 (매도로 줄면 위 칸부터 감소). 매 틱 부름. 바뀌었으면 True"""
    sub = SG.norm(state.get("sub"))
    nb = SG.sync_qty(sub["buckets"], int(_f(held_qty)))
    if nb != sub["buckets"]:
        sub["buckets"] = nb
        if not nb:
            sub["anchor"], sub["cycle_min"], sub["ratchet_lots"] = 0.0, 0.0, 0
        state["sub"] = sub
        return True
    return False


def trigger_lines(s, st, state, now_et=None):
    """체결 알림·상황판용 '다음 매매' 글자: 층별 다음 매도(목표가·수량) + 다음 매수 타점(눌림/돌파·기준·상한). 상태는 안 바꿈"""
    lines = []
    tpp, tfr = _f((s or {}).get("sell_profit_pct")), _f((s or {}).get("sell_fraction_pct"))
    for r in sorted(sell_rows(st, s, 0.0), key=lambda r: r["no"])[:6]:
        if r["complete"]:              # v2.3.0 완성 층 = 탑 매도 (층 평단 +sell_profit_pct% 에 보유의 sell_fraction_pct%)
            sq = TW.floor_sell_qty(r["qty"], tfr)
            lines.append(f"다음 매도: {r['label']}(완성·탑) 평단 ${r['avg']:.2f} → 목표가 ${ceil2(r['avg'] * (1 + tpp / 100.0)):.2f} 에 " + (f"{sq}주 ({tfr:g}%)" if sq >= 1 else "자동 매도 없음 (1주 층)") + f" (+{tpp:g}%)")
            continue
        bxs = r.get("boxes") or []                                  # v2.6.0: 미완성 층은 박스별 다음 매도 (박스 하나씩 전량)
        for b in bxs[:4]:
            lines.append(f"다음 매도: {r['label']} 공사중 박스 평단 ${b['avg']:.2f} → 목표가 ${b['target']:.2f} 에 {b['qty']}주 전량 (+{b['pct']:g}%{' · 공격 박스' if b['role'] == 'L1' else ''})")
        if len(bxs) > 4:
            lines.append(f"다음 매도: {r['label']} 그 위 {len(bxs) - 4}개 박스는 같은 규칙")
    fl = active_floors(st)
    anchor, kind = anchor_info(st, state, s)
    cap = min((TW.floor_avg(f) for f in fl), default=0.0)
    if anchor > 0:
        sig = buy_signal(0.0, anchor, kind, cap, depth_layers(state, len(fl)), None, False)
        lines.append(f"다음 매수: 눌림 ${sig['pullback_price']:.2f} ({sig['drop_pct']:+.1f}%)" + (f" / 돌파 ${sig['breakout_price']:.2f} (RSI {BREAKOUT_MAX_RSI:g} 이하)" if sig["breakout_price"] > 0 else "")
                     + f" · 기준 ${anchor:.2f}" + (f" · 상한 ${cap:.2f}" if cap > 0 else ""))
    else:
        lines.append("다음 매수: 기준가 없음 (텔레그램 설정에서 첫 기준가를 정해 주세요)")
    return lines


# ---------------------------------------------------------------- 상태 파일 (cfg = ConfigManager: _load_json·_save_json 재사용)
def new_state():
    return {"version": 1, "anchor": 0.0, "anchor_kind": "", "anchor_at": "", "last_order_ts": 0.0, "buy_block_until": 0.0, "peak_layers": 0, "series": [], "picks": {}, "sub": SG.new_sub()}


def load_state(cfg):
    d = cfg._load_json(SNIPER_FILE, None)
    if not isinstance(d, dict):
        return new_state()
    base = new_state()
    base.update({k: v for k, v in d.items() if k in base})
    if not isinstance(base.get("series"), list):
        base["series"] = []
    if not isinstance(base.get("picks"), dict):
        base["picks"] = {}
    base["sub"] = SG.norm(base.get("sub"))
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
