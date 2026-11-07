# -*- coding: utf-8 -*-
"""
# MODIFIED: quant_indicators_plugin.py
# 4bot 2번 v2.4.0 (2026-11-07): 원작 c4ad8d6 Case 93 [모의] 암살자용 지표 추가 — QQQ 지표(compute_qqq_macro_metrics_1m)·전일종가/04:07프리시가/프리VWAP 래치·단기 변화율 (기존 키 값은 그대로, 새 키만 추가)
# 4bot 2번 v2.2.0 (2026-11-05): 원작 254eef5(c1b9b27) 골든포켓 폐기 이식 + 기존 골든포켓 → 지하층(basement_pocket) 보관·목표가 매도 전용 (신규 매수 없음)
# 4bot 2번 v2.0.0 (2026-11-03): 원작 d7b3a66 이식 + 사용자 수정 재적용 (단일파일 구조 유지)
인피니트 스노우볼 (Infinite Snowball) v3.0 — 순수 롱(SOXL) 매수 04:07 ~ 16:00 EST 제한
(정규장 마감 30분 전 15:30 ~ 16:00 EST 본·서브 그리드 0주 새 사이클 첫 1층 진입 및 상단층 보유 중 1층 공석 +1.0% 돌파 추격 동시 차단 ·
2층 단가 이하 -1.0% 눌림목 재장전 및 10분 게이트 추매/잔량보충 100% 허용 · Case 84, Case 88) &
익절 매도 24시간 전 세션(프리마켓 + 정규장 + 애프터마켓 + 데이마켓 · 방안 C 오버나이트 통합이평 사수) 확장 오버나이트 지층관리 스나이퍼
시계열 100% 벡터화 지표 엔진 · 실시간 틱 인메모리 1분봉 자체 합성기(_LIVE_1M_BAR_STORE) 및
10분 고정 매수 게이트 버킷 산출(본 그리드 및 Default-ON 3층 서브 그리드 독립 평가 지원) 코어 모듈 (Step 03 / 13)
- 제4헌법 & Case 01, Case 79, Case 83, Case 84 & Case 88:
  1) 모든 시계열 및 세션 경계 연산은 미국 동부 시간(EST_TZ = ZoneInfo('America/New_York')) 단일 소스 락온
  2) 매수 허용 시간창(is_active_buy_window : 평일 04:07 ~ 16:00 EST)과
     익절 매도 허용 시간창(is_active_sell_window : 04:00 ~ 04:06 EST 오프닝 안정화 및 주말 휴장 외
     프리마켓 · 정규장 · 애프터마켓[16:00 ~ 19:59 EST] · 데이마켓[20:00 ~ 03:59 EST] 전 구간) 엄격 분리!
  3) 금요일 애프터마켓(16:00 ~ 19:59 EST) 익절 매도를 허용하기 위해 주말 휴장 구간을
     금요일 20:00 EST ~ 일요일 17:59 EST 로 제어 (일요일 18:00 EST 이후 월요일 데이마켓 정상 개방)
  4) API 1분봉(공식 거래량 V · 시가 O 우선 보존) + 실시간 1.5초 틱 인메모리 1분봉(고가 H · 저가 L 극단값 보존)
     하이브리드 무손실 벡터화 병합(_sync_api_candles_into_memory_store 경합 방어) ·
     Wilder's RSI(14) O(1) 상수 시간 무부하 합성 탑재!
  5) 🛡️ [Case 84 & Case 88] 정규장 마감 30분 전(is_late_regular_new_cycle_cutoff_window : 평일 15:30 ~ 16:00 EST) 판별기 탑재
     - 기보유 지층(본·서브 1층 이상)의 10분 게이트 신저가/스텝업/저가해금 추매(DIP_1FL / SUB_DIP_1FL),
       1층 미체결 잔량 보충(TOPUP_1FL / SUB_TOPUP_1FL), 상단층 보유 중 1층 공석 시 2층 단가 이하 눌림목(-1.00%, PULLBACK_RELOAD) 재장전은 100% 허용하되,
       본·서브 0주 상태(사이클 종료 상태)에서 새 사이클 첫 1층(REENTRY_1FL / SUB_REENTRY_1FL)으로 고점 진입하는 것과
       상단층 보유 중 1층 공석 상태에서 +1.00% 상승돌파(BREAKOUT_RELOAD)로 추격 진입하는 것을 동시 원천 차단!
- Case 36, Case 64 & Case 88: 04:07 ~ 16:00 EST 구간 10분 고정 매수 게이트(LOCKED_BUY_INTERVAL_MIN = 10) 버킷 산출 및
  본 그리드·서브 그리드 각각의 동일 버킷 내 중복 평가 원천 차단(evaluate_buy_gate_bucket_status)
- 벡터화 강제: Pandas DataFrame / NumPy 배열 연산 시 for 루프를 100% 배제하고 벡터화 수식으로만
  프리장(04:00 ~ 09:29 EST) / 정규장(09:30 ~ 16:00 EST) 누적 VWAP, 고/저가 진폭, 5일 이동평균(5MA) 진폭 기반
  예상 변동 밴드, 실시간 하이킨 아시(Heikin-Ashi) 양/음봉 배지 및 Wilder's RSI(14)를 고속 산출한다.
"""

from __future__ import annotations

import logging
import math
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from toss_api import (
    EST_TZ,
    LOCKED_BUY_INTERVAL_MIN,
    NEW_CYCLE_BUY_CUTOFF_HM as _API_NEW_CYCLE_BUY_CUTOFF_HM,
    TARGET_SYMBOL,
    safe_float,
    safe_int,
)

logger = logging.getLogger("toss_sniper.quant_indicators_plugin")

# 04:07 EST 기준 분(minute of day = 4 * 60 + 7 = 247) 및 16:00 EST 마감 분(16 * 60 = 960) 0칸 표준 정렬
GATE_START_MIN_OF_DAY: int = 4 * 60 + 7   # 247 (04:07 EST)
GATE_END_MIN_OF_DAY: int = 16 * 60        # 960 (16:00 EST)
REGULAR_START_MIN_OF_DAY: int = 9 * 60 + 30  # 570 (09:30 EST)

# [Case 84 & Case 88]: 정규장 마감 30분 전(15:30 ~ 16:00 EST) 본·서브 0주 새 사이클 첫 1층 진입 및 1층 공석 +1.0% 돌파 추격 동시 차단 기준 시각(HHMM)
NEW_CYCLE_BUY_CUTOFF_HM: int = safe_int(_API_NEW_CYCLE_BUY_CUTOFF_HM, 1530)

# 브로커 1분봉 차트 API 지연/결측 시에도 실시간 1.5초 현재가 틱으로 1분봉을 자체 축적하는 인메모리 링버퍼
_LIVE_1M_BAR_LOCK = threading.RLock()
_LIVE_1M_BAR_STORE: Dict[str, List[Dict[str, Any]]] = {TARGET_SYMBOL: []}
_MAX_MEMORY_1M_BARS: int = 360

# [4bot v2.4.0 · 원작 c4ad8d6 Case 93 · 암살자 전용] [Case 93]: 정규장 진입 및 장 마감 후에도 당일 한번 진성으로 확보된 전일 정규장 종가 · 04:07 프리장 시가 · 프리장 누적 VWAP을 보존하는 당일 인메모리 래치
_DAILY_ANCHOR_LOCK = threading.RLock()
_DAILY_SESSION_ANCHOR_STORE: Dict[Tuple[str, str], Dict[str, Any]] = {}


def _is_collapsed_anchor_triplet(
    prev_c: float, pre_o: float, pre_v: float
) -> bool:
    """
    전일 정규장 종가(prev_c), 당일 04:07 프리장 시가(pre_o), 프리장 누적 VWAP(pre_v) 3개 값이
    모두 양수이면서 동일한 단일 현재가 폴백값으로 뭉개져 있는지 판별한다.
    """
    if prev_c <= 0.0 or pre_o <= 0.0 or pre_v <= 0.0:
        return False
    return bool(
        abs(prev_c - pre_o) < 1e-6 and abs(pre_v - prev_c) < 1e-6
    )


def _get_daily_anchor_latch(symbol: str, target_date: str) -> Dict[str, Any]:
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    d_key = str(target_date or "").strip()
    if not d_key:
        return {}
    with _DAILY_ANCHOR_LOCK:
        saved = _DAILY_SESSION_ANCHOR_STORE.get((sym, d_key))
        if not isinstance(saved, dict):
            return {}
        s_prev = safe_float(saved.get("prev_reg_close"), 0.0)
        s_open = safe_float(saved.get("pre_open_price"), 0.0)
        s_stats = saved.get("pre_stats")
        s_vwap = (
            safe_float(s_stats.get("vwap"), 0.0)
            if isinstance(s_stats, dict)
            else 0.0
        )
        if _is_collapsed_anchor_triplet(s_prev, s_open, s_vwap) and not bool(
            saved.get("verified_distinct", False)
        ):
            _DAILY_SESSION_ANCHOR_STORE.pop((sym, d_key), None)
            return {}
        return dict(saved)


def _update_daily_anchor_latch(
    symbol: str,
    target_date: str,
    prev_reg_close: float = 0.0,
    pre_open_price: float = 0.0,
    pre_stats: Optional[Dict[str, float]] = None,
    verified_distinct: bool = False,
) -> None:
    """
    # MODIFIED [Case 93 : 오직 실제 차트(1d/1m)에서 확인된 진성 앵커만 당일 인메모리 래치에 저장]:
    현재가나 정규장 시가/정규장 VWAP 폴백으로 채워진 가짜 데이터는 래치에 절대 저장하지 않는다.
    """
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    d_key = str(target_date or "").strip()
    if not d_key:
        return

    with _DAILY_ANCHOR_LOCK:
        if len(_DAILY_SESSION_ANCHOR_STORE) > 12:
            oldest_keys = sorted(_DAILY_SESSION_ANCHOR_STORE.keys())[:-6]
            for ok in oldest_keys:
                _DAILY_SESSION_ANCHOR_STORE.pop(ok, None)

        entry = _DAILY_SESSION_ANCHOR_STORE.setdefault((sym, d_key), {})
        if prev_reg_close > 0.0:
            entry["prev_reg_close"] = round(float(prev_reg_close), 4)
        if pre_open_price > 0.0:
            entry["pre_open_price"] = round(float(pre_open_price), 4)
        if (
            isinstance(pre_stats, dict)
            and safe_float(pre_stats.get("vwap"), 0.0) > 0.0
        ):
            entry["pre_stats"] = dict(pre_stats)
        if verified_distinct:
            entry["verified_distinct"] = True




