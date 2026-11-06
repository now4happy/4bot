# -*- coding: utf-8 -*-
"""
# MODIFIED: sniper_plugin.py (원작 sniper_plugin_core.py + 원작 sniper_plugin.py 병합)
# 4bot 2번 v2.3.0 (2026-11-06): 원작 a4b4790 Case 91 이식 — 자산증식형(복리·기본)⇄인출형(단리) 모드 전환 + 무제한 시멘트추가(예비시드 · 횟수만 카운트 · GUARD30 유지) · 표시 문구 '수혈'→'시멘트추가' · 지하층 보존
# 4bot 2번 v2.2.0 (2026-11-05): 원작 254eef5(c1b9b27) 골든포켓 폐기 이식 + 기존 골든포켓 → 지하층(basement_pocket) 보관·목표가 매도 전용 (신규 매수 없음)
# 4bot 2번 v2.1.0 (2026-11-04): 원작 e5ae290 Case 89(사이클 수익·배분 게이지·졸업예정자산) 이식 · 이전 v2.0.0 = 원작 d7b3a66 이식 + 사용자 수정 재적용 (단일파일 구조 유지)
인피니트 스노우볼 (Infinite Snowball) v3.0 — 스나이퍼 매수 코어 Part 1 / 2 (Step 06 / 13)
역할:
1) 스나이퍼 매수 전역 상수 락온 (DEFAULT_GRID_MERGE_MODE = "L2_L7_MERGE_SORT" [Case 87] ·
   SUB_MERGE_MODE_L1_L3 = "SUB_L1_L3_MERGE" / SUB_MAX_TIERS_3 = 3 / SUB_MAX_TOTAL_LOTS_4 = 4 [Case 88] ·
   STEP2X_15PCT_C20 · BUY_ORDER_MAX_WAIT_SEC = 60.0 · AUTO_FILL_GRACE_SHIELD_SEC = 15.0 ·
   REENTRY_MONITOR_TIME_SHIELD_SEC = 60.0 · RESERVE_DEPOSIT_CHECK_INTERVAL_SEC = 60.0)
2) 매수·매도 체결 직후 토스 잔고 API 인덱싱 시차(0.1 ~ 0.4초) 보호 양방향 15.0초 그레이스 쉴드 및
   매수 체결 후 60.0초 타임쉴드 각인기 (mark_auto_fill_grace_shield, is_within_auto_fill_grace_shield · Case 61, 65, 69, 88)
3) 본 그리드 상단 2층 ~ 7층 보유 중 1층 공석 시 60.0초(1분) 타임쉴드 주기 하이브리드 재장전 모니터 타임쉴드 관리기
   (mark_reentry_monitor_60s_cycle_shield, is_within_reentry_monitor_time_shield · Case 73) 및
   🛡️ Default-ON 3층 서브 그리드 상단 2층 ~ 3층 보유 중 서브 1층 공석 시 60.0초(1분) 타임쉴드 관리기
   (mark_sub_reentry_monitor_60s_cycle_shield, is_within_sub_reentry_monitor_time_shield · Case 88)
4) 시드고갈 입금 대기(waiting_reserve_deposit) 중 60.0초 주기 확인 타임쉴드 관리기
   (mark_reserve_deposit_check_shield, is_within_reserve_deposit_check_shield · Case 77)
5) 실시간 SOXL 현재가 추출 및 60초 타임쉴드 경과 직후 최신 현재가 직접 재조회기
   (_get_live_soxl_price, _fetch_fresh_current_soxl_price · Case 65, 73)
6) 💉 GUARD30 & 무제한 예비수혈 (30% 자투리 1주 승격 방지 가드 · 계좌별 동적 왕복 수수료율 연동[Case 86] ·
   예수금 API 0.0 반환 시 0.25초 재시도 · 시드고갈 단 1회 입금 요청 알림 영구 래치 waiting_reserve_deposit_alert_sent 및 중복 디스크 쓰기 스킵 ·
   토스 실계좌 여유자금 감지 기반 횟수 제한 없는 무제한 온디맨드 예비시드 자동 수혈 및 수혈 횟수 카운트) 실행 엔진
   (_check_and_execute_guard30_or_reserve_injection · Case 75, 77, 86, 89, 91)
7) 매수 체결(FILLED / 부분 체결 후 60초 취소 종료 / 세션 경계 force_settle 강제 정산) 원장 커밋 ·
   🛡️ Default-ON 3층 서브 그리드(SUB_REENTRY_1FL / SUB_TOPUP_1FL / SUB_DIP_1FL : 3층 초과 시 구 1층+구 3층 양끝 합병 SUB_L1_L3_MERGE ·
   서브 최고 도달 회차 sub_ratchet_max_lots 잠금 · 10일/-10% 저가해금 · sub_consec_frozen_days = 0 리셋 · Case 88) 분리 정산 ·
   본 그리드 부분 체결 수량 비례 자투리 정산 및 현재 사이클 자투리 절약금(cycle_leftover_saved_usd) 동시 누적 ·
   1층 목표 정량(l1_target_quota_qty) 보존(Case 78) ·
   7층 초과 시 구 1층 보존 + 구 2층 + 구 7층 통합 중간층 재배치(L2_L7_MERGE_SORT) 및 사이클 최고 도달 회차(cycle_ratchet_max_lots) 단차 잠금 갱신(Case 87) ·
   STEP2X_15PCT_C20 스텝업 잠금 저가/회차 갱신(Case 76, 87) ·
   15:30 EST 경계 미체결 취소 시 본·서브 0주 신규 진입 및 1층 공석 +1.0% 돌파 추격 동시 안전 취소(Case 84, Case 88) 및
   미체결 매수 주문 60.0초 동기화/안전 취소기 (_commit_filled_buy_to_stratum_ledger, sync_pending_buy_order_plugin · Case 19, 24, 59 ~ 91)
- 제1헌법 ~ 제6헌법 및 Case 01 ~ 91 완벽 준수
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from quant_engine import (
    BASE_MAX_LOTS_8PCT,
    DEFAULT_GRID_MERGE_MODE,
    MAX_GRID_TIERS_7,
    MAX_RESERVE_PORTIONS,
    MIN_DIP_BUDGET_RATIO,
    MIN_DIP_VS_L1_RATIO,
    PORTION_MODE_COMPOUND,
    PORTION_MODE_SIMPLE,
    REENTRY_BREAKOUT_RISE_PCT,
    ROUND_TRIP_FEE_RATE_PCT,
    SUB_FROZEN_DAYS_TRIGGER,
    SUB_GRID_DEFAULT_ENABLED,
    SUB_MAX_TIERS_3,
    SUB_MAX_TOTAL_LOTS_4,
    SUB_MERGE_MODE_L1_L3,
    SUB_PORTION_RATIO_4PCT,
    SUB_RESERVE_MAIN_PORTIONS,
    SUB_UNLOCK_DROP_FROM_L1_PCT,
    SUB_UNLOCK_FROZEN_DAYS_10,
    add_lot_to_sub_grid,
    add_lot_to_sub_grid_with_flag,
    buckets_from_dicts,
    buckets_to_dicts,
    evaluate_guard30_and_reserve_injection,
    has_active_l1_bucket,
    is_simple_income_mode,
    resolve_effective_round_trip_fee_rate_pct,
    resolve_portion_budget_base_equity,
    summarize_stratum_portfolio,
    vrev_add_quota_lot_and_merge_2tier,
)
from quant_indicators_plugin import (
    is_late_regular_new_cycle_cutoff_window,
    refresh_metrics_with_live_tick,
)
from sniper_exit_plugin import (
    is_within_post_buy_time_shield,
    is_within_post_sell_time_shield,
)
import toss_api
from toss_api import (
    EST_TZ,
    TARGET_SYMBOL,
    safe_float,
    safe_int,
)

logger = logging.getLogger("toss_sniper.sniper_plugin_core")

# Case 76: 🔓 06_STEP2X_15PCT_C20 스텝업 저가 해금 상수 폴백 바인딩
DEFAULT_UNLOCK_MODE: str = str(
    getattr(toss_api, "DEFAULT_UNLOCK_MODE", "STEP2X_15PCT_C20")
)
STEP_UP_2X_DROP_PCT: float = float(
    getattr(toss_api, "STEP_UP_2X_DROP_PCT", 15.0)
)
STEP_UP_2X_MIN_CASH_RATIO: float = float(
    getattr(toss_api, "STEP_UP_2X_MIN_CASH_RATIO", 0.20)
)
STEP_UP_2X_MIN_REBOUND_MULT: float = float(
    getattr(toss_api, "STEP_UP_2X_MIN_REBOUND_MULT", 2.0)
)
STEP_UP_2X_MAX_TIERS: int = int(
    getattr(toss_api, "STEP_UP_2X_MAX_TIERS", 2)
)

# 순수 현재가 지정가 매수 주문 발주 후 미체결 최대 대기 시간(초) — 상향 추격 정정 없이 60초 미체결 시 안전 취소
BUY_ORDER_MAX_WAIT_SEC: float = 60.0

# Case 61 & Case 69: 매수 또는 매도 FILLED 직후 토스 잔고 API(/api/v1/holdings) 인덱싱 시차(0.1 ~ 0.4초) 보호 그레이스 쉴드(초)
AUTO_FILL_GRACE_SHIELD_SEC: float = 15.0

# Case 73 & Case 88: 상단층 보유 중 1층 공석 시 하이브리드 독립 1층(REENTRY_1FL / SUB_REENTRY_1FL) 재장전 모니터 주기 타임쉴드(60.0초 = 1분)
REENTRY_MONITOR_TIME_SHIELD_SEC: float = 60.0

# Case 77: 시드고갈 입금 대기(waiting_reserve_deposit == True) 상태에서 토스 계좌 입금 감지 주기 타임쉴드(60.0초 = 1분)
RESERVE_DEPOSIT_CHECK_INTERVAL_SEC: float = 60.0


# ---------------------------------------------------------------------------
# 내부 헬퍼 : 매수·매도 체결 직후 잔고 인덱싱 시차 보호 그레이스 쉴드 & 60초 타임쉴드 각인 (Case 61, 65, 69, 73, 77, 88)
# ---------------------------------------------------------------------------
def mark_auto_fill_grace_shield(
    context: Any,
    symbol: str = TARGET_SYMBOL,
    lot_type: str = "QUOTA_L1",
    fill_price: float = 0.0,
    filled_qty: int = 0,
) -> None:
    """
    🚨 Case 61, Case 65, Case 69, Case 73, Case 77 & Case 88:
    1) 매수(또는 매도) 주문이 거래소에서 FILLED 된 직후 토스 잔고 API(/api/v1/holdings) 인덱싱 시차(0.1 ~ 0.4초) 동안
       잔고 동기화 모듈(reconcile)이 시차를 수동 매매로 오판하지 않도록 15.0초 그레이스 쉴드(last_auto_fill_ts)를 각인한다.
    2) 매수 체결 시에는 last_buy_fill_mono(단조 시계)와 last_buy_fill_ts(Epoch)를 전용 키로 각인하여,
       매수 체결 후 정확히 60.0초(POST_BUY_TO_SELL_SHIELD_SEC) 동안 매도 및 중복 매수가 발사되지 않도록 타임쉴드를 건다!
    3) 본 그리드 매수 체결로 1층이 채워지면 본 그리드 1층 공석 재장전 모니터 타임쉴드(last_reentry_eval_mono / last_reentry_eval_ts)를 리셋하고,
       서브 그리드 매수(SUB_*) 체결로 서브 1층이 채워지면 서브 1층 공석 재장전 모니터 타임쉴드(last_sub_reentry_eval_mono / last_sub_reentry_eval_ts)를 리셋한다.
    """
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    now_mono = time.monotonic()
    now_epoch = time.time()
    tag = str(lot_type or "QUOTA_L1").upper().strip()
    is_sub_tag = tag.startswith("SUB_")

    guard_map = getattr(context, "indexing_grace_cache", None)
    if isinstance(guard_map, dict):
        prev = guard_map.get(sym) if isinstance(guard_map.get(sym), dict) else {}
        updated = dict(prev)
        updated["last_auto_fill_ts"] = now_mono
        updated["lot_type"] = tag
        updated["fill_price"] = safe_float(fill_price, 0.0)
        updated["filled_qty"] = safe_int(filled_qty, 0)
        if tag != "SELL_FILL":
            updated["last_buy_fill_mono"] = now_mono
            updated["last_buy_fill_ts"] = now_epoch
            if is_sub_tag:
                updated["last_sub_buy_fill_mono"] = now_mono
                updated["last_sub_buy_fill_ts"] = now_epoch
                updated["last_sub_reentry_eval_mono"] = 0.0
                updated["last_sub_reentry_eval_ts"] = 0.0
            else:
                updated["last_reentry_eval_mono"] = 0.0
                updated["last_reentry_eval_ts"] = 0.0
            updated["last_reserve_check_mono"] = 0.0
            updated["last_reserve_check_ts"] = 0.0
        else:
            updated["last_sell_fill_mono"] = now_mono
            updated["last_sell_fill_ts"] = now_epoch
        guard_map[sym] = updated

    if tag != "SELL_FILL":
        snap_map = getattr(context, "exit_snapshot_cache", None)
        if isinstance(snap_map, dict):
            s_entry = (
                snap_map.get(sym) if isinstance(snap_map.get(sym), dict) else {}
            )
            if is_sub_tag:
                s_entry["last_sub_reentry_eval_mono"] = 0.0
                s_entry["last_sub_reentry_eval_ts"] = 0.0
            else:
                s_entry["last_reentry_eval_mono"] = 0.0
                s_entry["last_reentry_eval_ts"] = 0.0
            s_entry["last_reserve_check_mono"] = 0.0
            s_entry["last_reserve_check_ts"] = 0.0
            snap_map[sym] = s_entry


def is_within_auto_fill_grace_shield(
    context: Any, symbol: str = TARGET_SYMBOL
) -> bool:
    """
    🚨 Case 61, Case 69 & Case 88 [양방향 15.0초 잔고 인덱싱 시차 보호 그레이스 쉴드]:
    최근 15.0초(AUTO_FILL_GRACE_SHIELD_SEC) 이내에 자동 매수 체결(본·서브) 또는 자동 매도 체결(개별 층 익절 / 0주 졸업)
    이력이 존재하면 True 를 반환하여, defense_plugin.py 의 reconcile 모듈이 잔고 API 인덱싱 시차로 인해
    유령 추매(h_qty > ledger_qty)나 유령 부분매도(h_qty < ledger_qty) 또는 백업 덮어쓰기를 수행하는 것을 100% 차단한다!
    """
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    now_mono = time.monotonic()

    guard_map = getattr(context, "indexing_grace_cache", None)
    if isinstance(guard_map, dict):
        info = guard_map.get(sym)
        if isinstance(info, dict):
            last_mono = max(
                safe_float(info.get("last_auto_fill_ts"), 0.0),
                safe_float(info.get("last_buy_fill_mono"), 0.0),
                safe_float(info.get("last_sub_buy_fill_mono"), 0.0),
                safe_float(info.get("last_sell_fill_mono"), 0.0),
                safe_float(info.get("last_cycle_end_mono"), 0.0),
            )
            if (
                last_mono > 0.0
                and 0.0 <= (now_mono - last_mono) <= AUTO_FILL_GRACE_SHIELD_SEC
            ):
                return True

    snap_map = getattr(context, "exit_snapshot_cache", None)
    if isinstance(snap_map, dict):
        s_info = snap_map.get(sym)
        if isinstance(s_info, dict):
            last_s_mono = max(
                safe_float(s_info.get("last_sell_fill_mono"), 0.0),
                safe_float(s_info.get("last_cycle_end_mono"), 0.0),
            )
            if (
                last_s_mono > 0.0
                and 0.0 <= (now_mono - last_s_mono) <= AUTO_FILL_GRACE_SHIELD_SEC
            ):
                return True

    if hasattr(context, "ledger"):
        try:
            st = context.ledger.get_state(sym)
            last_epoch = max(
                safe_float(st.get("last_buy_fill_ts"), 0.0),
                safe_float(st.get("last_sub_buy_fill_ts"), 0.0),
                safe_float(st.get("last_sell_fill_ts"), 0.0),
                safe_float(st.get("last_sub_sell_fill_ts"), 0.0),
                safe_float(st.get("last_cycle_end_ts"), 0.0),
                safe_float(st.get("last_sub_cycle_end_ts"), 0.0),
            )
            if (
                last_epoch > 0.0
                and 0.0 <= (time.time() - last_epoch) <= AUTO_FILL_GRACE_SHIELD_SEC
            ):
                return True
        except Exception:
            pass

    return False


# ---------------------------------------------------------------------------
# [Case 73, Case 77 & Case 88] 본 그리드 / 서브 그리드 1층 공석 60초 재장전 타임쉴드 & 시드고갈 60초 입금 감지 타임쉴드 관리기
# ---------------------------------------------------------------------------
def mark_reentry_monitor_60s_cycle_shield(
    context: Any,
    symbol: str = TARGET_SYMBOL,
    eval_price: float = 0.0,
    clear_shield: bool = False,
) -> float:
    """
    🚨 [Case 73 : 본 그리드 1층 공석 60.0초(1분) 타임쉴드 주기 하이브리드 재장전 모니터 재장전기]:
    """
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    now_mono = 0.0 if clear_shield else time.monotonic()
    now_epoch = 0.0 if clear_shield else time.time()

    guard_map = getattr(context, "indexing_grace_cache", None)
    if isinstance(guard_map, dict):
        g_entry = (
            guard_map.get(sym) if isinstance(guard_map.get(sym), dict) else {}
        )
        g_entry["last_reentry_eval_mono"] = now_mono
        g_entry["last_reentry_eval_ts"] = now_epoch
        if eval_price > 0.0:
            g_entry["last_reentry_eval_price"] = round(
                safe_float(eval_price, 0.0), 4
            )
        guard_map[sym] = g_entry

    snap_map = getattr(context, "exit_snapshot_cache", None)
    if isinstance(snap_map, dict):
        s_entry = (
            snap_map.get(sym) if isinstance(snap_map.get(sym), dict) else {}
        )
        s_entry["last_reentry_eval_mono"] = now_mono
        s_entry["last_reentry_eval_ts"] = now_epoch
        if eval_price > 0.0:
            s_entry["last_reentry_eval_price"] = round(
                safe_float(eval_price, 0.0), 4
            )
        snap_map[sym] = s_entry

    return now_epoch


def is_within_reentry_monitor_time_shield(
    context: Any,
    st: Optional[Dict[str, Any]] = None,
    symbol: str = TARGET_SYMBOL,
) -> Tuple[bool, float]:
    """
    🚨 [Case 73 : 본 그리드 1층 공석 60.0초(1분) 주기 재장전 모니터 타임쉴드 작동 여부 판별]:
    """
    in_post_sell, rem_sell = is_within_post_sell_time_shield(
        context, st, symbol
    )
    if in_post_sell:
        return True, rem_sell

    in_post_buy, rem_buy = is_within_post_buy_time_shield(context, st, symbol)
    if in_post_buy:
        return True, rem_buy

    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    now_mono = time.monotonic()

    guard_map = getattr(context, "indexing_grace_cache", None)
    if isinstance(guard_map, dict):
        g_entry = guard_map.get(sym)
        if isinstance(g_entry, dict):
            re_mono = safe_float(g_entry.get("last_reentry_eval_mono"), 0.0)
            if re_mono > 0.0:
                elapsed_g = now_mono - re_mono
                if 0.0 <= elapsed_g < REENTRY_MONITOR_TIME_SHIELD_SEC:
                    return True, round(
                        REENTRY_MONITOR_TIME_SHIELD_SEC - elapsed_g, 1
                    )

    snap_map = getattr(context, "exit_snapshot_cache", None)
    if isinstance(snap_map, dict):
        s_entry = snap_map.get(sym)
        if isinstance(s_entry, dict):
            s_re_mono = safe_float(s_entry.get("last_reentry_eval_mono"), 0.0)
            if s_re_mono > 0.0:
                elapsed_s = now_mono - s_re_mono
                if 0.0 <= elapsed_s < REENTRY_MONITOR_TIME_SHIELD_SEC:
                    return True, round(
                        REENTRY_MONITOR_TIME_SHIELD_SEC - elapsed_s, 1
                    )

    state_obj = (
        st
        if isinstance(st, dict)
        else (
            context.ledger.get_state(sym)
            if hasattr(context, "ledger")
            else {}
        )
    )
    re_epoch = safe_float(state_obj.get("last_reentry_eval_ts"), 0.0)
    if re_epoch > 0.0:
        elapsed_epoch = time.time() - re_epoch
        if 0.0 <= elapsed_epoch < REENTRY_MONITOR_TIME_SHIELD_SEC:
            return True, round(REENTRY_MONITOR_TIME_SHIELD_SEC - elapsed_epoch, 1)

    return False, 0.0


def mark_sub_reentry_monitor_60s_cycle_shield(
    context: Any,
    symbol: str = TARGET_SYMBOL,
    eval_price: float = 0.0,
    clear_shield: bool = False,
) -> float:
    """
    # [Case 88 : Default-ON 3층 서브 그리드 1층 공석 60.0초(1분) 타임쉴드 주기 하이브리드 재장전 모니터 기록기]:
    """
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    now_mono = 0.0 if clear_shield else time.monotonic()
    now_epoch = 0.0 if clear_shield else time.time()

    guard_map = getattr(context, "indexing_grace_cache", None)
    if isinstance(guard_map, dict):
        g_entry = (
            guard_map.get(sym) if isinstance(guard_map.get(sym), dict) else {}
        )
        g_entry["last_sub_reentry_eval_mono"] = now_mono
        g_entry["last_sub_reentry_eval_ts"] = now_epoch
        if eval_price > 0.0:
            g_entry["last_sub_reentry_eval_price"] = round(
                safe_float(eval_price, 0.0), 4
            )
        guard_map[sym] = g_entry

    snap_map = getattr(context, "exit_snapshot_cache", None)
    if isinstance(snap_map, dict):
        s_entry = (
            snap_map.get(sym) if isinstance(snap_map.get(sym), dict) else {}
        )
        s_entry["last_sub_reentry_eval_mono"] = now_mono
        s_entry["last_sub_reentry_eval_ts"] = now_epoch
        if eval_price > 0.0:
            s_entry["last_sub_reentry_eval_price"] = round(
                safe_float(eval_price, 0.0), 4
            )
        snap_map[sym] = s_entry

    return now_epoch


def is_within_sub_reentry_monitor_time_shield(
    context: Any,
    st: Optional[Dict[str, Any]] = None,
    symbol: str = TARGET_SYMBOL,
) -> Tuple[bool, float]:
    """
    # [Case 88 : Default-ON 3층 서브 그리드 1층 공석 60.0초(1분) 주기 재장전 모니터 타임쉴드 판별기]:
    """
    in_post_sell, rem_sell = is_within_post_sell_time_shield(
        context, st, symbol
    )
    if in_post_sell:
        return True, rem_sell

    in_post_buy, rem_buy = is_within_post_buy_time_shield(context, st, symbol)
    if in_post_buy:
        return True, rem_buy

    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    now_mono = time.monotonic()

    guard_map = getattr(context, "indexing_grace_cache", None)
    if isinstance(guard_map, dict):
        g_entry = guard_map.get(sym)
        if isinstance(g_entry, dict):
            sub_re_mono = safe_float(
                g_entry.get("last_sub_reentry_eval_mono"), 0.0
            )
            if sub_re_mono > 0.0:
                elapsed_g = now_mono - sub_re_mono
                if 0.0 <= elapsed_g < REENTRY_MONITOR_TIME_SHIELD_SEC:
                    return True, round(
                        REENTRY_MONITOR_TIME_SHIELD_SEC - elapsed_g, 1
                    )

    snap_map = getattr(context, "exit_snapshot_cache", None)
    if isinstance(snap_map, dict):
        s_entry = snap_map.get(sym)
        if isinstance(s_entry, dict):
            s_sub_re_mono = safe_float(
                s_entry.get("last_sub_reentry_eval_mono"), 0.0
            )
            if s_sub_re_mono > 0.0:
                elapsed_s = now_mono - s_sub_re_mono
                if 0.0 <= elapsed_s < REENTRY_MONITOR_TIME_SHIELD_SEC:
                    return True, round(
                        REENTRY_MONITOR_TIME_SHIELD_SEC - elapsed_s, 1
                    )

    state_obj = (
        st
        if isinstance(st, dict)
        else (
            context.ledger.get_state(sym)
            if hasattr(context, "ledger")
            else {}
        )
    )
    sub_re_epoch = max(
        safe_float(state_obj.get("last_sub_reentry_eval_ts"), 0.0),
        safe_float(state_obj.get("last_sub_sell_fill_ts"), 0.0),
        safe_float(state_obj.get("last_sub_cycle_end_ts"), 0.0),
    )
    if sub_re_epoch > 0.0:
        elapsed_epoch = time.time() - sub_re_epoch
        if 0.0 <= elapsed_epoch < REENTRY_MONITOR_TIME_SHIELD_SEC:
            return True, round(
                REENTRY_MONITOR_TIME_SHIELD_SEC - elapsed_epoch, 1
            )

    return False, 0.0


def mark_reserve_deposit_check_shield(
    context: Any,
    symbol: str = TARGET_SYMBOL,
    clear_shield: bool = False,
) -> float:
    """
    # [Case 77 : 시드고갈 입금 대기 중 60.0초 주기 확인 타임쉴드 기록기]:
    """
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    now_mono = 0.0 if clear_shield else time.monotonic()
    now_epoch = 0.0 if clear_shield else time.time()

    guard_map = getattr(context, "indexing_grace_cache", None)
    if isinstance(guard_map, dict):
        g_entry = (
            guard_map.get(sym) if isinstance(guard_map.get(sym), dict) else {}
        )
        g_entry["last_reserve_check_mono"] = now_mono
        g_entry["last_reserve_check_ts"] = now_epoch
        guard_map[sym] = g_entry

    snap_map = getattr(context, "exit_snapshot_cache", None)
    if isinstance(snap_map, dict):
        s_entry = (
            snap_map.get(sym) if isinstance(snap_map.get(sym), dict) else {}
        )
        s_entry["last_reserve_check_mono"] = now_mono
        s_entry["last_reserve_check_ts"] = now_epoch
        snap_map[sym] = s_entry

    return now_epoch


def is_within_reserve_deposit_check_shield(
    context: Any,
    st: Optional[Dict[str, Any]] = None,
    symbol: str = TARGET_SYMBOL,
) -> Tuple[bool, float]:
    """
    # [Case 77 : 시드고갈 입금 대기 중 60.0초 타임쉴드 판별기]:
    """
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    now_mono = time.monotonic()

    guard_map = getattr(context, "indexing_grace_cache", None)
    if isinstance(guard_map, dict):
        g_entry = guard_map.get(sym)
        if isinstance(g_entry, dict):
            rc_mono = safe_float(g_entry.get("last_reserve_check_mono"), 0.0)
            if rc_mono > 0.0:
                elapsed_g = now_mono - rc_mono
                if 0.0 <= elapsed_g < RESERVE_DEPOSIT_CHECK_INTERVAL_SEC:
                    return True, round(
                        RESERVE_DEPOSIT_CHECK_INTERVAL_SEC - elapsed_g, 1
                    )

    snap_map = getattr(context, "exit_snapshot_cache", None)
    if isinstance(snap_map, dict):
        s_entry = snap_map.get(sym)
        if isinstance(s_entry, dict):
            s_rc_mono = safe_float(s_entry.get("last_reserve_check_mono"), 0.0)
            if s_rc_mono > 0.0:
                elapsed_s = now_mono - s_rc_mono
                if 0.0 <= elapsed_s < RESERVE_DEPOSIT_CHECK_INTERVAL_SEC:
                    return True, round(
                        RESERVE_DEPOSIT_CHECK_INTERVAL_SEC - elapsed_s, 1
                    )

    state_obj = (
        st
        if isinstance(st, dict)
        else (
            context.ledger.get_state(sym)
            if hasattr(context, "ledger")
            else {}
        )
    )
    rc_epoch = safe_float(state_obj.get("last_reserve_check_ts"), 0.0)
    if rc_epoch > 0.0:
        elapsed_epoch = time.time() - rc_epoch
        if 0.0 <= elapsed_epoch < RESERVE_DEPOSIT_CHECK_INTERVAL_SEC:
            return True, round(
                RESERVE_DEPOSIT_CHECK_INTERVAL_SEC - elapsed_epoch, 1
            )

    return False, 0.0


def _get_live_soxl_price(
    context: Any,
    prices: Dict[str, float],
    holdings: Dict[str, Dict[str, Any]],
    now_est: datetime,
) -> float:
    """
    실시간 가격 딕셔너리(prices) -> 캔들 캐시 -> 보유 잔고 현재가 순으로 SOXL 현재가를 추출한다.
    """
    lp = safe_float((prices or {}).get(TARGET_SYMBOL), 0.0)
    if lp > 0.0:
        return lp
    raw_cache = getattr(context, "candle_metrics_cache", {})
    base_met = (
        raw_cache.get(TARGET_SYMBOL) if isinstance(raw_cache, dict) else None
    )
    if isinstance(base_met, dict):
        met = refresh_metrics_with_live_tick(base_met, 0.0, now_est=now_est)
        lp = safe_float(met.get("live_price"), 0.0)
        if lp > 0.0:
            return lp
    h_info = (holdings or {}).get(TARGET_SYMBOL, {})
    return safe_float(h_info.get("last_price"), 0.0)


async def _fetch_fresh_current_soxl_price(
    context: Any,
    fallback_price: float = 0.0,
) -> float:
    """
    🚨 Case 65 & Case 73:
    60초 타임쉴드가 경과한 뒤 매수 조건 판정 및 지정가 주문 발주 직전에
    토스 Open API(/api/v1/prices)를 직접 호출하여 가장 최신의 실시간 현재가를 조회한다.
    """
    try:
        fresh_map = await context.api.get_current_prices_batch((TARGET_SYMBOL,))
        fresh_p = safe_float((fresh_map or {}).get(TARGET_SYMBOL), 0.0)
        if fresh_p > 0.0:
            if isinstance(getattr(context, "latest_prices", None), dict):
                context.latest_prices[TARGET_SYMBOL] = fresh_p
            if isinstance(getattr(context, "candle_metrics_cache", None), dict):
                base_met = context.candle_metrics_cache.get(TARGET_SYMBOL)
                if isinstance(base_met, dict):
                    context.candle_metrics_cache[TARGET_SYMBOL] = (
                        refresh_metrics_with_live_tick(base_met, fresh_p)
                    )
            return fresh_p
    except Exception as exc:
        logger.debug("매수 직전 실시간 현재가 재조회 폴백 사용: %s", exc)
    return safe_float(fallback_price, 0.0)


def min_req_cash_str(val: float) -> str:
    return f"{safe_float(val, 0.0):,.2f}"


# ---------------------------------------------------------------------------
# [핵심 0-B · Case 75, Case 77, Case 86, Case 89 & Case 91] GUARD30 자투리 차단 · 계좌별 동적 수수료율 연동 · 예수금 API 일시 오류 방어 · 횟수 제한 없는 무제한 온디맨드 예비수혈 카운트 · 단 1회 입금 요청 알림 실행기
# ---------------------------------------------------------------------------
async def _check_and_execute_guard30_or_reserve_injection(
    context: Any,
    st_now: Dict[str, Any],
    exec_order_p: float,
    portion_budget: float,
    l1_actual_cost_usd: float,
    is_dip_promotion: bool,
    is_vacant_l1_reentry: bool,
    trigger_desc: str,
) -> Tuple[bool, float, float, Dict[str, Any]]:
    """
    # MODIFIED [Case 75, Case 77, Case 86, Case 89 & Case 91 : 예비시드 6회 상한 제한 전면 해제 — 무제한 수혈 및 수혈 횟수 카운트]:
    본 그리드 주문 발주 직전(뮤텍스 내부)에 호출되어:
    1) 토스 실계좌 주문가능 달러(`raw_bp_usd = await context.api.get_buying_power_usd(safety_buffer_pct=0.0)`)를 조회하되,
       원장 가용현금이 충분함에도(`now_free_cash >= est_min_req`) 일시 네트워크 타임아웃으로 `0.0` 이 반환되면
       `0.25초` 후 1회 재시도하고, 여전히 `0.0` 이면 허위 시드고갈 알림 발송이나 영구 래치 잠금 없이
       해당 틱만 조용히 보류(`HOLD_TRANSIENT_BP_API_ERROR`)한다!
    2) `evaluate_guard30_and_reserve_injection(..., round_trip_fee_rate_pct=eff_rt_pct)` 으로
       계좌 고유 수수료율이 반영된 30% 자투리 가드(`min_req_cash`) 통과 여부 및 예비시드 수혈 가능 여부를 판정한다.
    3) [PROCEED_NORMAL] / [INJECT_AND_PROCEED] (횟수 제한 없이 자동 수혈 및 `used_reserve_portions_cnt`, `total_reserve_injected_cnt` 카운트) / [BLOCK_AND_ALERT_DEPOSIT] 분기 처리
    """
    now_free_cash = max(0.0, safe_float(st_now.get("free_cash_usd"), 0.0))
    cur_used_res = max(0, safe_int(st_now.get("used_reserve_portions_cnt"), 0))
    cur_inj_usd = max(0.0, safe_float(st_now.get("injected_reserve_usd"), 0.0))

    eff_rt_pct = resolve_effective_round_trip_fee_rate_pct(state_dict=st_now)
    fee_mult = 1.0 + (eff_rt_pct / 100.0)
    est_min_req = max(
        exec_order_p * fee_mult,
        portion_budget * MIN_DIP_BUDGET_RATIO,
        (l1_actual_cost_usd * MIN_DIP_VS_L1_RATIO if is_dip_promotion else 0.0),
    )

    raw_bp_usd = await context.api.get_buying_power_usd(safety_buffer_pct=0.0)
    if raw_bp_usd <= 0.0 and now_free_cash >= est_min_req:
        await asyncio.sleep(0.25)
        raw_bp_usd = await context.api.get_buying_power_usd(
            safety_buffer_pct=0.0
        )
        if raw_bp_usd <= 0.0:
            logger.debug(
                "🛡️ [Case 77 예수금 API 일시 조회 지연 방어] 원장 가용현금($%.2f >= 최소 $%.2f) 정상이나 예수금 API가 0.0을 반환하여 허위 시드고갈 알림 없이 다음 루프 재시도",
                now_free_cash,
                est_min_req,
            )
            return (
                False,
                now_free_cash,
                0.0,
                {
                    "action": "HOLD_TRANSIENT_BP_API_ERROR",
                    "should_proceed": False,
                    "free_cash_usd": now_free_cash,
                    "min_req_cash": round(est_min_req, 4),
                },
            )

    eff_bp_for_eval: Optional[float] = (
        raw_bp_usd if raw_bp_usd > 0.0 else 0.0
    )

    guard_eval = evaluate_guard30_and_reserve_injection(
        free_cash_usd=now_free_cash,
        broker_bp_usd=eff_bp_for_eval,
        exec_price=exec_order_p,
        portion_budget=portion_budget,
        l1_actual_cost_usd=l1_actual_cost_usd,
        is_dip_promotion=is_dip_promotion,
        used_reserve_portions_cnt=cur_used_res,
        max_reserve_portions=MAX_RESERVE_PORTIONS,
        round_trip_fee_rate_pct=eff_rt_pct,
    )
    action = str(guard_eval.get("action") or "BLOCK_AND_ALERT_DEPOSIT")
    eff_bp_for_order = round(raw_bp_usd * 0.998, 4) if raw_bp_usd > 0.0 else 0.0

    # [케이스 1] 현재 가용현금 및 실계좌 예수금이 충분한 경우 -> 정상 매수 진행
    if action == "PROCEED_NORMAL":
        if bool(st_now.get("waiting_reserve_deposit")) or bool(
            st_now.get("waiting_reserve_deposit_alert_sent")
        ):
            mark_reserve_deposit_check_shield(
                context, TARGET_SYMBOL, clear_shield=True
            )
            await context.ledger.update_state(
                TARGET_SYMBOL,
                waiting_reserve_deposit=False,
                waiting_reserve_deposit_alert_sent=False,
                required_reserve_deposit_usd=0.0,
                last_reserve_check_ts=0.0,
            )
        return True, now_free_cash, eff_bp_for_order, guard_eval

    # [케이스 2] 토스 계좌에 여유자금이 입금되어 있어 온디맨드 예비시드 무제한 자동 수혈 및 횟수 카운트 실행! (Case 91)
    if action == "INJECT_AND_PROCEED":
        inj_portions = max(1, safe_int(guard_eval.get("inject_portions"), 1))
        inj_usd = round(max(0.01, safe_float(guard_eval.get("inject_usd"), 0.0)), 4)
        new_used_cnt = cur_used_res + inj_portions
        new_inj_usd = round(cur_inj_usd + inj_usd, 4)
        new_tot_inj_cnt = (
            safe_int(st_now.get("total_reserve_injected_cnt"), 0) + inj_portions
        )
        new_day_inj_cnt = (
            safe_int(st_now.get("daily_reserve_injected_cnt"), 0) + inj_portions
        )

        mark_reserve_deposit_check_shield(
            context, TARGET_SYMBOL, clear_shield=True
        )
        updated_st = await context.ledger.update_state(
            TARGET_SYMBOL,
            used_reserve_portions_cnt=new_used_cnt,
            injected_reserve_usd=new_inj_usd,
            total_reserve_injected_cnt=new_tot_inj_cnt,
            daily_reserve_injected_cnt=new_day_inj_cnt,
            waiting_reserve_deposit=False,
            waiting_reserve_deposit_alert_sent=False,
            required_reserve_deposit_usd=0.0,
            last_reserve_check_ts=0.0,
        )
        updated_free_cash = max(
            0.0,
            safe_float(updated_st.get("free_cash_usd"), now_free_cash + inj_usd),
        )
        logger.info(
            "💉 [Case 77/89/91 SOXL 온디맨드 예비시드 자동 수혈 완료] +%d회분(+%.2f$) 수혈 -> 가용현금 $%.2f (현재수혈 %d회분 · 누적총 %d회 · 수혈잔액 $%.2f · 타점=%s)",
            inj_portions,
            inj_usd,
            updated_free_cash,
            new_used_cnt,
            new_tot_inj_cnt,
            new_inj_usd,
            trigger_desc,
        )
        if hasattr(context, "send_slim_alert"):
            await context.send_slim_alert(
                title=f"💉 [SOXL 자동 시멘트추가 (+{inj_portions}회분 · +${inj_usd:,.2f})]",
                body=(
                    f"시드고갈(30% 가드) 감지 즉시 토스 계좌 여유자금에서 +{inj_portions}회분(${inj_usd:,.2f}) 자동 시멘트추가 완료! · "
                    f"시멘트추가 후 가용현금 ${updated_free_cash:,.2f} · "
                    f"현재 시멘트추가 {new_used_cnt}회분(누적 총 {new_tot_inj_cnt}회 · 시멘트추가 잔액 ${new_inj_usd:,.2f} / 0주 졸업 시 원금 자동 상환) · "
                    f"즉시 {trigger_desc} 정량 매수를 집행합니다!"
                ),
            )
        return True, updated_free_cash, eff_bp_for_order, guard_eval

    # [케이스 3] 계좌 미입금 상태 -> 자투리 1주 매수 차단 & 단 1회 입금 요청 알림(영구 래치 · 6회 제한 없이 입금 시 즉시 자동 수혈)
    already_waiting_dep = bool(st_now.get("waiting_reserve_deposit", False))
    alert_already_sent = bool(
        st_now.get("waiting_reserve_deposit_alert_sent", False)
    )
    rec_dep_usd = round(
        max(
            portion_budget,
            safe_float(guard_eval.get("recommended_deposit_usd"), portion_budget),
        ),
        2,
    )
    min_req_c = safe_float(guard_eval.get("min_req_cash"), portion_budget * 0.30)
    needed_p = max(1, safe_int(guard_eval.get("needed_portions"), 1))
    tot_inj_cnt_now = safe_int(st_now.get("total_reserve_injected_cnt"), 0)

    now_rc_epoch = mark_reserve_deposit_check_shield(
        context, TARGET_SYMBOL, clear_shield=False
    )
    re_epoch = safe_float(st_now.get("last_reentry_eval_ts"), 0.0)
    if is_vacant_l1_reentry:
        re_epoch = mark_reentry_monitor_60s_cycle_shield(
            context=context, symbol=TARGET_SYMBOL, eval_price=exec_order_p
        )

    # [Case 75 & Case 77 : 이미 시드고갈 입금 대기 상태이고 1회 알림도 발송 완료된 경우 중복 카운터 증가 및 매 60초 os.fsync 디스크 쓰기 스킵!]
    if already_waiting_dep and alert_already_sent:
        prev_req_dep = safe_float(
            st_now.get("required_reserve_deposit_usd"), 0.0
        )
        if abs(prev_req_dep - rec_dep_usd) >= 1.0:
            await context.ledger.update_state(
                TARGET_SYMBOL,
                required_reserve_deposit_usd=rec_dep_usd,
            )
        return False, now_free_cash, eff_bp_for_order, guard_eval

    is_dust_blk = bool(guard_eval.get("is_dust_blocked", False))
    dust_inc = 1 if is_dust_blk else 0
    new_dust_cnt = safe_int(st_now.get("dust_guard_blocked_cnt"), 0) + dust_inc
    new_day_dust_cnt = (
        safe_int(st_now.get("daily_dust_guard_blocked_cnt"), 0) + dust_inc
    )
    new_pass_cnt = safe_int(st_now.get("seed_protect_pass_cnt"), 0) + 1
    new_day_pass = safe_int(st_now.get("daily_seed_protect_pass_cnt"), 0) + 1

    await context.ledger.update_state(
        TARGET_SYMBOL,
        waiting_reserve_deposit=True,
        waiting_reserve_deposit_alert_sent=True,
        required_reserve_deposit_usd=rec_dep_usd,
        last_reserve_check_ts=now_rc_epoch,
        last_reentry_eval_ts=re_epoch,
        dust_guard_blocked_cnt=new_dust_cnt,
        daily_dust_guard_blocked_cnt=new_day_dust_cnt,
        seed_protect_pass_cnt=new_pass_cnt,
        daily_seed_protect_pass_cnt=new_day_pass,
    )

    if not alert_already_sent and hasattr(context, "send_slim_alert"):
        title_msg = (
            f"🚨 [💉 SOXL 시드고갈 감지 · 예비시드 {needed_p}회분(${rec_dep_usd:,.2f}) 입금 요청]"
        )
        body_msg = (
            f"타점({trigger_desc} @ ${exec_order_p:.2f}) 도달 · "
            f"현재 가용현금(${now_free_cash:,.2f}) 및 토스 주문가능금액(${raw_bp_usd:,.2f})이 "
            f"30% 자투리 승격 방지 가드(${min_req_cash_str(min_req_c)}) 미만이어서 자투리 매수를 차단했습니다. · "
            f"토스 달러 계좌에 예비시드(권장 ${rec_dep_usd:,.2f} · 최소 30% 가드 이상 · 현재 시멘트추가 {cur_used_res}회/누적 {tot_inj_cnt_now}회)를 입금해 주시면 "
            f"60초 내 자동 감지하여 횟수 제한 없이 즉시 시멘트추가 매수합니다! (※ 스팸 방지를 위해 입금 요청 알림은 1회만 발송됩니다)"
        )
        await context.send_slim_alert(title=title_msg, body=body_msg)
        logger.warning(
            "🚨 [Case 77/91 시드고갈 단 1회 입금 요청 알림 발송 완료 & 래치 잠금] 가용=$%.2f · 토스예수금=$%.2f · 30%%가드=$%.2f · 권장입금=$%.2f · 현재수혈=%d회(누적%d회)",
            now_free_cash,
            raw_bp_usd,
            min_req_c,
            rec_dep_usd,
            cur_used_res,
            tot_inj_cnt_now,
        )

    return False, now_free_cash, eff_bp_for_order, guard_eval
# ---------------------------------------------------------------------------
# [핵심 1] 매수 체결(FILLED) 커밋 · 비례 자투리 정산(Case 78) · 현재 사이클 자투리 절약금(cycle_leftover_saved_usd) 누적 · Default-ON 3층 서브 그리드 SUB_L1_L3_MERGE(Case 88) · 1~7층 본 그리드 L2+L7 중간합병 및 최고도달회차 잠금(Case 87) · 매수 후 60초 타임쉴드 각인
# ---------------------------------------------------------------------------
async def _commit_filled_buy_to_stratum_ledger(
    context: Any,
    filled_qty: int,
    avg_fill_price: float,
    portion_budget: float,
    lot_type: str,
    settled_order_id: str = "",
    ordered_qty: Optional[int] = None,
) -> Dict[str, Any]:
    """
    # MODIFIED [🎯 1, 🎯 3, 🎯 4 & Case 25, 46, 53, 59, 60, 61, 65, 67, 69, 71, 72, 73, 74, 76, 77, 78, Case 87, Case 88 & Case 91]:
    매수 주문 체결(FILLED 또는 부분 체결 후 60초 타임아웃/세션 경계 취소 종료)이 확인된 즉시:
    1) 🛡️ [Case 88 : Default-ON 3층 서브 그리드(lot_type 이 "SUB_" 로 시작) 체결 분리 정산 · SUB_L1_L3_MERGE 양끝 합병 · sub_consec_frozen_days = 0 리셋 · cycle_leftover_saved_usd 동시 누적]
    2) 👑 [Case 78 & Case 87 : 본 그리드 부분 체결 비례 자투리 정산 · cycle_leftover_saved_usd 동시 누적 · L2_L7_MERGE_SORT 중간층 재배치 · cycle_ratchet_max_lots 잠금 갱신 · main_consec_frozen_days = 0 리셋]
    """
    st = context.ledger.get_state(TARGET_SYMBOL)
    old_buckets = buckets_from_dicts(st.get("buckets", []))
    old_sub_buckets = buckets_from_dicts(st.get("sub_buckets", []))

    q_int = max(1, safe_int(filled_qty, 1))
    ord_q = max(
        q_int,
        safe_int(
            ordered_qty
            if ordered_qty is not None
            else st.get("ordered_qty"),
            q_int,
        ),
    )
    fill_p = round(max(0.01, safe_float(avg_fill_price, 0.01)), 4)
    actual_spent = round(float(q_int) * fill_p, 4)
    raw_tag = str(lot_type or "QUOTA_L1").upper().strip()
    eff_oid = str(settled_order_id or st.get("buy_order_id") or "").strip()

    settled_oids: List[str] = list(st.get("last_settled_order_ids") or [])
    if eff_oid and eff_oid not in settled_oids:
        settled_oids.append(eff_oid)
    settled_oids = settled_oids[-50:]

    now_buy_epoch = time.time()

    # -----------------------------------------------------------------------
    # [트랙 1 · Case 88 분기 : Default-ON 3층 서브 그리드(lot_type 이 "SUB_" 로 시작) 체결 커밋]
    # -----------------------------------------------------------------------
    if raw_tag.startswith("SUB_"):
        sub_tag = (
            "SUB_REENTRY_1FL"
            if raw_tag in ("SUB_REENTRY_1FL_BREAKOUT", "SUB_REENTRY_1FL_PULLBACK")
            else raw_tag
        )
        raw_sub_budget = safe_float(portion_budget, 0.0)
        if raw_sub_budget <= 0.0:
            eff_sub_budget = actual_spent
            saved_from_sub_portion = 0.0
        elif q_int < ord_q and ord_q > 0:
            eff_sub_budget = round(
                raw_sub_budget * (float(q_int) / float(ord_q)), 4
            )
            saved_from_sub_portion = round(
                max(0.0, eff_sub_budget - actual_spent), 4
            )
        else:
            eff_sub_budget = raw_sub_budget
            saved_from_sub_portion = round(
                max(0.0, eff_sub_budget - actual_spent), 4
            )

        was_sub_empty = len(old_sub_buckets) == 0
        was_sub_l2_only = bool(
            len(old_sub_buckets) > 0 and not has_active_l1_bucket(old_sub_buckets)
        )
        eff_sub_merge_mode = str(
            st.get("sub_merge_mode") or SUB_MERGE_MODE_L1_L3
        ).upper()

        new_sub_buckets, did_sub_merge = add_lot_to_sub_grid_with_flag(
            sub_queue=old_sub_buckets,
            buy_qty=q_int,
            buy_price=fill_p,
            actual_spent_usd=actual_spent,
            lot_type=sub_tag,
            max_tiers=SUB_MAX_TIERS_3,
            merge_mode=eff_sub_merge_mode,
        )

        raw_sub_target_q = max(
            0, safe_int(st.get("sub_l1_target_quota_qty"), 0)
        )
        cur_sub_l1_qty = new_sub_buckets[0].qty if new_sub_buckets else q_int
        if sub_tag == "SUB_TOPUP_1FL":
            next_sub_l1_target_q = max(cur_sub_l1_qty, raw_sub_target_q)
        else:
            next_sub_l1_target_q = max(cur_sub_l1_qty, ord_q)
        sub_rem_after_fill = max(0, next_sub_l1_target_q - cur_sub_l1_qty)

        old_sub_min_p = safe_float(st.get("sub_cycle_min_buy_price"), 0.0)
        pending_sub_step_p = safe_float(
            st.get("pending_sub_step_up_min_price"), 0.0
        )
        is_sub_unlock_fill = False

        if was_sub_empty or old_sub_min_p <= 0.0:
            new_sub_cycle_min_p = fill_p
        elif pending_sub_step_p > 0.0 and sub_tag not in (
            "SUB_REENTRY_1FL",
            "SUB_TOPUP_1FL",
        ):
            new_sub_cycle_min_p = round(min(pending_sub_step_p, fill_p), 4)
            is_sub_unlock_fill = True
        else:
            new_sub_cycle_min_p = round(min(old_sub_min_p, fill_p), 4)

        new_sub_lots = sum(sb.lot_count for sb in new_sub_buckets)
        new_sub_shares = sum(sb.qty for sb in new_sub_buckets)
        new_sub_tiers = len(new_sub_buckets)

        prev_sub_ratchet_lots = max(
            0, safe_int(st.get("sub_ratchet_max_lots"), 0)
        )
        if was_sub_empty or is_sub_unlock_fill:
            new_sub_ratchet_lots = new_sub_lots
        else:
            new_sub_ratchet_lots = max(prev_sub_ratchet_lots, new_sub_lots)

        tot_buy_ev = safe_int(st.get("total_buy_events"), 0) + 1
        tot_buy_sh = safe_int(st.get("total_buy_shares"), 0) + q_int
        day_buy_ev = safe_int(st.get("daily_buy_events"), 0) + 1

        sub_buy_ev = safe_int(st.get("sub_buy_events"), 0) + 1
        sub_buy_sh = safe_int(st.get("sub_buy_shares"), 0) + q_int
        day_sub_buy_cnt = safe_int(st.get("daily_sub_buy_cnt"), 0) + 1
        day_sub_buy_ev = safe_int(st.get("daily_sub_buy_events"), 0) + 1
        sub_merge_ev = safe_int(st.get("sub_merge_events"), 0) + (
            1 if did_sub_merge else 0
        )
        sub_unlock_inc = 1 if is_sub_unlock_fill else 0
        sub_unlock_ev = (
            safe_int(st.get("sub_unlock_events"), 0) + sub_unlock_inc
        )
        day_sub_unlock_ev = (
            safe_int(st.get("daily_sub_unlock_events"), 0) + sub_unlock_inc
        )

        cum_saved = round(
            safe_float(st.get("cumulative_leftover_saved_usd"), 0.0)
            + saved_from_sub_portion,
            4,
        )
        day_saved = round(
            safe_float(st.get("daily_leftover_saved_usd"), 0.0)
            + saved_from_sub_portion,
            4,
        )
        cyc_saved = round(
            safe_float(st.get("cycle_leftover_saved_usd"), 0.0)
            + saved_from_sub_portion,
            4,
        )

        mark_auto_fill_grace_shield(
            context=context,
            symbol=TARGET_SYMBOL,
            lot_type=sub_tag,
            fill_price=fill_p,
            filled_qty=q_int,
        )
        mark_sub_reentry_monitor_60s_cycle_shield(
            context=context,
            symbol=TARGET_SYMBOL,
            eval_price=fill_p,
            clear_shield=True,
        )
        mark_reserve_deposit_check_shield(
            context=context,
            symbol=TARGET_SYMBOL,
            clear_shield=True,
        )

        updated_st = await context.ledger.update_state(
            TARGET_SYMBOL,
            sub_buckets=buckets_to_dicts(new_sub_buckets),
            sub_anchor_price=(
                new_sub_buckets[0].book_price if new_sub_buckets else fill_p
            ),
            sub_cycle_min_buy_price=round(new_sub_cycle_min_p, 4),
            sub_ratchet_max_lots=new_sub_ratchet_lots,
            sub_l1_target_quota_qty=next_sub_l1_target_q,
            sub_consec_frozen_days=0,
            buy_order_id="",
            ordered_qty=0,
            buy_price=0.0,
            pending_portion_budget=0.0,
            pending_lot_type="",
            pending_step_up_min_price=0.0,
            pending_sub_step_up_min_price=0.0,
            waiting_reserve_deposit=False,
            waiting_reserve_deposit_alert_sent=False,
            required_reserve_deposit_usd=0.0,
            last_reserve_check_ts=0.0,
            last_settled_order_ids=settled_oids,
            total_buy_events=tot_buy_ev,
            total_buy_shares=tot_buy_sh,
            daily_buy_events=day_buy_ev,
            sub_buy_events=sub_buy_ev,
            sub_buy_shares=sub_buy_sh,
            daily_sub_buy_cnt=day_sub_buy_cnt,
            daily_sub_buy_events=day_sub_buy_ev,
            sub_merge_events=sub_merge_ev,
            sub_unlock_events=sub_unlock_ev,
            daily_sub_unlock_events=day_sub_unlock_ev,
            cumulative_leftover_saved_usd=cum_saved,
            daily_leftover_saved_usd=day_saved,
            cycle_leftover_saved_usd=cyc_saved,
            entry_ts=now_buy_epoch,
            last_buy_fill_ts=now_buy_epoch,
            last_sub_buy_fill_ts=now_buy_epoch,
            last_sub_reentry_eval_ts=0.0,
        )

        context.wakeup_event.set()
        free_cash_now = safe_float(updated_st.get("free_cash_usd"), 0.0)
        summary = summarize_stratum_portfolio(updated_st, live_price=fill_p)
        sub_l1_target = safe_float(summary.get("sub_l1_target_price"), 0.0)
        sub_u_cnt = safe_int(summary.get("sub_upper_tier_count"), 0)
        sub_u_qty = safe_int(summary.get("sub_upper_qty"), 0)
        sub_u_wma_p = safe_float(summary.get("sub_upper_wma_price"), 0.0)
        sub_u_wma_t = safe_float(summary.get("sub_upper_wma_target_price"), 0.0)
        sub_trig_buy_p = safe_float(summary.get("sub_trigger_buy_price"), 0.0)
        sub_drop_req_p = safe_float(summary.get("sub_drop_buy_pct"), -1.0)
        sub_l1_book_now = (
            new_sub_buckets[0].book_price if new_sub_buckets else fill_p
        )
        merge_badge = " · 🔄구1층+구3층 양끝합병 완료!" if did_sub_merge else ""
        cap_badge = (
            " · 🔒4/4회분 상한 캡 도달"
            if new_sub_lots >= SUB_MAX_TOTAL_LOTS_4
            else ""
        )

        if hasattr(context, "send_slim_alert"):
            sub_rem_note = (
                f" · 🎯서브잔량 {sub_rem_after_fill}주(목표 {next_sub_l1_target_q}주 중 {cur_sub_l1_qty}주 체결 ➔ "
                f"🛡️60초 타임쉴드 후 1.5초 모니터에서 ${sub_l1_book_now:.2f} 이하 도래 시 잔량 60초 지정가 재대기!)"
                if sub_rem_after_fill > 0
                else ""
            )
            sub_upper_note = (
                f" · 서브2~{new_sub_tiers}층({sub_u_cnt}개층·{sub_u_qty}주) 이평 ${sub_u_wma_p:.2f}(목표 ${sub_u_wma_t:.2f})"
                if len(new_sub_buckets) >= 2
                else ""
            )
            if sub_tag == "SUB_TOPUP_1FL":
                title_str = (
                    f"🛡️ [SOXL 서브그리드 1층 미체결 잔량 보충 체결] +{q_int}주 @ ${fill_p:.2f} "
                    f"(서브1층 {cur_sub_l1_qty}/{next_sub_l1_target_q}주 합산)"
                )
            elif is_sub_unlock_fill:
                title_str = (
                    f"🔓 [SOXL 서브그리드 10일/-10% 저가해금 추매 체결 ({new_sub_lots}/{SUB_MAX_TOTAL_LOTS_4}회분 · {new_sub_tiers}개층)] "
                    f"{q_int}주 @ ${fill_p:.2f}"
                )
            elif was_sub_l2_only and sub_tag == "SUB_REENTRY_1FL":
                title_str = (
                    f"🛡️ [SOXL 서브그리드 1층 재장전 체결 ({new_sub_lots}/{SUB_MAX_TOTAL_LOTS_4}회분 · {new_sub_tiers}개층)] "
                    f"{q_int}주 @ ${fill_p:.2f}"
                )
            else:
                title_str = (
                    f"🛡️ [SOXL 3층 서브그리드 ({new_sub_lots}/{SUB_MAX_TOTAL_LOTS_4}회분 · {new_sub_tiers}개층) 지정가 매수 체결] "
                    f"{q_int}주 @ ${fill_p:.2f}"
                )
            body_str = (
                f"실사용 ${actual_spent:,.2f} (4%정량 자투리 +${saved_from_sub_portion:.2f} 시드보존){merge_badge}{cap_badge} · "
                f"🛡️60초 타임쉴드 후 서브1층목표 ${sub_l1_target:.2f}(+1.5%) 감시{sub_upper_note}{sub_rem_note} · "
                f"서브기억저가 ${new_sub_cycle_min_p:.2f}(단차 {sub_drop_req_p:.1f}% ➔ ${sub_trig_buy_p:.2f}) · "
                f"가용현금 ${free_cash_now:,.2f} (서브 총 {new_sub_shares}주)"
            )
            await context.send_slim_alert(title=title_str, body=body_str)

        return {
            "status": "SUB_BUY_FILLED_AND_MERGED",
            "symbol": TARGET_SYMBOL,
            "lot_type": sub_tag,
            "is_sub_unlock": is_sub_unlock_fill,
            "did_sub_merge": did_sub_merge,
            "filled_qty": q_int,
            "ordered_qty": ord_q,
            "sub_l1_target_quota_qty": next_sub_l1_target_q,
            "sub_l1_rem_quota_qty": sub_rem_after_fill,
            "fill_price": fill_p,
            "actual_spent_usd": actual_spent,
            "saved_from_portion_usd": saved_from_sub_portion,
            "sub_cycle_min_buy_price": round(new_sub_cycle_min_p, 4),
            "sub_ratchet_max_lots": new_sub_ratchet_lots,
            "sub_held_lots": new_sub_lots,
            "sub_held_tiers": new_sub_tiers,
            "sub_held_shares": new_sub_shares,
            "free_cash_usd": free_cash_now,
        }

    # -----------------------------------------------------------------------
    # [트랙 2 : 본 그리드 8% 정량 매수(REENTRY_1FL / TOPUP_1FL / DIP_1FL) 커밋]
    # -----------------------------------------------------------------------
    tag = (
        "REENTRY_1FL"
        if raw_tag in ("REENTRY_1FL_BREAKOUT", "REENTRY_1FL_PULLBACK")
        else raw_tag
    )
    raw_portion_budget = safe_float(portion_budget, 0.0)
    if raw_portion_budget <= 0.0:
        eff_portion_budget = actual_spent
        saved_from_portion = 0.0
    elif q_int < ord_q and ord_q > 0:
        eff_portion_budget = round(
            raw_portion_budget * (float(q_int) / float(ord_q)), 4
        )
        saved_from_portion = round(
            max(0.0, eff_portion_budget - actual_spent), 4
        )
    else:
        eff_portion_budget = raw_portion_budget
        saved_from_portion = round(
            max(0.0, eff_portion_budget - actual_spent), 4
        )

    was_empty = len(old_buckets) == 0
    was_l2_only = bool(
        len(old_buckets) > 0 and not has_active_l1_bucket(old_buckets)
    )
    prev_l1_p = (
        old_buckets[0].book_price
        if (old_buckets and has_active_l1_bucket(old_buckets))
        else 0.0
    )

    eff_merge_mode = str(
        st.get("grid_merge_mode") or DEFAULT_GRID_MERGE_MODE
    ).upper()
    new_buckets = vrev_add_quota_lot_and_merge_2tier(
        queue=old_buckets,
        buy_qty=q_int,
        buy_price=fill_p,
        actual_spent_usd=actual_spent,
        lot_type=tag,
        max_tiers=MAX_GRID_TIERS_7,
        merge_mode=eff_merge_mode,
    )

    raw_target_q = max(0, safe_int(st.get("l1_target_quota_qty"), 0))
    cur_l1_qty = new_buckets[0].qty if new_buckets else q_int
    if tag == "TOPUP_1FL":
        next_l1_target_q = max(cur_l1_qty, raw_target_q)
    else:
        next_l1_target_q = max(cur_l1_qty, ord_q)
    rem_after_fill = max(0, next_l1_target_q - cur_l1_qty)

    old_min_p = safe_float(st.get("cycle_min_buy_price"), 0.0)
    pending_step_up_p = safe_float(st.get("pending_step_up_min_price"), 0.0)
    is_step_up_unlock_fill = False

    if was_empty or old_min_p <= 0.0:
        new_cycle_min_p = fill_p
    elif pending_step_up_p > 0.0 and tag not in (
        "REENTRY_1FL",
        "TOPUP_1FL",
    ):
        new_cycle_min_p = round(min(pending_step_up_p, fill_p), 4)
        is_step_up_unlock_fill = True
    else:
        new_cycle_min_p = round(min(old_min_p, fill_p), 4)

    new_held_lots = sum(b.lot_count for b in new_buckets)
    new_held_shares = sum(b.qty for b in new_buckets)
    new_held_tiers = len(new_buckets)

    # [Case 87 : 사이클 최고 도달 회차(cycle_ratchet_max_lots) 잠금 갱신 및 STEP2X 스텝업 해금 시 동기화]
    prev_ratchet_lots = max(0, safe_int(st.get("cycle_ratchet_max_lots"), 0))
    if was_empty or is_step_up_unlock_fill:
        new_ratchet_max_lots = new_held_lots
    else:
        new_ratchet_max_lots = max(prev_ratchet_lots, new_held_lots)

    tot_buy_ev = safe_int(st.get("total_buy_events"), 0) + 1
    tot_buy_sh = safe_int(st.get("total_buy_shares"), 0) + q_int
    day_buy_ev = safe_int(st.get("daily_buy_events"), 0) + 1
    day_main_buy_cnt = safe_int(st.get("daily_main_buy_cnt"), 0) + 1
    unlock_inc = 1 if is_step_up_unlock_fill else 0
    cond_unlock_ev = safe_int(st.get("cond_unlock_buy_events"), 0) + unlock_inc
    day_unlock_ev = safe_int(st.get("daily_unlock_buy_events"), 0) + unlock_inc
    extra_13 = safe_int(st.get("extra_13plus_buy_events"), 0) + (
        1
        if (tag != "TOPUP_1FL" and new_held_lots > BASE_MAX_LOTS_8PCT)
        else 0
    )
    cum_saved = round(
        safe_float(st.get("cumulative_leftover_saved_usd"), 0.0)
        + saved_from_portion,
        4,
    )
    day_saved = round(
        safe_float(st.get("daily_leftover_saved_usd"), 0.0)
        + saved_from_portion,
        4,
    )
    cyc_saved = round(
        safe_float(st.get("cycle_leftover_saved_usd"), 0.0)
        + saved_from_portion,
        4,
    )

    mark_auto_fill_grace_shield(
        context=context,
        symbol=TARGET_SYMBOL,
        lot_type=tag,
        fill_price=fill_p,
        filled_qty=q_int,
    )
    mark_reentry_monitor_60s_cycle_shield(
        context=context,
        symbol=TARGET_SYMBOL,
        eval_price=fill_p,
        clear_shield=True,
    )
    mark_reserve_deposit_check_shield(
        context=context,
        symbol=TARGET_SYMBOL,
        clear_shield=True,
    )

    updated_st = await context.ledger.update_state(
        TARGET_SYMBOL,
        buckets=buckets_to_dicts(new_buckets),
        anchor_price=new_buckets[0].book_price if new_buckets else fill_p,
        cycle_min_buy_price=round(new_cycle_min_p, 4),
        cycle_ratchet_max_lots=new_ratchet_max_lots,
        ratchet_anchor_price=new_buckets[0].book_price if new_buckets else fill_p,
        cycle_reanchor_credit_usd=0.0,
        l1_target_quota_qty=next_l1_target_q,
        main_consec_frozen_days=0,
        daily_main_buy_cnt=day_main_buy_cnt,
        buy_order_id="",
        ordered_qty=0,
        buy_price=0.0,
        pending_portion_budget=0.0,
        pending_lot_type="",
        pending_step_up_min_price=0.0,
        pending_sub_step_up_min_price=0.0,
        waiting_reserve_deposit=False,
        waiting_reserve_deposit_alert_sent=False,
        required_reserve_deposit_usd=0.0,
        last_reserve_check_ts=0.0,
        last_settled_order_ids=settled_oids,
        total_buy_events=tot_buy_ev,
        total_buy_shares=tot_buy_sh,
        daily_buy_events=day_buy_ev,
        cond_unlock_buy_events=cond_unlock_ev,
        daily_unlock_buy_events=day_unlock_ev,
        extra_13plus_buy_events=extra_13,
        cumulative_leftover_saved_usd=cum_saved,
        daily_leftover_saved_usd=day_saved,
        cycle_leftover_saved_usd=cyc_saved,
        entry_ts=now_buy_epoch,
        last_buy_fill_ts=now_buy_epoch,
        last_reentry_eval_ts=0.0,
    )

    context.wakeup_event.set()
    free_cash_now = safe_float(updated_st.get("free_cash_usd"), 0.0)
    summary = summarize_stratum_portfolio(updated_st, live_price=fill_p)
    l1_target = safe_float(summary.get("l1_target_price"), 0.0)
    u_cnt = safe_int(summary.get("upper_tier_count"), 0)
    u_qty = safe_int(summary.get("upper_qty"), 0)
    u_wma_p = safe_float(summary.get("upper_wma_price"), 0.0)
    u_wma_t = safe_float(summary.get("upper_wma_target_price"), 0.0)
    trig_buy_p = safe_float(summary.get("trigger_buy_price"), 0.0)
    drop_req_p = safe_float(summary.get("drop_buy_pct"), -1.0)
    l1_book_now = new_buckets[0].book_price if new_buckets else fill_p
    ratchet_note = (
        f"(단차잠금 {new_ratchet_max_lots}회차)"
        if new_ratchet_max_lots > new_held_lots
        else ""
    )

    if hasattr(context, "send_slim_alert"):
        rem_quota_note = (
            f" · 🎯미체결 잔량 {rem_after_fill}주(목표 {next_l1_target_q}주 중 {cur_l1_qty}주 체결 ➔ "
            f"🛡️60초 타임쉴드 후 1.5초 모니터에서 ${l1_book_now:.2f} 이하 도래 시 잔량 60초 지정가 재대기!)"
            if rem_after_fill > 0
            else ""
        )
        if tag == "TOPUP_1FL":
            done_badge = (
                f"정량 {next_l1_target_q}주 완수!"
                if rem_after_fill == 0
                else f"잔여 {rem_after_fill}주 추가 대기"
            )
            title_str = (
                f"🎯 [SOXL 1층 미체결 잔량 보충 체결] +{q_int}주 @ ${fill_p:.2f} "
                f"(1층 {cur_l1_qty}/{next_l1_target_q}주 합산 · {done_badge})"
            )
            body_str = (
                f"실사용 ${actual_spent:,.2f} (자투리 +${saved_from_portion:.2f} 시드보존) · "
                f"2층 승격 없이 기존 1층 합산(단가 ${l1_book_now:.2f} · 익절목표 ${l1_target:.2f}){rem_quota_note} · "
                f"가용현금 ${free_cash_now:,.2f} (총 {new_held_shares}주)"
            )
        elif was_l2_only and tag == "REENTRY_1FL" and len(new_buckets) >= 2:
            title_str = (
                f"🔥 [SOXL 현재가 지정가 1층 재장전 체결] {q_int}주 @ ${fill_p:.2f} (상단 {u_cnt}개층 비병합)"
            )
            body_str = (
                f"실사용 ${actual_spent:,.2f} (자투리 +${saved_from_portion:.2f} 시드보존) · "
                f"🛡️60초 타임쉴드 후 1층목표 ${l1_target:.2f}(+1.5%) 감시{rem_quota_note} · "
                f"2~{new_held_tiers}층({u_qty}주) 이평 ${u_wma_p:.2f}(목표 ${u_wma_t:.2f}) 유지 · "
                f"기억저가 ${new_cycle_min_p:.2f}{ratchet_note}(와이드 {drop_req_p:.1f}% 추매가 ${trig_buy_p:.2f}) · "
                f"가용현금 ${free_cash_now:,.2f}"
            )
        elif is_step_up_unlock_fill:
            reb_m = (
                prev_l1_p / max(0.01, old_min_p)
                if (prev_l1_p > 0.0 and old_min_p > 0.0)
                else 2.0
            )
            title_str = (
                f"🔓 [SOXL 스텝업 저가 해금 추매 체결 ({new_held_lots}회차/{new_held_tiers}개층)] {q_int}주 @ ${fill_p:.2f}"
            )
            body_str = (
                f"구저가 ${old_min_p:.2f}(반등 {reb_m:.2f}x) ➔ 스텝업 잠금저가 ${new_cycle_min_p:.2f}(잠금 {new_ratchet_max_lots}회차) 갱신! · "
                f"실사용 ${actual_spent:,.2f} (자투리 +${saved_from_portion:.2f} 시드보존) · "
                f"🛡️60초 타임쉴드 후 1층목표 ${l1_target:.2f} & 2~{new_held_tiers}층({u_qty}주) 이평 ${u_wma_p:.2f}(목표 ${u_wma_t:.2f}) 감시{rem_quota_note} · "
                f"차기단차 {drop_req_p:.1f}%(${trig_buy_p:.2f}) · 가용현금 ${free_cash_now:,.2f}"
            )
        else:
            upper_note = ""
            if len(new_buckets) >= 2:
                upper_note = (
                    f" · 2~{new_held_tiers}층({u_cnt}개층·{u_qty}주) 순수이평 ${u_wma_p:.2f}(목표 ${u_wma_t:.2f})"
                )
            title_str = (
                f"🔵 [SOXL {new_held_lots}회차{ratchet_note}({new_held_tiers}개층) 현재가 지정가 매수 체결] {q_int}주 @ ${fill_p:.2f}"
            )
            body_str = (
                f"실사용 ${actual_spent:,.2f} (자투리 +${saved_from_portion:.2f} 시드보존) "
                f"· 🛡️60초 타임쉴드 후 1층목표 ${l1_target:.2f} 감시{upper_note}{rem_quota_note} · 차기단차 {drop_req_p:.1f}%(${trig_buy_p:.2f}) "
                f"· 가용현금 ${free_cash_now:,.2f} (총 {new_held_shares}주)"
            )
        await context.send_slim_alert(title=title_str, body=body_str)

    return {
        "status": "BUY_FILLED_AND_MERGED",
        "symbol": TARGET_SYMBOL,
        "lot_type": tag,
        "is_step_up_unlock": is_step_up_unlock_fill,
        "filled_qty": q_int,
        "ordered_qty": ord_q,
        "l1_target_quota_qty": next_l1_target_q,
        "l1_rem_quota_qty": rem_after_fill,
        "fill_price": fill_p,
        "actual_spent_usd": actual_spent,
        "saved_from_portion_usd": saved_from_portion,
        "cycle_min_buy_price": round(new_cycle_min_p, 4),
        "cycle_ratchet_max_lots": new_ratchet_max_lots,
        "held_lots": new_held_lots,
        "held_tiers": new_held_tiers,
        "held_shares": new_held_shares,
        "free_cash_usd": free_cash_now,
    }


async def sync_pending_buy_order_plugin(
    context: Any,
    holdings: Dict[str, Dict[str, Any]],
    prices: Dict[str, float],
    now_est: Optional[datetime] = None,
    force_settle: bool = False,
) -> Dict[str, Any]:
    """
    # MODIFIED [🎯 1 & 🎯 5 & Case 19, 24, 59, 60, 61, 65, 66, 71, 72, 73, 76, 77, 78, Case 84, Case 87 & Case 88]:
    장부에 대기 중인 미체결 매수 주문(buy_order_id : 본 그리드 / 서브 그리드)이 존재할 때 체결/부분체결/취소를 동기화한다.
    - 15:30 EST 경계 도래 시 미체결 안전 취소(should_abort_late_cutoff)는:
      ① 본 그리드 및 서브 그리드 0주 새 사이클 첫 1층 진입 주문(is_zero_grid_reentry / is_zero_sub_reentry) 및
      ② 본 그리드 및 서브 그리드 상단층 보유 · 1층 공석 상태에서 직전 익절가 대비 +1.00% 이상 상승돌파로 발주된 주문(is_vacant_l1_breakout_reentry / is_sub_vacant_l1_breakout_reentry)에 동시 적용하며,
      1층 공석 눌림목(-1.00%) 주문, 10분 게이트 신저가 추매(DIP_1FL / SUB_DIP_1FL), 1층 잔량 보충(TOPUP_1FL / SUB_TOPUP_1FL) 주문은 취소하지 않고 정상 체결을 대기한다!
    """
    st = context.ledger.get_state(TARGET_SYMBOL)
    buy_oid = str(st.get("buy_order_id") or "").strip()
    if not buy_oid:
        return {"status": "NO_PENDING_BUY"}

    dt_now = now_est.astimezone(EST_TZ) if now_est else datetime.now(EST_TZ)
    hm_now = dt_now.hour * 100 + dt_now.minute
    is_late_cutoff_now = is_late_regular_new_cycle_cutoff_window(
        hm_now, now_est=dt_now
    )

    ordered_qty = max(1, safe_int(st.get("ordered_qty"), 1))
    ord_price = safe_float(st.get("buy_price"), 0.0)
    portion_budget = safe_float(
        st.get("pending_portion_budget"), float(ordered_qty) * ord_price
    )
    raw_lot_type = (
        str(st.get("pending_lot_type") or "QUOTA_L1").upper().strip()
    )
    is_sub_lot = raw_lot_type.startswith("SUB_")
    if raw_lot_type in ("REENTRY_1FL_BREAKOUT", "REENTRY_1FL_PULLBACK"):
        lot_type = "REENTRY_1FL"
    elif raw_lot_type in (
        "SUB_REENTRY_1FL_BREAKOUT",
        "SUB_REENTRY_1FL_PULLBACK",
    ):
        lot_type = "SUB_REENTRY_1FL"
    else:
        lot_type = raw_lot_type

    buckets_now = buckets_from_dicts(st.get("buckets", []))
    has_active_l1_now = has_active_l1_bucket(buckets_now)
    is_vacant_l1_now = bool(len(buckets_now) > 0 and not has_active_l1_now)
    cur_target_q = max(0, safe_int(st.get("l1_target_quota_qty"), 0))
    fallback_target_q_on_zero_cancel = (
        max(buckets_now[0].qty, cur_target_q)
        if ((lot_type == "TOPUP_1FL" or is_sub_lot) and has_active_l1_now)
        else (buckets_now[0].qty if has_active_l1_now else 0)
    )

    sub_buckets_now = buckets_from_dicts(st.get("sub_buckets", []))
    has_sub_active_l1_now = has_active_l1_bucket(sub_buckets_now)
    is_sub_vacant_l1_now = bool(
        len(sub_buckets_now) > 0 and not has_sub_active_l1_now
    )
    cur_sub_target_q = max(0, safe_int(st.get("sub_l1_target_quota_qty"), 0))
    fallback_sub_target_q_on_zero_cancel = (
        max(sub_buckets_now[0].qty, cur_sub_target_q)
        if (
            (lot_type == "SUB_TOPUP_1FL" or not is_sub_lot)
            and has_sub_active_l1_now
        )
        else (sub_buckets_now[0].qty if has_sub_active_l1_now else 0)
    )

    # [Case 84 & Case 88]: 15:30 EST 도래 시 미체결 본·서브 0주 신규 진입 주문 및 1층 공석 +1.0% 돌파 추격 주문을 즉시 안전 취소!
    is_zero_grid_reentry = bool(
        not is_sub_lot and len(buckets_now) == 0 and lot_type == "REENTRY_1FL"
    )
    anchor_p_now = safe_float(st.get("anchor_price"), 0.0)
    is_vacant_l1_breakout_reentry = bool(
        not is_sub_lot
        and is_vacant_l1_now
        and lot_type == "REENTRY_1FL"
        and (
            raw_lot_type == "REENTRY_1FL_BREAKOUT"
            or (
                anchor_p_now > 0.0
                and ord_price
                >= anchor_p_now
                * (1.0 + REENTRY_BREAKOUT_RISE_PCT / 100.0 - 1e-4)
            )
        )
    )

    is_zero_sub_reentry = bool(
        is_sub_lot
        and len(sub_buckets_now) == 0
        and lot_type == "SUB_REENTRY_1FL"
    )
    sub_anchor_p_now = safe_float(st.get("sub_anchor_price"), 0.0)
    is_sub_vacant_l1_breakout_reentry = bool(
        is_sub_lot
        and is_sub_vacant_l1_now
        and lot_type == "SUB_REENTRY_1FL"
        and (
            raw_lot_type == "SUB_REENTRY_1FL_BREAKOUT"
            or (
                sub_anchor_p_now > 0.0
                and ord_price
                >= sub_anchor_p_now
                * (1.0 + REENTRY_BREAKOUT_RISE_PCT / 100.0 - 1e-4)
            )
        )
    )

    should_abort_late_cutoff = bool(
        is_late_cutoff_now
        and (
            is_zero_grid_reentry
            or is_vacant_l1_breakout_reentry
            or is_zero_sub_reentry
            or is_sub_vacant_l1_breakout_reentry
        )
    )

    now_mono = time.monotonic()
    last_mod = safe_float(st.get("last_modify_mono"), 0.0)
    if last_mod <= 0.0 or last_mod > now_mono:
        last_mod = now_mono
        await context.ledger.update_state(
            TARGET_SYMBOL, last_modify_mono=last_mod
        )
    elapsed_mod = max(0.0, now_mono - last_mod)

    detail = await context.api.get_order_detail(buy_oid)
    if isinstance(detail, dict):
        ord_status = str(detail.get("status") or "").upper().strip()
        exec_obj = (
            detail.get("execution")
            if isinstance(detail.get("execution"), dict)
            else {}
        )
        filled_q = safe_int(exec_obj.get("filledQuantity"), 0)
        avg_fill_p = safe_float(exec_obj.get("averageFilledPrice"), 0.0)

        if ord_status == "FILLED" or (
            filled_q > 0 and ord_status in ("CANCELED", "REJECTED", "REPLACED")
        ):
            eff_q = filled_q if filled_q > 0 else ordered_qty
            eff_p = avg_fill_p if avg_fill_p > 0.0 else ord_price
            return await _commit_filled_buy_to_stratum_ledger(
                context=context,
                filled_qty=eff_q,
                avg_fill_price=eff_p,
                portion_budget=portion_budget,
                lot_type=lot_type,
                settled_order_id=buy_oid,
                ordered_qty=ordered_qty,
            )

        if (
            ord_status in ("PARTIAL_FILLED", "PENDING_CANCEL")
            or filled_q > 0
        ):
            if (
                elapsed_mod >= BUY_ORDER_MAX_WAIT_SEC
                or force_settle
                or should_abort_late_cutoff
                or ord_status == "PENDING_CANCEL"
            ):
                try:
                    await context.api.cancel_order(buy_oid)
                except Exception:
                    pass
                final_det = await context.api.get_order_detail(buy_oid)
                if isinstance(final_det, dict):
                    f_ex = (
                        final_det.get("execution")
                        if isinstance(final_det.get("execution"), dict)
                        else {}
                    )
                    f_q2 = safe_int(f_ex.get("filledQuantity"), filled_q)
                    f_p2 = safe_float(
                        f_ex.get("averageFilledPrice"), avg_fill_p
                    )
                    if f_q2 > 0:
                        filled_q = f_q2
                    if f_p2 > 0.0:
                        avg_fill_p = f_p2
                if filled_q > 0:
                    eff_p = avg_fill_p if avg_fill_p > 0.0 else ord_price
                    return await _commit_filled_buy_to_stratum_ledger(
                        context=context,
                        filled_qty=filled_q,
                        avg_fill_price=eff_p,
                        portion_budget=portion_budget,
                        lot_type=lot_type,
                        settled_order_id=buy_oid,
                        ordered_qty=ordered_qty,
                    )
            else:
                return {
                    "status": "BUY_PARTIAL_FILLED_WAITING",
                    "filled_qty": filled_q,
                    "ordered_qty": ordered_qty,
                }

        if ord_status in ("CANCELED", "REJECTED") and filled_q == 0:
            re_epoch = (
                mark_reentry_monitor_60s_cycle_shield(
                    context=context, symbol=TARGET_SYMBOL, eval_price=ord_price
                )
                if (is_vacant_l1_now and not is_sub_lot)
                else safe_float(st.get("last_reentry_eval_ts"), 0.0)
            )
            sub_re_epoch = (
                mark_sub_reentry_monitor_60s_cycle_shield(
                    context=context, symbol=TARGET_SYMBOL, eval_price=ord_price
                )
                if (is_sub_vacant_l1_now and is_sub_lot)
                else safe_float(st.get("last_sub_reentry_eval_ts"), 0.0)
            )
            clear_kw: Dict[str, Any] = {
                "l1_target_quota_qty": fallback_target_q_on_zero_cancel,
                "sub_l1_target_quota_qty": fallback_sub_target_q_on_zero_cancel,
                "buy_order_id": "",
                "ordered_qty": 0,
                "buy_price": 0.0,
                "pending_portion_budget": 0.0,
                "pending_lot_type": "",
                "pending_step_up_min_price": 0.0,
                "pending_sub_step_up_min_price": 0.0,
                "last_reentry_eval_ts": re_epoch,
                "last_sub_reentry_eval_ts": sub_re_epoch,
            }
            await context.ledger.update_state(TARGET_SYMBOL, **clear_kw)
            return {"status": f"BUY_ORDER_{ord_status}_CLEARED"}

    if (
        elapsed_mod >= BUY_ORDER_MAX_WAIT_SEC
        or force_settle
        or should_abort_late_cutoff
    ):
        try:
            await context.api.cancel_order(buy_oid)
        except Exception:
            pass

        final_detail = await context.api.get_order_detail(buy_oid)
        if isinstance(final_detail, dict):
            f_status = str(final_detail.get("status") or "").upper().strip()
            f_exec = (
                final_detail.get("execution")
                if isinstance(final_detail.get("execution"), dict)
                else {}
            )
            f_qty = safe_int(f_exec.get("filledQuantity"), 0)
            f_avg = safe_float(f_exec.get("averageFilledPrice"), 0.0)
            if f_status == "FILLED" or f_qty > 0:
                return await _commit_filled_buy_to_stratum_ledger(
                    context=context,
                    filled_qty=(f_qty if f_qty > 0 else ordered_qty),
                    avg_fill_price=(f_avg if f_avg > 0.0 else ord_price),
                    portion_budget=portion_budget,
                    lot_type=lot_type,
                    settled_order_id=buy_oid,
                    ordered_qty=ordered_qty,
                )

        re_epoch = (
            mark_reentry_monitor_60s_cycle_shield(
                context=context, symbol=TARGET_SYMBOL, eval_price=ord_price
            )
            if (is_vacant_l1_now and not is_sub_lot)
            else safe_float(st.get("last_reentry_eval_ts"), 0.0)
        )
        sub_re_epoch = (
            mark_sub_reentry_monitor_60s_cycle_shield(
                context=context, symbol=TARGET_SYMBOL, eval_price=ord_price
            )
            if (is_sub_vacant_l1_now and is_sub_lot)
            else safe_float(st.get("last_sub_reentry_eval_ts"), 0.0)
        )
        timeout_kw: Dict[str, Any] = {
            "l1_target_quota_qty": fallback_target_q_on_zero_cancel,
            "sub_l1_target_quota_qty": fallback_sub_target_q_on_zero_cancel,
            "buy_order_id": "",
            "ordered_qty": 0,
            "buy_price": 0.0,
            "pending_portion_budget": 0.0,
            "pending_lot_type": "",
            "pending_step_up_min_price": 0.0,
            "pending_sub_step_up_min_price": 0.0,
            "last_reentry_eval_ts": re_epoch,
            "last_sub_reentry_eval_ts": sub_re_epoch,
        }
        await context.ledger.update_state(TARGET_SYMBOL, **timeout_kw)
        if should_abort_late_cutoff:
            abort_desc = (
                "서브 0주 신규 진입"
                if is_zero_sub_reentry
                else (
                    "서브 1층 공석 돌파 추격"
                    if is_sub_vacant_l1_breakout_reentry
                    else (
                        "0주 신규 진입"
                        if is_zero_grid_reentry
                        else "1층 공석 돌파 추격"
                    )
                )
            )
            logger.info(
                "🛡️ [Case 84/88 장마감 30분전(15:30 EST) 도래 -> 미체결 %s(%s) 즉시 안전 취소] 지정가 $%.2f 취소 ➔ 컷오프 방어 전환",
                abort_desc,
                raw_lot_type,
                ord_price,
            )
            return {
                "status": "BUY_ORDER_LATE_CUTOFF_CANCELED_SAFE",
                "abort_type": abort_desc,
            }
        logger.info(
            "⏳ [SOXL 현재가 지정가 매수(%s) 60초 미체결 안전 취소] 지정가 $%.2f 유지 종료 ➔ 관망 복귀",
            lot_type,
            ord_price,
        )
        return {"status": "BUY_ORDER_UNFILLED_CANCELED_SAFE"}

    return {"status": "BUY_ORDER_PENDING", "orderId": buy_oid}


# 하위 호환 별칭
sync_dynamic_vwap_buy_order_modify = sync_pending_buy_order_plugin


# ======================================================================
# [4bot 단일파일 병합] 아래는 원작 sniper_plugin.py (Part 2/2) — 원작 sniper_plugin_core.py (Part 1/2) 위에 이어 붙임
# ======================================================================
# -*- coding: utf-8 -*-
"""
# MODIFIED: sniper_plugin.py (황금시간 07:00~07:50 RSI<=19 올인 분기 G · 골든포켓 참조 · 임포트 전면 영구 소각 & Case 91 무제한 예비수혈 및 인출형[단리]/자산증식형[복리] 매수 정량 연동)
인피니트 스노우볼 (Infinite Snowball) v3.0 — 스나이퍼 매수 코어 Part 2 / 2 (Step 07 / 13)
역할:
1) sniper_plugin_core.py (Part 1 / 2) 의 모든 상수·타임쉴드·GUARD30 무제한 예비수혈·체결커밋·미체결 동기화 심볼 명시적 재익스포트(Facade Re-export)로
   타 모듈(defense_plugin.py, tg_ui_plugin.py, main_runtime.py, main.py, plugin_updater.py) AST 임포트 호환성 100% 보장
