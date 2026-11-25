# ==========================================================
# FILE: meritz_laoer/tower_strategy.py   (MERITZ_LAOER v2.7.0 · 판 39 v2.12.0)
# v2.16.0 (2026-11-25, 판 43): _apply_sell — 매도로 완성 F가 다시 미완성이 되면 빈 F(st['empty'])를 전부 없앰 → 다음 매수가 그 미완성 F부터 채움 (미완성 F 2개 방지)
#   + Q1 합치기: 탑 매도로 미완성 F가 2개가 되면 방금 미완성이 된 F를 원래 있던 미완성 F에 합침 (merge_due — 매도 주문 전량 체결 때, 부분 체결로 끝나면 reconcile 때)
#   + Q5 초과분 분리: 합산 원가가 F 목표($15,000)를 넘으면 목표를 안 넘는 가장 큰 정수 주식수는 원래 F 번호의 완성 F, 나머지는 같은 평단의 새 공사중 F (_split_over)
# v2.15.0 (2026-11-25, 판 41 할 일 5): 바벨 삭제 — barbell_factor(F 완성 기준·버킷 시드 0.60 배율)·BARBELL_PORTION_PCT·portion_mode 의 바벨 분기 제거. portion_mode 는 단리 10%·복리 8% 둘뿐. 바벨이 꺼져 있었으므로 지금 동작(배율 1.0) 그대로
# v2.12.0 (2026-11-24, 판 39): portion_mode 신설(복리 8%·단리 10%·바벨 15%) · portion_pct 가 설정 sniper_portion_pct 를 더 안 읽음 · tower_remaining_seed_usd·REMAINING_SEED_USD 삭제
# v2.10.0 (2026-11-23, 판 36 D5): 눌림 매수 기본 8% → 10%, 바벨 켜짐이면 15%(BARBELL_PORTION_PCT, 시드 $9,000 → $1,350). 돌파 매수 비율(BREAKOUT_PORTION_PCT·breakout_portion_pct/usd) 삭제 (설정 키는 남아 있어도 무시)
# v2.9.0 6차 (2026-11-22, 판 33): trade_mode(s)·buy_gap(s) 추가 — params 의 간격(칸 수)은 tower 모드에서만 설정 tower_buy_gap_usd(1~10, 기본 5), 스나이퍼 모드는 예전처럼 GAP_USD=5. 그 밖의 계산은 안 바꿈
# v2.7.0 (2026-11-21, 판 27): 층 간격 사용자 설정(tower_gap_usd) 제거 — params()는 간격을 내부 고정값 GAP_USD=5로만 돌려줌 (층 칸(levels) 만들기에만 씀, 매매 규칙 아님). 설정 파일에 tower_gap_usd가 남아 있어도 무시함.
# v2.6.0 (2026-11-21, 판 26): ① 버킷 모델 — 미완성 층 floor['boxes'] = [{id, qty, cost, ono}] (매수 체결 1건 = 버킷 1개, 층 qty·cost = 버킷 합, 예전 상태·불일치는 층 전체 1버킷 id 0) · boxes_view·sync_boxes·fit_boxes·next_box_id · _apply_sell 버킷별(층 원가·수량은 판 버킷 몫만) · 병합·장부 조정·입고가 버킷 유지 ② portion_pct(s) 추가, portion_usd(s) 가 설정 비율 사용 (PORTION_PCT=8.0 은 기본값) · percent_plan(portion_pct_=)
# v2.5.0 (2026-11-21, 판 25 하이브리드 버킷·층): ① 버킷 시드 box_seed(s)(tower_box_seed_usd, 기본 $15,000)·매수 분할 portion_usd(s)(버킷 시드의 8%, 단리 고정)·서브 4% sub_portion_usd(s) 추가 ② 층 표현 = 평단 정수 달러(price_label·floor_labels, 소수점 버림 — 내부 id 는 그대로)
#   ③ 탑 매도 체결 뒤 남은 층은 '잠금'을 풀어 공사중 버킷으로 되돌림(_apply_sell — 토스 스나이퍼가 비워진 부분을 다시 채우고, 채워지면 다시 완성 층) ④ percent_plan(남은 시드→나누는 비율 계산, 표시용 순수 계산) ⑤ view_lines 가 층을 평단 달러로 표시.
#   바뀌지 않은 것: make_plan·_apply_buy(탑쌓기 칸 매수 — 하이브리드에서는 안 부름)·is_tower·합병·동기화.
# v2.4.0 (2026-11-21, 판 24): 층 상태에 locked(잠금=탑 매도)·st["empty"](빈 층: 지하층·스나이퍼 선택 새 층)·indep(합병 안 하는 층) 추가 — is_tower(잠금 또는 완성)·ledger_fix_state(일회성 장부 바로잡기용 층 목록 교체). 기본값이면 v2.3.0 동작 그대로.
# v2.3.0 (2026-11-21, 판 23 하이브리드): make_plan 에 인자 2개 추가(기본값이면 v2.2.20 동작 그대로) — complete_only=True: 매도를 '완성 층'만 계산(탑 매도 +10% → 50%), sell_only=True: 매도 계산 뒤 매수 계획 없이 돌려줌(매수는 스나이퍼 몫).
#   _apply_sell: 스나이퍼 부분 매도 잔여는 완성으로 만들지 않고 미완성으로 둠(스나이퍼가 계속 관리). view_lines: 총 층 수 한도 표시 없음('N층'). 한도(층 수·총 시드)는 하이브리드에서 안 씀(tower_floors 는 예전 탑쌓기 코드용으로만 남음).
# v2.2.20 (2026-11-21, 판 22 듀얼 모드): 스나이퍼 체결 반영 추가 — apply_fill 이 kind 'buy_sniper' 를 받음(_apply_sniper_buy: 지정 층에 수량·원가 더함, 새 층 가능), _apply_sell 은 주문 mode 가 'sniper' 면 남은 주식을 탑업·재매수 대기 없이 완성 층으로 둠. 탑쌓기 계산(make_plan·_apply_buy·탑쌓기 매도)은 그대로
# v2.2.17 (2026-11-20, 판 20 하루 매수·매도 층 수 설정): 설정 tower_max_buy_layers_per_day · tower_max_sell_layers_per_day (1~3 정수, 없으면 1 = 예전 동작 그대로). buy_layers(s)·sell_layers(s) 추가.
#   make_plan 이 매수를 하루에 최대 N_buy 층까지 계획: 위에서부터 미완성 층을 차례로 최대 N개 (닫힌 층은 건너뛰고 N에 안 셈), 층마다 안 산 칸 전부 · 칸 금액·이월(carry)·반올림 이월(roll)·시초가 상한(cap_levels)은 층마다 따로.
#   새 F는 하루 최대 1개 — 미완성 F가 하나도 없을 때만 만들고 그날은 그 새 F만 삼. 현금·총 한도(pool)는 사는 F 전체가 순서대로 같이 씀 (모자라 멈추면 그 뒤 F는 안 삼).
#   info["tower"]["layers"] = 오늘 사는 F별 {id,new_floor,unit_usd,cells,levels,filled,open_cap}. 예전 키(active·new_floor·cells·info["unit_usd"]·info["open_cap"] 등)는 첫 F 기준 그대로. 매도 계산(make_plan 매도 부분)·체결 반영은 안 건드림
# v2.2.15 (2026-11-20, 판 19 오늘 계획 미리보기에 탑 진행률): make_plan 이 info["tower"]["floors"] 각 F에 "target"(그 F 목표 금액) 키를 하나 더 실음 — 표시 전용 (main.plan_head 가 view_lines 와 같은 비율을 내려면 F 목표가 필요). 주문·장부·F 계산은 그대로
# v2.2.14 (2026-11-20, 판 17 시초가 상한): 오늘 채우는 F의 안 산 칸 가격이 그날 시초가를 넘지 않게 함 — cap_levels(첫 칸 = min(시초가, 첫 계획 칸), 거기서 $1씩 아래로 안 산 칸 수만큼). make_plan(open_px=)·next_layer_cells(open_px=) 에 선택 인자 추가(0 이면 예전 그대로 = 시초가 확정 전).
#   칸 수·칸당 금액(base_usd)·주식수 반올림 규칙은 그대로, 바뀐 가격으로 주식수만 다시 계산. 상한이 걸리면 주문에 cap_levels 를 실어 _apply_buy 가 체결 반영 때 그 F의 칸(levels)을 '이미 산 칸 + 상한 칸'으로 바꿈(안 그러면 산 칸이 원래 칸 목록에 없어 같은 칸이 또 계획됨). 이미 산 칸(settled)·_new_floor_band·매도·간격·금액·F 수는 안 건드림
# v2.2.9 (2026-11-20, audit-fix 7-4·새 층 규칙, 3차): ① 1주 층은 자동 매도에서 뺌 (floor_sell_qty(1,·)=0, info["sell_excluded"]) — 풀이님 결정 10:03 ② 새 층을 못 만들면(총 한도 도달·가격 칸 없음) 만들지 않고 info["tower"]["new_floor_blocked"] 로 알림 — 자동으로 늘리거나 멈추지 않음 (풀이님 결정 09:59). 사다리(accum_strategy.py) 삭제로 탑쌓기 전용. 간격 기본값 GAP_USD=5 그대로
# v2.2.6 (2026-11-20, 판 16 본격): ① F별 매도(각 F 자기 평단 +10% 에 그 F 50%, 주문마다 floor_id·floor_avg 기록, 1주 F는 1주) ② 전역 sell_block → F별 rebuy_pending (그 F 매수 체결·F 닫힘 때 해제)
#   ③ 반영한 주문번호 맵(st["applied"]) — 같은 체결 두 번 반영 방지(누적 체결 기준 증분만 반영) ④ sort_fills: 시간순(없으면 매도 먼저)·새 F 계획 매수는 그날 매도 반영 뒤로 (B1)
#   ⑤ 새 F 계획 매수의 1층 빈칸 판정은 체결 평균가 기준 ±0.01 (B2) · closes F는 건너뜀 (B3) · F 완성 기준 금액 상한·base_usd 재계산 (B4) · 흡수한 가격은 새 F settled (B5)
#   ⑥ add_holdings(토스 입고분을 1층 빈곳에 넣음) ⑦ view_lines: 반칸 표시·미완성 글자. 새 층 기준점은 아래층 평단 그대로 (Q4)
# v2.2.5 (2026-11-20, 판 16 1층 채우기 매수): apply_fill 매수 체결 때, 계획한 새 층이 아직 없는데 위에 미완성 층이 있고 그 층의 안 산 칸에 이 체결 가격이 있으면 그 F(1층 탑업)에 넣음. 아침에 1층 완성 상태로 2층을 계획했는데 장중 매도로 1층이 미완성이 된 경우(버그 2) — 매수가 2층이 아니라 1층 빈곳을 채움. 이월(carry)은 주문의 계획 금액 기준으로 계산 (마지막 칸이 남은 부족분을 전부 가져가서 스스로 바로잡힘)
# v2.2.4 (2026-11-19, 1층 시작가 메뉴): _topup_setup·apply_fill·apply_fill_to_state·normalize·reconcile 에 start_usd 전달 — 1층 시작가가 정해졌으면 1층 칸이 시작가 기준
# v2.2.3 (2026-11-19, 판 14 색상 고침): 층 칸을 층별 색상 네모로 바꿈 (1층 🟩 시작). 흰색 █ 한 가지라 층 구분이 안 된다는 사용자 지적. 완성/쌓는 중 구분은 상세 줄 글자로만.
# v2.2.2 (2026-11-19, 판 14): 표시용 view_lines · floor_status 추가 (층 상태를 글자 줄로 바꾸는 순수 계산 — 상태·주문 계산은 안 건드림). 텔레그램 현상태(상황판)에서 tg_menu.py 가 부름
# v2.2.0 (2026-11-19, 판 13): 새 파일 — 탑쌓기(동적 층 시스템) 계산부. 순수 계산 (파일·네트워크·시계 없음). 사다리는 v2.2.9 에서 삭제됨
#   (v2.2.9: 7번은 탑쌓기만 씀 — 전환 설정 strategy 없음)
# 설계 (판 13 지시):
#   - 10F · 한 F $15,000 · 총 $150,000 · F 칸 수 GAP_USD=5 (v2.7.0 판 27: 내부 고정값, 사용자 설정 tower_gap_usd는 없앰) · F 완성 기준 금액·F 수 (settings tower_floor_usd / tower_floors, 없으면 기본값)
#   - 한 F = 간격(달러) 칸. 칸마다 1달러씩 내려가며 분산 매수. 칸당 금액 = F 완성 기준 금액 ÷ 간격 (반올림). 주식수도 반올림(0.5 는 올림)
#   - F는 동적: F 투자금(실제 체결 수량×체결가)이 F 완성 기준 금액에서 TOL_USD 이내로 모자라거나 넘으면 완성. 그 F 평단(가중평균)이 기준 →
#     다음 F 첫 칸 = 기준 평단 − 간격 (이어서 1달러씩 아래로 간격 칸)
#   - 매도: (v2.2.6) 각 F가 자기 평단 +10% 에 닿으면 그 F 보유의 50% (설정값 sell_profit_pct·sell_fraction_pct). 예전(v2.2.5 까지)은 전체 평단 기준·F별 비례로 뺌
#   - 탑업: 매도 뒤 각 F는 (남은 주식 원가 + 새로 사는 금액) = F 완성 기준 금액 이 되도록 부족분을, 그 F 평단 −1 ~ −간격 달러 칸에 나눠 산다
#   - F가 꼬이면(위 F보다 평단이 같거나 높음) 가중평균으로 합치고 평단 오름차순으로 재배치 (수량·투자금 보존)
#   - 슬리피지: F 상태는 실제 체결로만 계산. 못 산 금액은 같은 F의 다음 칸에 더함. 매일 동기화 때 장부(실제 보유분)와 다르면 가장 최근 F가 차이를 흡수
#   - 바벨 모드·SGOV·현금 배분 없음
# 상태(state): {"version": 1, "floors": [ {id, qty, cost, target, done, closed, levels, settled, base_usd, carry_usd, kind, rebuy_pending} ... 평단 오름차순 ],
#               "next_id": int, "applied": {주문번호: {"q": 반영한 누적 체결 수량, "amt": 누적 금액}}, "absorbed": {새 층 id: [1층에 흡수된 가격]}}
#   v2.2.6: 전역 sell_block 은 없어지고 F마다 rebuy_pending (예전 상태 파일의 sell_block=true 는 ensure_state 가 미완성 F의 rebuy_pending 으로 옮김)
#   id = 위에서부터 몇 F인지 (1 = 평단 가장 높은 F). 정리(normalize) 때마다 평단 순서로 다시 붙임
# ==========================================================
import copy
import math