# ---------------------------------------------------------------------------
# [핵심 0] 인메모리 실시간 1분봉 자체 합성기 및 API 1분봉 하이브리드 병합기
# ---------------------------------------------------------------------------
def _record_live_tick_to_memory_bar(
    symbol: str,
    live_price: float,
    now_est: Optional[datetime] = None,
) -> Tuple[str, int]:
    """
    실시간 1.5초 현재가 틱 기반 인메모리 1분봉 자체 합성기:
    매 1.5초 루프 또는 /avwap 조회 시 유입되는 실시간 현재가(live_price)를
    미국 동부 시간(EST_TZ) 분 단위 버킷(YYYY-MM-DDTHH:MM:00±HH:MM)으로 축적한다.
    반환값: (현재 분 키 문자열 cur_min_key, 인메모리 누적 분봉 개수)
    """
    dt = now_est.astimezone(EST_TZ) if now_est else datetime.now(EST_TZ)
    dt_min = dt.replace(second=0, microsecond=0)
    min_key = dt_min.strftime("%Y-%m-%d %H:%M")
    iso_ts = dt_min.isoformat()
    lp = round(safe_float(live_price, 0.0), 4)
    sym = str(symbol or TARGET_SYMBOL).upper().strip()

    if lp <= 0.0:
        with _LIVE_1M_BAR_LOCK:
            bars = _LIVE_1M_BAR_STORE.get(sym, [])
            return min_key, len(bars)

    with _LIVE_1M_BAR_LOCK:
        bars = _LIVE_1M_BAR_STORE.setdefault(sym, [])
        if bars and str(bars[-1].get("_min_key") or "") == min_key:
            last_b = bars[-1]
            prev_h = safe_float(last_b.get("highPrice"), lp)
            prev_l = safe_float(last_b.get("lowPrice"), lp)
            last_b["highPrice"] = round(max(prev_h, lp), 4)
            last_b["lowPrice"] = round(
                min(prev_l, lp) if prev_l > 0.0 else lp, 4
            )
            last_b["closePrice"] = lp
        else:
            bars.append(
                {
                    "_min_key": min_key,
                    "timestamp": iso_ts,
                    "openPrice": lp,
                    "highPrice": lp,
                    "lowPrice": lp,
                    "closePrice": lp,
                    "volume": 1.0,
                    "currency": "USD",
                }
            )
            if len(bars) > _MAX_MEMORY_1M_BARS:
                del bars[: len(bars) - _MAX_MEMORY_1M_BARS]
        return min_key, len(bars)


def _sync_api_candles_into_memory_store(
    symbol: str,
    df_valid: pd.DataFrame,
) -> None:
    """
    API 1분봉 ↔ 인메모리 실시간 틱 덮어쓰기 경합(Race Condition) 및 거래량(volume) 증발 원천 차단:
    API에서 정상적으로 수신·정제된 1분봉 DataFrame(df_valid)을 인메모리 1분봉 저장소(_LIVE_1M_BAR_STORE)와
    동기화하되, 차트 연산 도중 1.5초 메인 스나이퍼 루프가 기록한 최신 분봉(_min_key)의
    고가(max)·저가(min)·최신 종가(closePrice)·거래량(max) 및 연산 도중 새로 열린 분봉이 절대 덮어써져 유실되지 않도록
    _LIVE_1M_BAR_LOCK 내부에서 원자적으로 병합 보존한다.
    """
    if df_valid is None or df_valid.empty:
        return
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    try:
        tail_df = df_valid.tail(_MAX_MEMORY_1M_BARS)
        dt_list = tail_df["dt_est"].tolist()
        o_list = tail_df["O"].tolist()
        h_list = tail_df["H"].tolist()
        l_list = tail_df["L"].tolist()
        c_list = tail_df["C"].tolist()
        v_list = tail_df["V"].tolist()

        synced_bars: List[Dict[str, Any]] = []
        for dt_v, o_v, h_v, l_v, c_v, v_v in zip(
            dt_list, o_list, h_list, l_list, c_list, v_list
        ):
            dt_m = dt_v.replace(second=0, microsecond=0)
            synced_bars.append(
                {
                    "_min_key": dt_m.strftime("%Y-%m-%d %H:%M"),
                    "timestamp": dt_m.isoformat(),
                    "openPrice": round(float(o_v), 4),
                    "highPrice": round(float(h_v), 4),
                    "lowPrice": round(float(l_v), 4),
                    "closePrice": round(float(c_v), 4),
                    "volume": round(max(1.0, float(v_v)), 2),
                    "currency": "USD",
                }
            )
        if synced_bars:
            with _LIVE_1M_BAR_LOCK:
                existing_bars = _LIVE_1M_BAR_STORE.get(sym, [])
                if existing_bars:
                    last_sync_key = str(synced_bars[-1].get("_min_key") or "")
                    for eb in existing_bars[-3:]:
                        eb_key = str(eb.get("_min_key") or "")
                        if not eb_key:
                            continue
                        if eb_key == last_sync_key:
                            eb_h = safe_float(eb.get("highPrice"), 0.0)
                            eb_l = safe_float(eb.get("lowPrice"), 0.0)
                            eb_c = safe_float(eb.get("closePrice"), 0.0)
                            eb_v = safe_float(eb.get("volume"), 0.0)
                            cur_s = synced_bars[-1]
                            if eb_h > 0.0:
                                cur_s["highPrice"] = round(
                                    max(
                                        safe_float(cur_s.get("highPrice"), eb_h),
                                        eb_h,
                                    ),
                                    4,
                                )
                            if eb_l > 0.0:
                                cur_s_l = safe_float(cur_s.get("lowPrice"), eb_l)
                                cur_s["lowPrice"] = round(
                                    min(cur_s_l, eb_l)
                                    if cur_s_l > 0.0
                                    else eb_l,
                                    4,
                                )
                            if eb_c > 0.0:
                                cur_s["closePrice"] = round(eb_c, 4)
                            if eb_v > 0.0:
                                cur_s["volume"] = round(
                                    max(
                                        safe_float(cur_s.get("volume"), 1.0),
                                        eb_v,
                                    ),
                                    2,
                                )
                        elif eb_key > last_sync_key:
                            synced_bars.append(dict(eb))
                            last_sync_key = eb_key
                _LIVE_1M_BAR_STORE[sym] = synced_bars[-_MAX_MEMORY_1M_BARS:]
    except Exception:
        pass


def _merge_api_and_memory_candles(
    api_candles: Optional[List[Dict[str, Any]]],
    symbol: str = TARGET_SYMBOL,
) -> List[Dict[str, Any]]:
    """
    인메모리 1분봉 선행 + 토스 API 공식 1분봉 후행 배치:
    인메모리 실시간 합성 1분봉(mem_bars, volume=1.0)을 먼저 배치하고,
    브로커 API 공식 1분봉(api_candles, 실제 거래량 및 공식 시가 보유)을 뒤에 배치하여
    동일 분(dt_min) 중복 제거(keep="last") 시 공식 시가(O)·종가(C)·거래량(V)이 우선 채택되도록 보장한다.
    """
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    combined: List[Dict[str, Any]] = []
    with _LIVE_1M_BAR_LOCK:
        mem_bars = list(_LIVE_1M_BAR_STORE.get(sym, []))
    if mem_bars:
        combined.extend(mem_bars)
    if isinstance(api_candles, list) and api_candles:
        combined.extend(c for c in api_candles if isinstance(c, dict))
    return combined


def _parse_timestamp_series_to_est(ts_series: pd.Series) -> pd.Series:
    """
    pandas 2.x 혼합 ISO8601 타임스탬프 NaT 증발 원천 방어:
    밀리초(.123)가 포함된 문자열과 초 단위로 끝나는 문자열이 혼재된 경우에도
    format="ISO8601" 로 전수 파싱하여 단 1개의 유효 캔들도 NaT 로 유실되지 않게 보장한다.
    """
    try:
        ts_utc = pd.to_datetime(
            ts_series, format="ISO8601", utc=True, errors="coerce"
        )
    except Exception:
        ts_utc = pd.to_datetime(ts_series, utc=True, errors="coerce")

    if ts_utc.notna().sum() == 0 and len(ts_series) > 0:
        ts_utc = pd.to_datetime(ts_series, utc=True, errors="coerce")
    return ts_utc


# ---------------------------------------------------------------------------
# [핵심 1] 매수 시간창(04:07 ~ 16:00 EST) · 장마감 30분전 0주 신규 및 1층 공석 돌파 차단창(15:30 ~ 16:00 EST) vs 익절 매도 시간창(24시간 전 세션) 판별기 (Case 01, 79, 84, 88)
# ---------------------------------------------------------------------------
def is_weekend_nyse_closed(now_est: Optional[datetime] = None) -> bool:
    """
    # [Case 01 & Case 79]:
    미국 동부 시간(EST/EDT) 기준 주말 휴장 판정:
    - 금요일 애프터마켓(16:00 ~ 19:59 EST) 익절 매도 주문을 허용하기 위해 금요일(wd == 4)은 20:00 EST 부터 휴장으로 판정한다.
    - 토요일(wd == 5) 전 구간 및 일요일(wd == 6) 17:59 EST 까지를 주말 휴장으로 판정하며,
      일요일 18:00 EST 이후(한국 시간 월요일 오전 데이마켓)는 익절 매도 감시를 위해 정상 개장(False)으로 판정한다.
    """
    dt = now_est.astimezone(EST_TZ) if now_est else datetime.now(EST_TZ)
    wd = dt.weekday()  # 월=0, 화=1, ..., 금=4, 토=5, 일=6
    hm = dt.hour * 100 + dt.minute

    if wd == 4 and hm >= 2000:
        return True
    if wd == 5:
        return True
    if wd == 6 and hm < 2000:  # [사용자] 토스 데이마켓은 일요일 20:00 ET 시작
        return True
    return False


