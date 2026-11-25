# ==========================================================
# FILE: meritz_laoer/sniper_mode.py   (MERITZ_LAOER v2.12.0)
# v2.12.0 (2026-11-24, 판 39): ① first_buy_signal·exec_price 신설 — 보유 층 0개 = 원작 분기 A: 가격 조건 없이 현재가(소수 2자리 내림), 검문 순서 15:00 컷오프 → 개장 7분 쉴드 → 직전 1분봉 무머리 HA음봉 ② plan_buy(ha=)·make_plan(ha=) ③ anchor_info 에서 첫 기준가(sniper_first_anchor_usd) 삭제 ④ 레이더 문구 3곳 교체(NO_ANCHOR·trigger_lines)
# v2.11.0 (2026-11-24, 판 38 시간 확대): STATUS_*·SELL_STATUS·BUY_STATUS·sell_ok·buy_ok 추가 (원작 is_active_buy_window 04:07~16:00 · is_active_sell_window 04:00~04:06 제외 전 구간 을 어댑터로 그대로 부름). 10분 게이트는 sub_grid.gate_status 가 04:07 부터 엶. 15:00 신규 진입 컷오프·개장 7분 쉴드(09:30~09:36)는 그대로 — 컷오프는 15:00~16:00 에만, 쉴드는 정규장 개장 직후에만 걸려 프리장 매수와 겹치지 않음
# v1.4.4 (판 37 Case 113 이식 + 후속 — 버전 번호는 Muse 지정 전이라 미확정): ① 개장 7분 쉴드 매번 적용 ② 10분 게이트(04:07 ET 기점·정규장 안, 보유 층이 있을 때 추가매수만) ③ 상한 가드·기준가 상한 = 가장 낮은 층 평단(그대로) ④ 눌림 계단(-1/-2/-3.5/-5.5) 유지(항목 2 취소) ⑤ 층 태그 GRID_L1~L7 고정·7층 상한·L2_L7_MERGE_SORT 합병 (grid_tiers.py·tower_strategy._tag_on_buy·sniper_adapter.tiered — 1층이 팔리면 새 1층 안 생김) ⑥ 2층 공석 돌파 연결(OFF — 원작 Case 113 폐기). 항목 6(시간외)은 미적용 → 노션 질문
# v2.10.0 (2026-11-23, 판 36 Case 113 이식): 원작 복사본 5개를 7718e29 로 교체한 뒤 하이브리드 자체 값 정리 — ① 돌파 매수 삭제(BREAKOUT_* 상수·돌파 가격·돌파 매수액 분기) ② 눌림 타점 표시를 원작 결과(pullback_target_price = min(직전 매도가, 최하단 F 평단) 기준)로 맞춤 ③ 서브 그리드 끔(SUB_GRID_ON=False — plan_buy 가 plan_sub 를 안 부름, 서브 상태·체결 반영·수량 동기화 코드는 남김) ④ 신규 진입 컷오프 15:30 → 15:00 (보유 F 0개일 때만 매수 차단) ⑤ 개장 7분 쉴드(09:30~09:36): 보유 F 0개 첫 진입일 때만 원작 신호 함수에 시각(hm) 전달 ⑥ 1층 익절 기본값 1.5 → 1.0 (TP_L1_DEFAULT)
# v2.9.0 6차 (2026-11-22, 판 33): plan_tower_buy 신설(탑쌓기 매매 매수 계획 = TW.make_plan 매수 쪽) · make_plan 미리보기가 tower 모드면 스나이퍼 매수 대신 탑쌓기 매수. 스나이퍼 매수·매도·래칫 계산은 안 바꿈
# v2.9.0 판 32 질문 4·5 (2026-11-22): 1층(가장 낮은 버킷) 고정 +1.5% 매도를 원작 트레일링(점화 +1.5% → 샤프 5단 보존선 · 하드캡 +6.0% · RSI 65 수확)으로 바꿈 — trail_tick 이 메모리 슬롯(상태 파일에 저장 안 함, 재시작하면 다시 계산)을 갱신, 원작 실호가 재확인·매도 하한가·2층 동반 졸업 따라감. box_rows 는 trail_tick 을 한 번이라도 부르면(main) 트레일링 방식, 안 부르면 예전 고정 방식
# v2.9.0 판 31 질문 3 (2026-11-22): 원작식 부분 주문 — plan_sells 가 매도가능이 모자라면 평단 낮은 버킷부터 가능한 만큼만(마지막 버킷은 일부) 주문, 장외 매도가능 0이면 조용히 대기, 정규장 0이면 목표 수량 시도. main 이 주문 전에 매도가능을 2초(0.25초 간격) 기다림
# v2.9.0 판 31 (2026-11-22): 매도 판정(box_rows)을 원작 evaluate_multi_grid_sell_targets(어댑터 sell_plan, 방식 B = 전체 층 그대로)로 바꿈 — 미완성 층 버킷 전체 한 묶음: 1층 +1.5% · 2층 +1.0% · 3층 이상은 개별 매도 없음, 졸업(3층~끝 가중평단 +1.0%)에 닿으면 전량. 탑 매도·매수·서브는 안 바뀜
# v2.9.0 (2026-11-22, 판 30): 신호 판정(buy_signal)을 원작 복사본(sniper_adapter → orig_sniper/quant_engine_core.evaluate_l2_only_hybrid_reentry_signal)으로 바꿈. B1 눌림 깊이 = 버킷 수 · B2 상한 = 가장 낮은 층 평단 · B3 눌림·돌파는 % 로 비교(반올림 목표가 아님) · B3b RSI 모르면 돌파 안 막음. 표시용 눌림·돌파 가격은 그대로. 매도·탑쌓기·서브 매수 규칙은 안 바뀜
# v2.7.0 (2026-11-21, 판 27): 층 간격 설정 제거 — make_plan info에서 'gap' 키 삭제 (계획 미리보기 '새 층 가격' 줄이 없어져서 안 씀). 간격은 내부 고정값 GAP_USD=5로만 씀 (tower_strategy.params).
# v2.6.0 (2026-11-21, 판 26): ① 버킷별 매도 — box_rows(버킷마다 평단 +1.5%(그 층 안 최저 평단 L1) / +1.0%) · plan_sells 가 닿은 버킷만 그 버킷 전량 주문(floor_id + box_id) · sell_rows 층 행에 boxes 추가 ② 눌림 매수% = TW.portion_pct(s) (설정 sniper_portion_pct, 기본 8) ③ trigger_lines 버킷별 줄 · make_plan info['boxes']
# v2.5.0 (2026-11-21, 판 25 하이브리드 버킷·층 — 토스 스나이퍼 이식): ① 매수 = 신호 1번에 버킷 시드의 8%(단리 고정, plan_buy: min(8%, 버킷 남은 시드) → 13번째가 나머지) ② 새 버킷 가격은 신호가 뜰 때 정해짐 — 층 간격(tower_gap_usd)·'새 층 보류' 규칙 삭제, 시초가 상한은 호출한 쪽(main)이 그대로
#   ③ 버킷 안 매도(미완성 층 +1.5% 공격 버킷 / +1.0% 위 버킷, 버킷 전체 전량)는 다시 자동 매도 — 판 24 선택 대기(pick_scan·pick_resolve) 코드는 그대로 두고 부르지 않음, plan_buy 도 선택 대기 층을 안 봄
#   ④ 서브 그리드(Case 88) 4% 매수 plan_sub — sub_grid.py ⑤ 첫 기준가 sniper_first_anchor_usd(기준가·층이 없을 때만) ⑥ 지하층 → 공사중 이름 ⑦ 층 표현 = 평단 정수 달러(row["label"])
#   수정1: 돌파 매수액 별도 설정 sniper_breakout_portion_pct(기본 16%, 눌림 8% 그대로).
#   신호 숫자·돌파 RSI·15:30~16:00 돌파 차단·상한 가드(buy_signal)는 그대로.
# v2.4.0 (2026-11-21, 판 24): ① 잠긴 층(locked)은 스나이퍼 매도 안 함 — 탑 매도만 ② 스나이퍼 목표가에 닿아도 자동 매도 안 함: 층마다 선택 대기(picks) → 텔레그램 버튼 '스나이퍼/탑쌓기'(탑쌓기=잠금, 스나이퍼=층 그대로 + 닿은 목표가를 기준가로 하는 새 빈 층). 무응답=대기(탑쌓기 기본), 대기 중 매수 신호가 오면 바로 새 층 매수(다시 안 물음).
#   ③ 지하층(빈 층, 0주·$0) = st["empty"]: 다음 스나이퍼 매수는 빈 층부터 채움.
# v2.3.0 (2026-11-21, 판 23 하이브리드): 모드 선택 없음(trading_mode·get_mode·mode_ko 삭제) — 항상 하이브리드. 사기=스나이퍼만(눌림·돌파), 팔기: 완성 F(F 완성 기준 금액 도달)은 탑 매도(F 평단 +10% → 50%), 미완성 F(재매수 대기 포함)만 스나이퍼 매도.
#   총 시드·층 수 한도 없음. 새 층은 '가장 낮은 층 평단 − 층 간격(tower_gap_usd, 기본 5)' 이하일 때만 만듦. 탑 매도 체결도 스나이퍼 기준가(직전 익절)를 갱신(note_fills 가 모든 SELL 체결을 받음 — 원래부터).
# v2.2.20 (2026-11-21, 판 22 듀얼 모드): 새 파일 — 스나이퍼 모드 계산부. 순수 계산 + 상태 파일(data/sniper_state.json) 읽기·쓰기 도우미만 (네트워크·시계 없음, 시각은 호출한 쪽이 넘김).
#   toss_sniper(참조, 고치지 않음)에서 가져온 규칙:
#   - 채우기(층 사기): 직전 익절가(기준가) 대비 눌림목 또는 +1.0% 돌파 (quant_engine.evaluate_l2_only_hybrid_reentry_signal 규칙 — 돌파는 RSI(14) <= 50 필터·15:30~16:00 ET 돌파 차단·기준가의 2층 단가 상한 가드 Case 73).
#     눌림 깊이는 보유 층 수에 따라 1-4층 -1.0% · 5-8층 -2.0% · 9-10층 -3.5% (quant_engine.get_golden8_prog_thresholds).
#   - 비우기(층 팔기): 층 평단 + 익절% 에 닿으면 그 층 전량 (quant_engine.evaluate_multi_grid_sell_targets 의 1층 +1.5% · 상단층 +1.0% 개별 판정만. 2~7층 통합이평 졸업(WMA) 판정은 판 22 지시에 없어 안 가져옴).
#   빼거나 바꾼 것(판 22 지시): 바벨·암살자·서브 그리드·지하층·복리(자산 % 회차 크기)·24시간 매도 창·1.5초 간격. 회차 크기는 자산 % 가 아니라 F 완성 기준 금액(tower_floor_usd, 기본 $15,000).
#   F는 탑쌓기와 같은 F(tower_state.json)를 공유. 스나이퍼의 '1층' = 가장 아래 활성 F(평단이 가장 낮은 F = 가장 최근에 채운 공격 층), 나머지는 상단층.
#   RSI(14): 메리츠 분봉 API 는 근거 파일에 없어 미확인 → 봇이 시세를 읽을 때마다 1분 단위로 모은 종가(series)로 Wilder RSI(14)를 계산. 15개가 안 모이면 RSI 를 모른다고 보고 돌파를 막지 않음 (판 30 Q2 결정 — 원작처럼 RSI 를 모르면 돌파 필터만 건너뜀. 눌림은 RSI 무관).
# 상태 파일: {"version": 1, "anchor": 기준가, "anchor_kind": "exit"|"buy"|"avg"|"", "anchor_at": ISO, "last_order_ts": 에포크초, "buy_block_until": 에포크초(매수 거절 뒤 쉬는 시각), "series": [[분 에포크, 종가], ...]}
# ==========================================================
import copy
import datetime
import math
import time

