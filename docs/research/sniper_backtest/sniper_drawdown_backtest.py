#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sniper_drawdown_backtest.py — 2번 토스 스나이퍼 물림 대처(5-1 짝 매도 · 5-2 졸업 트레일링 · 5-3 쿼터 정리) 백테스트
버전: 0.1.0 (2026-11-05, Claude) · 연구용 별도 스크립트 · 봇 코드 수정 없음

[무엇을 하나]
  - toss_sniper/quant_engine.py 의 순수 판정 함수를 그대로 불러 과거 SOXL 가격 위에서 봇 규칙을 재생한다.
  - 계획 문서 docs/log/2026-11-05_claude_sniper-drawdown-plan.md 의 5-1·5-2·5-3을 각각 켜고 끌 수 있다.
  - 9개 시나리오(현행·단독 3·조합 3·묶음·SOXL 단순 보유)를 같은 데이터·같은 시작 조건으로 비교한다.

[하지 않는 것]
  - 주문·네트워크·계좌·비밀값 사용 없음. 봇 폴더에 아무것도 쓰지 않음(.pyc 도 만들지 않음).
  - 토스 계좌 겹침(2번 수혈 ↔ 3번 적립)은 해결하지 않음. 예비시드 최대 사용량만 3번 영향 대리 지표로 보고.

[데이터 출처 — 이 스크립트는 데이터를 받지 않는다. 사용자가 준비한 CSV만 읽는다]
  - 일봉: --daily 로 지정한 CSV. 권장 출처 = Yahoo Finance(yfinance 라이브러리, 분할 조정 OHLC, auto_adjust=False).
          받는 명령은 이 스크립트 밖(서버 SSH 명령)에서 따로 실행한다. 실제로 쓴 출처·받은 날짜를 결과 파일에 적는다(--data-note).
  - 5분봉: --intraday 로 지정한 CSV(선택). 2018년 이후 프리·애프터·오버나이트 포함 5분봉은 무료 출처에서 구할 수 없음
          (yfinance 는 최근 60일 한도). 없으면 해당 기간은 일봉으로 돌리고, 세션 규칙 재현 불가로 결과에 표시한다.
  - CSV 형식: 일봉 = date,open,high,low,close[,split] / 분봉 = datetime(미국 동부시각),open,high,low,close
  - 가격은 '분할 전 실제 거래 가격'이어야 한다(센트 반올림·정수 주 계산이 실제와 같아지도록). split 열이 있으면
    그 날 시가 전에 보유 주수×비율, 단가÷비율로 바꾼다. Yahoo 분할 조정 가격을 실제 가격으로 되돌리는 방법은
    함께 준 서버 명령(데이터 받기)에 있다.
  - 데이터가 없으면 지어내지 않고 무엇이 없는지 출력한 뒤 종료(코드 2). --selftest 의 합성 가격은 코드 점검 전용이며 결과로 쓰지 않는다.

[실행 예]
  python3 sniper_drawdown_backtest.py --bot-dir /home/gieokkim/toss_sniper --daily soxl_daily.csv --out bt_out
  python3 sniper_drawdown_backtest.py --bot-dir ... --daily ... --config my_config.json      # 설정값 바꿔 돌리기
  python3 sniper_drawdown_backtest.py --bot-dir ... --selftest                                # 코드 점검만

[재현 범위와 단순화 — 결과 해석 때 반드시 함께 볼 것]
  재현(quant_engine 함수 그대로): get_golden8_prog_thresholds(간격·목표·래칫), compute_golden8_quota_qty(8% 1회분),
    evaluate_guard30_and_reserve_injection(30% 가드·예비시드 수혈), compute_reserve_repayment_on_zero(졸업 상환),
    evaluate_step_up_2x_dip_signal(신저가 추매·스텝업), evaluate_l2_only_hybrid_reentry_signal(1층 재장전),
    evaluate_sub_grid_dip_signal / compute_sub4_quota_qty / compute_sub_grid_available_idle_cash(서브),
    vrev_add_quota_lot_and_merge_2tier / add_lot_to_sub_grid(층 적재·합병), relabel_upper_grid_tiers /
    relabel_sub_upper_grid_tiers(매도 후 층 재배치), evaluate_multi_grid_sell_targets(개별 매도·졸업),
    compute_upper_2_to_12_moving_avg(졸업가), resolve_affordable_buy_qty(매수 수량).
  플러그인 쪽 갱신 규칙(sniper_plugin._commit_filled_buy_to_stratum_ledger, sniper_exit_plugin 매도 정산,
    defense_plugin.execute_1600_daily_closing_settlement_plugin 무매매일)은 같은 규칙으로 이 파일에 옮겨 적었다.
  단순화: 60초 타임쉴드·10분 게이트·미체결 잔량 보충(TOPUP)·재앵커(vrev_reanchor_single_tier_quota)·윗꼬리 재평가·
    지하층(basement_pocket)·수동 매매는 재현하지 않음. 체결은 목표가 터치 시 전량 체결 가정(+ 미끄러짐 민감도).
    일봉 구간은 봉 안 경로를 시가→저가→고가→종가(양봉) / 시가→고가→저가→종가(음봉)로 가정하고, 정규장 시간만 있다고 본다.
  예비시드: 외부 미할당 달러가 남은 예비 회분만큼 항상 있다고 가정(실계좌 잔고·3번 몫은 모름).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True  # 봇 폴더에 __pycache__ 를 만들지 않는다

SCRIPT_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# 설정값 — 기본값 = 계획 문서 시작값. --config JSON 으로 어떤 키든 덮어쓸 수 있다.
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: Dict[str, Any] = {
    # 공통 시작 조건 (지시문 v2)
    "initial_seed_usd": 10000.0,
    "threshold_mode": "WIDE_RUNWAY",
    "grid_merge_mode": "L2_L7_MERGE_SORT",
    "sub_grid_enabled": True,
    "max_reserve_portions": 6,
    "round_trip_fee_pct": 0.14,          # 왕복 0.14% → 편도 0.07%
    "slippage_pct_list": [0.0, 0.1],     # 계획 §6: 0.1% 미끄러짐 민감도
    "portion_mode": "COMP_08PCT",
    # 5-1 짝 매도
    "pair_enabled": False,
    "pair_offset_ratio": 0.70,           # 체결 이익의 70%를 상쇄에 사용
    "pair_high_tier_pct": 12.0,          # 1층 매수가 대비 +12% 이상 층만 대상
    "pair_include_sub_profit": True,     # 서브 개별 익절 이익도 재원에 포함
    "pair_fund_reset_on_cycle_end": True,
    # 5-2 졸업 트레일링
    "trail_enabled": False,
    "trail_min_ratchet_lots": 6,         # 사이클 최고 회차 6 이상만
    "trail_base_pct": 3.0,               # k = 3% + 보유 거래일 × 0.1%p
    "trail_per_day_pct": 0.1,
    "trail_cap_pct": 6.0,                # 상한 6%
    "trail_max_days": 10,                # 트레일 시작 후 10거래일 지나면 전량 매도
    "trail_regular_session_only": True,  # 오버나이트·장외에서는 바닥선·트레일 판정 안 함
    # 5-3 쿼터 정리
    "quota_enabled": False,
    "quota_trigger_days": 40,            # 사이클 보유 40거래일
    "quota_trigger_loss_pct": 25.0,      # 본 평가손실 −25%(본 원가 대비)
    "quota_trigger_reserve_portions": 4, # 예비시드 4회분 이상 사용
    "quota_sell_ratio": 0.25,            # 본 보유량 25%
    "quota_max_times": 2,                # 최대 2회
    "quota_gap_days": 10,                # 재발동 간격 10거래일
    # 필수 구간 (지시문 v2)
    "required_windows": [
        ["2018년 말", "2018-10-01", "2018-12-31"],
        ["2020-03", "2020-02-15", "2020-04-30"],
        ["2022", "2022-01-01", "2022-12-31"],
        ["2025-04", "2025-03-15", "2025-05-15"],
    ],
}

