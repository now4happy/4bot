#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/asset_board.py   (사무실 v1.3.7)
# v1.4.4: 자산 구성(mix)을 포트폴리오 버킷 6개로 — 금·가상화폐·달러·단기채·간접자산·주식·전환 대기 현금
#        (시트 '입력정리'!A103:B109 '포트폴리오 자산 구성' 블록을 읽음 · 기존 A83:B87 4개 항목 블록은 안 읽음)
#        amt 는 이제 '전환 대기 현금' 항목에만 저장 (이름 변경 · 천만 단위 표기는 보드 그대로)
#        HIDE_BELOW mix 1.0 → 0.0: 금 0.8%·가상화폐 0.1% 같은 작은 버킷도 도넛·목록에 보임
#        (버전 번호는 승인 때 채움)
#        (2) 투자 종목(stock) 항목마다 증권사별 구간 segments=[{"broker","val"(만원)}] 저장 — E열 구성 칸
#            E27:E30·E34:E35·E37:E38 을 추가로 읽음 (기존 범위 그대로) · val 0 구간은 뺌 · pct 는 지금처럼 B열 기준
#            미국·한국·중국·일본관련주 = 키움(B열 값 그대로 1구간) · SOXL = 한투 E28 + 메리츠 E29 + 토스 E34
#            TQQQ = 한투 E27 + 메리츠 E30 · 토스 해외주식 = 토스 E35 · 코인 = 빗썸 E37+E38 (1구간)
#            E칸이 숫자가 아니면 그 항목만 segments 없음 (보드는 한 색으로 그림 · 오류 아님)
# v1.4.2: 수익률 추가 — 월별 표 '입력정리'!A67:H78 에서 B(총자산)가 있는 마지막 월의 월 수익률(D)·1년 수익률(H)만 %로 저장
#        (returns = {month, monthly, yearly} · 총자산 금액은 저장 안 함 · 표가 비었거나 D·H가 비면 returns 없음, 오류 아님)
# v1.3.8: 자산 구성(mix) 도넛에서만 비율 1% 미만 항목 숨김 (합계·다른 항목 % 그대로) · mix 기본 이름 '간접자산'
# v1.3.7: 신규. 상황판 '자산 현황' 도넛 2개용 자료를 구글 시트에서 읽어 비율(%)만 저장
#        (버전 번호는 승인 때 채움)
# 읽기 전용: 시트 '읽기' 권한(spreadsheets.readonly)만 요청. 시트에 쓰지 않음.
#  - 비밀값(새로 필요 · 사용자 승인·작업): 구글 서비스 계정 키 /etc/bot-office/google_sa.json (root 전용)
#    시트 "26년 계획"을 그 서비스 계정 이메일에 '보기' 권한으로 공유해야 읽힘. 파일이 없으면 '자료 없음'/오래된 값으로만 표시
#  - 독립 파일: 서명(openssl)·HTTP 부품을 이 파일 안에 둠 (kiwoom_holdings.py 를 쓰지 않음)
#  - 이름: A열 글자에서 앞에 붙은 '42.7% ' 같은 퍼센트를 떼고 씀 (보드가 계산한 % 와 이중 표시 방지)
#  - 읽는 칸 (코드에 고정): '입력정리'!A14:Z14 (기준일), A103:B109 (포트폴리오 자산 구성), A91:B99 (투자 종목), A67:H78 (월별 수익률)
#                          + v1.4.3: E27:E30, E34:E35, E37:E38 (투자 종목 증권사별 구성)
#  - 저장: /var/lib/bot-office/assets/assets.json (0644) — 이름·비율(%)·기준일·가져온 시각·수익률(%)만.
#          금액·계좌번호·토큰·주소는 저장하지 않음. 예외(v1.4.3): 현금 amt 1개 · stock segments 의 증권사별 val(만원)만. 웹서버(office_board.py)는 이 파일만 읽음.
#  - 시트에 못 닿으면 이전 자료를 그대로 두고 error·tried 만 갱신 → 상황판은 '오래된 값'으로 표시
# 사용:
#   python3 asset_board.py            # dry-run (기본, 파일 안 씀) — 이름·비율만 출력
#   python3 asset_board.py --write    # 파일에 기록 (타이머 bot-office-assets.timer 가 부르는 것)
#   python3 asset_board.py --probe    # 시트에서 읽은 이름 칸·기준일 칸만 출력 (금액 출력 안 함)
# ==========================================================
import argparse, base64, json, math, os, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

