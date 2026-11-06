#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/kiwoom_holdings.py   (KIWOOM_HOLDINGS_vNEXT)
# v1.3.6: 신규. 키움 국내주식 보유 종목 읽기 → 미국/한국/중국/일본/머니마켓 분류 → 구글 시트 기록
#        (버전 번호는 승인 때 채움)
# 읽기 전용: 주문·매매·출금 TR 을 부르지 않습니다. 허용 api-id = kt00018, kt00001 뿐 (그 외는 막음)
#  - 키는 /etc/bot-office/kiwoom.json 에만 둡니다 (GitHub 에 절대 올리지 않음)
#    {"appkey": "...", "secretkey": "...", "c40_unit": "만원",
#     "google_sa_path": "/etc/bot-office/google_sa.json"}
#  - 토큰은 만료 120초 전까지 /var/lib/bot-office/kiwoom/kiwoom_token.json 에 두고 재사용
#  - 시트에 쓰는 칸은 '입력정리'!B91:B94 + '입력정리'!C40 뿐 (코드에 고정, 바꿀 수 없음)
# 사용:
#   python3 kiwoom_holdings.py            # dry-run (기본, 시트에 안 씀) — 5줄만 출력
#   python3 kiwoom_holdings.py --write    # 시트에 기록 (타이머가 부르는 것)
#   python3 kiwoom_holdings.py --probe    # 머니마켓 위치 확인용: 종목별 분류 + kt00001 항목 출력
#   python3 kiwoom_holdings.py --ip       # 이 서버 외부 IP (키움 포털 등록 확인용)
# ==========================================================
import argparse, base64, json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

R = Path(os.environ.get("OFFICE_ROOT", "/"))
KEYS = R / "etc/bot-office/kiwoom.json"
TOKEN_CACHE = R / "var/lib/bot-office/kiwoom/kiwoom_token.json"
DEFAULT_SA = R / "etc/bot-office/google_sa.json"
BASE = os.environ.get("KIWOOM_BASE_URL", "https://api.kiwoom.com")
KST = timezone(timedelta(hours=9))

# 읽기 전용 잠금 — 여기 없는 api-id/경로는 부르지 않는다
ALLOWED = {("/api/dostk/acnt", "kt00018"), ("/api/dostk/acnt", "kt00001")}

# 시트 — 쓰는 칸 고정
SHEET_ID = "1ET9YGdqvArmHkKRFXLjsK9YUuQnSlHT74WCQHyao8Cs"
TAB = "입력정리"
RANGE_4 = f"'{TAB}'!B91:B94"     # 미국 / 한국 / 중국 / 일본 (만원, 정수 반올림)
RANGE_MM = f"'{TAB}'!C40"        # 키움 머니마켓
WRITE_RANGES = (RANGE_4, RANGE_MM)
C40_UNITS = {"만원": 10000, "원": 1}

# 분류 규칙 (종목명). 대소문자 무시
ORDER = ("미국", "한국", "중국", "일본")
RULES = {
    "미국": ("미국", "나스닥", "S&P", "다우"),
    "중국": ("중국", "차이나", "CSI", "항셍"),
    "일본": ("일본", "닛케이", "TOPIX"),
}
MM_WORDS = ("머니마켓",)


class KiwoomError(RuntimeError):
    pass


class StopReport(RuntimeError):
    """분류·검산에서 멈춰야 할 때 (시트에 아무것도 쓰지 않음)"""


# ---------------- 공통 HTTP (테스트에서 바꿔 끼움)
def urllib_http(method, url, headers, body, timeout=20):
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            try:
                d = json.loads(raw) if raw else {}
            except ValueError:
                d = {"_raw": raw[:200].decode("utf-8", "replace")}
            return r.status, {k.lower(): v for k, v in r.headers.items()}, d
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            d = json.loads(raw)
        except ValueError:
            d = {"_raw": raw[:200].decode("utf-8", "replace")}
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, d


def external_ip(http=urllib_http):
    """GCP 메타데이터 서버에서 외부 IP. 실패하면 None (외부 사이트는 쓰지 않음)"""
    url = ("http://metadata.google.internal/computeMetadata/v1/instance/"
           "network-interfaces/0/access-configs/0/external-ip")
    try:
        st, _, d = http("GET", url, {"Metadata-Flavor": "Google"}, None, timeout=3)
    except Exception:
        return None
    if st == 200 and isinstance(d, (str, int)):
        return str(d)
    if st == 200 and isinstance(d, dict) and d.get("_raw"):
        return d["_raw"].strip()
    return None