SCENARIOS: List[Tuple[str, Dict[str, bool]]] = [
    ("현행", {}),
    ("5-1만", {"pair_enabled": True}),
    ("5-2만", {"trail_enabled": True}),
    ("5-3만", {"quota_enabled": True}),
    ("5-1+5-2", {"pair_enabled": True, "trail_enabled": True}),
    ("5-1+5-3", {"pair_enabled": True, "quota_enabled": True}),
    ("5-2+5-3", {"trail_enabled": True, "quota_enabled": True}),
    ("5-1+5-2+5-3 묶음", {"pair_enabled": True, "trail_enabled": True, "quota_enabled": True}),
]
BUY_AND_HOLD = "SOXL 단순 보유"


# ---------------------------------------------------------------------------
# 엔진 불러오기 (읽기만)
# ---------------------------------------------------------------------------
def load_engine(bot_dir: str):
    bot_dir = os.path.abspath(os.path.expanduser(bot_dir))
    if not os.path.isfile(os.path.join(bot_dir, "quant_engine.py")):
        print(f"[막힘] quant_engine.py 를 찾지 못함: {bot_dir}")
        sys.exit(2)
    if bot_dir not in sys.path:
        sys.path.insert(0, bot_dir)
    import quant_engine as qe  # noqa: E402
    return qe


# ---------------------------------------------------------------------------
# 데이터
# ---------------------------------------------------------------------------
@dataclass
class Bar:
    day: date
    hm: int            # 미국 동부시각 HHMM (일봉은 1600)
    o: float
    h: float
    l: float
    c: float
    intraday: bool
    split: float = 1.0  # 이 날 시가 전에 적용되는 주식 분할 비율(2.0 = 1주→2주). 1.0 = 없음


def _f(x: str) -> float:
    return float(str(x).replace(",", "").strip())


def read_daily_csv(path: str) -> List[Bar]:
    out: List[Bar] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        cols = {k.lower().strip(): k for k in (rd.fieldnames or [])}
        need = ["date", "open", "high", "low", "close"]
        miss = [n for n in need if n not in cols]
        if miss:
            print(f"[막힘] 일봉 CSV 열 없음: {miss} (필요: {need})")
            sys.exit(2)
        for r in rd:
            try:
                d = datetime.strptime(r[cols["date"]].strip()[:10], "%Y-%m-%d").date()
                o, h, l, c = (_f(r[cols[k]]) for k in ("open", "high", "low", "close"))
                sp = _f(r[cols["split"]]) if "split" in cols and str(r[cols["split"]]).strip() else 1.0
            except Exception:
                continue
            if min(o, h, l, c) <= 0:
                continue
            out.append(Bar(d, 1600, o, max(o, h, l, c), min(o, h, l, c), c, False, sp if sp > 0 else 1.0))
    out.sort(key=lambda b: b.day)
    return out


def read_intraday_csv(path: str) -> List[Bar]:
    out: List[Bar] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        cols = {k.lower().strip(): k for k in (rd.fieldnames or [])}
        need = ["datetime", "open", "high", "low", "close"]
        miss = [n for n in need if n not in cols]
        if miss:
            print(f"[막힘] 분봉 CSV 열 없음: {miss} (필요: {need}, datetime 은 미국 동부시각)")
            sys.exit(2)
        for r in rd:
            try:
                raw = r[cols["datetime"]].strip()[:16].replace("T", " ")
                dt = datetime.strptime(raw, "%Y-%m-%d %H:%M")
                o, h, l, c = (_f(r[cols[k]]) for k in ("open", "high", "low", "close"))
            except Exception:
                continue
            if min(o, h, l, c) <= 0:
                continue
            # 오버나이트(20:00~23:59)는 다음 거래일 세션으로 묶는다
            d = dt.date() + (timedelta(days=1) if dt.hour >= 20 else timedelta(0))
            out.append(Bar(d, dt.hour * 100 + dt.minute, o, max(o, h, l, c), min(o, h, l, c), c, True))
    out.sort(key=lambda b: (b.day, (b.hm + 400) % 2400))
    return out


def merge_bars(daily: List[Bar], intraday: List[Bar]) -> List[List[Bar]]:
    """거래일별 봉 묶음. 분봉이 있는 날은 분봉, 없는 날은 일봉 1개."""
    by_day: Dict[date, List[Bar]] = {}
    for b in intraday:
        by_day.setdefault(b.day, []).append(b)
    for b in daily:
        if b.day not in by_day:
            by_day[b.day] = [b]
        elif abs(b.split - 1.0) > 1e-9:
            by_day[b.day][0].split = b.split
    return [by_day[d] for d in sorted(by_day)]


def synthetic_days(n_days: int = 1500, seed: int = 7) -> List[List[Bar]]:
    """--selftest 전용 합성 가격(코드 경로 점검용). 결과로 쓰지 않는다."""
    rnd = random.Random(seed)
    p = 30.0
    out = []
    d = date(2001, 1, 2)
    for i in range(n_days):
        mu = -0.004 if (i // 250) % 2 else 0.003
        r = rnd.gauss(mu, 0.045)
        o = p * (1 + rnd.gauss(0, 0.01))
        c = max(0.5, o * (1 + r))
        h = max(o, c) * (1 + abs(rnd.gauss(0, 0.02)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, 0.02)))
        out.append([Bar(d, 1600, o, h, l, c, False)])
        p = c
        d += timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
    return out


# ---------------------------------------------------------------------------
# 시뮬레이터
# ---------------------------------------------------------------------------
@dataclass
class CycleRec:
    start_idx: int
    end_idx: int = -1
    net_usd: float = 0.0
    max_lots: int = 0
    end_reason: str = ""


