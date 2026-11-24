# ==========================================================
# FILE: meritz_laoer/sub_grid.py   (MERITZ_LAOER v2.5.0)
# v2.11.0 (2026-11-24, 판 38): gate_status 의 시작 시각을 09:30 → 04:07 로 (원작 매수 창 04:07~16:00 에 맞춤). 버킷 번호 계산식·16:00 마감봉 72 는 그대로
# v2.5.0 (2026-11-21, 판 25): 새 파일 — 토스 서브 그리드(Case 88)의 판정·장부 계산을 가져온 순수 계산부 (네트워크·시계·파일 없음. 시각·거래일 판정은 호출한 쪽이 넘김).
#   근거(토스 기준 파일, 로직은 그대로·숫자만 설정 가능):
#   - toss_quant_engine.py evaluate_sub_grid_dip_signal (SUB_STATIC_NEW_LOW · SUB_UNLOCK_10D_D10 · HOLD_SUB_CAP_4_LOTS_REACHED) → evaluate_dip
#   - toss_quant_engine.py relabel_sub_upper_grid_tiers_with_flag · add_lot_to_sub_grid_with_flag (SUB_L1_L3_MERGE: 4번째 층이 생기면 구 1층 + 구 3층을 양끝 합병) → add_lot · _relabel_uppers
#   - toss_quant_engine.py compute_sub_grid_available_idle_cash (본 그리드 0.5회분 보호예수금 차감) → avail_idle_cash
#   - toss sniper_plugin.py _execute_sub_grid_buy_engine_plugin: 본 그리드 5영업일 무매매(또는 서브 가동 중)에 작동 · 서브 0주 첫 진입(S-A) · 10분 게이트 추매(S-B2, 04:07 ET 기점 10분 버킷, 버킷당 한 번 판정)
#     (10분 게이트 버킷 식 = toss_sniper/quant_indicators_plugin.py evaluate_buy_gate_bucket_status 의 mins_from_0407 // 10 — 저장소 파일 기준, 노션 첨부본 해시 대조는 안 함)
#   메리츠 이식에서 달라진 점 (VERIFY.md '미확인·차이' 참고): 서브 버킷은 별도 계좌 장부가 아니라 '버킷(층) 안에 들어간 매수의 기록(memo)' — 매도는 버킷 안 매도 규칙(버킷 전체)을 따름.
#   서브 수량 기록은 보유 주수보다 클 수 없게 sync 가 위쪽(높은 가격) 버킷부터 깎음. 수수료율 보정(fee_mult)은 안 씀(메리츠 근거 파일에 없음).
# 상태(sub): {"buckets": [{"qty", "cost", "lots"} ... 평단 오름차순, [0] = 서브 1층(가장 낮은 가격)], "anchor", "cycle_min", "last_main_day": ISO, "last_sub_day": ISO, "gate_bucket": int, "gate_date": ISO, "ratchet_lots": int}
# ==========================================================
import datetime
import math

SUB_PORTION_PCT = 4.0                 # 서브 1회 = 버킷 시드의 4% (SUB_PORTION_RATIO_4PCT)
SUB_MAX_TIERS = 3                     # 서브 그리드 최대 3층 (SUB_MAX_TIERS_3)
SUB_MAX_TOTAL_LOTS = 4                # 최대 4회분 = 16% (SUB_MAX_TOTAL_LOTS_4)
SUB_RESERVE_MAIN_PORTIONS = 0.5       # 본 그리드 0.5회분(= 시드의 4%)을 보호예수금으로 뗌 (SUB_RESERVE_MAIN_PORTIONS)
SUB_FROZEN_DAYS_TRIGGER = 5           # 본 그리드 5영업일 무매매면 서브 가동 (SUB_FROZEN_DAYS_TRIGGER)
SUB_UNLOCK_FROZEN_DAYS = 10           # 서브 10영업일 무매매 + 서브 1층 대비 -10% 저가 해금 (SUB_UNLOCK_FROZEN_DAYS_10)
SUB_UNLOCK_DROP_PCT = 10.0            # (SUB_UNLOCK_DROP_FROM_L1_PCT)
MIN_DIP_BUDGET_RATIO = 0.30           # 서브 첫 진입 최소 예수금 = max(현재가, 서브 1회 × 0.30) (MIN_DIP_BUDGET_RATIO)
GATE_INTERVAL_MIN = 10                # 10분 고정 게이트 (LOCKED_BUY_INTERVAL_MIN)
GATE_START_MIN_OF_DAY = 4 * 60 + 7    # 04:07 ET 기점
MERGE_MODE = "SUB_L1_L3_MERGE"