R = Path(os.environ.get("OFFICE_ROOT", "/"))
SA_FILE = R / "etc/bot-office/google_sa.json"
OUT = R / "var/lib/bot-office/assets/assets.json"
KST = timezone(timedelta(hours=9))
SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"

SHEET_ID = "1ET9YGdqvArmHkKRFXLjsK9YUuQnSlHT74WCQHyao8Cs"
TAB = "입력정리"
DATE_RANGE = f"'{TAB}'!A14:Z14"
# (키, 제목, 범위(이름 A열 + 값 B열, 마지막 줄 = 합계), 이름 칸이 비었을 때 쓸 이름)
CHARTS = (
    ("mix", "자산 구성", f"'{TAB}'!A103:B109", ("금", "가상화폐", "달러·단기채", "간접자산", "주식", "전환 대기 현금")),
    ("stock", "투자 종목", f"'{TAB}'!A91:B99",
     ("미국", "한국관련주", "중국관련주", "일본관련주", "SOXL", "TQQQ", "토스 해외주식", "코인")),
)
HIDE_BELOW = {"mix": 0.0}   # v1.4.4: 포트폴리오 버킷은 1% 미만도 그림에 보임 (금·가상화폐 포함) · stock 은 숨기지 않음
# 월별 표 (2026-01~12): A=월 B=총자산(만원) C=전월 차액 D=월 수익률 E=연초 대비 F=연초 수익률 G=전년 동월 H=1년 수익률
RETURNS_RANGE = f"'{TAB}'!A67:H78"
RETURNS_YEAR = 2026        # A열 글자에서 월을 못 읽을 때만 '행 순서 = 1~12월'로 씀
# v1.4.3: 투자 종목 증권사별 구성 칸 (E열) · 행 번호 → 범위 안 위치
SEG_RANGES = (f"'{TAB}'!E27:E30", f"'{TAB}'!E34:E35", f"'{TAB}'!E37:E38")
SEG_ROWS = {27: (0, 0), 28: (0, 1), 29: (0, 2), 30: (0, 3), 34: (1, 0), 35: (1, 1), 37: (2, 0), 38: (2, 1)}
KIWOOM = "키움"
# stock 항목 순서(B91~B98)별 구간: (증권사, [E열 행]) · None = 키움 (B열 값 그대로 1구간)
STOCK_SEGS = (None, None, None, None,
              (("한투", (28,)), ("메리츠", (29,)), ("토스", (34,))),   # SOXL
              (("한투", (27,)), ("메리츠", (30,))),                    # TQQQ
              (("토스", (35,)),),                                      # 토스 해외주식
              (("빗썸", (37, 38)),))                                   # 코인 (BTC+ETH)
AMT_NAMES = {"mix": ("전환 대기 현금",)}   # 차트별: 금액(amt)을 저장하는 항목 이름 — 전환 대기 현금만
READ_RANGES = (DATE_RANGE,) + tuple(c[2] for c in CHARTS) + SEG_RANGES + (RETURNS_RANGE,)
TOTAL_TOL = 0.005          # 항목 합 vs 시트 합계 차이 허용 (0.5%)
PCT_PREFIX = re.compile(r"^\s*[-+]?\d+(?:[.,]\d+)?\s*%\s*")   # A열 '42.7% 현금' 의 앞 퍼센트
MONTH_RE = re.compile(r"(20\d\d)\s*[./\-년]\s*(\d{1,2})")
DATE_RE = re.compile(r"(20\d\d)\s*[./\-년]\s*(\d{1,2})\s*[./\-월]\s*(\d{1,2})")


class SheetError(RuntimeError):
    pass


