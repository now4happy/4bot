"""과거 자료 받기·읽기 (조회 전용). 수집기의 REST 클라이언트·키 읽기·저장 방식을 그대로 쓴다.

BOT_DIR/universe.json, daily/<코드>.json, minute/<코드>_<YYYYMMDD>.json, candidates.json
"""
import json
import os
from datetime import datetime

from hk_collector import config as C
from hk_collector.bars import num
from hk_collector.rest import Rest, load_keys
from hk_collector.store import Store

from . import config as B
from .strategy import day_ctx

C.ALLOWED_TR.update(B.EXTRA_QUERY_TR)   # 조회 TR만 추가


def make_rest():
    appkey, secret, _ = load_keys(C.KEY_FILE)
    store = Store(os.path.join(B.BOT_DIR, "raw"))
    return Rest(store, appkey, secret), store


def _p(*a):
    return os.path.join(B.BOT_DIR, *a)


def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(path + ".tmp", path)


def _load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _rows(pages, key):
    out = []
    for code, text in pages:
        if code == 0:
            out.extend(json.loads(text).get(key) or [])
    return out


def parse_daily(rows):
    out = {}
    for r in rows:
        o, h, l, c = (num(r.get(k)) for k in ("open_pric", "high_pric", "low_pric", "cur_prc"))
        if r.get("dt") and None not in (o, h, l, c):
            out[r["dt"]] = {"dt": r["dt"], "o": o, "h": h, "l": l, "c": c,
                            "v": num(r.get("trde_qty")) or 0, "val": num(r.get("trde_prica")) or 0}
    return [out[k] for k in sorted(out)]


def parse_minute(rows):
    """cntr_tm을 봉 시작 시각으로 본다 (시작/끝 어느 쪽인지 미확인)."""
    out = {}
    for r in rows:
        o, h, l, c = (num(r.get(k)) for k in ("open_pric", "high_pric", "low_pric", "cur_prc"))
        tm = str(r.get("cntr_tm", ""))
        if len(tm) == 14 and None not in (o, h, l, c):
            out[tm] = {"t": tm, "o": o, "h": h, "l": l, "c": c, "v": num(r.get("trde_qty")) or 0}
    return [out[k] for k in sorted(out)]


def fetch_universe(rest):
    lists = {mk: _rows(rest.call("ka10099", {"mrkt_tp": mk}, max_pages=20), "list")
             for mk in ("0", "10", "8", "60")}
    excl = {r.get("code") for mk in ("8", "60") for r in lists[mk]}
    uni = {}
    for mk in ("0", "10"):
        for r in lists[mk]:
            code, name = r.get("code"), r.get("name", "")
            if not code or code in excl or "스팩" in name:   # 스팩은 이름으로 거름 (근사)
                continue
            if r.get("orderWarning") not in (None, "", "0"):
                continue   # Q6 결정 (2026-11-16): 투자유의 종목 제외 (정리매매·단기과열·투자위험·투자경과)
            if name.endswith("우") or "우B" in name:
                continue   # Q6 결정: 우선주 제외 (이름 기준, 근사)
            uni[code] = {"name": name, "shares": num(r.get("listCount")), "market": mk}
    if uni:
        _save(_p("universe.json"), {"asof": datetime.now(C.KST).strftime("%Y%m%d"), "codes": uni})
    return uni


def load_universe():
    return (_load(_p("universe.json")) or {}).get("codes", {})


def fetch_daily_one(rest, code, base_dt):
    rows = parse_daily(_rows(rest.call("ka10081", {"stk_cd": code, "base_dt": base_dt,
                                                    "upd_stkpc_tp": "1"},
                                       max_pages=B.DAILY_PAGES), "stk_dt_pole_chart_qry"))
    if rows:
        _save(_p("daily", code + ".json"), {"base_dt": base_dt, "rows": rows})
    return rows


def fetch_daily(rest, codes, base_dt):
    n = 0
    for code in codes:
        if (_load(_p("daily", code + ".json")) or {}).get("base_dt") == base_dt:
            continue                                 # 이어받기
        n += bool(fetch_daily_one(rest, code, base_dt))
    return n


def load_daily(code):
    return (_load(_p("daily", code + ".json")) or {}).get("rows", [])