class Sim:
    def __init__(self, qe, cfg: Dict[str, Any], slip_pct: float):
        self.qe = qe
        self.cfg = cfg
        self.slip = slip_pct / 100.0
        self.fee_rt = float(cfg["round_trip_fee_pct"])
        self.fee1 = self.fee_rt / 200.0
        seed = float(cfg["initial_seed_usd"])
        self.st: Dict[str, Any] = {
            "initial_seed_usd": seed,
            "cumulative_realized_net_usd": 0.0,
            "free_cash_usd": seed,
            "injected_reserve_usd": 0.0,
            "used_reserve_portions_cnt": 0,
            "threshold_mode": cfg["threshold_mode"],
            "grid_merge_mode": cfg["grid_merge_mode"],
            "cycle_ratchet_max_lots": 0,
            "sub_ratchet_max_lots": 0,
            "anchor_price": 0.0,
            "cycle_min_buy_price": 0.0,
            "sub_anchor_price": 0.0,
            "sub_cycle_min_buy_price": 0.0,
            "main_consec_frozen_days": 0,
            "sub_consec_frozen_days": 0,
            "round_trip_fee_rate_pct": self.fee_rt,
        }
        self.B: List[Any] = []   # 본 층 (StratumBucket)
        self.S: List[Any] = []   # 서브 층
        # 계획 문서 새 필드 (원장에 없는 것 — 시뮬레이터 안에서만)
        self.cycle_start_idx = -1
        self.pair_fund = 0.0
        self.trail_active = False
        self.trail_floor = 0.0
        self.trail_peak = 0.0
        self.trail_start_idx = -1
        self.quota_count = 0
        self.quota_last_idx = -10 ** 9
        # 기록
        self.day_idx = 0
        self.main_traded = False
        self.sub_traded = False
        self.cycles: List[CycleRec] = []
        self.cur_cycle: Optional[CycleRec] = None
        self.max_used_reserve = 0
        self.max_injected = 0.0
        self.realized_by: Dict[str, float] = {k: 0.0 for k in
            ("개별", "졸업", "서브", "짝매도", "트레일", "쿼터")}
        self.event_cnt: Dict[str, int] = {}
        self.blocked_buy_cnt = 0
        self.equity: List[Tuple[date, float]] = []
        self.locked_usd_days = 0.0
        self.invested_usd_days = 0.0
        self.max_unrealized_loss = 0.0
        self.max_unrealized_loss_pct = 0.0
        # 입출금(예비시드 수혈·상환)을 반영한 기준가: 1단위 = 시드/시드
        self.units = seed

    def total_equity(self, price: float) -> float:
        return self.st["free_cash_usd"] + (self.qty(self.B) + self.qty(self.S)) * price

    def _flow(self, amount: float, price: float):
        """amount>0 수혈 입금, <0 상환 출금. 입출금 직전 기준가로 단위를 사고판다."""
        eq_before = self.total_equity(price) - amount
        nav = eq_before / self.units if self.units > 0 and eq_before > 0 else 1.0
        self.units = max(1e-9, self.units + amount / nav)

    # ---- 기본 값 ----
    def _ev(self, k: str, n: int = 1):
        self.event_cnt[k] = self.event_cnt.get(k, 0) + n

    def lots(self, bl) -> int:
        return sum(max(1, b.lot_count) for b in bl)

    def cost(self, bl) -> float:
        return sum(b.actual_cost_usd for b in bl)

    def qty(self, bl) -> int:
        return sum(b.qty for b in bl)

    def core_eq(self) -> float:
        st = self.st
        return max(st["initial_seed_usd"],
                   st["free_cash_usd"] + self.cost(self.B) + self.cost(self.S) - st["injected_reserve_usd"])

    def thresholds(self, sub: bool = False):
        qe = self.qe
        if sub:
            return qe.get_golden8_prog_thresholds(self.lots(self.S), self.st["threshold_mode"],
                                                  self.st["sub_ratchet_max_lots"])
        return qe.get_golden8_prog_thresholds(self.lots(self.B), self.st["threshold_mode"],
                                              self.st["cycle_ratchet_max_lots"])

    def cycle_age(self) -> int:
        return (self.day_idx - self.cycle_start_idx) if self.cycle_start_idx >= 0 else 0

    # ---- 매수 ----
    def _guard_and_qty(self, exec_p: float, target_qty: int, budget: float,
                       is_dip: bool, l1_cost: float) -> int:
        qe, st = self.qe, self.st
        max_res = int(self.cfg["max_reserve_portions"])
        rem = max(0, max_res - st["used_reserve_portions_cnt"])
        bp = st["free_cash_usd"] + rem * budget  # 가정: 남은 예비 회분만큼 외부 미할당 달러 존재
        g = qe.evaluate_guard30_and_reserve_injection(
            free_cash_usd=st["free_cash_usd"], broker_bp_usd=bp, exec_price=exec_p,
            portion_budget=budget, l1_actual_cost_usd=l1_cost, is_dip_promotion=is_dip,
            used_reserve_portions_cnt=st["used_reserve_portions_cnt"], max_reserve_portions=max_res,
            round_trip_fee_rate_pct=self.fee_rt)
        if not g.get("should_proceed"):
            self.blocked_buy_cnt += 1
            return 0
        if g.get("action") == "INJECT_AND_PROCEED":
            inj = float(g.get("inject_usd") or 0.0)
            st["injected_reserve_usd"] += inj
            st["used_reserve_portions_cnt"] += int(g.get("inject_portions") or 0)
            st["free_cash_usd"] += inj
            self._flow(inj, exec_p)
            self.max_used_reserve = max(self.max_used_reserve, st["used_reserve_portions_cnt"])
            self.max_injected = max(self.max_injected, st["injected_reserve_usd"])
            self._ev("예비시드 수혈")
        q = qe.resolve_affordable_buy_qty(
            target_qty=target_qty, price_t=exec_p, free_cash_usd=st["free_cash_usd"],
            broker_buying_power_usd=st["free_cash_usd"], max_portion_budget_usd=budget,
            round_trip_fee_rate_pct=self.fee_rt)
        try:
            q = int(q[0] if isinstance(q, (tuple, list)) else q)
        except Exception:
            q = 0
        if q <= 0:
            self.blocked_buy_cnt += 1
        return max(0, q)

    def buy_main(self, price: float, tag: str, quota_ref: float, stepped_min: float = 0.0) -> bool:
        qe, st = self.qe, self.st
        exec_p = round(price * (1 + self.slip), 4)
        was_empty = len(self.B) == 0
        tq, budget = qe.compute_golden8_quota_qty(
            anchor_price=quota_ref if quota_ref > 0 else exec_p, current_total_equity=self.core_eq(),
            initial_seed_usd=st["initial_seed_usd"], portion_mode=self.cfg["portion_mode"], exec_price=exec_p)
        tq = min(int(tq), max(1, int(math.floor((float(budget) + 1e-9) / exec_p))))
        l1c = self.B[0].actual_cost_usd if (self.B and qe.has_active_l1_bucket(self.B)) else 0.0
        q = self._guard_and_qty(exec_p, tq, float(budget), tag == "DIP_1FL", l1c)
        if q <= 0:
            return False
        spent = round(q * exec_p * (1 + self.fee1), 4)
        st["free_cash_usd"] -= spent
        self.B = qe.vrev_add_quota_lot_and_merge_2tier(
            queue=self.B, buy_qty=q, buy_price=exec_p, actual_spent_usd=spent, lot_type=tag,
            max_tiers=qe.MAX_GRID_TIERS_7, merge_mode=st["grid_merge_mode"])
        # sniper_plugin._commit_filled_buy_to_stratum_ledger 와 같은 갱신 규칙
        old_min = st["cycle_min_buy_price"]
        step_fill = stepped_min > 0.0 and tag not in ("REENTRY_1FL", "TOPUP_1FL")
        if was_empty or old_min <= 0.0:
            st["cycle_min_buy_price"] = exec_p
        elif step_fill:
            st["cycle_min_buy_price"] = round(min(stepped_min, exec_p), 4)
        else:
            st["cycle_min_buy_price"] = round(min(old_min, exec_p), 4)
        held = self.lots(self.B)
        st["cycle_ratchet_max_lots"] = held if (was_empty or step_fill) else max(st["cycle_ratchet_max_lots"], held)
        if was_empty:
            self.cycle_start_idx = self.day_idx
            self.cur_cycle = CycleRec(start_idx=self.day_idx)
            self.quota_count = 0
            self.quota_last_idx = -10 ** 9
        if self.cur_cycle:
            self.cur_cycle.max_lots = max(self.cur_cycle.max_lots, st["cycle_ratchet_max_lots"])
        self.main_traded = True
        self._ev("본 매수:" + tag + ("(스텝업)" if step_fill else ""))
        return True

    def buy_sub(self, price: float, tag: str) -> bool:
        qe, st = self.qe, self.st
        exec_p = round(price * (1 + self.slip), 4)
        was_empty = len(self.S) == 0
        core = self.core_eq()
        idle = qe.compute_sub_grid_available_idle_cash(
            free_cash_usd=st["free_cash_usd"], core_equity_usd=core,
            broker_buying_power_usd=st["free_cash_usd"], reserve_main_portions=qe.SUB_RESERVE_MAIN_PORTIONS
            if hasattr(qe, "SUB_RESERVE_MAIN_PORTIONS") else 0.5)
        avail = float(idle.get("avail_idle_cash_usd") or 0.0)
        ref = st["sub_anchor_price"] if (st["sub_anchor_price"] > 0 and not was_empty) else exec_p
        tq, budget = qe.compute_sub4_quota_qty(sub_anchor_price=ref, current_core_equity=core,
                                              initial_seed_usd=st["initial_seed_usd"], exec_price=exec_p)
        q = min(int(tq), int(math.floor(avail / (exec_p * (1 + self.fee1)))))
        if q <= 0:
            self.blocked_buy_cnt += 1
            return False
        spent = round(q * exec_p * (1 + self.fee1), 4)
        st["free_cash_usd"] -= spent
        self.S = qe.add_lot_to_sub_grid(sub_queue=self.S, buy_qty=q, buy_price=exec_p, actual_spent_usd=spent,
                                        lot_type=tag, max_tiers=qe.SUB_MAX_TIERS_3,
                                        merge_mode=qe.DEFAULT_SUB_MERGE_MODE)
        old_min = st["sub_cycle_min_buy_price"]
        st["sub_cycle_min_buy_price"] = exec_p if (was_empty or old_min <= 0) else round(min(old_min, exec_p), 4)
        held = self.lots(self.S)
        st["sub_ratchet_max_lots"] = held if was_empty else max(st["sub_ratchet_max_lots"], held)
        if was_empty:
            st["sub_anchor_price"] = exec_p
        self.sub_traded = True
        self._ev("서브 매수:" + tag)
        return True

    # ---- 매도 ----
    def _realize(self, sold: List[Any], exec_p: float) -> float:
        proceeds = sum(b.qty for b in sold) * exec_p * (1 - self.fee1)
        pnl = proceeds - sum(b.actual_cost_usd for b in sold)
        self.st["free_cash_usd"] += proceeds
        self.st["cumulative_realized_net_usd"] += pnl
        if self.cur_cycle:
            self.cur_cycle.net_usd += pnl
        return pnl

    def _after_main_sell(self, exec_p: float, sub_sold: bool, main_sold: bool, reason: str):
        """sniper_exit_plugin 매도 정산 규칙: 래칫·앵커·최저가·졸업 상환."""
        qe, st = self.qe, self.st
        if self.B:
            st["cycle_ratchet_max_lots"] = max(self.lots(self.B), st["cycle_ratchet_max_lots"])
        else:
            st["cycle_ratchet_max_lots"] = 0
        if main_sold or not self.B:
            st["anchor_price"] = exec_p
            st["cycle_min_buy_price"] = st["cycle_min_buy_price"] if self.B else 0.0
        if self.S:
            st["sub_ratchet_max_lots"] = max(self.lots(self.S), st["sub_ratchet_max_lots"])
        else:
            st["sub_ratchet_max_lots"] = 0
        if sub_sold or not self.S:
            st["sub_anchor_price"] = exec_p
            st["sub_cycle_min_buy_price"] = st["sub_cycle_min_buy_price"] if self.S else 0.0
        if not self.B:
            self._end_main_cycle(reason)
        if not self.B and not self.S and st["injected_reserve_usd"] > 0:
            rp = qe.compute_reserve_repayment_on_zero(
                initial_seed_usd=st["initial_seed_usd"],
                cumulative_realized_net_usd=st["cumulative_realized_net_usd"],
                injected_reserve_usd=st["injected_reserve_usd"],
                used_reserve_portions_cnt=st["used_reserve_portions_cnt"],
                max_reserve_portions=int(self.cfg["max_reserve_portions"]))
            if rp.get("did_repay"):
                repaid = float(rp["repaid_usd"])
                st["free_cash_usd"] -= repaid
                self._flow(-repaid, exec_p)
                st["injected_reserve_usd"] = float(rp["rem_injected_reserve_usd"])
                st["used_reserve_portions_cnt"] = int(rp["rem_used_reserve_portions_cnt"])
                self._ev("예비시드 상환")

    def _end_main_cycle(self, reason: str):
        if self.cur_cycle:
            self.cur_cycle.end_idx = self.day_idx
            self.cur_cycle.end_reason = reason
            self.cycles.append(self.cur_cycle)
        self.cur_cycle = None
        self.cycle_start_idx = -1
        self.trail_active = False
        if self.cfg["pair_fund_reset_on_cycle_end"]:
            self.pair_fund = 0.0
        self.quota_count = 0

    def _relabel(self):
        qe = self.qe
        if self.B:
            if qe.has_active_l1_bucket(self.B):
                self.B = [self.B[0]] + qe.relabel_upper_grid_tiers(
                    self.B[1:], max_tiers=qe.MAX_GRID_TIERS_7, merge_mode=self.st["grid_merge_mode"])
            else:
                self.B = qe.relabel_upper_grid_tiers(self.B, max_tiers=qe.MAX_GRID_TIERS_7,
                                                     merge_mode=self.st["grid_merge_mode"])
        if self.S:
            if qe.has_active_l1_bucket(self.S):
                self.S = [self.S[0]] + qe.relabel_sub_upper_grid_tiers(
                    self.S[1:], max_tiers=qe.SUB_MAX_TIERS_3, merge_mode=qe.DEFAULT_SUB_MERGE_MODE)
            else:
                self.S = qe.relabel_sub_upper_grid_tiers(self.S, max_tiers=qe.SUB_MAX_TIERS_3,
                                                         merge_mode=qe.DEFAULT_SUB_MERGE_MODE)

    def sell_all(self, price: float, reason: str):
        exec_p = round(price * (1 - self.slip), 4)
        pnl = self._realize(list(self.B) + list(self.S), exec_p)
        self.realized_by[reason] = self.realized_by.get(reason, 0.0) + pnl
        had_main = bool(self.B)
        self.B, self.S = [], []
        self.main_traded = True
        self._ev("전량 매도:" + reason)
        self._after_main_sell(exec_p, True, had_main, reason)

    def sell_partial_expensive(self, price: float, n_shares: int, reason: str,
                               candidates: Optional[List[int]] = None) -> float:
        """비싼 층부터 n주 매도(층 일부 매도 허용). 실현손익 반환."""
        qe = self.qe
        exec_p = round(price * (1 - self.slip), 4)
        idxs = candidates if candidates is not None else list(range(len(self.B)))
        idxs = sorted(idxs, key=lambda i: self.B[i].book_price, reverse=True)
        left = n_shares
        pnl_sum = 0.0
        new_B = list(self.B)
        for i in idxs:
            if left <= 0:
                break
            b = new_B[i]
            k = min(left, b.qty)
            unit = b.actual_cost_usd / b.qty
            part = qe.StratumBucket(qty=k, book_price=b.book_price, book_invested_usd=unit * k,
                                    actual_cost_usd=unit * k, lot_count=1, lot_type=b.lot_type)
            pnl_sum += self._realize([part], exec_p)
            if k >= b.qty:
                new_B[i] = None
            else:
                rest = b.qty - k
                new_B[i] = qe.StratumBucket(qty=rest, book_price=b.book_price,
                                            book_invested_usd=unit * rest, actual_cost_usd=unit * rest,
                                            lot_count=b.lot_count, lot_type=b.lot_type)
            left -= k
        self.B = [b for b in new_B if b is not None]
        self._relabel()
        self.realized_by[reason] = self.realized_by.get(reason, 0.0) + pnl_sum
        self.main_traded = True
        self._after_main_sell(exec_p, False, True, reason)
        return pnl_sum

    # ---- 5-1 짝 매도 ----
    def high_tier_indices(self) -> List[int]:
        qe = self.qe
        if len(self.B) < 2:
            return []
        if qe.has_active_l1_bucket(self.B):
            ref, start = self.B[0].book_price, 1
        else:
            ref, start = min(b.book_price for b in self.B), 0
        thr = ref * (1 + float(self.cfg["pair_high_tier_pct"]) / 100.0)
        return [i for i in range(start, len(self.B)) if self.B[i].book_price >= thr - 1e-9
                and self.B[i].book_price > ref + 1e-9]

    def pair_offset(self, price: float):
        while self.pair_fund > 0 and self.B:
            hi = self.high_tier_indices()
            if not hi:
                return
            i = max(hi, key=lambda j: self.B[j].book_price)
            b = self.B[i]
            exec_p = price * (1 - self.slip)
            loss_ps = b.actual_cost_usd / b.qty - exec_p * (1 - self.fee1)
            if loss_ps <= 0:
                return
            n = min(b.qty, int(math.floor((self.pair_fund + 1e-9) / loss_ps)))
            if n <= 0:
                return
            pnl = self.sell_partial_expensive(price, n, "짝매도", candidates=[i])
            self.pair_fund = max(0.0, self.pair_fund + pnl)  # pnl 은 음수(손실)
            self._ev("짝매도 주수", n)

    # ---- 봉 안 처리 ----
    def trail_k_pct(self) -> float:
        c = self.cfg
        return min(float(c["trail_cap_pct"]),
                   float(c["trail_base_pct"]) + float(c["trail_per_day_pct"]) * self.cycle_age())

    def trail_stop(self) -> float:
        return max(self.trail_floor, self.trail_peak * (1 - self.trail_k_pct() / 100.0))

    def act_at(self, p: float, hm: int, intraday: bool) -> bool:
        """가격 p 에서 할 수 있는 행동을 1개 실행하면 True."""
        qe, st, cfg = self.qe, self.st, self.cfg
        buy_ok = (not intraday) or (407 <= hm <= 1600)
        sell_ok = (not intraday) or not (400 <= hm <= 406)
        overnight = intraday and sell_ok and not buy_ok
        regular = (not intraday) or (930 <= hm <= 1600)
        late_cut = intraday and 1530 <= hm <= 1600

        # 5-2 트레일 진행 중: 고점 갱신 · 정지선 이탈 시 전량 · 그 외 매수·개별 매도 정지
        if self.trail_active:
            self.trail_peak = max(self.trail_peak, p)
            judge = regular or not cfg["trail_regular_session_only"]
            if judge and sell_ok and p <= self.trail_stop() + 1e-9:
                self.sell_all(p, "트레일")
                return True
            return False

        # 매도 (개별·졸업) — evaluate_multi_grid_sell_targets
        if sell_ok and (self.B or self.S):
            _, r1, ru = self.thresholds()
            ev = qe.evaluate_multi_grid_sell_targets(buckets=self.B, live_price=p, rise_l1_pct=r1,
                                                     rise_upper_pct=ru, is_overnight_session=overnight,
                                                     sub_buckets=self.S)
            if ev.get("should_sell"):
                grad = bool(ev.get("hit_wma_grad"))
                if (grad and cfg["trail_enabled"]
                        and st["cycle_ratchet_max_lots"] >= int(cfg["trail_min_ratchet_lots"])
                        and regular):
                    info = qe.compute_upper_2_to_12_moving_avg(self.B, rise_upper_pct=ru)
                    self.trail_active = True
                    self.trail_floor = float(info.get("upper_wma_target_price") or p)
                    self.trail_peak = p
                    self.trail_start_idx = self.day_idx
                    self._ev("트레일 시작")
                    return True
                si = [i for i in (ev.get("sold_indices") or []) if 0 <= i < len(self.B)]
                ssi = [i for i in (ev.get("sub_sold_indices") or []) if 0 <= i < len(self.S)]
                if not si and not ssi:
                    return False
                exec_p = round(p * (1 - self.slip), 4)
                sold_m = [self.B[i] for i in si]
                sold_s = [self.S[i] for i in ssi]
                pm = self._realize(sold_m, exec_p) if sold_m else 0.0
                ps = self._realize(sold_s, exec_p) if sold_s else 0.0
                self.B = [b for i, b in enumerate(self.B) if i not in set(si)]
                self.S = [b for i, b in enumerate(self.S) if i not in set(ssi)]
                self._relabel()
                if sold_m:
                    self.main_traded = True
                if sold_s:
                    self.sub_traded = True
                key = "졸업" if (grad and not self.B) else "개별"
                self.realized_by[key] += pm
                self.realized_by["서브"] += ps
                self._ev("매도:" + key, 1)
                self._after_main_sell(exec_p, bool(sold_s), bool(sold_m), key)
                # 5-1: 졸업이 아닌 익절 이익을 상쇄 재원으로
                if cfg["pair_enabled"] and self.B:
                    gain = (pm if pm > 0 else 0.0) + (ps if (ps > 0 and cfg["pair_include_sub_profit"]) else 0.0)
                    if gain > 0:
                        self.pair_fund += gain * float(cfg["pair_offset_ratio"])
                        self.pair_offset(p)
                return True

        if not buy_ok:
            return False

        # 본: 0주 새 사이클
        if not self.B:
            if late_cut:
                return False
            return self.buy_main(p, "REENTRY_1FL", quota_ref=st["anchor_price"] or p)
        # 본: 1층 공석 재장전
        if not qe.has_active_l1_bucket(self.B):
            info = qe.compute_upper_2_to_12_moving_avg(self.B)
            ceil_p = float(info.get("min_indiv_upper_price") or 0.0)
            sig = qe.evaluate_l2_only_hybrid_reentry_signal(
                live_price=p, anchor_price=st["anchor_price"], l2_book_price=ceil_p,
                min_upper_tier_price=ceil_p, is_late_new_cycle_cutoff=late_cut, is_late_cutoff=late_cut)
            if sig.get("should_buy"):
                return self.buy_main(p, "REENTRY_1FL", quota_ref=float(sig.get("quota_ref_price") or p))
        else:
            drop, _, _ = self.thresholds()
            sig = qe.evaluate_step_up_2x_dip_signal(
                live_price=p, buckets=self.B, anchor_price=st["anchor_price"],
                cycle_min_buy_price=st["cycle_min_buy_price"], drop_buy_pct=drop,
                free_cash_usd=st["free_cash_usd"],
                realized_equity_usd=st["initial_seed_usd"] + st["cumulative_realized_net_usd"])
            if sig.get("should_buy"):
                stepped = float(sig.get("stepped_min_price") or 0.0) if sig.get("is_step_up_unlock") else 0.0
                if self.buy_main(p, "DIP_1FL", quota_ref=float(sig.get("quota_ref_price") or p),
                                 stepped_min=stepped):
                    return True
        # 서브
        if cfg["sub_grid_enabled"] and self.B:
            triggered = st["main_consec_frozen_days"] >= qe.SUB_FROZEN_DAYS_TRIGGER or len(self.S) > 0
            if triggered:
                if not self.S:
                    if not late_cut:
                        return self.buy_sub(p, "SUB_REENTRY_1FL")
                elif not qe.has_active_l1_bucket(self.S):
                    info = qe.compute_upper_2_to_12_moving_avg(self.S)
                    ceil_p = float(info.get("min_indiv_upper_price") or 0.0)
                    sig = qe.evaluate_l2_only_hybrid_reentry_signal(
                        live_price=p, anchor_price=st["sub_anchor_price"], l2_book_price=ceil_p,
                        min_upper_tier_price=ceil_p, is_late_new_cycle_cutoff=late_cut, is_late_cutoff=late_cut)
                    if sig.get("should_buy") and self.lots(self.S) < qe.SUB_MAX_TOTAL_LOTS_4:
                        return self.buy_sub(p, "SUB_REENTRY_1FL")
                else:
                    sdrop, _, _ = self.thresholds(sub=True)
                    sig = qe.evaluate_sub_grid_dip_signal(
                        live_price=p, sub_buckets=self.S, sub_anchor_price=st["sub_anchor_price"],
                        sub_cycle_min_buy_price=st["sub_cycle_min_buy_price"], sub_drop_buy_pct=sdrop,
                        sub_consec_frozen_days=st["sub_consec_frozen_days"],
                        sub_max_total_lots=qe.SUB_MAX_TOTAL_LOTS_4,
                        unlock_frozen_days=qe.SUB_UNLOCK_FROZEN_DAYS_10,
                        unlock_drop_pct=qe.SUB_UNLOCK_DROP_FROM_L1_PCT)
                    if sig.get("should_buy"):
                        return self.buy_sub(p, "SUB_DIP_1FL")
        return False

    def settle_at(self, p: float, hm: int, intraday: bool):
        for _ in range(60):
            if not self.act_at(p, hm, intraday):
                return

    # ---- 주식 분할 ----
    def apply_split(self, r: float, ref_price: float):
        qe, st = self.qe, self.st
        if r <= 0 or abs(r - 1.0) < 1e-9:
            return
        def conv(bl):
            out = []
            for b in bl:
                nq = int(math.floor(b.qty * r + 1e-9))
                if nq <= 0:
                    st["free_cash_usd"] += b.qty * r * ref_price  # 1주 미만 현금 정산
                    continue
                frac = b.qty * r - nq
                if frac > 1e-9:
                    st["free_cash_usd"] += frac * ref_price
                cost = b.actual_cost_usd * (nq / (b.qty * r))
                out.append(qe.StratumBucket(qty=nq, book_price=cost / nq, book_invested_usd=cost,
                                            actual_cost_usd=cost, lot_count=b.lot_count, lot_type=b.lot_type))
            return out
        self.B, self.S = conv(self.B), conv(self.S)
        for k in ("anchor_price", "cycle_min_buy_price", "sub_anchor_price", "sub_cycle_min_buy_price"):
            st[k] = st[k] / r
        self.trail_floor /= r
        self.trail_peak /= r
        self._ev("주식 분할")

    # ---- 다음 발동 가격 찾기 (연속 이동 근사) ----
    @staticmethod
    def _ceil2(x: float) -> float:
        return math.ceil((x - 1e-9) * 100.0) / 100.0

    @staticmethod
    def _floor2(x: float) -> float:
        return math.floor((x + 1e-9) * 100.0) / 100.0

    def up_levels(self) -> List[float]:
        qe = self.qe
        if self.trail_active:
            return []
        lv: List[float] = []
        _, r1, ru = self.thresholds()
        for grp in (self.B, self.S):
            if not grp:
                continue
            act = qe.has_active_l1_bucket(grp)
            for i, b in enumerate(grp):
                r = r1 if (i == 0 and act) else ru
                lv.append(self._ceil2(b.book_price * (1 + r / 100.0)))
            info = qe.compute_upper_2_to_12_moving_avg(grp, rise_upper_pct=ru)
            t = float(info.get("upper_wma_target_price") or 0.0)
            if t > 0:
                lv.append(t)
        # 1층 공석 돌파 재장전
        for grp, anc in ((self.B, self.st["anchor_price"]), (self.S, self.st["sub_anchor_price"])):
            if grp and not qe.has_active_l1_bucket(grp) and anc > 0:
                lv.append(self._ceil2(anc * (1 + qe.REENTRY_BREAKOUT_RISE_PCT / 100.0)))
        return lv

    def down_levels(self) -> List[float]:
        qe, st = self.qe, self.st
        if self.trail_active:
            return [self.trail_stop()]
        lv: List[float] = []
        if self.B and qe.has_active_l1_bucket(self.B):
            drop, _, _ = self.thresholds()
            refs = [x for x in (self.B[0].book_price, st["anchor_price"], st["cycle_min_buy_price"]) if x > 0]
            if refs:
                lv.append(self._floor2(min(refs) * (1 + drop / 100.0)))
            l1 = self.B[0].book_price
            lv.append(self._floor2(l1 * (1 - qe.STEP_UP_2X_DROP_PCT / 100.0)))
        if self.B and not qe.has_active_l1_bucket(self.B) and st["anchor_price"] > 0:
            lv.append(self._floor2(st["anchor_price"] * (1 + qe.REENTRY_PULLBACK_DROP_PCT / 100.0)))
        if self.S:
            sdrop, _, _ = self.thresholds(sub=True)
            if qe.has_active_l1_bucket(self.S):
                refs = [x for x in (self.S[0].book_price, st["sub_anchor_price"], st["sub_cycle_min_buy_price"])
                        if x > 0]
                if refs:
                    lv.append(self._floor2(min(refs) * (1 + sdrop / 100.0)))
                lv.append(self._floor2(self.S[0].book_price * (1 - qe.SUB_UNLOCK_DROP_FROM_L1_PCT / 100.0)))
            elif st["sub_anchor_price"] > 0:
                lv.append(self._floor2(st["sub_anchor_price"] * (1 + qe.REENTRY_PULLBACK_DROP_PCT / 100.0)))
        return lv

    def walk(self, p: float, q: float, hm: int, intraday: bool) -> float:
        guard = 0
        while guard < 400:
            guard += 1
            if q > p:
                cand = [x for x in self.up_levels() if p + 1e-9 < x <= q + 1e-9]
                if self.trail_active:
                    self.trail_peak = max(self.trail_peak, q)
                if not cand:
                    return q
                p = min(cand)
            elif q < p:
                cand = [x for x in self.down_levels() if q - 1e-9 <= x < p - 1e-9]
                if not cand:
                    return q
                p = max(cand)
            else:
                return q
            self.settle_at(p, hm, intraday)
        return q

    def run_bar(self, b: Bar, prev_close: Optional[float]):
        # 시가 갭: 지나간 발동은 시가에 체결
        self.settle_at(b.o, b.hm, b.intraday)
        path = [b.o, b.l, b.h, b.c] if b.c >= b.o else [b.o, b.h, b.l, b.c]
        p = b.o
        for q in path[1:]:
            p = self.walk(p, q, b.hm, b.intraday)

    # ---- 일 마감 ----
    def close_day(self, d: date, close_p: float, last_hm: int, intraday: bool):
        st, cfg = self.st, self.cfg
        # 5-2 최대 대기
        if self.trail_active and (self.day_idx - self.trail_start_idx) >= int(cfg["trail_max_days"]):
            self.sell_all(close_p, "트레일")
            self._ev("트레일 기한 매도")
        # 5-3 쿼터 정리 (정규장 마감 무렵)
        if cfg["quota_enabled"] and self.B and not self.trail_active \
                and self.quota_count < int(cfg["quota_max_times"]) \
                and (self.day_idx - self.quota_last_idx) >= int(cfg["quota_gap_days"]):
            cost_m = self.cost(self.B)
            mv = self.qty(self.B) * close_p * (1 - self.fee1)
            loss_pct = (mv - cost_m) / cost_m * 100.0 if cost_m > 0 else 0.0
            hit = (self.cycle_age() >= int(cfg["quota_trigger_days"])
                   or loss_pct <= -float(cfg["quota_trigger_loss_pct"])
                   or st["used_reserve_portions_cnt"] >= int(cfg["quota_trigger_reserve_portions"]))
            if hit:
                tot = self.qty(self.B)
                n = min(tot - 1, int(round(tot * float(cfg["quota_sell_ratio"]))))
                if n >= 1:
                    self.sell_partial_expensive(close_p, n, "쿼터")
                    self.quota_count += 1
                    self.quota_last_idx = self.day_idx
                    self._ev("쿼터 정리")
        # 무매매일 (defense_plugin.execute_1600_daily_closing_settlement_plugin 규칙)
        st["main_consec_frozen_days"] = 0 if self.main_traded else st["main_consec_frozen_days"] + 1
        st["sub_consec_frozen_days"] = 0 if self.sub_traded else st["sub_consec_frozen_days"] + 1
        self.main_traded = self.sub_traded = False
        # 지표
        inv = self.cost(self.B) + self.cost(self.S)
        mv = (self.qty(self.B) + self.qty(self.S)) * close_p
        tot = st["free_cash_usd"] + mv
        nav_idx = tot / self.units * st["initial_seed_usd"]  # 시드 $10,000 에서 출발한 기준가 지수
        self.equity.append((d, nav_idx))
        self.last_total = tot
        self.invested_usd_days += inv
        if inv > 0 and mv < inv:
            self.locked_usd_days += inv
            self.max_unrealized_loss = max(self.max_unrealized_loss, inv - mv)
            self.max_unrealized_loss_pct = max(self.max_unrealized_loss_pct, (inv - mv) / inv * 100.0)
        self.day_idx += 1