def is_active_buy_window(
    hm: int, now_est: Optional[datetime] = None
) -> bool:
    """
    # [🎯 2 & Case 01, Case 79, Case 88 : 매수 전용 시간창 (평일 04:07 ~ 16:00 EST 엄격 제한)]:
    - 본 그리드 및 서브 그리드의 모든 매수(0주 첫 진입 REENTRY_1FL / SUB_REENTRY_1FL ·
      1층 미체결 잔량 TOPUP_1FL / SUB_TOPUP_1FL · 1층 공석 60초 주기 재장전 ·
      10분 와이드/스텝업/저가해금 추매 DIP_1FL / SUB_DIP_1FL)는
      오직 평일(월~금) 프리장 개시(04:07 EST)부터 정규장 마감(16:00 EST)까지만 허용한다.
    - 애프터마켓(16:01 ~ 19:59 EST) 및 데이마켓(20:00 ~ 03:59 EST, 일요일 저녁 포함)에서는 매수를 100% 차단(False)한다.
    """
    if now_est is not None:
        dt = now_est.astimezone(EST_TZ)
        if is_weekend_nyse_closed(dt) or dt.weekday() >= 5:
            return False
    hm_int = safe_int(hm, 0)
    return 407 <= hm_int <= 1600


def is_active_trading_window(
    hm: int, now_est: Optional[datetime] = None
) -> bool:
    """
    하위 호환 심볼 유지: 기존 매수 게이트 및 10분 버킷 산출기에서 호출하는 함수로
    is_active_buy_window(04:07 ~ 16:00 EST)와 동일하게 작동한다.
    """
    return is_active_buy_window(hm, now_est=now_est)


def is_late_regular_new_cycle_cutoff_window(
    hm: Optional[int] = None, now_est: Optional[datetime] = None
) -> bool:
    """
    # [Case 84 & Case 88 : 정규장 마감 30분 전(평일 15:30:00 ~ 16:00:59 EST) 본·서브 0주 새 사이클 첫 1층 진입 및 상단층 보유 중 1층 공석 +1.0% 돌파 추격 동시 차단 판별기]:
    - 평일(월~금) 정규장 마감 30분 전 구간(1530 <= hm <= 1600)일 때 True 를 반환한다.
    - 이 구간에서는 기보유 지층(본·서브 1층 이상 적재)의 10분 게이트 신저가/스텝업/저가해금 추매(DIP_1FL / SUB_DIP_1FL),
      1층 미체결 잔량 보충(TOPUP_1FL / SUB_TOPUP_1FL), 그리고 상단층 보유 중 1층 공석 시 2층 단가 이하
      -1.00% 눌림목 재장전(PULLBACK_RELOAD)은 100% 정상 허용하되,
      본 그리드 또는 서브 그리드 0주 상태(사이클 종료 상태)에서 새 사이클 첫 1층(REENTRY_1FL / SUB_REENTRY_1FL)으로 고점 진입하는 것과
      상단층 보유 중 1층 공석 상태에서 +1.00% 상승돌파(BREAKOUT_RELOAD)로 추격 진입하는 것을 동시 원천 차단한다!
    """
    dt = now_est.astimezone(EST_TZ) if now_est else datetime.now(EST_TZ)
    if is_weekend_nyse_closed(dt) or dt.weekday() >= 5:
        return False
    hm_int = (
        safe_int(hm, dt.hour * 100 + dt.minute)
        if hm is not None
        else (dt.hour * 100 + dt.minute)
    )
    return NEW_CYCLE_BUY_CUTOFF_HM <= hm_int <= 1600


def is_active_sell_window(
    hm: int, now_est: Optional[datetime] = None
) -> bool:
    """
    # [🎯 2 & Case 79, Case 88 : 익절 매도 전용 확장 시간창 (프리마켓 + 정규장 + 애프터마켓 + 데이마켓 전 구간 개방)]:
    - 오버나이트를 하면서도 목표 익절가(본·서브 1층 +1.50% / 본 2~7층·서브 2~3층 개별 및 통합이동평균 +1.00%)에 도달하면
      애프터마켓(16:00 ~ 19:59 EST)과 데이마켓(20:00 ~ 03:59 EST)에서도 즉시 지정가 익절 매도가 나가도록 개방한다.
    - 오직 04:00 ~ 04:06 EST 프리장 오프닝 안정화 구간(7분)과 주말 휴장(금 20:00 ~ 일 17:59 EST)에만 매도 모니터를 멈춘다.
    """
    if now_est is not None:
        dt = now_est.astimezone(EST_TZ)
        if is_weekend_nyse_closed(dt):
            return False
    hm_int = safe_int(hm, 0)
    if 400 <= hm_int <= 406:
        return False
    return True


def is_extended_sell_only_window(
    hm: int, now_est: Optional[datetime] = None
) -> bool:
    """
    # [Case 79 : 장외 익절 매도 전용 구간(애프터마켓 · 데이마켓) 여부 판별기]:
    현재 시각이 익절 매도는 열려 있으나(is_active_sell_window == True)
    신규/추가 매수는 잠겨 있는(is_active_buy_window == False) 애프터마켓 또는 데이마켓 구간인지 판별한다.
    """
    return bool(
        is_active_sell_window(hm, now_est=now_est)
        and not is_active_buy_window(hm, now_est=now_est)
    )


def get_market_session_label(now_est: Optional[datetime] = None) -> str:
    """
    # [Case 79, Case 83, Case 84 & Case 88]:
    현재 EST 시각에 따른 세션 상태 라벨(프리장 · 정규장 · 정규장 마감30분전 0주/돌파차단 · 애프터장 · 데이장 익절감시 및 매수잠금 상태 명시)을 반환한다.
    """
    dt = now_est.astimezone(EST_TZ) if now_est else datetime.now(EST_TZ)
    if is_weekend_nyse_closed(dt):
        return "🛑 주말휴장"
    hm = dt.hour * 100 + dt.minute
    if 400 <= hm <= 406:
        return "🌅 프리장 오프닝 안정화(04:00~04:06)"
    if 407 <= hm <= 929 and dt.weekday() < 5:
        return "🔫 프리장 스나이퍼 가동(04:07~09:29)"
    if 1530 <= hm <= 1600 and dt.weekday() < 5:
        return "🔥 정규장 마감30분전 가동(15:30~16:00·0주/돌파차단)"
    if 930 <= hm <= 1529 and dt.weekday() < 5:
        return "🔥 정규장 스나이퍼 가동(09:30~16:00)"
    if 1601 <= hm <= 1959 and dt.weekday() < 5:
        return "🌇 애프터장 익절감시(16:00~19:59·매수잠금)"
    return "🌃 데이장 익절감시(20:00~03:59·매수잠금)"


