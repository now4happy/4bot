# briefing/portfolio.py — 소스 수집 → 오늘 스냅샷 → 어제와 diff → 버킷 %
# 원칙: 소스는 서로 독립. 실패한 소스는 status=unavailable 로 저장하고 어제 값을 오늘로 이월하지 않는다.
# 버킷 %는 가격·환율과 모든 버킷의 소스가 있어야 분모가 확정된다(Q4·Q5 미확인). 불완전하면 % 는 None('—')이고
# 수량 변동만 보여 준다. portfolio.denominator_complete 는 가격 소스와 금·가상화폐·간접자산·달러 소스가 모두 붙기 전까지 false.
import os
import sys

from . import state as _state
from .sources import acct_fail, kiwoom, meritz, toss

KIWOOM = "키움"


def load_targets(path):
    """portfolio_targets.json (Muse 제공): targets_pct, ticker_to_bucket, kiwoom_default_bucket,
    kiwoom_gold_tickers, confirmed. 없거나 형식이 틀리면 None(= 버킷 표 생략, 수량 변동은 계속)."""
    d = _state.read_json(path, None)
    if not isinstance(d, dict):
        return None
    if not isinstance(d.get("targets_pct"), dict) or not isinstance(d.get("ticker_to_bucket"), dict):
        return None
    d.setdefault("kiwoom_default_bucket", "stock")
    d.setdefault("kiwoom_gold_tickers", [])
    d.setdefault("confirmed", False)
    return d


def fetch_all(cfg, today, st, fetchers=None):
    """(소스별 결과). 어떤 소스가 예외를 던져도 다른 소스는 계속한다."""
    f = fetchers or {}
    out = {}
    for name, default in (("toss", lambda: toss.fetch(cfg)),
                          ("meritz", lambda: meritz.fetch(cfg)),
                          ("kiwoom", lambda: kiwoom.fetch(cfg, today, st))):
        try:
            out[name] = (f.get(name) or default)()
        except Exception as e:
            out[name] = {"status": "unavailable", "meta": {},
                         "accounts": {name: acct_fail("예외: %s" % type(e).__name__)}}
    return out


def build_snapshot(date, generated_at, results, prices):
    accounts, sources = {}, {}
    for name, r in results.items():
        sources[name] = {"status": r.get("status"), "meta": r.get("meta", {})}
        for a, v in r.get("accounts", {}).items():
            accounts[a] = {"source": name, "status": v["status"], "holdings": v["holdings"],
                           "note": v.get("note", "")}
    return {"date": date, "generated_at": generated_at, "sources": sources,
            "accounts": accounts, "prices": prices or {}}


def diff(prev, snap):
    """(changes, incomparable). 키움은 fixed 모드면 비교 안 함(표시에서 따로 안내), api 는 양쪽 모두 api 일 때만 비교."""
    changes, incomparable = [], []
    if not prev:
        return changes, incomparable
    kcur = snap["sources"].get("kiwoom", {}).get("meta", {}).get("mode")
    kprev = prev.get("sources", {}).get("kiwoom", {}).get("meta", {}).get("mode")
    for acct, cur in snap["accounts"].items():
        if cur["source"] == "kiwoom" and kcur != "api":
            continue
        p = prev.get("accounts", {}).get(acct)
        if cur["source"] == "kiwoom" and kprev != "api":
            incomparable.append(acct)
            continue
        if cur["status"] != "ok" or not p or p.get("status") != "ok":
            incomparable.append(acct)
            continue
        for t in sorted(set(cur["holdings"]) | set(p["holdings"])):
            a, b = p["holdings"].get(t, 0.0), cur["holdings"].get(t, 0.0)
            if abs(b - a) > 1e-9:
                changes.append({"account": acct, "ticker": t, "prev_qty": a, "today_qty": b, "delta": b - a})
    return changes, incomparable


def bucket_values(snap, targets, gold_key):
    """({버킷: 평가액}, complete). 가격 없는 티커·매핑 없는 티커·실패 계좌가 있으면 complete=False."""
    vals, complete = {}, True
    prices = snap.get("prices", {})
    gold = set(targets.get("kiwoom_gold_tickers", []))
    for acct, a in snap["accounts"].items():
        if a["status"] != "ok":
            complete = False
            continue
        for t, q in a["holdings"].items():
            if a["source"] == "kiwoom":
                b = gold_key if t in gold else targets.get("kiwoom_default_bucket", "stock")
            else:
                b = targets["ticker_to_bucket"].get(t)
            px = prices.get(t)
            if b is None or px is None:
                complete = False
                continue
            vals[b] = vals.get(b, 0.0) + q * px
    return vals, complete


def pcts(vals, complete, denominator_complete):
    total = sum(vals.values())
    if not (complete and denominator_complete) or total <= 0:
        return None
    return {k: v / total * 100.0 for k, v in vals.items()}


def build_buckets(cfg, targets, snap, prev):
    if targets is None:
        return None, None
    pc = cfg.get("portfolio", {})
    gold_key = pc.get("gold_bucket_key", "gold")
    dc = bool(pc.get("denominator_complete", False))
    today = pcts(*bucket_values(snap, targets, gold_key), dc)
    before = pcts(*bucket_values(prev, targets, gold_key), dc) if prev else None
    thr = pc.get("bucket_highlight_pp")
    rows = []
    for key, target in targets["targets_pct"].items():
        t = today.get(key, 0.0) if today is not None else None
        b = before.get(key, 0.0) if before is not None else None
        d = (t - b) if (t is not None and b is not None) else None
        rows.append({"key": key, "target": target, "prev_pct": b, "today_pct": t, "delta": d,
                     "highlight": bool(thr is not None and d is not None and abs(d) >= thr)})
    note = None
    if today is None:
        note = "버킷 %는 가격·일부 소스 미확인으로 생략"
    return rows, note


def collect(cfg, date, generated_at, prev, results, targets, prices=None):
    """(section, snapshot). section 은 briefing_latest.json 의 portfolio 항목(설계 6절 + 표시용 보조 필드)."""
    snap = build_snapshot(date, generated_at, results, prices)
    first = prev is None
    changes, incomparable = diff(prev, snap)
    buckets, note = build_buckets(cfg, targets, snap, prev)
    km = results.get("kiwoom", {}).get("meta", {})
    recaptured = bool(prev and km.get("fixed_sha") and
                      prev.get("sources", {}).get("kiwoom", {}).get("meta", {}).get("fixed_sha") not in (None, km.get("fixed_sha")))
    srcs = {n: {"status": r.get("status")} for n, r in results.items()}
    srcs["kiwoom"] = {"status": results.get("kiwoom", {}).get("status"), "mode": km.get("mode"),
                      "as_of": km.get("as_of"), "elapsed_days": km.get("elapsed_days")}
    sts = [r.get("status") for r in results.values()]
    if sts and all(s == "unavailable" for s in sts):
        status = "failed"
    elif all(s == "ok" for s in sts) and not incomparable:
        status = "ok"
    else:
        status = "degraded"
    section = {"status": status, "date": date, "prev_date": (prev or {}).get("date"),
               "targets_confirmed": bool(targets.get("confirmed")) if targets else False,
               "sources": srcs, "buckets": buckets, "buckets_note": note,
               "changes": changes, "incomparable": incomparable, "first_snapshot": first,
               "kiwoom": {"mode": km.get("mode"), "as_of": km.get("as_of"), "recaptured": recaptured}}
    return section, snap