def find_candidates(start, end):
    """가격 조건(전고점 돌파 + D 최소 상승률 도달) + 정배열 + 거래대금 순위(근사)로 D 후보를 만든다.

    근사: 과거 장중 순위는 복원할 수 없어 '그날 일봉 거래대금 순위'를 쓴다 (미래 정보 포함).
    """
    uni = load_universe()
    daily = {c: load_daily(c) for c in uni}
    days = sorted({r["dt"] for rows in daily.values() for r in rows if start <= r["dt"] <= end})
    idx = {c: {r["dt"]: i for i, r in enumerate(rows)} for c, rows in daily.items()}
    cands, funnel = [], {"price": 0, "ma": 0, "rank": 0}
    for d in days:
        today = []
        for c, rows in daily.items():
            i = idx[c].get(d)
            if i:
                chg = (rows[i]["c"] / rows[i - 1]["c"] - 1) * 100 if rows[i - 1]["c"] else 0.0
                today.append((rows[i]["val"], c, i, chg))
        today.sort(reverse=True)
        rank = {c: n + 1 for n, (_, c, _, _) in enumerate(today)}
        lead15 = any(chg >= B.THEME_MIN_FLU for _, _, _, chg in today[:B.RANK_LIMITS[0]])
        limit = B.RANK_LIMITS[0] if lead15 else B.RANK_LIMITS[1]
        for _, c, i, chg in today:
            ctx = day_ctx(daily[c][:i], uni[c].get("shares"))
            if not ctx or daily[c][i]["h"] <= ctx["level"]:
                continue
            funnel["price"] += 1
            if not ctx["ma_ok"]:
                continue
            funnel["ma"] += 1
            if rank[c] > limit:
                continue
            funnel["rank"] += 1
            nxt = [r["dt"] for r in daily[c][i:i + 3]]
            cands.append({"code": c, "day": d, "rank": rank[c], "flu": round(chg, 2),
                          "hold_days": nxt, "ctx": {**ctx, "eligible": True, "rank": rank[c]}})
    _save(_p("candidates.json"), {"start": start, "end": end, "days": days, "funnel": funnel,
                                  "cands": cands})
    return cands


def fetch_minutes(rest, cands):
    """후보 종목의 D~D+2 1분봉. 쪽수 상한 안에서 못 닿으면 그날은 비게 된다 (제공 기간 미확인)."""
    got = miss = 0
    for cd in cands:
        need = [d for d in cd["hold_days"] if not os.path.exists(_p("minute", f"{cd['code']}_{d}.json"))]
        if not need:
            continue
        rows = parse_minute(_rows(rest.call("ka10080", {"stk_cd": cd["code"], "tic_scope": "1",
                                                        "upd_stkpc_tp": "1", "base_dt": need[-1]},
                                            max_pages=B.MINUTE_PAGES), "stk_min_pole_chart_qry"))
        for d in need:
            day_rows = [r for r in rows if r["t"][:8] == d]
            whole = day_rows and (rows[0]["t"] < day_rows[0]["t"] or day_rows[0]["t"][8:12] <= "0901")
            if whole:
                _save(_p("minute", f"{cd['code']}_{d}.json"), day_rows)
                got += 1
            else:
                miss += 1
    return got, miss


def load_minute(code, day):
    rows = _load(_p("minute", f"{code}_{day}.json"))
    if rows is None:
        return None
    return [{**r, "t": datetime.strptime(r["t"], "%Y%m%d%H%M%S")} for r in rows]


def fetch_all(days):
    rest, store = make_rest()
    today = datetime.now(C.KST).strftime("%Y%m%d")
    uni = fetch_universe(rest)
    n = fetch_daily(rest, sorted(uni), today)
    dates = sorted({r["dt"] for c in uni for r in load_daily(c)})
    if not dates:
        store.close()
        return {"universe": len(uni), "daily_fetched": n, "error": "일봉 없음"}
    window = dates[-days:]
    cands = find_candidates(window[0], window[-1])
    got, miss = fetch_minutes(rest, cands)
    store.close()
    return {"universe": len(uni), "daily_fetched": n, "window": [window[0], window[-1]],
            "candidates": len(cands), "minute_days_saved": got, "minute_days_missing": miss,
            "rest_codes": dict(rest.codes)}