# ---------------------------------------------------------------------------
# [핵심 2] 04:07 ~ 16:00 EST 10분 고정 매수 게이트 버킷 산출기 (Case 01, 36, 64, 79, 84, 88)
# ---------------------------------------------------------------------------
def evaluate_buy_gate_bucket_status(
    now_est: Optional[datetime] = None,
    buy_interval_min: int = LOCKED_BUY_INTERVAL_MIN,
    last_evaluated_bucket_id: int = -1,
    last_evaluated_date: str = "",
) -> Tuple[bool, int, str, Dict[str, Any]]:
    """
    🚨 Case 01, Case 36, Case 64, Case 79, Case 84 & Case 88:
    04:07 EST 기점 10분 고정 매수 게이트(04:07, 04:17, 04:27, ..., 15:57 및 16:00 마감봉)의
    현재 버킷 ID(cur_bucket_id)와 게이트 오픈 여부(is_gate_open), 차기 검문 시각(next_gate_hm_str)을 산출한다.
    - 본 그리드(last_evaluated_buy_bucket_id)와 서브 그리드(sub_last_evaluated_buy_bucket_id) 각각에 대해
      독립적으로 게이트 오픈 여부를 판정할 수 있다.
    - 애프터마켓(16:01 ~ 19:59 EST) 및 데이마켓(20:00 ~ 03:59 EST)에서는 is_active_buy_window == False 이므로
      언제나 is_gate_open = False 를 반환하여 장외 매수를 100% 원천 차단한다.
    - 동일 거래일(today_str) 내 동일 버킷(cur_bucket_id <= last_evaluated_bucket_id)에서는
      is_gate_open = False 를 반환하여 중복 매수를 100% 원천 차단한다.
    """
    dt = now_est.astimezone(EST_TZ) if now_est else datetime.now(EST_TZ)
    today_str = dt.strftime("%Y-%m-%d")
    hm = dt.hour * 100 + dt.minute
    cur_min_of_day = dt.hour * 60 + dt.minute

    interval = LOCKED_BUY_INTERVAL_MIN  # 10분 하드 고정 (Case 64)

    if not is_active_buy_window(hm, now_est=dt) or is_weekend_nyse_closed(dt):
        return (
            False,
            -1,
            today_str,
            {
                "is_active_window": False,
                "is_sell_window_open": is_active_sell_window(hm, now_est=dt),
                "is_new_cycle_cutoff": False,
                "mins_from_0407": -1,
                "bucket_10m": -1,
                "is_exact_boundary_min": False,
                "next_gate_hm_str": "04:07 EST (매수잠금·익절감시)",
                "session_label": get_market_session_label(dt),
            },
        )

    mins_from_0407 = max(0, cur_min_of_day - GATE_START_MIN_OF_DAY)
    if hm == 1600:
        cur_bucket_id = 72
        is_exact_boundary = True
        next_gate_str = "익일 04:07 EST"
    else:
        cur_bucket_id = int(mins_from_0407 // interval)
        is_exact_boundary = bool((mins_from_0407 % interval) == 0)
        next_bucket_min_of_day = (
            GATE_START_MIN_OF_DAY + (cur_bucket_id + 1) * interval
        )
        if next_bucket_min_of_day >= GATE_END_MIN_OF_DAY:
            next_gate_str = "16:00 EST"
        else:
            nh = next_bucket_min_of_day // 60
            nm = next_bucket_min_of_day % 60
            next_gate_str = f"{nh:02d}:{nm:02d} EST"

    prev_date = str(last_evaluated_date or "").strip()
    prev_bucket = safe_int(last_evaluated_bucket_id, -1)

    if prev_date != today_str:
        is_gate_open = True
    else:
        is_gate_open = bool(cur_bucket_id > prev_bucket)

    info: Dict[str, Any] = {
        "is_active_window": True,
        "is_sell_window_open": True,
        "is_new_cycle_cutoff": is_late_regular_new_cycle_cutoff_window(
            hm, now_est=dt
        ),
        "mins_from_0407": mins_from_0407,
        "bucket_10m": cur_bucket_id,
        "is_exact_boundary_min": is_exact_boundary,
        "next_gate_hm_str": next_gate_str,
        "session_label": get_market_session_label(dt),
    }
    return is_gate_open, cur_bucket_id, today_str, info


# ---------------------------------------------------------------------------
# [핵심 3] 100% 벡터화 시계열 지표 산출 엔진 (compute_soxl_quant_metrics_1m)
# ---------------------------------------------------------------------------
def _compute_5ma_intraday_amp_pct_vectorized(
    daily_candles: Optional[List[Dict[str, Any]]],
    df_1m: Optional[pd.DataFrame] = None,
) -> float:
    """
    최근 5영업일 일봉(또는 1분봉 일별 집계)의 일중 진폭 ((High - Low) / Low * 100.0) 평균을
    100% 벡터화 연산으로 산출한다.
    """
    if isinstance(daily_candles, list) and len(daily_candles) >= 2:
        try:
            df_d = pd.DataFrame(daily_candles)
            if "highPrice" in df_d.columns and "lowPrice" in df_d.columns:
                h_s = pd.to_numeric(df_d["highPrice"], errors="coerce")
                l_s = pd.to_numeric(df_d["lowPrice"], errors="coerce")
                valid = (h_s > 0.0) & (l_s > 0.0) & (h_s >= l_s)
                h_v = h_s[valid].to_numpy(dtype=float)
                l_v = l_s[valid].to_numpy(dtype=float)
                if len(l_v) >= 2:
                    if len(l_v) > 5:
                        h_sub = h_v[-6:-1]
                        l_sub = l_v[-6:-1]
                    else:
                        h_sub = h_v[-5:]
                        l_sub = l_v[-5:]
                    amps = ((h_sub - l_sub) / np.maximum(0.01, l_sub)) * 100.0
                    mean_amp = float(np.mean(amps))
                    if not math.isnan(mean_amp) and mean_amp > 0.0:
                        return round(mean_amp, 2)
        except Exception:
            pass

    if df_1m is not None and not df_1m.empty and "Date" in df_1m.columns:
        try:
            grp = df_1m.groupby("Date", sort=True).agg(
                day_h=("H", "max"), day_l=("L", "min")
            )
            valid_g = grp[(grp["day_l"] > 0.0) & (grp["day_h"] >= grp["day_l"])]
            if not valid_g.empty:
                amps = (
                    (
                        valid_g["day_h"].to_numpy(dtype=float)
                        - valid_g["day_l"].to_numpy(dtype=float)
                    )
                    / np.maximum(0.01, valid_g["day_l"].to_numpy(dtype=float))
                ) * 100.0
                mean_amp = float(np.mean(amps[-5:]))
                if not math.isnan(mean_amp) and mean_amp > 0.0:
                    return round(mean_amp, 2)
        except Exception:
            pass

    return 6.50


def _compute_vectorized_heikin_ashi_and_rsi(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> Dict[str, Any]:
    """
    Wilder's RSI(14) 벡터화 연산 및 2봉 이상 즉시 기저값 생성:
    100% 벡터화(np.diff + Wilder's EWM) 연산으로 n >= 2 이상이면 첫 봉 NaN 왜곡 없이
    직전 완성봉 종가(prev_bar_close)와 직전 완성봉까지의 평균 상승/하락폭(prev_avg_gain, prev_avg_loss)을 산출한다.
    """
    n = len(closes)
    if n == 0:
        return {
            "rsi_14": 50.0,
            "rsi_ready": False,
            "candle_count": 0,
            "prev_bar_close": 0.0,
            "prev_avg_gain": 0.0,
            "prev_avg_loss": 0.0,
            "ha_open": 0.0,
            "ha_close": 0.0,
            "prev_ha_open": 0.0,
            "prev_ha_close": 0.0,
            "cur_bar_open": 0.0,
            "cur_bar_high": 0.0,
            "cur_bar_low": 0.0,
            "ha_bull": True,
            "ha_badge": "🕯️HA양봉",
        }

    ha_close_arr = (opens + highs + lows + closes) * 0.25
    ha_seed = (opens[0] + closes[0]) * 0.5
    shifted_hc = np.empty(n, dtype=float)
    shifted_hc[0] = ha_seed
    if n > 1:
        shifted_hc[1:] = ha_close_arr[:-1]
    ha_open_series = (
        pd.Series(shifted_hc)
        .ewm(alpha=0.5, adjust=False)
        .mean()
        .to_numpy(dtype=float)
    )

    cur_ha_open = float(ha_open_series[-1])
    cur_ha_close = float(ha_close_arr[-1])
    prev_ha_open = float(ha_open_series[-2]) if n >= 2 else cur_ha_open
    prev_ha_close = float(ha_close_arr[-2]) if n >= 2 else cur_ha_close
    is_bull = bool(cur_ha_close >= cur_ha_open)

    # Wilder's RSI(14) 벡터화 연산 (np.diff 기반으로 첫 원소 NaN 오염 원천 배제)
    rsi_val = 50.0
    prev_bar_close = float(closes[-2]) if n >= 2 else float(closes[-1])
    prev_avg_g = 0.0
    prev_avg_l = 0.0

    if n >= 2:
        deltas = np.diff(closes)
        gains = np.maximum(0.0, deltas)
        losses = np.maximum(0.0, -deltas)
        avg_gain_arr = (
            pd.Series(gains)
            .ewm(alpha=1.0 / 14.0, min_periods=1, adjust=False)
            .mean()
            .to_numpy(dtype=float)
        )
        avg_loss_arr = (
            pd.Series(losses)
            .ewm(alpha=1.0 / 14.0, min_periods=1, adjust=False)
            .mean()
            .to_numpy(dtype=float)
        )
        last_g = float(avg_gain_arr[-1])
        last_l = float(avg_loss_arr[-1])
        if len(avg_gain_arr) >= 2:
            prev_avg_g = float(avg_gain_arr[-2])
            prev_avg_l = float(avg_loss_arr[-2])
        else:
            prev_avg_g = 0.0
            prev_avg_l = 0.0

        if last_g <= 1e-12 and last_l <= 1e-12:
            rsi_val = 50.0
        elif last_l <= 1e-12:
            rsi_val = 100.0
        else:
            rs = last_g / last_l
            rsi_val = 100.0 - (100.0 / (1.0 + rs))

    # [4bot v2.4.0 · 원작 c4ad8d6 Case 93 · 암살자 전용 새 키] 3분/10분 전 종가 · 단기 변화율 (기존 키 무변경)
    cur_c_v = float(closes[-1])
    c_3m_ago = float(closes[-4]) if n >= 4 else float(closes[0])
    c_10m_ago = float(closes[-11]) if n >= 11 else float(closes[0])
    vel_1m_pct = ((cur_c_v - prev_bar_close) / prev_bar_close) * 100.0 if prev_bar_close > 0.0 else 0.0
    vel_3m_pct = ((cur_c_v - c_3m_ago) / c_3m_ago) * 100.0 if c_3m_ago > 0.0 else 0.0
    vel_10m_pct = ((cur_c_v - c_10m_ago) / c_10m_ago) * 100.0 if c_10m_ago > 0.0 else 0.0

    return {
        "rsi_14": round(rsi_val, 2),
        "rsi_ready": bool(n >= 14),
        "candle_count": int(n),
        "close_3m_ago": round(c_3m_ago, 4),
        "close_10m_ago": round(c_10m_ago, 4),
        "vel_1m_pct": round(vel_1m_pct, 4),
        "vel_3m_pct": round(vel_3m_pct, 4),
        "vel_10m_pct": round(vel_10m_pct, 4),
        "vel_max_3m_10m_pct": round(max(vel_3m_pct, vel_10m_pct), 4),
        "prev_bar_close": round(prev_bar_close, 4),
        "prev_avg_gain": round(prev_avg_g, 6),
        "prev_avg_loss": round(prev_avg_l, 6),
        "ha_open": round(cur_ha_open, 4),
        "ha_close": round(cur_ha_close, 4),
        "prev_ha_open": round(prev_ha_open, 4),
        "prev_ha_close": round(prev_ha_close, 4),
        "cur_bar_open": round(float(opens[-1]), 4),
        "cur_bar_high": round(float(highs[-1]), 4),
        "cur_bar_low": round(float(lows[-1]), 4),
        "ha_bull": is_bull,
        "ha_badge": "🕯️HA양봉" if is_bull else "🌑HA음봉",
    }


def _recompute_ha_rsi_from_memory_store(
    symbol: str = TARGET_SYMBOL,
) -> Optional[Dict[str, Any]]:
    """
    인메모리 1분봉 저장소(_LIVE_1M_BAR_STORE)에 축적된 분봉이 2개 이상일 때,
    O(1) 수준의 경량 배열 연산으로 Wilder's RSI(14) 및 Heikin-Ashi 기저값을 즉시 재산출한다.
    """
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    with _LIVE_1M_BAR_LOCK:
        bars = list(_LIVE_1M_BAR_STORE.get(sym, []))
    if len(bars) < 2:
        return None
    try:
        df_m = pd.DataFrame(bars)
        opens = pd.to_numeric(df_m["openPrice"], errors="coerce").to_numpy(
            dtype=float
        )
        highs = pd.to_numeric(df_m["highPrice"], errors="coerce").to_numpy(
            dtype=float
        )
        lows = pd.to_numeric(df_m["lowPrice"], errors="coerce").to_numpy(
            dtype=float
        )
        closes = pd.to_numeric(df_m["closePrice"], errors="coerce").to_numpy(
            dtype=float
        )
        valid_mask = (
            np.isfinite(opens)
            & np.isfinite(highs)
            & np.isfinite(lows)
            & np.isfinite(closes)
            & (closes > 0.0)
        )
        if int(np.sum(valid_mask)) < 2:
            return None
        res = _compute_vectorized_heikin_ashi_and_rsi(
            opens[valid_mask],
            highs[valid_mask],
            lows[valid_mask],
            closes[valid_mask],
        )
        res["cur_bar_minute_key"] = str(bars[-1].get("_min_key") or "")
        return res
    except Exception:
        return None


def _calc_session_vwap_and_bands(
    df_sess: pd.DataFrame,
    ma5_amp_pct: float,
) -> Dict[str, float]:
    """
    주어진 세션(프리장 또는 정규장) DataFrame 에 대해 누적 VWAP, 고가, 저가, 진폭(%),
    5MA 진폭 기반 예상 저가/고가 밴드를 100% 벡터화 연산으로 산출한다.
    """
    if df_sess is None or df_sess.empty:
        return {
            "vwap": 0.0,
            "high": 0.0,
            "low": 0.0,
            "amp_pct": 0.0,
            "est_low": 0.0,
            "est_high": 0.0,
        }

    h_arr = df_sess["H"].to_numpy(dtype=float)
    l_arr = df_sess["L"].to_numpy(dtype=float)
    c_arr = df_sess["C"].to_numpy(dtype=float)
    v_arr = np.maximum(0.0, df_sess["V"].to_numpy(dtype=float))

    tp_arr = (h_arr + l_arr + c_arr) / 3.0
    tot_vol = float(np.sum(v_arr))
    if tot_vol > 0.0:
        vwap_val = float(np.sum(tp_arr * v_arr) / tot_vol)
    else:
        vwap_val = float(np.mean(tp_arr))

    sess_h = float(np.max(h_arr))
    sess_l = float(np.min(l_arr))
    amp_pct = (
        ((sess_h - sess_l) / sess_l) * 100.0 if sess_l > 0.0 else 0.0
    )

    amp_ratio = max(0.01, float(ma5_amp_pct) / 100.0)
    est_high = sess_l * (1.0 + amp_ratio) if sess_l > 0.0 else 0.0
    est_low = sess_h / (1.0 + amp_ratio) if sess_h > 0.0 else 0.0

    return {
        "vwap": round(vwap_val, 4),
        "high": round(sess_h, 4),
        "low": round(sess_l, 4),
        "amp_pct": round(amp_pct, 2),
        "est_low": round(min(est_low, sess_l), 2),
        "est_high": round(max(est_high, sess_h), 2),
    }


# [4bot v2.4.0 · 원작 c4ad8d6 Case 93 · 암살자 전용 앵커 추출기 — 원작 그대로]
def _extract_daily_candle_date_str(
    dc: Dict[str, Any],
) -> Tuple[str, str]:
    """
    # MODIFIED [Case 93 : 토스 일봉(1d) KST +09:00 ➔ EST 변환 시 날짜 하루 밀림 버그 원천 제거]:
    토스 API 일봉(interval="1d")의 "timestamp": "2026-11-06T09:00:00+09:00" 을 EST로 변환해
    "2026-11-05" 로 하루 밀리게 하던 타임존 변환을 제거하고,
    일봉의 고유 명목 거래일(raw_date = ts_raw[:10])을 그대로 반환한다.
    """
    ts_raw = str(
        dc.get("timestamp") or dc.get("date") or dc.get("dt") or ""
    ).strip()
    raw_date = ts_raw[:10] if len(ts_raw) >= 10 else ""
    return raw_date, raw_date


def _resolve_active_us_trading_date(
    df_all: pd.DataFrame,
    today_est_str: str,
) -> str:
    """
    # NEW [Case 93 : EST 자정(00:00 ~ 04:06 EST) 데이마켓 및 주말 기동 시 합성 분봉 날짜 선점 방어]:
    공식 API 분봉(~df_all["is_synthetic"]) 중 실제 장중 세션(04:00 ~ 16:00 EST) 데이터가 존재하는
    최신 미국 거래일을 우선 target_date 로 선택한다.
    """
    if df_all is None or df_all.empty or "Date" not in df_all.columns:
        return today_est_str

    has_syn = "is_synthetic" in df_all.columns
    df_api = df_all[~df_all["is_synthetic"]] if has_syn else df_all

    if not df_api.empty:
        df_api_sess = df_api[
            (df_api["hm"] >= 400) & (df_api["hm"] <= 1600)
        ]
        if not df_api_sess.empty:
            if (df_api_sess["Date"] == today_est_str).any():
                return today_est_str
            return str(df_api_sess["Date"].iloc[-1])
        if (df_api["Date"] == today_est_str).any():
            return today_est_str
        return str(df_api["Date"].iloc[-1])

    if (df_all["Date"] == today_est_str).any():
        return today_est_str
    return str(df_all["Date"].iloc[-1])


def _extract_prev_reg_close_and_pre_open(
    df_all: pd.DataFrame,
    target_date: str,
    daily_candles: Optional[List[Dict[str, Any]]] = None,
    explicit_prev_close: float = 0.0,
    fallback_price: float = 0.0,
    symbol: str = TARGET_SYMBOL,
) -> Tuple[float, float, bool, bool]:
    """
    # MODIFIED [Case 93 : 암살자 정찰병 필수 조건 3(전날 정규장 종가 prev_reg_close) & 조건 4(당일 04:07 프리장 시가 pre_open_price) 무오염 분리 및 가짜 정규장 시가 폴백 영구 소각]:
    1) prev_reg_close (전일 정규장 종가):
       - explicit_prev_close > 0.0 이면 최우선 채택
       - 일봉(daily_candles)의 고유 명목 거래일(raw_d)을 기준으로 당일 진행 일봉(raw_d >= target_date)이면
         직전 확정 일봉(sorted_d[-2])의 종가를, 당일 일봉 생성 전(raw_d < target_date)이면 최신 확정 일봉(sorted_d[-1])의 종가를 추출
       - 부재 시 공식 1분봉(df_all) 내 target_date 이전 영업일의 정규장(09:30 ~ 16:00 EST) 마지막 완성봉 종가(C)만 추출하며,
         전날 밤 23:59 EST 데이마켓 야간봉으로 빠지던 왜곡 폴백은 영구 삭제!
    2) pre_open_price (당일 04:07 프리장 시가):
       - 당일(target_date) 실제 API 1분봉(_synthetic == False) 중 04:07 ~ 09:29 EST (또는 04:00 ~ 09:29 EST) 첫 봉의 시가(O)만 추출
       - 장 마감 후 1분봉 조회 윈도우 이탈 등으로 당일 04:00 ~ 09:29 EST 봉이 없고 인메모리 래치에도 없을 때는,
         일봉의 정규장 시가(09:30 EST Open)나 정규장 1분봉 시가/전일종가/현재가로 덮어쓰지 않고 정확히 0.0 (found_true_pre_open = False)을 반환한다!
    """
    latch = _get_daily_anchor_latch(symbol, target_date)
    prev_reg_c = safe_float(explicit_prev_close, 0.0)
    found_true_prev_close = bool(prev_reg_c > 0.0)

    pre_open_p = 0.0
    found_true_pre_open = False

    # 1단계: 일봉(1d)에서 고유 거래일(raw_d) 기준 직전 영업일 확정 정규장 종가 추출 (일봉 시가는 정규장 09:30 시가이므로 프리시가에 절대 사용하지 않음)
    if isinstance(daily_candles, list) and len(daily_candles) >= 1:
        try:
            valid_d = [
                c
                for c in daily_candles
                if isinstance(c, dict)
                and safe_float(c.get("closePrice") or c.get("close"), 0.0)
                > 0.0
            ]
            sorted_d = sorted(
                valid_d,
                key=lambda x: _extract_daily_candle_date_str(x)[0],
            )
            if sorted_d:
                last_dc = sorted_d[-1]
                raw_d, _ = _extract_daily_candle_date_str(last_dc)
                last_close = safe_float(
                    last_dc.get("closePrice") or last_dc.get("close"), 0.0
                )

                if raw_d and raw_d >= target_date:
                    if prev_reg_c <= 0.0:
                        prior_list = [
                            c
                            for c in sorted_d
                            if _extract_daily_candle_date_str(c)[0]
                            < target_date
                        ]
                        if prior_list:
                            c_val = safe_float(
                                prior_list[-1].get("closePrice")
                                or prior_list[-1].get("close"),
                                0.0,
                            )
                            if c_val > 0.0:
                                prev_reg_c = c_val
                                found_true_prev_close = True
                        elif len(sorted_d) >= 2:
                            c_val = safe_float(
                                sorted_d[-2].get("closePrice")
                                or sorted_d[-2].get("close"),
                                0.0,
                            )
                            if c_val > 0.0:
                                prev_reg_c = c_val
                                found_true_prev_close = True
                else:
                    if prev_reg_c <= 0.0 and last_close > 0.0:
                        prev_reg_c = last_close
                        found_true_prev_close = True
        except Exception:
            pass

    # 2단계: 공식 API 1분봉(df_all)에서 당일 04:07 프리장 시가 및 전일 정규장(09:30 ~ 16:00 EST) 마감 종가 추출
    if df_all is not None and not df_all.empty and "Date" in df_all.columns:
        has_syn_col = "is_synthetic" in df_all.columns
        df_api_all = (
            df_all[~df_all["is_synthetic"]] if has_syn_col else df_all
        )

        df_today_api = df_api_all[df_api_all["Date"] == target_date]
        if not df_today_api.empty:
            pre_0407 = df_today_api[
                (df_today_api["hm"] >= 407) & (df_today_api["hm"] <= 929)
            ]
            if not pre_0407.empty:
                pre_open_p = float(pre_0407["O"].iloc[0])
                found_true_pre_open = True
            else:
                pre_0400 = df_today_api[
                    (df_today_api["hm"] >= 400) & (df_today_api["hm"] <= 929)
                ]
                if not pre_0400.empty:
                    pre_open_p = float(pre_0400["O"].iloc[0])
                    found_true_pre_open = True

        # 전일 정규장(09:30 ~ 16:00 EST) 봉이 실제로 존재할 때만 종가 채택 (23:59 EST 야간봉 폴백 영구 금지!)
        if prev_reg_c <= 0.0:
            df_prev_api = df_api_all[df_api_all["Date"] < target_date]
            if not df_prev_api.empty:
                reg_prev_all = df_prev_api[
                    (df_prev_api["hm"] >= 930) & (df_prev_api["hm"] <= 1600)
                ]
                if not reg_prev_all.empty:
                    prev_reg_c = float(reg_prev_all["C"].iloc[-1])
                    found_true_prev_close = True

    # 3단계: 당일 인메모리 래치(_DAILY_SESSION_ANCHOR_STORE) 복원 및 진성값만 갱신
    latched_prev_c = safe_float(latch.get("prev_reg_close"), 0.0)
    latched_pre_o = safe_float(latch.get("pre_open_price"), 0.0)

    if not found_true_prev_close and latched_prev_c > 0.0:
        prev_reg_c = latched_prev_c
        found_true_prev_close = True
    if not found_true_pre_open and latched_pre_o > 0.0:
        pre_open_p = latched_pre_o
        found_true_pre_open = True

    if found_true_prev_close or found_true_pre_open:
        _update_daily_anchor_latch(
            symbol=symbol,
            target_date=target_date,
            prev_reg_close=(prev_reg_c if found_true_prev_close else 0.0),
            pre_open_price=(pre_open_p if found_true_pre_open else 0.0),
            verified_distinct=bool(
                found_true_prev_close
                and found_true_pre_open
                and abs(prev_reg_c - pre_open_p) > 1e-6
            ),
        )

    # 4단계: 전일 종가만 최후 안전 폴백 적용 (프리시가 pre_open_p 는 미확보 시 정규장 가격으로 덮어쓰지 않고 0.0 유지!)
    fb = safe_float(fallback_price, 0.0)
    if prev_reg_c <= 0.0:
        prev_reg_c = pre_open_p if pre_open_p > 0.0 else fb

    return (
        round(prev_reg_c, 4),
        round(pre_open_p, 4) if found_true_pre_open else 0.0,
        found_true_prev_close,
        found_true_pre_open,
    )


def _compute_assassin_anchor_fields(
    api_candles: Optional[List[Dict[str, Any]]],
    daily_candles: Optional[List[Dict[str, Any]]],
    dt_now: datetime,
    today_str: str,
    lp: float,
    ma5_amp: float,
    reg_vwap_existing: float,
    prev_day_close: float = 0.0,
    symbol: str = TARGET_SYMBOL,
) -> Dict[str, Any]:
    """
    # NEW [4bot 2번 v2.4.0 · 원작 c4ad8d6 Case 93 · 🗡️ 암살자 4대 지표 전용 · 새 키만 반환]:
    브로커 API 1분봉(api_candles — 인메모리 합성봉 제외)만으로 전일 정규장 종가(prev_reg_close) · 당일 04:07 프리장 시가(pre_open_price) ·
    04:07 프리장 누적 VWAP(assn_premarket_vwap)을 산출하고 당일 래치에 보존한다.
    기존 스나이퍼 지표 키(premarket_vwap 등)는 건드리지 않는다. 예외 시 빈 dict.
    """
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    try:
        df = pd.DataFrame([c for c in (api_candles or []) if isinstance(c, dict)])
        if not df.empty:
            ts_col = next((c for c in ("timestamp", "dt", "dateTime") if c in df.columns), None)
            if ts_col is None:
                df = pd.DataFrame()
            else:
                ts_est = _parse_timestamp_series_to_est(df[ts_col])
                df = df.loc[ts_est.notna()].copy()
                if not df.empty:
                    df["dt_est"] = ts_est[ts_est.notna()].dt.tz_convert(EST_TZ)
                    for col, keys in (("O", ("openPrice", "open")), ("H", ("highPrice", "high")), ("L", ("lowPrice", "low")), ("C", ("closePrice", "close"))):
                        src = next((k for k in keys if k in df.columns), None)
                        df[col] = pd.to_numeric(df[src], errors="coerce") if src else np.nan
                    v_src = "volume" if "volume" in df.columns else None
                    df["V"] = pd.to_numeric(df[v_src], errors="coerce").fillna(0.0) if v_src else 0.0
                    df = df.dropna(subset=["O", "H", "L", "C"])
                    df = df[(df["O"] > 0.0) & (df["C"] > 0.0)].copy()
                    df = df.sort_values("dt_est")
                    df["Date"] = df["dt_est"].dt.strftime("%Y-%m-%d")
                    df["hm"] = df["dt_est"].dt.hour * 100 + df["dt_est"].dt.minute
        target_date = _resolve_active_us_trading_date(df, today_str) if not df.empty else today_str
        prev_reg_c, pre_open_p, found_prev, found_open = _extract_prev_reg_close_and_pre_open(
            df_all=df if not df.empty else None,
            target_date=target_date,
            daily_candles=daily_candles,
            explicit_prev_close=safe_float(prev_day_close, 0.0),
            fallback_price=lp,
            symbol=sym,
        )
        pre_vwap = 0.0
        found_pre_vwap = False
        if not df.empty:
            df_t = df[df["Date"] == target_date]
            df_pre = df_t[(df_t["hm"] >= 407) & (df_t["hm"] <= 929)]
            if df_pre.empty:
                df_pre = df_t[(df_t["hm"] >= 400) & (df_t["hm"] <= 929)]
            pre_stats = _calc_session_vwap_and_bands(df_pre, ma5_amp)
            if safe_float(pre_stats.get("vwap"), 0.0) > 0.0:
                pre_vwap = safe_float(pre_stats.get("vwap"), 0.0)
                found_pre_vwap = True
                _update_daily_anchor_latch(
                    symbol=sym,
                    target_date=target_date,
                    pre_stats=pre_stats,
                    verified_distinct=bool(
                        found_prev and found_open
                        and not _is_collapsed_anchor_triplet(prev_reg_c, pre_open_p, pre_vwap)
                    ),
                )
        if not found_pre_vwap:
            l_stats = _get_daily_anchor_latch(sym, target_date).get("pre_stats")
            if isinstance(l_stats, dict) and safe_float(l_stats.get("vwap"), 0.0) > 0.0:
                pre_vwap = safe_float(l_stats.get("vwap"), 0.0)
                found_pre_vwap = True
        bear_drop = (
            max(0.0, (pre_open_p - lp) / pre_open_p * 100.0)
            if pre_open_p > 0.0 and lp > 0.0
            else 0.0
        )
        anchors_ready = bool(
            found_prev
            and (found_open or found_pre_vwap or safe_float(reg_vwap_existing, 0.0) > 0.0)
            and not _is_collapsed_anchor_triplet(prev_reg_c, pre_open_p, pre_vwap)
        )
        return {
            "anchors_ready": anchors_ready,
            "found_true_prev_close": bool(found_prev),
            "found_true_pre_open": bool(found_open),
            "found_true_pre_vwap": bool(found_pre_vwap),
            "prev_reg_close": prev_reg_c,
            "prev_day_close": prev_reg_c,
            "pre_open_price": pre_open_p,
            "assn_premarket_vwap": round(pre_vwap, 4),
            "bear_drop_amp_pct": round(bear_drop, 4),
            "api_candle_count": len(api_candles) if isinstance(api_candles, list) else 0,
        }
    except Exception as exc:
        logger.debug("암살자 4대 지표 앵커 산출 폴백(묵음 · 스나이퍼 지표 무영향): %s", exc)
        return {}


def compute_soxl_quant_metrics_1m(
    candles: List[Dict[str, Any]],
    live_price: float = 0.0,
    now_est: Optional[datetime] = None,
    daily_candles: Optional[List[Dict[str, Any]]] = None,
    prev_day_close: float = 0.0,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    """
    🎯 2 & Case 01, 15, 79, 84, 88 (+ 4bot v2.4.0 Case 93: symbol·prev_day_close 인자 · 암살자 새 키 추가, 기존 키 값 동일):
    토스 Open API 1분봉(candles), 인메모리 실시간 합성 1분봉(_LIVE_1M_BAR_STORE) 및 일봉(daily_candles)을 입력받아:
    1) 당일 프리장(04:00 ~ 09:29 EST) VWAP · 고/저가 진폭 · 예상 변동 밴드
    2) 당일 정규장(09:30 ~ 16:00 EST) VWAP · 고/저가 진폭 · 예상 변동 밴드
    3) 최근 5영업일 평균 진폭(5MA) 및 실시간 하이킨 아시 추세 배지(🕯️HA양봉 / 🌑HA음봉) · Wilder's RSI(14)
    4) 04:07 ~ 16:00 EST 10분 고정 매수 게이트 버킷 · 장마감 30분전 0주 신규 및 1층 공석 돌파 컷오프(15:30 ~ 16:00 EST) 정보
    를 100% 벡터화 연산으로 산출하여 반환한다.
    (Case 79: 데이마켓/애프터마켓에서 브로커가 시세·캔들을 제공하지 않는 경우에도 경고 로그나 알림 없이 조용히 묵음 반환)
    """
    dt_now = now_est.astimezone(EST_TZ) if now_est else datetime.now(EST_TZ)
    hm_now = dt_now.hour * 100 + dt_now.minute
    _, cur_bucket_id, today_str, gate_info = evaluate_buy_gate_bucket_status(
        now_est=dt_now, buy_interval_min=LOCKED_BUY_INTERVAL_MIN
    )
    lp = safe_float(live_price, 0.0)
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    cur_min_key, _ = _record_live_tick_to_memory_bar(
        sym, lp, now_est=dt_now
    )

    default_out: Dict[str, Any] = {
        "symbol": sym,
        "live_price": round(lp, 4),
        "ma5_amp_pct": 6.50,
        "rsi_14": 50.0,
        "rsi_ready": False,
        "candle_count": 0,
        "cur_bar_minute_key": cur_min_key,
        "prev_bar_close": 0.0,
        "prev_avg_gain": 0.0,
        "prev_avg_loss": 0.0,
        "ha_open": round(lp, 4),
        "ha_close": round(lp, 4),
        "prev_ha_open": round(lp, 4),
        "prev_ha_close": round(lp, 4),
        "cur_bar_open": round(lp, 4),
        "cur_bar_high": round(lp, 4),
        "cur_bar_low": round(lp, 4),
        "ha_bull": True,
        "ha_badge": "🕯️HA양봉",
        "premarket_vwap": 0.0,
        "premarket_high": 0.0,
        "premarket_low": 0.0,
        "premarket_amp_pct": 0.0,
        "premarket_est_low": 0.0,
        "premarket_est_high": 0.0,
        "regular_vwap": 0.0,
        "regular_high": 0.0,
        "regular_low": 0.0,
        "regular_amp_pct": 0.0,
        "regular_est_low": 0.0,
        "regular_est_high": 0.0,
        "day_vwap": 0.0,
        "day_high": 0.0,
        "day_low": 0.0,
        "day_amp_pct": 0.0,
        "bucket_10m": cur_bucket_id,
        "is_new_cycle_cutoff": is_late_regular_new_cycle_cutoff_window(
            hm_now, now_est=dt_now
        ),
        "next_gate_hm_str": gate_info.get("next_gate_hm_str", "04:07 EST"),
        "session_label": gate_info.get("session_label", ""),
        "updated_est": dt_now.strftime("%m-%d %H:%M:%S EST"),
    }

    merged_candles = _merge_api_and_memory_candles(candles, sym)
    if not merged_candles:
        default_out["ma5_amp_pct"] = _compute_5ma_intraday_amp_pct_vectorized(
            daily_candles, None
        )
        return default_out

    try:
        df = pd.DataFrame(merged_candles)
        if df.empty:
            return default_out

        ts_col = (
            "timestamp"
            if "timestamp" in df.columns
            else (
                "dt"
                if "dt" in df.columns
                else ("dateTime" if "dateTime" in df.columns else None)
            )
        )
        if ts_col is None:
            return default_out

        ts_utc = _parse_timestamp_series_to_est(df[ts_col])
        valid_ts = ts_utc.notna()
        df = df.loc[valid_ts].copy()
        if df.empty:
            return default_out

        df["dt_est"] = ts_utc[valid_ts].dt.tz_convert(EST_TZ)
        df["dt_min"] = df["dt_est"].dt.floor("min")

        df["O"] = pd.to_numeric(
            df.get("openPrice", df.get("open", df.get("price"))),
            errors="coerce",
        )
        df["H"] = pd.to_numeric(
            df.get("highPrice", df.get("high", df.get("price"))),
            errors="coerce",
        )
        df["L"] = pd.to_numeric(
            df.get("lowPrice", df.get("low", df.get("price"))),
            errors="coerce",
        )
        df["C"] = pd.to_numeric(
            df.get("closePrice", df.get("close", df.get("price"))),
            errors="coerce",
        )
        df["V"] = pd.to_numeric(
            df.get("volume", 0.0), errors="coerce"
        ).fillna(0.0)

        df.dropna(subset=["O", "H", "L", "C"], inplace=True)
        df = df[
            (df["O"] > 0.0)
            & (df["H"] > 0.0)
            & (df["L"] > 0.0)
            & (df["C"] > 0.0)
        ].copy()
        if df.empty:
            return default_out

        # 동일 분(dt_min) 내 인메모리 틱 고/저가 극단값 및 거래소 공식 거래량(V)·시가(O) 벡터화 병합
        if df.duplicated(subset=["dt_min"]).any():
            grp_min = df.groupby("dt_min", sort=False)
            df["H"] = grp_min["H"].transform("max")
            df["L"] = grp_min["L"].transform("min")
            df["V"] = grp_min["V"].transform("max")
            df.drop_duplicates(subset=["dt_min"], keep="last", inplace=True)

        df.sort_values("dt_min", ascending=True, inplace=True)

        # API + 메모리 병합 정제본을 인메모리 1분봉 저장소에 다시 동기화하여 히스토리 영구 보존
        _sync_api_candles_into_memory_store(sym, df)

        df["Date"] = df["dt_est"].dt.strftime("%Y-%m-%d")
        df["hm"] = df["dt_est"].dt.hour * 100 + df["dt_est"].dt.minute

        last_candle_close = float(df["C"].iloc[-1])
        if lp <= 0.0:
            lp = last_candle_close

        ma5_amp = _compute_5ma_intraday_amp_pct_vectorized(daily_candles, df)

        opens = df["O"].to_numpy(dtype=float)
        highs = df["H"].to_numpy(dtype=float)
        lows = df["L"].to_numpy(dtype=float)
        closes = df["C"].to_numpy(dtype=float)
        if lp > 0.0 and len(closes) > 0:
            closes[-1] = lp
            highs[-1] = max(highs[-1], lp)
            lows[-1] = min(lows[-1], lp)

        ha_rsi_info = _compute_vectorized_heikin_ashi_and_rsi(
            opens, highs, lows, closes
        )
        last_dt_min = df["dt_min"].iloc[-1]
        ha_rsi_info["cur_bar_minute_key"] = last_dt_min.strftime(
            "%Y-%m-%d %H:%M"
        )

        target_date = (
            today_str
            if (df["Date"] == today_str).any()
            else str(df["Date"].iloc[-1])
        )
        df_today = df[df["Date"] == target_date]

        df_pre = df_today[(df_today["hm"] >= 400) & (df_today["hm"] <= 929)]
        df_reg = df_today[(df_today["hm"] >= 930) & (df_today["hm"] <= 1600)]

        # [사용자] 데이마켓(20:00~03:59 ET) 세션 VWAP
        day_start = dt_now.replace(hour=20, minute=0, second=0, microsecond=0)
        if dt_now.hour < 20:
            day_start -= timedelta(days=1)
        df_daymarket = df[(df["dt_est"] >= day_start)
                          & (df["dt_est"] <= dt_now)
                          & ((df["hm"] >= 2000) | (df["hm"] < 400))]
        daymarket_stats = _calc_session_vwap_and_bands(df_daymarket, ma5_amp)
        pre_stats = _calc_session_vwap_and_bands(df_pre, ma5_amp)
        reg_stats = _calc_session_vwap_and_bands(df_reg, ma5_amp)
        all_stats = _calc_session_vwap_and_bands(df_today, ma5_amp)

        active_vwap = (
            reg_stats["vwap"]
            if reg_stats["vwap"] > 0.0
            else (
                pre_stats["vwap"]
                if pre_stats["vwap"] > 0.0
                else all_stats["vwap"]
            )
        )

        if dt_now.hour >= 20 or dt_now.hour < 4:
            # [사용자] 주간거래 중 전일 정규장 VWAP을 현재 세션 값으로 사용하지 않는다.
            active_vwap = daymarket_stats["vwap"]
            all_stats = daymarket_stats

        out = dict(default_out)
        out.update(ha_rsi_info)
        out.update(
            {
                "live_price": round(lp, 4),
                "ma5_amp_pct": ma5_amp,
                "premarket_vwap": pre_stats["vwap"],
                "premarket_high": pre_stats["high"],
                "premarket_low": pre_stats["low"],
                "premarket_amp_pct": pre_stats["amp_pct"],
                "premarket_est_low": pre_stats["est_low"],
                "premarket_est_high": pre_stats["est_high"],
                "regular_vwap": reg_stats["vwap"],
                "regular_high": reg_stats["high"],
                "regular_low": reg_stats["low"],
                "regular_amp_pct": reg_stats["amp_pct"],
                "regular_est_low": reg_stats["est_low"],
                "regular_est_high": reg_stats["est_high"],
                "day_vwap": active_vwap,
                "day_high": all_stats["high"],
                "day_low": all_stats["low"],
                "day_amp_pct": all_stats["amp_pct"],
            }
        )
        # [4bot v2.4.0 · Case 93] 🗡️ 암살자 4대 지표 새 키만 추가 (자체 예외 격리 · 기존 키 무변경)
        assn_fields = _compute_assassin_anchor_fields(
            api_candles=candles,
            daily_candles=daily_candles,
            dt_now=dt_now,
            today_str=today_str,
            lp=lp,
            ma5_amp=ma5_amp,
            reg_vwap_existing=safe_float(reg_stats.get("vwap"), 0.0),
            prev_day_close=prev_day_close,
            symbol=sym,
        )
        for a_key, a_val in assn_fields.items():
            if a_key not in out:
                out[a_key] = a_val
        return refresh_metrics_with_live_tick(out, lp, now_est=dt_now, symbol=sym)
    except Exception as exc:
        # Case 79: 데이마켓 등 장외 시간대 캔들 결측 시에도 소음 없이 조용히 디버그 로깅
        logger.debug("compute_soxl_quant_metrics_1m 연산 폴백(묵음): %s", exc)
        # [4bot v2.4.0 · Case 93] 위 연산이 실패해도 암살자 4대 지표 새 키는 API 1분봉만으로 따로 산출 (기존 키 무변경)
        fb_out = dict(default_out)
        for a_key, a_val in _compute_assassin_anchor_fields(
            api_candles=candles,
            daily_candles=daily_candles,
            dt_now=dt_now,
            today_str=today_str,
            lp=lp,
            ma5_amp=6.50,
            reg_vwap_existing=0.0,
            prev_day_close=prev_day_close,
            symbol=sym,
        ).items():
            if a_key not in fb_out:
                fb_out[a_key] = a_val
        return refresh_metrics_with_live_tick(fb_out, lp, now_est=dt_now, symbol=sym)


# ---------------------------------------------------------------------------
# [핵심 4] 실시간 틱(live_price) O(1) 무부하 합성기 (refresh_metrics_with_live_tick — Case 84 & Case 88)
# ---------------------------------------------------------------------------
# [4bot v2.4.0 · 원작 c4ad8d6 Case 93 · 암살자 전용] QQQ 방향성 안전망 지표 (원작 그대로)
def compute_qqq_macro_metrics_1m(
    candles: List[Dict[str, Any]],
    live_price: float = 0.0,
    now_est: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    # NEW: 나스닥 100 추종 QQQ 1분봉 기반 방향성 인지 3단계 안전망 지표 산출기
    """
    return compute_soxl_quant_metrics_1m(
        candles=candles,
        live_price=live_price,
        now_est=now_est,
        daily_candles=None,
        prev_day_close=0.0,
        symbol="QQQ",
    )


def refresh_metrics_with_live_tick(
    base_metrics: Optional[Dict[str, Any]],
    live_price: float,
    now_est: Optional[datetime] = None,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    """
    # [Case 84 & Case 88 : 실시간 틱 O(1) 합성 · dt_now.minute 변수명 정합성 락온 · 장마감 30분전 0주/돌파 컷오프 상태 동기화]:
    1) 실시간 현재가(live_price)를 인메모리 1분봉 저장소(_LIVE_1M_BAR_STORE)에 즉시 반영한다.
    2) 만약 새로운 분(minute)으로 넘어갔거나 기존 base_metrics 의 prev_bar_close 가 0.0 인 경우,
       인메모리 1분봉 저장소에서 직전 완성봉 기저값(prev_bar_close, prev_avg_gain, prev_avg_loss)을 즉시 복원한다.
    3) prev_bar_close > 0.0 이면 매 1.5초 실시간 현재가 변동을 Wilder's RSI(14) 공식에 즉시 합성하여
       레이더에 살아 움직이는 실시간 RSI(14)를 제공한다!
    """
    dt_now = now_est.astimezone(EST_TZ) if now_est else datetime.now(EST_TZ)
    dt = dt_now
    hm = dt_now.hour * 100 + dt_now.minute
    _, cur_bucket_id, _, gate_info = evaluate_buy_gate_bucket_status(
        now_est=dt, buy_interval_min=LOCKED_BUY_INTERVAL_MIN
    )

    met = dict(base_metrics) if isinstance(base_metrics, dict) else {}
    lp = safe_float(live_price, 0.0)
    if lp <= 0.0:
        lp = safe_float(met.get("live_price"), 0.0)
    else:
        met["live_price"] = round(lp, 4)

    # [4bot v2.4.0 · Case 93] symbol 미지정(기존 스나이퍼 호출)이면 SOXL 저장소 그대로 사용
    sym = str(symbol or TARGET_SYMBOL).upper().strip()
    cur_min_key, mem_bar_cnt = _record_live_tick_to_memory_bar(
        sym, lp, now_est=dt_now
    )
    prev_min_key = str(met.get("cur_bar_minute_key") or "")

    # 새로운 1분봉 경계 진입 또는 기저값(prev_bar_close) 미초기화 시 인메모리 1분봉으로 기저값 즉시 갱신
    if mem_bar_cnt >= 2 and (
        safe_float(met.get("prev_bar_close"), 0.0) <= 0.0
        or (prev_min_key and prev_min_key != cur_min_key)
    ):
        mem_ha_rsi = _recompute_ha_rsi_from_memory_store(sym)
        if isinstance(mem_ha_rsi, dict):
            met.update(mem_ha_rsi)

    met["cur_bar_minute_key"] = cur_min_key

    ma5_amp = max(1.0, safe_float(met.get("ma5_amp_pct"), 6.50))
    amp_ratio = ma5_amp / 100.0

    # 1) 실시간 틱 기반 Heikin-Ashi 양/음봉 및 Wilder's RSI(14) O(1) 상수 시간 합성
    if lp > 0.0:
        prev_ho = safe_float(met.get("prev_ha_open"), lp)
        prev_hc = safe_float(met.get("prev_ha_close"), lp)
        cur_o = safe_float(met.get("cur_bar_open"), lp)
        if cur_o <= 0.0:
            cur_o = lp
        cur_h = max(safe_float(met.get("cur_bar_high"), lp), lp)
        cur_l_raw = safe_float(met.get("cur_bar_low"), 0.0)
        cur_l = min(cur_l_raw, lp) if cur_l_raw > 0.0 else lp
        live_ha_open = (prev_ho + prev_hc) * 0.5
        live_ha_close = (cur_o + cur_h + cur_l + lp) * 0.25
        is_bull = bool(live_ha_close >= live_ha_open)
        met["cur_bar_open"] = round(cur_o, 4)
        met["cur_bar_high"] = round(cur_h, 4)
        met["cur_bar_low"] = round(cur_l, 4)
        met["ha_open"] = round(live_ha_open, 4)
        met["ha_close"] = round(live_ha_close, 4)
        met["ha_bull"] = is_bull
        met["ha_badge"] = "🕯️HA양봉" if is_bull else "🌑HA음봉"

        prev_b_close = safe_float(met.get("prev_bar_close"), 0.0)
        prev_avg_g = max(0.0, safe_float(met.get("prev_avg_gain"), 0.0))
        prev_avg_l = max(0.0, safe_float(met.get("prev_avg_loss"), 0.0))

        if prev_b_close > 0.0:
            diff = lp - prev_b_close
            cur_g = max(0.0, diff)
            cur_l_val = max(0.0, -diff)
            if prev_avg_g <= 1e-12 and prev_avg_l <= 1e-12:
                live_avg_g = cur_g / 14.0
                live_avg_l = cur_l_val / 14.0
            else:
                live_avg_g = (prev_avg_g * 13.0 + cur_g) / 14.0
                live_avg_l = (prev_avg_l * 13.0 + cur_l_val) / 14.0

            if live_avg_g <= 1e-12 and live_avg_l <= 1e-12:
                live_rsi = 50.0
            elif live_avg_l <= 1e-12:
                live_rsi = 100.0
            else:
                rs = live_avg_g / live_avg_l
                live_rsi = 100.0 - (100.0 / (1.0 + rs))
            met["rsi_14"] = round(live_rsi, 2)

        if not bool(met.get("rsi_ready", False)) and mem_bar_cnt >= 14:
            met["rsi_ready"] = True

    # 2) 현재 세션(프리장 04:00 ~ 09:29 / 정규장 09:30 ~ 16:00) 고/저가 및 예상 밴드 실시간 갱신
    if lp > 0.0 and 400 <= hm <= 929:
        ph = max(safe_float(met.get("premarket_high"), 0.0), lp)
        pl_prev = safe_float(met.get("premarket_low"), 0.0)
        pl = min(pl_prev, lp) if pl_prev > 0.0 else lp
        p_amp = ((ph - pl) / pl) * 100.0 if pl > 0.0 else 0.0
        met["premarket_high"] = round(ph, 4)
        met["premarket_low"] = round(pl, 4)
        met["premarket_amp_pct"] = round(p_amp, 2)
        met["premarket_est_high"] = round(max(ph, pl * (1.0 + amp_ratio)), 2)
        met["premarket_est_low"] = round(min(pl, ph / (1.0 + amp_ratio)), 2)
        if safe_float(met.get("premarket_vwap"), 0.0) <= 0.0:
            met["premarket_vwap"] = round(lp, 4)
    elif lp > 0.0 and 930 <= hm <= 1600:
        rh = max(safe_float(met.get("regular_high"), 0.0), lp)
        rl_prev = safe_float(met.get("regular_low"), 0.0)
        rl = min(rl_prev, lp) if rl_prev > 0.0 else lp
        r_amp = ((rh - rl) / rl) * 100.0 if rl > 0.0 else 0.0
        met["regular_high"] = round(rh, 4)
        met["regular_low"] = round(rl, 4)
        met["regular_amp_pct"] = round(r_amp, 2)
        met["regular_est_high"] = round(max(rh, rl * (1.0 + amp_ratio)), 2)
        met["regular_est_low"] = round(min(rl, rh / (1.0 + amp_ratio)), 2)
        if safe_float(met.get("regular_vwap"), 0.0) <= 0.0:
            met["regular_vwap"] = round(lp, 4)

    met["bucket_10m"] = cur_bucket_id
    met["is_new_cycle_cutoff"] = is_late_regular_new_cycle_cutoff_window(
        hm, now_est=dt_now
    )
    met["next_gate_hm_str"] = gate_info.get("next_gate_hm_str", "04:07 EST")
    met["session_label"] = gate_info.get("session_label", "")
    met["updated_est"] = dt_now.strftime("%m-%d %H:%M:%S EST")
    _refresh_assassin_tick_fields(met, lp, dt_now, sym)
    return met


def _refresh_assassin_tick_fields(
    met: Dict[str, Any], lp: float, dt_now: datetime, sym: str
) -> None:
    """
    # NEW [4bot 2번 v2.4.0 · 원작 c4ad8d6 Case 93 · 🗡️ 암살자 전용 새 키만 O(1) 갱신 · 기존 스나이퍼 키 무변경]:
    단기 변화율(vel_1m/3m/10m) · 당일 래치의 전일종가/04:07 프리시가/프리VWAP 복원 · 04:07~09:29 첫 틱 프리시가 래치 ·
    프리시가 대비 하락 진폭(bear_drop_amp_pct). 예외는 묵음 처리한다.
    """
    try:
        if lp <= 0.0:
            return
        today_str = dt_now.strftime("%Y-%m-%d")
        hm = dt_now.hour * 100 + dt_now.minute
        prev_b_close = safe_float(met.get("prev_bar_close"), 0.0)
        if prev_b_close > 0.0:
            met["vel_1m_pct"] = round((lp - prev_b_close) / prev_b_close * 100.0, 4)
        c_3m = safe_float(met.get("close_3m_ago"), prev_b_close)
        c_10m = safe_float(met.get("close_10m_ago"), prev_b_close)
        if c_3m > 0.0:
            met["vel_3m_pct"] = round((lp - c_3m) / c_3m * 100.0, 4)
        if c_10m > 0.0:
            met["vel_10m_pct"] = round((lp - c_10m) / c_10m * 100.0, 4)
        met["vel_max_3m_10m_pct"] = round(
            max(safe_float(met.get("vel_3m_pct"), 0.0), safe_float(met.get("vel_10m_pct"), 0.0)), 4
        )

        latch = _get_daily_anchor_latch(sym, today_str)
        latched_prev_c = safe_float(latch.get("prev_reg_close"), 0.0)
        latched_pre_o = safe_float(latch.get("pre_open_price"), 0.0)
        latched_pre_stats = latch.get("pre_stats")
        if latched_prev_c > 0.0:
            met["prev_reg_close"] = latched_prev_c
            met["prev_day_close"] = latched_prev_c
            met["found_true_prev_close"] = True
        if latched_pre_o > 0.0:
            met["pre_open_price"] = latched_pre_o
            met["found_true_pre_open"] = True
        if isinstance(latched_pre_stats, dict) and safe_float(latched_pre_stats.get("vwap"), 0.0) > 0.0:
            if (
                safe_float(met.get("assn_premarket_vwap"), 0.0) <= 0.0
                or hm > 929
                or not bool(met.get("found_true_pre_vwap", False))
            ):
                met["assn_premarket_vwap"] = round(safe_float(latched_pre_stats.get("vwap"), 0.0), 4)
                met["found_true_pre_vwap"] = True
        if 407 <= hm <= 929 and safe_float(met.get("assn_premarket_vwap"), 0.0) <= 0.0:
            # 프리장 첫 틱: 원작처럼 현재가로 임시 표시 (진성 래치에는 저장하지 않음)
            met["assn_premarket_vwap"] = round(lp, 4)

        pre_open_p = safe_float(met.get("pre_open_price"), 0.0)
        if pre_open_p <= 0.0 and 407 <= hm <= 929:
            pre_open_p = round(lp, 4)
            met["pre_open_price"] = pre_open_p
            met["found_true_pre_open"] = True
            _update_daily_anchor_latch(symbol=sym, target_date=today_str, pre_open_price=pre_open_p)
        if pre_open_p > 0.0:
            met["bear_drop_amp_pct"] = round(max(0.0, (pre_open_p - lp) / pre_open_p * 100.0), 4)
        else:
            met["pre_open_price"] = 0.0
            met["bear_drop_amp_pct"] = 0.0
        if safe_float(met.get("prev_reg_close"), 0.0) <= 0.0:
            met["prev_reg_close"] = round(
                safe_float(met.get("prev_day_close"), pre_open_p if pre_open_p > 0.0 else lp), 4
            )
        if safe_float(met.get("prev_day_close"), 0.0) <= 0.0:
            met["prev_day_close"] = met["prev_reg_close"]
    except Exception as exc:
        logger.debug("암살자 틱 지표 갱신 폴백(묵음): %s", exc)


# 하위 호환 별칭 (타 모듈 임포트 호환 100% 보장)
compute_quant_metrics_1m = compute_soxl_quant_metrics_1m
calculate_soxl_quant_metrics_1m = compute_soxl_quant_metrics_1m
is_weekend_closed = is_weekend_nyse_closed