def ip_hint(http=urllib_http):
    ip = external_ip(http)
    where = f"이 서버 외부 IP = {ip}" if ip else "외부 IP 확인 실패 (GCP 콘솔 > VM 인스턴스 > 외부 IP 에서 확인)"
    return (f"\n  → 키움 포털(openapi.kiwoom.com)에 등록된 IP 가 맞는지 확인하세요. {where}"
            "\n  → GCP 는 정지/시작하면 IP 가 바뀔 수 있어, 바뀌었으면 포털에서 다시 등록해야 합니다.")


# ---------------- 숫자
def to_int(v, what):
    """키움 숫자 문자열 ('000000000730000', '-00000000012000', '+000…') → int"""
    if v is None:
        raise KiwoomError(f"{what} 값 없음")
    s = str(v).strip().replace(",", "")
    if s == "":
        raise KiwoomError(f"{what} 값 비어 있음")
    try:
        return int(s)
    except ValueError:
        raise KiwoomError(f"{what} 숫자 아님: {s[:20]}") from None


def man_won(won):
    """원 → 만원 정수 (사사오입, 은행가 반올림 아님)"""
    return int((Decimal(won) / Decimal(10000)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


# ---------------- 키움
class Kiwoom:
    def __init__(self, keys_path=KEYS, token_cache=TOKEN_CACHE, http=urllib_http, now=time.time):
        k = json.loads(Path(keys_path).read_text(encoding="utf-8"))
        self.key, self.secret = str(k["appkey"]).strip(), str(k["secretkey"]).strip()
        self.cfg = k
        self.token_cache = Path(token_cache)
        self.http, self.now = http, now

    def token(self, fresh=False):
        if not fresh:
            try:
                c = json.loads(self.token_cache.read_text())
                if c.get("key") == self.key[:6] and c.get("exp", 0) > self.now() + 120:
                    return c["token"]
            except (OSError, ValueError, KeyError):
                pass
        st, _, d = self.http("POST", BASE + "/oauth2/token",
                             {"content-type": "application/json;charset=UTF-8"},
                             {"grant_type": "client_credentials", "appkey": self.key, "secretkey": self.secret},
                             timeout=15)
        d = d if isinstance(d, dict) else {}
        tok = d.get("token")
        if st != 200 or not tok or str(d.get("return_code", 0)) != "0":
            msg = d.get("return_msg") or d.get("_raw") or ""
            raise KiwoomError(f"토큰 발급 실패 HTTP {st} code={d.get('return_code', '')} {msg}".strip()
                              + ip_hint(self.http))
        exp = self._parse_exp(d.get("expires_dt"))
        self.token_cache.parent.mkdir(parents=True, exist_ok=True)
        self.token_cache.write_text(json.dumps({"token": tok, "exp": exp, "key": self.key[:6]}))
        os.chmod(self.token_cache, 0o600)
        return tok

    def _parse_exp(self, s):
        """expires_dt 'YYYYMMDDHHMMSS' (KST) → epoch. 없거나 이상하면 발급 시각 + 24시간"""
        try:
            return datetime.strptime(str(s), "%Y%m%d%H%M%S").replace(tzinfo=KST).timestamp()
        except (TypeError, ValueError):
            return self.now() + 24 * 3600

    def _call(self, path, api_id, body, cont_key=None, _retry=True):
        if (path, api_id) not in ALLOWED:
            raise KiwoomError(f"읽기 전용 잠금: {api_id} {path} 는 허용되지 않음")
        h = {"content-type": "application/json;charset=UTF-8", "authorization": "Bearer " + self.token(),
             "api-id": api_id}
        if cont_key:
            h["cont-yn"], h["next-key"] = "Y", cont_key
        st, rh, d = self.http("POST", BASE + path, h, body)
        if st == 401 and _retry:
            self.token(fresh=True)
            return self._call(path, api_id, body, cont_key, _retry=False)
        if st == 429 and _retry:
            time.sleep(1.2)
            return self._call(path, api_id, body, cont_key, _retry=False)
        if not isinstance(d, dict):
            raise KiwoomError(f"{api_id} 응답 형식 이상 HTTP {st}")
        code = str(d.get("return_code", ""))
        if st != 200 or code != "0":
            raise KiwoomError(f"{api_id} 실패 HTTP {st} code={code} {d.get('return_msg', '')}".strip()
                              + (ip_hint(self.http) if st in (401, 403) else ""))
        return rh, d

    def holdings(self):
        """kt00018 전체 페이지. (행 목록, tot_evlt_amt 원)"""
        rows, tot, key = [], None, None
        for _ in range(20):
            rh, d = self._call("/api/dostk/acnt", "kt00018", {"qry_tp": "1", "dmst_stex_tp": "KRX"}, key)
            if tot is None:
                tot = to_int(d.get("tot_evlt_amt"), "tot_evlt_amt")
            page = d.get("acnt_evlt_remn_indv_tot")
            if page is None:
                page = []
            if not isinstance(page, list):
                raise KiwoomError("acnt_evlt_remn_indv_tot 형식 확인 필요")
            rows += page
            if str(rh.get("cont-yn", "N")).upper() != "Y" or not rh.get("next-key"):
                break
            key = rh["next-key"]
        else:
            raise KiwoomError("kt00018 연속조회 20쪽 초과 — 응답이 완전하지 않음")
        return rows, tot

    def deposit_detail(self):
        """kt00001 (추정조회 3). --probe 에서만 사용"""
        _, d = self._call("/api/dostk/acnt", "kt00001", {"qry_tp": "3"})
        return d


# ---------------- 분류
def classify_name(name):
    """→ ('머니마켓'|'미국'|'중국'|'일본'|'한국', None) 또는 (None, 이유)"""
    n = (name or "").strip()
    if not n:
        return None, "종목명 없음"
    up = n.upper()
    hits = [c for c, words in RULES.items() if any(w.upper() in up for w in words)]
    mm = any(w in n for w in MM_WORDS)
    if mm and hits:
        return None, f"머니마켓이면서 {'/'.join(hits)} 규칙에도 걸림"
    if mm:
        return "머니마켓", None
    if len(hits) > 1:
        return None, f"규칙 여러 개에 걸림: {'/'.join(hits)}"
    if hits:
        return hits[0], None
    return "한국", None


def summarize(rows, tot_evlt_amt):
    """모든 행을 정확히 한 칸에 넣는다. 못 넣으면 StopReport (목록 포함)"""
    buckets = {c: 0 for c in ORDER}
    mm, detail, bad = 0, [], []
    for r in rows:
        code = str(r.get("stk_cd", "")).strip()
        name = str(r.get("stk_nm", "")).strip()
        try:
            qty = to_int(r.get("rmnd_qty"), f"{code} rmnd_qty")
            amt = to_int(r.get("evlt_amt"), f"{code} evlt_amt")
        except KiwoomError as e:
            bad.append(f"{code} {name}: {e}")
            continue
        cat, why = classify_name(name)
        if cat is None:
            bad.append(f"{code} {name}: {why}")
            continue
        if cat == "머니마켓":
            mm += amt
        else:
            buckets[cat] += amt
        detail.append({"code": code, "name": name, "qty": qty, "amt": amt, "cat": cat})
    if bad:
        raise StopReport("분류할 수 없는 보유 종목이 있어 멈춥니다 (추측해서 넣지 않음):\n  - " + "\n  - ".join(bad))
    total = sum(buckets.values()) + mm
    assert total == sum(x["amt"] for x in detail)   # 한 종목이 두 칸에 들어가지 않았는지
    return {"buckets": buckets, "mm": mm, "total": total, "tot_evlt_amt": tot_evlt_amt, "detail": detail}


def check(s, strict):
    """내부 검산만 (외부 고정 숫자 없음): 종목별 평가금액 합 == 응답 tot_evlt_amt"""
    problems = []
    if s["total"] != s["tot_evlt_amt"]:
        problems.append(f"종목별 평가금액 합 {s['total']:,}원 ≠ 응답 총평가금액(tot_evlt_amt) {s['tot_evlt_amt']:,}원")
    if not any(x["cat"] == "머니마켓" for x in s["detail"]):
        problems.append("kt00018 보유 내역에 이름에 '머니마켓'이 든 종목이 없음 — 머니마켓 위치 미확인 (--probe 로 확인)")
    if problems and strict:
        raise StopReport("검산에서 멈춥니다 (시트에 쓰지 않음):\n  - " + "\n  - ".join(problems))
    return problems


# ---------------- 구글 시트 (서비스 계정, 표준 라이브러리 + openssl)
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
        raise KiwoomError("서비스 계정 서명 실패 (openssl): " + err[:200].decode("utf-8", "replace"))
    return out


def google_token(sa_path, http=urllib_http, now=time.time, signer=rs256_sign):
    sa = json.loads(Path(sa_path).read_text(encoding="utf-8"))
    t = int(now())
    head = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claim = _b64(json.dumps({"iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/spreadsheets",
                             "aud": sa.get("token_uri", "https://oauth2.googleapis.com/token"),
                             "iat": t, "exp": t + 3600}).encode())
    unsigned = f"{head}.{claim}".encode()
    jwt = unsigned.decode() + "." + _b64(signer(sa["private_key"], unsigned))
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                                   "assertion": jwt}).encode()
    st, _, d = http("POST", sa.get("token_uri", "https://oauth2.googleapis.com/token"),
                    {"content-type": "application/x-www-form-urlencoded"}, body)
    if st != 200 or not d.get("access_token"):
        raise KiwoomError(f"구글 토큰 실패 HTTP {st} {d.get('error', '')} {d.get('error_description', '')}".strip())
    return d["access_token"], sa["client_email"]


