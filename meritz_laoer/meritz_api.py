# ==========================================================
# FILE: meritz_laoer/meritz_api.py   (MERITZ_LAOER v2.0.6)
# v2.0.6 (2026-11-19, 판 8): 버전 표기만 올림 — staging 에 빠진 v2.0.4 파일(notifier·tg_menu·accum_strategy)을 v2.0.5 main·meritz_api 와 한 묶음으로 맞춤 (ImportError 해소). 코드 로직 변경 없음
# v2.0.5 (2026-11-19): fills_rows 가 체결 행 심볼을 ovrs_stck_symb_iscd 가 없으면 iscd 로도 읽음 (실제 체결 내역 응답에는 iscd 만 있음 — Muse 서버 확인). holding()·open_orders_today() 는 그대로
# v2.0.4 (2026-11-19): MeritzError.definite(서버가 오류 코드로 분명히 거절 = True) 구분 · order() 가 네트워크 오류·시간 초과를 '응답 못 받음'(definite=False)으로 바꿔 던짐 ·
#   fills_rows(체결 행 목록, 심볼 있으면 포함) 추가 — fills() 결과는 그대로. 주문 응답을 못 받았을 때 main 이 자동으로 확인하는 데 씀
# 메리츠증권 Open API — 무한매수 봇용 최소 연결 (해외주식 현재가·일봉·잔고·외화예수금·장운영·즉시주문·체결내역)
# v2.0.0 (2026-11-18): 자동환전용 krw_cash(읽기)·fx_exchange(환전 신청 POST, main.auto_fx 에서만 호출) 추가 — 형식은 meritz_dca_bot 과 같음.
#   fx_applied_rate 추가 (읽기 전용: GET /forex/v1/rates/applied, 매수=mnec_clcd '1' 의 tltr_aply_byrt).
#   적립봇의 회차 금액(원→달러) 환산용. 형식은 meritz_dca_bot/meritz_api.py 와 같음. 환전 신청(POST)은 넣지 않음
# v1.0.0 (2026-11-08): 첫 버전. 토큰·호출 부분은 bot_office/meritz_client.py(V1.5) 방식을 따르되 파일을 공유하지 않음
#   - 키 파일 경로는 기본값 없음(설정 key_file 필수) → P·VR6 키(/etc/bot-office/...)를 실수로 읽지 않음
#   - 토큰 캐시도 이 봇 전용 (state_dir/data/meritz_token.json)
#   - 주문: POST /trading/v1/overseas/orders/buy|sell (공식 openapi.json 2026-10-28)
#     LOC = oder_cls_code "32" + 조건 "7" · MOC = "34" + "7"(가격 0) · 지정가 = "01" + "0"
#   - 앱키에 계좌가 묶임(공식 README) → 계좌번호는 요청에 넣지 않음. 계좌 확인은 키 지문으로 함
# ==========================================================
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

BASE = os.environ.get("MERITZ_BASE_URL", "https://openapi.imeritz.com:9443")
OK_CODES = {"0000", "0001", "5620", "5762", "5766", "5820", "5822"}
ORDER_TYPES = {"LOC": ("32", "7"), "MOC": ("34", "7"), "LIMIT": ("01", "0")}


class MeritzError(RuntimeError):
    definite = False          # True: 서버가 오류 코드로 분명히 거절함(주문이 안 들어감). False: 응답을 못 받았거나 불확실(주문이 들어갔을 수도 있음)


class WarnNeeded(MeritzError):
    """증권사 착오 방지 경고 → 사람이 확인해야 함 (자동으로 'Y' 재전송하지 않음)"""
    definite = True           # 경고 응답을 받았으니 주문은 안 들어간 것


def key_fingerprint(path):
    """키 파일의 app_key 지문 (sha256 앞 12자리). 원문은 출력하지 않음"""
    k = json.loads(Path(path).read_text(encoding="utf-8"))
    return hashlib.sha256(str(k["app_key"]).strip().encode()).hexdigest()[:12]


def _mac():
    n = uuid.getnode()
    return "".join(f"{(n >> s) & 0xFF:02X}" for s in range(40, -1, -8))


