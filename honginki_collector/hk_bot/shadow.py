"""그림자 모드: 수집기가 쌓는 실시간 자료(1분봉·거래대금 순위)를 읽어 가상 매매를 기록만 한다.

주문은 내지 않는다. 키움 호출은 조회뿐이다 (후보 종목 일봉, 종목 목록, 보유 종목 분봉 보충).
기록: BOT_DIR/shadow_trades.jsonl, 상태: BOT_DIR/shadow_state.json
"""
import json
import os
import signal
import time
from datetime import datetime, timedelta

from hk_collector import config as C

from . import config as B
from . import hist
from .strategy import Book, day_ctx, grid, hm, in_session

FLUSH_GRACE_S = 20       # 임시값: 수집기 1분봉이 도착할 여유
STALE_S = 120            # 임시값: 보유 종목 봉이 이만큼 안 오면 REST로 보충


class Tail:
    def __init__(self, path, offset=0):
        self.path, self.offset = path, offset

    def lines(self):
        try:
            with open(self.path, "rb") as f:
                f.seek(self.offset)
                data = f.read()
        except OSError:
            return []
        end = data.rfind(b"\n") + 1
        self.offset += end
        out = []
        for ln in data[:end].splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
        return out


class Agg:
    def __init__(self, m):
        self.m, self.cur, self.last = m, None, None

    def _start(self, t):
        mod = t.hour * 60 + t.minute
        return t.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
            minutes=mod - mod % self.m)

    def push(self, b):
        st, out = self._start(b["t"]), []
        if self.last is not None and st <= self.last:
            return out                         # 이미 내보낸 구간의 늦은 봉
        if self.cur and self.cur["t"] != st:
            out.append(self._emit())
        if self.cur is None:
            self.cur = {"t": st, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"], "v": b["v"]}
        else:
            x = self.cur
            x["h"], x["l"], x["c"], x["v"] = max(x["h"], b["h"]), min(x["l"], b["l"]), b["c"], \
                x["v"] + b["v"]
        if (b["t"].hour * 60 + b["t"].minute) % self.m == self.m - 1:
            out.append(self._emit())
        return out

    def flush(self, now):
        if self.cur and now >= self.cur["t"] + timedelta(minutes=self.m, seconds=FLUSH_GRACE_S):
            return [self._emit()]
        return []

    def _emit(self):
        x, self.cur = self.cur, None
        self.last = x["t"]
        return x


class Shadow:
    def __init__(self, now_fn=None, daily_fn=None, minute_fn=None, universe_fn=None):
        self.now_fn = now_fn or (lambda: datetime.now(C.KST).replace(tzinfo=None))
        self._rest = None
        self.daily_fn = daily_fn or self._daily
        self.minute_fn = minute_fn or self._minute
        self.universe_fn = universe_fn or self._universe
        self.books = {v.id: Book(v, self._log) for v in grid()}
        self.by_m = {}
        for b in self.books.values():
            self.by_m.setdefault(b.v.bar_m, []).append(b)
        self.day = None
        self.state_path = os.path.join(B.BOT_DIR, "shadow_state.json")
        self.log_path = os.path.join(B.BOT_DIR, "shadow_trades.jsonl")
        os.makedirs(B.BOT_DIR, exist_ok=True)
        st = hist._load(self.state_path) or {}
        for vid, bs in (st.get("books") or {}).items():
            if vid in self.books:
                self.books[vid].from_state(bs)
        self._new_day(st.get("day"), st.get("offsets") or {})
        self.fed = {k: datetime.fromisoformat(v) for k, v in (st.get("fed") or {}).items()}
        self.eod_done = st.get("eod_done", False)

    # --- 조회 (기본 구현) ---
    def rest(self):
        if self._rest is None:
            self._rest = hist.make_rest()[0]
        return self._rest

    def _daily(self, code, day):
        return hist.fetch_daily_one(self.rest(), code, day)

    def _minute(self, code, day):
        pages = self.rest().call("ka10080", {"stk_cd": code, "tic_scope": "1", "upd_stkpc_tp": "1",
                                             "base_dt": day}, tag="shadow_held")
        return [r for r in hist.parse_minute(hist._rows(pages, "stk_min_pole_chart_qry"))
                if r["t"][:8] == day]

    def _universe(self, day):
        saved = hist._load(hist._p("universe.json")) or {}
        if saved.get("asof") == day:
            return saved.get("codes", {})
        return hist.fetch_universe(self.rest()) or saved.get("codes", {})

    # --- 내부 ---
    def _log(self, e):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": self.now_fn().isoformat(timespec="seconds"), "mode": "shadow",
                                **e}, ensure_ascii=False) + "\n")

    def _new_day(self, day, offsets=None):
        offsets = offsets or {}
        self.day = day
        d = os.path.join(C.DATA_DIR, day or "-")
        self.t_bars = Tail(os.path.join(d, "bars_1m.jsonl"), offsets.get("bars", 0))
        self.t_rank = Tail(os.path.join(d, "rest_ka10032.jsonl"), offsets.get("rank", 0))
        self.rank, self.limit, self.base, self.aggs = {}, B.RANK_LIMITS[1], {}, {}
        self.last_bar, self.last_fill, self.fed = {}, {}, {}
        self.uni = None
        self.eod_done = False

    def _save(self):
        hist._save(self.state_path, {"day": self.day, "eod_done": self.eod_done,
                                     "offsets": {"bars": self.t_bars.offset, "rank": self.t_rank.offset},
                                     "fed": {k: v.isoformat() for k, v in self.fed.items()},
                                     "books": {k: b.to_state() for k, b in self.books.items()}})

    def _read_rank(self):
        recs = [r for r in self.t_rank.lines() if r.get("page") == 0]
        if not recs:
            return
        try:
            rows = json.loads(recs[-1]["raw"]).get("trde_prica_upper") or []
        except (ValueError, KeyError, AttributeError):
            return
        rank = {}
        for r in rows:
            try:
                rank[str(r["stk_cd"]).split("_")[0]] = (int(r["now_rank"]), float(r["flu_rt"]))
            except (KeyError, ValueError, TypeError):
                continue
        if rank:
            self.rank = rank
            lead = any(n <= B.RANK_LIMITS[0] and f >= B.THEME_MIN_FLU for n, f in rank.values())
            self.limit = B.RANK_LIMITS[0] if lead else B.RANK_LIMITS[1]

    def _ctx(self, code):
        info = self.rank.get(code)
        if not info:
            return None
        n, flu = info
        if code not in self.base:
            if n > B.RANK_LIMITS[1] or flu < B.D_MIN_LARGE * 100:
                return None                    # 아직 일봉을 받을 만큼 오르지 않음
            if self.uni is None:
                try:
                    self.uni = self.universe_fn(self.day) or {}
                except Exception as e:  # noqa: BLE001
                    self.uni = {}
                    self._log({"ev": "error", "what": "universe", "err": f"{type(e).__name__}: {e}"})
                if not self.uni:
                    self._log({"ev": "warn", "what": "universe_missing"})
            base = None
            if code in self.uni:
                try:
                    rows = [r for r in self.daily_fn(code, self.day) if r["dt"] < self.day]
                    base = day_ctx(rows, self.uni[code].get("shares"))
                    if base is None:
                        self._log({"ev": "warn", "what": "history_short", "code": code,
                                   "rows": len(rows)})
                except Exception as e:  # noqa: BLE001
                    self._log({"ev": "error", "what": "daily", "code": code,
                               "err": f"{type(e).__name__}: {e}"})
            self.base[code] = base
        base = self.base[code]
        if not base:
            return None
        return {**base, "rank": n, "flu": flu,
                "eligible": base["ma_ok"] and n <= self.limit and flu >= B.THEME_MIN_FLU}

    def _feed(self, code, b1):
        if not in_session(b1["t"]) or b1["t"] <= self.fed.get(code, datetime.min):
            return
        self.fed[code] = b1["t"]
        for m in self.by_m:
            agg = self.aggs.setdefault((code, m), Agg(m))
            for nb in agg.push(b1):
                self._dispatch(code, nb, m)

    def _dispatch(self, code, bar, m):
        held = any(b.pos and b.pos["code"] == code for b in self.by_m[m])
        ctx = self._ctx(code)
        if ctx or held:
            for b in self.by_m[m]:
                b.on_bar(code, bar, ctx)

    def _fill_held(self, now):
        if not in_session(now):
            return
        for code in {b.pos["code"] for b in self.books.values() if b.pos}:
            seen = self.last_bar.get(code, datetime.combine(now.date(), hm(B.SESSION_OPEN)))
            if (now - seen).total_seconds() < STALE_S or \
                    (now - self.last_fill.get(code, datetime.min)).total_seconds() < 60:
                continue
            self.last_fill[code] = now
            try:
                rows = self.minute_fn(code, self.day)
            except Exception as e:  # noqa: BLE001
                self._log({"ev": "error", "what": "minute", "code": code,
                           "err": f"{type(e).__name__}: {e}"})
                continue
            for r in rows:
                t = datetime.strptime(r["t"], "%Y%m%d%H%M%S")
                if t + timedelta(minutes=1, seconds=5) <= now:
                    self._feed(code, {**r, "t": t})

    def step(self):
        now = self.now_fn()
        day = now.strftime("%Y%m%d")
        if day != self.day:
            self._new_day(day)
        self._read_rank()
        for r in self.t_bars.lines():
            try:
                t = datetime.fromisoformat(r["start"]).replace(tzinfo=None)
                b1 = {"t": t, "o": r["o"], "h": r["h"], "l": r["l"], "c": r["c"], "v": r["v"]}
            except (KeyError, ValueError, TypeError):
                continue
            self.last_bar[r["item"]] = now
            self._feed(r["item"], b1)
        for (code, m), agg in list(self.aggs.items()):
            for nb in agg.flush(now):
                self._dispatch(code, nb, m)
        self._fill_held(now)
        if not self.eod_done and now.time() >= hm("15:35"):
            for b in self.books.values():
                b.end_of_day(now.date())
            self.eod_done = True
            self._log({"ev": "eod", "open": sum(1 for b in self.books.values() if b.pos)})
        self._save()


def main():
    stop = []
    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, lambda *_: stop.append(1))
    sh = Shadow()
    while not stop:
        now = sh.now_fn()
        if now.weekday() < 5 and hm("08:55") <= now.time() < hm("15:45"):
            sh.step()
            time.sleep(2)
        else:
            time.sleep(20)
