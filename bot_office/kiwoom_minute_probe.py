#!/usr/bin/env python3
"""키움 REST API 과거 분봉 수집 (시세 조회 전용, 표준 라이브러리만 사용).

호출하는 주소는 두 개뿐이다: 토큰 발급(/oauth2/token), 차트 조회(/api/dostk/chart, ka10080).
주문·계좌 API 는 없고, 그 밖의 주소는 코드에서 막는다.
앱키·시크릿키는 환경변수에서 읽거나 화면에 안 보이게 입력받으며, 출력·저장하지 않는다.
"""
import argparse
import csv
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://api.kiwoom.com"
TOKEN_PATH, CHART_PATH = "/oauth2/token", "/api/dostk/chart"
ALLOWED_PATHS = (TOKEN_PATH, CHART_PATH)
API_ID = "ka10080"
LIST_KEY = "stk_min_pole_chart_qry"
FIELDS = ("cntr_tm", "open_pric", "high_pric", "low_pric", "cur_prc", "trde_qty")
HEADER = ("time", "open", "high", "low", "close", "volume")


class Stop(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None          # 다른 주소로 인증정보가 넘어가지 않게 이동을 따라가지 않음


def http_post(path, body, headers):
    """→ (응답 JSON, 응답 헤더 dict(소문자 키))"""
    if path not in ALLOWED_PATHS:
        raise Stop(f"허용하지 않는 주소: {path}")
    if path == CHART_PATH and headers.get("api-id") != API_ID:
        raise Stop("허용하지 않는 api-id")
    # 키움 앞단 방화벽이 파이썬 기본 User-Agent를 막아 400 "Request Blocked"를 돌려준다 (2026-11-27 서버에서 직접 확인). 브라우저 UA를 보낸다.
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json;charset=UTF-8",
                                          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                                          **headers})
    with urllib.request.build_opener(_NoRedirect).open(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8")), {k.lower(): v for k, v in r.headers.items()}


def get_token(post, appkey, secret):
    data, _ = post(TOKEN_PATH, {"grant_type": "client_credentials", "appkey": appkey, "secretkey": secret}, {})
    tok = data.get("token")
    if not tok:
        raise Stop(f"토큰 발급 실패: return_code={data.get('return_code')} {data.get('return_msg')}")
    return tok


def to_row(item):
    """가격의 +/- 부호(전일 대비 표시)는 떼고 숫자로. 읽을 수 없으면 None"""
    try:
        t = str(item["cntr_tm"]).strip()
        if len(t) != 14 or not t.isdigit():
            return None
        o, h, l, c = (abs(float(str(item[k]).replace(",", ""))) for k in FIELDS[1:5])
        v = abs(float(str(item["trde_qty"]).replace(",", "")))
    except (KeyError, ValueError):
        return None
    if min(o, h, l, c) <= 0 or h < max(o, c) or l > min(o, c):
        return None
    return (t, o, h, l, c, v)


def fetch(post, token, code, scope, until="", max_pages=3000, sleep=time.sleep, delay=1.2, log=print):
    """최신 → 과거로 연속조회. → (rows {time: row}, 정보). 중간에 멈춰도 그때까지 받은 것을 돌려준다"""
    rows, bad, pages, fails = {}, 0, 0, 0
    cont, nkey, oldest, why = "N", "", "", "max_pages"
    seen_keys = set()
    while pages < max_pages:
        headers = {"authorization": f"Bearer {token}", "api-id": API_ID, "cont-yn": cont, "next-key": nkey}
        try:
            data, rh = post(CHART_PATH, {"stk_cd": code, "tic_scope": scope, "upd_stkpc_tp": "1"}, headers)
            if str(data.get("return_code", 0)) != "0":
                raise ValueError(f"return_code={data.get('return_code')} {data.get('return_msg')}")
        except KeyboardInterrupt:
            why = "interrupted"
            break
        except (urllib.error.URLError, ValueError, TimeoutError, ConnectionError) as e:
            fails += 1
            log(f"  조회 실패 {fails}/3: {e}")
            if fails >= 3:
                why = "error"
                break
            sleep(delay * 5 * fails)
            continue
        fails, pages = 0, pages + 1
        got = []
        for item in data.get(LIST_KEY) or []:
            r = to_row(item)
            if r is None:
                bad += 1
            else:
                got.append(r)
        if not got:
            why = "no_rows"
            break
        for r in got:
            rows[r[0]] = r
        new_oldest = min(rows)
        if new_oldest == oldest:
            why = "not_advancing"
            break
        oldest = new_oldest
        if pages % 20 == 0:
            log(f"  {pages}쪽, 가장 오래된 시각 {oldest}")
        if until and oldest[:8] <= until:
            why = "reached_until"
            break
        cont, nkey = rh.get("cont-yn", "N"), rh.get("next-key", "")
        if cont != "Y" or not nkey:
            why = "server_end"
            break
        if nkey in seen_keys:
            why = "repeated_key"
            break
        seen_keys.add(nkey)
        sleep(delay)
    return rows, {"pages": pages, "bad_rows": bad, "stop": why}


def save(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows[k] for k in sorted(rows))
    os.replace(tmp, path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="키움 과거 분봉 수집 (시세 조회 전용)")
    ap.add_argument("--codes", default="005930,000660,229200,132030")
    ap.add_argument("--scope", default="1", choices=["1", "3", "5", "10", "15", "30", "45", "60"])
    ap.add_argument("--until", default="", help="YYYYMMDD. 이 날짜까지 받으면 멈춤 (비우면 서버가 주는 끝까지)")
    ap.add_argument("--max-pages", type=int, default=3000)
    ap.add_argument("--out", default="kiwoom_minute")
    a = ap.parse_args(argv)
    appkey = os.environ.get("KIWOOM_APPKEY") or getpass.getpass("앱키(화면에 안 보임): ")
    secret = os.environ.get("KIWOOM_SECRETKEY") or getpass.getpass("시크릿키(화면에 안 보임): ")
    os.makedirs(a.out, exist_ok=True)
    try:
        token = get_token(http_post, appkey.strip(), secret.strip())
    except (Stop, urllib.error.URLError, ValueError) as e:
        print(f"중단: {e}")
        return 1
    summary = []
    for code in [c.strip() for c in a.codes.split(",") if c.strip()]:
        print(f"[{code}] {a.scope}분봉 조회 시작")
        rows, info = fetch(http_post, token, code, a.scope, a.until, a.max_pages)
        if rows:
            save(os.path.join(a.out, f"{code}_{a.scope}m.csv"), rows)
        line = {"code": code, "scope_min": a.scope, "rows": len(rows), "days": len({k[:8] for k in rows}),
                "oldest": min(rows) if rows else "", "newest": max(rows) if rows else "", **info}
        summary.append(line)
        print("  " + json.dumps(line, ensure_ascii=False))
        if info["stop"] in ("error", "interrupted"):
            break
        time.sleep(1.2)
    with open(os.path.join(a.out, f"summary_{a.scope}m.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return 1 if any(x["stop"] in ("error", "interrupted") for x in summary) else 0


if __name__ == "__main__":
    sys.exit(main())
