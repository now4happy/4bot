"""책 D/D+1/D+2 규칙 엔진. 백테스트와 그림자 모드가 같은 코드를 쓴다. 주문은 내지 않는다. [v2]

봉(bar) = {"t": 봉 시작 datetime(KST, tz 없음), "o","h","l","c","v"}.
"""
import math
from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta
from itertools import product

from . import config as B
from .orders import intent


def hm(s):
    h, m = s.split(":")
    return dtime(int(h), int(m))


def tick(p):
    for lim, t in B.TICKS:
        if p < lim:
            return t


def up_tick(p):
    t = tick(p)
    return math.ceil(p / t) * t


def upper_limit(prev_close):
    raw = prev_close * (1 + B.PRICE_LIMIT)
    t = tick(raw)
    return int(raw) // t * t


@dataclass(frozen=True)
class Variant:
    bar_m: int
    confirm: str
    fail_stop: bool
    tp_pct: float
    last_entry: str
    stop_pct: float = B.STOP_PCT     # 판 2: 손절폭 축. 기본값 = 판 1 고정값 0.03

    @property
    def id(self):
        return (f"m{self.bar_m}-{self.confirm}-fs{int(self.fail_stop)}-tp{self.tp_pct:g}"
                f"-le{self.last_entry.replace(':', '')}-sl{self.stop_pct * 100:g}")


def grid():
    keys = list(B.AXIS)
    return [Variant(**dict(zip(keys, vals))) for vals in product(*(B.AXIS[k] for k in keys))]


def neighbors(v, allv):
    """축 하나만 한 칸 다른 변형들."""
    out = []
    for w in allv:
        diff = [k for k in B.AXIS if getattr(v, k) != getattr(w, k)]
        if len(diff) == 1:
            ax = B.AXIS[diff[0]]
            if abs(ax.index(getattr(v, diff[0])) - ax.index(getattr(w, diff[0]))) == 1:
                out.append(w)
    return out


def day_ctx(rows, shares):
    """D일 이전 일봉(오름차순, D일 제외)으로 D일 판정 기준을 만든다. 자료가 모자라면 None."""
    if len(rows) < max(B.HIGH_LOOKBACK, max(B.MA_SET)):
        return None
    prev_close = rows[-1]["c"]
    if prev_close <= 0:
        return None
    prior_high = max(r["h"] for r in rows[-B.HIGH_LOOKBACK:])
    ma = [sum(r["c"] for r in rows[-n:]) / n for n in B.MA_SET]
    large = shares is not None and shares * prev_close >= B.LARGE_CAP
    d_min = B.D_MIN_LARGE if large else B.D_MIN
    return {"prev_close": prev_close, "prior_high": prior_high,
            "ma_ok": all(a > b for a, b in zip(ma, ma[1:])), "d_min": d_min,
            "cap_known": shares is not None,
            "level": max(prior_high, prev_close * (1 + d_min))}


def in_session(t):
    return hm(B.SESSION_OPEN) <= t.time() < hm(B.SESSION_CLOSE)


def aggregate(bars1, m):
    """1분봉 목록 → m분봉 목록 (정규장만)."""
    out = []
    for b in bars1:
        if not in_session(b["t"]):
            continue
        mod = b["t"].hour * 60 + b["t"].minute
        st = b["t"].replace(minute=0, second=0, microsecond=0, hour=0) + timedelta(
            minutes=mod - mod % m)
        if out and out[-1]["t"] == st:
            x = out[-1]
            x["h"], x["l"], x["c"], x["v"] = max(x["h"], b["h"]), min(x["l"], b["l"]), b["c"], \
                x["v"] + b["v"]
        else:
            out.append({"t": st, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]})
    return out


def costs(buy, sell, qty, year):
    return buy * qty * B.COMMISSION + sell * qty * (B.COMMISSION + B.TAX.get(year, max(B.TAX.values())))