# ---------------- HTTP · 서명 (표준 라이브러리 + openssl, 이 파일 안에서만)
def urllib_http(method, url, headers, body, timeout=20):
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, st, hd = r.read(), r.status, r.headers
    except urllib.error.HTTPError as e:
        raw, st, hd = e.read(), e.code, e.headers
    try:
        d = json.loads(raw) if raw else {}
    except ValueError:
        d = {"_raw": raw[:200].decode("utf-8", "replace")}
    return st, {k.lower(): v for k, v in (hd or {}).items()}, d


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def rs256_sign(private_key_pem, data):
    """openssl 로 RS256 서명. 비밀키는 파이프로만 넘김 (디스크에 임시파일 안 만듦)"""
    rfd, wfd = os.pipe()
    try:
        p = subprocess.Popen(["openssl", "dgst", "-sha256", "-sign", f"/dev/fd/{rfd}"],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             pass_fds=(rfd,))
        os.close(rfd)
        rfd = None
        with os.fdopen(wfd, "wb") as w:
            wfd = None
            w.write(private_key_pem.encode())
        out, err = p.communicate(data, timeout=15)
    finally:
        for fd in (rfd, wfd):
            if fd is not None:
                os.close(fd)
    if p.returncode != 0 or not out:
        raise SheetError("서비스 계정 서명 실패 (openssl)")
    return out


# ---------------- 시트 읽기
def google_token(path, http, now=time.time, signer=None):
    signer = signer or rs256_sign
    if not Path(path).is_file():
        raise SheetError(f"서비스 계정 키 없음: {path} (설치 필요 · VERIFY.md 참고)")
    sa = json.loads(Path(path).read_text(encoding="utf-8"))
    t = int(now())
    uri = sa.get("token_uri", "https://oauth2.googleapis.com/token")
    head = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claim = _b64(json.dumps({"iss": sa["client_email"], "scope": SCOPE, "aud": uri,
                             "iat": t, "exp": t + 3600}).encode())
    unsigned = f"{head}.{claim}".encode()
    jwt = unsigned.decode() + "." + _b64(signer(sa["private_key"], unsigned))
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                   "assertion": jwt}).encode()
    st, _, d = http("POST", uri, {"content-type": "application/x-www-form-urlencoded"}, body)
    if st != 200 or not d.get("access_token"):
        raise SheetError(f"구글 토큰 실패 HTTP {st} {d.get('error', '')}".strip())
    return d["access_token"], sa["client_email"]


def read_sheet(http, path=None, now=time.time, signer=None):
    """→ {범위: [[칸, 칸], ...]} (숫자는 숫자 그대로, 날짜는 보이는 글자로)"""
    tok, email = google_token(path or SA_FILE, http, now, signer)
    q = [("ranges", r) for r in READ_RANGES] + [("valueRenderOption", "UNFORMATTED_VALUE"),
                                                 ("dateTimeRenderOption", "FORMATTED_STRING")]
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchGet?"
           + urllib.parse.urlencode(q))
    st, _, d = http("GET", url, {"authorization": "Bearer " + tok}, None)
    if st != 200:
        err = d.get("error", {}) if isinstance(d, dict) else {}
        hint = f" (시트를 {email} 에 공유했는지 확인)" if st in (403, 404) else ""
        raise SheetError(f"시트 읽기 실패 HTTP {st} {err.get('status', '')}".strip() + hint)
    vr = d.get("valueRanges") or []
    if len(vr) != len(READ_RANGES):
        raise SheetError(f"시트 응답 범위 수 이상 ({len(vr)}/{len(READ_RANGES)})")
    return {rng: (v.get("values") or []) for rng, v in zip(READ_RANGES, vr)}


# ---------------- 계산 (금액은 여기서 비율로 바꾸고 버림)
def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"[,\s₩원만]", "", str(v or ""))
    try:
        return float(s) if s else 0.0
    except ValueError:
        return None


def base_date(row_values):
    for row in row_values:
        for cell in row:
            m = DATE_RE.search(str(cell))
            if m:
                y, mo, d = (int(x) for x in m.groups())
                if 1 <= mo <= 12 and 1 <= d <= 31:
                    return f"{y}.{mo}.{d}"
    return ""


def amt10(v):
    """만원 → ÷10 반올림(0.5 는 올림) 정수 · 예: 23481 → 2348"""
    return int(math.floor(v / 10 + 0.5))


def segments(seg_values, idx, b_val):
    """stock 항목 idx 의 증권사별 구간 [{"broker","val"}] · val 0 구간 뺌 · E칸이 숫자가 아니면 None"""
    spec = STOCK_SEGS[idx] if idx < len(STOCK_SEGS) else None
    if spec is None:
        return [{"broker": KIWOOM, "val": round(b_val, 1)}] if b_val > 0 else None
    out = []
    for broker, rows in spec:
        tot = 0.0
        for row in rows:
            ri, pos = SEG_ROWS[row]
            rng = list(seg_values[ri]) if ri < len(seg_values) else []
            cell = (list(rng[pos]) if pos < len(rng) else []) + [""]
            v = _num(cell[0])
            if v is None or v < 0:
                return None
            tot += v
        if tot > 0:
            out.append({"broker": broker, "val": round(tot, 1)})
    return out or None


