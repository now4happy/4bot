#!/usr/bin/env python3
# ==========================================================
# FILE: bot_office/fanding_vault.py   (FANDING_VAULT v0.1.1-shadow)
# P매매(SOXL) 수익금 분리(30% → 현금 인출 + SGOV) — 그림자 모드 전용
#
# 이 모듈은 주문·환전·계좌 조회를 하지 않는다 (broker/네트워크 import 없음, 표준 라이브러리만).
# 입력 = 매 표일 가격표 한 줄(표 숫자), 출력 = 상태 파일 + 이벤트 로그(JSONL)뿐.
# 실거래 전환은 별도 결정: 이 파일에는 실거래 경로가 없고 go_live() 는 항상 거부한다.
#
# 단위: '표 단위'(배수 1, 시즌 원금 base_units=10,000). 실제 금액·계좌번호는 다루지 않는다.
# 근거 설계: 노션 작업 페이지 [AI] 구역 판 3 가정 + 결정됨 (2026-11-16 사용자).
# 근거 코드: bot_office/fanding_trade.py raw_lines·cap_sells·order_lines (now4happy/4bot main 231fef6)
# ==========================================================
import json
import math
import os
import tempfile
from dataclasses import dataclass, asdict, field
from pathlib import Path

VERSION = "v0.1.1-shadow"
SHADOW_ONLY = True
EPS = 1e-9


def go_live(*_a, **_k):
    """실거래 전환 경로는 이 버전에 없다 (별도 결정·별도 구현·Muse 검토·텔레그램 9번 Update 승인 뒤)."""
    raise RuntimeError("fanding_vault: 그림자 모드 전용 — 실거래 전환 미구현")


# ---------------------------------------------------------------- 설정
@dataclass
class VaultConfig:
    threshold_pct: float = 30.0      # 분리 기준 (결정됨: 30%)
    fee_rate: float = 0.0007         # 미국주식 0.07% (Super365, 사용자 확정 2026-11-16)
    sec_fee_rate: float = 0.0000206  # SEC Fee 0.00206% — 매도분만 별도
    sgov_buy_fee_rate: float = 0.0007  # SGOV 매수에도 fee_rate 와 같게 적용 — 미확인(가정), 0 으로 바꿀 수 있음
    base_units: float = 10000.0      # 표 시즌 원금
    target_units: float = 10000.0    # T: 목표 운용금액 (표 단위)
    reset_mode: str = "compound"     # 시즌 리셋 배수: compound = (T+남은 실현순수익)÷base / fixed = 1
    reset_mult: float = None         # 값이 있으면 사용자가 정한 리셋 배수가 우선 (둘 다 이 값으로)
    g_denominator: str = "base"      # G 분모: base(시즌 원금 10,000 — 표 '총수익률'과 같은 기준) | target(T)
    carry_across_seasons: bool = True  # 시즌이 바뀌어도 아직 인출 안 한 순수익을 G 에 계속 합산
    # ↑ 두 기본값은 판 3 방 기록의 날짜(복리 2차 02-09 · 고정 3차 07-07)와 맞추려고 고른 것 — 근거: VERIFY.md 4절 (backtest_v3.py 원본 대조는 미실행)
    max_buy_usd: float = 8000.0      # fanding.json max_buy_usd — 당일 매수 총액(배수 적용 후)이 넘으면 봇은 자동주문을 막고 사람이 결정
    real_mult: float = 1.0           # 표 단위 → 실제 금액 배수(사용자 배수). 한도 비교에만 사용, 기본 1 — 미확인(Q13)
    s_field: str = "total_realized_usd"  # 실거래 훅에서 표 '시즌실현수익'으로 읽을 가격표 칸 — 미확인(매핑 가정)

    def validate(self):
        if self.reset_mode not in ("compound", "fixed"):
            raise ValueError("reset_mode: compound | fixed")
        if self.g_denominator not in ("target", "base"):
            raise ValueError("g_denominator: target | base")
        if self.threshold_pct <= 0 or self.base_units <= 0 or self.target_units <= 0:
            raise ValueError("threshold/base/target 은 0 보다 커야 함")
        if self.reset_mult is not None and self.reset_mult <= 0:
            raise ValueError("reset_mult 는 0 보다 커야 함")
        return self


