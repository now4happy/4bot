#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/meritz_client.py   (MERITZ_CLIENT_V1.1)
# V1.1: 예약주문 발주 시간 선택 (장개시 0 / 장마감 10분 전 1 / 장마감 30분 전 2 / 장개시 30분 후 3)
# 메리츠증권 Open API 최소 연결 (해외주식: 현재가·잔고·예약주문)
#  - 키는 /etc/bot-office/meritz.json 에만 둡니다 (GitHub 에 절대 올리지 않음)
#    {"app_key": "...", "app_secret": "..."}
#  - 토큰은 만료 전까지 /var/lib/bot-office/fanding/meritz_token.json 에 두고 재사용
# ==========================================================
import json, os, time, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path

R = Path(os.environ.get("OFFICE_ROOT", "/"))
KEYS = R / "etc/bot-office/meritz.json"
TOKEN_CACHE = R / "var/lib/bot-office/fanding/meritz_token.json"
BASE = os.environ.get("MERITZ_BASE_URL", "https://openapi.imeritz.com:9443")
OK_CODES = {"0000", "0001", "5620", "5762", "5766", "5820", "5822"}


class MeritzError(RuntimeError):
    pass


def _mac():
    n = uuid.getnode()
    return "".join(f"{(n >> s) & 0xFF:02X}" for s in range(40, -1, -8))


class Meritz:
    def __init__(self, keys_path=KEYS):
        k = json.loads(Path(keys_path).read_text(encoding="utf-8"))
        self.key, self.secret = k["app_key"].strip(), k["app_secret"].strip()

    # ---------------- 토큰
    def token(self, fresh=False):
        if not fresh:
            try:
                c = json.loads(TOKEN_CACHE.read_text())
                if c.get("key") == self.key[:6] and c.get("exp", 0) > time.time() + 120:
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
            raise MeritzError(f"토큰 발급 실패 HTTP {e.code}: {e.read()[:200].decode('utf-8', 'replace')}")
        tok, ttl = d["access_token"], int(d.get("expires_in", 43200))
        TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE.write_text(json.dumps({"token": tok, "exp": time.time() + ttl - 60, "key": self.key[:6]}))
        os.chmod(TOKEN_CACHE, 0o600)
        return tok

    # ---------------- 호출
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
            raise MeritzError(f"{code} {msg}".strip())
        return d

    # ---------------- 조회
    def price(self, symbol, mrkt_cls_code):
        d = self._call("GET", "/market/v1/overseas/prices",
                       {"mrkt_div_code": "OV", "mrkt_cls_code": mrkt_cls_code, "iscd": symbol, "dely_rltm_cls_code": "0"})
        data = d.get("data") or {}
        if not data.get("prpr"):
            raise MeritzError(f"{symbol} 시세 없음 (거래소 {mrkt_cls_code} 확인 필요)")
        return {"price": float(data["prpr"]), "prev_close": float(data.get("prdy_clpr") or 0), "raw": data}

    def holdings(self):
        rows, q = [], {}
        for _ in range(10):
            d = self._call("GET", "/accounts/v1/me/overseas/holdings", q or None)
            rows += d.get("data") or []
            if d.get("tr_cont") != "1" or not d.get("tr_cont_key"):
                break
            q = {"tr_cont": "1", "tr_cont_key": d["tr_cont_key"]}
        return rows

    def holding(self, symbol):
        """(보유수량, 매도가능수량, 거래소벤더번호, 평단). 없으면 (0, 0, None, None)"""
        for r in self.holdings():
            sym = str(r.get("ovrs_stck_symb_iscd") or r.get("iscd") or "").strip().upper()
            if sym == symbol.upper():
                f = lambda k: float(r.get(k) or 0)
                return int(f("rmnd_dqty")), int(f("seln_able_dqty")), (r.get("ovrs_exch_vndr_idno") or None), f("avrg_unpr")
        return 0, 0, None, None

    def exchanges(self):
        return self._call("GET", "/reference/v1/overseas/exchanges").get("data") or []

    def market_hours(self):
        return self._call("GET", "/reference/v1/overseas/market-hours", {"ovrs_stck_mrkt_tr_cls_code": "01"}).get("data") or {}

    # ---------------- 예약주문 (Limit VWAP, 장개시 발주)
    def reserve(self, side, symbol, exch_id, qty, price, date_us, aspr="8", confirm_warn=False, hour_code="2"):
        """예약주문 접수. 증권사 착오매매 경고가 오면 WarnNeeded 를 올림 (자동으로 '확인' 하지 않음)"""
        body = {"ovrs_stck_symb_iscd": symbol, "ovrs_exch_vndr_idno": exch_id, "rsev_aspr_tpcd": aspr,
                "odqt": str(int(qty)), "ovrs_stck_oder_prc": f"{price:.4f}".rstrip("0").rstrip("."),
                "warn_cnfr_yn": "Y" if confirm_warn else "N", "oder_rsev_cls_code": "1",
                "oder_rsev_hour_clcd": str(hour_code), "oder_sta_date": date_us, "oder_fin_date": date_us}
        path = f"/trading/v1/overseas/reserved-orders/{'buy' if side == 'buy' else 'sell'}"
        d = self._call("POST", path, body=body)
        data = d.get("data") or {}
        warn = str(data.get("warn_cls_code", "0")).strip()
        if warn and warn != "0":
            raise WarnNeeded(str(data.get("warn_msg") or f"경고코드 {warn}"))
        return {"no": data.get("oder_rsev_mst_no"), "msg": d.get("rsp_msg", ""), "body": body}

    def reserve_cancel(self, date_kst, no):
        return self._call("POST", "/trading/v1/overseas/reserved-orders/cancel",
                          body={"oder_rsev_mst_date": date_kst, "oder_rsev_mst_no": no})


class WarnNeeded(MeritzError):
    """증권사가 '주문 착오 방지' 경고를 보냄 → 사람이 확인해야 함"""