FLOOR_USD = 15000.0        # F 완성 기준 금액 (달러)
FLOORS = 10                # F 수 → 총 한도 = FLOOR_USD × FLOORS = $150,000
GAP_USD = 5                # v2.7.0 판 27: F 칸 수 (내부 고정값) — 한 F의 칸(levels) 수. 사용자 설정(tower_gap_usd)은 없앴고, 칸 만들기에만 씀 (매매 규칙 아님).
TOL_USD = 100.0            # 완성 허용 오차: F 투자금이 목표에서 이만큼 이내로 모자라면 완성 (슬리피지·반올림)
BOX_SEED_USD = 15000.0     # v2.5.0 버킷 시드 기본값 (달러) — 설정 tower_box_seed_usd. 풀이님 결정 2026-11-21 (Q9): 기존 완성 F($15,000)과 같은 금액
PORTION_PCT = 10.0         # v2.10.0 판 36 D5: 신호 한 번에 사는 금액 = 버킷 시드의 10% (Case 113 단리 10%; 예전 8%)
SUB_PORTION_PCT = 4.0      # v2.5.0 서브 그리드 한 번에 사는 금액 = 버킷 시드의 4% (토스 SUB_PORTION_RATIO_4PCT = 0.04)
COMPOUND_PORTION_PCT = 8.0  # v2.12.0 판 39: 복리 모드(compound_enabled True) 첫·눌림 매수 = 버킷 시드의 8% (원작 PORTION_RATIO_COMPOUND 0.08). 하이브리드는 시드가 버킷 고정이라 '복리 = 비율만 8%' (원금 재투자 계산은 안 함)
PCT_BAND_HI_USD = 30.0     # 퍼센트 작업: 고르게 나눌 가격 구간 위쪽 ($30) — 근거 percent_work.md
PCT_BAND_LO_USD = 10.0     # 퍼센트 작업: 구간 아래쪽 ($10)


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
    """한 F의 매도 수량: 보유 q 의 frac% (반올림, 0.5 는 올림). 2주 이상이면 1주는 남김. 1주 F는 0주 — 자동 매도에서 빼고 보류 (v2.2.9 audit-fix 7-4, 풀이님 결정 2026-11-20 10:03: 1주 남으면 '1주 남음' 메시지만, 팔려면 직접 매도. v2.2.6 의 '1주 층 1주 판매' 를 되돌림)"""
    q = int(_f(q))
    if q <= 1 or _f(frac) <= 0:
        return 0
    return max(0, min(rnd(q * _f(frac) / 100.0), q - 1))


def params(s):
    """(F 완성 기준 금액, F 수, 간격=칸 수). 설정에 없거나 이상하면 기본값. v2.7.0 판 27: 간격은 사용자 설정이 아니라 내부 고정값 GAP_USD=5로만 돌려줌 (설정 파일에 tower_gap_usd가 남아 있어도 무시)."""
    s = s or {}
    fu = _f(s.get("tower_floor_usd")) or FLOOR_USD
    fl = int(_f(s.get("tower_floors"))) or FLOORS
    fu = fu if fu > 0 else FLOOR_USD
    return round(fu, 2), (fl if fl >= 1 else FLOORS), buy_gap(s)


def trade_mode(s):
    """v2.9.0 6차 판 33: 매매 모드 'sniper'(기본, 하이브리드) | 'tower'(탑쌓기 매매). 이상한 값은 sniper"""
    return "tower" if str((s or {}).get("trade_mode") or "").strip().lower() == "tower" else "sniper"


def buy_gap(s):
    """판 33: 탑쌓기 매매 모드에서만 설정 tower_buy_gap_usd(1~10 정수, 기본 5) — 스나이퍼 모드는 예전처럼 내부 고정값 GAP_USD"""
    if trade_mode(s) != "tower":
        return GAP_USD
    g = _f((s or {}).get("tower_buy_gap_usd"))
    return int(g) if g == int(g) and 1 <= g <= 10 else GAP_USD


def box_seed(s):
    """v2.5.0 버킷 시드(달러): 설정 tower_box_seed_usd, 없거나 0 이하면 기본 $15,000"""
    v = _f((s or {}).get("tower_box_seed_usd"))
    return round(v if v > 0 else BOX_SEED_USD, 2)


def portion_mode(s):
    """v2.15.0 판 41 할 일 5: 매수 비율 모드 'compound'(복리 8%) | 'simple'(단리 10%, 기본) 둘뿐 (바벨 15% 삭제). 복리(compound_enabled True)가 아니면 단리"""
    return "compound" if (s or {}).get("compound_enabled") is True else "simple"


def portion_pct(s):
    """첫·눌림(본) 매수 비율(%): 모드로만 결정 — 복리 8.0(COMPOUND_PORTION_PCT) · 단리 10.0(PORTION_PCT)"""
    return COMPOUND_PORTION_PCT if portion_mode(s) == "compound" else PORTION_PCT


def portion_usd(s):
    """v2.6.0 신호 한 번에 사는 금액 = 버킷 시드 × 눌림 비율(portion_pct, 단리 10% · 복리 8%) (달러 2자리). 시드 $15,000 × 10% = $1,500"""
    return round(box_seed(s) * portion_pct(s) / 100.0, 2)


def sub_portion_usd(s):
    """v2.5.0 서브 그리드 한 번에 사는 금액 = 버킷 시드 × 4% (시드 $15,000 이면 $600)"""
    return round(box_seed(s) * SUB_PORTION_PCT / 100.0, 2)


def price_label(avg, no=None):
    """v2.5.0 F 표현: 평단의 정수 달러 + F + 스나이퍼 번호 (평단 오름차순, 1 = 가장 낮음). 평단 $48.14 → '48F2'. 번호가 없으면 번호 없이 '48F'. 평단이 0 이하면 '공사중'"""
    a = _f(avg)
    if a <= 0:
        return "공사중"
    base = f"{int(math.floor(a + 1e-9))}F"
    return f"{base}{int(no)}" if no is not None else base


def _f_rank(st):
    """스나이퍼 번호 {층 id: 번호} — 평단 오름차순 (1 = 가장 낮은 평단). 같으면 번호가 큰 층이 아래 (sniper_numbers 와 같은 키)"""
    fl = [f for f in top_down(st if isinstance(st, dict) else {}) if int(_f(f.get("qty"))) > 0]
    return {int(_f(f.get("id"))): n + 1 for n, f in enumerate(sorted(fl, key=lambda f: (floor_avg(f), -int(_f(f.get("id"))))))}