# ---------------------------------------------------------------- 순수 함수 (fanding_trade.py 와 같은 동작)
def raw_lines(buys, sells, mult):
    """fanding_trade.raw_lines 와 같음: 표 수량 × 배수. buys/sells = [(가격, 표 수량)]. 배수는 소수 허용(코드의 배수는 정수 — 미확인)."""
    return ([("buy", float(p), q * mult) for p, q in buys] +
            [("sell", float(p), q * mult) for p, q in sells])


def cap_sells(lines, sellable):
    """fanding_trade.cap_sells 와 같은 알고리즘(float 허용): 매도 합계가 매도가능보다 많으면
    가장 높은 매도가 줄부터 줄임. 줄 순서·개수 그대로. sellable None 이면 그대로."""
    if sellable is None:
        return list(lines), 0
    short = sum(q for s, _, q in lines if s == "sell") - sellable
    if short <= EPS:
        return list(lines), 0
    out, cut = list(lines), 0
    for i in sorted((i for i, (s, _, _) in enumerate(out) if s == "sell"), key=lambda i: -out[i][1]):
        if short <= EPS:
            break
        s, pr, q = out[i]
        d = min(q, short)
        out[i] = (s, pr, q - d)
        short -= d
        cut += d
    return out, cut


def fee_amount(side, notional, cfg):
    f = notional * cfg.fee_rate
    if side == "sell":
        f += notional * cfg.sec_fee_rate
    return f


def classify_transition(last, row):
    """표 두 줄(전날→오늘)의 변화로 체결 종류를 판정. 총거래대금은 표만으로는 구할 수 없는 날이 있다(혼합 체결일 — 미확인).
    idle / buy / sell / mixed"""
    dq = row["hold"] - last["hold"]
    dc = row["cash"] - last["cash"]
    dS = row["S"] - last["S"]
    if dq == 0 and abs(dc) < 1e-6 and abs(dS) < 1e-6:
        return "idle"
    if dq > 0 and abs(dS) < 1e-6:
        return "buy"
    la, ra = last.get("avg") or 0.0, row.get("avg") or 0.0
    if dq < 0 and (row["hold"] == 0 or abs(la - ra) < 6e-4):
        return "sell"
    return "mixed"


# ---------------------------------------------------------------- 상태
def _blank_state(cfg):
    return {
        "v": 1, "version": VERSION, "mode": "shadow", "config": asdict(cfg),
        "last": None, "season": None, "scale": 1.0, "T": cfg.target_units,
        "core_qty": 0.0, "core_cost": 0.0, "exc_qty": 0.0, "exc_cost": 0.0,
        "cash": 0.0, "withdrawn_total": 0.0, "sgov_usd": 0.0,
        "season_stats": {"R_gross": 0.0, "fees": 0.0, "excess_pnl": 0.0, "W": 0.0},
        "pending_sep": None, "pending_excess": None,
        "counters": {"separations": 0, "mixed_days": 0, "capped_days": 0, "cash_short": 0, "excess_sells": 0, "short_buys": 0, "buy_over_limit": 0},
        "seq": 0,
    }


def norm_row(d):
    """표 한 줄 정규화. 키: date, close, hold, avg, cash, S, season(없으면 None), buys, sells. 칸이 비면 None 반환(건너뜀)."""
    try:
        row = {
            "date": str(d["date"]), "close": float(d["close"]), "hold": float(d["hold"]),
            "avg": None if d.get("avg") in (None, "") else float(d["avg"]),
            "cash": float(d["cash"]), "S": float(d["S"]),
            "season": d.get("season"),
            "buys": [(float(p), float(q)) for p, q in d.get("buys", [])],
            "sells": [(float(p), float(q)) for p, q in d.get("sells", [])],
        }
    except (KeyError, TypeError, ValueError):
        return None
    if not row["date"] or not math.isfinite(row["close"]) or row["close"] <= 0:
        return None
    return row