2) 🛡️ [Case 88 & Case 91 : 13_SUB_L1L3_RESV05_CAP4L] 스위치 없는 100% 기본 상시 적용(Default ON) 3층 서브 그리드 매수 엔진(_execute_sub_grid_buy_engine_plugin):
   - 본 그리드 1개 층 이상 보유 중(len(buckets) > 0) 본 그리드 5영업일 이상 연속 무매매(main_consec_frozen_days >= 5) 도달 시 또는 서브 그리드 기가동 중(len(sub_buckets) > 0) 상시 작동
   - 자산증식형(복리 · COMP_08PCT) / 인출형(단리 · SIMPLE_08PCT) 운용 모드에 연동된 본 그리드 0.5회분(4.0%) 보호예수금(reserved_for_main_usd) 차감 가용 유휴 현금(avail_idle_cash_usd) 및 서브 최대 누적 4회분(16.0%) 상한 캡(SUB_MAX_TOTAL_LOTS_4 = 4) 엄격 적용
   - 분기 S-A (서브 0주 첫 진입 SUB_REENTRY_1FL : 15:30 ~ 16:00 EST 차단 Case 84 & 유휴현금 부족 시 60초 쉴드 & 뮤텍스 2차 타임쉴드 검문) ·
     분기 S-B1 (서브 1층 공석 60초 주기 눌림/돌파 재장전 SUB_REENTRY_1FL : 서브 2층 단가 상한 가드 Case 73 & 15:30 ~ 16:00 EST 돌파 차단 Case 84 & 뮤텍스 2차 타임쉴드 검문) ·
     분기 S-B0 (서브 1층 부분체결 잔량 SUB_TOPUP_1FL 1.5초 모니터 재대기 Case 78 & 유휴현금 부족 시 60초 쉴드 & 뮤텍스 2차 타임쉴드 검문) ·
     분기 S-B2 (서브 활성 1층 보유 중 10분 게이트 : 서브 최고도달회차 4단 와이드 신저가 OR 서브 10영업일 무매매 & -10.0% 저가해금 SUB_UNLOCK_10D_D10 추매 SUB_DIP_1FL & 유휴현금 부족 시 해당 10분 버킷 즉시 소모 처리로 무한 API 폴링 차단)