import sniper_adapter as AD
import sub_grid as SG
import tower_strategy as TW
from tower_strategy import ceil2

MODE_SNIPER = "sniper"          # 주문 'mode' 표시 글자 (체결 반영이 스나이퍼 매도를 알아봄). 설정으로 고르는 모드는 없음 (v2.3.0)

TP_L1_DEFAULT = 1.0            # 스나이퍼 1층(공격 층) 익절 % — 설정 sniper_tp_l1_pct (v2.10.0 판 36 D3: Case 113 원작 +1.00% 에 맞춰 1.5 → 1.0)
TP_UPPER_DEFAULT = 1.0         # 상단층 익절 % — 설정 sniper_tp_upper_pct
PULLBACK_TIERS = ((4, -1.00), (8, -2.00), (10, -3.50))      # (보유 층 수 이하, 눌림 %) — 그 위는 PULLBACK_DEEP (참조 get_golden8_prog_thresholds). 판 37 후속(풀이님 정정): 항목 2 취소 — 계단 그대로
PULLBACK_DEEP = -5.50
RSI_PERIOD = 14
LATE_CUTOFF = datetime.time(15, 0)       # 15:00~16:00 ET 신규 진입 차단 (v2.10.0 판 36 D7: 원작 Case 113 컷오프 15:00 — 보유 F 0개일 때만 적용)
SUB_GRID_ON = False                      # v2.10.0 판 36 D2: 서브 그리드 끔 (원작 Case 113 서브 폐기). True 로 바꾸면 plan_sub 가 다시 돈다 (코드는 남겨 둠)
TICK_SEC_DEFAULT = 1.5          # v2.13.0 판 40 할 일 1: 틱 간격 (원작 NORMAL_LOOP_INTERVAL_SEC 1.50). 되돌리기 = 설정 sniper_tick_sec 30
BOUNDARY_WAIT_SEC = 15          # 분 경계 쉴드: 새 분이 시작된 뒤 이 초 안에 직전 분 완결봉이 아직 안 보이면 기다림 (원작 :00.25s 캔들 레이더가 새 완결봉을 받을 때까지 정각 잠금과 같은 뜻)
HA_WAIT_CAP_SEC = 65            # 원작 pullback_ha_wait 잠금 상한 (같은 분 안에서만 유효, 65초 넘으면 풀림)
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


# ---------------------------------------------------------------- F 매핑
def active_floors(st):
    """수량이 있는 F, 위(탑쌓기 번호 1 = 평단 가장 높은 F)부터"""
    return [f for f in TW.top_down(st if isinstance(st, dict) else {}) if int(_f(f.get("qty"))) > 0]


def layer_count(fl):
    """보유 버킷(매수 1건) 수 — 활성 F 들의 버킷 합 (판 30 B1: 눌림 깊이는 F 개수가 아니라 버킷 수 = 회차 수). 버킷 기록이 없는 F 는 1개로 셈 (boxes_view)"""
    return sum(len(TW.boxes_view(f)) for f in fl)


def lowest_layer_avg(fl):
    """가장 낮은 버킷 평단 (판 30 B2: 상한 가드 기준 — 예전엔 F 평단 최소값). F가 없으면 0.0"""
    return min((TW.box_avg(b) for f in fl for b in TW.boxes_view(f)), default=0.0)


def attack_id(st):
    """스나이퍼 '1층'(공격 층) = 활성 F 중 평단이 가장 낮은 F (같으면 번호가 큰 F). 활성 F가 없으면 None"""
    fl = active_floors(st)
    if not fl:
        return None
    return int(_f(min(fl, key=lambda f: (TW.floor_avg(f), -int(_f(f.get("id"))))).get("id")))


# ---------------------------------------------------------------- 비우기 (익절)
def sniper_numbers(st):
    """{탑쌓기 층 id: 스나이퍼 층 번호} — 번호는 평단 낮은 F부터 1, 2, 3 … (1 = 공격 층). 표시·알림 글자용 (주문·장부는 탑쌓기 id 그대로)"""
    order = sorted(active_floors(st), key=lambda f: (TW.floor_avg(f), -int(_f(f.get("id")))))
    return {int(_f(f.get("id"))): i + 1 for i, f in enumerate(order)}


# ---------------------------------------------------------------- 판 32 1층 트레일링 (원작 SniperL1TrailSlot 메모리 슬롯 — 상태 파일에 저장 안 함 = 원작대로, 재시작하면 다시 계산)
TRAIL = {"on": False, "slot": None, "fire": None, "code": ""}


def trail_reset():
    TRAIL.update(on=False, slot=None, fire=None, code="")


def _src_boxes(st):
    """미완성 F의 버킷 전체, 평단 오름차순 (같으면 나중에 산 버킷이 앞). box_rows 와 같은 입력 순서 — 큐 순서(1층 → 상단층)는 어댑터 tiered 가 정함 (판 37 후속: 태그 기준)"""
    src = [(f, b) for f in active_floors(st) if not TW.is_tower(f) for b in TW.boxes_view(f)]
    src.sort(key=lambda fb: (TW.box_avg(fb[1]), -int(fb[1]["id"]), -int(_f(fb[0].get("id")))))
    return src


def _src_layers(src):
    """(F, 버킷) 목록 → 어댑터 층 목록 (태그 lot_type 포함)"""
    return [{"qty": int(b["qty"]), "cost": _f(b["cost"]), "lot_type": b.get("lot_type") or ""} for _f_, b in src]