def _f(v):
    try:
        x = float(str(v if v is not None else 0).replace(",", ""))
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def new_sub():
    return {"buckets": [], "anchor": 0.0, "cycle_min": 0.0, "last_main_day": "", "last_sub_day": "", "gate_bucket": -1, "gate_date": "", "ratchet_lots": 0}


def norm(sub):
    """상태 모양 보정 (이상하면 새 상태). 버킷은 수량 1주 이상만, 평단 오름차순"""
    if not isinstance(sub, dict):
        return new_sub()
    base = new_sub()
    base.update({k: v for k, v in sub.items() if k in base})
    bl = []
    for b in base.get("buckets") or []:
        if isinstance(b, dict) and int(_f(b.get("qty"))) > 0 and _f(b.get("cost")) > 0:
            bl.append({"qty": int(_f(b["qty"])), "cost": round(_f(b["cost"]), 4), "lots": max(1, int(_f(b.get("lots")) or 1))})
    base["buckets"] = sorted(bl, key=bprice)
    return base


def bprice(b):
    q = int(_f(b.get("qty")))
    return round(_f(b.get("cost")) / q, 4) if q > 0 else 0.0


def total_lots(buckets):
    return sum(max(1, int(_f(b.get("lots")))) for b in buckets or [] if int(_f(b.get("qty"))) > 0)


def total_qty(buckets):
    return sum(int(_f(b.get("qty"))) for b in buckets or [])


# ---------------------------------------------------------------- 영업일·게이트
def business_days_since(day_iso, today_iso, is_trading_day=None):
    """day_iso 다음 날부터 today_iso 까지의 거래일 수 (둘 중 하나가 비면 0 = 모름 → 서브를 안 깨움). is_trading_day(date) 가 없으면 주말만 뺌"""
    if not day_iso or not today_iso:
        return 0
    try:
        a, b = datetime.date.fromisoformat(str(day_iso)[:10]), datetime.date.fromisoformat(str(today_iso)[:10])
    except ValueError:
        return 0
    chk = is_trading_day or (lambda d: d.weekday() < 5)
    n, d = 0, a + datetime.timedelta(days=1)
    while d <= b and n < 400:
        if chk(d):
            n += 1
        d += datetime.timedelta(days=1)
    return n