class VaultShadow:
    def __init__(self, cfg=None, state=None, log=None):
        self.cfg = (cfg or VaultConfig()).validate()
        self.st = state or _blank_state(self.cfg)
        self.events = []          # 이번 step 에서 만든 이벤트
        self._log = log           # 호출 가능: log(event_dict) — 파일 기록용

    # ---- 이벤트
    def _ev(self, ev_kind, date, **f):
        self.st["seq"] += 1
        e = {"seq": self.st["seq"], "kind": ev_kind, "date": date, "shadow": True, **f}
        self.events.append(e)
        if self._log:
            self._log(e)
        return e

    # ---- 계산 보조
    def retained(self):
        s = self.st["season_stats"]
        return s["R_gross"] - s["fees"] + s["excess_pnl"] - s["W"]

    def r_net(self):
        s = self.st["season_stats"]
        return s["R_gross"] - s["fees"] + s["excess_pnl"]

    def g(self):
        den = self.st["T"] if self.cfg.g_denominator == "target" else self.cfg.base_units
        return self.retained() / den

    def own_qty(self):
        return self.st["core_qty"] + self.st["exc_qty"]

    # ---- 한 표일 처리 (매일 표 마감 뒤 1번)
    def step(self, raw_row):
        self.events = []
        row = norm_row(raw_row)
        st, cfg = self.st, self.cfg
        if row is None:
            self._ev("skipped_row", str((raw_row or {}).get("date")), reason="칸 부족/형식 오류 (판독 실패 포함)")
            return self.events
        last = st["last"]
        if last is None:
            return self._init(row)
        new_season = row["season"] is not None and row["season"] != st["season"]
        if not new_season and row["season"] is None:
            # 시즌 칸이 없는 입력(실거래 훅): 표가 새로 시작된 모양(실현 0·보유 0·잔금=원금)이면 새 시즌 — 미확인(추정 규칙)
            new_season = (abs(row["S"]) < EPS and abs(last["S"]) > EPS and row["hold"] == 0
                          and abs(row["cash"] - cfg.base_units) < 1e-6)
            if new_season:
                row["season"] = (st["season"] or 1) + 1
        if row["date"] < last["date"] or (row["date"] == last["date"] and not new_season):
            self._ev("duplicate_or_old", row["date"], last_date=last["date"])
            return self.events
        if new_season:
            return self._season_reset(row)
        row["season"] = st["season"] if row["season"] is None else row["season"]
        self._transition(last, row)
        self._excess_exec(row)
        self._separation_exec(row)
        self._after_close(row)
        return self.events

    # ---- 첫 줄: 표와 같은 상태로 시작(배수 1) — 가정
    def _init(self, row):
        st = self.st
        st["last"], st["season"] = row, row["season"] if row["season"] is not None else 1
        st["core_qty"] = row["hold"]
        st["core_cost"] = row["hold"] * (row["avg"] or 0.0)
        st["cash"] = row["cash"]
        # 첫 줄 이전에 이미 실현된 손익은 현금에 들어 있으므로 시즌 실현 합계의 시작값으로 포함 (안 하면 현금과 T 가 어긋남)
        st["season_stats"]["R_gross"] = row["S"]
        self._ev("init", row["date"], assumption="첫 줄은 표(배수 1)와 같은 상태로 시작 (이전 실현손익 포함)",
                 hold=row["hold"], cash=row["cash"], S0=row["S"])
        self._plan(row)
        return self.events

    # ---- 전날→오늘 체결 반영 (내 배수로 환산: 표 변화량 × 배수)
    def _transition(self, last, row):
        st, cfg = self.st, self.cfg
        m = st["scale"]
        kind = classify_transition(last, row)
        dq = row["hold"] - last["hold"]
        dc = row["cash"] - last["cash"]
        dS = row["S"] - last["S"]
        dcost = row["hold"] * (row["avg"] or 0.0) - last["hold"] * (last["avg"] or 0.0)
        f = 1.0
        if dq * m < 0 and st["core_qty"] + dq * m < -EPS:
            # 내 코어 보유가 표×배수보다 모자라 매도가 불가능한 만큼 → 가능한 만큼만 (cap_sells 취지)
            f = st["core_qty"] / (-dq * m) if dq * m != 0 else 1.0
            st["counters"]["capped_days"] += 1
            self._ev("core_sell_capped", row["date"], factor=round(f, 6), note="비례 축소(근사)")
        dq_o, dc_o, dS_o, dcost_o = dq * m * f, dc * m * f, dS * m * f, dcost * m * f
        if dq_o > EPS and dc_o < 0:
            # 매수 현금 한도 (backtest_v3 방식): 살 수 있는 수량 = max(현금,0) ÷ (체결평균가 × (1+수수료)), 부족분은 기록
            cost = -dc_o * (1 + cfg.fee_rate)
            avail = max(st["cash"], 0.0)
            if cost > avail + 1e-9:
                fb = avail / cost
                target = dq_o
                dq_o, dc_o, dcost_o = dq_o * fb, dc_o * fb, dcost_o * fb
                st["counters"]["short_buys"] += 1
                self._ev("short_buys", row["date"], target_qty=round(target, 6), got_qty=round(dq_o, 6),
                         short_qty=round(target - dq_o, 6), avg_price=round(-dc / dq, 6) if dq else None,
                         cash_before=round(st["cash"], 4),
                         approx=(kind == "mixed"),
                         note=("혼합 체결일: 순매수분에만 한도 적용(근사) — 미확인" if kind == "mixed" else None))
        notional = abs(dc_o)
        side = "buy" if dc_o < 0 else "sell"
        fee = fee_amount(side, notional, cfg) if kind != "idle" else 0.0
        st["core_qty"] = max(0.0, st["core_qty"] + dq_o)
        st["core_cost"] = max(0.0, st["core_cost"] + dcost_o)
        if st["core_qty"] < EPS:
            st["core_qty"], st["core_cost"] = 0.0, 0.0
        was_neg = st["cash"] < -1e-6
        st["cash"] += dc_o - fee
        if st["cash"] < -1e-6 and not was_neg:
            self._ev("anomaly", row["date"], what="cash_negative", cash=round(st["cash"], 4),
                     note="가드: 매수는 현금 한도로 줄이므로 매수로는 안 떠야 함 — 뜨면 수수료·초기 상태 등 다른 원인 확인")
        ss = st["season_stats"]
        ss["R_gross"] += dS_o
        ss["fees"] += fee
        if kind == "mixed":
            st["counters"]["mixed_days"] += 1
        self._ev("tx", row["date"], fill_kind=kind, mult=round(m, 6), d_qty=round(dq_o, 6), d_cash=round(dc_o, 4),
                 d_realized=round(dS_o, 4), fee=round(fee, 4),
                 fee_lower_bound=(kind == "mixed"),
                 note=("혼합 체결일: 표만으로 총거래대금 불명 → 수수료는 순현금흐름 기준 하한 (미확인)" if kind == "mixed" else None))
        st["last"] = row

    # ---- 표 보유 0 다음 표일 종가 초과 보유 별도 매도 (코드에 없는 새 경로 — 그림자는 기록만)
    def _excess_exec(self, row):
        st, cfg = self.st, self.cfg
        pe = st["pending_excess"]
        if not pe or st["exc_qty"] < EPS:
            st["pending_excess"] = None
            return
        qty, price = st["exc_qty"], row["close"]
        avg = st["exc_cost"] / qty
        proceeds = qty * price
        fee = fee_amount("sell", proceeds, cfg)
        pnl = qty * (price - avg)
        st["cash"] += proceeds - fee
        ss = st["season_stats"]
        ss["excess_pnl"] += pnl
        ss["fees"] += fee
        st["exc_qty"], st["exc_cost"] = 0.0, 0.0
        st["pending_excess"] = None
        st["counters"]["excess_sells"] += 1
        self._ev("excess_sell", row["date"], qty=round(qty, 6), price=price, avg_cost=round(avg, 4), pnl=round(pnl, 4),
                 fee=round(fee, 4), scheduled_on=pe["scheduled_on"],
                 order_type="미확인 (표일 종가 매도 주문 방식은 코드에 없음)")

    # ---- 분리 실행: 감지 다음 표일
    def _separation_exec(self, row):
        st, cfg = self.st, self.cfg
        ps = st["pending_sep"]
        if not ps:
            return
        st["pending_sep"] = None
        amount = self.retained()
        if amount <= EPS:
            self._ev("separation_cancelled", row["date"], reason="실행일 남은 순수익 ≤ 0", detected_on=ps["detected_on"])
            return
        withdraw = min(amount, max(0.0, st["cash"]))
        if withdraw < amount - 1e-6:
            st["counters"]["cash_short"] += 1
            self._ev("anomaly", row["date"], what="cash_short", wanted=round(amount, 4), cash=round(st["cash"], 4),
                     note="손익금이 현금보다 큼 → 현금 한도로 인출 (백테스트 판 3은 이런 날 0)")
        st["cash"] -= withdraw
        st["withdrawn_total"] += withdraw
        st["season_stats"]["W"] += withdraw
        sgov_buy_fee = withdraw * cfg.sgov_buy_fee_rate
        st["sgov_usd"] += withdraw - sgov_buy_fee
        old_scale = st["scale"]
        new_scale = st["T"] / (cfg.base_units + row["S"])
        if new_scale <= 0 or not math.isfinite(new_scale):
            new_scale = old_scale
        st["scale"] = new_scale
        target_core = new_scale * row["hold"]
        moved = max(0.0, st["core_qty"] - target_core)
        if moved > EPS and st["core_qty"] > EPS:
            avg = st["core_cost"] / st["core_qty"]
            st["core_qty"] -= moved
            st["core_cost"] -= moved * avg
            st["exc_qty"] += moved
            st["exc_cost"] += moved * avg
        st["counters"]["separations"] += 1
        self._ev("separation", row["date"], detected_on=ps["detected_on"], g_at_detect=round(ps["g"], 6),
                 withdraw=round(withdraw, 4), sgov_buy_usd=round(withdraw - sgov_buy_fee, 4),
                 sgov_buy_fee=round(sgov_buy_fee, 4), sgov_qty=None,
                 note="SGOV 수량은 SGOV 시세 미연결(미확인) — 달러만 기록; 계좌 이동·결제일은 이동 가능 가정(Q5 미확인)",
                 scale_old=round(old_scale, 6), scale_new=round(new_scale, 6),
                 scale_formula="T÷(base+표 시즌실현수익)", S_table=row["S"],
                 new_excess_qty=round(moved, 6), excess_qty_total=round(st["exc_qty"], 6))

    # ---- 마감 처리: 초과 해소 예약 + 분리 감지 + 다음 주문 계획
    def _after_close(self, row):
        st = self.st
        if row["hold"] == 0 and st["exc_qty"] > EPS and not st["pending_excess"]:
            st["pending_excess"] = {"scheduled_on": row["date"]}
            self._ev("excess_sell_scheduled", row["date"], excess_qty=round(st["exc_qty"], 6),
                     rule="표 보유 0 확인 → 다음 표일 종가에 초과 보유 전량 별도 매도")
        g = self.g()
        if g * 100.0 >= self.cfg.threshold_pct - EPS and not st["pending_sep"]:
            st["pending_sep"] = {"detected_on": row["date"], "g": g}
            self._ev("separation_detected", row["date"], g=round(g, 6), threshold_pct=self.cfg.threshold_pct,
                     retained_net=round(self.retained(), 4), execute_on="다음 표일")
        self._plan(row)

    # ---- 다음 날 주문 계획 (기록용; 새 배수 × 표 수량, 내 보유 기준 cap_sells)
    def _plan(self, row):
        st = self.st
        m = st["scale"]
        lines = raw_lines(row["buys"], row["sells"], m)
        lines, cut = cap_sells(lines, self.own_qty())
        buy_notional = sum(p * q for s, p, q in lines if s == "buy")
        buy_total = buy_notional * self.cfg.real_mult      # 따라잡기 매수는 그림자에 없음(0) — 미반영
        over = buy_total > self.cfg.max_buy_usd + 1e-9
        if over:
            st["counters"]["buy_over_limit"] += 1
            self._ev("buy_total_over_limit", row["date"], buy_total=round(buy_total, 4), limit=self.cfg.max_buy_usd,
                     real_mult=self.cfg.real_mult, catchup_included=False,
                     status="자동주문 차단·수동 결정 대기 (fanding_trade checks: buy_total ≤ max_buy_usd → auto_ok=False)",
                     qty_reduced=False)
        self._ev("plan", row["date"], mult=round(m, 6),
                 buys=[(p, round(q, 6)) for s, p, q in lines if s == "buy"],
                 sells=[(p, round(q, 6)) for s, p, q in lines if s == "sell"],
                 cap_cut=round(cut, 6),
                 buys_floor=[(p, math.floor(q + EPS)) for s, p, q in lines if s == "buy"],
                 sells_floor=[(p, math.floor(q + EPS)) for s, p, q in lines if s == "sell"],
                 int_rounding="미확인 (코드의 배수·수량은 정수; 여기는 소수 그대로 + floor 참고값)",
                 buy_notional=round(buy_notional, 4), cash=round(st["cash"], 4),
                 cash_short_for_buys=buy_notional > st["cash"] + 1e-6,
                 auto_order_blocked=over,
                 own_qty=round(self.own_qty(), 6), exc_qty=round(st["exc_qty"], 6),
                 retained_net=round(self.retained(), 4), g=round(self.g(), 6))

    # ---- 시즌 리셋 (표가 원금으로 돌아감). 리셋 배수는 설정값/모드
    def _season_reset(self, row):
        st, cfg = self.st, self.cfg
        keep = max(0.0, self.retained())
        if cfg.reset_mult is not None:
            mult, how = cfg.reset_mult, "설정값(reset_mult)"
        elif cfg.reset_mode == "fixed":
            mult, how = 1.0, "고정=1"
        else:
            mult, how = (st["T"] + keep) / cfg.base_units, "복리=(T+남은 실현 순수익)÷base"
        prev = {"season": st["season"], "r_net": round(self.r_net(), 4), "W": round(st["season_stats"]["W"], 4),
                "retained": round(keep, 4), "scale": round(st["scale"], 6), "T": st["T"]}
        st["scale"] = mult
        st["T"] = cfg.base_units * mult
        st["season"] = row["season"]
        if not cfg.carry_across_seasons:
            st["season_stats"] = {"R_gross": 0.0, "fees": 0.0, "excess_pnl": 0.0, "W": 0.0}
        st["pending_sep"] = None
        st["last"] = row
        self._ev("season_reset", row["date"], how=how, new_scale=round(mult, 6), new_T=round(st["T"], 4), prev=prev,
                 note="리셋 시점 내 보유·초과 보유·현금은 그대로 (표는 원금으로 복귀) — 리셋 뒤 처리 방식은 판 3 미확인 항목")
        self._after_close_light(row)
        return self.events

    def _after_close_light(self, row):
        if row["hold"] == 0 and self.st["exc_qty"] > EPS and not self.st["pending_excess"]:
            self.st["pending_excess"] = {"scheduled_on": row["date"]}
            self._ev("excess_sell_scheduled", row["date"], excess_qty=round(self.st["exc_qty"], 6),
                     rule="표 보유 0 확인 → 다음 표일 종가에 초과 보유 전량 별도 매도")
        self._plan(row)

    # ---- 저장/불러오기
    def snapshot(self):
        st = json.loads(json.dumps(self.st))
        if st["last"]:
            st["last"]["buys"] = [list(x) for x in st["last"]["buys"]]
            st["last"]["sells"] = [list(x) for x in st["last"]["sells"]]
        return st

    @classmethod
    def from_state(cls, state, log=None):
        cfg = VaultConfig(**state["config"])
        for k in ("short_buys", "buy_over_limit"):       # v0.1.0 상태 파일 호환
            state["counters"].setdefault(k, 0)
        if state.get("last"):
            state["last"]["buys"] = [tuple(x) for x in state["last"]["buys"]]
            state["last"]["sells"] = [tuple(x) for x in state["last"]["sells"]]
        return cls(cfg, state, log)


