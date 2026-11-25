# briefing/need_table.py — need.json 읽기 → 재발행 규칙 → 계좌 행 계산
# need.json 구조 (Q1·Q16, Muse 서버 확인, 키만):
#   ok(bool), as_of_kst(str), accounts[{name, lines[{label?, currency, holding|null, need|null, sufficient, auto_fx}]}],
#   total_need_usd, total_need_krw.  skipped 키는 v1.0.3 적용 전이라 아직 없음 → 있을 때/없을 때 둘 다 처리.
#   계좌 name: "토스"·"메리츠"·"한투"·"빗썸". line.label: 바벨 씨드="바벨 씨드", 메리츠 "P"·"VR6"·"3번"(=메리츠 4번).
#   토스 본 USD·KRW line, 한투 lines, 빗썸 line 은 label 없음. "메리츠 SOXL 3번" 은 need.json 에 없다 → settings.json 에서 만든다(Q17).
import json
import re
import time

from . import state as _state

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def load_need(path):
    """(data, err). 파일 없음·읽기 실패·JSON 깨짐·구조 이상은 err 문자열."""
    try:
        with open(_state.expand(path), "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None, "파일 없음"
    except (OSError, ValueError) as e:
        return None, "읽기 실패/JSON 깨짐: %s" % type(e).__name__
    err = validate_need(data)
    if err:
        return None, err
    return data, None


def validate_need(data):
    """구조 검사. 이상 없으면 None, 있으면 이유 문자열. (재발행 stdout JSON 을 쓰기 전에도 같은 검사를 쓴다, Q21)"""
    if not isinstance(data, dict) or not isinstance(data.get("accounts"), list):
        return "구조 이상(accounts 없음)"
    for a in data["accounts"]:
        if not isinstance(a, dict) or not isinstance(a.get("lines"), list):
            return "구조 이상(lines 없음)"
        for ln in a["lines"]:
            if not isinstance(ln, dict):
                return "구조 이상(line 형식)"
    return None


def as_of_date(data):
    m = _DATE_RE.search(str((data or {}).get("as_of_kst", "")))
    return m.group(1) if m else None


def is_stale(data, today_kst):
    d = as_of_date(data)
    return d != today_kst  # 날짜를 못 읽어도 stale 로 본다


def has_null_holding(data):
    for a in data.get("accounts", []):
        for ln in a.get("lines", []):
            if ln.get("holding") is None:
                return True
    return False


def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _line_label(ln):
    """Q16: line 의 label 키만 본다 (바벨 씨드·메리츠 P·VR6·3번). label 없는 line 은 빈 문자열."""
    v = ln.get("label")
    return str(v) if v is not None else ""


def classify(acct_name, line_label, rules):
    """(계좌 name, line label) → 규칙. 규칙: {"account": 정규식, "line": 정규식(선택), "label": 표시 이름, "kind": ...}.
    맞는 규칙이 없으면 표시 이름 = 계좌 name (+ line label 이 있으면 ' label'), kind=normal."""
    for r in rules:
        try:
            if not re.search(r.get("account", ""), acct_name or ""):
                continue
            if r.get("line") is not None and not re.search(r["line"], line_label or ""):
                continue
            return r
        except re.error:
            continue
    base = acct_name or "?"
    return {"label": ("%s %s" % (base, line_label)).strip() if line_label else base, "kind": "normal"}


def read_soxl3_seed(seed_cfg):
    """속쓸 봇 설정(Q17: /etc/meritz-laoer/settings.json)에서 전체 시드와 당일 시드를 만든다.
    당일 시드 = total_krw / split_count. 파일을 못 읽거나 키·값이 이상하면 None(= 확인 불가)."""
    if not seed_cfg or not seed_cfg.get("path"):
        return None
    d = _state.read_json(seed_cfg["path"], None)
    if not isinstance(d, dict):
        return None
    t = _num(d.get(seed_cfg.get("total_key") or ""))
    n = _num(d.get(seed_cfg.get("split_key") or ""))
    if t is None or n is None or n <= 0:
        return None
    return {"total": t, "day": t / n}


# need 를 아예 계산하지 않는 줄 (need.json 에서 need=None 인 채로 나옴). 부족 판단에 안 쓰이는 잔고 표시용 줄이라
# 부족 목록에도 안 나오고 완충 판정도 막지 않는다 (3차 rev1). 서버 config.json 은 업데이터가 못 올리니 기본값을 코드에 둔다.
#   한투 KRW: office_briefing.need_data 가 need=None 고정.  토스 KRW: 마스터 계좌가 아니면 need=None.
# config.json need.untracked 가 있으면 그 목록으로 바꾼다. need 가 숫자인 줄은 이 목록에 있어도 일반 줄 (부족 계산 그대로).
DEFAULT_UNTRACKED = [{"account": "^한투$", "currency": "KRW"}, {"account": "^토스$", "currency": "KRW"}]


def is_untracked(acct_name, currency, rules):
    for r in rules or []:
        try:
            if re.search(r.get("account", ""), acct_name or "") and (r.get("currency") in (None, currency)):
                return True
        except re.error:
            continue
    return False


def _line_row(label, kind, ln):
    cur = ln.get("currency") or "USD"
    need = _num(ln.get("need"))
    hold = _num(ln.get("holding"))
    row = {"label": label, "kind": kind, "currency": cur, "need": need, "holding": hold,
           "shortage": None, "status": "ok", "auto_fx": ln.get("auto_fx"),
           "sufficient": ln.get("sufficient"), "notes": []}
    if hold is None:
        row["status"] = "unavailable"          # 부족액·보유 둘 다 '확인 불가'
    elif need is None:
        row["status"] = "need_null"            # Q7: 부족액 '계산 불가'
    else:
        row["shortage"] = max(need - hold, 0.0)
    return row


def build_rows(data, ncfg, seed_reader=read_soxl3_seed):
    rules = ncfg.get("account_rules", [])
    barbell_re = ncfg.get("barbell_match", "바벨 씨드")
    rows, totals = [], {}
    last_meritz = -1
    for acct in data.get("accounts", []):
        aname = acct.get("name") or "?"
        barbell = [ln for ln in acct["lines"] if barbell_re and re.search(barbell_re, _line_label(ln))]
        main = [ln for ln in acct["lines"] if ln not in barbell]
        # 바벨 씨드: 토스 계좌 안의 label="바벨 씨드" line. 합계에 넣지 않고 둘째 줄 '참고'로만.
        bref = None
        if barbell:
            br = _line_row(aname, "barbell", barbell[0])
            bref = {"shortage": br["shortage"], "need": br["need"], "currency": br["currency"],
                    "status": br["status"]}
        for i, ln in enumerate(main):
            rule = classify(aname, _line_label(ln), rules)
            kind = rule.get("kind", "normal")
            row = _line_row(rule.get("label") or aname, kind, ln)
            if row["need"] is None and is_untracked(aname, row["currency"], ncfg.get("untracked", DEFAULT_UNTRACKED)):
                row["untracked"] = True          # need 가 없는 줄: 완충·부족 판정 제외 (holding 이 null 이어도)
            skipped = ln.get("skipped", acct.get("skipped"))
            if kind == "meritz4" and isinstance(skipped, list) and skipped:
                row["skipped"] = [str(x) for x in skipped]
            if i == 0 and bref is not None:
                row["barbell_ref"] = bref
            rows.append(row)
            if aname.startswith("메리츠"):
                last_meritz = len(rows) - 1
            if row["shortage"] is not None and row["shortage"] > 0:
                totals[row["currency"]] = totals.get(row["currency"], 0.0) + row["shortage"]
        if not main and bref is not None:
            # 바벨 줄만 있는 계좌: 일반 행으로 만들지 않고 참고만 별도 행(부족액 '—')
            rows.append({"label": aname, "kind": "barbell_only", "currency": bref["currency"],
                         "need": None, "holding": None, "shortage": None, "status": "na",
                         "barbell_ref": bref, "notes": []})
    # 메리츠 SOXL 3번: need.json 에 line 이 없다(Q16) → 속쓸 봇 설정(Q17)에서 만든다. 부족액 합계에는 넣지 않는다.
    seed = seed_reader(ncfg.get("soxl3_seed"))
    soxl = {"label": ncfg.get("soxl3_label", "메리츠 SOXL 3번"), "kind": "soxl3", "currency": "KRW",
            "need": None, "holding": None, "shortage": None, "soxl": seed, "auto_fx": None,
            "sufficient": None, "notes": [], "status": "ok" if seed else "unavailable"}
    rows.insert(last_meritz + 1 if last_meritz >= 0 else len(rows), soxl)
    return rows, totals


def collect(cfg, today_kst, need_path, reissue_fn, sleep=time.sleep, dry=False,
            seed_reader=read_soxl3_seed):
    """필요 달러 표 데이터를 만든다.
    재발행 규칙(설계 7절): need.json 없음/깨짐/stale/holding null 이면 1회 재발행 → (선택 대기) → 재독.
    재발행은 호출자가 넘긴 reissue_fn() 만 쓴다 ((ok, msg) 반환). 실제 구현은 run.reissue_cmd: --print stdout JSON 을 검증해\n    need.json 에 직접 쓴다(Q21, 텔레그램 중복 없음)."""
    wait = cfg.get("reissue", {}).get("wait_sec", 20)
    notes = []
    data, err = load_need(need_path)
    stale0 = (data is not None) and is_stale(data, today_kst)
    null0 = (data is not None) and has_null_holding(data)
    reissued, reissue_ok = False, None
    if err or stale0 or null0:
        reissued = True
        if dry:
            notes.append("dry: 재발행 건너뜀")
            reissue_ok = None
        else:
            reissue_ok, msg = reissue_fn()
            if reissue_ok:
                if wait and wait > 0:
                    sleep(wait)      # Q21: 재발행이 동기식(stdout→파일 쓰기)이라 기본 0초. 설정으로만 켠다.
                d2, e2 = load_need(need_path)
                if d2 is not None:
                    data, err = d2, None
                elif data is None:
                    err = e2
            else:
                notes.append("재발행 실패: %s" % msg)   # 기존 파일로 진행, 반복 안 함
    if data is None:
        return {"status": "failed", "error": err or "알 수 없음", "as_of": None, "stale": None,
                "reissued": reissued, "reissue_ok": reissue_ok, "null_cause": None,
                "rows": [], "totals": {}, "notes": notes}
    stale = is_stale(data, today_kst)
    rows, totals = build_rows(data, cfg.get("need", {}), seed_reader)
    unavailable = any(r["status"] == "unavailable" for r in rows)
    if data.get("ok") is False:
        notes.append("need.json ok=false")
    status = "ok"
    if unavailable or stale or data.get("ok") is False or (reissued and reissue_ok is False):
        status = "degraded"
    return {"status": status, "error": None, "as_of": data.get("as_of_kst"), "stale": stale,
            "reissued": reissued, "reissue_ok": reissue_ok,
            "null_cause": bool(null0), "rows": rows, "totals": totals, "notes": notes,
            "unavailable": unavailable}