def gate_status(now_et, last_bucket, last_date):
    """10분 게이트 (04:07 ET 기점 버킷 = (분 − 04:07) // 10, 16:00 마감봉 72). 판 38: 매수 창이 원작처럼 04:07~16:00 이라 그 밖이면 닫힘 (예전 09:30~16:00).
    → (열림, 지금 버킷 id, 오늘 글자). 같은 날 같은 버킷은 한 번만 판정 (열림 = 버킷이 바뀌었을 때)"""
    today = now_et.strftime("%Y-%m-%d")
    hm = now_et.hour * 100 + now_et.minute
    if hm < 407 or hm > 1600:
        return False, -1, today
    mins = max(0, now_et.hour * 60 + now_et.minute - GATE_START_MIN_OF_DAY)
    cur = 72 if hm == 1600 else int(mins // GATE_INTERVAL_MIN)
    return (not (int(_f(last_bucket)) == cur and str(last_date or "") == today)), cur, today


# ---------------------------------------------------------------- 버킷 장부 (SUB_L1_L3_MERGE)
def _relabel_uppers(uppers, max_tiers=SUB_MAX_TIERS):
    """서브 1층 위의 상단 버킷이 max_tiers − 1 개를 넘으면 양끝(가장 낮은 것 + 가장 높은 것)을 가중평균으로 합침 (SUB_L1_L3_MERGE). 합친 평단은 원가÷수량(평균 장부가 이하로 제한), 오름차순 재배치. → (목록, 합병했는지)"""
    valid = [dict(b) for b in uppers or [] if int(_f(b.get("qty"))) > 0]
    cap = max(1, int(max_tiers) - 1)
    did = False
    while len(valid) > cap:
        did = True
        if len(valid) >= 3:
            low, high, mid = valid[0], valid[-1], valid[1:-1]
            m = {"qty": int(low["qty"]) + int(high["qty"]), "cost": round(_f(low["cost"]) + _f(high["cost"]), 4), "lots": max(1, int(low.get("lots") or 1)) + max(1, int(high.get("lots") or 1))}
            valid = sorted(mid + [m], key=bprice)
        else:                                            # 상단이 2개뿐인데 cap 이 1 이면 둘을 합침
            m = {"qty": sum(int(b["qty"]) for b in valid), "cost": round(sum(_f(b["cost"]) for b in valid), 4), "lots": sum(max(1, int(b.get("lots") or 1)) for b in valid)}
            valid = [m]
    return valid, did


def add_lot(buckets, qty, cost):
    """체결된 서브 매수 1건(수량 qty·원가 cost)을 서브 버킷에 넣음 (add_lot_to_sub_grid_with_flag 의 SUB_DIP_1FL 경로) → (새 목록, 합병했는지).
    서브 활성 1층보다 비싸면 승격 없이 위 칸으로 · 같거나 싸면 새 1층 (옛 1층~3층이 상단이 돼 3층 초과 시 양끝 합병)"""
    q, c = int(_f(qty)), _f(cost)
    if q <= 0 or c <= 0:
        return [dict(b) for b in buckets or []], False
    new = {"qty": q, "cost": round(c, 4), "lots": 1}
    existing = sorted([dict(b) for b in buckets or [] if int(_f(b.get("qty"))) > 0], key=bprice)
    if not existing:
        return [new], False
    if bprice(new) > bprice(existing[0]) + 1e-6:
        comb = sorted(existing + [new], key=bprice)
        uppers, did = _relabel_uppers(comb[1:])
        return [comb[0]] + uppers, did
    uppers, did = _relabel_uppers(existing)
    return [new] + uppers, did


def sync_qty(buckets, held_qty):
    """서브 기록 수량이 보유 주수보다 크면 위쪽(높은 가격) 버킷부터 깎음. 보유 0이면 비움 → 새 목록"""
    held = max(0, int(_f(held_qty)))
    out = [dict(b) for b in sorted(buckets or [], key=bprice) if int(_f(b.get("qty"))) > 0]
    over = total_qty(out) - held
    while over > 0 and out:
        top = out[-1]
        if int(top["qty"]) <= over:
            over -= int(top["qty"])
            out.pop()
        else:
            avg = _f(top["cost"]) / int(top["qty"])
            top["qty"] = int(top["qty"]) - over
            top["cost"] = round(avg * top["qty"], 4)
            over = 0
    return out


# ---------------------------------------------------------------- 돈
def avail_idle_cash(usd_cash, main_portion_usd, reserve_mult=SUB_RESERVE_MAIN_PORTIONS):
    """서브가 쓸 수 있는 달러 = 예수금 − 본 그리드 보호예수금(본 1회분 × 0.5). 0 아래로는 안 내려감 (compute_sub_grid_available_idle_cash)"""
    return round(max(0.0, _f(usd_cash) - _f(main_portion_usd) * max(0.0, _f(reserve_mult))), 4)


# ---------------------------------------------------------------- 신호
def evaluate_dip(live_price, buckets, anchor, cycle_min, drop_buy_pct, frozen_days=0, max_total_lots=SUB_MAX_TOTAL_LOTS,
                 unlock_days=SUB_UNLOCK_FROZEN_DAYS, unlock_drop_pct=SUB_UNLOCK_DROP_PCT):
    """서브 추매 신호 (evaluate_sub_grid_dip_signal 포팅). trigger_tag: NO_ACTIVE_SUB_L1 · HOLD_SUB_CAP_4_LOTS_REACHED · NO_LIVE_PRICE · SUB_STATIC_NEW_LOW(서브 기억 저가 대비 drop_buy_pct 이하) ·
    SUB_UNLOCK_10D_D10(서브 10영업일 무매매 & 서브 1층 대비 -10% 이하) · HOLD_SUB_GATE"""
    valid = sorted([b for b in buckets or [] if int(_f(b.get("qty"))) > 0], key=bprice)
    lp, anc, cmin = _f(live_price), _f(anchor), _f(cycle_min)
    req_drop = _f(drop_buy_pct) if drop_buy_pct is not None else -1.0
    cap = max(1, int(_f(max_total_lots)))
    need_days = max(1, int(_f(unlock_days)))
    udrop = max(1.0, _f(unlock_drop_pct))
    lots = total_lots(valid)
    base = {"should_buy": False, "is_sub_unlock": False, "sub_cur_total_lots": lots, "sub_max_total_lots": cap}
    if not valid:
        return dict(base, trigger_tag="NO_ACTIVE_SUB_L1", ref_static_anchor=round(cmin if cmin > 0 else lp, 4))
    l1 = bprice(valid[0])
    refs = [p for p in (l1, anc, cmin) if p > 0]
    ref = min(refs) if refs else l1
    eff_min = cmin if cmin > 0 else ref
    chg = ((lp - ref) / ref) * 100.0 if lp > 0 and ref > 0 else 0.0
    unlock_ok = bool(int(_f(frozen_days)) >= need_days and l1 > 0)
    step_min = round(l1 * (1.0 - udrop / 100.0), 4) if l1 > 0 else 0.0
    step_trig = round(math.floor((step_min + 1e-9) * 100.0) / 100.0, 2) if step_min > 0 else 0.0
    info = dict(base, ref_static_anchor=round(ref, 4), chg_static_pct=round(chg, 2), sub_unlock_eligible=unlock_ok, sub_stepped_min_price=step_min,
                sub_stepped_trigger_price=step_trig, next_sub_cycle_min_price=round(eff_min, 4), drop_buy_pct=req_drop)
    if lots >= cap:
        return dict(info, trigger_tag="HOLD_SUB_CAP_4_LOTS_REACHED", sub_unlock_eligible=False)
    if lp <= 0:
        return dict(info, trigger_tag="NO_LIVE_PRICE")
    if chg <= req_drop:
        return dict(info, should_buy=True, trigger_tag="SUB_STATIC_NEW_LOW", next_sub_cycle_min_price=round(min(eff_min, lp), 4))
    if unlock_ok and step_min > 0 and lp <= step_min:
        return dict(info, should_buy=True, is_sub_unlock=True, trigger_tag="SUB_UNLOCK_10D_D10", quota_ref_price=step_min, next_sub_cycle_min_price=round(min(step_min, lp), 4))
    return dict(info, trigger_tag="HOLD_SUB_GATE")


SUB_TAG_KO = {"SUB_FIRST_ENTRY": "서브 첫 진입 (본 그리드 5영업일 무매매)", "SUB_STATIC_NEW_LOW": "서브 신저가 추매", "SUB_UNLOCK_10D_D10": "서브 저가 해금 추매 (10영업일 무매매 · 서브 1층 대비 -10%)",
              "HOLD_SUB_CAP_4_LOTS_REACHED": "서브 한도 (4회분 = 16%)", "HOLD_SUB_GATE": "서브 대기 (10분 게이트)", "NO_ACTIVE_SUB_L1": "서브 없음",
              "HOLD_SUB_LATE_SESSION_NEW_CYCLE_CUTOFF": "서브 첫 진입 차단 (15:30~16:00)", "HOLD_SUB_INSUFFICIENT_IDLE_CASH": "서브 보류 (유휴 달러 부족)", "HOLD_SUB_GATE_PASSED": "서브 게이트 지남 (이번 10분 판정 끝)"}