def chart(rows, defaults, hide_below=0.0, amt_names=(), seg_values=None):
    """rows = A·B 열 (항목 n줄 + 합계 1줄) → {"items":[{"name","pct"}], "check":"ok|diff|no_total", "zero":[...]}
    hide_below: pct(전체 합 대비, 소수 첫째 자리 반올림) < hide_below 인 항목은 items 에서만 뺌 (pct == hide_below 는 보임)
    amt_names: 이 이름 항목에만 "amt"(만원 ÷ 10 반올림 정수) 추가 (v1.4.4 · mix 의 전환 대기 현금만)
    seg_values: 주면 각 항목에 증권사별 "segments" 추가 (v1.4.3 · stock 만, E열 구성 칸 값)"""
    n = len(defaults)
    rows = list(rows) + [[]] * (n + 1 - len(rows))
    names, vals = [], []
    for i in range(n):
        r = list(rows[i]) + ["", ""]
        name = PCT_PREFIX.sub("", r[0]).strip() if isinstance(r[0], str) else ""
        names.append(name[:20] or defaults[i])
        v = _num(r[1])
        if v is None:
            raise SheetError(f"{names[-1]} 값이 숫자가 아님")
        vals.append(v)
    if any(v < 0 for v in vals):
        raise SheetError("음수 값이 있음")
    s = sum(vals)
    if s <= 0:
        raise SheetError("항목 합이 0")
    tot = _num((list(rows[n]) + ["", ""])[1])
    check = "no_total" if not tot else ("ok" if abs(tot - s) <= abs(tot) * TOTAL_TOL else "diff")
    items = []
    for k, (nm, v) in enumerate(zip(names, vals)):
        if v <= 0:
            continue
        it = {"name": nm, "pct": round(v * 100 / s, 1)}
        if nm in amt_names:
            it["amt"] = amt10(v)
        if seg_values is not None:
            sg = segments(seg_values, k, v)
            if sg:
                it["segments"] = sg
        items.append(it)
    items = [i for i in items if i["pct"] >= hide_below]
    return {"items": items, "check": check, "zero": [nm for nm, v in zip(names, vals) if v <= 0]}


def _ratio(v):
    """수익률 칸 → % (소수 -0.0773 → -7.7). 빈칸·글자는 None. '-7.7%' 처럼 글자로 오면 그대로 %"""
    if v is None or isinstance(v, bool) or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, str) and v.strip().endswith("%"):
        n = _num(v.strip()[:-1])
        return None if n is None else round(n, 1) + 0.0
    n = _num(v)
    return None if n is None else round(n * 100, 1) + 0.0     # + 0.0: -0.0 → 0.0


def returns(rows):
    """월별 표 → {"month":"2026-11","monthly":-7.7,"yearly":0.5} · B(총자산)가 있는 마지막 행 기준 · 없으면 None"""
    last = None
    for i, r in enumerate(rows[:12]):
        r = list(r) + [""] * 8
        b = _num(r[1]) if not (isinstance(r[1], str) and not r[1].strip()) else None
        if b:                                   # 빈칸·0·글자는 '아직 없는 달'
            last = (i, r)
    if last is None:
        return None
    i, r = last
    m = MONTH_RE.search(str(r[0]))
    month = f"{int(m.group(1))}-{int(m.group(2)):02d}" if m and 1 <= int(m.group(2)) <= 12 else f"{RETURNS_YEAR}-{i + 1:02d}"
    mo, yr = _ratio(r[3]), _ratio(r[7])
    if mo is None or yr is None:
        return None
    return {"month": month, "monthly": mo, "yearly": yr}


def build(values):
    out = {"base_date": base_date(values.get(DATE_RANGE, [])), "charts": [], "errors": []}
    ret = returns(values.get(RETURNS_RANGE, []))
    if ret:
        out["returns"] = ret
    for key, title, rng, defaults in CHARTS:
        try:
            segv = [values.get(r, []) for r in SEG_RANGES] if key == "stock" else None
            c = chart(values.get(rng, []), defaults, HIDE_BELOW.get(key, 0.0), AMT_NAMES.get(key, ()), segv)
            c.update(key=key, title=title)
            out["charts"].append(c)
        except SheetError as e:
            out["errors"].append(f"{title}: {e}")
    return out