3) 04:07 ~ 16:00 EST 비대칭 매수 타격 게이트 실행기 (execute_seed_protected_buy_gate_plugin):
   - 🛡️ [분기 A · Case 65, 67, 77, 84, 91] : 본 그리드 0주 상태(is_zero_shares)에서 0주 종료 후 60.0초 타임쉴드 경과 뒤 현재가 지정가 첫 1층(REENTRY_1FL) 산입하되,
     정규장 마감 30분 전(15:30 ~ 16:00 EST, is_late_regular_new_cycle_cutoff_window) 구간에서는 0주 새 사이클 첫 1층 진입을 100% 원천 차단(HOLD_LATE_SESSION_NEW_CYCLE_CUTOFF)!
   - 🔥 [분기 B-1 · Case 67, 73, 77, 84, 88, 91] : 본 그리드 상단 2층 ~ 7층(GRID_L2 ~ GRID_L7) 보유 중 1층 공석 시 매 60.0초 주기 재장전 모니터
     (본 그리드 패스/대기 시 즉시 Default-ON 3층 서브 그리드 엔진으로 제어권 인계)
   - 🎯 [분기 B-0 · Case 78, 88] : 본 그리드 활성 1층 지정가 부분 체결 미체결 잔량(TOPUP_1FL) 1.5초 모니터 (원장 가용현금 1주 비용 선행 가드 및 부족 시 60초 쿨다운 쉴드 적용)
   - 🔵 [분기 B-2 · Case 60, 72, 76, 77, 87, 88, 91] : 본 그리드 활성 1층 보유 중 10분 고정 매수 게이트(4단 와이드 신저가 OR STEP2X_15PCT_C20 스텝업 해금) 및
     본 그리드 대기/패스 틱에서 Default-ON 3층 서브 그리드 매수 엔진 연속 가동