class Book:
    """변형 1개의 가상 장부. 동시 보유 1종목, 일일 손실 한도, 물타기 없음."""

    def __init__(self, v, log=None):
        self.v = v
        self.log = log or (lambda e: None)
        self.pos = None
        self.pending = None
        self.day = None
        self.day_pnl = 0.0
        self.halted = False
        self.done = set()
        self.trades = []

    def _roll(self, d):
        if d != self.day:
            self.day, self.day_pnl, self.halted, self.done, self.pending = d, 0.0, False, set(), None

    def on_bar(self, code, bar, ctx):
        """ctx: day_ctx 결과 + "eligible"(순위·정배열·제외 판정). 보유 종목이면 ctx 불필요."""
        self._roll(bar["t"].date())
        if self.pos:
            if self.pos["code"] == code and bar["t"] > self.pos["last_t"]:
                self._manage(bar)
            return
        ok = not self.halted and bool(ctx) and ctx.get("eligible") and code not in self.done
        if self.pending == code:
            self.pending = None
            if ok:
                self._enter(code, bar, ctx, bar["o"] * (1 + B.SLIPPAGE), "close")
            return
        if not ok:
            return
        if self.pending or not hm(B.ENTRY_START) <= bar["t"].time() < hm(self.v.last_entry):
            return
        if self.v.confirm == "touch":
            if bar["h"] > ctx["level"]:
                self._enter(code, bar, ctx, max(up_tick(ctx["level"]), bar["o"]), "touch")
        elif bar["c"] > ctx["level"]:
            self.pending = code        # 다음 봉 시가에 체결로 가정

    def _enter(self, code, bar, ctx, price, how):
        self.done.add(code)
        qty = int(B.BOWL // price)
        if price >= upper_limit(ctx["prev_close"]) or qty < 1:
            self.log({"ev": "skip", "variant": self.v.id, "code": code, "t": bar["t"].isoformat(),
                      "why": "upper_limit" if qty >= 1 else "qty0", "price": price})
            return
        self.pos = {"code": code, "E": price, "qty": qty, "dates": [bar["t"].date()],
                    "ref": ctx["prev_close"], "last_c": bar["c"], "last_t": bar["t"],
                    "prior_high": ctx["prior_high"], "entry_t": bar["t"], "how": how}
        self.log({"ev": "entry", "variant": self.v.id, "code": code, "t": bar["t"].isoformat(),
                  "price": price, "qty": qty, "how": how,
                  "basis": {k: ctx.get(k) for k in ("prev_close", "prior_high", "d_min", "level",
                                                    "rank", "flu", "cap_known")},
                  "intent": intent("buy", code, qty, "limit", price)})
        self._manage(bar, fresh=True)

    def _manage(self, bar, fresh=False):
        p, s = self.pos, B.SLIPPAGE
        o, h, l, c = bar["o"], bar["h"], bar["l"], bar["c"]
        first = False
        if bar["t"].date() != p["dates"][-1]:
            p["dates"].append(bar["t"].date())
            p["ref"] = p["last_c"]
            first = True
        idx = len(p["dates"]) - 1
        stop, line = p["E"] * (1 - self.v.stop_pct), p["ref"] * (1 - B.GAP_PCT)
        end = (bar["t"] + timedelta(minutes=self.v.bar_m)).time()
        if idx > 2:
            return self._exit(bar["t"], o * (1 - s), "overdue")
        if first and o <= line:                      # D+1·D+2 시초가 -1%
            return self._exit(bar["t"], o * (1 - s), f"d{idx}_open_gap")
        # touch 진입 봉: ENTRY_BAR_STOP=close 면 종가로 판정 (저가는 진입 이전일 수 있음). 그 밖의 봉은 저가.
        low_for_stop = c if (fresh and p["how"] == "touch" and B.ENTRY_BAR_STOP == "close") else l
        if low_for_stop <= stop:                     # 기계적 손절 (같은 봉이면 불리하게 가정)
            return self._exit(bar["t"], (stop if fresh else min(o, stop)) * (1 - s),
                              f"stop{self.v.stop_pct * 100:g}")   # 0.03 -> "stop3" (판 1 라벨 유지)
        if idx == 2 and l <= line:                   # D+2 손절 라인
            return self._exit(bar["t"], min(o, line) * (1 - s), "d2_line")
        if idx == 0 and self.v.fail_stop and not fresh and c < p["prior_high"]:
            return self._exit(bar["t"], c * (1 - s), "break_fail")
        if idx >= 1 and bar["t"].time() < hm(B.TP_CUTOFF):
            tp = p["ref"] * (1 + self.v.tp_pct / 100)
            if h >= tp:
                return self._exit(bar["t"], max(o, tp), f"d{idx}_tp")
        if idx == 2 and end >= hm(B.D2_EXIT):
            return self._exit(bar["t"], c * (1 - s), "d2_time")
        p["last_c"], p["last_t"] = c, bar["t"]

    def end_of_day(self, d):
        p = self.pos
        if p and p["dates"][-1] == d and len(p["dates"]) - 1 >= 2:
            self._exit(p["last_t"], p["last_c"] * (1 - B.SLIPPAGE), "d2_eod")

    def _exit(self, t, price, reason):
        p = self.pos
        fee = costs(p["E"], price, p["qty"], t.year)
        net = (price - p["E"]) * p["qty"] - fee
        tr = {"variant": self.v.id, "code": p["code"], "entry_t": p["entry_t"].isoformat(),
              "exit_t": t.isoformat(), "entry": p["E"], "exit": price, "qty": p["qty"],
              "fee": round(fee), "net": round(net), "reason": reason, "how": p["how"],
              "days": len(p["dates"])}
        self.trades.append(tr)
        self.pos = None
        if t.date() == self.day:
            self.day_pnl += net
            if self.day_pnl <= -B.DAILY_LOSS_LIMIT:
                self.halted = True
        self.log({"ev": "exit", **tr, "intent": intent("sell", tr["code"], tr["qty"], "market")})

    # --- 그림자 모드 상태 저장용 ---
    def to_state(self):
        p = dict(self.pos) if self.pos else None
        if p:
            p["dates"] = [d.isoformat() for d in p["dates"]]
            p["last_t"], p["entry_t"] = p["last_t"].isoformat(), p["entry_t"].isoformat()
        return {"pos": p, "pending": self.pending, "day": self.day and self.day.isoformat(),
                "day_pnl": self.day_pnl, "halted": self.halted, "done": sorted(self.done)}

    def from_state(self, st):
        p = st.get("pos")
        if p:
            p["dates"] = [datetime.fromisoformat(d).date() for d in p["dates"]]
            p["last_t"] = datetime.fromisoformat(p["last_t"])
            p["entry_t"] = datetime.fromisoformat(p["entry_t"])
        self.pos, self.pending = p, st.get("pending")
        self.day = datetime.fromisoformat(st["day"]).date() if st.get("day") else None
        self.day_pnl, self.halted = st.get("day_pnl", 0.0), st.get("halted", False)
        self.done = set(st.get("done", []))