def trail_tick(st, s, price, now_ts, state):
    """판 32: 거래 루프가 시세를 읽을 때마다 부름 — 1층(가장 낮은 버킷) 슬롯을 맞추고 원작 트레일링 한 번 평가 → 신호가 났으면 {"l1_price", "l2_price"(2층 동반 졸업, 없으면 0), "code"}.
    원작 execute_1m_sniper_sell 흐름을 따름: 신호 뒤 실호가 재확인 — 점화가 밑이면 슬롯 해제(허락보다 용서를) · 보존선 이탈 신호인데 실호가가 보존선 이상이면 취소 · 매도 하한가 = 보존선(없으면 점화가) 이상, 하드캡이면 캡 가격, 보존선 위면 실호가 -0.2% 와 보존선 중 큰 값 · 2층이 활성이고 하한가가 2층 목표(+1.0%) 이상이거나 실호가가 2층 목표 이상이면 2층 동반 졸업.
    완결 분·RSI 는 봇이 모은 1분 종가(state['series']: [분 번호, 종가])에서 만듦. 졸업(전 층 전량)이 닿은 때는 box_rows 가 졸업을 우선"""
    TRAIL["on"] = True
    px = _f(price)
    src = _src_boxes(st)
    lay = _src_layers(src)
    if not src or px <= 0 or not AD.has_l1(lay):                       # 판 37 후속: 1층이 없으면(1층이 팔려 상단층만 남음 — 원작은 새 1층을 안 만듦) 트레일링 슬롯 없음
        if TRAIL["slot"] is not None:
            TRAIL["slot"].full_reset()
        TRAIL.update(fire=None, code="")
        return None
    if TRAIL["slot"] is None:
        TRAIL["slot"] = AD.l1_trail_slot("MAIN")
    slot = TRAIL["slot"]
    f1, b1 = src[AD.queue_order(lay)[0]]
    AD.l1_trail_sync(slot, int(b1["qty"]), TW.box_avg(b1))
    cur_min = int(now_ts // 60)
    closed = [x for x in (state or {}).get("series") or [] if isinstance(x, (list, tuple)) and len(x) == 2 and int(x[0]) < cur_min]
    closed_ts = int(closed[-1][0]) * 60 if closed else None
    rsi = rsi14([x[1] for x in closed]) if closed else None
    code, _ign = AD.l1_trail_step(slot, px, now_ts, closed_ts, rsi)
    TRAIL.update(fire=None, code=code or "")
    if not code:
        return None
    if px < slot.arm_100_p - 1e-9:                                     # 허락보다 용서를: 실호가가 점화가 밑이면 슬롯 해제
        slot.release_forgive()
        TRAIL["code"] = ""
        return None
    stop = slot.refresh_stop_price()
    if code == "TRAIL_CB_STOP" and (stop <= 0.0 or px >= stop - 1e-9):
        TRAIL["code"] = ""
        return None
    lock = slot.lock_floor_p if slot.lock_floor_p > 0.0 else slot.arm_100_p
    if code == "TRAIL_CAP_500" and px >= slot.cap_500_p - 1e-9:
        fl = slot.cap_500_p
    elif px >= lock - 1e-9:
        fl = max(lock, math.floor((px * 0.998 + 1e-9) * 100.0) / 100.0)
    else:
        fl = max(lock, math.floor((px + 1e-9) * 100.0) / 100.0)
    l2p = 0.0
    if len(src) >= 2:
        rows, _res = AD.sell_plan(lay, px, rise_l1_pct=tp_pcts(s)[0], rise_upper_pct=tp_pcts(s)[1], exclude_l1=True)
        l2r = next((r for r in rows if r["role"] == "L2"), None)
        if l2r is not None:
            raw2 = ceil2(TW.box_avg(src[l2r["src"]][1]) * (1 + tp_pcts(s)[1] / 100.0))
            if raw2 <= fl + 1e-9 or px >= raw2 - 1e-9:
                l2p = raw2
    TRAIL["fire"] = {"l1_price": round(fl, 2), "l2_price": l2p, "code": code}
    return TRAIL["fire"]


def box_rows(st, s, price):
    """v2.9.0(판 31) 버킷별 익절 행 — 원작 매도 판정(어댑터 sell_plan, 방식 B = 전체 F 그대로)으로 계산. 미완성 F의 버킷만 (완성·잠긴 F는 탑 매도): floor_id·box_id·label·qty·avg·cost·pct·target·role·reached·gain_pct·floor_avg.
    미완성 F 전체 버킷을 평단 오름차순 한 묶음으로 봄: 가장 낮은 버킷 = L1(+1.5%) · 그 다음 = L2(+1.0%, 닿으면 L1 도 같이) · 3번째 이상은 개별 매도 없음, 졸업(3번째~끝 가중평단 +1.0%)에 닿으면 전 버킷 전량 (role 'grad', target = 졸업 목표가). reached = 원작 sold_indices. 계산만 함 (상태 안 바꿈)"""
    tp1, tpu = tp_pcts(s)
    labs = TW.floor_labels(st)
    px = _f(price)
    src = []
    for f in active_floors(st):
        if TW.is_tower(f):
            continue
        for b in TW.boxes_view(f):
            src.append((f, b))
    src.sort(key=lambda fb: (TW.box_avg(fb[1]), -int(fb[1]["id"]), -int(_f(fb[0].get("id")))))     # 평단 같으면 나중에 산 버킷이 1층 쪽 (판 26 규칙 유지)
    layers = _src_layers(src)
    trail_on = bool(TRAIL.get("on"))
    fire = TRAIL.get("fire") if trail_on else None
    plan, _res = AD.sell_plan(layers, px, rise_l1_pct=tp1, rise_upper_pct=tpu, exclude_l1=trail_on) if layers else ([], {})
    grad = bool((_res or {}).get("reason_tag") == "SELL_ALL_GRAD")
    rows = []
    for pr in plan:
        f, b = src[pr["src"]]
        fid, ba = int(_f(f.get("id"))), TW.box_avg(b)
        role = "L1" if pr["role"] == "L1" else "upper"
        tg = pr["target"] if pr["target"] > 0 else ceil2(ba * (1 + tpu / 100.0))
        pct = tp1 if pr["role"] == "L1" else (tpu if pr["role"] == "L2" else (round((tg / ba - 1) * 100, 2) if ba > 0 else 0.0))
        reached = bool(px > 0 and pr["reached"])
        if trail_on and not grad:                                       # 판 32: 1층은 트레일링 신호로만, 2층은 동반 졸업으로만 (원작)
            if pr["role"] == "L1":
                reached = bool(fire)
                tg = fire["l1_price"] if fire else (TRAIL["slot"].arm_100_p if TRAIL.get("slot") is not None and TRAIL["slot"].arm_100_p > 0 else ceil2(ba * (1 + tp1 / 100.0)))
            elif pr["role"] == "L2":
                reached = bool(fire and fire["l2_price"] > 0)
                if reached:
                    tg = fire["l2_price"]
        rows.append({"floor_id": fid, "box_id": int(b["id"]), "label": labs.get(fid, TW.price_label(TW.floor_avg(f))), "qty": int(b["qty"]), "avg": ba, "cost": round(_f(b["cost"]), 2),
                     "pct": pct, "target": tg, "role": role, "reached": reached, "gain_pct": (round((px / ba - 1) * 100, 2) if px > 0 and ba > 0 else None),
                     "floor_avg": TW.floor_avg(f), "kind": pr["role"] or "none"})
    return rows


def sell_rows(st, s, price):
    """F마다 익절 행 (미완성 F = 스나이퍼 익절 %, 완성 F = 탑 매도 %): id(탑쌓기 F 번호)·no(스나이퍼 F 번호 — 평단 낮은 F가 1)·qty·avg·pct(그 F 익절 %)·target(올림 2자리)·reached·gain_pct(현재가 대비 평단 %)·role(L1|upper)"""
    tp1, tpu = tp_pcts(s)
    aid = attack_id(st)
    nos = sniper_numbers(st)
    labs = TW.floor_labels(st)                                                   # v2.5.0: F 표현 = 평단 정수 달러 + F + 번호
    px = _f(price)
    rows = []
    brows = {}
    for br in box_rows(st, s, price):                                            # v2.6.0: 미완성 F는 버킷별 목표 (F 행의 목표·도달 = 그 F 버킷 중 가장 먼저 닿는 L1 버킷 기준, 도달 = 하나라도 닿음)
        brows.setdefault(br["floor_id"], []).append(br)
    for f in active_floors(st):
        fid, fa = int(_f(f.get("id"))), TW.floor_avg(f)
        role = "L1" if fid == aid else "upper"
        pct = tp1 if role == "L1" else tpu
        if brows.get(fid):
            role, pct = "L1", brows[fid][0]["pct"]
        if TW.is_tower(f):                # v2.4.0: 잠긴 F도 탑 매도 F. 판 23 수정1: 완성 F의 목표는 탑 매도 목표(평단 +sell_profit_pct%) — 스나이퍼 목표가를 '+10% 목표'로 적던 라벨 오류 고침. pct 도 탑 % 로
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
    """스나이퍼 목표(1층 +1.5% · 상단 +1.0%)에 닿은 '잠기지 않은 미완성 F'를 찾아 선택 대기(picks)에 올림 → 새로 물어볼 F 목록(dict: key·no·avg·qty·target·pct).
    이미 대기 중이면 다시 안 물음. 스나이퍼를 골랐던 F는 현재가가 목표 아래로 내려갔다가 다시 닿을 때만 다시 물음(무장). 없어진 F의 기록은 지움. state 를 바꿈(저장은 호출한 쪽)"""
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
    """선택 반영 (버튼). choice='t'(탑쌓기) → 그 F 잠금, 기록 'tower'. choice='s'(스나이퍼) → F는 그대로, 닿은 목표가를 기준가로 하는 빈 F를 st['empty'] 에 추가, 기록 'sniper'.
    대기 중이 아니면(이미 처리·없어진 F) None. → 알림 글자 또는 None. state(스나이퍼 상태)·st(탑쌓기 상태) 둘 다 바꿈"""
    e = (state.get("picks") or {}).get(key)
    if not isinstance(e, dict) or e.get("status") != "pending":
        return None
    f = next((x for x in TW.top_down(st) if int(_f(x.get("qty"))) > 0 and pick_key(TW.floor_avg(x)) == key), None)
    if f is None:
        state["picks"].pop(key, None)
        return None
    tgt = _f(e.get("target"))
    lab = TW.floor_labels(st).get(int(_f(f.get("id")))) or TW.price_label(TW.floor_avg(f))
    if choice == "t":
        f["locked"] = True
        e["status"] = "tower"
        return f"탑쌓기 선택 — {lab}을 잠가 탑 매도(평단 +10% → 50%)로 넘겼어요"
    e["status"] = "sniper"
    st.setdefault("empty", []).append({"kind": "pick", "ref_px": round(tgt, 2), "id": "p" + key})
    return f"스나이퍼 선택 — {lab}은 그대로 두고, 목표가 ${tgt:.2f} 를 기준가로 하는 새 F를 만들어 스나이퍼 매매를 해요"


SELLABLE_WAIT_SEC = 2.0            # 원작 SELLABLE_QTY_POLL_WAIT_SEC
SELLABLE_POLL_SEC = 0.25           # 원작 SELLABLE_QTY_POLL_INTERVAL_SEC


def wait_sellable(fetch, need, sleep=time.sleep, mono=time.monotonic, wait=None, every=None):
    """원작식 매도가능 수량 대기: fetch() 가 돌려주는 매도가능이 need 이상이 되거나 wait(기본 2초)가 지날 때까지 every(기본 0.25초) 간격으로 확인 → 마지막으로 본 매도가능 수량. need <= 0 이면 바로 한 번만 읽음"""
    wait = SELLABLE_WAIT_SEC if wait is None else wait
    every = SELLABLE_POLL_SEC if every is None else every
    q = int(_f(fetch()))
    end = mono() + wait
    while need > 0 and q < need and mono() < end:
        sleep(every)
        q = int(_f(fetch()))
    return q


def plan_sells(s, st, price, sellable, skip_ids=(), otype="LIMIT", skip_boxes=(), ext=False):
    """v2.9.0(판 31 질문 3) 원작식 부분 주문 (원작 execute_bulletproof_sell_sweep): 목표에 닿은 버킷(졸업이면 전 버킷)의 합 = 목표 수량. 매도가능(sellable)이 목표 이상이면 전량, 모자라면 가능한 만큼만 —
    평단 낮은 버킷부터 채우고(원작 정산 순서) 마지막 버킷은 일부 수량만 주문(그 버킷은 남은 수량이 장부에 그대로 남음). 매도가능 0: 장외(ext=True)면 주문 없이 조용히 대기(원작 SILENT_EXTENDED_SELL_RESTRICTED), 정규장이면 원작처럼 목표 수량 그대로 주문 시도.
    주문은 버킷별(floor_id + box_id) 그대로 → (주문 목록, 알림 글자 목록). skip_ids = 이 층 전체 건너뜀 · skip_boxes = {(층 id, 버킷 id)} 이미 주문이 나가 있거나 오늘 거절된 버킷. 계산만 함 (상태 안 바꿈)"""
    notes, orders = [], []
    cap = max(0, int(_f(sellable)))
    skip = {int(x) for x in skip_ids}
    skipb = {(int(a), int(b)) for a, b in skip_boxes}
    hit = sorted((r for r in box_rows(st, s, price) if r["reached"] and r["floor_id"] not in skip and (r["floor_id"], r["box_id"]) not in skipb), key=lambda r: (r["avg"], -r["box_id"], r["floor_id"]))
    want = sum(r["qty"] for r in hit)
    if want <= 0:
        return orders, notes
    if cap <= 0 and ext:
        return orders, notes                                                  # 장외 매도가능 0주: 조용히 대기 (원작과 같음)
    left = want if cap <= 0 else min(want, cap)                               # 정규장 0주는 원작처럼 목표 수량 그대로 시도
    for r in hit:
        q = min(r["qty"], left)
        if q <= 0:
            break
        left -= q
        part = q < r["qty"]
        if part:
            notes.append(f"매도 {r['label']} 버킷 ${r['avg']:.2f} {r['qty']}주 중 {q}주만 — 매도가능 {cap}주 (원작식 부분 주문, 나머지 {r['qty'] - q}주는 장부에 그대로)")
        orders.append({"side": "SELL", "type": otype, "qty": q, "price": r["target"], "kind": "sell", "mode": MODE_SNIPER, "level": None,
                       "floor_id": r["floor_id"], "box_id": r["box_id"], "floor_avg": r["floor_avg"], "box_avg": r["avg"], "reached": True,
                       "desc": f"스나이퍼 {r['label']} 버킷 평단 ${r['avg']:.2f} +{r['pct']:g}% {'일부 ' + str(q) + '/' + str(r['qty']) + '주' if part else '전량'} 매도 (버킷별 매도{' · 공격 버킷' if r['role'] == 'L1' else ''}{' · 졸업' if r.get('kind') == 'grad' else ''})"})
    if want > cap > 0:
        notes.append(f"매도 목표 {want}주 > 매도가능 {cap}주 — 가능한 만큼만 주문 (원작식)")
    return orders, notes


# ---------------------------------------------------------------- 채우기 (층 사기)
def drop_pct(n_layers):
    """보유 층 수에 따른 눌림 % (음수). 참조 get_golden8_prog_thresholds: 1-4층 -1.0 · 5-8층 -2.0 · 9-10층 -3.5 · 그 위 -5.5 (판 37 후속: -1.00 고정은 취소 — 계단 유지)"""
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
    """15:00 ~ 16:00 ET 인가 (신규 진입 차단 구간, v2.10.0 판 36 D7)"""
    t = now_et.time()
    return LATE_CUTOFF <= t < datetime.time(16, 0)


# ---- v2.11.0 판 38 시간 확대: 매수 창·매도 창 (원작 is_active_buy_window · is_active_sell_window 를 어댑터로 그대로 부름)
STATUS_NIGHT, STATUS_PRE, STATUS_REGULAR, STATUS_AFTER = "001", "003", "004", "005"    # 메리츠 장운영 코드. 004 만 공식 근거(us_market_status 주석). 003(프리)·005(장후)는 v2.0.5 주석뿐 — 미확인. 001(야간·데이마켓 20:00~03:50 ET)은 2026-11-24 실시간 확인 (판 42 Q1)
SELL_STATUS = (STATUS_NIGHT, STATUS_PRE, STATUS_REGULAR, STATUS_AFTER)          # 이 코드일 때만 매도 주문 (그 밖 코드는 메리츠 접수 여부 미확인이라 안 냄)
BUY_STATUS = (STATUS_PRE, STATUS_REGULAR)                         # 프리장 매수 접수는 미확인 — 거절되면 main.py 가 5분 쉼 (buy_block_until)


def sell_ok(status, now_et):
    """매도 주문을 내도 되는가: 장운영 코드가 SELL_STATUS 이고 원작 매도 창(평일 04:00~04:06 ET 7분만 닫힘)이 열려 있음. now_et = 시간대 붙은 미국 동부 시각"""
    return str(status) in SELL_STATUS and AD.sell_window_open(now_et)


def buy_ok(status, now_et):
    """매수 주문을 내도 되는가: 장운영 코드가 BUY_STATUS 이고 원작 매수 창(평일 04:07 ET~) 안이며 16:00 ET 전 (16:00 정각부터는 닫음 — 예전과 같음)"""
    return str(status) in BUY_STATUS and AD.buy_window_open(now_et) and now_et.time() < datetime.time(16, 0)


def anchor_info(st, state, s=None):
    """(기준가, 종류). 저장된 직전 익절/매수가가 있으면 그것, 없으면 가장 아래 활성 F 평단('avg'). (v2.12.0 판 39: 첫 기준가 설정 sniper_first_anchor_usd 삭제 — 첫 매수는 first_buy_signal 이 가격 조건 없이 처리, 기준가는 2번째 이후 눌림 매수용)
    예전 설명: 기준가도 F도 없을 때만(v2.5.0) 설정 sniper_first_anchor_usd('first' — 풀이님이 텔레그램 설정에서 정한 첫 기준가).
    첫 매매 체결이 생기면 체결가가 기준가가 됨(note_fills — 토스 anchor_price = fill_p). 모두 없으면 (0.0, '')"""
    a = _f((state or {}).get("anchor"))
    if a > 0:
        return a, str((state or {}).get("anchor_kind") or "exit")
    fl = active_floors(st)
    if fl:
        return min(TW.floor_avg(f) for f in fl), "avg"
    return 0.0, ""


def buy_signal(price, anchor, kind, cap_price, n_layers, rsi, late_cutoff, hm=None):
    """재장전 신호 판정 (원작 Case 113 evaluate_l2_only_hybrid_reentry_signal 을 어댑터로 호출) → dict(should_buy, signal_type, pullback_price, ref_anchor, ...).
    signal_type: NO_PRICE · NO_ANCHOR · HOLD_PREVENT_INVERSION(현재가 > 가장 낮은 F 평단 = Case 73 상한) · PULLBACK_RELOAD · HOLD_REG_OPEN_7M_VWAP_SHIELD(hm 을 준 경우만) · HOLD_WAIT_GATE.
    v2.10.0 판 36: 돌파 매수 삭제 (원작이 BREAKOUT_RELOAD 를 안 만듦). 눌림 타점·기준가는 원작 결과 그대로 — 기준가 = min(직전 매도가, 가장 낮은 F 평단) (D6). 눌림 % 는 층 수별(-1/-2/-3.5/-5.5, Q-C 그대로).
    late_cutoff 는 원작이 무시함 (신규 진입 컷오프는 plan_buy 가 보유 F 0개일 때 따로 적용). hm = ET 시각 HHMM (개장 7분 쉴드 용, 없으면 쉴드 없음)"""
    lp, anc, cap = _f(price), _f(anchor), _f(cap_price)
    drop = drop_pct(n_layers)
    pull = round(anc * (1.0 + drop / 100.0), 2) if anc > 0 else 0.0
    base = {"should_buy": False, "signal_type": "", "anchor": round(anc, 4), "anchor_kind": kind, "drop_pct": drop, "pullback_price": pull,
            "ref_anchor": round(anc, 4), "cap_price": round(cap, 4), "rsi": rsi, "chg_pct": (round((lp / anc - 1) * 100, 2) if lp > 0 and anc > 0 else 0.0)}
    if anc <= 0:
        return dict(base, signal_type="NO_ANCHOR")
    r = AD.reentry_signal(lp, anc, cap, rsi=rsi, late_cutoff=late_cutoff, pullback_drop_pct=drop, hm=hm)          # 원작 판정 (판 30·36)
    typ = str(r.get("signal_type") or "")
    base = dict(base, pullback_price=_f(r.get("pullback_target_price")) or pull, ref_anchor=_f(r.get("ref_anchor")) or round(anc, 4),
                chg_pct=(round(_f(r.get("chg_from_exit_pct")), 2) if lp > 0 else 0.0))
    return dict(base, should_buy=bool(typ == "PULLBACK_RELOAD" and r.get("should_buy")), signal_type=typ)


SIGNAL_KO = {"NO_PRICE": "시세 없음", "NO_ANCHOR": "기준가 없음 (첫 매수 뒤 생겨요)", "HOLD_PREVENT_INVERSION": "상한 가드 (가장 아래 F 평단 초과)",
             "PULLBACK_RELOAD": "눌림 재장전", "HOLD_REG_OPEN_7M_VWAP_SHIELD": "개장 7분 쉴드 (09:30~09:36, 첫 진입)", "HOLD_LATE_SESSION_NEW_CYCLE_CUTOFF": "신규 진입 차단 (15:00~16:00)",
             "HOLD_WAIT_GATE": "대기 (눌림 전)", "FIRST_BUY": "첫 매수 (가격 조건 없이 현재가)",
             "HOLD_ZERO_SHARES_REG_OPEN_7M_SHIELD": "첫 매수 개장 7분 쉴드 (09:30~09:36)", "HOLD_ZERO_SHARES_SHAVED_HA_BEAR": "첫 매수 보류 (직전 1분봉 무머리 HA음봉 또는 1분봉 준비 전)"}


def plan_sub(s, st, price, state, usd_cash, now_et, is_trading_day=None):
    """v2.5.0 서브 그리드(Case 88) 매수 판정 — 본 신호가 없을 때만 부름. 상태·장부를 바꾸지 않음. → {"buy": bool, "tag": 글자, "gate": 열렸으면 {"bucket","date"}(호출한 쪽이 sub 상태에 저장), "info": dict}.
    가동 조건: F가 있고 (본 그리드 5영업일 무매매 또는 서브 버킷이 이미 있음). 서브 0주 = 첫 진입(15:30~16:00 차단 · 유휴 달러 ≥ max(현재가, 서브 1회 × 0.30)), 서브 있음 = 10분 게이트 · 한도 4회분 · 서브 추매 신호(SG.evaluate_dip).
    유휴 달러 = 예수금 − 본 1회분 × 0.5 (보호예수금). 서브 1회 = 버킷 시드 × 4%"""
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


def timed_signal(price, anchor, kind, cap_price, depth, rsi, now_et, n_held):
    """buy_signal + 시각 규칙. ① (v1.4.4 판 37 항목 5) ET 시각 HHMM 을 매번 원작 신호 함수에 넘겨 개장 7분 쉴드(09:30~09:36) 적용 — 보유 F 개수와 상관없음
    ② (v2.10.0 판 36 D7) 15:00~16:00 ET 이면 보유 F 0개(신규 진입)일 때만 매수 신호를 HOLD_LATE_SESSION_NEW_CYCLE_CUTOFF 로 막음"""
    entry0 = int(n_held) <= 0
    late = is_late_cutoff(now_et)
    hm = now_et.hour * 100 + now_et.minute            # v1.4.4 판 37 항목 5: 개장 7분 쉴드는 첫 진입만이 아니라 매번 적용 (원작: hm 을 매번 넘김)
    sg = buy_signal(price, anchor, kind, cap_price, depth, rsi, late, hm=hm)
    if entry0 and late and sg["should_buy"]:
        sg = dict(sg, should_buy=False, signal_type="HOLD_LATE_SESSION_NEW_CYCLE_CUTOFF")
    return sg


def first_buy_signal(price, now_et, ha):
    """v2.12.0 판 39 할 일 1: 첫 매수 = 원작 분기 A(보유 0주) — 가격 조건 없이 현재가. 검문 순서(원작 그대로):
    ① 15:00~16:00 ET 신규 진입 차단 → ② 개장 7분 쉴드 09:30~09:36 → ③ 직전 완결 1분봉 무머리 HA음봉(또는 1분봉 준비 전) 이면 보류.
    분 경계 타임쉴드(Audit-113-01)는 원작 1.5초 루프의 로그·연산 중복 차단용 → 하이브리드 30초 틱은 매번 새 1분봉으로 ③을 다시 판정하므로 따로 안 둠 (VERIFY.md 설명).
    주문 직후 60초 쉼(ORDER_SHIELD_SEC)은 main.py 가 매수 판단 앞에서 이미 지킴. ha = AD.first_buy_ha(...) 결과 (None 이면 준비 안 됨 = 보류)"""
    px = _f(price)
    base = {"should_buy": False, "signal_type": "", "anchor": 0.0, "anchor_kind": "", "drop_pct": 0.0, "pullback_price": 0.0, "ref_anchor": 0.0, "cap_price": 0.0, "rsi": None, "chg_pct": 0.0}
    if px <= 0:
        return dict(base, signal_type="NO_PRICE")
    if AD.zero_share_cutoff(now_et):
        return dict(base, signal_type="HOLD_LATE_SESSION_NEW_CYCLE_CUTOFF")
    if AD.zero_share_open_shield(now_et):
        return dict(base, signal_type="HOLD_ZERO_SHARES_REG_OPEN_7M_SHIELD")
    if not ha or (not ha.get("ready")) or ha.get("shaved_bear"):
        return dict(base, signal_type="HOLD_ZERO_SHARES_SHAVED_HA_BEAR")
    return dict(base, should_buy=True, signal_type="FIRST_BUY")


def exec_price(price):
    """원작 exec_order_p: max(0.01, floor((현재가 + 1e-9) × 100) / 100) — 소수 2자리 내림 (판 39)"""
    return max(0.01, math.floor((_f(price) + 1e-9) * 100.0) / 100.0)


def plan_buy(s, st, price, state, rsi, usd_cash, now_et, otype="LIMIT", is_trading_day=None, ha=None):
    """오늘 재장전 매수 계획 → {"order": 주문 또는 None, "notes", "signal", "target", "sub", "sub_gate"}. 상태·장부를 바꾸지 않음.
    v2.5.0 사는 금액 = min(신호 1번 몫, 그 버킷의 남은 시드): 몫 = 버킷 시드(tower_box_seed_usd, 기본 $15,000)의 8% (돌파 신호는 sniper_breakout_portion_pct, 기본 16%=$2,400 · 서브 신호는 4%) — 단리 고정. 시드 $15,000 이면 $1,200씩 12번, 13번째에 남은 $600 (13번은 정한 횟수가 아니라 계산 결과).
    채울 버킷 = 빈 F(공사중, st["empty"]) → 위에서부터 첫 미완성 F(공사중) → 새 버킷(시드 = 버킷 시드). 새 버킷 가격은 신호 가격 (F 간격 규칙 없음). 신호 한 번에 1회분만 (여러 회분 한 번에 안 삼).
    주식수는 정수 내림(시드를 안 넘김), 달러 예수금이 모자라면 살 수 있는 만큼만. 주문 가격 = 현재가 (지정가). 본 신호가 없고 서브 신호가 나면 서브 4% (out["sub"])"""
    fu, _nfl, _gap = TW.params(s)
    box, portion = TW.box_seed(s), TW.portion_usd(s)
    fl = active_floors(st)
    n = layer_count(fl)
    px = _f(price)
    labs = TW.floor_labels(st)
    anchor, kind = anchor_info(st, state, s)
    cap = lowest_layer_avg(fl)
    first = n == 0                                            # v2.12.0 판 39: 보유 층 0개 = 원작 분기 A(0주 첫 진입) — 가격 조건 없이 현재가, 눌림·기준가 안 봄
    sig = first_buy_signal(px, now_et, ha) if first else timed_signal(px, anchor, kind, cap, depth_layers(state, n), rsi, now_et, n)
    out = {"order": None, "notes": [], "signal": sig, "target": None, "sub": None, "sub_gate": None, "gate": None, "l2_vac": None}
    chosen = None
    cands = [] if first else [{"empty_id": e.get("id"), "ref": _f(e.get("ref_px")), "kind": e.get("kind")} for e in (st.get("empty") or []) if isinstance(e, dict)]      # 판 24 선택 대기(picks)는 v2.5.0 에서 안 봄
    for c in cands:
        sg = timed_signal(px, c["ref"], "exit", 0.0, depth_layers(state, n), rsi, now_et, n) if c["ref"] > 0 else sig
        if not sg["should_buy"]:
            continue
        chosen, sig = c, sg
        out["signal"] = sg
        break
    if n > 0 and chosen is None and not sig["should_buy"]:       # 판 37 후속 항목 3 (Q1: 연결은 하되 OFF): 2층 공석 돌파 — 원작 함수를 부르며, 원작 Case 113 이 영구 폐기해 항상 NOT_ELIGIBLE (절대 안 삼)
        out["l2_vac"] = AD.l2_vacant_break_signal(AD.layers_of(st), px, cycle_min_buy_price=cap, ratchet_layers=depth_layers(state, n))
        if out["l2_vac"].get("should_buy"):
            sig = dict(sig, should_buy=True, signal_type="LOW_BREAK_L2_VAC_RELOAD")
            out["signal"] = sig
    if n > 0 and (chosen is not None or sig["should_buy"]):     # v1.4.4 판 37 항목 7(Muse Q8): 10분 게이트는 보유 층이 있을 때(추가매수)만 — 첫 매수(층 0개)는 안 기다림. 04:07 ET 기점, 같은 날 같은 10분 구간에 주문은 1번
        g_open, g_bucket, g_day = SG.gate_status(now_et, (state or {}).get("buy_gate_bucket", -1), (state or {}).get("buy_gate_date", ""))
        if not g_open:
            out["signal"] = dict(sig, should_buy=False, signal_type="HOLD_BUY_GATE_10M")
            return out
        out["gate"] = {"bucket": g_bucket, "date": g_day}
    is_sub, per, per_pct, tag = False, portion, TW.portion_pct(s), sig["signal_type"]
    if chosen is None and not sig["should_buy"]:
        if not SUB_GRID_ON:                                                    # v2.10.0 판 36 D2: 서브 그리드 끔 — plan_sub 를 안 부름 (서브 상태·체결 반영 코드는 남김)
            return out
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
        label = "공사중 버킷" if chosen is not None else "새 버킷"
    else:
        fid, nf = int(_f(inc.get("id"))), None
        remaining = max(0.0, _f(inc.get("target") or fu) - _f(inc.get("cost")))
        label = f"{labs.get(fid, TW.price_label(TW.floor_avg(inc)))} 공사중"
    amount = round(min(per, remaining), 2)
    opx = exec_price(px) if (first and not is_sub) else px      # 첫 매수만 원작 exec_order_p (소수 2자리 내림). 다른 매수는 예전 그대로
    q = int(math.floor(amount / opx + 1e-9)) if opx > 0 else 0
    cash = _f(usd_cash)
    if q * opx > cash + 1e-9:
        q = int(math.floor(cash / opx + 1e-9)) if cash > 0 else 0
        out["notes"].append(f"달러 예수금 ${cash:,.0f} 만큼만 매수 (필요 ${amount:,.0f})")
    if q < 1:
        out["notes"].append(f"매수 못 함 — {label} ${amount:,.0f} 로 1주(${opx:.2f})도 못 삼 (예수금 ${cash:,.0f})")
        return out
    out["target"] = {"floor_id": fid, "amount": round(amount, 2), "label": label, "remaining": round(remaining, 2), "last_portion": bool(amount >= remaining - 1e-9), "portion_pct": per_pct}
    desc = (f"서브 그리드 {SG.SUB_TAG_KO.get(tag, tag)} · {label} ${amount:,.0f} (버킷 시드 {per_pct:g}%)" if is_sub
            else f"스나이퍼 {SIGNAL_KO.get(tag, tag)} · {label} ${amount:,.0f} (버킷 시드 {per_pct:g}%{' · 마지막 회차(남은 시드)' if amount >= remaining - 1e-9 and remaining < per - 1e-9 else ''} · 기준 ${sig['anchor']:.2f} {sig['chg_pct']:+.2f}%)")
    out["order"] = {"side": "BUY", "type": otype, "qty": q, "price": round(opx, 2), "kind": "buy_sniper", "mode": MODE_SNIPER, "level": None,
                    "floor_id": fid, "new_floor": nf, "plan_usd": round(amount, 2), "signal": tag, "sub": bool(is_sub), "portion_pct": per_pct, "box_seed": round(box, 2),
                    "empty_id": (chosen or {}).get("empty_id"), "pick_key": None, "desc": desc}
    return out


def tower_sells(s, st, price, sellable, skip_ids=()):
    """v2.3.0 탑 매도: 완성 F만, F 평단 +sell_profit_pct%(기본 10) 에 닿으면 그 F 보유의 sell_fraction_pct%(기본 50, 1주 F 제외). 목표에 닿은 F만 주문 → (주문 목록, 알림 글자 목록, F별 행).
    TW.make_plan(sell_only, complete_only) 의 매도 계산을 그대로 씀 (계산만 — 상태 안 바꿈)"""
    q, _p = TW.totals(st)
    plan = TW.make_plan(s, st, q, _p, _f(price), 0.0, 0.0, sellable, complete_only=True, sell_only=True)
    skip = {int(x) for x in skip_ids}
    nos = sniper_numbers(st)
    tpp, tfr = _f(s.get("sell_profit_pct")), _f(s.get("sell_fraction_pct"))
    orders = [dict(o, mode="tower", desc=f"탑 매도 {nos.get(int(o['floor_id']), o['floor_id'])}F(완성) 평단 ${o['floor_avg']:.2f} +{tpp:g}% → 보유의 {tfr:g}%")
              for o in plan["orders"] if o.get("reached") and int(o["floor_id"]) not in skip]
    return orders, plan["notes"], plan["info"].get("sells") or []


def make_plan(s, st, price, state, rsi, usd_cash, sellable, now_et, otype=None, is_trading_day=None, skip_sell_ids=(), skip_sell_boxes=(), ha=None):
    """오늘(지금) 하이브리드 계획 미리보기 — {"orders","notes","info"}. 상태·장부를 바꾸지 않음. 상황판·--check·텔레그램 오늘 계획용.
    주문 = 버킷 안 매도(미완성 F, v2.5.0 자동) + 탑 매도(완성 F) + 스나이퍼 매수(본 8% 또는 서브 4%)"""
    otype = otype or s.get("order_type") or "LIMIT"
    sells, snotes = plan_sells(s, st, price, max(0, int(_f(sellable))), skip_ids=skip_sell_ids, otype=otype, skip_boxes=skip_sell_boxes)     # v2.6.0: 버킷별 매도 자동 (판 24 선택 대기 폐기)
    taken = sum(int(o["qty"]) for o in sells)
    tsells, tnotes, trows = tower_sells(s, st, price, max(0, int(_f(sellable)) - taken), skip_ids=skip_sell_ids)
    if TW.trade_mode(s) == "tower":      # 판 33: 탑쌓기 매매 — 스나이퍼 매수 대신 탑쌓기 매수 (미리보기는 시초가·환율을 몰라 계획 그대로)
        _q, _p = TW.totals(st)
        tb = plan_tower_buy(s, st, _q, _p, price, 1.0, usd_cash, 0.0)
        buy = {"order": None, "signal": {"should_buy": False, "signal_type": "tower"}, "target": 0.0, "notes": ["탑쌓기 매매 모드 — 스나이퍼 매수 신호 안 씀"] + tb["notes"], "sub": None, "tower_orders": tb["orders"]}
    else:
        buy = plan_buy(s, st, price, state, rsi, usd_cash, now_et, otype=otype, is_trading_day=is_trading_day, ha=ha)
    orders = list(sells) + [dict(o, type=otype) for o in tsells] + ([buy["order"]] if buy["order"] else []) + list(buy.get("tower_orders") or [])
    fl = active_floors(st)
    q, principal = TW.totals(st)
    avg = round(principal / q, 4) if q > 0 else 0.0
    rows = sell_rows(st, s, price)
    fu, _nfl, _gap = TW.params(s)
    info = {"mode": MODE_SNIPER, "price": _f(price), "avg": avg, "qty": q, "profit_pct": (round((_f(price) / avg - 1) * 100, 2) if avg > 0 and _f(price) > 0 else None),
            "sells": rows, "boxes": box_rows(st, s, price), "sell_target": min((r["target"] for r in rows), default=0.0), "profit_reached": any(r["reached"] for r in rows),
            "signal": buy["signal"], "buy_target": buy["target"], "n_layers": layer_count(fl), "depth_layers": depth_layers(state, layer_count(fl)), "floor_usd": fu, "tower_sells": trows,
            "tower_pct": [_f(s.get("sell_profit_pct")), _f(s.get("sell_fraction_pct"))],
            "hits": [{"no": r["no"], "avg": r["avg"], "target": r["target"], "pending": (((state or {}).get("picks") or {}).get(pick_key(r["avg"])) or {}).get("status") == "pending"}
                     for r in rows if r["reached"] and not r["complete"]],                       # v2.4.0: 목표에 닿은 스나이퍼 F (자동 매도 없음 — 선택 대기 중이면 pending)
            "empty": [dict(e) for e in (st.get("empty") or []) if isinstance(e, dict)],
            "sub": (buy.get("sub") or {}).get("info"), "sub_buy": bool(buy["order"] and buy["order"].get("sub")), "box_seed": TW.box_seed(s), "portion_usd": TW.portion_usd(s), "sub_portion_usd": TW.sub_portion_usd(s),
            "fill": next(({"no": r["no"], "label": r["label"], "ratio": round(r["cost"] / r["tgt_usd"], 4) if r["tgt_usd"] else 0.0, "cost": r["cost"], "target": r["tgt_usd"], "rebuy": r["rebuy"]}
                          for r in sorted(rows, key=lambda r: r["id"]) if not r["complete"]), None),      # 채우는 F(위에서부터 첫 미완성 F)의 채움률 = 원가 ÷ F 완성 기준 금액 (총 시드가 아니라 F 완성 기준 금액 기준)
            "tp_l1": tp_pcts(s)[0], "tp_upper": tp_pcts(s)[1], "attack_id": attack_id(st), "rsi": rsi, "usd_cash": round(_f(usd_cash), 2),
            "need_usd": round(buy["order"]["qty"] * buy["order"]["price"], 2) if buy["order"] else 0.0}
    return {"orders": orders, "notes": snotes + tnotes + buy["notes"], "info": info}


# ---------------------------------------------------------------- 판 33 탑쌓기 매매 모드
def plan_tower_buy(s, st, qty, principal, price, fx, usd_cash, open_px):
    """v2.9.0 6차 판 33 탑쌓기 매매: 스나이퍼 신호 대신 탑쌓기 매수 계획(TW.make_plan 의 매수 쪽)을 그대로 씀 — 시초가(open_px)와 가장 가까운 칸부터 간격(tower_buy_gap_usd, 기본 5칸·1달러씩)만큼 아래로,
    채우는 F 의 완성 기준 금액(tower_floor_usd)을 칸마다 같은 금액으로 나눔. 매도는 안 만듦(sellable=0 — 매도는 기존 plan_sells·tower_sells 가 함). 시드를 다 채우면 F 완성 → 다음 날 계획이 다음 F 를 만듦. 계산만 (상태 안 바꿈)
    → {"orders": [BUY 주문...], "notes": [...]}"""
    pl = TW.make_plan(s, st, int(_f(qty)), _f(principal), _f(price), _f(fx), _f(usd_cash), 0, open_px=_f(open_px))
    buys = [dict(o, mode="tower") for o in pl["orders"] if o.get("side") == "BUY"]
    return {"orders": buys, "notes": [n for n in pl["notes"] if "매도" not in n]}


# ---------------------------------------------------------------- 체결 뒤 기준가 갱신
def note_fills(state, done, now_iso=""):
    """체결 반영 결과(done = apply_tower_fills 가 돌려준 목록)로 기준가를 갱신: 매도 체결 → 스나이퍼 매도는 그 체결 평균가, 탑 매도(mode tower)는 매도한 F의 평단 (직전 익절가, 'exit'), 매수(본) 체결 → 그 체결 평균가('buy').
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
            state["anchor"] = round(_f(o.get("floor_avg")), 4)           # v2.3.0 판 23: 탑 매도 체결 → 매도한 F의 평단(주문에 적힌 매도 시점 F 평단)이 기준가
        else:
            state["anchor"] = round(da / dq, 4)                          # 스나이퍼 매도·매수 체결은 그대로: 그 체결 평균가
        state["anchor_kind"] = "exit" if a.get("side") == "SELL" else "buy"
        state["anchor_at"] = now_iso
        changed = True
    return changed


def mark_buy_gate(state, plan):
    """본 매수 주문을 낸 틱의 10분 게이트 기록 (v1.4.4 판 37 항목 7 — 같은 10분 구간 재주문 방지). 바뀌었으면 True"""
    g = (plan or {}).get("gate")
    if not g:
        return False
    state["buy_gate_bucket"], state["buy_gate_date"] = g["bucket"], g["date"]
    return True


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


def seed_main_day(state, st, today):
    """판 30 B4: F가 있는데 본 그리드 마지막 매매일(last_main_day)이 한 번도 안 찍혔으면(봇을 F 보유 중에 처음 켠 경우 등) 오늘로 찍어 '5영업일 무매매' 시계를 시작함 — 안 찍으면 영영 0일이라 서브가 안 깸. 바로 깨우지는 않음. 바뀌었으면 True"""
    if not active_floors(st) or not today:
        return False
    sub = SG.norm(state.get("sub"))
    if str(sub.get("last_main_day") or "").strip():
        return False
    sub["last_main_day"] = str(today)[:10]
    state["sub"] = sub
    return True


def trigger_lines(s, st, state, now_et=None):
    """체결 알림·상황판용 '다음 매매' 글자: F별 다음 매도(목표가·수량) + 다음 매수 타점(눌림/돌파·기준·상한). 상태는 안 바꿈"""
    lines = []
    tpp, tfr = _f((s or {}).get("sell_profit_pct")), _f((s or {}).get("sell_fraction_pct"))
    for r in sorted(sell_rows(st, s, 0.0), key=lambda r: r["no"])[:6]:
        if r["complete"]:              # v2.3.0 완성 F = 탑 매도 (F 평단 +sell_profit_pct% 에 보유의 sell_fraction_pct%)
            sq = TW.floor_sell_qty(r["qty"], tfr)
            lines.append(f"다음 매도: {r['label']}(완성·탑) 평단 ${r['avg']:.2f} → 목표가 ${ceil2(r['avg'] * (1 + tpp / 100.0)):.2f} 에 " + (f"{sq}주 ({tfr:g}%)" if sq >= 1 else "자동 매도 없음 (1주 F)") + f" (+{tpp:g}%)")
            continue
        bxs = r.get("boxes") or []                                  # v2.6.0: 미완성 F는 버킷별 다음 매도 (버킷 하나씩 전량)
        for b in bxs[:4]:
            lines.append(f"다음 매도: {r['label']} 공사중 버킷 평단 ${b['avg']:.2f} → 목표가 ${b['target']:.2f} 에 {b['qty']}주 전량 (+{b['pct']:g}%{' · 졸업 매도' if b.get('kind') == 'grad' else ''}{' · 공격 버킷' if b['role'] == 'L1' else ''})")
        if len(bxs) > 4:
            lines.append(f"다음 매도: {r['label']} 그 위 {len(bxs) - 4}개 버킷은 같은 규칙")
    fl = active_floors(st)
    anchor, kind = anchor_info(st, state, s)
    cap = lowest_layer_avg(fl)
    if not fl:      # v2.12.0 판 39: 보유 0개 = 원작 분기 A (가격 조건 없는 첫 매수)
        lines.append(f"다음 매수: 첫 매수 — 가격 조건 없이 현재가 (소수 2자리 내림) · 버킷 시드의 {TW.portion_pct(s):g}% (${TW.portion_usd(s):,.0f})")
    elif anchor > 0:
        sig = buy_signal(0.0, anchor, kind, cap, depth_layers(state, layer_count(fl)), None, False)
        lines.append(f"다음 매수: 눌림 ${sig['pullback_price']:.2f} ({sig['drop_pct']:+.1f}%)"
                     + f" · 기준 ${sig['ref_anchor']:.2f}" + (f" · 상한 ${cap:.2f}" if cap > 0 else ""))
    else:
        lines.append("다음 매수: 눌림 기준가가 아직 없어요 (첫 매수 체결 뒤에 생겨요)")
    return lines


# ---------------------------------------------------------------- 상태 파일 (cfg = ConfigManager: _load_json·_save_json 재사용)
def new_state():
    return {"version": 1, "anchor": 0.0, "anchor_kind": "", "anchor_at": "", "last_order_ts": 0.0, "buy_block_until": 0.0, "peak_layers": 0, "series": [], "picks": {}, "sub": SG.new_sub(), "buy_gate_bucket": -1, "buy_gate_date": ""}


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
    """시드 배분 10칸 게이지 (참조 quant_engine 게이지 규칙: 🟦 완성 F · 🟨 채우는 중인 F · 🟩 남은 시드(현금)). 있는 영역은 최소 1칸, 합계 10칸 → (막대, 완성%, 진행%, 현금%)"""
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


# ---------------------------------------------------------------- v2.13.0 판 40 할 일 1: 1.5초 틱 + 분 경계 쉴드
def tick_gap(s):
    """스나이퍼 틱 간격(초): 설정 sniper_tick_sec (없으면 1.5, 1.5 미만은 1.5). 되돌리기 조건: 메리츠 API·서버 부하 문제가 보이면 sniper_tick_sec 를 30 으로 (옛 동작)"""
    v = _f((s or {}).get("sniper_tick_sec")) if (s or {}).get("sniper_tick_sec") is not None else TICK_SEC_DEFAULT
    return max(TICK_SEC_DEFAULT, v)


def buy_check_gap(n_layers, s=None):
    """매수 판단 간격(초): 보유 층 0개(첫 매수, 분기 A)는 틱 간격 (원작은 1.5초마다 + 분 경계 쉴드) · 층이 있으면 예전 그대로 60초"""
    return tick_gap(s) if int(n_layers) <= 0 else float(BUY_CHECK_SEC)


def _min_key(now_et):
    return now_et.strftime("%Y-%m-%d %H:%M")


def _prev_min_key(now_et):
    return (now_et - datetime.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")


def ha_shield(state, now_et, ha, mono=None):
    """분 경계 쉴드 (원작 Audit-113-01 is_within_reentry_monitor_time_shield 의 하이브리드 판) → (막힘, 이유, 남은 초).
    ① 같은 분 안에서 HA음봉으로 한 번 보류됐으면(state['ha_wait']) 그 분 끝까지 다시 안 판정 — 새 완결봉이 오기 전엔 같은 봉이라 결과가 같음 (조회·연산 중복 차단). 새 분이 되면 저절로 풀림. 65초 상한
    ② 새 분이 시작된 직후(BOUNDARY_WAIT_SEC 초 안)인데 직전 분 완결봉이 아직 안 보이면 기다림 — 낡은 완결봉으로 사지 않게 (1.5초마다 다시 봄). 이 초를 넘겨도 안 오면 예전처럼 낡음 가드(FIRST_BUY_MAX_BAR_AGE_MIN)가 판정.
    ha = AD.first_buy_ha 결과 또는 None (None 이면 판정 재료 없음 → 쉴드는 아무것도 안 함). mono = 단조 시계 초 (테스트용)"""
    mono = time.monotonic() if mono is None else float(mono)
    cur = _min_key(now_et)
    w = (state or {}).get("ha_wait") or {}
    if w and w.get("mk") == cur and -0.01 <= mono - _f(w.get("mono")) < HA_WAIT_CAP_SEC:   # 저장값을 소수 3자리로 반올림하므로 아주 작은 음수 오차 허용
        rem = max(0.5, 60.0 - (now_et.second + now_et.microsecond / 1e6))
        return True, "HA_WAIT_SAME_MINUTE", round(rem, 1)
    if ha and ha.get("closed_mk") is not None:
        sec_in_min = now_et.second + now_et.microsecond / 1e6
        if sec_in_min < BOUNDARY_WAIT_SEC and str(ha.get("closed_mk") or "") < _prev_min_key(now_et):
            return True, "WAIT_CLOSED_BAR", round(BOUNDARY_WAIT_SEC - sec_in_min, 1)
    return False, "", 0.0


def ha_wait_mark(state, now_et, ha, mono=None):
    """HA음봉(또는 준비 전)으로 첫 매수를 보류했을 때 부름 → 같은 분 안에서는 다시 안 봄 (원작 mark_pullback_ha_bear_minute_wait)"""
    state["ha_wait"] = {"mk": _min_key(now_et), "closed": str((ha or {}).get("closed_mk") or ""), "mono": round(time.monotonic() if mono is None else float(mono), 3)}
    return state["ha_wait"]


# ---------------------------------------------------------------- v2.13.0 판 40 할 일 6: B-0 부분체결 잔량 모니터 (원작 분기 B-0 · 서브는 S-B0 — Case 78, 88)
TOPUP_SIGNAL = "TOPUP_1FL"
TOPUP_DROP_KEYS = ("no", "placed_ts", "notified_qty", "ts", "topup_done", "status", "intraday", "new_floor", "empty_id")


def topup_find(orders, rows, open_orders):
    """오늘 낸 스나이퍼 매수 중 '일부만 체결되고 더는 열려 있지 않은 것'(앱에서 취소·장 마감·60초 안전 취소 등 — 판 42부터 봇도 60초 뒤 취소함) → 보충 대기 dict 또는 None.
    원작 rem_quota_qty = 1층 목표 수량 − 체결 수량. 여기서는 주문 수량 − 누적 체결 수량. 이미 보충 주문을 낸 주문(topup_done)은 제외 (같은 잔량을 두 번 내지 않게).
    orders = 오늘 기록 m["orders"] · rows = {주문번호: {"qty": 누적 체결}} · open_orders = 아직 열린 매수 주문 목록 (sniper_open_orders). 가장 나중에 낸 주문 1건"""
    open_nos = {str(o.get("no")) for o in (open_orders or []) if isinstance(o, dict)}
    found = None
    for o in orders or []:
        if not isinstance(o, dict) or o.get("side") != "BUY" or o.get("kind") != "buy_sniper" or not o.get("no") or o.get("topup_done"):
            continue
        no = str(o["no"])
        q, f = int(_f(o.get("qty"))), int(_f((rows.get(no) or {}).get("qty")))
        if no in open_nos or not (1 <= f < q) or o.get("floor_id") is None:
            continue
        found = {"no": no, "floor_id": int(_f(o["floor_id"])), "rem_qty": q - f, "book_price": round(_f(o.get("price")), 2), "sub": bool(o.get("sub")), "order": o}
    return found


def topup_order(s, st, tp, price, usd_cash, now_et, otype="LIMIT"):
    """보충 주문 계획 → (주문 또는 None, 사유). 원작 조건: 잔량>0 · 현재가 ≤ 1층 단가(그 주문의 가격) · 쓸 수 있는 달러 ≥ 1주 비용 · 그 층이 아직 미완성.
    가격 = min(현재가 소수 2자리 내림, 단가) (원작 exec_order_p) · 수량 = min(잔량, 달러로 살 수 있는 수). 층 상태가 바뀌었으면(층 없음·완성) 보충하지 않음 (원작 L1_STATE_CHANGED). 서브 주문은 서브 그리드가 켜져 있을 때만"""
    if not tp:
        return None, ""
    if tp.get("sub") and not SUB_GRID_ON:
        return None, "서브 그리드 꺼짐 — 서브 잔량 보충 안 함"
    px = _f(price)
    if px <= 0:
        return None, "시세 없음"
    fl = next((f for f in active_floors(st) if int(_f(f.get("id"))) == int(tp["floor_id"])), None)
    if fl is None or TW.is_complete(fl):
        return None, "층 상태가 바뀜 (없거나 완성) — 잔량 보충 안 함"
    book = _f(tp["book_price"])
    if px > book + 1e-6:
        return None, f"현재가 ${px:.2f} > 단가 ${book:.2f} — 도래 대기"
    opx = max(0.01, min(math.floor((px + 1e-9) * 100.0) / 100.0, book))
    cash = _f(usd_cash)
    if cash < opx:
        return None, f"달러 ${cash:,.2f} < 1주 ${opx:.2f} — 보충 못 함"
    q = min(int(tp["rem_qty"]), int(math.floor(cash / opx + 1e-9)))
    if q < 1:
        return None, "보충 수량 0"
    base = {k: v for k, v in dict(tp["order"]).items() if k not in TOPUP_DROP_KEYS}
    desc = f"{'서브 ' if tp.get('sub') else ''}1층 부분체결 잔량 보충(TOPUP) · 이전 주문 {tp['no']} 의 남은 {tp['rem_qty']}주 중 {q}주 @ ${opx:.2f} (단가 ${book:.2f})"
    return dict(base, side="BUY", type=otype, qty=q, price=round(opx, 2), kind="buy_sniper", mode=MODE_SNIPER, floor_id=int(tp["floor_id"]), new_floor=None, empty_id=None,
                plan_usd=round(q * opx, 2), signal=TOPUP_SIGNAL, desc=desc), ""