- 제1헌법 ~ 제6헌법 및 Case 01 ~ 91 완벽 준수
"""

# [4bot 단일파일 병합] 원작 분할 임포트 제거: sniper_plugin_core

import asyncio
import logging
import math
import time
from datetime import datetime
from typing import Any, Dict, Optional

from quant_engine import (
    DEFAULT_GRID_MERGE_MODE,
    MAX_RESERVE_PORTIONS,
    MIN_DIP_BUDGET_RATIO,
    MIN_DIP_VS_L1_RATIO,
    PORTION_MODE_COMPOUND,
    PORTION_MODE_SIMPLE,
    PORTION_RATIO_LOCKED,
    ROUND_TRIP_FEE_RATE_PCT,
    SUB_FROZEN_DAYS_TRIGGER,
    SUB_GRID_DEFAULT_ENABLED,
    SUB_MAX_TIERS_3,
    SUB_MAX_TOTAL_LOTS_4,
    SUB_MERGE_MODE_L1_L3,
    SUB_PORTION_RATIO_4PCT,
    SUB_RESERVE_MAIN_PORTIONS,
    SUB_UNLOCK_DROP_FROM_L1_PCT,
    SUB_UNLOCK_FROZEN_DAYS_10,
    buckets_from_dicts,
    compute_golden8_quota_qty,
    compute_sub4_quota_qty,
    compute_sub_grid_available_idle_cash,
    compute_sub_upper_2_to_3_moving_avg,
    compute_upper_2_to_7_moving_avg,
    evaluate_l2_only_hybrid_reentry_signal,
    evaluate_step_up_2x_dip_signal,
    evaluate_sub_grid_dip_signal,
    get_golden8_prog_thresholds,
    has_active_l1_bucket,
    is_simple_income_mode,
    resolve_affordable_buy_qty,
    resolve_effective_round_trip_fee_rate_pct,
    resolve_portion_budget_base_equity,
)
from quant_indicators_plugin import (
    NEW_CYCLE_BUY_CUTOFF_HM,
    evaluate_buy_gate_bucket_status,
    is_active_buy_window,
    is_late_regular_new_cycle_cutoff_window,
    refresh_metrics_with_live_tick,
)
from sniper_exit_plugin import (
    POST_BUY_TO_SELL_SHIELD_SEC,
    POST_SELL_TO_BUY_SHIELD_SEC,
    is_within_post_buy_time_shield,
    is_within_post_sell_time_shield,
)
# [4bot 단일파일 병합] 원작 분할 임포트 제거: sniper_plugin_core
from toss_api import (
    DEFAULT_INITIAL_SEED_USD,
    EST_TZ,
    LOCKED_BUY_INTERVAL_MIN,
    TARGET_SYMBOL,
    generate_client_order_id,
    safe_float,
    safe_int,
)

logger = logging.getLogger("toss_sniper.sniper_plugin")


# ---------------------------------------------------------------------------
# [핵심 1 · Case 88 & Case 91] 스위치 없는 100% 기본 상시 적용(Default ON) 3층 서브 그리드 매수 엔진 (_execute_sub_grid_buy_engine_plugin)
# ---------------------------------------------------------------------------
async def _execute_sub_grid_buy_engine_plugin(
    context: Any,
    holdings: Dict[str, Dict[str, Any]],
    prices: Dict[str, float],
    dt_now: datetime,
    live_p: float,
) -> Optional[Dict[str, Any]]:
    """
    # MODIFIED [Case 88 & Case 91 : 🛡️ 13_SUB_L1L3_RESV05_CAP4L — Default-ON 3층 서브 그리드 매수 엔진 (자산증식형[복리] ⇄ 인출형[단리] 연동 & 유휴현금 부족 시 10분 버킷 즉시 소모 & 60초 쉴드 & 뮤텍스 2차 타임쉴드 검문 강화)]:
    본 그리드가 대기/패스한 틱에서 호출되어:
    1) 본 그리드가 최소 1개 층 이상 보유 중(len(buckets) > 0)이고,
       본 그리드 연속 무매매일(main_consec_frozen_days >= 5)이 5영업일 이상이거나 이미 서브 그리드가 가동 중(len(sub_buckets) > 0)일 때 작동한다.
    2) 운용 모드(portion_mode : COMP_08PCT 복리 vs SIMPLE_08PCT 단리)에 따라 산출된 본 그리드 보호예수금 0.5회분(reserved_for_main_usd, 기준자산의 4.0%)을 차감한
       순수 유휴 현금(avail_idle_cash_usd) 범위 내에서만 매수하며, 온디맨드 예비시드 차입이나 시드고갈 알림을 절대 발동하지 않는다.
    3) 서브 누적 합병 회차가 최대 상한 4회분(SUB_MAX_TOTAL_LOTS_4 = 4, 기준자산의 16.0%)에 도달하면
       미체결 잔량 보충(SUB_TOPUP_1FL) 외의 모든 신규/추가 서브 매수를 차단(HOLD_SUB_CAP_4_LOTS_REACHED)하여 본 그리드 탄약을 보전한다.
    4) 서브 10분 게이트(S-B2)에서 유휴현금 부족 시 해당 10분 버킷(sub_last_evaluated_buy_bucket_id)을 즉시 소모 처리하고,
       서브 0주(S-A) 및 서브 잔량 보충(S-B0)에서 유휴현금 부족 시 60.0초 쿨다운 쉴드를 각인하여 불필요한 반복 API 호출을 원천 차단한다.
    """
    st = context.ledger.get_state(TARGET_SYMBOL)
    if str(st.get("buy_order_id") or "").strip() or str(
        st.get("sell_order_id") or ""
    ).strip():
        return None

    buckets = buckets_from_dicts(st.get("buckets", []))
    if not buckets:
        return None

    sub_buckets = buckets_from_dicts(st.get("sub_buckets", []))
    main_frozen_d = max(0, safe_int(st.get("main_consec_frozen_days"), 0))
    if main_frozen_d < SUB_FROZEN_DAYS_TRIGGER and len(sub_buckets) == 0:
        return None

    hm = dt_now.hour * 100 + dt_now.minute
    if not is_active_buy_window(hm, now_est=dt_now):
        return None

    in_sell_sh, _ = is_within_post_sell_time_shield(context, st, TARGET_SYMBOL)
    in_buy_sh, _ = is_within_post_buy_time_shield(context, st, TARGET_SYMBOL)
    if in_sell_sh or in_buy_sh:
        return None

    eff_rt_pct = resolve_effective_round_trip_fee_rate_pct(state_dict=st)
    fee_mult = 1.0 + (eff_rt_pct / 100.0)

    init_seed = max(
        100.0, safe_float(st.get("initial_seed_usd"), DEFAULT_INITIAL_SEED_USD)
    )
    free_cash = max(0.0, safe_float(st.get("free_cash_usd"), 0.0))
    inj_res_usd = max(0.0, safe_float(st.get("injected_reserve_usd"), 0.0))
    actual_inv_total = sum(b.actual_cost_usd for b in buckets) + sum(
        sb.actual_cost_usd for sb in sub_buckets
    )
    core_equity = max(init_seed, (free_cash + actual_inv_total) - inj_res_usd)
    portion_mode = (
        str(st.get("portion_mode") or PORTION_MODE_COMPOUND).upper().strip()
    )

    idle_info = compute_sub_grid_available_idle_cash(
        free_cash_usd=free_cash,
        core_equity_usd=core_equity,
        broker_buying_power_usd=None,
        reserve_main_portions=SUB_RESERVE_MAIN_PORTIONS,
        initial_seed_usd=init_seed,
        portion_mode=portion_mode,
    )
    avail_idle_ledger = safe_float(idle_info.get("avail_idle_cash_usd"), 0.0)
    sub_portion_budget = safe_float(
        idle_info.get("sub_portion_budget"), round(core_equity * 0.04, 4)
    )

    sub_cur_total_lots = sum(max(1, sb.lot_count) for sb in sub_buckets)
    sub_max_lots_cap = max(
        1, safe_int(st.get("sub_max_total_lots"), SUB_MAX_TOTAL_LOTS_4)
    )
    has_sub_active_l1 = has_active_l1_bucket(sub_buckets)
    is_sub_l2_only = bool(len(sub_buckets) > 0 and not has_sub_active_l1)

    # -----------------------------------------------------------------------
    # [서브 분기 S-A : 서브 그리드 0주 첫 진입 (len(sub_buckets) == 0 and main_consec_frozen_days >= 5)]
    # -> 15:30 ~ 16:00 EST 구간에서는 서브 0주 새 사이클 첫 1층 진입 차단 (Case 84 & Case 88)
    # -----------------------------------------------------------------------
    if len(sub_buckets) == 0:
        if is_late_regular_new_cycle_cutoff_window(hm, now_est=dt_now):
            return {
                "status": "HOLD_SUB_LATE_SESSION_NEW_CYCLE_CUTOFF",
                "hm": hm,
                "cutoff_hm": NEW_CYCLE_BUY_CUTOFF_HM,
            }

        in_sub_re_sh, rem_sub_re = is_within_sub_reentry_monitor_time_shield(
            context, st, TARGET_SYMBOL
        )
        if in_sub_re_sh:
            return {
                "status": "HOLD_SUB_POST_SELL_60S_SHIELD",
                "remain_shield_sec": rem_sub_re,
            }

        min_req_sub_0sh = max(
            live_p * fee_mult, sub_portion_budget * MIN_DIP_BUDGET_RATIO
        )
        if avail_idle_ledger < min_req_sub_0sh:
            mark_sub_reentry_monitor_60s_cycle_shield(
                context=context,
                symbol=TARGET_SYMBOL,
                eval_price=live_p,
            )
            return {
                "status": "HOLD_SUB_INSUFFICIENT_IDLE_CASH",
                "avail_idle_cash_usd": avail_idle_ledger,
                "min_req_cash_usd": round(min_req_sub_0sh, 4),
            }

        async with context.in_memory_ordering_lock:
            async with context.dual_strike_mutex:
                st_now = context.ledger.get_state(TARGET_SYMBOL)
                if str(st_now.get("buy_order_id") or "").strip() or str(
                    st_now.get("sell_order_id") or ""
                ).strip():
                    return {"status": "ALREADY_ORDERING_IN_MUTEX"}

                in_s_sh, _ = is_within_post_sell_time_shield(
                    context, st_now, TARGET_SYMBOL
                )
                in_b_sh, _ = is_within_post_buy_time_shield(
                    context, st_now, TARGET_SYMBOL
                )
                in_sub_re_m, _ = is_within_sub_reentry_monitor_time_shield(
                    context, st_now, TARGET_SYMBOL
                )
                if in_s_sh or in_b_sh or in_sub_re_m:
                    return {"status": "HOLD_60S_TIME_SHIELD_IN_MUTEX"}

                now_buckets = buckets_from_dicts(st_now.get("buckets", []))
                now_sub_buckets = buckets_from_dicts(
                    st_now.get("sub_buckets", [])
                )
                now_main_frozen = max(
                    0, safe_int(st_now.get("main_consec_frozen_days"), 0)
                )
                if (
                    not now_buckets
                    or len(now_sub_buckets) > 0
                    or now_main_frozen < SUB_FROZEN_DAYS_TRIGGER
                ):
                    return {"status": "SUB_STATE_CHANGED_IN_MUTEX"}

                dt_mutex = datetime.now(EST_TZ)
                hm_mutex = dt_mutex.hour * 100 + dt_mutex.minute
                if is_late_regular_new_cycle_cutoff_window(
                    hm_mutex, now_est=dt_mutex
                ):
                    return {
                        "status": "HOLD_SUB_LATE_SESSION_NEW_CYCLE_CUTOFF",
                        "hm": hm_mutex,
                    }

                fresh_live_p = await _fetch_fresh_current_soxl_price(
                    context, fallback_price=live_p
                )
                if fresh_live_p <= 0.0:
                    return {"status": "NO_FRESH_LIVE_PRICE"}

                exec_order_p = max(
                    0.01, math.floor((fresh_live_p + 1e-9) * 100.0) / 100.0
                )
                eff_rt_pct_m = resolve_effective_round_trip_fee_rate_pct(
                    state_dict=st_now
                )
                fee_mult_m = 1.0 + (eff_rt_pct_m / 100.0)
                now_free_cash = max(
                    0.0, safe_float(st_now.get("free_cash_usd"), 0.0)
                )
                now_init_seed = max(
                    100.0,
                    safe_float(
                        st_now.get("initial_seed_usd"),
                        DEFAULT_INITIAL_SEED_USD,
                    ),
                )
                now_inj_res = max(
                    0.0, safe_float(st_now.get("injected_reserve_usd"), 0.0)
                )
                now_inv_tot = sum(b.actual_cost_usd for b in now_buckets)
                now_core_eq = max(
                    now_init_seed, (now_free_cash + now_inv_tot) - now_inj_res
                )
                now_p_mode = (
                    str(st_now.get("portion_mode") or PORTION_MODE_COMPOUND)
                    .upper()
                    .strip()
                )

                raw_bp_sub = await context.api.get_buying_power_usd(
                    safety_buffer_pct=0.2
                )
                if raw_bp_sub <= 0.0 and now_free_cash >= (
                    exec_order_p * fee_mult_m
                ):
                    await asyncio.sleep(0.25)
                    raw_bp_sub = await context.api.get_buying_power_usd(
                        safety_buffer_pct=0.2
                    )

                idle_m = compute_sub_grid_available_idle_cash(
                    free_cash_usd=now_free_cash,
                    core_equity_usd=now_core_eq,
                    broker_buying_power_usd=(
                        raw_bp_sub if raw_bp_sub > 0.0 else 0.0
                    ),
                    reserve_main_portions=SUB_RESERVE_MAIN_PORTIONS,
                    initial_seed_usd=now_init_seed,
                    portion_mode=now_p_mode,
                )
                avail_idle_m = safe_float(
                    idle_m.get("avail_idle_cash_usd"), 0.0
                )
                prev_sub_anc = safe_float(st_now.get("sub_anchor_price"), 0.0)
                ref_sub_anc = (
                    prev_sub_anc if prev_sub_anc > 0.0 else exec_order_p
                )
                sub_target_qty, sub_p_bud = compute_sub4_quota_qty(
                    sub_anchor_price=ref_sub_anc,
                    current_core_equity=now_core_eq,
                    initial_seed_usd=now_init_seed,
                    exec_price=exec_order_p,
                    portion_mode=now_p_mode,
                )
                min_req_sub_m = max(
                    exec_order_p * fee_mult_m,
                    sub_p_bud * MIN_DIP_BUDGET_RATIO,
                )
                if avail_idle_m < min_req_sub_m:
                    mark_sub_reentry_monitor_60s_cycle_shield(
                        context=context,
                        symbol=TARGET_SYMBOL,
                        eval_price=exec_order_p,
                    )
                    return {
                        "status": "HOLD_SUB_INSUFFICIENT_IDLE_CASH_IN_MUTEX",
                        "avail_idle_cash_usd": avail_idle_m,
                    }

                buy_qty_sub, _ = resolve_affordable_buy_qty(
                    target_qty=sub_target_qty,
                    price_t=exec_order_p,
                    free_cash_usd=avail_idle_m,
                    broker_buying_power_usd=avail_idle_m,
                    max_portion_budget_usd=sub_p_bud,
                    round_trip_fee_rate_pct=eff_rt_pct_m,
                )
                if buy_qty_sub <= 0:
                    mark_sub_reentry_monitor_60s_cycle_shield(
                        context=context,
                        symbol=TARGET_SYMBOL,
                        eval_price=exec_order_p,
                    )
                    return {"status": "INSUFFICIENT_IDLE_CASH_FOR_SUB_0SH"}

                _, sub_cur_bucket_id, sub_today_str, _ = (
                    evaluate_buy_gate_bucket_status(
                        now_est=dt_now,
                        buy_interval_min=LOCKED_BUY_INTERVAL_MIN,
                        last_evaluated_bucket_id=safe_int(
                            st_now.get("sub_last_evaluated_buy_bucket_id"), -1
                        ),
                        last_evaluated_date=str(
                            st_now.get("sub_last_evaluated_date") or ""
                        ),
                    )
                )
                cid = generate_client_order_id(prefix="SUB1FL")
                try:
                    ord_res = await context.api.create_order(
                        symbol=TARGET_SYMBOL,
                        side="BUY",
                        quantity=buy_qty_sub,
                        price=exec_order_p,
                        order_type="LIMIT",
                        time_in_force="DAY",
                        client_order_id=cid,
                        enforce_daymarket_block=True,
                    )
                except Exception as exc:
                    mark_sub_reentry_monitor_60s_cycle_shield(
                        context=context,
                        symbol=TARGET_SYMBOL,
                        eval_price=exec_order_p,
                    )
                    logger.warning(
                        "Case 88 서브그리드 0주 첫 1층(SUB_REENTRY_1FL) 주문 예외: %s",
                        exc,
                    )
                    return {"status": "SUB_ORDER_ERROR", "error": str(exc)}

                oid = str(ord_res.get("orderId") or "").strip()
                await context.ledger.update_state(
                    TARGET_SYMBOL,
                    sub_l1_target_quota_qty=buy_qty_sub,
                    buy_order_id=oid,
                    client_order_id=cid,
                    ordered_qty=buy_qty_sub,
                    buy_price=exec_order_p,
                    pending_portion_budget=sub_p_bud,
                    pending_lot_type="SUB_REENTRY_1FL",
                    pending_step_up_min_price=0.0,
                    pending_sub_step_up_min_price=0.0,
                    sub_last_evaluated_buy_bucket_id=sub_cur_bucket_id,
                    sub_last_evaluated_date=sub_today_str,
                    last_modify_mono=time.monotonic(),
                    last_sub_reentry_eval_ts=0.0,
                )
                context.wakeup_event.set()
                logger.info(
                    "🛡️ [Case 88 SOXL 본그리드 %d일 무매매 동결 -> 3층 서브그리드 첫 1층(SUB_REENTRY_1FL) 발주] %d주 @ 지정가 $%.2f (4%%예산 $%.2f · 유휴현금 $%.2f · orderId=%s)",
                    now_main_frozen,
                    buy_qty_sub,
                    exec_order_p,
                    sub_p_bud,
                    avail_idle_m,
                    oid,
                )
                return {
                    "status": "SUB_ZERO_SHARES_1FL_ORDERED",
                    "orderId": oid,
                    "qty": buy_qty_sub,
                    "price": exec_order_p,
                    "main_consec_frozen_days": now_main_frozen,
                }

    # -----------------------------------------------------------------------
    # [서브 분기 S-B1 : 서브 상단(2~3층)만 보유 중 (서브 1층 공석, is_sub_l2_only == True)]
    # -> 서브 누적 4회분 미만 & 매 60.0초 주기 & 서브 2층 단가 상한(Case 73) & 15:30 돌파 차단(Case 84)
    # -----------------------------------------------------------------------
    if is_sub_l2_only:
        if sub_cur_total_lots >= sub_max_lots_cap:
            return {
                "status": "HOLD_SUB_CAP_4_LOTS_REACHED",
                "sub_cur_total_lots": sub_cur_total_lots,
                "sub_max_total_lots": sub_max_lots_cap,
            }

        in_sub_re_sh, rem_sub_re = is_within_sub_reentry_monitor_time_shield(
            context, st, TARGET_SYMBOL
        )
        if in_sub_re_sh:
            return {
                "status": "HOLD_SUB_REENTRY_60S_TIME_SHIELD",
                "remain_shield_sec": rem_sub_re,
            }

        fresh_live_p = await _fetch_fresh_current_soxl_price(
            context, fallback_price=live_p
        )
        if fresh_live_p <= 0.0:
            return {"status": "NO_FRESH_LIVE_PRICE"}

        sub_min_upper_p = min(sb.book_price for sb in sub_buckets)
        sub_anchor_p = safe_float(
            st.get("sub_anchor_price"), sub_min_upper_p
        )
        is_late_cutoff = is_late_regular_new_cycle_cutoff_window(
            hm, now_est=dt_now
        )

        sub_re_sig = evaluate_l2_only_hybrid_reentry_signal(
            live_price=fresh_live_p,
            anchor_price=sub_anchor_p,
            l2_book_price=sub_min_upper_p,
            min_upper_tier_price=sub_min_upper_p,
            is_late_new_cycle_cutoff=is_late_cutoff,
            is_late_cutoff=is_late_cutoff,
        )
        sub_sig_type = str(sub_re_sig.get("signal_type") or "HOLD_WAIT_GATE")

        if not bool(sub_re_sig.get("should_buy")):
            sub_re_epoch = mark_sub_reentry_monitor_60s_cycle_shield(
                context=context,
                symbol=TARGET_SYMBOL,
                eval_price=fresh_live_p,
            )
            await context.ledger.update_state(
                TARGET_SYMBOL,
                last_sub_reentry_eval_ts=sub_re_epoch,
            )
            return {
                "status": "SUB_L2_ONLY_REENTRY_HOLD",
                "signal_type": sub_sig_type,
                "live_price": fresh_live_p,
                "sub_l2_ceiling_price": sub_min_upper_p,
            }

        async with context.in_memory_ordering_lock:
            async with context.dual_strike_mutex:
                st_now = context.ledger.get_state(TARGET_SYMBOL)
                if str(st_now.get("buy_order_id") or "").strip() or str(
                    st_now.get("sell_order_id") or ""
                ).strip():
                    return {"status": "ALREADY_ORDERING_IN_MUTEX"}

                in_s_sh, _ = is_within_post_sell_time_shield(
                    context, st_now, TARGET_SYMBOL
                )
                in_b_sh, _ = is_within_post_buy_time_shield(
                    context, st_now, TARGET_SYMBOL
                )
                in_sub_re_m, _ = is_within_sub_reentry_monitor_time_shield(
                    context, st_now, TARGET_SYMBOL
                )
                if in_s_sh or in_b_sh or in_sub_re_m:
                    return {"status": "HOLD_60S_TIME_SHIELD_IN_MUTEX"}

                now_buckets = buckets_from_dicts(st_now.get("buckets", []))
                now_sub_buckets = buckets_from_dicts(
                    st_now.get("sub_buckets", [])
                )
                if (
                    not now_buckets
                    or not now_sub_buckets
                    or has_active_l1_bucket(now_sub_buckets)
                ):
                    return {"status": "SUB_L1_STATE_CHANGED_IN_MUTEX"}

                now_sub_lots = sum(
                    max(1, sb.lot_count) for sb in now_sub_buckets
                )
                if now_sub_lots >= sub_max_lots_cap:
                    return {"status": "HOLD_SUB_CAP_4_LOTS_REACHED"}

                dt_re_m = datetime.now(EST_TZ)
                hm_re_m = dt_re_m.hour * 100 + dt_re_m.minute
                if (
                    sub_sig_type == "BREAKOUT_RELOAD"
                    and is_late_regular_new_cycle_cutoff_window(
                        hm_re_m, now_est=dt_re_m
                    )
                ):
                    sub_re_epoch = mark_sub_reentry_monitor_60s_cycle_shield(
                        context=context,
                        symbol=TARGET_SYMBOL,
                        eval_price=fresh_live_p,
                    )
                    await context.ledger.update_state(
                        TARGET_SYMBOL,
                        last_sub_reentry_eval_ts=sub_re_epoch,
                    )
                    return {
                        "status": "SUB_L2_ONLY_LATE_BREAKOUT_BLOCKED",
                        "signal_type": "HOLD_LATE_SESSION_BREAKOUT_CUTOFF",
                    }

                sub_min_upper_p = min(sb.book_price for sb in now_sub_buckets)
                exec_order_p = max(
                    0.01, math.floor((fresh_live_p + 1e-9) * 100.0) / 100.0
                )
                if sub_min_upper_p > 0.0 and exec_order_p > (
                    sub_min_upper_p + 1e-6
                ):
                    sub_re_epoch = mark_sub_reentry_monitor_60s_cycle_shield(
                        context=context,
                        symbol=TARGET_SYMBOL,
                        eval_price=fresh_live_p,
                    )
                    await context.ledger.update_state(
                        TARGET_SYMBOL,
                        last_sub_reentry_eval_ts=sub_re_epoch,
                    )
                    return {
                        "status": "SUB_L2_ONLY_INVERSION_BLOCKED",
                        "signal_type": "HOLD_PREVENT_INVERSION",
                    }

                eff_rt_pct_re = resolve_effective_round_trip_fee_rate_pct(
                    state_dict=st_now
                )
                fee_mult_re = 1.0 + (eff_rt_pct_re / 100.0)
                now_free_cash = max(
                    0.0, safe_float(st_now.get("free_cash_usd"), 0.0)
                )
                now_init_seed = max(
                    100.0,
                    safe_float(
                        st_now.get("initial_seed_usd"),
                        DEFAULT_INITIAL_SEED_USD,
                    ),
                )
                now_inj_res = max(
                    0.0, safe_float(st_now.get("injected_reserve_usd"), 0.0)
                )
                now_inv_tot = sum(b.actual_cost_usd for b in now_buckets) + sum(
                    sb.actual_cost_usd for sb in now_sub_buckets
                )
                now_core_eq = max(
                    now_init_seed, (now_free_cash + now_inv_tot) - now_inj_res
                )
                now_p_mode = (
                    str(st_now.get("portion_mode") or PORTION_MODE_COMPOUND)
                    .upper()
                    .strip()
                )

                raw_bp_re = await context.api.get_buying_power_usd(
                    safety_buffer_pct=0.2
                )
                if raw_bp_re <= 0.0 and now_free_cash >= (
                    exec_order_p * fee_mult_re
                ):
                    await asyncio.sleep(0.25)
                    raw_bp_re = await context.api.get_buying_power_usd(
                        safety_buffer_pct=0.2
                    )

                idle_re = compute_sub_grid_available_idle_cash(
                    free_cash_usd=now_free_cash,
                    core_equity_usd=now_core_eq,
                    broker_buying_power_usd=(
                        raw_bp_re if raw_bp_re > 0.0 else 0.0
                    ),
                    reserve_main_portions=SUB_RESERVE_MAIN_PORTIONS,
                    initial_seed_usd=now_init_seed,
                    portion_mode=now_p_mode,
                )
                avail_idle_re = safe_float(
                    idle_re.get("avail_idle_cash_usd"), 0.0
                )
                quota_ref_p = max(
                    0.01,
                    safe_float(
                        sub_re_sig.get("ref_anchor"),
                        sub_anchor_p if sub_anchor_p > 0.0 else exec_order_p,
                    ),
                )
                sub_target_qty, sub_p_bud = compute_sub4_quota_qty(
                    sub_anchor_price=quota_ref_p,
                    current_core_equity=now_core_eq,
                    initial_seed_usd=now_init_seed,
                    exec_price=exec_order_p,
                    portion_mode=now_p_mode,
                )
                min_req_sub_re = max(
                    exec_order_p * fee_mult_re,
                    sub_p_bud * MIN_DIP_BUDGET_RATIO,
                )
                if avail_idle_re < min_req_sub_re:
                    sub_re_epoch = mark_sub_reentry_monitor_60s_cycle_shield(
                        context=context,
                        symbol=TARGET_SYMBOL,
                        eval_price=exec_order_p,
                    )
                    await context.ledger.update_state(
                        TARGET_SYMBOL,
                        last_sub_reentry_eval_ts=sub_re_epoch,
                    )
                    return {"status": "HOLD_SUB_REENTRY_NO_IDLE_CASH"}

                buy_qty_sub, _ = resolve_affordable_buy_qty(
                    target_qty=sub_target_qty,
                    price_t=exec_order_p,
                    free_cash_usd=avail_idle_re,
                    broker_buying_power_usd=avail_idle_re,
                    max_portion_budget_usd=sub_p_bud,
                    round_trip_fee_rate_pct=eff_rt_pct_re,
                )
                if buy_qty_sub <= 0:
                    sub_re_epoch = mark_sub_reentry_monitor_60s_cycle_shield(
                        context=context,
                        symbol=TARGET_SYMBOL,
                        eval_price=exec_order_p,
                    )
                    await context.ledger.update_state(
                        TARGET_SYMBOL,
                        last_sub_reentry_eval_ts=sub_re_epoch,
                    )
                    return {"status": "HOLD_SUB_REENTRY_ZERO_QTY"}

                sub_re_epoch = mark_sub_reentry_monitor_60s_cycle_shield(
                    context=context,
                    symbol=TARGET_SYMBOL,
                    eval_price=exec_order_p,
                )
                pending_sub_lot_tag = (
                    "SUB_REENTRY_1FL_BREAKOUT"
                    if sub_sig_type == "BREAKOUT_RELOAD"
                    else "SUB_REENTRY_1FL"
                )
                cid = generate_client_order_id(prefix="SRE1FL")
                try:
                    ord_res = await context.api.create_order(
                        symbol=TARGET_SYMBOL,
                        side="BUY",
                        quantity=buy_qty_sub,
                        price=exec_order_p,
                        order_type="LIMIT",
                        time_in_force="DAY",
                        client_order_id=cid,
                        enforce_daymarket_block=True,
                    )
                except Exception as exc:
                    await context.ledger.update_state(
                        TARGET_SYMBOL, last_sub_reentry_eval_ts=sub_re_epoch
                    )
                    logger.warning(
                        "Case 88 서브그리드 1층 공석 재장전 주문 예외: %s",
                        exc,
                    )
                    return {"status": "SUB_ORDER_ERROR", "error": str(exc)}

                oid = str(ord_res.get("orderId") or "").strip()
                await context.ledger.update_state(
                    TARGET_SYMBOL,
                    sub_l1_target_quota_qty=buy_qty_sub,
                    buy_order_id=oid,
                    client_order_id=cid,
                    ordered_qty=buy_qty_sub,
                    buy_price=exec_order_p,
                    pending_portion_budget=sub_p_bud,
                    pending_lot_type=pending_sub_lot_tag,
                    pending_step_up_min_price=0.0,
                    pending_sub_step_up_min_price=0.0,
                    last_modify_mono=time.monotonic(),
                    last_sub_reentry_eval_ts=sub_re_epoch,
                )
                context.wakeup_event.set()
                logger.info(
                    "🛡️ [Case 88 SOXL 서브그리드 상단 %d개층 보유 중 60초 주기 서브 1층 재장전(%s) 발주] %d주 @ 지정가 $%.2f <= 서브2층상한 $%.2f (4%%예산 $%.2f · orderId=%s)",
                    len(now_sub_buckets),
                    sub_sig_type,
                    buy_qty_sub,
                    exec_order_p,
                    sub_min_upper_p,
                    sub_p_bud,
                    oid,
                )
                return {
                    "status": "SUB_L2_HELD_HYBRID_1FL_ORDERED",
                    "signal_type": sub_sig_type,
                    "orderId": oid,
                    "qty": buy_qty_sub,
                    "price": exec_order_p,
                }

    if not sub_buckets or not has_sub_active_l1:
        return None

    # -----------------------------------------------------------------------
    # [서브 분기 S-B0 · Case 78 & Case 88 : 서브 활성 1층 부분 체결 잔량(sub_rem_quota_qty > 0) 존재 시 1.5초 모니터]
    # -----------------------------------------------------------------------
    sub_l1_target_q = max(
        sub_buckets[0].qty, safe_int(st.get("sub_l1_target_quota_qty"), 0)
    )
    sub_rem_quota_qty = max(0, sub_l1_target_q - sub_buckets[0].qty)
    sub_l1_book_p = round(sub_buckets[0].book_price, 2)

    if sub_rem_quota_qty > 0 and live_p <= (sub_l1_book_p + 1e-6):
        in_sub_top_sh, _ = is_within_sub_reentry_monitor_time_shield(
            context, st, TARGET_SYMBOL
        )
        if not in_sub_top_sh and avail_idle_ledger >= (live_p * fee_mult):
            async with context.in_memory_ordering_lock:
                async with context.dual_strike_mutex:
                    st_now = context.ledger.get_state(TARGET_SYMBOL)
                    if str(st_now.get("buy_order_id") or "").strip() or str(
                        st_now.get("sell_order_id") or ""
                    ).strip():
                        return {"status": "ALREADY_ORDERING_IN_MUTEX"}

                    in_s_sh, _ = is_within_post_sell_time_shield(
                        context, st_now, TARGET_SYMBOL
                    )
                    in_b_sh, _ = is_within_post_buy_time_shield(
                        context, st_now, TARGET_SYMBOL
                    )
                    in_sub_top_m, _ = is_within_sub_reentry_monitor_time_shield(
                        context, st_now, TARGET_SYMBOL
                    )
                    if in_s_sh or in_b_sh or in_sub_top_m:
                        return {"status": "HOLD_60S_TIME_SHIELD_IN_MUTEX"}

                    now_buckets = buckets_from_dicts(st_now.get("buckets", []))
                    now_sub_buckets = buckets_from_dicts(
                        st_now.get("sub_buckets", [])
                    )
                    if (
                        not now_buckets
                        or not now_sub_buckets
                        or not has_active_l1_bucket(now_sub_buckets)
                    ):
                        return {"status": "SUB_L1_STATE_CHANGED_IN_MUTEX"}

                    now_sub_target_q = max(
                        now_sub_buckets[0].qty,
                        safe_int(st_now.get("sub_l1_target_quota_qty"), 0),
                    )
                    now_sub_rem_q = max(
                        0, now_sub_target_q - now_sub_buckets[0].qty
                    )
                    now_sub_l1_book_p = round(now_sub_buckets[0].book_price, 2)

                    if now_sub_rem_q > 0:
                        fresh_live_p = await _fetch_fresh_current_soxl_price(
                            context, fallback_price=live_p
                        )
                        if fresh_live_p > 0.0 and fresh_live_p <= (
                            now_sub_l1_book_p + 1e-6
                        ):
                            eff_rt_pct_top = (
                                resolve_effective_round_trip_fee_rate_pct(
                                    state_dict=st_now
                                )
                            )
                            fee_mult_top = 1.0 + (eff_rt_pct_top / 100.0)
                            cur_lim_p = (
                                math.floor((fresh_live_p + 1e-9) * 100.0)
                                / 100.0
                            )
                            exec_order_p = max(
                                0.01, min(cur_lim_p, now_sub_l1_book_p)
                            )
                            sub_topup_budget = round(
                                float(now_sub_rem_q) * now_sub_l1_book_p, 4
                            )
                            now_free_cash = max(
                                0.0, safe_float(st_now.get("free_cash_usd"), 0.0)
                            )
                            now_init_seed = max(
                                100.0,
                                safe_float(
                                    st_now.get("initial_seed_usd"),
                                    DEFAULT_INITIAL_SEED_USD,
                                ),
                            )
                            now_inj_res = max(
                                0.0,
                                safe_float(
                                    st_now.get("injected_reserve_usd"), 0.0
                                ),
                            )
                            now_inv_tot = sum(
                                b.actual_cost_usd for b in now_buckets
                            ) + sum(
                                sb.actual_cost_usd for sb in now_sub_buckets
                            )
                            now_core_eq = max(
                                now_init_seed,
                                (now_free_cash + now_inv_tot) - now_inj_res,
                            )
                            now_p_mode = (
                                str(
                                    st_now.get("portion_mode")
                                    or PORTION_MODE_COMPOUND
                                )
                                .upper()
                                .strip()
                            )
                            raw_bp_top = await context.api.get_buying_power_usd(
                                safety_buffer_pct=0.2
                            )
                            if raw_bp_top <= 0.0 and now_free_cash >= (
                                exec_order_p * fee_mult_top
                            ):
                                await asyncio.sleep(0.25)
                                raw_bp_top = (
                                    await context.api.get_buying_power_usd(
                                        safety_buffer_pct=0.2
                                    )
                                )
                            idle_top = compute_sub_grid_available_idle_cash(
                                free_cash_usd=now_free_cash,
                                core_equity_usd=now_core_eq,
                                broker_buying_power_usd=(
                                    raw_bp_top if raw_bp_top > 0.0 else 0.0
                                ),
                                reserve_main_portions=SUB_RESERVE_MAIN_PORTIONS,
                                initial_seed_usd=now_init_seed,
                                portion_mode=now_p_mode,
                            )
                            avail_idle_top = safe_float(
                                idle_top.get("avail_idle_cash_usd"), 0.0
                            )
                            buy_qty_sub_top, _ = resolve_affordable_buy_qty(
                                target_qty=now_sub_rem_q,
                                price_t=exec_order_p,
                                free_cash_usd=avail_idle_top,
                                broker_buying_power_usd=avail_idle_top,
                                max_portion_budget_usd=sub_topup_budget,
                                round_trip_fee_rate_pct=eff_rt_pct_top,
                            )
                            if buy_qty_sub_top > 0:
                                eff_sub_top_bud = round(
                                    float(buy_qty_sub_top) * now_sub_l1_book_p,
                                    4,
                                )
                                cid = generate_client_order_id(prefix="STOP1F")
                                try:
                                    ord_res = await context.api.create_order(
                                        symbol=TARGET_SYMBOL,
                                        side="BUY",
                                        quantity=buy_qty_sub_top,
                                        price=exec_order_p,
                                        order_type="LIMIT",
                                        time_in_force="DAY",
                                        client_order_id=cid,
                                        enforce_daymarket_block=True,
                                    )
                                    oid = str(
                                        ord_res.get("orderId") or ""
                                    ).strip()
                                    await context.ledger.update_state(
                                        TARGET_SYMBOL,
                                        sub_l1_target_quota_qty=now_sub_target_q,
                                        buy_order_id=oid,
                                        client_order_id=cid,
                                        ordered_qty=buy_qty_sub_top,
                                        buy_price=exec_order_p,
                                        pending_portion_budget=eff_sub_top_bud,
                                        pending_lot_type="SUB_TOPUP_1FL",
                                        pending_step_up_min_price=0.0,
                                        pending_sub_step_up_min_price=0.0,
                                        last_modify_mono=time.monotonic(),
                                    )
                                    context.wakeup_event.set()
                                    logger.info(
                                        "🎯 [Case 78/88 SOXL 서브 1층 단가($%.2f) 재도래 -> 서브 미체결 잔량(SUB_TOPUP_1FL) 발주] +%d주 @ 지정가 $%.2f (orderId=%s)",
                                        now_sub_l1_book_p,
                                        buy_qty_sub_top,
                                        exec_order_p,
                                        oid,
                                    )
                                    return {
                                        "status": "SUB_L1_PARTIAL_TOPUP_ORDERED",
                                        "orderId": oid,
                                        "qty": buy_qty_sub_top,
                                        "price": exec_order_p,
                                    }
                                except Exception as exc:
                                    mark_sub_reentry_monitor_60s_cycle_shield(
                                        context=context,
                                        symbol=TARGET_SYMBOL,
                                        eval_price=exec_order_p,
                                    )
                                    logger.debug(
                                        "서브 1층 잔량(SUB_TOPUP_1FL) 주문 예외(60초 쿨다운): %s",
                                        exc,
                                    )
                            else:
                                mark_sub_reentry_monitor_60s_cycle_shield(
                                    context=context,
                                    symbol=TARGET_SYMBOL,
                                    eval_price=exec_order_p,
                                )

    # -----------------------------------------------------------------------
    # [서브 분기 S-B2 · Case 88 : 서브 활성 1층 보유 중 10분 고정 매수 게이트 (4단 와이드 신저가 OR 10영업일/-10% 저가해금)]
    # -----------------------------------------------------------------------
    if sub_cur_total_lots >= sub_max_lots_cap:
        return {
            "status": "HOLD_SUB_CAP_4_LOTS_REACHED",
            "sub_cur_total_lots": sub_cur_total_lots,
            "sub_max_total_lots": sub_max_lots_cap,
        }

    sub_gate_open, sub_cur_bucket_id, sub_today_str, _ = (
        evaluate_buy_gate_bucket_status(
            now_est=dt_now,
            buy_interval_min=LOCKED_BUY_INTERVAL_MIN,
            last_evaluated_bucket_id=safe_int(
                st.get("sub_last_evaluated_buy_bucket_id"), -1
            ),
            last_evaluated_date=str(st.get("sub_last_evaluated_date") or ""),
        )
    )
    if not sub_gate_open:
        return None

    fresh_live_p = await _fetch_fresh_current_soxl_price(
        context, fallback_price=live_p
    )
    if fresh_live_p <= 0.0:
        return None

    sub_ratchet_lots = max(
        sub_cur_total_lots, safe_int(st.get("sub_ratchet_max_lots"), 0)
    )
    threshold_mode = str(st.get("threshold_mode") or "WIDE_RUNWAY").upper()
    sub_drop_pct, _, _ = get_golden8_prog_thresholds(
        held_lots=sub_cur_total_lots,
        threshold_mode=threshold_mode,
        cycle_ratchet_max_lots=sub_ratchet_lots,
    )
    sub_anchor_p = safe_float(
        st.get("sub_anchor_price"), sub_buckets[0].book_price
    )
    sub_cycle_min_p = safe_float(
        st.get("sub_cycle_min_buy_price"), sub_anchor_p
    )
    sub_frozen_d = max(0, safe_int(st.get("sub_consec_frozen_days"), 0))

    sub_dip_eval = evaluate_sub_grid_dip_signal(
        live_price=fresh_live_p,
        sub_buckets=sub_buckets,
        sub_anchor_price=sub_anchor_p,
        sub_cycle_min_buy_price=sub_cycle_min_p,
        sub_drop_buy_pct=sub_drop_pct,
        sub_consec_frozen_days=sub_frozen_d,
        sub_max_total_lots=sub_max_lots_cap,
    )
    if not bool(sub_dip_eval.get("should_buy")):
        await context.ledger.update_state(
            TARGET_SYMBOL,
            sub_last_evaluated_buy_bucket_id=sub_cur_bucket_id,
            sub_last_evaluated_date=sub_today_str,
        )
        return {
            "status": "SUB_GATE_HOLD_PASSED",
            "trigger_tag": sub_dip_eval.get("trigger_tag"),
            "sub_cur_total_lots": sub_cur_total_lots,
        }

    async with context.in_memory_ordering_lock:
        async with context.dual_strike_mutex:
            st_now = context.ledger.get_state(TARGET_SYMBOL)
            if str(st_now.get("buy_order_id") or "").strip() or str(
                st_now.get("sell_order_id") or ""
            ).strip():
                return {"status": "ALREADY_ORDERING_IN_MUTEX"}

            in_s_sh, _ = is_within_post_sell_time_shield(
                context, st_now, TARGET_SYMBOL
            )
            in_b_sh, _ = is_within_post_buy_time_shield(
                context, st_now, TARGET_SYMBOL
            )
            if in_s_sh or in_b_sh:
                return {"status": "HOLD_60S_TIME_SHIELD_IN_MUTEX"}

            now_buckets = buckets_from_dicts(st_now.get("buckets", []))
            now_sub_buckets = buckets_from_dicts(st_now.get("sub_buckets", []))
            if (
                not now_buckets
                or not now_sub_buckets
                or not has_active_l1_bucket(now_sub_buckets)
            ):
                return {"status": "SUB_L1_STATE_CHANGED_IN_MUTEX"}

            now_sub_lots = sum(max(1, sb.lot_count) for sb in now_sub_buckets)
            if now_sub_lots >= sub_max_lots_cap:
                return {"status": "HOLD_SUB_CAP_4_LOTS_REACHED"}

            sub_gate_m, _, _, _ = evaluate_buy_gate_bucket_status(
                now_est=dt_now,
                buy_interval_min=LOCKED_BUY_INTERVAL_MIN,
                last_evaluated_bucket_id=safe_int(
                    st_now.get("sub_last_evaluated_buy_bucket_id"), -1
                ),
                last_evaluated_date=str(
                    st_now.get("sub_last_evaluated_date") or ""
                ),
            )
            if not sub_gate_m:
                return {"status": "SUB_BUCKET_ALREADY_EVALUATED_IN_MUTEX"}

            now_sub_ratchet = max(
                now_sub_lots, safe_int(st_now.get("sub_ratchet_max_lots"), 0)
            )
            now_sub_drop, _, _ = get_golden8_prog_thresholds(
                held_lots=now_sub_lots,
                threshold_mode=threshold_mode,
                cycle_ratchet_max_lots=now_sub_ratchet,
            )
            now_sub_anc = safe_float(
                st_now.get("sub_anchor_price"), now_sub_buckets[0].book_price
            )
            now_sub_min_p = safe_float(
                st_now.get("sub_cycle_min_buy_price"), now_sub_anc
            )
            now_sub_frozen = max(
                0, safe_int(st_now.get("sub_consec_frozen_days"), 0)
            )

            now_sub_dip_eval = evaluate_sub_grid_dip_signal(
                live_price=fresh_live_p,
                sub_buckets=now_sub_buckets,
                sub_anchor_price=now_sub_anc,
                sub_cycle_min_buy_price=now_sub_min_p,
                sub_drop_buy_pct=now_sub_drop,
                sub_consec_frozen_days=now_sub_frozen,
                sub_max_total_lots=sub_max_lots_cap,
            )
            if not bool(now_sub_dip_eval.get("should_buy")):
                return {"status": "SUB_DIP_SIGNAL_CHANGED_IN_MUTEX"}

            is_sub_unlock = bool(now_sub_dip_eval.get("is_sub_unlock", False))
            sub_trig_tag = str(
                now_sub_dip_eval.get("trigger_tag") or "SUB_STATIC_NEW_LOW"
            )
            sub_ref_static = safe_float(
                now_sub_dip_eval.get("ref_static_anchor"),
                now_sub_buckets[0].book_price,
            )
            sub_quota_ref_p = max(
                0.01,
                safe_float(
                    now_sub_dip_eval.get("quota_ref_price"), sub_ref_static
                ),
            )
            sub_stepped_min_p = safe_float(
                now_sub_dip_eval.get("sub_stepped_min_price"), 0.0
            )

            if is_sub_unlock and sub_stepped_min_p > 0.0:
                max_sub_trig_p = (
                    math.floor((sub_stepped_min_p + 1e-9) * 100.0) / 100.0
                )
            else:
                max_sub_trig_p = (
                    math.floor(
                        (
                            sub_ref_static * (1.0 + now_sub_drop / 100.0)
                            + 1e-9
                        )
                        * 100.0
                    )
                    / 100.0
                )
            cur_limit_p = math.floor((fresh_live_p + 1e-9) * 100.0) / 100.0
            exec_order_p = max(0.01, min(cur_limit_p, max_sub_trig_p))

            eff_rt_pct_dip = resolve_effective_round_trip_fee_rate_pct(
                state_dict=st_now
            )
            fee_mult_dip = 1.0 + (eff_rt_pct_dip / 100.0)
            now_free_cash = max(
                0.0, safe_float(st_now.get("free_cash_usd"), 0.0)
            )
            now_init_seed = max(
                100.0,
                safe_float(
                    st_now.get("initial_seed_usd"), DEFAULT_INITIAL_SEED_USD
                ),
            )
            now_inj_res = max(
                0.0, safe_float(st_now.get("injected_reserve_usd"), 0.0)
            )
            now_inv_tot = sum(b.actual_cost_usd for b in now_buckets) + sum(
                sb.actual_cost_usd for sb in now_sub_buckets
            )
            now_core_eq = max(
                now_init_seed, (now_free_cash + now_inv_tot) - now_inj_res
            )
            now_p_mode = (
                str(st_now.get("portion_mode") or PORTION_MODE_COMPOUND)
                .upper()
                .strip()
            )

            raw_bp_dip = await context.api.get_buying_power_usd(
                safety_buffer_pct=0.2
            )
            if raw_bp_dip <= 0.0 and now_free_cash >= (
                exec_order_p * fee_mult_dip
            ):
                await asyncio.sleep(0.25)
                raw_bp_dip = await context.api.get_buying_power_usd(
                    safety_buffer_pct=0.2
                )

            idle_dip = compute_sub_grid_available_idle_cash(
                free_cash_usd=now_free_cash,
                core_equity_usd=now_core_eq,
                broker_buying_power_usd=(
                    raw_bp_dip if raw_bp_dip > 0.0 else 0.0
                ),
                reserve_main_portions=SUB_RESERVE_MAIN_PORTIONS,
                initial_seed_usd=now_init_seed,
                portion_mode=now_p_mode,
            )
            avail_idle_dip = safe_float(
                idle_dip.get("avail_idle_cash_usd"), 0.0
            )
            sub_target_qty, sub_p_bud = compute_sub4_quota_qty(
                sub_anchor_price=sub_quota_ref_p,
                current_core_equity=now_core_eq,
                initial_seed_usd=now_init_seed,
                exec_price=exec_order_p,
                portion_mode=now_p_mode,
            )
            min_req_sub_dip = max(
                exec_order_p * fee_mult_dip,
                sub_p_bud * MIN_DIP_BUDGET_RATIO,
                now_sub_buckets[0].actual_cost_usd * MIN_DIP_VS_L1_RATIO,
            )
            if avail_idle_dip < min_req_sub_dip:
                await context.ledger.update_state(
                    TARGET_SYMBOL,
                    sub_last_evaluated_buy_bucket_id=sub_cur_bucket_id,
                    sub_last_evaluated_date=sub_today_str,
                )
                return {
                    "status": "HOLD_SUB_DIP_INSUFFICIENT_IDLE_CASH",
                    "avail_idle_cash_usd": avail_idle_dip,
                }

            buy_qty_sub, _ = resolve_affordable_buy_qty(
                target_qty=sub_target_qty,
                price_t=exec_order_p,
                free_cash_usd=avail_idle_dip,
                broker_buying_power_usd=avail_idle_dip,
                max_portion_budget_usd=sub_p_bud,
                round_trip_fee_rate_pct=eff_rt_pct_dip,
            )
            if buy_qty_sub <= 0:
                await context.ledger.update_state(
                    TARGET_SYMBOL,
                    sub_last_evaluated_buy_bucket_id=sub_cur_bucket_id,
                    sub_last_evaluated_date=sub_today_str,
                )
                return {"status": "HOLD_SUB_DIP_ZERO_QTY"}

            cid_prefix = (
                f"SU{now_sub_lots + 1}L"
                if is_sub_unlock
                else f"SB{now_sub_lots + 1}L"
            )
            cid = generate_client_order_id(prefix=cid_prefix)
            try:
                ord_res = await context.api.create_order(
                    symbol=TARGET_SYMBOL,
                    side="BUY",
                    quantity=buy_qty_sub,
                    price=exec_order_p,
                    order_type="LIMIT",
                    time_in_force="DAY",
                    client_order_id=cid,
                    enforce_daymarket_block=True,
                )
            except Exception as exc:
                await context.ledger.update_state(
                    TARGET_SYMBOL,
                    sub_last_evaluated_buy_bucket_id=sub_cur_bucket_id,
                    sub_last_evaluated_date=sub_today_str,
                )
                logger.warning(
                    "Case 88 서브그리드 10분 게이트(%s) 추매 주문 예외: %s",
                    sub_trig_tag,
                    exc,
                )
                return {"status": "SUB_BUY_ORDER_ERROR", "error": str(exc)}

            oid = str(ord_res.get("orderId") or "").strip()
            await context.ledger.update_state(
                TARGET_SYMBOL,
                sub_l1_target_quota_qty=buy_qty_sub,
                buy_order_id=oid,
                client_order_id=cid,
                ordered_qty=buy_qty_sub,
                buy_price=exec_order_p,
                pending_portion_budget=sub_p_bud,
                pending_lot_type="SUB_DIP_1FL",
                pending_step_up_min_price=0.0,
                pending_sub_step_up_min_price=(
                    round(sub_stepped_min_p, 4) if is_sub_unlock else 0.0
                ),
                sub_last_evaluated_buy_bucket_id=sub_cur_bucket_id,
                sub_last_evaluated_date=sub_today_str,
                last_modify_mono=time.monotonic(),
            )
            context.wakeup_event.set()
            logger.info(
                "🛡️ [Case 88 SOXL 3층 서브그리드 %d/%d회분(%s) 추매 발주] %d주 @ 지정가 $%.2f (4%%예산 $%.2f · 유휴현금 $%.2f · orderId=%s)",
                now_sub_lots + 1,
                sub_max_lots_cap,
                sub_trig_tag,
                buy_qty_sub,
                exec_order_p,
                sub_p_bud,
                avail_idle_dip,
                oid,
            )
            return {
                "status": "SUB_QUOTA_DIP_BUY_ORDERED",
                "trigger_tag": sub_trig_tag,
                "is_sub_unlock": is_sub_unlock,
                "orderId": oid,
                "qty": buy_qty_sub,
                "price": exec_order_p,
                "sub_cur_total_lots": now_sub_lots,
            }
# ---------------------------------------------------------------------------
# [핵심 2] 진화 챔피언 (👑 06_L2L7_RATCHET_8PCT × 🛡️ 13_SUB_L1L3_RESV05_CAP4L[Default ON] × 💉 무제한 예비수혈 × 🔓 06_STEP2X_15PCT_C20 × 🛡️ Case 84 × 💵 Case 91 복리/단리 연동) : 비대칭 매수 타격 엔진
#  - 분기 A   : 본 그리드 0주 상태(사이클 종료) -> 15:30 ~ 16:00 EST 구간에서는 새 사이클 첫 1층 진입 100% 차단(Case 84) · 그 외 60초 타임쉴드 후 첫 1층(REENTRY_1FL) 산입
#  - 분기 B-1 : 본 그리드 상단 2~7층 보유 중 1층 공석 -> 매 60.0초(1분) 주기 재장전 모니터 & 2층 단가 상한(Case 73) 하에서
#               -1.00% 눌림목(PULLBACK_RELOAD · 04:07 ~ 16:00 EST 전 구간 허용) 및 +1.00% 상승돌파(BREAKOUT_RELOAD · 04:07 ~ 15:29 EST 허용 / 15:30 ~ 16:00 EST 돌파 차단 · Case 84)
#               (본 그리드 대기/패스 시 Default-ON 3층 서브 그리드 엔진 연속 가동 · Case 88)
#  - 분기 B-0 : 본 그리드 활성 1층 부분체결 미체결 잔량(rem_quota_qty > 0) -> 60초 타임쉴드 후 매 1.5초 모니터에서 현재가 <= 1층 단가 도래 시 잔량(TOPUP_1FL) 발주(Case 78)
#  - 분기 B-2 : 본 그리드 활성 1층 보유 중 -> 10분 고정 게이트 & 정적 기억저가 및 최고도달회차(cycle_ratchet_max_lots · Case 87) 잠금 4단 와이드 신저가 OR STEP2X_15PCT_C20 스텝업 추매(Case 76) & GUARD30/무제한 예비수혈(Case 77, Case 91)
#               (본 그리드 대기/패스 시 Default-ON 3층 서브 그리드 엔진 연속 가동 · Case 88)
# ---------------------------------------------------------------------------
async def execute_seed_protected_buy_gate_plugin(
    context: Any,
    holdings: Dict[str, Dict[str, Any]],
    prices: Dict[str, float],
    now_est: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    🎯 1, 🎯 2, 🎯 4 & Case 25 ~ 91 (챔피언 : 👑 06_L2L7_RATCHET_8PCT × 🛡️ 13_SUB_L1L3_RESV05_CAP4L[Default ON] × 💉 무제한 예비수혈 × 🔓 06_STEP2X_15PCT_C20 × 🛡️ Case 84 × 💵 Case 91 복리/단리 모드 연동):
    04:07:00 ~ 16:00:00 EST 운용 구간에서 작동하는 비대칭 매수 타격 엔진.
    """
    dt_now = now_est.astimezone(EST_TZ) if now_est else datetime.now(EST_TZ)
    hm = dt_now.hour * 100 + dt_now.minute

    # 1) 미체결 매수 주문이 있으면 먼저 체결 확인 수행
    st = context.ledger.get_state(TARGET_SYMBOL)
    if str(st.get("buy_order_id") or "").strip():
        return await sync_pending_buy_order_plugin(
            context=context,
            holdings=holdings,
            prices=prices,
            now_est=dt_now,
        )

    # 2) 04:07 ~ 16:00 EST 운용 시간대 및 마스터 전원(is_active) 확인
    if not is_active_buy_window(hm, now_est=dt_now):
        return {"status": "OUTSIDE_TRADING_WINDOW"}

    if not bool(st.get("is_active", True)):
        return {"status": "BOT_INACTIVE"}

    # 미체결 매도 주문이 진행 중이면 매도 완료까지 대기 (동일 틱 자전거래 방지, Case 44)
    if str(st.get("sell_order_id") or "").strip():
        return {"status": "SELL_ORDER_IN_PROGRESS"}

    # 🛡️ 3) [Case 65 핵심] 매도(및 0주 싸이클 종료) 후 60.0초 타임쉴드 & 직전 매수 후 60.0초 타임쉴드 최우선 강제 검문!
    in_sell_shield, remain_sell_sec = is_within_post_sell_time_shield(
        context, st, TARGET_SYMBOL
    )
    if in_sell_shield:
        return {
            "status": "HOLD_POST_SELL_60S_TIME_SHIELD",
            "remain_shield_sec": remain_sell_sec,
        }

    in_buy_shield, remain_buy_sec = is_within_post_buy_time_shield(
        context, st, TARGET_SYMBOL
    )
    if in_buy_shield:
        return {
            "status": "HOLD_POST_BUY_60S_TIME_SHIELD",
            "remain_shield_sec": remain_buy_sec,
        }

    live_p = _get_live_soxl_price(context, prices, holdings, dt_now)
    if live_p <= 0.0:
        return {"status": "NO_LIVE_PRICE"}

    buckets = buckets_from_dicts(st.get("buckets", []))
    sub_buckets = buckets_from_dicts(st.get("sub_buckets", []))
    h_qty = safe_int((holdings or {}).get(TARGET_SYMBOL, {}).get("qty"), 0)

    # 🛡️ 3-B) [Case 77 & Case 88] 본 그리드 시드고갈 입금 대기 중일 때 60.0초 감지 타임쉴드 검문
    # (단, 본 그리드가 입금 대기 쉴드 중이더라도 서브 그리드 미체결 잔량 보충 등 서브 엔진 작동 가능 여부를 먼저 점검)
    in_res_sh, rem_res_sec = is_within_reserve_deposit_check_shield(
        context, st, TARGET_SYMBOL
    )
    if in_res_sh:
        if buckets:
            sub_res_during_sh = await _execute_sub_grid_buy_engine_plugin(
                context=context,
                holdings=holdings,
                prices=prices,
                dt_now=dt_now,
                live_p=live_p,
            )
            if isinstance(sub_res_during_sh, dict) and str(
                sub_res_during_sh.get("status") or ""
            ).endswith("_ORDERED"):
                return sub_res_during_sh
        return {
            "status": "HOLD_WAITING_RESERVE_DEPOSIT_60S_SHIELD",
            "remain_shield_sec": rem_res_sec,
            "required_reserve_deposit_usd": safe_float(
                st.get("required_reserve_deposit_usd"), 0.0
            ),
        }

    eff_rt_pct = resolve_effective_round_trip_fee_rate_pct(state_dict=st)
    init_seed = max(
        100.0,
        safe_float(st.get("initial_seed_usd"), DEFAULT_INITIAL_SEED_USD),
    )
    injected_reserve_usd = max(
        0.0, safe_float(st.get("injected_reserve_usd"), 0.0)
    )
    free_cash = max(0.0, safe_float(st.get("free_cash_usd"), 0.0))
    actual_invested = sum(b.actual_cost_usd for b in buckets) + sum(
        sb.actual_cost_usd for sb in sub_buckets
    )
    # Case 77, Case 88 & Case 91: 온디맨드 예비시드 수혈금(injected_reserve_usd)을 제외한 순수 코어 총자산(core_equity) 및 운용 모드 기준자산 산출
    core_equity = max(
        init_seed, (free_cash + actual_invested) - injected_reserve_usd
    )
    portion_mode = (
        str(st.get("portion_mode") or PORTION_MODE_COMPOUND).upper().strip()
    )
    budget_base_eq = resolve_portion_budget_base_equity(
        initial_seed_usd=init_seed,
        core_equity_usd=core_equity,
        portion_mode=portion_mode,
    )
    threshold_mode = str(st.get("threshold_mode") or "WIDE_RUNWAY").upper()
    unlock_mode = str(
        st.get("unlock_mode") or DEFAULT_UNLOCK_MODE
    ).upper()
    buy_interval_min = LOCKED_BUY_INTERVAL_MIN

    sub_total_sh = sum(sb.qty for sb in sub_buckets)
    is_zero_shares = bool(
        len(buckets) == 0 and (h_qty == 0 or h_qty == sub_total_sh)
    )
    has_active_l1 = has_active_l1_bucket(buckets)
    # 🚨 Case 71, Case 72 & Case 73: 본 그리드 상단에 2층 ~ 7층 그리드(GRID_L2 ~ GRID_L7)가 남아 있고 1층이 익절되어 공석인 상태!
    is_l2_only_vacant_l1 = bool(len(buckets) > 0 and not has_active_l1)

    # -----------------------------------------------------------------------
    # [분기 A : 본 그리드 보유 잔고 0주 상태 (is_zero_shares)]
    # -> 🛡️ [Case 84 핵심 방어] : 정규장 마감 30분 전(15:30 ~ 16:00 EST) 구간에서는 0주 새 사이클 첫 1층(REENTRY_1FL) 진입 100% 금지!
    # -----------------------------------------------------------------------
    if is_zero_shares:
        if is_late_regular_new_cycle_cutoff_window(hm, now_est=dt_now):
            return {
                "status": "HOLD_LATE_SESSION_NEW_CYCLE_CUTOFF",
                "hm": hm,
                "cutoff_hm": NEW_CYCLE_BUY_CUTOFF_HM,
            }

        async with context.in_memory_ordering_lock:
            async with context.dual_strike_mutex:
                st_now = context.ledger.get_state(TARGET_SYMBOL)
                if str(st_now.get("buy_order_id") or "").strip() or str(
                    st_now.get("sell_order_id") or ""
                ).strip():
                    return {"status": "ALREADY_ORDERING_IN_MUTEX"}

                now_buckets = buckets_from_dicts(st_now.get("buckets", []))
                if len(now_buckets) > 0:
                    return {"status": "L1_ALREADY_FILLED_IN_MUTEX"}

                # [Case 84 뮤텍스 내부 2차 시각 재검문 : 15:29:59 -> 15:30:00 경계 경합 원천 차단]
                dt_mutex = (
                    now_est.astimezone(EST_TZ)
                    if now_est
                    else datetime.now(EST_TZ)
                )
                hm_mutex = dt_mutex.hour * 100 + dt_mutex.minute
                if is_late_regular_new_cycle_cutoff_window(
                    hm_mutex, now_est=dt_mutex
                ):
                    return {
                        "status": "HOLD_LATE_SESSION_NEW_CYCLE_CUTOFF",
                        "hm": hm_mutex,
                        "cutoff_hm": NEW_CYCLE_BUY_CUTOFF_HM,
                    }

                in_s_sh, rem_s = is_within_post_sell_time_shield(
                    context, st_now, TARGET_SYMBOL
                )
                if in_s_sh:
                    return {
                        "status": "HOLD_POST_SELL_60S_TIME_SHIELD_IN_MUTEX",
                        "remain_shield_sec": rem_s,
                    }

                in_b_sh, rem_b = is_within_post_buy_time_shield(
                    context, st_now, TARGET_SYMBOL
                )
                if in_b_sh:
                    return {
                        "status": "HOLD_POST_BUY_60S_TIME_SHIELD_IN_MUTEX",
                        "remain_shield_sec": rem_b,
                    }

                fresh_live_p = await _fetch_fresh_current_soxl_price(
                    context, fallback_price=live_p
                )
                if fresh_live_p <= 0.0:
                    return {"status": "NO_FRESH_LIVE_PRICE"}

                exec_order_p = max(
                    0.01, math.floor((fresh_live_p + 1e-9) * 100.0) / 100.0
                )

                # [Case 67, Case 77, Case 88 & Case 91 : 뮤텍스 내부 st_now 기준 now_core_eq, now_init_seed, now_p_mode 재산출 통일]
                eff_rt_pct_0sh = resolve_effective_round_trip_fee_rate_pct(
                    state_dict=st_now
                )
                now_sub_0sh = buckets_from_dicts(st_now.get("sub_buckets", []))
                now_free_cash_0sh = max(
                    0.0, safe_float(st_now.get("free_cash_usd"), 0.0)
                )
                now_init_seed_0sh = max(
                    100.0,
                    safe_float(
                        st_now.get("initial_seed_usd"),
                        DEFAULT_INITIAL_SEED_USD,
                    ),
                )
                now_inj_res_0sh = max(
                    0.0, safe_float(st_now.get("injected_reserve_usd"), 0.0)
                )
                now_inv_tot_0sh = sum(
                    sb.actual_cost_usd for sb in now_sub_0sh
                )
                now_core_eq_0sh = max(
                    now_init_seed_0sh,
                    (now_free_cash_0sh + now_inv_tot_0sh) - now_inj_res_0sh,
                )
                now_p_mode_0sh = (
                    str(st_now.get("portion_mode") or PORTION_MODE_COMPOUND)
                    .upper()
                    .strip()
                )

                prev_anchor_p = safe_float(st_now.get("anchor_price"), 0.0)
                ref_zero_anchor = (
                    prev_anchor_p if prev_anchor_p > 0.0 else exec_order_p
                )
                target_qty, portion_budget = compute_golden8_quota_qty(
                    anchor_price=ref_zero_anchor,
                    current_total_equity=now_core_eq_0sh,
                    initial_seed_usd=now_init_seed_0sh,
                    portion_mode=now_p_mode_0sh,
                    exec_price=exec_order_p,
                )

                (
                    can_proceed_0sh,
                    eff_free_cash_0sh,
                    bp_usd_0sh,
                    guard_res_0sh,
                ) = await _check_and_execute_guard30_or_reserve_injection(
                    context=context,
                    st_now=st_now,
                    exec_order_p=exec_order_p,
                    portion_budget=portion_budget,
                    l1_actual_cost_usd=0.0,
                    is_dip_promotion=False,
                    is_vacant_l1_reentry=False,
                    trigger_desc="0주 첫 1층 진입",
                )
                if not can_proceed_0sh:
                    return {
                        "status": "HOLD_GUARD30_WAITING_RESERVE_DEPOSIT",
                        "guard_eval": guard_res_0sh,
                    }

                buy_qty, _est_spent = resolve_affordable_buy_qty(
                    target_qty=target_qty,
                    price_t=exec_order_p,
                    free_cash_usd=eff_free_cash_0sh,
                    broker_buying_power_usd=(
                        bp_usd_0sh if bp_usd_0sh > 0.0 else None
                    ),
                    max_portion_budget_usd=portion_budget,
                    round_trip_fee_rate_pct=eff_rt_pct_0sh,
                )

                if buy_qty <= 0:
                    return {"status": "INSUFFICIENT_CASH_FOR_0SH_ENTRY"}

                _, cur_bucket_id, today_str, _ = evaluate_buy_gate_bucket_status(
                    now_est=dt_now,
                    buy_interval_min=buy_interval_min,
                    last_evaluated_bucket_id=safe_int(
                        st_now.get("last_evaluated_buy_bucket_id"), -1
                    ),
                    last_evaluated_date=str(
                        st_now.get("last_evaluated_date") or ""
                    ),
                )

                cid = generate_client_order_id(prefix="INI1FL")
                try:
                    ord_res = await context.api.create_order(
                        symbol=TARGET_SYMBOL,
                        side="BUY",
                        quantity=buy_qty,
                        price=exec_order_p,
                        order_type="LIMIT",
                        time_in_force="DAY",
                        client_order_id=cid,
                        enforce_daymarket_block=True,
                    )
                except Exception as exc:
                    logger.warning(
                        "0주 현재가 지정가 실물 1층(REENTRY_1FL) 매수 주문 예외: %s",
                        exc,
                    )
                    return {"status": "ORDER_ERROR", "error": str(exc)}

                oid = str(ord_res.get("orderId") or "").strip()
                await context.ledger.update_state(
                    TARGET_SYMBOL,
                    l1_target_quota_qty=buy_qty,
                    buy_order_id=oid,
                    client_order_id=cid,
                    ordered_qty=buy_qty,
                    buy_price=exec_order_p,
                    pending_portion_budget=portion_budget,
                    pending_lot_type="REENTRY_1FL",
                    pending_step_up_min_price=0.0,
                    pending_sub_step_up_min_price=0.0,
                    last_evaluated_buy_bucket_id=cur_bucket_id,
                    last_evaluated_date=today_str,
                    last_modify_mono=time.monotonic(),
                    last_reentry_eval_ts=0.0,
                )
                context.wakeup_event.set()
                logger.info(
                    "🔵 [SOXL 0주 60초 타임쉴드 완료 후 현재가 지정가 1층 매수 발주] %d주 @ 지정가 $%.2f (1회예산 $%.2f · orderId=%s)",
                    buy_qty,
                    exec_order_p,
                    portion_budget,
                    oid,
                )
                return {
                    "status": "ZERO_SHARES_IMMEDIATE_1FL_ORDERED",
                    "orderId": oid,
                    "qty": buy_qty,
                    "price": exec_order_p,
                }

    # -----------------------------------------------------------------------
    # [분기 B-1 · Case 73, Case 77, Case 84, Case 88 & Case 91 : 본 그리드 상단(2층 ~ 7층)만 보유 중 (1층 공석, is_l2_only_vacant_l1 == True)]
    # -> 2층 단가 이하(Case 73) 안전 영역 내에서:
    #    - 눌림목(-1.00%, PULLBACK_RELOAD)은 04:07 ~ 16:00 EST 전 구간 허용!
    #    - 상승돌파(+1.00%, BREAKOUT_RELOAD)는 04:07 ~ 15:29 EST 허용하되,
    #      15:30 ~ 16:00 EST 구간에서는 데드캣 고점 추격 방어를 위해 HOLD_LATE_SESSION_BREAKOUT_CUTOFF 로 원천 차단!
    #    - 본 그리드가 60초 재장전 쉴드 중이거나 패스했을 때는 즉시 Default-ON 3층 서브 그리드 엔진을 가동!
    # -----------------------------------------------------------------------
    if is_l2_only_vacant_l1:
        in_re_shield, rem_re_sec = is_within_reentry_monitor_time_shield(
            context, st, TARGET_SYMBOL
        )
        if in_re_shield:
            sub_res_re = await _execute_sub_grid_buy_engine_plugin(
                context=context,
                holdings=holdings,
                prices=prices,
                dt_now=dt_now,
                live_p=live_p,
            )
            if isinstance(sub_res_re, dict) and str(
                sub_res_re.get("status") or ""
            ).endswith("_ORDERED"):
                return sub_res_re
            return {
                "status": "HOLD_REENTRY_60S_TIME_SHIELD",
                "remain_shield_sec": rem_re_sec,
            }

        fresh_live_p = await _fetch_fresh_current_soxl_price(
            context, fallback_price=live_p
        )
        if fresh_live_p <= 0.0:
            return {"status": "NO_FRESH_LIVE_PRICE"}

        min_upper_tier_p = min(b.book_price for b in buckets)
        wma_info = compute_upper_2_to_7_moving_avg(buckets)
        upper_wma_p = safe_float(
            wma_info.get("upper_wma_price"), min_upper_tier_p
        )
        anchor_p = safe_float(st.get("anchor_price"), min_upper_tier_p)
        is_late_cutoff = is_late_regular_new_cycle_cutoff_window(
            hm, now_est=dt_now
        )

        reentry_sig = evaluate_l2_only_hybrid_reentry_signal(
            live_price=fresh_live_p,
            anchor_price=anchor_p,
            l2_book_price=min_upper_tier_p,
            min_upper_tier_price=min_upper_tier_p,
            is_late_new_cycle_cutoff=is_late_cutoff,
            is_late_cutoff=is_late_cutoff,
        )
        sig_type = str(reentry_sig.get("signal_type") or "HOLD_WAIT_GATE")

        if not bool(reentry_sig.get("should_buy")):
            new_pass_cnt = safe_int(st.get("seed_protect_pass_cnt"), 0) + 1
            new_day_pass = (
                safe_int(st.get("daily_seed_protect_pass_cnt"), 0) + 1
            )
            re_eval_epoch = mark_reentry_monitor_60s_cycle_shield(
                context=context,
                symbol=TARGET_SYMBOL,
                eval_price=fresh_live_p,
            )
            await context.ledger.update_state(
                TARGET_SYMBOL,
                last_reentry_eval_ts=re_eval_epoch,
                seed_protect_pass_cnt=new_pass_cnt,
                daily_seed_protect_pass_cnt=new_day_pass,
            )
            sub_res_after_pass = await _execute_sub_grid_buy_engine_plugin(
                context=context,
                holdings=holdings,
                prices=prices,
                dt_now=dt_now,
                live_p=fresh_live_p,
            )
            if isinstance(sub_res_after_pass, dict) and str(
                sub_res_after_pass.get("status") or ""
            ).endswith("_ORDERED"):
                return sub_res_after_pass

            if sig_type == "HOLD_PREVENT_INVERSION":
                logger.info(
                    "🛡️ [Case 73 1층>2층 단가역전 원천 차단] 현재가 $%.2f > 2층단가 상한 $%.2f (직전익절 $%.2f 대비 %+.2f%%) -> 매수 패스 & 60초 타임쉴드 재장전",
                    fresh_live_p,
                    min_upper_tier_p,
                    safe_float(reentry_sig.get("ref_anchor"), anchor_p),
                    safe_float(reentry_sig.get("chg_from_exit_pct"), 0.0),
                )
                return {
                    "status": "L2_ONLY_REENTRY_INVERSION_BLOCKED",
                    "signal_type": sig_type,
                    "live_price": fresh_live_p,
                    "l2_ceiling_price": min_upper_tier_p,
                    "ref_anchor": reentry_sig.get("ref_anchor"),
                    "chg_from_exit_pct": reentry_sig.get("chg_from_exit_pct"),
                    "seed_protect_pass_cnt": new_day_pass,
                    "next_reentry_check_sec": REENTRY_MONITOR_TIME_SHIELD_SEC,
                }
            if sig_type == "HOLD_LATE_SESSION_BREAKOUT_CUTOFF":
                logger.info(
                    "🛡️ [Case 84 장마감 30분전(15:30~16:00 EST) 1층 공석 +1.0%% 돌파 추격 원천 차단] 현재가 $%.2f (직전익절 $%.2f 대비 %+.2f%%) -> 돌파매수 패스 & 눌림목(-1.0%%)만 감시",
                    fresh_live_p,
                    safe_float(reentry_sig.get("ref_anchor"), anchor_p),
                    safe_float(reentry_sig.get("chg_from_exit_pct"), 0.0),
                )
                return {
                    "status": "L2_ONLY_REENTRY_LATE_BREAKOUT_BLOCKED",
                    "signal_type": sig_type,
                    "live_price": fresh_live_p,
                    "l2_ceiling_price": min_upper_tier_p,
                    "ref_anchor": reentry_sig.get("ref_anchor"),
                    "chg_from_exit_pct": reentry_sig.get("chg_from_exit_pct"),
                    "seed_protect_pass_cnt": new_day_pass,
                    "next_reentry_check_sec": REENTRY_MONITOR_TIME_SHIELD_SEC,
                }
            return {
                "status": "L2_ONLY_REENTRY_HOLD_PASSED",
                "signal_type": sig_type,
                "ref_anchor": reentry_sig.get("ref_anchor"),
                "l2_ceiling_price": min_upper_tier_p,
                "chg_from_exit_pct": reentry_sig.get("chg_from_exit_pct"),
                "seed_protect_pass_cnt": new_day_pass,
                "next_reentry_check_sec": REENTRY_MONITOR_TIME_SHIELD_SEC,
            }

        async with context.in_memory_ordering_lock:
            async with context.dual_strike_mutex:
                st_now = context.ledger.get_state(TARGET_SYMBOL)
                if str(st_now.get("buy_order_id") or "").strip() or str(
                    st_now.get("sell_order_id") or ""
                ).strip():
                    return {"status": "ALREADY_ORDERING_IN_MUTEX"}

                now_buckets = buckets_from_dicts(st_now.get("buckets", []))
                if not now_buckets or has_active_l1_bucket(now_buckets):
                    return {"status": "L1_STATE_CHANGED_IN_MUTEX"}

                in_re_m, _ = is_within_reentry_monitor_time_shield(
                    context, st_now, TARGET_SYMBOL
                )
                if in_re_m:
                    return {"status": "HOLD_60S_REENTRY_TIME_SHIELD_IN_MUTEX"}

                # [Case 84 : 뮤텍스 내부 15:29:59 -> 15:30:00 경계 돌파 추격 2차 차단]
                dt_re_mutex = (
                    now_est.astimezone(EST_TZ)
                    if now_est
                    else datetime.now(EST_TZ)
                )
                hm_re_mutex = dt_re_mutex.hour * 100 + dt_re_mutex.minute
                if (
                    sig_type == "BREAKOUT_RELOAD"
                    and is_late_regular_new_cycle_cutoff_window(
                        hm_re_mutex, now_est=dt_re_mutex
                    )
                ):
                    new_pass_cnt = (
                        safe_int(st_now.get("seed_protect_pass_cnt"), 0) + 1
                    )
                    new_day_pass = (
                        safe_int(st_now.get("daily_seed_protect_pass_cnt"), 0)
                        + 1
                    )
                    re_eval_epoch = mark_reentry_monitor_60s_cycle_shield(
                        context=context,
                        symbol=TARGET_SYMBOL,
                        eval_price=fresh_live_p,
                    )
                    await context.ledger.update_state(
                        TARGET_SYMBOL,
                        last_reentry_eval_ts=re_eval_epoch,
                        seed_protect_pass_cnt=new_pass_cnt,
                        daily_seed_protect_pass_cnt=new_day_pass,
                    )
                    return {
                        "status": "L2_ONLY_REENTRY_LATE_BREAKOUT_BLOCKED",
                        "signal_type": "HOLD_LATE_SESSION_BREAKOUT_CUTOFF",
                        "live_price": fresh_live_p,
                        "seed_protect_pass_cnt": new_day_pass,
                    }

                min_upper_tier_p = min(b.book_price for b in now_buckets)
                exec_order_p = max(
                    0.01, math.floor((fresh_live_p + 1e-9) * 100.0) / 100.0
                )
                if min_upper_tier_p > 0.0 and exec_order_p > (
                    min_upper_tier_p + 1e-6
                ):
                    new_pass_cnt = (
                        safe_int(st_now.get("seed_protect_pass_cnt"), 0) + 1
                    )
                    new_day_pass = (
                        safe_int(st_now.get("daily_seed_protect_pass_cnt"), 0)
                        + 1
                    )
                    re_eval_epoch = mark_reentry_monitor_60s_cycle_shield(
                        context=context,
                        symbol=TARGET_SYMBOL,
                        eval_price=fresh_live_p,
                    )
                    await context.ledger.update_state(
                        TARGET_SYMBOL,
                        last_reentry_eval_ts=re_eval_epoch,
                        seed_protect_pass_cnt=new_pass_cnt,
                        daily_seed_protect_pass_cnt=new_day_pass,
                    )
                    return {
                        "status": "L2_ONLY_REENTRY_INVERSION_BLOCKED",
                        "signal_type": "HOLD_PREVENT_INVERSION",
                        "live_price": fresh_live_p,
                        "l2_ceiling_price": min_upper_tier_p,
                        "seed_protect_pass_cnt": new_day_pass,
                    }

                eff_rt_pct_re = resolve_effective_round_trip_fee_rate_pct(
                    state_dict=st_now
                )
                now_sub_re = buckets_from_dicts(st_now.get("sub_buckets", []))
                now_free_cash = max(
                    0.0, safe_float(st_now.get("free_cash_usd"), 0.0)
                )
                now_init_seed = max(
                    100.0,
                    safe_float(
                        st_now.get("initial_seed_usd"), DEFAULT_INITIAL_SEED_USD
                    ),
                )
                now_inj_res = max(
                    0.0, safe_float(st_now.get("injected_reserve_usd"), 0.0)
                )
                now_inv_tot = sum(
                    b.actual_cost_usd for b in now_buckets
                ) + sum(sb.actual_cost_usd for sb in now_sub_re)
                now_core_eq = max(
                    now_init_seed,
                    (now_free_cash + now_inv_tot) - now_inj_res,
                )
                now_p_mode_re = (
                    str(st_now.get("portion_mode") or PORTION_MODE_COMPOUND)
                    .upper()
                    .strip()
                )

                quota_ref_p = max(
                    0.01,
                    safe_float(
                        reentry_sig.get("ref_anchor"),
                        anchor_p if anchor_p > 0.0 else exec_order_p,
                    ),
                )
                target_qty, portion_budget = compute_golden8_quota_qty(
                    anchor_price=quota_ref_p,
                    current_total_equity=now_core_eq,
                    initial_seed_usd=now_init_seed,
                    portion_mode=now_p_mode_re,
                    exec_price=exec_order_p,
                )

                (
                    can_proceed_re,
                    eff_free_cash_re,
                    bp_usd_re,
                    guard_res_re,
                ) = await _check_and_execute_guard30_or_reserve_injection(
                    context=context,
                    st_now=st_now,
                    exec_order_p=exec_order_p,
                    portion_budget=portion_budget,
                    l1_actual_cost_usd=0.0,
                    is_dip_promotion=False,
                    is_vacant_l1_reentry=True,
                    trigger_desc=f"1층 공석 재장전({sig_type})",
                )
                if not can_proceed_re:
                    return {
                        "status": "HOLD_L2_ONLY_GUARD30_WAITING_RESERVE_DEPOSIT",
                        "signal_type": sig_type,
                        "guard_eval": guard_res_re,
                    }

                buy_qty, _est_spent = resolve_affordable_buy_qty(
                    target_qty=target_qty,
                    price_t=exec_order_p,
                    free_cash_usd=eff_free_cash_re,
                    broker_buying_power_usd=(
                        bp_usd_re if bp_usd_re > 0.0 else None
                    ),
                    max_portion_budget_usd=portion_budget,
                    round_trip_fee_rate_pct=eff_rt_pct_re,
                )

                if buy_qty <= 0:
                    re_eval_epoch = mark_reentry_monitor_60s_cycle_shield(
                        context=context,
                        symbol=TARGET_SYMBOL,
                        eval_price=fresh_live_p,
                    )
                    await context.ledger.update_state(
                        TARGET_SYMBOL,
                        last_reentry_eval_ts=re_eval_epoch,
                    )
                    return {"status": "HOLD_L2_ONLY_NO_CASH_FOR_REENTRY"}

                re_eval_epoch = mark_reentry_monitor_60s_cycle_shield(
                    context=context,
                    symbol=TARGET_SYMBOL,
                    eval_price=exec_order_p,
                )
                pending_lot_tag_re = (
                    "REENTRY_1FL_BREAKOUT"
                    if sig_type == "BREAKOUT_RELOAD"
                    else "REENTRY_1FL"
                )
                cid = generate_client_order_id(prefix="RE1FL")
                try:
                    ord_res = await context.api.create_order(
                        symbol=TARGET_SYMBOL,
                        side="BUY",
                        quantity=buy_qty,
                        price=exec_order_p,
                        order_type="LIMIT",
                        time_in_force="DAY",
                        client_order_id=cid,
                        enforce_daymarket_block=True,
                    )
                except Exception as exc:
                    await context.ledger.update_state(
                        TARGET_SYMBOL, last_reentry_eval_ts=re_eval_epoch
                    )
                    logger.warning(
                        "상단 그리드 보유 중 60초 주기 현재가 지정가 1층(REENTRY_1FL) 재장전 주문 예외: %s",
                        exc,
                    )
                    return {"status": "ORDER_ERROR", "error": str(exc)}

                oid = str(ord_res.get("orderId") or "").strip()
                await context.ledger.update_state(
                    TARGET_SYMBOL,
                    l1_target_quota_qty=buy_qty,
                    buy_order_id=oid,
                    client_order_id=cid,
                    ordered_qty=buy_qty,
                    buy_price=exec_order_p,
                    pending_portion_budget=portion_budget,
                    pending_lot_type=pending_lot_tag_re,
                    pending_step_up_min_price=0.0,
                    pending_sub_step_up_min_price=0.0,
                    last_modify_mono=time.monotonic(),
                    last_reentry_eval_ts=re_eval_epoch,
                )
                context.wakeup_event.set()
                logger.info(
                    "🔥 [SOXL 상단 %d개층 보유 중 60초 주기 현재가 지정가 1층 재장전(%s) 발주] %d주 @ 지정가 $%.2f <= 2층상한 $%.2f (1회예산 $%.2f · 직전익절 $%.2f · 이평 $%.2f · orderId=%s)",
                    len(now_buckets),
                    sig_type,
                    buy_qty,
                    exec_order_p,
                    min_upper_tier_p,
                    portion_budget,
                    quota_ref_p,
                    upper_wma_p,
                    oid,
                )
                return {
                    "status": "L2_HELD_HYBRID_REAL_1FL_ORDERED",
                    "signal_type": sig_type,
                    "orderId": oid,
                    "qty": buy_qty,
                    "price": exec_order_p,
                    "l2_ceiling_price": min_upper_tier_p,
                }

    if not buckets or not has_active_l1:
        return {
            "status": "WAIT_HOLDINGS_RECONCILE_SYNC",
            "ledger_grid_qty": len(buckets),
            "broker_qty": h_qty,
        }

    # -----------------------------------------------------------------------
    # [분기 B-0 · Case 77, Case 78 & Case 88 : 본 그리드 활성 1층 부분 체결 미체결 잔량(rem_quota_qty > 0) 존재 시]
    # -> 원장 가용현금(free_cash)이 최소 1주 매수 비용 이상일 때만 진입하고, 부족 시 60초 쿨다운 쉴드 각인!
    # -----------------------------------------------------------------------
    l1_target_q = max(
        buckets[0].qty, safe_int(st.get("l1_target_quota_qty"), 0)
    )
    rem_quota_qty = max(0, l1_target_q - buckets[0].qty)
    l1_book_p = round(buckets[0].book_price, 2)
    one_share_min_cost = live_p * (1.0 + eff_rt_pct / 100.0)

    if (
        rem_quota_qty > 0
        and live_p <= (l1_book_p + 1e-6)
        and free_cash >= one_share_min_cost
    ):
        async with context.in_memory_ordering_lock:
            async with context.dual_strike_mutex:
                st_now = context.ledger.get_state(TARGET_SYMBOL)
                if str(st_now.get("buy_order_id") or "").strip() or str(
                    st_now.get("sell_order_id") or ""
                ).strip():
                    return {"status": "ALREADY_ORDERING_IN_MUTEX"}

                now_buckets = buckets_from_dicts(st_now.get("buckets", []))
                if not now_buckets or not has_active_l1_bucket(now_buckets):
                    return {"status": "L1_STATE_CHANGED_IN_MUTEX"}

                in_s_sh, _ = is_within_post_sell_time_shield(
                    context, st_now, TARGET_SYMBOL
                )
                in_b_sh, _ = is_within_post_buy_time_shield(
                    context, st_now, TARGET_SYMBOL
                )
                in_res_m, _ = is_within_reserve_deposit_check_shield(
                    context, st_now, TARGET_SYMBOL
                )
                if in_s_sh or in_b_sh or in_res_m:
                    return {"status": "HOLD_60S_TIME_SHIELD_IN_MUTEX"}

                now_target_q = max(
                    now_buckets[0].qty,
                    safe_int(st_now.get("l1_target_quota_qty"), 0),
                )
                now_rem_qty = max(0, now_target_q - now_buckets[0].qty)
                now_l1_book_p = round(now_buckets[0].book_price, 2)

                if now_rem_qty > 0:
                    fresh_live_p = await _fetch_fresh_current_soxl_price(
                        context, fallback_price=live_p
                    )
                    if fresh_live_p > 0.0 and fresh_live_p <= (
                        now_l1_book_p + 1e-6
                    ):
                        eff_rt_pct_top = resolve_effective_round_trip_fee_rate_pct(
                            state_dict=st_now
                        )
                        cur_lim_p = (
                            math.floor((fresh_live_p + 1e-9) * 100.0) / 100.0
                        )
                        exec_order_p = max(
                            0.01, min(cur_lim_p, now_l1_book_p)
                        )
                        topup_budget = round(
                            float(now_rem_qty) * now_l1_book_p, 4
                        )
                        now_free_cash = max(
                            0.0, safe_float(st_now.get("free_cash_usd"), 0.0)
                        )
                        one_share_top_cost = exec_order_p * (
                            1.0 + eff_rt_pct_top / 100.0
                        )
                        if now_free_cash < one_share_top_cost:
                            mark_reserve_deposit_check_shield(
                                context=context,
                                symbol=TARGET_SYMBOL,
                                clear_shield=False,
                            )
                            return {
                                "status": "HOLD_TOPUP_INSUFFICIENT_FREE_CASH",
                                "free_cash_usd": now_free_cash,
                            }

                        raw_bp_top = await context.api.get_buying_power_usd(
                            safety_buffer_pct=0.2
                        )
                        if (
                            raw_bp_top <= 0.0
                            and now_free_cash >= one_share_top_cost
                        ):
                            await asyncio.sleep(0.25)
                            raw_bp_top = await context.api.get_buying_power_usd(
                                safety_buffer_pct=0.2
                            )

                        if raw_bp_top < one_share_top_cost:
                            mark_reserve_deposit_check_shield(
                                context=context,
                                symbol=TARGET_SYMBOL,
                                clear_shield=False,
                            )
                            return {
                                "status": "HOLD_TOPUP_INSUFFICIENT_BROKER_BP",
                                "broker_bp_usd": raw_bp_top,
                                "free_cash_usd": now_free_cash,
                            }

                        buy_qty_top, _ = resolve_affordable_buy_qty(
                            target_qty=now_rem_qty,
                            price_t=exec_order_p,
                            free_cash_usd=now_free_cash,
                            broker_buying_power_usd=raw_bp_top,
                            max_portion_budget_usd=topup_budget,
                            round_trip_fee_rate_pct=eff_rt_pct_top,
                        )
                        if buy_qty_top > 0:
                            eff_topup_budget = round(
                                float(buy_qty_top) * now_l1_book_p, 4
                            )
                            cid = generate_client_order_id(prefix="TOP1FL")
                            try:
                                ord_res = await context.api.create_order(
                                    symbol=TARGET_SYMBOL,
                                    side="BUY",
                                    quantity=buy_qty_top,
                                    price=exec_order_p,
                                    order_type="LIMIT",
                                    time_in_force="DAY",
                                    client_order_id=cid,
                                    enforce_daymarket_block=True,
                                )
                                oid = str(
                                    ord_res.get("orderId") or ""
                                ).strip()
                                await context.ledger.update_state(
                                    TARGET_SYMBOL,
                                    l1_target_quota_qty=now_target_q,
                                    buy_order_id=oid,
                                    client_order_id=cid,
                                    ordered_qty=buy_qty_top,
                                    buy_price=exec_order_p,
                                    pending_portion_budget=eff_topup_budget,
                                    pending_lot_type="TOPUP_1FL",
                                    pending_step_up_min_price=0.0,
                                    pending_sub_step_up_min_price=0.0,
                                    last_modify_mono=time.monotonic(),
                                )
                                context.wakeup_event.set()
                                logger.info(
                                    "🎯 [Case 78 SOXL 1.5초 모니터 1층 단가($%.2f) 재도래 포착 -> 미체결 잔량(TOPUP_1FL) 지정가 발주] +%d주 @ 지정가 $%.2f (기보유 %d주 / 목표 %d주 · 60초 지정가 대기 개시 · orderId=%s)",
                                    now_l1_book_p,
                                    buy_qty_top,
                                    exec_order_p,
                                    now_buckets[0].qty,
                                    now_target_q,
                                    oid,
                                )
                                return {
                                    "status": "L1_PARTIAL_TOPUP_ORDERED",
                                    "orderId": oid,
                                    "qty": buy_qty_top,
                                    "price": exec_order_p,
                                    "l1_cur_qty": now_buckets[0].qty,
                                    "l1_target_quota_qty": now_target_q,
                                }
                            except Exception as exc:
                                mark_reserve_deposit_check_shield(
                                    context=context,
                                    symbol=TARGET_SYMBOL,
                                    clear_shield=False,
                                )
                                logger.warning(
                                    "Case 78 1층 미체결 잔량(TOPUP_1FL) 지정가 주문 예외(60초 쿨다운): %s",
                                    exc,
                                )
                                return {
                                    "status": "TOPUP_ORDER_ERROR",
                                    "error": str(exc),
                                }
                        else:
                            mark_reserve_deposit_check_shield(
                                context=context,
                                symbol=TARGET_SYMBOL,
                                clear_shield=False,
                            )

    # -----------------------------------------------------------------------
    # [분기 B-2 · Case 60, Case 72, Case 76, Case 77, Case 87, Case 88 & Case 91 : 본 그리드 활성 1층 보유 중 (has_active_l1_bucket(buckets) == True)]
    # -> 04:07 EST 기점 10분 고정 매수 게이트 신규 버킷 도래 시 정적 기억 최저가 및 최고 도달 회차(cycle_ratchet_max_lots) 잠금 기준
    #    4단 와이드 OR STEP2X_15PCT_C20 스텝업 추매 판정! (본 그리드 대기/패스 시 Default-ON 3층 서브 그리드 엔진 연속 가동)
    # -----------------------------------------------------------------------
    is_gate_open, cur_bucket_id, today_str, b_info = (
        evaluate_buy_gate_bucket_status(
            now_est=dt_now,
            buy_interval_min=buy_interval_min,
            last_evaluated_bucket_id=safe_int(
                st.get("last_evaluated_buy_bucket_id"), -1
            ),
            last_evaluated_date=str(st.get("last_evaluated_date") or ""),
        )
    )

    if not is_gate_open:
        sub_res_wait = await _execute_sub_grid_buy_engine_plugin(
            context=context,
            holdings=holdings,
            prices=prices,
            dt_now=dt_now,
            live_p=live_p,
        )
        if isinstance(sub_res_wait, dict) and str(
            sub_res_wait.get("status") or ""
        ).endswith("_ORDERED"):
            return sub_res_wait

        if rem_quota_qty > 0:
            return {
                "status": "MONITORING_1_5S_L1_TOPUP_PRICE",
                "l1_cur_qty": buckets[0].qty,
                "l1_target_quota_qty": l1_target_q,
                "l1_rem_quota_qty": rem_quota_qty,
                "l1_book_price": l1_book_p,
                "live_price": live_p,
            }
        return {
            "status": "WAIT_NEXT_BUY_GATE",
            "next_gate": b_info.get("next_gate_hm_str", ""),
        }

    fresh_live_p = await _fetch_fresh_current_soxl_price(
        context, fallback_price=live_p
    )
    if fresh_live_p <= 0.0:
        return {"status": "NO_FRESH_LIVE_PRICE"}

    held_lots = sum(b.lot_count for b in buckets)
    ratchet_max_lots = max(
        held_lots, safe_int(st.get("cycle_ratchet_max_lots"), 0)
    )
    drop_buy_pct, _, _ = get_golden8_prog_thresholds(
        held_lots=held_lots,
        threshold_mode=threshold_mode,
        cycle_ratchet_max_lots=ratchet_max_lots,
    )

    anchor_p = safe_float(st.get("anchor_price"), buckets[0].book_price)
    cycle_min_p = safe_float(st.get("cycle_min_buy_price"), anchor_p)
    eff_step_drop = (
        0.0 if unlock_mode in ("STATIC", "NONE", "OFF") else STEP_UP_2X_DROP_PCT
    )

    dip_eval = evaluate_step_up_2x_dip_signal(
        live_price=fresh_live_p,
        buckets=buckets,
        anchor_price=anchor_p,
        cycle_min_buy_price=cycle_min_p,
        drop_buy_pct=drop_buy_pct,
        free_cash_usd=free_cash,
        realized_equity_usd=budget_base_eq,
        step_up_drop_pct=eff_step_drop,
        min_cash_ratio=STEP_UP_2X_MIN_CASH_RATIO,
        min_rebound_mult=STEP_UP_2X_MIN_REBOUND_MULT,
        max_tiers_for_unlock=STEP_UP_2X_MAX_TIERS,
    )
    ref_buy_anchor = safe_float(
        dip_eval.get("ref_static_anchor"), buckets[0].book_price
    )
    chg_for_buy_pct = safe_float(dip_eval.get("chg_static_pct"), 0.0)
    lot_tag = "DIP_1FL"

    if not bool(dip_eval.get("should_buy")):
        if bool(st.get("waiting_reserve_deposit", False)):
            mark_reserve_deposit_check_shield(
                context=context, symbol=TARGET_SYMBOL, clear_shield=False
            )
            sub_res_dep = await _execute_sub_grid_buy_engine_plugin(
                context=context,
                holdings=holdings,
                prices=prices,
                dt_now=dt_now,
                live_p=fresh_live_p,
            )
            if isinstance(sub_res_dep, dict) and str(
                sub_res_dep.get("status") or ""
            ).endswith("_ORDERED"):
                return sub_res_dep
            return {
                "status": "HOLD_WAITING_RESERVE_DEPOSIT_PRICE_REBOUND",
                "trigger_tag": dip_eval.get("trigger_tag", "HOLD"),
                "ref_buy_anchor": round(ref_buy_anchor, 4),
                "chg_pct": round(chg_for_buy_pct, 2),
                "required_drop_pct": drop_buy_pct,
            }

        new_pass_cnt = safe_int(st.get("seed_protect_pass_cnt"), 0) + 1
        new_day_pass = safe_int(st.get("daily_seed_protect_pass_cnt"), 0) + 1
        await context.ledger.update_state(
            TARGET_SYMBOL,
            last_evaluated_buy_bucket_id=cur_bucket_id,
            last_evaluated_date=today_str,
            seed_protect_pass_cnt=new_pass_cnt,
            daily_seed_protect_pass_cnt=new_day_pass,
        )

        # 🛡️ [Case 88 핵심 : 본 그리드가 10분 게이트를 패스한 즉시 Default-ON 3층 서브 그리드 엔진 가동!]
        sub_res_gate = await _execute_sub_grid_buy_engine_plugin(
            context=context,
            holdings=holdings,
            prices=prices,
            dt_now=dt_now,
            live_p=fresh_live_p,
        )
        if isinstance(sub_res_gate, dict) and str(
            sub_res_gate.get("status") or ""
        ).endswith("_ORDERED"):
            return sub_res_gate

        return {
            "status": "SEED_PROTECT_PASSED",
            "trigger_tag": dip_eval.get("trigger_tag", "HOLD"),
            "ref_buy_anchor": round(ref_buy_anchor, 4),
            "chg_pct": round(chg_for_buy_pct, 2),
            "required_drop_pct": drop_buy_pct,
            "cycle_ratchet_max_lots": ratchet_max_lots,
            "step_up_eligible": bool(dip_eval.get("step_up_eligible", False)),
            "stepped_min_price": safe_float(
                dip_eval.get("stepped_min_price"), 0.0
            ),
            "seed_protect_pass_cnt": new_day_pass,
            "sub_grid_eval": sub_res_gate,
        }

    async with context.in_memory_ordering_lock:
        async with context.dual_strike_mutex:
            st_now = context.ledger.get_state(TARGET_SYMBOL)
            if str(st_now.get("buy_order_id") or "").strip() or str(
                st_now.get("sell_order_id") or ""
            ).strip():
                return {"status": "ALREADY_ORDERING_IN_MUTEX"}

            now_buckets = buckets_from_dicts(st_now.get("buckets", []))
            if not now_buckets or not has_active_l1_bucket(now_buckets):
                return {"status": "L1_STATE_CHANGED_IN_MUTEX"}

            gate_open_m, _, _, _ = evaluate_buy_gate_bucket_status(
                now_est=dt_now,
                buy_interval_min=buy_interval_min,
                last_evaluated_bucket_id=safe_int(
                    st_now.get("last_evaluated_buy_bucket_id"), -1
                ),
                last_evaluated_date=str(
                    st_now.get("last_evaluated_date") or ""
                ),
            )
            if not gate_open_m:
                return {"status": "BUCKET_ALREADY_EVALUATED_IN_MUTEX"}

            in_s_sh, _ = is_within_post_sell_time_shield(
                context, st_now, TARGET_SYMBOL
            )
            in_b_sh, _ = is_within_post_buy_time_shield(
                context, st_now, TARGET_SYMBOL
            )
            if in_s_sh or in_b_sh:
                return {"status": "HOLD_60S_TIME_SHIELD_IN_MUTEX"}

            eff_rt_pct_dip = resolve_effective_round_trip_fee_rate_pct(
                state_dict=st_now
            )
            now_held_lots = sum(b.lot_count for b in now_buckets)
            now_ratchet_lots = max(
                now_held_lots, safe_int(st_now.get("cycle_ratchet_max_lots"), 0)
            )
            now_drop_pct, _, _ = get_golden8_prog_thresholds(
                held_lots=now_held_lots,
                threshold_mode=threshold_mode,
                cycle_ratchet_max_lots=now_ratchet_lots,
            )
            now_sub_dip = buckets_from_dicts(st_now.get("sub_buckets", []))
            now_free_cash = max(0.0, safe_float(st_now.get("free_cash_usd"), 0.0))
            now_init_seed = max(
                100.0,
                safe_float(
                    st_now.get("initial_seed_usd"), DEFAULT_INITIAL_SEED_USD
                ),
            )
            now_inj_res = max(
                0.0, safe_float(st_now.get("injected_reserve_usd"), 0.0)
            )
            now_inv_tot = sum(
                b.actual_cost_usd for b in now_buckets
            ) + sum(sb.actual_cost_usd for sb in now_sub_dip)
            now_core_eq = max(
                now_init_seed,
                (now_free_cash + now_inv_tot) - now_inj_res,
            )
            now_p_mode_dip = (
                str(st_now.get("portion_mode") or PORTION_MODE_COMPOUND)
                .upper()
                .strip()
            )
            now_budget_base_eq = resolve_portion_budget_base_equity(
                initial_seed_usd=now_init_seed,
                core_equity_usd=now_core_eq,
                portion_mode=now_p_mode_dip,
            )

            now_dip_eval = evaluate_step_up_2x_dip_signal(
                live_price=fresh_live_p,
                buckets=now_buckets,
                anchor_price=safe_float(
                    st_now.get("anchor_price"), now_buckets[0].book_price
                ),
                cycle_min_buy_price=safe_float(
                    st_now.get("cycle_min_buy_price"), 0.0
                ),
                drop_buy_pct=now_drop_pct,
                free_cash_usd=now_free_cash,
                realized_equity_usd=now_budget_base_eq,
                step_up_drop_pct=eff_step_drop,
                min_cash_ratio=STEP_UP_2X_MIN_CASH_RATIO,
                min_rebound_mult=STEP_UP_2X_MIN_REBOUND_MULT,
                max_tiers_for_unlock=STEP_UP_2X_MAX_TIERS,
            )
            if not bool(now_dip_eval.get("should_buy")):
                return {"status": "DIP_SIGNAL_CHANGED_IN_MUTEX"}

            is_step_up_unlock = bool(
                now_dip_eval.get("is_step_up_unlock", False)
            )
            trigger_tag = str(
                now_dip_eval.get("trigger_tag") or "STATIC_NEW_LOW"
            )
            quota_ref_p = max(
                0.01,
                safe_float(
                    now_dip_eval.get("quota_ref_price"), ref_buy_anchor
                ),
            )
            stepped_min_p = safe_float(
                now_dip_eval.get("stepped_min_price"), 0.0
            )

            if is_step_up_unlock and stepped_min_p > 0.0:
                max_trigger_p = (
                    math.floor((stepped_min_p + 1e-9) * 100.0) / 100.0
                )
            else:
                max_trigger_p = (
                    math.floor(
                        (
                            ref_buy_anchor * (1.0 + now_drop_pct / 100.0)
                            + 1e-9
                        )
                        * 100.0
                    )
                    / 100.0
                )
            cur_limit_p = (
                math.floor((fresh_live_p + 1e-9) * 100.0) / 100.0
            )
            exec_order_p = max(0.01, min(cur_limit_p, max_trigger_p))

            target_qty, portion_budget = compute_golden8_quota_qty(
                anchor_price=quota_ref_p,
                current_total_equity=now_core_eq,
                initial_seed_usd=now_init_seed,
                portion_mode=now_p_mode_dip,
                exec_price=exec_order_p,
            )

            (
                can_proceed_dip,
                eff_free_cash_dip,
                bp_usd_dip,
                guard_res_dip,
            ) = await _check_and_execute_guard30_or_reserve_injection(
                context=context,
                st_now=st_now,
                exec_order_p=exec_order_p,
                portion_budget=portion_budget,
                l1_actual_cost_usd=now_buckets[0].actual_cost_usd,
                is_dip_promotion=True,
                is_vacant_l1_reentry=False,
                trigger_desc=f"{now_held_lots + 1}회차 추매({trigger_tag})",
            )
            if not can_proceed_dip:
                return {
                    "status": "HOLD_DIP_GUARD30_WAITING_RESERVE_DEPOSIT",
                    "trigger_tag": trigger_tag,
                    "guard_eval": guard_res_dip,
                }

            buy_qty, _est_spent = resolve_affordable_buy_qty(
                target_qty=target_qty,
                price_t=exec_order_p,
                free_cash_usd=eff_free_cash_dip,
                broker_buying_power_usd=(
                    bp_usd_dip if bp_usd_dip > 0.0 else None
                ),
                max_portion_budget_usd=portion_budget,
                round_trip_fee_rate_pct=eff_rt_pct_dip,
            )

            if buy_qty <= 0:
                return {"status": "CASH_EXHAUSTED_SKIP"}

            cid_prefix = (
                f"U{now_held_lots + 1}L"
                if is_step_up_unlock
                else f"B{now_held_lots + 1}L"
            )
            cid = generate_client_order_id(prefix=cid_prefix)
            try:
                ord_res = await context.api.create_order(
                    symbol=TARGET_SYMBOL,
                    side="BUY",
                    quantity=buy_qty,
                    price=exec_order_p,
                    order_type="LIMIT",
                    time_in_force="DAY",
                    client_order_id=cid,
                    enforce_daymarket_block=True,
                )
            except Exception as exc:
                logger.error(
                    "SOXL 10분 게이트(%s) 현재가 지정가 그리드 추매 주문 발사 예외: %s",
                    trigger_tag,
                    exc,
                )
                return {"status": "BUY_ORDER_ERROR", "error": str(exc)}

            oid = str(ord_res.get("orderId") or "").strip()
            await context.ledger.update_state(
                TARGET_SYMBOL,
                l1_target_quota_qty=buy_qty,
                buy_order_id=oid,
                client_order_id=cid,
                ordered_qty=buy_qty,
                buy_price=exec_order_p,
                pending_portion_budget=portion_budget,
                pending_lot_type=lot_tag,
                pending_step_up_min_price=(
                    round(stepped_min_p, 4) if is_step_up_unlock else 0.0
                ),
                pending_sub_step_up_min_price=0.0,
                last_evaluated_buy_bucket_id=cur_bucket_id,
                last_evaluated_date=today_str,
                last_modify_mono=time.monotonic(),
            )
            context.wakeup_event.set()
            if is_step_up_unlock:
                logger.info(
                    "🔓 [Case 76 SOXL 스텝업 저가 해금(%s) 추매 발주] %d주 @ 지정가 $%.2f (1층 $%.2f 대비 -15%% 해금가 $%.2f · 구저가 $%.2f[%.2fx] · 현금비중 %.1f%% · orderId=%s)",
                    trigger_tag,
                    buy_qty,
                    exec_order_p,
                    now_buckets[0].book_price,
                    stepped_min_p,
                    ref_buy_anchor,
                    safe_float(now_dip_eval.get("rebound_mult"), 2.0),
                    safe_float(now_dip_eval.get("cash_ratio_pct"), 20.0),
                    oid,
                )
            else:
                logger.info(
                    "🔵 [SOXL %d회차(잠금%d회차 · 단차 %.1f%%) 현재가 지정가 그리드 추매 발주] %d주 @ 지정가 $%.2f (기억저가 $%.2f 대비 %.2f%% · orderId=%s)",
                    now_held_lots + 1,
                    now_ratchet_lots,
                    now_drop_pct,
                    buy_qty,
                    exec_order_p,
                    ref_buy_anchor,
                    chg_for_buy_pct,
                    oid,
                )
            return {
                "status": "QUOTA_DIP_BUY_ORDERED",
                "trigger_tag": trigger_tag,
                "is_step_up_unlock": is_step_up_unlock,
                "orderId": oid,
                "qty": buy_qty,
                "price": exec_order_p,
                "ref_buy_anchor": round(quota_ref_p, 4),
                "chg_pct": round(chg_for_buy_pct, 2),
                "drop_threshold_pct": now_drop_pct,
                "cycle_ratchet_max_lots": now_ratchet_lots,
            }


# 하위 호환 별칭 (외부 모듈에서 구 함수명으로 호출하더라도 신규 게이트 엔진으로 안전 직결)
execute_premarket_vwap_sniper_plugin = execute_seed_protected_buy_gate_plugin
