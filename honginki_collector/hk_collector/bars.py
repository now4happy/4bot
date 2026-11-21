"""0B 틱 → 자체 분봉 (1·2·3·5분). 마감된 봉만 내보낸다. 신호 평가는 하지 않는다."""
from datetime import datetime, timedelta

from .config import KST


def num(s):
    """'+60700', '-20800', '--30000' → 60700 / 20800 / 30000 (부호 제거)."""
    s = str(s).strip().lstrip("+-")
    return int(s) if s.isdigit() else None


class BarBuilder:
    def __init__(self, minutes, on_bar, grace_s=3.0):
        self.m = minutes
        self.on_bar = on_bar
        self.grace = timedelta(seconds=grace_s)
        self.cur = {}
        self.closed_until = {}
        self.late = 0
        self.gaps = []  # [(start_dt, end_dt)]

    def _start(self, t):
        mod = t.hour * 60 + t.minute
        mod -= mod % self.m
        return t.replace(hour=mod // 60, minute=mod % 60, second=0, microsecond=0)

    def mark_gap(self, a, b):
        self.gaps.append((a, b))

    def tick(self, item, values, day=None):
        hhmmss = str(values.get("20", ""))
        p, v = num(values.get("10")), num(values.get("15"))
        if len(hhmmss) != 6 or not hhmmss.isdigit() or p is None or v is None:
            return
        day = day or datetime.now(KST).date()
        t = datetime(day.year, day.month, day.day, int(hhmmss[:2]), int(hhmmss[2:4]),
                     int(hhmmss[4:]), tzinfo=KST)
        st = self._start(t)
        if item in self.closed_until and st < self.closed_until[item]:
            self.late += 1
            return
        b = self.cur.get(item)
        if b and st < b["_st"]:
            self.late += 1
            return
        if b and st > b["_st"]:
            self._close(item, "next_tick")
            b = None
        if b is None:
            b = self.cur[item] = {"_st": st, "o": p, "h": p, "l": p, "c": p, "v": 0, "tv": 0,
                                  "n": 0, "first_ex": hhmmss}
        b["h"], b["l"], b["c"] = max(b["h"], p), min(b["l"], p), p
        b["v"] += v
        b["tv"] += p * v
        b["n"] += 1
        b["last_ex"] = hhmmss

    def sweep(self, now=None):
        now = now or datetime.now(KST)
        for item in [k for k, b in self.cur.items()
                     if now >= b["_st"] + timedelta(minutes=self.m) + self.grace]:
            self._close(item, "timer")

    def _close(self, item, reason):
        b = self.cur.pop(item)
        st = b.pop("_st")
        en = st + timedelta(minutes=self.m)
        self.closed_until[item] = en
        gap = any(a < en and g > st for a, g in self.gaps)
        self.on_bar({"item": item, "m": self.m, "start": st.isoformat(), "end": en.isoformat(),
                     **b, "close_reason": reason, "gap": gap})

    def flush_all(self):
        for item in list(self.cur):
            self._close(item, "session_end")