def floor_labels(st):
    """v2.5.0 {층 id: '48F2'} — 수량이 있는 F만. F 표기 (평단 정수 + F + 스나이퍼 번호). 내부 id 는 안 바뀜"""
    fl = [f for f in top_down(st if isinstance(st, dict) else {}) if int(_f(f.get("qty"))) > 0]
    rank = _f_rank(st)
    return {int(_f(f.get("id"))): price_label(floor_avg(f), rank.get(int(_f(f.get("id"))))) for f in fl}


def percent_plan(remaining_usd, box_usd, hi=PCT_BAND_HI_USD, lo=PCT_BAND_LO_USD, portion_pct_=None):
    """v2.5.0 퍼센트 작업(표시용 순수 계산, 주문에 안 씀): 남은 시드를 가격 구간 hi→lo 에 버킷마다 같은 금액·같은 가격 폭으로 나눔.
    버킷 수 n = 남은 시드 ÷ 버킷 시드 (반올림, 최소 1) · 버킷당 금액 = 남은 시드 ÷ n · 버킷당 비율(%) = 100 ÷ n · 버킷당 가격 폭 = (hi − lo) ÷ n ·
    $1 당 금액 = 남은 시드 ÷ (hi − lo) · $1 당 비율(%) = 100 ÷ (hi − lo). 구간 = 위에서부터 [hi, hi − 폭], … 입력이 이상하면(0 이하·hi ≤ lo) None.
    토스 신호 숫자(눌림·돌파)는 안 바꿈 — 남은 시드를 바꾸면 이 값이 다시 계산됨. v2.6.0: portion_pct_ 를 주면(호출한 쪽이 TW.portion_pct(s) 를 넘김) 그 비율을, 없으면 기본 8%를 표시"""
    r, b, h, l_ = _f(remaining_usd), _f(box_usd), _f(hi), _f(lo)
    pp = _f(portion_pct_) if (portion_pct_ is not None and 0 < _f(portion_pct_) <= 100) else PORTION_PCT
    if r <= 0 or b <= 0 or h <= l_ or l_ < 0:
        return None
    n = max(1, int(math.floor(r / b + 0.5 + 1e-9)))
    w = (h - l_) / n
    bands = [(round(h - i * w, 2), round(h - (i + 1) * w, 2)) for i in range(n)]
    return {"remaining_usd": round(r, 2), "box_usd": round(b, 2), "boxes": n, "per_box_usd": round(r / n, 2), "per_box_pct": round(100.0 / n, 2),
            "band_width_usd": round(w, 4), "per_dollar_usd": round(r / (h - l_), 2), "per_dollar_pct": round(100.0 / (h - l_), 2),
            "hi": h, "lo": l_, "bands": bands, "portion_pct": pp, "portion_usd": round(b * pp / 100.0, 2)}


LAYERS_MAX = 3             # v2.2.17: 하루 매수·매도 층 수 설정의 상한 (1 ~ LAYERS_MAX 정수만)


def _layers_setting(s, key):
    """하루 층 수 설정 → 1 ~ LAYERS_MAX 정수. 설정에 없거나(None) 이상하면(0·4 이상·소수·글자·bool) 1 = 예전 동작 (이상한 값은 validate_settings 가 주문 전에 막음)"""
    v = (s or {}).get(key)
    if v is None or isinstance(v, bool):
        return 1
    x = _f(v)
    return int(x) if 1 <= x <= LAYERS_MAX and x == int(x) else 1


def buy_layers(s):
    """하루에 살 최대 층 수 (tower_max_buy_layers_per_day, 기본 1)"""
    return _layers_setting(s, "tower_max_buy_layers_per_day")


def sell_layers(s):
    """하루에 팔 최대 층 수 (tower_max_sell_layers_per_day, 기본 1)"""
    return _layers_setting(s, "tower_max_sell_layers_per_day")


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
    if isinstance(st.get("next_box"), bool) or not isinstance(st.get("next_box"), int) or st.get("next_box") < 1:
        st["next_box"] = 1                                            # v2.6.0: 버킷 번호 발급기 (상태 안에서 겹치지 않는 버킷 번호)
    if not isinstance(st.get("empty"), list):
        st["empty"] = []                                              # v2.4.0: 빈 F(공사중·스나이퍼 선택 새 F) 목록 — 0주라 floors 에 못 둠 (normalize 가 수량 0 F를 지움)
    legacy = bool(st.pop("sell_block", False))
    for f in st["floors"]:
        f.setdefault("locked", False)                                 # v2.4.0: 잠금 = 탑쌓기 매도 (이 층은 스나이퍼 매도 안 함)
        if "rebuy_pending" not in f:
            f["rebuy_pending"] = bool(legacy and int(_f(f.get("qty"))) > 0 and not is_complete(f))
    return st


def floor_avg(f):
    q = int(_f(f.get("qty")))
    return round(_f(f.get("cost")) / q, 4) if q > 0 else 0.0


def is_complete(f, tol=TOL_USD):
    """완성된 F: 완성 표시(done)가 있거나, 투자금이 목표에서 tol 이내로 모자라거나 넘음"""
    return bool(f.get("done")) or _f(f.get("cost")) >= _f(f.get("target") or FLOOR_USD) - tol - 1e-9


def is_tower(f):
    """v2.4.0: 탑 매도 F = 잠긴 F 또는 완성 F (스나이퍼 매도 대상이 아님)"""
    return bool(f.get("locked")) or is_complete(f)


def _floor(fid, qty, cost, target, kind):
    return {"id": int(fid), "qty": int(qty), "cost": round(_f(cost), 4), "target": float(target), "done": False, "closed": False,
            "levels": [], "settled": [], "base_usd": 0.0, "carry_usd": 0.0, "kind": kind, "rebuy_pending": False, "locked": False, "boxes": []}


# ---------------------------------------------------------------- v2.6.0 버킷 (미완성 F의 매수 1건 = 버킷 1개)
# 버킷 = {"id": 상태 안에서 겹치지 않는 번호, "qty": 주, "cost": 원가(달러), "ono": 산 주문번호(선택 — 같은 주문의 부분 체결을 한 버킷으로 모음)}.
# 규칙: F의 qty·cost 는 버킷들의 합과 같다. 버킷이 없거나 합이 안 맞으면(예전 상태 파일·장부 조정·탑 매도 뒤 잔여) F 전체를 버킷 1개(id 0, 평단 = F 평단)로 본다.
# 완성 F(탑 매도)은 버킷을 안 씀 — 완성되면 boxes 를 비움.
BOX_COST_TOL = 0.05         # 버킷 원가 합과 F 원가가 이만큼(달러) 이내로 다르면 같은 것으로 봄 (반올림 먼지)


def boxes_view(f):
    """읽기 전용 버킷 목록 (복사본, 상태 안 바꿈). 수량 0 이하 F는 []. 버킷 합이 F qty·cost 와 다르거나 버킷이 없으면 [F 전체 1개(id 0)]"""
    q, c = int(_f(f.get("qty"))), _f(f.get("cost"))
    if q <= 0:
        return []
    bs = []
    for b in (f.get("boxes") if isinstance(f.get("boxes"), list) else []):
        if isinstance(b, dict) and int(_f(b.get("qty"))) > 0:
            bx = {"id": int(_f(b.get("id"))), "qty": int(_f(b.get("qty"))), "cost": round(_f(b.get("cost")), 4), "ono": str(b.get("ono") or "")}
            if b.get("lot_type"):
                bx["lot_type"] = str(b["lot_type"])               # 판 37 후속: 층 태그(GRID_L1..L7) 보존 — 원작 버킷의 lot_type 과 같은 역할 (grid_tiers.py)
            bs.append(bx)
    if bs and sum(b["qty"] for b in bs) == q and abs(sum(b["cost"] for b in bs) - c) <= BOX_COST_TOL and len({b["id"] for b in bs}) == len(bs):
        return bs
    return [{"id": 0, "qty": q, "cost": round(c, 4), "ono": ""}]


def box_avg(b):
    q = int(_f(b.get("qty")))
    return round(_f(b.get("cost")) / q, 4) if q > 0 else 0.0


def next_box_id(st):
    """겹치지 않는 새 버킷 번호 (발급기 st['next_box'] 와 지금 있는 버킷 번호 중 큰 값 + 1 을 보장)"""
    used = [int(_f(b.get("id"))) for f in (st.get("floors") or []) for b in (f.get("boxes") or []) if isinstance(b, dict)]
    nb = max(int(_f(st.get("next_box"))) or 1, max(used, default=0) + 1, 1)
    st["next_box"] = nb + 1
    return nb


def sync_boxes(st, f):
    """상태를 바꾸는 쪽에서 부름: F f 의 boxes 를 boxes_view 결과로 맞춤 (합이 맞으면 반올림 먼지를 마지막 버킷에 흡수해 합을 정확히). 완성 F는 건드리지 않음 → 버킷 목록"""
    if is_tower(f):
        return boxes_view(f)
    bs = boxes_view(f)                                                # 예전 상태·불일치면 1버킷 (id 0)
    if bs:
        bs[-1]["cost"] = round(bs[-1]["cost"] + (_f(f.get("cost")) - sum(b["cost"] for b in bs)), 4)
    f["boxes"] = bs
    return bs


def fit_boxes(st, f):
    """F qty·cost 를 바깥에서 바꾼 뒤(장부 조정·입고) 버킷을 맞춤: 차이를 마지막 버킷이 받음 (받아도 수량이 1 이상 남을 때만) — 안 되면 버킷을 비워 1버킷으로 접음"""
    q, c = int(_f(f.get("qty"))), _f(f.get("cost"))
    bs = [b for b in (f.get("boxes") or []) if isinstance(b, dict) and int(_f(b.get("qty"))) > 0]
    if q <= 0 or not bs:
        f["boxes"] = []
        return
    dq, dc = q - sum(int(_f(b["qty"])) for b in bs), round(c - sum(_f(b["cost"]) for b in bs), 4)
    last = max(bs, key=lambda b: int(_f(b.get("id"))))
    if int(_f(last["qty"])) + dq >= 1 and _f(last["cost"]) + dc > 0:
        last["qty"], last["cost"] = int(_f(last["qty"])) + dq, round(_f(last["cost"]) + dc, 4)
        f["boxes"] = bs
    else:
        f["boxes"] = []