# ---------------- 저장 (마지막 성공 값 유지)
def now_kst(now=time.time):
    return datetime.fromtimestamp(now(), KST).strftime("%Y-%m-%d %H:%M")


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def update(http, out_path=OUT, now=time.time, signer=None, sa=None):
    """시트 읽기 → 성공한 도넛만 바꾸고, 실패하면 이전 값 + error 기록. 반환: 저장한 dict"""
    try:
        prev = json.loads(Path(out_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prev = {}
    rec = {"version": "v1.4.4", "tried_kst": now_kst(now), "error": "",
           "fetched_kst": prev.get("fetched_kst", ""), "base_date": prev.get("base_date", ""),
           "charts": prev.get("charts", [])}
    if prev.get("returns"):
        rec["returns"] = prev["returns"]          # 시트 못 읽으면 이전 수익률 유지
    try:
        b = build(read_sheet(http, sa, now, signer))
    except Exception as e:   # 연결·토큰·응답 문제 → 이전 값 유지
        rec["error"] = (str(e) if isinstance(e, SheetError) else f"{type(e).__name__}")[:160]
        return rec
    old = {c.get("key"): c for c in rec["charts"]}
    for c in b["charts"]:
        old[c["key"]] = c
    rec["charts"] = [old[k] for k, *_ in CHARTS if k in old]
    if b.get("returns"):
        rec["returns"] = b["returns"]
    else:
        rec.pop("returns", None)                  # 시트는 읽었는데 월별 표가 비었음 → 보드에서 안 보임
    if b["charts"]:
        rec["fetched_kst"] = rec["tried_kst"]
        rec["base_date"] = b["base_date"] or rec["base_date"]
    rec["error"] = "; ".join(b["errors"])[:160]
    return rec


def returns_line(r):
    if not r:
        return "수익률: 없음 (월별 표에 총자산이 있는 달이 없거나 수익률 칸이 비어 있음)"
    sg = lambda v: ("+" if v > 0 else "") + f"{v:.1f}%"
    return f"수익률 월 {sg(r['monthly'])} · 수익률 년 {sg(r['yearly'])} ({r['month']})"


def main(argv=None, http=None, out=print):
    ap = argparse.ArgumentParser(description="상황판 자산 현황 자료 (시트 읽기 전용)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help="assets.json 에 기록 (기본은 dry-run)")
    g.add_argument("--probe", action="store_true", help="이름 칸·기준일만 출력 (금액 출력 안 함)")
    a = ap.parse_args(argv)
    http = http or urllib_http
    if a.probe:
        v = read_sheet(http)
        out("기준일 줄(14행)에서 찾은 날짜: " + (base_date(v[DATE_RANGE]) or "못 찾음"))
        for key, title, rng, defaults in CHARTS:
            rows = v.get(rng, [])
            out(f"[{title}] {rng}")
            for i, d in enumerate(defaults + ("(합계)",)):
                cell = (list(rows[i]) if i < len(rows) else []) + [""]
                a_txt = cell[0] if isinstance(cell[0], str) else "(숫자/빈칸)"
                out(f"  {i + 1}줄  A열 이름 칸: {a_txt or '(빈칸)'}  → 보드 이름: {PCT_PREFIX.sub('', a_txt).strip() or d}")
        return 0
    if a.write:
        rec = update(http)
        save(OUT, rec)
    else:
        rec = update(http, out_path=OUT)
    out(f"기준일 {rec['base_date'] or '?'} · 가져온 시각 {rec['fetched_kst'] or '-'} KST"
        + (f" · 오류: {rec['error']}" if rec["error"] else ""))
    for c in rec["charts"]:
        out(f"[{c['title']}] " + ", ".join(f"{i['pct']}% {i['name']}" for i in c["items"])
            + ("" if c["check"] == "ok" else f"  (합계 확인: {c['check']})"))
    out(returns_line(rec.get("returns")))
    out("(dry-run: 파일 안 씀)" if not a.write else f"저장: {OUT}")
    return 0 if not rec["error"] else 1


if __name__ == "__main__":
    sys.exit(main())