def build_values(s, c40_unit):
    if c40_unit not in C40_UNITS:
        raise StopReport("C40 단위 미확인: /etc/bot-office/kiwoom.json 에 \"c40_unit\": \"만원\" 또는 \"원\" 을 "
                         "시트에서 확인한 뒤 적어 주세요 (추측해서 쓰지 않음)")
    four = [man_won(s["buckets"][c]) for c in ORDER]
    mm = man_won(s["mm"]) if c40_unit == "만원" else s["mm"]
    return four, mm


def write_sheet(four, mm, sa_path, http=urllib_http, now=time.time, signer=rs256_sign):
    data = [{"range": RANGE_4, "values": [[v] for v in four]}, {"range": RANGE_MM, "values": [[mm]]}]
    assert tuple(x["range"] for x in data) == WRITE_RANGES   # 쓰는 칸 고정
    tok, email = google_token(sa_path, http, now, signer)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate"
    st, _, d = http("POST", url, {"authorization": "Bearer " + tok, "content-type": "application/json"},
                    {"valueInputOption": "RAW", "data": data})
    if st != 200:
        err = d.get("error", {}) if isinstance(d, dict) else {}
        hint = (f"\n  → 시트를 서비스 계정 {email} 에 '편집자'로 공유했는지 확인하세요."
                if st in (403, 404) else "")
        raise KiwoomError(f"시트 쓰기 실패 HTTP {st} {err.get('status', '')} {err.get('message', '')}".strip() + hint)
    return [x.get("updatedRange", "") for x in (d.get("responses") or [])]