def ledger_fix_state(st, specs, fu):
    """v2.4.0 장부 바로잡기 (일회성): F 목록을 specs=[(수량, 원가), ...] 로 통째로 바꿈. 두 F 모두 잠금(탑쌓기 매도)·완성 표시, 공사중 1개(빈 F, 0주·$0) 추가.
    applied(반영한 주문번호)·absorbed 는 그대로 둠 — 늦은 체결(run_late_fills)이 이미 반영한 것을 다시 넣지 않게. 실제 잔고·주문은 안 건드림 (상태만). → st"""
    ensure_state(st)
    fl = []
    for i, (q, c) in enumerate(specs, 1):
        f = _floor(i, int(q), float(c), fu, "ledger_fix")
        f["done"], f["locked"] = True, True
        fl.append(f)
    st["floors"] = sorted(fl, key=floor_avg)
    for i, f in enumerate(sorted(fl, key=lambda x: -floor_avg(x)), 1):
        f["id"] = i
    st["next_id"] = len(fl) + 1
    st["empty"] = [{"kind": "basement", "ref_px": 0.0, "id": "b1"}]
    return st


def migrate_from_holdings(qty, principal, s=None):
    """지금 보유분(장부의 주식수·원금) → 1F. 숫자는 호출한 쪽이 장부에서 읽어 넘김 (여기서 정하지 않음).
    1F는 투자금이 F 완성 기준 금액보다 적어도 '완성된 F'로 침. 보유 0주면 F 없음"""
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
    """위(평단 높은 F)부터. id 순서 (정리 뒤에는 평단 내림차순과 같음)"""
    return sorted(st.get("floors") or [], key=lambda f: int(_f(f.get("id"))))


def _topup_setup(f, gap, start_usd=0.0):
    """매도·합병 뒤: 부족분(F 완성 기준 금액 − 남은 투자금)을 그 F 평단 −1 ~ −간격 달러 칸에 나눠 사도록 준비. 부족분이 tol 이하면 완성.
    v2.2.4: 맨 위 F 시작가가 정해졌으면(start_usd > 0) 맨 위 F는 평단 대신 시작가를 기준으로 칸을 정함 (보유 주식이 있어도 맨 위 F 가격 배정을 직접 정할 수 있게). 그 아래 F는 평단 기준 그대로."""
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
    """새 F: 첫 칸 = 기준 평단 − 간격, 이어서 1달러씩 아래로 간격 칸"""
    return [p for p in (round(_f(anchor) - gap - i, 2) for i in range(gap)) if p > 0], float(rnd(target / gap))


def cap_levels(cand, open_px):
    """v2.2.14 시초가 상한. cand = 안 산 칸 가격(계획 그대로) → (새 칸 목록, 상한이 걸렸는지).
    첫 칸 = min(시초가, 첫 계획 칸) — 시초가가 첫 계획 칸 이상이면 그대로(위로 올리지 않음·안 걸림). 걸리면 시초가에서 $1씩 아래로 칸 수만큼(0 이하 가격은 뺌).
    시초가가 0 이하면(확정 전) 그대로. 순수 계산"""
    cand = list(cand or [])
    op = _f(open_px)
    if not cand or op <= 0:
        return cand, False
    first = max(cand)
    if op >= first - 1e-9:
        return cand, False
    return [p for p in (round(op - i, 2) for i in range(len(cand))) if p > 0], True


def next_layer_cells(active, tgt_active, open_px=0.0):
    """다음 회차(채우는 F)의 칸별 배정: [{price, amount, qty}] — 오늘 주문 수와 무관하게 전체 칸.
    금액은 칸당 base_usd(첫 칸은 이월 carry 더함), 마지막 칸은 F에 모자란 만큼 전부. 주식수는 반올림.
    0.5주 미만 칸은 금액이 다음 칸으로 넘어감 (주문 계산과 같은 규칙). 현금·한도 검사는 안 함 (배정 미리보기).
    v2.2.14: open_px > 0(시초가 확정)이면 안 산 칸 가격에 시초가 상한(cap_levels)을 적용. 0 이면 예전 그대로"""
    if not active:
        return []
    cand = [p for p in active.get("levels") or [] if p not in set(active.get("settled") or [])]
    cand, _capped = cap_levels(cand, open_px)
    cells, planned, roll = [], 0.0, 0.0
    for n, p in enumerate(cand):
        is_last = (p == cand[-1])
        carry = _f(active.get("carry_usd")) if n == 0 else 0.0
        if is_last:
            amount = max(0.0, _f(tgt_active) - _f(active.get("cost")) - planned)
        else:
            amount = max(0.0, _f(active.get("base_usd")) + carry + roll)
            amount = min(amount, max(0.0, _f(tgt_active) - _f(active.get("cost")) - planned))      # v2.2.6 B4: 마지막이 아닌 칸도 F 목표를 못 넘게
        q = rnd(amount / p) if amount > 0 and p > 0 else 0
        if q < 1:
            roll += amount
            continue
        roll = 0.0
        cells.append({"price": round(_f(p), 2), "amount": round(amount, 2), "qty": q})
        planned += amount
    return cells