def _num(v):
    try:
        x = float(str(v if v not in (None, "") else 0).replace(",", ""))
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


class MeritzApi:
    def __init__(self, key_file, token_cache):
        if not key_file:
            raise MeritzError("key_file 설정 없음")
        k = json.loads(Path(key_file).read_text(encoding="utf-8"))
        self.key, self.secret = k["app_key"].strip(), k["app_secret"].strip()
        self.token_cache = Path(token_cache)

    # ---------------- 토큰
    def token(self, fresh=False):
        if not fresh:
            try:
                c = json.loads(self.token_cache.read_text())
                if c.get("key") == hashlib.sha256(self.key.encode()).hexdigest()[:12] and c.get("exp", 0) > time.time() + 120:
                    return c["token"]
            except (OSError, ValueError, KeyError):
                pass
        body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": self.key,
                                       "client_secret": self.secret, "scope": "login"}).encode()
        req = urllib.request.Request(BASE + "/oauth2/token", data=body, method="POST",
                                     headers={"content-type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.load(r)
        except urllib.error.HTTPError as e:
            raise MeritzError(f"토큰 발급 실패 HTTP {e.code}")
        tok, ttl = d["access_token"], int(d.get("expires_in", 43200))
        self.token_cache.parent.mkdir(parents=True, exist_ok=True)
        self.token_cache.write_text(json.dumps({"token": tok, "exp": time.time() + ttl - 60,
                                                "key": hashlib.sha256(self.key.encode()).hexdigest()[:12]}))
        os.chmod(self.token_cache, 0o600)
        return tok

    def _call(self, method, path, query=None, body=None, _retry=True):
        url = BASE + path + ("?" + urllib.parse.urlencode(query) if query else "")
        h = {"authorization": "Bearer " + self.token(), "mac_address": _mac(),
             "content-type": "application/json; charset=utf-8"}
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.load(r)
        except urllib.error.HTTPError as e:   # 메리츠는 오류를 HTTP 500 + 본문으로 보냄
            try:
                d = json.loads(e.read())
            except ValueError:
                raise MeritzError(f"HTTP {e.code} {path}")
        code = str(d.get("rsp_cd", ""))
        if code in ("EGW00121", "EGW00123") and _retry:      # 토큰 만료
            self.token(fresh=True)
            return self._call(method, path, query, body, _retry=False)
        if code == "EGW00200" and _retry:                    # 초당 한도
            time.sleep(1.2)
            return self._call(method, path, query, body, _retry=False)
        if code not in OK_CODES:
            msg = " — ".join(x for x in (d.get("rsp_msg"), d.get("rsp_sub_msg")) if x)
            e = MeritzError(f"{code} {msg}".strip())
            e.definite = True
            raise e
        return d

    # ---------------- 조회 (읽기 전용)
    def price(self, symbol, mrkt_cls_code):
        d = self._call("GET", "/market/v1/overseas/prices",
                       {"mrkt_div_code": "OV", "mrkt_cls_code": mrkt_cls_code, "iscd": symbol, "dely_rltm_cls_code": "0"})
        data = d.get("data") or {}
        if not data.get("prpr"):
            raise MeritzError(f"{symbol} 시세 없음 (거래소 {mrkt_cls_code} 확인 필요)")
        return {"price": _num(data["prpr"]), "prev_close": _num(data.get("prdy_clpr"))}

    def daily_closes(self, symbol, mrkt_cls_code):
        """최신 일봉 [(YYYYMMDD, 종가)] 최신순 (최대 40건)"""
        d = self._call("GET", "/market/v1/overseas/candles/days",
                       {"mrkt_div_code": "OV", "mrkt_cls_code": mrkt_cls_code, "iscd": symbol,
                        "dely_rltm_cls_code": "0", "mod_stpr_cls_code": "0"})
        rows = d.get("data") or []
        out = [(str(r.get("date")), _num(r.get("prpr"))) for r in rows if isinstance(r, dict) and _num(r.get("prpr")) > 0]
        return sorted(out, key=lambda x: x[0], reverse=True)

    def holding(self, symbol):
        """(보유수량, 매도가능수량, 거래소벤더번호). 없으면 (0, 0, None). 평단은 일부러 돌려주지 않음(입고 평단 안 씀)"""
        q = {}
        for _ in range(10):
            d = self._call("GET", "/accounts/v1/me/overseas/holdings", q or None)
            for r in d.get("data") or []:
                sym = str(r.get("ovrs_stck_symb_iscd") or "").strip().upper()
                if sym == symbol.upper():
                    return int(_num(r.get("rmnd_dqty"))), int(_num(r.get("seln_able_dqty"))), (r.get("ovrs_exch_vndr_idno") or None)
            if d.get("tr_cont") != "1" or not d.get("tr_cont_key"):
                break
            q = {"tr_cont": "1", "tr_cont_key": d["tr_cont_key"]}
        return 0, 0, None

    def usd_cash(self):
        """USD 예수금(frcr_amt)만. 평가액·추정예수금으로 대신하지 않음"""
        d = self._call("GET", "/accounts/v1/me/overseas/currencies")
        if d.get("tr_cont") == "1":
            raise MeritzError("외화잔고 응답이 완전하지 않음")
        rows = d.get("data")
        if not isinstance(rows, list):
            raise MeritzError("외화잔고 형식 확인 필요")
        usd = [r for r in rows if isinstance(r, dict) and str(r.get("crcd", "")).strip().upper() == "USD"]
        if len(usd) != 1 or usd[0].get("frcr_amt") in (None, ""):
            raise MeritzError("USD 예수금 행 없음 또는 중복")
        return _num(usd[0]["frcr_amt"])

    def fx_applied(self):
        """메리츠 환전 적용환율 (원화→달러 매수 기준) → (원/달러, 기준시각 exrt_stnd_time). 읽기 전용. 못 읽으면 MeritzError"""
        d = self._call("GET", "/forex/v1/rates/applied", {"crcd": "USD", "mnec_clcd": "1"})
        data = d.get("data") or {}
        rate = _num(data.get("tltr_aply_byrt"))
        if rate <= 0:
            raise MeritzError("적용환율 없음 또는 0 이하")
        return rate, data.get("exrt_stnd_time")

    def fx_applied_rate(self):
        return self.fx_applied()[0]

    def krw_cash(self):
        """원화 예수금 (GET /accounts/v1/me/deposit 의 tfam) — 환전 가능 여부 확인용. 읽기 전용. meritz_dca_bot 과 같은 호출"""
        d = self._call("GET", "/accounts/v1/me/deposit")
        data = d.get("data")
        if not isinstance(data, dict) or data.get("tfam") in (None, ""):
            raise MeritzError("KRW 예수금 확인 필요")
        v = _num(data["tfam"])
        if v < 0:
            raise MeritzError("KRW 예수금 숫자 확인 필요")
        return v

    def fx_exchange(self, frcr_amt, iqry_exrt, exrt_stnd_time):
        """실시간 환전신청 원화→달러 (실제 돈 이동 — main.auto_fx 의 안전장치를 모두 통과했을 때만 호출).
        POST /forex/v1/exchanges. 호출 형식·성공 코드는 meritz_dca_bot/meritz_api.py 와 같음(스펙상 frcr_amt 는 string —
        서버 수용 여부는 실환전 전까지 미확인이며 실환전 테스트로 확인하지 않음)"""
        body = {"mnec_clcd": "1", "crcd": "USD", "frcr_amt": str(frcr_amt),
                "wncr_amt": 0, "exrt_stnd_time": exrt_stnd_time, "iqry_exrt": str(iqry_exrt)}
        d = self._call("POST", "/forex/v1/exchanges", body=body)
        if str(d.get("rsp_cd")) != "0000":
            raise MeritzError("환전 성공 코드 불일치")
        return d.get("data") or {}

    def us_market_status(self):
        """미국 장운영 상태 코드 ("004" = 정규장 개시)"""
        d = self._call("GET", "/reference/v1/overseas/market-hours", {"ovrs_stck_mrkt_tr_cls_code": "01"})
        data = d.get("data")
        if isinstance(data, list):
            data = next((x for x in data if isinstance(x, dict) and str(x.get("ovrs_stck_mrkt_tr_cls_code")) == "01"), {})
        return str((data or {}).get("ovrs_mkop_cls_code", ""))

    def open_orders_today(self, symbol):
        """당일 미체결 주문 (이 계좌 전체 중 해당 심볼)"""
        d = self._call("GET", "/trading/v1/overseas/orders/today", {"cntg_cls_code": "2", "seln_byov_clcd": "0"})
        return [r for r in (d.get("data") or []) if isinstance(r, dict)
                and str(r.get("ovrs_stck_symb_iscd", "")).upper() == symbol.upper() and _num(r.get("ncnt_qty")) > 0]

    def fills_rows(self, date_from, date_to):
        """기간 체결 내역 [{"no", "side", "qty", "amt", "sym"}] (주문번호별 합산). sym 은 ovrs_stck_symb_iscd 가 있으면 그것, 없으면 iscd (체결 내역 응답은 iscd 만 있음). 둘 다 없으면 빈 문자열"""
        out, q = {}, {"oder_sta_date": date_from, "oder_fin_date": date_to, "cntg_cls_code": "1", "seln_byov_clcd": "0"}
        for _ in range(20):
            d = self._call("GET", "/trading/v1/overseas/orders/history", q)
            for r in d.get("data") or []:
                if not isinstance(r, dict):
                    continue
                no = str(r.get("oder_no", "")).strip()
                qty = int(_num(r.get("cntg_dqty")))
                amt = _num(r.get("cntg_camt")) or qty * _num(r.get("cntg_crnc_prc"))
                if no and qty > 0:
                    side = "SELL" if str(r.get("seln_byov_clcd")) == "1" else "BUY"
                    row = out.setdefault(no, {"no": no, "side": side, "qty": 0, "amt": 0.0,
                                              "sym": str(r.get("ovrs_stck_symb_iscd") or r.get("iscd") or "").strip().upper()})
                    row["qty"] += qty
                    row["amt"] += amt
            if d.get("tr_cont") != "1" or not d.get("tr_cont_key"):
                break
            q = dict(q, tr_cont="1", tr_cont_key=d["tr_cont_key"])
        return list(out.values())

    def fills(self, date_from, date_to):
        """기간 체결 내역 {주문번호: (매수/매도, 체결수량, 체결금액)}"""
        return {r["no"]: (r["side"], r["qty"], r["amt"]) for r in self.fills_rows(date_from, date_to)}

    # ---------------- 주문 (실제 돈이 움직임 — main.py 의 안전장치를 모두 통과했을 때만 호출)
    def order(self, side, symbol, exch_id, otype, qty, price):
        if otype not in ORDER_TYPES:
            raise MeritzError(f"지원 안 하는 주문 유형 {otype}")
        cls, cond = ORDER_TYPES[otype]
        px = "0" if otype == "MOC" else f"{float(price):.4f}".rstrip("0").rstrip(".")
        body = {"ovrs_stck_symb_iscd": symbol, "ovrs_exch_vndr_idno": exch_id, "oder_cls_code": cls,
                "oder_cond_cls_code": cond, "odqt": int(qty), "ovrs_stck_oder_prc": px}
        path = f"/trading/v1/overseas/orders/{'buy' if side == 'BUY' else 'sell'}"
        try:
            d = self._call("POST", path, body=body)
        except MeritzError:
            raise
        except Exception as e:      # 시간 초과·연결 끊김·알 수 없는 응답: 주문이 들어갔는지 모름 → 불확실로 표시 (main 이 자동 확인)
            raise MeritzError(f"주문 응답을 못 받음 ({type(e).__name__}) — 주문이 들어갔는지 불확실")
        data = d.get("data") or {}
        warn = str(data.get("warn_cls_code", "0")).strip()
        if warn and warn != "0":
            raise WarnNeeded(str(data.get("warn_msg") or f"경고코드 {warn}"))
        return {"no": str(data.get("oder_no", "")), "body": body}