# ---------------------------------------------------------------------------
# 실행·지표
# ---------------------------------------------------------------------------
def mdd(series: List[float]) -> float:
    peak, worst = -1e18, 0.0
    for v in series:
        peak = max(peak, v)
        if peak > 0:
            worst = min(worst, (v - peak) / peak)
    return worst * 100.0


def run_scenario(qe, days: List[List[Bar]], cfg: Dict[str, Any], slip: float) -> Dict[str, Any]:
    sim = Sim(qe, cfg, slip)
    prev = None
    for bars in days:
        if abs(bars[0].split - 1.0) > 1e-9:
            sim.apply_split(bars[0].split, bars[0].o)
        for b in bars:
            sim.run_bar(b, prev)
            prev = b.c
        last = bars[-1]
        sim.close_day(last.day, last.c, last.hm, last.intraday)
    eqs = [e for _, e in sim.equity]
    done = [c for c in sim.cycles]
    lens = [c.end_idx - c.start_idx for c in done]
    open_len = sim.cycle_age() if sim.B else 0
    nets = [c.net_usd for c in done]
    years = max(1e-9, len(days) / 252.0)
    seed = cfg["initial_seed_usd"]
    final = eqs[-1] if eqs else seed
    return {
        "최대손실(MDD%)": round(mdd(eqs), 1),
        "최대 평가손실$": round(sim.max_unrealized_loss, 0),
        "최대 평가손실%": round(sim.max_unrealized_loss_pct, 1),
        "최장 물림일": max(lens + [open_len]) if (lens or open_len) else 0,
        "끝에 진행중 사이클일": open_len,
        "완료 사이클 수": len(done),
        "사이클당 수익$(평균)": round(sum(nets) / len(nets), 1) if nets else 0.0,
        "사이클당 수익$(중앙)": round(sorted(nets)[len(nets) // 2], 1) if nets else 0.0,
        "잠긴 USD·일(만)": round(sim.locked_usd_days / 1e4, 1),
        "투입 USD·일(만)": round(sim.invested_usd_days / 1e4, 1),
        "예비시드 최대 회분": sim.max_used_reserve,
        "예비시드 최대$": round(sim.max_injected, 0),
        "최종 자산$": round(getattr(sim, "last_total", seed), 0),
        "미상환 예비$": round(sim.st["injected_reserve_usd"], 0),
        "연복리%": round(((final / seed) ** (1 / years) - 1) * 100.0, 1) if final > 0 else -100.0,
        "실현손익 내역$": {k: round(v, 0) for k, v in sim.realized_by.items()},
        "이벤트": dict(sorted(sim.event_cnt.items())),
        "매수 막힘(시도 수)": sim.blocked_buy_cnt,
        "_equity": sim.equity,
    }


def run_buy_and_hold(days: List[List[Bar]], cfg: Dict[str, Any]) -> Dict[str, Any]:
    seed = cfg["initial_seed_usd"]
    fee1 = cfg["round_trip_fee_pct"] / 200.0
    p0 = days[0][0].o
    sh = float(int(seed // (p0 * (1 + fee1))))
    cash = seed - sh * p0 * (1 + fee1)
    cost = sh * p0
    eq = []
    for i, bars in enumerate(days):
        if i > 0 and abs(bars[0].split - 1.0) > 1e-9:
            sh *= bars[0].split
        eq.append((bars[-1].day, cash + sh * bars[-1].c))
    vals = [v for _, v in eq]
    years = max(1e-9, len(days) / 252.0)
    final = vals[-1]
    # 원가 아래에 있던 날 = 물림
    under, longest, run = 0.0, 0, 0
    for _, v in eq:
        mv = v - cash
        if mv < cost:
            under += cost
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return {
        "최대손실(MDD%)": round(mdd(vals), 1), "최대 평가손실$": round(max(0.0, cost - min(v - cash for v in vals)), 0),
        "최대 평가손실%": round(max(0.0, (cost - min(v - cash for v in vals)) / cost * 100.0), 1),
        "최장 물림일": longest, "끝에 진행중 사이클일": 0, "완료 사이클 수": 0,
        "사이클당 수익$(평균)": None, "사이클당 수익$(중앙)": None,
        "잠긴 USD·일(만)": round(under / 1e4, 1), "투입 USD·일(만)": round(cost * len(days) / 1e4, 1),
        "예비시드 최대 회분": 0, "예비시드 최대$": 0, "최종 자산$": round(final, 0), "미상환 예비$": 0,
        "연복리%": round(((final / seed) ** (1 / years) - 1) * 100.0, 1) if final > 0 else -100.0,
        "_equity": eq,
    }


def window_stats(eq: List[Tuple[date, float]], d0: date, d1: date) -> Optional[Tuple[float, float]]:
    seg = [v for d, v in eq if d0 <= d <= d1]
    if len(seg) < 5:
        return None
    return round((seg[-1] / seg[0] - 1) * 100.0, 1), round(mdd(seg), 1)


TABLE_COLS = ["최대손실(MDD%)", "최대 평가손실%", "최장 물림일", "완료 사이클 수", "사이클당 수익$(평균)",
              "잠긴 USD·일(만)", "예비시드 최대 회분", "예비시드 최대$", "최종 자산$", "미상환 예비$", "연복리%"]


def fmt_table(rows: List[Tuple[str, Dict[str, Any]]]) -> str:
    head = "| 시나리오 | " + " | ".join(TABLE_COLS) + " |"
    sep = "|" + "---|" * (len(TABLE_COLS) + 1)
    lines = [head, sep]
    for name, r in rows:
        vals = ["—" if r.get(c) is None else str(r.get(c)) for c in TABLE_COLS]
        lines.append(f"| {name} | " + " | ".join(vals) + " |")
    return "\n".join(lines)


def coverage_report(days: List[List[Bar]], cfg: Dict[str, Any]) -> List[str]:
    have = {bars[0].day for bars in days}
    intra = {bars[0].day for bars in days if bars[0].intraday}
    out = []
    for name, a, b in cfg["required_windows"]:
        d0 = datetime.strptime(a, "%Y-%m-%d").date()
        d1 = datetime.strptime(b, "%Y-%m-%d").date()
        n = sum(1 for d in have if d0 <= d <= d1)
        ni = sum(1 for d in intra if d0 <= d <= d1)
        out.append(f"- {name} ({a}~{b}): 거래일 {n}일, 그중 분봉 {ni}일"
                   + ("" if n else "  ← [막힘] 데이터 없음")
                   + ("" if ni else "  ← 분봉 없음: 세션 규칙(오버나이트 잠금 등) 재현 불가, 일봉 근사"))
    return out


def main():
    ap = argparse.ArgumentParser(description="2번 스나이퍼 물림 대처 백테스트 (연구용, 주문 없음)")
    ap.add_argument("--bot-dir", required=True, help="toss_sniper 폴더 (quant_engine.py 읽기만)")
    ap.add_argument("--daily", help="SOXL 일봉 CSV (date,open,high,low,close)")
    ap.add_argument("--intraday", help="SOXL 5분봉 CSV (datetime[미국동부],open,high,low,close) — 선택")
    ap.add_argument("--config", help="설정 덮어쓰기 JSON")
    ap.add_argument("--start", help="시작일 YYYY-MM-DD")
    ap.add_argument("--end", help="종료일 YYYY-MM-DD")
    ap.add_argument("--scenarios", help="쉼표로 시나리오 이름 선택 (기본: 전부)")
    ap.add_argument("--out", default="bt_out", help="결과 폴더")
    ap.add_argument("--data-note", default="", help="데이터 출처·받은 날짜 메모 (결과 파일에 기록)")
    ap.add_argument("--selftest", action="store_true", help="합성 가격으로 코드 경로만 점검 (결과로 쓰지 않음)")
    a = ap.parse_args()

    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if a.config:
        with open(a.config, encoding="utf-8") as fh:
            user = json.load(fh)
        unknown = [k for k in user if k not in cfg]
        if unknown:
            print(f"[경고] 모르는 설정 키(무시): {unknown}")
        cfg.update({k: v for k, v in user.items() if k in cfg})

    qe = load_engine(a.bot_dir)

    if a.selftest:
        days = synthetic_days()
        src = "합성 가격(--selftest, 코드 점검 전용 — 결과로 쓰지 말 것)"
    else:
        if not a.daily or not os.path.isfile(a.daily):
            print("[막힘] 일봉 CSV 가 없습니다. --daily 로 SOXL 일봉(date,open,high,low,close)을 주세요.")
            print("       데이터를 지어내지 않으므로 실행을 멈춥니다.")
            sys.exit(2)
        daily = read_daily_csv(a.daily)
        intra = read_intraday_csv(a.intraday) if (a.intraday and os.path.isfile(a.intraday)) else []
        if a.intraday and not intra:
            print(f"[경고] 분봉 CSV 를 읽지 못함: {a.intraday} → 전 기간 일봉으로 실행")
        days = merge_bars(daily, intra)
        src = f"일봉 {os.path.basename(a.daily)}" + (f" + 분봉 {os.path.basename(a.intraday)}" if intra else "")
    if a.start:
        d0 = datetime.strptime(a.start, "%Y-%m-%d").date()
        days = [x for x in days if x[0].day >= d0]
    if a.end:
        d1 = datetime.strptime(a.end, "%Y-%m-%d").date()
        days = [x for x in days if x[0].day <= d1]
    if len(days) < 30:
        print("[막힘] 데이터가 30거래일보다 적습니다.")
        sys.exit(2)

    os.makedirs(a.out, exist_ok=True)
    cov = coverage_report(days, cfg) if not a.selftest else ["- (selftest)"]
    chosen = SCENARIOS
    if a.scenarios:
        want = {s.strip() for s in a.scenarios.split(",")}
        chosen = [s for s in SCENARIOS if s[0] in want]

    md: List[str] = []
    md.append(f"# 스나이퍼 물림 대처 백테스트 결과 (스크립트 v{SCRIPT_VERSION})")
    md.append(f"- 실행: {datetime.now().strftime('%Y-%m-%d %H:%M')} · 데이터: {src} · "
              f"기간 {days[0][0].day} ~ {days[-1][0].day} ({len(days)}거래일)")
    if a.data_note:
        md.append(f"- 데이터 출처 메모: {a.data_note}")
    md.append("- 필수 구간 확인:")
    md.extend(cov)
    md.append("- 설정: " + json.dumps({k: v for k, v in cfg.items() if k != "required_windows"}, ensure_ascii=False))

    all_rows: Dict[float, List[Tuple[str, Dict[str, Any]]]] = {}
    bh = run_buy_and_hold(days, cfg)
    for slip in cfg["slippage_pct_list"]:
        rows = []
        for name, flags in chosen:
            c2 = dict(cfg)
            c2.update({"pair_enabled": False, "trail_enabled": False, "quota_enabled": False})
            c2.update(flags)
            r = run_scenario(qe, days, c2, float(slip))
            rows.append((name, r))
            print(f"  · 미끄러짐 {slip}% · {name} 완료", flush=True)
        rows.append((BUY_AND_HOLD, bh))
        all_rows[slip] = rows
        md.append(f"\n## 시나리오 비교 — 미끄러짐 {slip}%\n")
        md.append(fmt_table(rows))
        md.append("\n### 실현손익 내역·이벤트 수\n")
        for name, r in rows:
            if "실현손익 내역$" in r:
                md.append(f"- {name}: 실현 {r['실현손익 내역$']} · 이벤트 {r['이벤트']} · 매수 막힘(시도) {r['매수 막힘(시도 수)']}")
        md.append("\n### 필수 구간별 (구간 수익% / 구간 MDD%)\n")
        for wname, w0, w1 in cfg["required_windows"]:
            d0 = datetime.strptime(w0, "%Y-%m-%d").date()
            d1 = datetime.strptime(w1, "%Y-%m-%d").date()
            parts = []
            for name, r in rows:
                ws = window_stats(r["_equity"], d0, d1)
                parts.append(f"{name} {ws[0]}%/{ws[1]}%" if ws else f"{name} 데이터없음")
            md.append(f"- {wname}: " + " · ".join(parts))

    md.append("\n## 지표 정의\n"
              "- 최대손실(MDD%): 기준가(예비시드 입출금을 단위로 환산한 자산 지수)의 고점 대비 최대 하락\n"
              "- 최종 자산$: 2번 장부 현금+평가액(예비시드 포함) · 미상환 예비$: 끝날 때 갚지 못한 수혈금\n"
              "- 연복리%: 기준가 기준\n"
              "- 최대 평가손실%: 본+서브 보유 원가 대비 평가손실의 최댓값\n"
              "- 최장 물림일: 본 그리드 사이클(0주→0주) 최장 거래일 수(끝에 진행 중인 사이클 포함)\n"
              "- 사이클당 수익$: 완료된 본 사이클 동안 실현된 순손익(서브·짝매도·쿼터 포함) 평균\n"
              "- 잠긴 USD·일: 평가손실 상태인 날의 보유 원가 합 (단위 만 USD·일)\n"
              "- 예비시드 최대: 동시에 쓴 예비 회분·금액 최댓값 = 3번 영향 대리 지표 (계좌 겹침은 해결 안 함)")
    path = os.path.join(a.out, "backtest_result.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    # 짧은 화면 출력
    for slip, rows in all_rows.items():
        print(f"\n[미끄러짐 {slip}%]")
        print(fmt_table(rows))
    print("\n필수 구간:")
    print("\n".join(cov))
    print(f"\n전체 결과: {os.path.abspath(path)}")
    if a.selftest:
        print("\n※ --selftest 결과는 합성 가격이라 의미 없음. 코드가 끝까지 도는지만 확인용.")


if __name__ == "__main__":
    main()