# ---------------------------------------------------------------- 계획
def make_plan(s, st, qty, principal, price, fx, usd_cash, sellable, ignore_auto_fx=False, open_px=0.0, complete_only=False, sell_only=False):
    """오늘 낼 주문 계산 → {"orders", "notes", "info"}. 상태·장부를 바꾸지 않음.
    open_px: 오늘 시초가 (v2.2.14 — 0 이면 아직 확정 전이라 계획 배정 그대로. 시초가를 여기서 지어내거나 전일종가로 대신하지 않음)
    s: 설정, st: 탑쌓기 상태, qty/principal: 장부(주·달러), price: 현재가, fx: 메리츠 적용환율(원/달러), usd_cash: USD 예수금, sellable: 매도가능 수량"""
    qty, principal, price = int(_f(qty)), _f(principal), _f(price)
    fu, nfl, gap = params(s)
    avg = round(principal / qty, 4) if qty > 0 else 0.0
    pct, frac = _f(s.get("sell_profit_pct")), _f(s.get("sell_fraction_pct"))
    otype = s.get("order_type")   # v2.2.8: 탑쌓기는 하루에 한 F(안 산 칸 전부)을 삼 — v2.2.17: 설정 tower_max_buy_layers_per_day 만큼 F 수 (기본 1). max_rounds_per_day(사다리 회차)는 탑쌓기 매수 칸 수에 안 씀
    st = ensure_state(copy.deepcopy(st))                              # 상태·장부를 바꾸지 않음 (사본으로 계산)
    labs = floor_labels(st)                                        # 표시용 F 라벨 {층 id: '40F1'} (스나이퍼 번호 — 평단 오름차순)
    notes, orders = [], []
    profit_pct = round((price / avg - 1) * 100, 2) if avg > 0 and price > 0 else None
    fl_qty, fl_cost = totals(st)
    info = {"mode": "tower", "avg": avg, "qty": qty, "price": price, "fx": fx, "sell_target": 0.0, "profit_pct": profit_pct,
            "filled": [], "levels": [], "rebuy_anchor": None, "rebuy_k": 0,
            "profit_reached": False, "credit_usd": 0.0, "sells": []}
    if qty > 0 and fl_qty != qty:
        notes.append(f"F 합계 {fl_qty}주 ≠ 장부 {qty}주 — 다음 주문일 동기화 때 가장 최근 F가 차이를 흡수해요")

    # ---------------- 매도 (v2.2.6 F별): 각 F가 자기 평단 +pct% 에 닿으면 그 F 보유의 frac%. 여러 F가 같은 날 닿으면 모두 판다.
    # 주문마다 F id(floor_id)·매도 시점 F 평단(floor_avg) 기록. F당 하루 1건은 호출한 쪽(main)이 지킴. 총 매도가능 검사는 F 합계 기준
    one_floors = []
    if qty > 0:
        cap_q, taken = min(int(_f(sellable)), qty), 0
        for f in top_down(st):
            fq = int(_f(f.get("qty")))
            if fq <= 0:
                continue
            if complete_only and not is_tower(f):                          # v2.4.0: 잠긴 F도 탑 매도. v2.3.0: 하이브리드 — 탑 매도는 완성 F만 (미완성 F는 스나이퍼가 팖)
                continue
            fa = floor_avg(f)
            tf = ceil2(fa * (1 + pct / 100.0))
            sq = floor_sell_qty(fq, frac)
            row = {"id": int(_f(f.get("id"))), "avg": fa, "target": tf, "qty": fq, "sell_qty": sq, "reached": bool(price > 0 and price >= tf),
                   "pending": bool(f.get("rebuy_pending")), "ordered": False}
            info["sells"].append(row)
            if f.get("rebuy_pending") and not s.get("allow_consecutive_sell"):
                notes.append(f"매도 보류: {labs.get(row['id'], price_label(fa))} — 직전 매도 뒤 이 F 재매수(탑업) 체결이 아직 없음 (allow_consecutive_sell=false)")
            elif fq == 1:                                                  # v2.2.9 audit-fix 7-4: 1주 F는 자동 매도 제외 (알림은 main 이 하루 한 번)
                row["held_one"] = True
                one_floors.append(row["id"])
                notes.append(f"매도 {labs.get(row['id'], price_label(fa))} 보유 1주 — 자동 매도 제외 (보류, 직접 매도해야 팔려요)")
            elif sq < 1:
                notes.append(f"매도 {labs.get(row['id'], price_label(fa))} {frac:g}% = 0주 (F 보유 {fq}주) — 매도 안 함")
            elif taken + sq > cap_q:
                notes.append(f"매도 {labs.get(row['id'], price_label(fa))} {sq}주 > 매도가능 {max(cap_q - taken, 0)}주 (총 매도가능 {int(_f(sellable))}/장부 {qty}) — 매도 안 함")
            else:
                taken += sq
                row["ordered"] = True
                orders.append({"side": "SELL", "type": otype, "qty": sq, "price": tf, "kind": "sell", "level": None, "floor_id": row["id"], "floor_avg": fa,
                               "reached": row["reached"], "desc": f"{labs.get(row['id'], price_label(fa))} 평단 ${fa:.2f} +{pct:g}% 매도 {frac:g}%"})
        if one_floors:
            info["sell_excluded"] = {"why": "one_share", "floors": list(one_floors), "qty": 1}
        if info["sells"]:
            info["sell_target"] = min(r["target"] for r in info["sells"])          # 가장 낮은 F의 목표 (제일 먼저 닿음)
            info["profit_reached"] = any(r["reached"] for r in info["sells"])

    if sell_only:                                                    # v2.3.0: 하이브리드 — 매수는 스나이퍼 몫이라 여기서 안 계획
        info["sell_only"] = True
        return {"orders": orders, "notes": notes, "info": info}
    if not (fx and fx > 0):
        notes.append("환율 없음 — 매수 계획 불가 (매도만)")
        return {"orders": orders, "notes": notes, "info": info}

    # ---------------- 오늘 채울 F 찾기 (v2.2.17: 위에서부터 미완성 F를 차례로 최대 N_buy 개). 범위를 벗어난 F·칸을 다 쓴 F는 닫힌 것으로 치고 건너뜀 — N 에 안 셈
    cap_total = fu * nfl
    floors = top_down(st)
    n_buy = buy_layers(s)
    closes, actives = [], []
    for f in floors:
        if len(actives) >= n_buy:
            break
        if int(_f(f.get("qty"))) <= 0 or is_complete(f) or f.get("closed"):
            continue
        unset = [p for p in f.get("levels") or [] if p not in set(f.get("settled") or [])]
        if not unset:
            closes.append(f["id"])                                   # 칸을 다 썼는데 미완성 → 미완성 F로 닫음 (부족분은 그대로)
            continue
        if _f(f.get("cost")) > 0 and price > 0 and price < min(f["levels"]) - gap:
            closes.append(f["id"])                                   # 가격이 F 범위를 한 간격 넘게 벗어남 → 미완성 F로 닫음
            notes.append(f"{labs.get(f['id'], price_label(floor_avg(f)))}: 현재가 ${price:.2f} 가 F 범위(맨 아래 ${min(f['levels']):.2f})를 벗어나 미완성 F로 둠 (부족분 ${max(_f(f['target']) - _f(f['cost']), 0):,.0f} 그대로)")
            continue
        actives.append(f)
    new_floor, new_floor_blocked = None, None
    room = cap_total - principal
    if not actives:                                                  # v2.2.17: 새 F는 미완성 F가 하나도 없을 때만, 하루 최대 1개 (새 F 평단이 없어 그날 다음 F를 또 만들 수 없음)
        have = [f for f in floors if int(_f(f.get("qty"))) > 0]
        if not have:
            notes.append("F 없음 (보유 0주) — 탑쌓기는 기존 보유분을 1F로 시작해야 해요 (장부 시작 필요)")
        elif room < TOL_USD:
            notes.append(f"총 한도 ${cap_total:,.0f} 도달 (보유 원가 ${principal:,.0f}) — 새 F 없음")
            new_floor_blocked = {"why": "limit", "text": f"총 한도 ${cap_total:,.0f} 에 닿았어요 (보유 원가 ${principal:,.0f})"}
        else:
            anchor = min(floor_avg(f) for f in have)
            tgt = min(fu, room)
            lv, base = _new_floor_band(anchor, gap, tgt)
            if not lv:                                                   # v2.2.9 (풀이님 결정 09:59): 새 F 가격 칸이 하나도 안 나오면 만들지 않고 멈춤 — 알아서 늘리거나 봇을 멈추지 않음
                notes.append(f"새 F를 만들 수 없음 — 기준 평단 ${anchor:.2f} − 간격 ${gap} 아래에 살 수 있는 가격(0 초과)이 없음")
                new_floor_blocked = {"why": "no_price", "text": f"새 F 가격 칸이 없어요 (기준 평단 ${anchor:.2f}, 간격 ${gap} — 모든 칸이 0달러 이하)"}
            else:
                nid = max(int(_f(st.get("next_id"))), max(int(_f(f.get("id"))) for f in floors) + 1)
                new_floor = {"id": nid, "anchor": anchor, "levels": lv, "base_usd": base, "target": tgt}
                actives = [{"id": nid, "qty": 0, "cost": 0.0, "target": tgt, "levels": lv, "settled": [], "base_usd": base, "carry_usd": 0.0}]

    # ---------------- F마다 안 산 칸 (v2.2.14 시초가 상한은 오늘 사는 각 F의 안 산 칸에만 — 산 칸·다른 F는 그대로)
    layers = []
    for active in actives:
        settled = set(active.get("settled") or [])
        cand = [p for p in active["levels"] if p not in settled]
        oc = {"open": (round(_f(open_px), 4) if _f(open_px) > 0 else None), "applied": False, "planned_first": None, "first": None}
        lv_all, filled = list(active["levels"]), sorted(settled, reverse=True)
        if cand:
            oc["planned_first"] = max(cand)
        cand, capped = cap_levels(cand, open_px)
        cap_out = None                                               # v2.2.14: 상한이 걸렸을 때만 채움 (주문에 실어 체결 반영이 F 칸을 바꿈)
        is_new = bool(new_floor) and int(_f(active["id"])) == int(new_floor["id"])
        if capped:
            cap_out = list(cand)
            if is_new:
                new_floor["levels"] = list(cand)                     # 새 F도 같은 칸으로 만들어짐 (_new_floor_band 자체는 그대로)
            lv_all = sorted(settled | set(cand), reverse=True)
            oc["applied"] = True
        if cand:
            oc["first"] = max(cand)
        layers.append({"f": active, "cand": cand, "cap_out": cap_out, "oc": oc, "levels": lv_all, "filled": filled, "new": is_new,
                       "tgt": _f(active.get("target") or fu)})
    first = layers[0] if layers else None
    info["open_cap"] = first["oc"] if first else {"open": (round(_f(open_px), 4) if _f(open_px) > 0 else None), "applied": False, "planned_first": None, "first": None}
    if first:                                                        # 예전 키(levels·filled·unit_usd·open_cap)는 첫 F(맨 위) 기준 그대로
        info["levels"], info["filled"], info["unit_usd"] = first["levels"], first["filled"], first["f"]["base_usd"]
    info["tower"] = {"floor_usd": fu, "floors_max": nfl, "cap_usd": cap_total, "active": (first["f"]["id"] if first else None),
                     "new_floor": bool(new_floor), "new_floor_blocked": new_floor_blocked, "buy_layers": n_buy,
                     "floors": [{"id": f["id"], "qty": f["qty"], "cost": round(_f(f["cost"]), 2), "avg": floor_avg(f),
                                 "complete": is_complete(f), "target": _f(f.get("target") or FLOOR_USD), "closed": bool(f.get("closed")) or f["id"] in closes,
                                 "rebuy_pending": bool(f.get("rebuy_pending"))} for f in floors]}

    # ---------------- 칸 금액 (칸당 금액 반올림 · 주식수 반올림 · 못 산 금액은 같은 F 다음 칸에 더함). v2.2.17: F마다 따로 계산(carry·roll·planned 가 F끼리 새지 않음), 현금·총 한도(pool)만 F 전체가 순서대로 같이 씀
    auto_fx = bool(s.get("auto_fx_enabled")) and not ignore_auto_fx
    pool = max(0.0, room if auto_fx else min(_f(usd_cash), room))
    cash_binds = (not auto_fx) and _f(usd_cash) <= room + 1e-9
    info.update({"unit_usd": info.get("unit_usd", 0.0), "cap_usd": round(cap_total, 2), "pool_usd": round(pool, 2)})
    spent, stop = 0.0, False
    for ly in layers:
        active, cand, tgt_active = ly["f"], ly["cand"], ly["tgt"]
        ly["cells"] = next_layer_cells(active, tgt_active, open_px)   # v2.2.3: 다음 회차 가격별 배정 미리보기 (v2.2.14: 시초가 확정이면 상한 적용) — F마다
        meta_nf = new_floor if ly["new"] else None
        planned, roll = 0.0, 0.0
        if stop:
            continue
        for n, p in enumerate(cand):   # v2.2.8: 이 F의 안 산 칸 전부
            is_last = (p == cand[-1])
            carry = _f(active.get("carry_usd")) if n == 0 else 0.0
            if is_last:                                                  # 마지막 칸 = F에 모자란 만큼 전부 (그날 앞 칸 계획분 제외)
                amount = max(0.0, tgt_active - _f(active.get("cost")) - planned)
            else:
                amount = max(0.0, _f(active["base_usd"]) + carry + roll)
                amount = min(amount, max(0.0, tgt_active - _f(active.get("cost")) - planned))     # v2.2.6 B4: F 목표를 못 넘게
            q = rnd(amount / p) if amount > 0 and p > 0 else 0
            if q < 1:
                notes.append(f"{labs.get(active['id'], '새 F')} ${p:.2f} 칸 금액 ${amount:,.2f} < 0.5주 — 생략 (금액은 다음 칸으로 넘김)")
                roll += amount
                continue
            roll = 0.0
            cost = q * p
            desc = (f"탑쌓기 {labs.get(active['id'], '새 F')} ${p:.2f} 칸 (칸당 ${_f(active['base_usd']):,.0f}"
                    + (f" + 이월 ${carry:,.0f}" if carry > 0.5 else "") + (", 마지막 칸" if is_last else "") + ")")
            meta = {"floor_id": active["id"], "new_floor": meta_nf, "closes": list(closes), "plan_usd": round(amount, 2), "carry_used": round(carry, 2)}
            if ly["cap_out"] is not None:
                meta["cap_levels"] = list(ly["cap_out"])             # v2.2.14: 체결 반영 때 이 F의 칸을 (산 칸 + 상한 칸) 으로 바꿈
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
                stop = True                                              # v2.2.17: 현금·한도가 모자라 멈추면 이 F의 남은 칸도, 그 뒤 F도 안 삼
                break
            spent += cost
            planned += amount
            orders.append(dict({"side": "BUY", "type": otype, "qty": q, "price": p, "kind": "buy_tower", "level": p, "idx": None, "credit": 0.0, "desc": desc}, **meta))
    info["tower"]["layers"] = [{"id": ly["f"]["id"], "new_floor": ly["new"], "unit_usd": ly["f"]["base_usd"], "cells": ly["cells"], "levels": ly["levels"],
                                "filled": ly["filled"], "open_cap": ly["oc"]} for ly in layers]
    if first:
        info["tower"]["cells"] = first["cells"]                      # 예전 키: 첫 F(맨 위)의 칸별 배정
    if not layers and not notes:
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
    """매수가 들어간 F의 완성·닫힘 정리 (이 F의 매도 금지는 매수 체결로 풀림 / 닫힐 때도 풂)"""
    f["rebuy_pending"] = False
    if is_complete(f):
        f["done"], f["closed"], f["levels"], f["settled"], f["carry_usd"] = True, False, [], [], 0.0
    elif f["levels"] and all(p in f["settled"] for p in f["levels"]):
        f["closed"] = True                                       # 칸을 다 썼는데 미완성: 부족분(carry_usd)은 그대로 두고 미완성 F로