# ---------------- 출력
def lines5(four, mm, c40_unit):
    out = [f"{c}: {v:,}만원" for c, v in zip(ORDER, four)]
    out.append(f"키움 머니마켓: {mm:,}{c40_unit}")
    return out


def probe(kw, out=print):
    rows, tot = kw.holdings()
    out(f"[kt00018] 행 {len(rows)}개 · tot_evlt_amt {tot:,}원")
    for r in rows:
        cat, why = classify_name(str(r.get("stk_nm", "")))
        out(f"  {str(r.get('stk_cd', '')):>8}  {str(r.get('stk_nm', ''))[:30]:<30}  "
            f"평가 {str(r.get('evlt_amt', '')).lstrip('0') or '0':>12}  → {cat or '분류불가: ' + why}")
    try:
        d = kw.deposit_detail()
        out("[kt00001 qry_tp=3] 항목 (0 이 아닌 값만, 계좌 관련 항목은 가림):")
        for k in sorted(d):
            v = d[k]
            if isinstance(v, (list, dict)):
                out(f"  {k}: (목록 {len(v)}개)")
                continue
            if "acnt" in k.lower():
                v = "****"
            elif str(v).strip().lstrip("+-0") == "":
                continue
            out(f"  {k}: {v}")
    except KiwoomError as e:
        out(f"[kt00001] 조회 실패: {e}")


def main(argv=None, http=urllib_http, keys_path=KEYS, token_cache=TOKEN_CACHE, out=print):
    ap = argparse.ArgumentParser(description="키움 보유 종목 → 시트 (읽기 전용)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help="시트에 기록 (기본은 dry-run)")
    g.add_argument("--probe", action="store_true", help="머니마켓 위치 확인용 상세 출력")
    g.add_argument("--ip", action="store_true", help="이 서버 외부 IP 출력")
    a = ap.parse_args(argv)
    if a.ip:
        out(external_ip(http) or "외부 IP 확인 실패 (GCP 메타데이터 서버 응답 없음)")
        return 0
    try:
        kw = Kiwoom(keys_path, token_cache, http)
        if a.probe:
            probe(kw, out)
            return 0
        rows, tot = kw.holdings()
        s = summarize(rows, tot)
        problems = check(s, strict=a.write)
        unit = kw.cfg.get("c40_unit")
        if not a.write and unit not in C40_UNITS:
            four = [man_won(s["buckets"][c]) for c in ORDER]
            for ln in lines5(four, man_won(s["mm"]), "만원 (C40 단위 미확인 — 만원으로 표시)"):
                out(ln)
        else:
            four, mm = build_values(s, unit)
            for ln in lines5(four, mm, unit):
                out(ln)
        for p in problems:   # dry-run 에서만 여기까지 옴
            print("경고: " + p, file=sys.stderr)
        if a.write:
            write_sheet(four, mm, kw.cfg.get("google_sa_path") or str(DEFAULT_SA), http)
            out(f"시트 기록 완료 ({datetime.now(KST):%Y-%m-%d %H:%M} KST): {RANGE_4}, {RANGE_MM}")
        return 0
    except StopReport as e:
        print(str(e), file=sys.stderr)
        return 2
    except (KiwoomError, OSError, KeyError, ValueError) as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