# ---------------------------------------------------------------- 파일 입출력 (그림자 상태 폴더)
def _atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def shadow_dir(home):
    return Path(home) / "vault_shadow"


def load_shadow(home, cfg=None):
    d = shadow_dir(home)
    events_path = d / "events.jsonl"

    def log(e):
        events_path.parent.mkdir(parents=True, exist_ok=True)
        with open(events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    p = d / "state.json"
    if p.exists():
        return VaultShadow.from_state(json.loads(p.read_text(encoding="utf-8")), log)
    return VaultShadow(cfg, None, log)


def save_shadow(home, vs):
    _atomic_write(shadow_dir(home) / "state.json", vs.snapshot())


def row_from_sheet(parsed, cfg=None, season=None):
    """fanding_trade 가격표(parsed, normalize() 결과) → 표 한 줄. 칸이 비면 None.
    시즌실현수익 칸 매핑(cfg.s_field)은 미확인 가정."""
    cfg = cfg or VaultConfig()
    ex = parsed.get("extra") or {}
    S = ex.get(cfg.s_field)
    if S is None or parsed.get("holding_qty") is None or ex.get("cash_usd") is None:
        return None
    return {"date": parsed.get("close_date"), "close": parsed.get("close"), "hold": parsed.get("holding_qty"),
            "avg": parsed.get("avg_price"), "cash": ex.get("cash_usd"), "S": S, "season": season,
            "buys": [(r["price"], r["qty"]) for r in parsed.get("buys", [])],
            "sells": [(r["price"], r["qty"]) for r in parsed.get("sells", [])]}


def shadow_on_sheet(parsed, home, cfg=None):
    """훅용 한 줄 진입점. 그림자 상태에 표 한 줄을 반영하고 저장. 예외는 호출자(훅)가 삼킴. 주문 없음."""
    vs = load_shadow(home, cfg)
    row = row_from_sheet(parsed, vs.cfg)
    if row is None:
        vs._ev("skipped_row", str(parsed.get("close_date")), reason="표 칸 부족 (보유·잔금·실현수익 중 없음)")
        return vs.events
    ev = vs.step(row)
    save_shadow(home, vs)
    return ev