def _absorb_into_open_floor(st, order, q, amt):
    """새 F 계획 매수 체결을, 위에 있는 미완성 F(1층)의 안 산 칸에 넣음 → (남은 수량, 남은 금액).
    Muse 검증 고침: 칸 판정은 주문 지정가(order["level"]) 기준 ±0.01 (반올림 허용). 체결 평균가(amt/q)는 원가 계산에만 씀.
    이유: 체결 평균가만으로 칸을 찾으면 지정가 이하로 체결된 주문이 엉뚱한 칸에 들어감 (예: 2층 $42.59 주문이 $42.59에 체결됐는데 1층 $43.59 칸으로 감 — 주문이 노린 칸이 아님).
    지정가 $43.59 주문이 $43.00에 체결돼도 $43.59 칸으로 감 (주문이 노린 칸). B3: 닫으라는 F(closes)는 건너뜀. B4: F 원가가 목표를 넘지 않게 정수 주 내림으로 상한 — 넘치는 주식은 남은 수량으로 돌려줘 새 층이 받음.
    넣은 직후 칸 금액(base_usd)을 (목표 − 원가) ÷ 안 산 칸 수 로 다시 계산 (B4). B5: 흡수한 가격은 새 F의 settled 가 되도록 st["absorbed"] 에 적어 둠"""
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
    if f is None and not isinstance(nf, dict):
        f = _by_moved_id(st, order.get("floor_id"))
    if not isinstance(nf, dict):
        f = _split_rest(st, f) or f
    amt0 = amt
    if f is None and isinstance(nf, dict):                           # 새 F 계획 (그 F는 아직 없음)
        q, amt = _absorb_into_open_floor(st, order, q, amt)          # v2.2.5·v2.2.6: 위에 미완성 F가 있으면 그 F 빈칸 먼저
        if q <= 0:
            return
        f = _floor(nf["id"], 0, 0.0, nf["target"], "build")
        f["levels"], f["base_usd"] = list(nf["levels"]), float(nf["base_usd"])
        f["settled"] = [p for p in (st.get("absorbed") or {}).get(str(int(_f(nf["id"]))), []) if p in f["levels"]]     # B5
        st["floors"].append(f)
        st["next_id"] = max(int(_f(st.get("next_id"))), int(nf["id"]) + 1)
    if f is None:
        return
    if order.get("cap_levels"):                                      # v2.2.14 시초가 상한: 이 F의 칸을 '이미 산 칸 + 상한 칸' 으로 (같은 주문들이 몇 번 들어와도 결과 같음)
        f["levels"] = sorted({round(_f(p), 2) for p in (f.get("settled") or [])} | {round(_f(p), 2) for p in order["cap_levels"]}, reverse=True)
    f["qty"] = int(f["qty"]) + q
    f["cost"] = round(_f(f["cost"]) + amt, 4)
    lv = round(_f(order.get("level")), 2)
    if lv not in (f.get("settled") or []):
        f.setdefault("settled", []).append(lv)
    f["carry_usd"] = round(_f(f.get("carry_usd")) - _f(order.get("carry_used")) + (_f(order.get("plan_usd")) - amt0), 2)   # 못 산 금액 이월 (계획 대비 — 1층으로 나눠 들어간 몫도 산 것으로 침)
    for cid in order.get("closes") or []:
        c = _by_id(st, cid)
        if c is not None and c is not f:
            c["closed"], c["rebuy_pending"] = True, False            # 닫힌 F의 매도 금지는 닫을 때 전부 푼다 (사용자 결정)
    _after_buy(f)


def _apply_sniper_buy(st, order, q, amt, gap, start_usd):
    """v2.2.20 스나이퍼 매수 체결 반영: 주문의 floor_id F(없으면 new_floor 로 새 F)에 수량·원가를 더함. 칸(levels) 계산은 안 씀.
    F 원가가 목표에서 TOL_USD 이내로 모자라거나, 남은 몫(목표 − 원가)이 체결 평균가 1주보다 작으면 완성(done). 아니면 남은 시드를 다음 스나이퍼 매수가 채우도록 미완성으로 둠 (탑쌓기로 바꿔도 칸은 _topup_setup 이 준비)"""
    f = _by_id(st, order.get("floor_id"))
    nf = order.get("new_floor")
    if f is None and not isinstance(nf, dict):
        f = _by_moved_id(st, order.get("floor_id"))
    if not isinstance(nf, dict):
        f = _split_rest(st, f) or f
    if f is None and isinstance(nf, dict):
        f = _floor(nf["id"], 0, 0.0, nf["target"], "sniper")
        f["indep"] = bool(nf.get("indep"))                            # v2.4.0: 스나이퍼 선택으로 만든 F는 평단이 위 F보다 높아도 합병하지 않음
        st["floors"].append(f)
        st["next_id"] = max(int(_f(st.get("next_id"))), int(nf["id"]) + 1)
        eid = order.get("empty_id")
        if eid:
            st["empty"] = [e for e in (st.get("empty") or []) if str(e.get("id")) != str(eid)]
    if f is None:
        return
    bs = sync_boxes(st, f)                                            # v2.6.0: 사기 전 보유분을 버킷으로 정리 (예전 상태면 1버킷)
    ono = str(order.get("no") or "").strip()
    hit = next((b for b in bs if ono and b.get("ono") == ono), None)  # 같은 주문의 부분 체결은 한 버킷으로 모음 (매수 체결 1건 = 버킷 1개)
    new_box = None
    if hit is not None:
        hit["qty"], hit["cost"] = int(hit["qty"]) + q, round(_f(hit["cost"]) + amt, 4)
    else:
        new_box = {"id": next_box_id(st), "qty": int(q), "cost": round(amt, 4), "ono": ono}
        bs.append(new_box)
    f["boxes"] = bs
    f["qty"] = int(f["qty"]) + q
    f["cost"] = round(_f(f["cost"]) + amt, 4)
    f["rebuy_pending"], f["closed"] = False, False
    need = _f(f.get("target") or FLOOR_USD) - _f(f["cost"])
    if is_complete(f) or need < amt / q - 1e-9:
        f["done"], f["levels"], f["settled"], f["base_usd"], f["carry_usd"] = True, [], [], 0.0, 0.0
        f["boxes"] = []                                               # v2.6.0: F 완성 = 탑 매도 F (버킷별 매도 끝)
    else:
        _topup_setup(f, gap, start_usd)
        f["rebuy_pending"] = False
        if new_box is not None:
            _tag_on_buy(st, f, new_box)                                   # 판 37 후속: 새 버킷 태그(GRID_L1~L7) — 원작 매수 때 층 재배치


def _tag_on_buy(st, f, new_box):
    """판 37 후속(Muse Q6: 원작대로): 스나이퍼 매수 1건이 큐(미완성 F 의 버킷 전체)에 들어올 때 원작 vrev_add_quota_lot_and_merge_2tier 규칙으로 모든 버킷의 층 태그를 다시 정해 box["lot_type"] 에 저장.
    7층 초과분은 L2_L7_MERGE_SORT 로 같은 7층 태그를 달아 한 층으로 봄 (장부 버킷은 주문 단위라 따로 남김). 태그 없는 예전 버킷은 지금 동적 규칙(가장 싼 것 = 1층)으로 처음 태그를 붙인 뒤 이어감.
    매수로 F 가 완성돼 버킷이 비워지는 경우는 안 부름 (그 버킷은 큐를 떠남)"""
    import grid_tiers as GT
    items, where = [], {}
    nkey = (int(_f(f.get("id"))), int(new_box["id"]))
    for g in top_down(st):
        if int(_f(g.get("qty"))) <= 0 or is_tower(g):
            continue
        bs = sync_boxes(st, g)
        for b in bs:
            key = (int(_f(g.get("id"))), int(b["id"]))
            where[key] = b                                                # sync_boxes 가 F 의 boxes 를 복사본으로 바꾸므로 지금 F 에 들어 있는 객체를 잡음
            if key != nkey:
                items.append({"key": key, "qty": int(b["qty"]), "cost": _f(b["cost"]), "lot_type": b.get("lot_type")})
    tags = GT.tags_on_buy(items, nkey, int(new_box["qty"]), _f(new_box["cost"]))
    for k, tag in tags.items():
        if k in where:
            where[k]["lot_type"] = tag


