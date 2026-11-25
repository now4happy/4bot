# ==========================================================
# FILE: meritz_laoer/free_cash.py   (MERITZ_LAOER v2.15.0 · 판 41 할 일 2)
# GUARD30 수혈 장부(free_cash) — 원작 evaluate_guard30_and_reserve_injection(수혈 판정)·compute_reserve_repayment_on_zero(수혈금 상환) 를 한 줄도 안 고치고 부르는 얇은 어댑터.
# 원작 로직은 여기서 다시 쓰지 않음. 여기는 (1) 장부 파일 읽기·쓰기 (2) 체결 반영(매수 −, 매도 +, 수혈금 먼저 상환) (3) 판정 결과를 장부에 적용하는 일만 함.
#
# 장부 = data/free_cash.json (서버에만 생기는 파일). 키:
#   free_cash_usd           봇 장부상 쓸 수 있는 달러 (원작 free_cash_usd)
#   injected_reserve_usd    수혈로 들어온 금액 중 아직 못 갚은 몫 (원작 injected_reserve_usd = '빌린 돈')
#   used_reserve_portions_cnt  수혈 횟수(회분) (원작 used_reserve_portions_cnt)
#   cumulative_realized_net_usd  장부 시작 뒤 누적 실현손익 (상환 판정용)
#   initial_seed_usd        장부를 시작할 때의 시드 (상환 판정용)
#   free_init               처음 한 번 시작값을 계산했는지
#
# 원작 불변식: free_cash = 시드 + 누적 실현손익 + 수혈금 − 투입 원가 (quant_engine.py 1440 줄 근처 expected_free_cash).
#   매수 체결: free_cash −= 체결 금액 · 매도 체결: free_cash += 체결 금액, 그다음 수혈금 상환분만큼 free_cash −= 상환액 (수혈금이 줄어드니 불변식이 맞음)
# 미확인(판 41 질문란): ① 시작값 = 시드 − 미완성 F 원가 (바벨 때 Q6 식에서 60% 배율만 뺀 것 — 지시문에 시작값 지정 없음) ② 상환을 '매도마다' 부름 (원작 함수 이름은 0주 졸업 때)
# ==========================================================
import json
import os
import sys

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orig_sniper")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import quant_engine_core as QC       # noqa: E402  원작 복사본 (orig_sniper/)

FILE = ("data", "free_cash.json")
DEFAULTS = {"free_cash_usd": 0.0, "injected_reserve_usd": 0.0, "used_reserve_portions_cnt": 0, "cumulative_realized_net_usd": 0.0,
            "initial_seed_usd": 0.0, "free_init": False}


def _path(state_dir):
    return os.path.join(state_dir, *FILE)


