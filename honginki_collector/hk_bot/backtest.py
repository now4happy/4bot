"""등급 분리 범위 백테스트. 책 확정 규칙은 고정, 등급 C 축만 격자 탐색. 결과: BOT_DIR/backtest_result.json [v2]"""
import json
import os
from collections import Counter, defaultdict
from datetime import datetime

from . import config as B
from . import hist
from .strategy import Book, aggregate, grid, neighbors

APPROX = [
    "거래대금 순위: 과거 장중 순위(ka10032)는 복원 불가 → 그날 일봉 거래대금 순위로 대체 (미래 정보 포함)",
    "시가총액: 현재 상장주식수 × 전일 종가",
    "ETF·ETN은 종목 목록으로, 스팩은 이름으로 제외",
    "체결: 터치=돌파 가격(호가 올림) 지정가 체결 가정, 종가 확정=다음 봉 시가+미끄러짐, 미체결 없음 가정",
    "같은 봉 안의 진입·손절 순서는 알 수 없어 손절 먼저로 가정",
    "수수료율·미끄러짐·정배열 이평선 묶음·D+2 청산 시각은 미확인/임시값 (config.py)",
    "테마 판정 없음 (거래대금 순위 + 상승률만 사용)",
]


def metrics(trades, days):
    by_day = defaultdict(float)
    for t in trades:
        by_day[t["exit_t"][:10]] += t["net"]
    eq = peak = dd = 0.0
    peak_i, rec, open_dd = 0, 0, False
    series = []
    for i, d in enumerate(days):
        x = by_day.get(f"{d[:4]}-{d[4:6]}-{d[6:]}", 0.0)
        series.append(x)
        eq += x
        if eq >= peak:
            if open_dd:
                rec = max(rec, i - peak_i)
            peak, peak_i, open_dd = eq, i, False
        else:
            open_dd = True
            dd = max(dd, peak - eq)
    n = len(trades)
    wins = [t["net"] for t in trades if t["net"] > 0]
    loss = [-t["net"] for t in trades if t["net"] <= 0]
    mean = sum(series) / len(series) if series else 0.0
    std = (sum((x - mean) ** 2 for x in series) / len(series)) ** 0.5 if series else 0.0
    by_month = defaultdict(float)
    for t in trades:
        by_month[t["exit_t"][:7]] += t["net"]
    return {"trades": n, "win_rate": round(len(wins) / n, 3) if n else None,
            "net": round(sum(t["net"] for t in trades)),
            "ret_pct": round(sum(t["net"] for t in trades) / B.BOWL * 100, 2),
            "profit_factor": round(sum(wins) / sum(loss), 2) if loss and sum(loss) else None,
            "max_dd": round(dd), "recovery_days": rec, "dd_unrecovered": open_dd,
            "daily_std": round(std), "plus_days": sum(x > 0 for x in series),
            "minus_days": sum(x < 0 for x in series),
            "by_month": {k: round(v) for k, v in sorted(by_month.items())},
            "by_reason": dict(Counter(t["reason"] for t in trades))}


def run():
    meta = hist._load(hist._p("candidates.json"))
    if not meta:
        raise SystemExit("candidates.json 없음 — 먼저 fetch 실행")
    days = meta["days"]
    by_day = defaultdict(list)
    for c in meta["cands"]:
        by_day[c["day"]].append(c)
    cache, missing = {}, set()

    def bars(code, day, m):
        k = (code, day, m)
        if k not in cache:
            raw = hist.load_minute(code, day)
            if raw is None:
                missing.add((code, day))
            cache[k] = aggregate(raw or [], m)
        return cache[k]

    variants = grid()
    res, all_trades = {}, []
    for v in variants:
        book = Book(v)
        for d in days:
            dd = datetime.strptime(d, "%Y%m%d").date()
            ctxs = {c["code"]: (c["rank"], c["ctx"]) for c in by_day.get(d, [])}
            codes = set(ctxs) | ({book.pos["code"]} if book.pos else set())
            ev = [(b["t"], ctxs.get(code, (0, None))[0], code, b) for code in codes
                  for b in bars(code, d, v.bar_m)]
            ev.sort(key=lambda e: (e[0], e[1], e[2]))
            for _, _, code, b in ev:
                book.on_bar(code, b, ctxs.get(code, (0, None))[1])
            book.end_of_day(dd)
        res[v.id] = {**metrics(book.trades, days), "open_at_end": bool(book.pos)}
        all_trades.extend(book.trades)
    for v in variants:
        nb = [res[w.id]["net"] for w in neighbors(v, variants)]
        res[v.id]["neighbors"] = {"n": len(nb), "min": min(nb), "mean": round(sum(nb) / len(nb)),
                                  "all_plus": all(x > 0 for x in nb)}
    nets = sorted(r["net"] for r in res.values())
    out = {"made": datetime.now().isoformat(timespec="seconds"),
           "window": [meta["start"], meta["end"]], "trading_days": len(days),
           "funnel": meta["funnel"], "candidates": len(meta["cands"]),
           "minute_missing": sorted(f"{c}_{d}" for c, d in missing),
           "n_variants": len(variants), "approximations": APPROX,
           "settings": {"commission": B.COMMISSION, "slippage": B.SLIPPAGE, "tax": B.TAX,
                        "ma_set": B.MA_SET, "d2_exit": B.D2_EXIT, "bowl": B.BOWL,
                        "entry_bar_stop": B.ENTRY_BAR_STOP, "stop_alt": B.STOP_ALT},
           "summary": {"plus_variants": sum(x > 0 for x in nets), "median_net": nets[len(nets) // 2],
                       "min_net": nets[0], "max_net": nets[-1],
                       "plateau_variants": sorted(k for k, r in res.items()
                                                  if r["net"] > 0 and r["neighbors"]["all_plus"])},
           "variants": res}
    os.makedirs(B.BOT_DIR, exist_ok=True)
    with open(hist._p("backtest_result.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(hist._p("backtest_trades.jsonl"), "w", encoding="utf-8") as f:
        for t in all_trades:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    return out