def _apply_sell(st, order, q, amt, gap, start_usd):
    """매도 체결 반영. 주문에 floor_id 가 있으면 그 F만 (v2.2.6 F별 매도). 없으면(예전 주문) 예전처럼 F별 보유 비율대로.
    잔여 원가 계산에 쓴 '뺀 원가'는 st["_cost_removed"] 에 임시로 둠 (main 이 장부에 같은 값을 쓰고 지움 — 파일에 저장하지 않음)"""
    floors = top_down(st)
    was_complete = [f for f in floors if is_complete(f)]             # v2.16.0 판 43: 매도 전 완성 F
    removed, sold = 0.0, []
    tf = _by_id(st, order.get("floor_id")) if order.get("floor_id") is not None else None
    rest = _split_rest(st, tf) if order.get("mode") == "sniper" else None
    if rest is not None:                                             # v2.16.0 Q5: 나누기 전에 나간 버킷 매도 → 공사중 F 에서 먼저 빼고, 모자라는 몫만 완성 F 에서 (미완성 F 1개 유지)
        k = min(q, int(_f(rest.get("qty"))))
        _apply_sell(st, dict(order, floor_id=int(rest["id"]), box_id=None), k, amt * k / q, gap, start_usd)
        first = _f(st.pop("_cost_removed", 0.0))
        if q > k:
            tf.pop("split_to", None)
            _apply_sell(st, dict(order, box_id=None), q - k, amt * (q - k) / q, gap, start_usd)
            first += _f(st.pop("_cost_removed", 0.0))
        st["_cost_removed"] = round(first, 4)
        return
    if tf is not None:
        a = min(q, int(_f(tf.get("qty"))))
        bid = order.get("box_id")
        box = None
        if a > 0 and bid is not None and order.get("mode") == "sniper":      # v2.6.0 버킷별 매도: 그 버킷만 줄임 (F 원가·수량도 그 버킷 몫만큼만)
            bs = sync_boxes(st, tf)
            box = next((b for b in bs if int(b["id"]) == int(_f(bid))), None)
        if box is not None:
            a = min(a, int(box["qty"]))
            c = _f(box["cost"]) if a == int(box["qty"]) else _f(box["cost"]) * a / int(box["qty"])
            box["qty"], box["cost"] = int(box["qty"]) - a, round(max(0.0, _f(box["cost"]) - c), 4)
            tf["boxes"] = [b for b in bs if int(b["qty"]) > 0]
            tf["qty"] = int(tf["qty"]) - a
            tf["cost"] = round(max(0.0, _f(tf["cost"]) - c), 4)
            removed = round(c, 4)
            sold = [tf]
        elif a > 0:
            c = _f(tf.get("cost")) if a == int(tf["qty"]) else _f(tf.get("cost")) * a / int(tf["qty"])
            tf["qty"] = int(tf["qty"]) - a
            tf["cost"] = round(max(0.0, _f(tf["cost"]) - c), 4)
            tf["boxes"] = []                                         # v2.6.0: F 단위 매도(탑 매도·예전 주문) 뒤 남은 주식은 버킷 1개로 봄 (평단 = F 평단)
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
        for f, a in zip(floors, cuts):                               # F 평단은 그대로 두고 수량·투자금만 줄임
            if a > 0:
                f["qty"] = int(f["qty"]) - a
                f["cost"] = round(max(0.0, _f(f["cost"]) - a * floor_avg_before(f, a)), 4)
                sold.append(f)
        left_q = tq - min(q, tq)
        want = round(before_cost * left_q / tq, 4)                   # 장부와 같은 규칙: 남은 원가 = 이전 원가 × 남은 수량 ÷ 이전 수량
        live = [f for f in floors if int(f["qty"]) > 0]
        if live:
            live[-1]["cost"] = round(_f(live[-1]["cost"]) + (want - sum(_f(f["cost"]) for f in live)), 4)   # 반올림 차이는 가장 최근 F가 흡수
        removed = round(before_cost - want, 4)
    st["floors"] = [f for f in st["floors"] if int(_f(f.get("qty"))) > 0]
    for f in sold:
        if int(_f(f.get("qty"))) > 0:
            if order.get("mode") == "sniper":                        # v2.3.0 스나이퍼 부분 매도 잔여: 완성으로 바꾸지 않음(미완성 F였으니 그대로 미완성 — 스나이퍼가 계속 사고 팖). 탑업 칸 준비 안 함
                f["done"], f["levels"], f["settled"], f["base_usd"], f["carry_usd"], f["rebuy_pending"] = False, [], [], 0.0, 0.0, False
                continue
            _topup_setup(f, gap, start_usd)                          # 팔린 F만 탑업 준비 (v2.2.6)
            f["rebuy_pending"] = not f.get("done")                   # 다시 살 게 없는(완성) F는 매도 금지를 걸지 않음 — 걸면 풀 매수가 영영 없음
            if not f.get("done"):                                    # v2.5.0 판 25: 탑 매도로 일부 비워진 F는 잠금을 풀어 다시 공사중 버킷으로 (스나이퍼가 채움 · 채워지면 다시 완성 F)
                f["locked"] = False
    if any(int(_f(f.get("qty"))) > 0 and not is_complete(f) for f in was_complete):
        st["empty"] = []                                             # v2.16.0 판 43: 완성 F가 다시 미완성 → 빈 F 전부 삭제 (plan_buy 는 빈 F를 미완성 F보다 먼저 채움)
    if (tf is not None and order.get("mode") != "sniper" and any(tf is f for f in was_complete) and int(_f(tf.get("qty"))) > 0 and not is_complete(tf)
            and any(not any(f is w for w in was_complete) and not is_complete(f) for f in st["floors"])):
        tf["merge_due"] = str(order.get("no") or "")                 # v2.16.0 Q1: 탑 매도로 미완성 F가 2개 → 합치기 예약 (부분 체결 중에는 F 번호를 유지)
    st["_cost_removed"] = removed


def floor_avg_before(f, a):
    """(예전 주문용 비례 매도) 이미 수량을 줄인 F의 '줄이기 전 평단' = 원가 ÷ (남은 수량 + a)"""
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
    elif kind == "buy_sniper":
        _apply_sniper_buy(st, order, q, amt, gap, start_usd)
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
    if order.get("kind") == "sell" and cq >= int(_f(order.get("qty"))):
        merge_due(st, gap, start_usd, no=no)                          # v2.16.0 Q1: 매도 주문이 전량 체결되면 합침
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
    ② 새 F 계획 매수(그 F가 아직 없는 buy_tower)는 같은 날 매도를 다 반영한 뒤로 미룸 — 매도로 1층이 미완성이 되면 그 매수가 1층 빈칸으로 들어가게 (B1)"""
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
    (v2.2.6: 주문번호가 있으면 누적 체결 기준으로 증분만 반영 — 같은 체결을 두 번 넣어도 F가 안 바뀜)"""
    if fill is None:
        return st
    if str(order.get("no") or "").strip():
        apply_fill_delta(st, order, fill[0], fill[1], gap, start_usd)
        return st
    return apply_fill(st, order, fill[0], fill[1], gap, start_usd)


def add_holdings(st, qty, avg, s=None):
    """v2.2.6 (사용자 결정): 토스 등에서 들어온 N주(평단 avg)는 '1F 빈곳'에 넣고, 그 F의 새 평단 기준으로 탑쌓기 로직대로 나머지 빈칸을 채운다.
    위에서부터 처음 미완성 F에 수량·원가를 더함 (미완성 F가 없으면 가장 아래 F — 매일 동기화가 하는 것과 같음). F가 없으면 1F를 새로 만듦.
    F가 목표 안에 들어오면 완성, 아니면 탑업 칸(그 F 평단 −1 ~ −간격)·칸 금액을 새 평단으로 다시 정함. → (F id, 알림 글자 목록)"""
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
        return 1, [f"F 없음 → 입고 {q}주를 1F로 만듦 (평단 ${a:.2f})"]
    f = next((x for x in live if not is_complete(x)), live[-1])
    bs = sync_boxes(st, f) if not is_tower(f) else []                  # v2.6.0: 입고분은 버킷 1개로 더함
    if bs or not is_tower(f):
        bs.append({"id": next_box_id(st), "qty": q, "cost": round(q * a, 4), "ono": ""})
        f["boxes"] = bs
    f["qty"] = int(f["qty"]) + q
    f["cost"] = round(_f(f["cost"]) + q * a, 4)
    if is_complete(f):
        f["boxes"] = []
        f["done"], f["closed"], f["levels"], f["settled"], f["carry_usd"] = True, False, [], [], 0.0
        f["rebuy_pending"] = False
        tail = f"{floor_labels(st).get(int(_f(f['id'])), price_label(floor_avg(f)))}이 완성돼요"
    else:
        _topup_setup(f, gap, start_usd)
        tail = f"남은 빈칸 ${max(_f(f.get('target') or fu) - _f(f['cost']), 0):,.0f} 는 탑쌓기로 매수 (칸 {len(f['levels'])}개)"
    fid = int(_f(f["id"]))
    lab = floor_labels(st).get(fid, price_label(floor_avg(f)))
    return fid, [f"입고 {q}주를 {lab} 빈곳에 넣음 → {lab} {int(f['qty'])}주 · 평단 ${floor_avg(f):.2f} · {tail}"]


# ---------------------------------------------------------------- 동기화 · 정리
def _merge(a, b, gap, start_usd=0.0, st=None):
    m = _floor(min(int(a["id"]), int(b["id"])), int(a["qty"]) + int(b["qty"]), _f(a["cost"]) + _f(b["cost"]), max(_f(a["target"]), _f(b["target"])), "merged")
    _topup_setup(m, gap, start_usd)
    if not is_tower(m) and not (a.get("locked") or b.get("locked")):       # v2.6.0: 합친 F가 미완성이면 두 F의 버킷을 이어 붙임 (번호가 겹치면 새로 발급)
        seen, mb = set(), []
        for b0 in boxes_view(a) + boxes_view(b):
            if b0["id"] in seen:
                b0 = dict(b0, id=(next_box_id(st) if st is not None else max([x["id"] for x in mb] + [0]) + 1))
            seen.add(b0["id"])
            mb.append(b0)
        m["boxes"] = mb
    m["locked"] = bool(a.get("locked") or b.get("locked"))                                     # v2.4.0: 잠금은 이어짐
    m["rebuy_pending"] = bool((a.get("rebuy_pending") or b.get("rebuy_pending")) and not m["done"])      # 합쳐도 금지는 이어짐 (다시 살 게 없으면 풂)
    return m


def merge_due(st, gap=GAP_USD, start_usd=0.0, no=None):
    """v2.16.0 판 43 Q1: 합치기 예약(merge_due)이 있는 F를 원래 있던 미완성 F(여럿이면 가장 위)에 합침. 주식수·원가는 합산 (평단 = 원가 가중평균), id 는 원래 있던 F 것을 유지.
    no 를 주면 그 매도 주문의 예약만, 없으면 전부. 그 사이 둘 중 하나가 완성됐거나 없어졌으면 합치지 않고 예약만 지움. → 알림 글자 목록"""
    notes = []
    for src in [f for f in top_down(st) if "merge_due" in f and (no is None or f["merge_due"] == no)]:
        key = src.pop("merge_due")
        if int(_f(src.get("qty"))) <= 0 or is_complete(src):
            continue
        dst = next((f for f in top_down(st) if f is not src and "merge_due" not in f and int(_f(f.get("qty"))) > 0 and not is_complete(f)), None)
        if dst is None:
            continue
        m = _merge(dst, src, gap, start_usd, st)
        m["id"] = int(dst["id"])                                      # 원래 있던 F 번호 유지 (그 F에 이미 나간 주문의 floor_id 가 계속 맞음)
        _topup_setup(m, gap, start_usd)
        m["rebuy_pending"] = bool((dst.get("rebuy_pending") or src.get("rebuy_pending")) and not m["done"])
        m["indep"] = bool(dst.get("indep") or src.get("indep"))
        m["keep_once"] = True                                         # 다음 normalize 한 번은 꼬인 F 합병에서 제외 (합친 평단이 중간 완성 F보다 높아져도 그 F까지 합치지 않음)
        m["merged_ids"] = list(dst.get("merged_ids") or []) + list(src.get("merged_ids") or []) + [int(src["id"])]
        m["merged_sell_nos"] = list(dst.get("merged_sell_nos") or []) + list(src.get("merged_sell_nos") or []) + ([key] if key else [])
        notes.append(f"미완성 F 합치기: {int(src['qty'])}주·${_f(src['cost']):,.2f} + {int(dst['qty'])}주·${_f(dst['cost']):,.2f} → {m['qty']}주 평단 ${floor_avg(m):.2f}")
        rest = _split_over(st, m, gap, start_usd) if _f(m["cost"]) > _f(m["target"]) + 1e-6 else None
        st["floors"] = [m if f is dst else f for f in st["floors"] if f is not src]
        if rest is not None:
            st["floors"].append(rest)
            notes.append(f"목표 초과분 분리: 완성 F {m['qty']}주·${_f(m['cost']):,.2f} + 새 공사중 F {rest['qty']}주·${_f(rest['cost']):,.2f} (평단 ${floor_avg(rest):.2f})")
    return notes