def load(state_dir):
    """장부 읽기 (없거나 깨졌으면 기본값 — free_init False)"""
    st = dict(DEFAULTS)
    try:
        with open(_path(state_dir), "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            st.update({k: d[k] for k in DEFAULTS if k in d})
    except (OSError, ValueError):
        pass
    return st


def save(state_dir, st):
    """장부 쓰기 (임시 파일 → 교체, 중간에 꺼져도 반쯤 쓴 파일이 안 남음)"""
    p = _path(state_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({k: st.get(k, DEFAULTS[k]) for k in DEFAULTS}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    return st


def ensure_init(state_dir, seed_usd, incomplete_f_cost):
    """처음 한 번만: free_cash = 시드 − 미완성 F 원가 (0 아래로 안 내려감). 이미 했으면 그대로. 시드·미완성 원가는 부르는 쪽이 계산해서 넘김"""
    st = load(state_dir)
    if st["free_init"]:
        return st
    st.update(free_cash_usd=round(max(0.0, float(seed_usd) - float(incomplete_f_cost or 0.0)), 4), initial_seed_usd=round(float(seed_usd), 4),
              injected_reserve_usd=0.0, used_reserve_portions_cnt=0, cumulative_realized_net_usd=0.0, free_init=True)
    return save(state_dir, st)


def on_fill(state_dir, side, amount, cost_removed=None):
    """SOXL 체결 한 건을 장부에 반영 → 상환 정보 dict(did_repay·repaid_usd·...) 또는 None (장부 시작 전이면 아무것도 안 함).
    매수: free_cash −= amount. 매도(Q5): 실현손익을 누적하고, 원작 상환기로 수혈금(빌린 돈)부터 먼저 갚은 뒤 free_cash += amount − 상환액"""
    amount = float(amount or 0.0)
    if amount <= 0:
        return None
    st = load(state_dir)
    if not st["free_init"]:
        return None
    if str(side).upper() == "BUY":
        st["free_cash_usd"] = round(max(0.0, st["free_cash_usd"] - amount), 4)
        save(state_dir, st)
        return None
    st["cumulative_realized_net_usd"] = round(st["cumulative_realized_net_usd"] + amount - float(cost_removed or 0.0), 4)
    rep = QC.compute_reserve_repayment_on_zero(
        initial_seed_usd=st["initial_seed_usd"], cumulative_realized_net_usd=st["cumulative_realized_net_usd"],
        injected_reserve_usd=st["injected_reserve_usd"], used_reserve_portions_cnt=st["used_reserve_portions_cnt"],
        portion_mode=QC.PORTION_MODE_SIMPLE)
    repaid = float(rep.get("repaid_usd") or 0.0)
    st["free_cash_usd"] = round(max(0.0, st["free_cash_usd"] + amount - repaid), 4)
    st["injected_reserve_usd"] = round(float(rep.get("rem_injected_reserve_usd") or 0.0), 4)
    st["used_reserve_portions_cnt"] = int(rep.get("rem_used_reserve_portions_cnt") or 0)
    save(state_dir, st)
    return rep


def guard(state_dir, broker_cash_usd, exec_price, portion_budget, l1_cost=0.0, is_dip=False):
    """원작 GUARD30 판정기 그대로: 장부 free_cash 와 메리츠 실제 달러(broker_cash_usd)를 견줌 → 판정 dict (action: PROCEED_NORMAL | INJECT_AND_PROCEED | BLOCK_AND_ALERT_DEPOSIT ...).
    장부가 시작 전(free_init False)이면 free_cash 0 으로 판정되므로, 부르는 쪽(main.free_cash_ctx)이 ensure_init 을 먼저 불러야 함"""
    st = load(state_dir)
    return QC.evaluate_guard30_and_reserve_injection(
        free_cash_usd=st["free_cash_usd"], broker_bp_usd=float(broker_cash_usd), exec_price=float(exec_price), portion_budget=float(portion_budget),
        l1_actual_cost_usd=float(l1_cost or 0.0), is_dip_promotion=bool(is_dip), used_reserve_portions_cnt=st["used_reserve_portions_cnt"])


def apply_inject(state_dir, info):
    """판정이 INJECT_AND_PROCEED 이면 장부에 수혈 반영 (free_cash += inject_usd, injected_reserve += inject_usd, 수혈 횟수 = 판정의 used_portions_after) → 반영했으면 True.
    다른 판정이면 아무것도 안 함. 주문 전에 부름 (주문이 거절돼도 수혈은 '장부 안 달러가 늘어난 것'일 뿐 — 다음 판정에서 PROCEED_NORMAL 로 이어짐)"""
    if str((info or {}).get("action")) != "INJECT_AND_PROCEED":
        return False
    inj = float(info.get("inject_usd") or 0.0)
    if inj <= 0:
        return False
    st = load(state_dir)
    st["free_cash_usd"] = round(st["free_cash_usd"] + inj, 4)
    st["injected_reserve_usd"] = round(st["injected_reserve_usd"] + inj, 4)
    st["used_reserve_portions_cnt"] = int(info.get("used_portions_after") or (st["used_reserve_portions_cnt"] + int(info.get("inject_portions") or 0)))
    save(state_dir, st)
    return True