def _split_over(st, m, gap, start_usd=0.0):
    """v2.16.0 판 43 Q5: 합친 F m 의 원가가 목표를 넘을 때 — m 은 목표를 안 넘는 가장 큰 정수 주식수의 완성 F 로 줄이고, 나머지(평단 같음, 원가 합 보존)를 담은 새 공사중 F 를 돌려줌 (st["floors"] 에는 부른 쪽이 넣음). 나눌 수 없으면 None"""
    q, c, tg = int(m["qty"]), _f(m["cost"]), _f(m["target"])
    avg = c / q
    n = int(math.floor(tg / avg + 1e-9))
    if not 1 <= n < q:
        return None
    full_cost = min(round(n * avg, 4), tg)
    nid = max(int(_f(st.get("next_id"))), max(int(_f(f.get("id"))) for f in st["floors"]) + 1)
    rest = _floor(nid, q - n, c - full_cost, tg, "merged")
    _topup_setup(rest, gap, start_usd)
    rest["rebuy_pending"] = bool(m.get("rebuy_pending") and not rest["done"])
    rest["indep"] = True                                              # 완성 F 와 평단이 같아서, 이 표시가 없으면 normalize 가 둘을 다시 합침
    rest["merged_sell_nos"] = list(m.get("merged_sell_nos") or [])    # 새 F 도 오늘은 매도 안 함 (방금 판 F의 잔여분이 섞여 있음)
    rest["merged_ids"] = m.pop("merged_ids", [])                      # 없어진 F 번호의 늦은 매수는 공사중 F 로
    st["next_id"] = nid + 1
    m.update(qty=n, cost=full_cost, done=True, closed=False, levels=[], settled=[], base_usd=0.0, carry_usd=0.0, rebuy_pending=False, locked=False, boxes=[])
    m["split_to"] = nid                                               # 원래 F 번호로 이미 나간 주문의 늦은 체결 → 공사중 F (매수는 거기에, 스나이퍼 매도는 거기서 먼저)
    return rest


def _split_rest(st, f):
    """v2.16.0 Q5: f 가 방금 나눈 완성 F 이면 짝이 되는 공사중 F, 아니면 None"""
    return _by_id(st, f.get("split_to")) if f is not None and f.get("split_to") is not None else None


def _by_moved_id(st, fid):
    """v2.16.0 Q1: 합쳐져 없어진 F 번호로 낸 매수의 체결 → 합친 F"""
    return next((f for f in st.get("floors") or [] if fid is not None and int(_f(fid)) in (f.get("merged_ids") or [])), None)


def merged_floor_ids(st, sell_nos):
    """v2.16.0 Q1: sell_nos(오늘 매도 주문번호들)의 매도 잔여분을 받은 F id 집합 — 방금 판 잔여분이 같은 날 다시 팔리지 않게 main 이 그 F의 매도를 건너뜀"""
    nos = {str(n) for n in sell_nos if n}
    return {int(f["id"]) for f in st.get("floors") or [] if nos & set(f.get("merged_sell_nos") or [])}


def normalize(st, gap=GAP_USD, start_usd=0.0):
    """수량 0 인 F 정리 → 꼬인 F 합병(위 F보다 평단이 같거나 높으면 가중평균으로 합침) → 평단 오름차순 재배치(id 는 위에서부터 다시 붙임). → 알림 글자 목록"""
    notes = []
    ensure_state(st)
    st["absorbed"] = {}                                              # 새 F id 는 매일 정리 때 다시 붙으니 하루 지나면 비움 (B5)
    fl = [f for f in top_down(st) if int(_f(f.get("qty"))) > 0]
    out = []
    for f in fl:
        cur = f
        while out and floor_avg(cur) >= floor_avg(out[-1]) - 1e-9 and not (cur.get("indep") or out[-1].get("indep") or cur.get("keep_once") or out[-1].get("keep_once")):
            top = out.pop()
            notes.append(f"F 합병: 평단 ${floor_avg(top):.2f} + 평단 ${floor_avg(cur):.2f} → 수량 {int(top['qty']) + int(cur['qty'])}주")
            cur = _merge(top, cur, gap, start_usd, st)
        out.append(cur)
    out.sort(key=lambda f: -floor_avg(f))                            # 위(평단 높은 F)부터 번호를 다시 붙임
    for i, f in enumerate(out, 1):
        f["id"] = i
        f.pop("keep_once", None)
        f.pop("merged_ids", None)                                     # 번호를 다시 붙였으니 옛 번호 기록은 뜻이 없음
        f.pop("split_to", None)
    st["floors"] = sorted(out, key=floor_avg)                        # 저장은 평단 오름차순 (수량·투자금 보존)
    st["next_id"] = len(out) + 1
    return notes


def reconcile(st, qty, principal, gap=GAP_USD, s=None):
    """v2.2.4: 맨 위 F 시작가(tower_floor1_start_usd)가 정해졌으면 normalize(합병)에도 넘김"""
    start_usd = _f((s or {}).get("tower_floor1_start_usd"))
    """매일 동기화: F 합계가 장부(실제 보유분)와 다르면 장부에 맞춤 — 차이는 가장 최근 F(가장 아래 F)가 흡수. 그 뒤 꼬인 F 정리.
    → (st, 알림 글자 목록). 장부가 0주면 F를 비움"""
    fu, _fl, _g = params(s)
    ensure_state(st)
    qty, principal = int(_f(qty)), _f(principal)
    notes = []
    if qty <= 0:
        if st.get("floors"):
            notes.append("장부 0주 — F 상태를 비움")
        st["floors"], st["next_id"], st["empty"] = [], 1, []
        return st, notes
    if not st.get("floors"):
        keep = st.get("applied") or {}
        st.update(migrate_from_holdings(qty, principal, s))
        st["applied"] = keep                                          # 반영한 주문번호 기록은 지키지 않으면 같은 체결을 다시 넣을 수 있음
        notes.append(f"F 없음 → 현재 보유분 {qty}주를 1F로 만듦")
        return st, notes
    notes += merge_due(st, gap, start_usd)                           # v2.16.0 Q1: 부분 체결로 끝난 탑 매도의 합치기 (합계는 안 바뀜)
    tq, tc = totals(st)
    dq, dc = qty - tq, round(principal - tc, 4)
    if dq != 0 or abs(dc) > 0.01:
        notes.append(f"F 상태 조정: F 합계 {tq}주·${tc:,.2f} → 장부 {qty}주·${principal:,.2f} (차이 {dq:+d}주·${dc:+,.2f}를 가장 최근 F가 흡수)")
        fl = sorted(st["floors"], key=lambda f: -int(_f(f.get("id"))))      # 가장 아래(최근) F부터
        rest_q, rest_c = dq, dc
        for f in fl:
            take_q = max(rest_q, -int(f["qty"])) if rest_q < 0 else rest_q
            if not is_tower(f):
                sync_boxes(st, f)                                     # v2.6.0: 조정 전에 버킷을 F와 맞춰 둠 (조정 뒤 fit_boxes 가 차이를 마지막 버킷에 넣음)
            f["qty"] = int(f["qty"]) + take_q
            rest_q -= take_q
            take_c = max(rest_c, -_f(f["cost"])) if rest_c < 0 else rest_c
            f["cost"] = round(_f(f["cost"]) + take_c, 4)
            rest_c = round(rest_c - take_c, 4)
            if f.get("boxes"):
                fit_boxes(st, f)
            if rest_q == 0 and abs(rest_c) <= 0.01:
                break
        if rest_q > 0 and fl:
            fl[0]["qty"] = int(fl[0]["qty"]) + rest_q
            fl[0]["boxes"] = []
        if rest_c > 0.01 and fl:
            fl[0]["cost"] = round(_f(fl[0]["cost"]) + rest_c, 4)
            fl[0]["boxes"] = []
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
    """F 채움 비율 = 원가 ÷ 목표 (0~1)"""
    tg = _f(f.get("target") or FLOOR_USD)
    return min(1.0, max(0.0, _f(f.get("cost")) / tg)) if tg > 0 else 0.0


DIAG_HALF = "◧"           # 미완성 F 한 칸에 그리는 사선 (반만 찬 표시, v2.2.7)


def layer_marker(f):
    """v2.2.7 반칸 표시 (사용자 결정: 2칸 중 1칸이 아니라 한 칸에 사선). F 하나 = 한 칸.
    완성 → F 색 (🟩) · 미완성 → 사선 한 칸 (◧)"""
    if is_complete(f):
        return layer_block(f)
    return DIAG_HALF


def floor_status(f):
    """F 상태 글자: 완성 | 공사중 (v2.5.0 — 완성이 아니면 전부 공사중(=판 24 까지의 '미완성'))"""
    return "완성" if is_complete(f) else "공사중"


def _fmt_layers(total):
    """F 수 표시: 완성 F 1 + 미완성 F는 채움 비율만큼 (v2.2.7). 0.48 → '0.48', 1.5 → '1.5', 2.0 → '2'."""
    s = f"{total:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def view_lines(st, s=None):
    """탑쌓기 F 시각화 글자 줄. 채워진 F(수량 > 0)만 보임 — 비어 있는 F는 안 보임.
    첫 줄: F마다 한 칸 마커(완성 🟩 · 미완성 ◧ 사선, 색은 1층 🟩 · 2층 🟦 · 3층 🟨 · 4층 🟧 · 5층 🟥 · 6층 🟪 · 7층 🟫 · 8층 ⬛ · 9층 ⬜ · 10층 🟩) + 'N/최대F' (N은 채움 비율 합계, 1층 48%면 0.48).
    다음 줄들: F별 '48F2 · 평단 $48.59 · 149주 · 미완성 (48%)' (위에서부터, % = 원가 ÷ F 목표).
    평단 = F 투자금(실제 체결 합계) ÷ 수량 = 가중평균. 상태가 비었거나 이상하면 0F"""
    fl = [f for f in top_down(st if isinstance(st, dict) else {}) if int(_f(f.get("qty"))) > 0]
    if not fl:
        return ["탑: 0F (채운 F 없음)"]
    total = sum(1.0 if is_complete(f) else fill_ratio(f) for f in fl)
    lines = [f"탑: {' '.join(layer_marker(f) for f in fl)}  {_fmt_layers(total)}F"]
    labels = floor_labels(st)
    for f in fl:
        lines.append(f"{labels.get(int(_f(f.get('id'))), price_label(floor_avg(f)))} · 평단 ${floor_avg(f):.2f} · {int(_f(f.get('qty')))}주 · {floor_status(f)}"
                     + ("" if is_complete(f) else f" ({int(round(fill_ratio(f) * 100))}%)"))
    return lines
