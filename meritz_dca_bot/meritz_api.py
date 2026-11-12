# ==========================================================
# FILE: meritz_dca_bot/meritz_api.py   (MERITZ_DCA v1.0.1)
# 메리츠증권 Open API — 메리츠 적립 봇(meritz_dca)용. 3번 toss_api.py 자리를 대신함 (미국주식만)
# v1.0.0 (2026-11-08): 첫 버전.
#   - 토큰·호출(_call)은 meritz_laoer/meritz_api.py(v1.0.0) 방식 그대로. 파일은 공유하지 않음(이 폴더 전용 복사)
#   - 키 파일 경로 기본값 없음(설정 key_file 필수). 토큰 캐시도 이 봇 전용(state_dir/meritz_token.json)
#   - 주문: POST /trading/v1/overseas/orders/buy|sell, 시장가 oder_cls_code "05" + 조건 "0" + 가격 "0"
#     (공식 openapi.json 2026-10-28). 수량은 정수 주만 보냄 (금액 주문·소수 주문 안 씀)
#   - usd_cash_or_zero(): 외화 잔고에 USD 행이 아예 없으면(달러가 한 번도 안 들어온 계좌) 0.0 — 멈추지 않음
#   - 평단은 증권사 값을 쓰지 않음 (봇 장부가 기준). holding_row()는 새 종목 등록 때 참고용으로만 평단을 줌
#   - MeritzDcaClient: 3번 엔진이 부르던 이름(get_current_price·get_symbol_holdings·get_buying_power…)을
#     메리츠 호출로 바꿔 주는 비동기 어댑터 (호출은 스레드로)
# ==========================================================
import asyncio
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = os.environ.get("MERITZ_BASE_URL", "https://openapi.imeritz.com:9443")
OK_CODES = {"0000", "0001", "5620", "5762", "5766", "5820", "5822"}
EST_TZ = ZoneInfo("America/New_York")
PRICE_MARKETS = ("OQ", "NY", "AX")                      # 미국 시세 거래소 구분 (나스닥·뉴욕·아멕스/아카)
VENDOR_FALLBACK = {"OQ": "0537", "NY": "0321", "AX": "0066"}   # 공식 명세 예시값 (거래소 조회가 실패할 때만)


class MeritzError(RuntimeError):
    pass


class WarnNeeded(MeritzError):
    """증권사 착오 방지 경고 → 사람이 확인해야 함 (자동으로 'Y' 재전송하지 않음)"""


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
    """동기 REST 호출 (읽기 + 시장가 주문)."""

    def __init__(self, key_file, token_cache):
        if not key_file:
            raise MeritzError("key_file 설정 없음")
        k = json.loads(Path(key_file).read_text(encoding="utf-8"))
        self.key, self.secret = k["app_key"].strip(), k["app_secret"].strip()
        self.token_cache = Path(token_cache)

    # ---------------- 토큰
    def token(self, fresh=False):
        kfp = hashlib.sha256(self.key.encode()).hexdigest()[:12]
        if not fresh:
            try:
                c = json.loads(self.token_cache.read_text())
                if c.get("key") == kfp and c.get("exp", 0) > time.time() + 120:
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
        self.token_cache.write_text(json.dumps({"token": tok, "exp": time.time() + ttl - 60, "key": kfp}))
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
        if code == "EGW00200" and _retry and method == "GET":   # 초당 한도 (주문은 다시 보내지 않음)
            time.sleep(1.2)
            return self._call(method, path, query, body, _retry=False)
        if code not in OK_CODES:
            msg = " — ".join(x for x in (d.get("rsp_msg"), d.get("rsp_sub_msg")) if x)
            raise MeritzError(f"API {code} {msg}".strip())
        return d

    # ---------------- 조회 (읽기 전용)
    def price(self, symbol, mrkt_cls_code):
        d = self._call("GET", "/market/v1/overseas/prices",
                       {"mrkt_div_code": "OV", "mrkt_cls_code": mrkt_cls_code, "iscd": symbol, "dely_rltm_cls_code": "0"})
        data = d.get("data") or {}
        if not data.get("prpr"):
            raise MeritzError(f"{symbol} 시세 없음 (거래소 {mrkt_cls_code})")
        return {"price": _num(data["prpr"]), "prev_close": _num(data.get("prdy_clpr")),
                "name": str(data.get("kor_isnm") or data.get("eng_isnm") or symbol).strip(),
                "currency": str(data.get("crnc_code") or "USD").upper(),
                "status": str(data.get("issu_stat_cls_code") or ""), "sell_only": str(data.get("sell_only") or "")}

    def daily_closes(self, symbol, mrkt_cls_code, date_from=None, date_to=None):
        """일봉 [(YYYYMMDD, 종가)] 오름차순. from/to 를 주면 그 기간 전부, 안 주면 최신 40건"""
        q = {"mrkt_div_code": "OV", "mrkt_cls_code": mrkt_cls_code, "iscd": symbol,
             "dely_rltm_cls_code": "0", "mod_stpr_cls_code": "0"}
        if date_from and date_to:
            q.update({"from": date_from, "to": date_to})
        d = self._call("GET", "/market/v1/overseas/candles/days", q)
        rows = d.get("data") or []
        out = {str(r.get("date")): _num(r.get("prpr")) for r in rows if isinstance(r, dict) and _num(r.get("prpr")) > 0}
        return sorted(out.items())

    def holdings(self):
        rows, q = [], {}
        for _ in range(10):
            d = self._call("GET", "/accounts/v1/me/overseas/holdings", q or None)
            rows += [r for r in (d.get("data") or []) if isinstance(r, dict)]
            if d.get("tr_cont") != "1" or not d.get("tr_cont_key"):
                break
            q = {"tr_cont": "1", "tr_cont_key": d["tr_cont_key"]}
        return rows

    def holding_row(self, symbol):
        """{"qty", "sellable", "exch_id", "broker_avg", "name"} — 같은 심볼 행(일반·소수 잔고)을 합침. 없으면 qty 0"""
        out = {"qty": 0.0, "sellable": 0.0, "exch_id": None, "broker_avg": 0.0, "name": symbol}
        cost = 0.0
        for r in self.holdings():
            sym = str(r.get("ovrs_stck_symb_iscd") or "").strip().upper()
            if sym != symbol.upper() or str(r.get("rmnd_clcd", "1")) == "3":   # 대출 잔고는 제외
                continue
            q = _num(r.get("rmnd_dqty"))
            out["qty"] += q
            out["sellable"] += _num(r.get("seln_able_dqty"))
            out["exch_id"] = out["exch_id"] or (r.get("ovrs_exch_vndr_idno") or None)
            out["name"] = str(r.get("isnm") or symbol).strip()
            cost += q * _num(r.get("avrg_unpr"))
        out["qty"], out["sellable"] = round(out["qty"], 6), round(out["sellable"], 6)
        out["broker_avg"] = round(cost / out["qty"], 6) if out["qty"] > 0 else 0.0
        return out

    def usd_cash_or_zero(self):
        """USD 예수금(frcr_amt)만. USD 행이 하나도 없으면 0.0 (빈 계좌). 중복·형식 오류는 예외"""
        d = self._call("GET", "/accounts/v1/me/overseas/currencies")
        if d.get("tr_cont") == "1":
            raise MeritzError("외화잔고 응답이 완전하지 않음")
        rows = d.get("data")
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            raise MeritzError("외화잔고 형식 확인 필요")
        usd = [r for r in rows if isinstance(r, dict) and str(r.get("crcd", "")).strip().upper() == "USD"]
        if not usd:
            return 0.0                                  # 달러가 한 번도 안 들어온 계좌 → 0원 (지시문 v1.1)
        if len(usd) != 1 or usd[0].get("frcr_amt") in (None, ""):
            raise MeritzError("USD 예수금 행 중복 또는 값 없음")
        return _num(usd[0]["frcr_amt"])

    def us_market_status(self):
        """미국 장운영 상태 코드 ("004" = 정규장 개시)"""
        d = self._call("GET", "/reference/v1/overseas/market-hours", {"ovrs_stck_mrkt_tr_cls_code": "01"})
        data = d.get("data")
        if isinstance(data, list):
            data = next((x for x in data if isinstance(x, dict) and str(x.get("ovrs_stck_mrkt_tr_cls_code")) == "01"), {})
        return str((data or {}).get("ovrs_mkop_cls_code", ""))

    def usd_estimated(self):
        """Estimated USD deposit (estm_frcr_amt, unsettled included); app '외화 추정 예수금' basis. Never use alone as spendable cash."""
        d = self._call("GET", "/accounts/v1/me/overseas/currencies")
        if d.get("tr_cont") == "1":
            raise MeritzError("외화잔고 응답이 완전하지 않음")
        rows = d.get("data")
        if not isinstance(rows, list):
            raise MeritzError("외화잔고 형식 확인 필요")
        usd = [row for row in rows if isinstance(row, dict) and str(row.get("crcd", "")).strip().upper() == "USD"]
        if len(usd) != 1 or usd[0].get("estm_frcr_amt") in (None, ""):
            raise MeritzError("USD 추정 예수금 행 없음")
        try:
            value = float(str(usd[0]["estm_frcr_amt"]).replace(",", ""))
        except (ValueError, TypeError):
            raise MeritzError("USD 추정 예수금 숫자 확인 필요") from None
        if not math.isfinite(value):
            raise MeritzError("USD 추정 예수금 숫자 확인 필요")
        return value

    def fx_applied_rate(self, crcd="USD", mnec_clcd="1"):
        """환전 적용환율 조회 (읽기 전용). 외화 매수(원화->외화)는 mnec_clcd='1', tltr_aply_byrt 사용.
        출처: 메리츠 Open API openapi.json v2026-10-22, GET /forex/v1/rates/applied"""
        d = self._call("GET", "/forex/v1/rates/applied", {"crcd": crcd, "mnec_clcd": mnec_clcd})
        data = d.get("data") or {}
        rate_key = "tltr_aply_byrt" if mnec_clcd == "1" else "tltr_aply_slrt"
        return {"rate": data.get(rate_key), "exrt_stnd_time": data.get("exrt_stnd_time"),
                "spead": data.get("spead"), "prft_aply_clcd": data.get("prft_aply_clcd"),
                "prft_aply_cls_val": data.get("prft_aply_cls_val"), "raw": data}

    def fx_exchange(self, frcr_amt, iqry_exrt, exrt_stnd_time, crcd="USD", mnec_clcd="1"):
        """실시간 환전신청 (실제 돈 이동 — 텔레그램 2차 확인 버튼에서만 호출할 것).
        스펙: POST /forex/v1/exchanges, 필수 mnec_clcd, wncr_amt, frcr_amt, exrt_stnd_time, iqry_exrt, crcd.
        스펙 예시는 wncr_amt=0, frcr_amt=외화금액으로, 원화는 적용환율로 계산된다.
        스펙상 frcr_amt 타입은 string이지만 예시는 숫자이다 — 서버 수용 여부는 실환전 전에 확인이 필요하고,
        실환전 테스트로 확인하지 않는다. 성공 rsp_cd는 '0000'이며, 기존 _call OK_CODES에 포함된다."""
        body = {"mnec_clcd": str(mnec_clcd), "crcd": crcd, "frcr_amt": str(frcr_amt),
                "wncr_amt": 0, "exrt_stnd_time": exrt_stnd_time, "iqry_exrt": str(iqry_exrt)}
        d = self._call("POST", "/forex/v1/exchanges", body=body)
        if str(d.get("rsp_cd")) != "0000":
            raise MeritzError("환전 성공 코드 불일치")
        return d.get("data") or {}

    def krw_cash(self):
        """KRW cash deposit (data.tfam) — used only to check whether KRW covers an FX buy.
        출처: 메리츠 Open API openapi.json v2026-10-22 (= v2026-10-28 동일 정의),
        GET /accounts/v1/me/deposit, 성공 rsp_cd '5766'.
        구 경로 GET /accounts/v1/me/overseas/currencies 는 외화 행만 주고 KRW 행을 아예 안 줌
        (명세 설명문: '이 API 의 응답에는 wncr_ 로 시작하는 항목이 없습니다')."""
        d = self._call("GET", "/accounts/v1/me/deposit")
        data = d.get("data")
        if not isinstance(data, dict) or data.get("tfam") in (None, ""):
            raise MeritzError("KRW 예수금 확인 필요")
        try:
            value = float(str(data["tfam"]).replace(",", ""))
        except (ValueError, TypeError):
            raise MeritzError("KRW 예수금 숫자 확인 필요") from None
        if not math.isfinite(value):
            raise MeritzError("KRW 예수금 숫자 확인 필요")
        return value

    def exchanges(self):
        """{시세 거래소 구분(AX 등): 주문 벤더번호(0066 등)} — 온라인 주문 가능한 미국 거래소만"""
        d = self._call("GET", "/reference/v1/overseas/exchanges")
        return {str(r.get("ovrs_stck_exch_idno")): str(r.get("ovrs_exch_vndr_idno"))
                for r in (d.get("data") or []) if isinstance(r, dict)
                and str(r.get("ovrs_stck_mrkt_tr_cls_code")) == "01" and str(r.get("onln_yn", "Y")).upper() == "Y"}

    def open_orders_today(self, symbol):
        d = self._call("GET", "/trading/v1/overseas/orders/today", {"cntg_cls_code": "2", "seln_byov_clcd": "0"})
        return [r for r in (d.get("data") or []) if isinstance(r, dict)
                and str(r.get("ovrs_stck_symb_iscd", "")).upper() == symbol.upper() and _num(r.get("ncnt_qty")) > 0]

    def fills(self, date_from, date_to):
        """기간 체결 내역 {주문번호: (BUY/SELL, 체결수량, 체결금액)} — 수량은 소수까지 그대로 합침"""
        out, q = {}, {"oder_sta_date": date_from, "oder_fin_date": date_to, "cntg_cls_code": "1", "seln_byov_clcd": "0"}
        for _ in range(20):
            d = self._call("GET", "/trading/v1/overseas/orders/history", q)
            for r in d.get("data") or []:
                if not isinstance(r, dict):
                    continue
                no = str(r.get("oder_no", "")).strip()
                if no.endswith(".0"):
                    no = no[:-2]
                qty = _num(r.get("cntg_dqty"))
                amt = _num(r.get("cntg_camt")) or qty * _num(r.get("cntg_crnc_prc"))
                if no and qty > 0:
                    side = "SELL" if str(r.get("seln_byov_clcd")) == "1" else "BUY"
                    _, q0, a0 = out.get(no, (side, 0.0, 0.0))
                    out[no] = (side, round(q0 + qty, 6), a0 + amt)
            if d.get("tr_cont") != "1" or not d.get("tr_cont_key"):
                break
            q = dict(q, tr_cont="1", tr_cont_key=d["tr_cont_key"])
        return out

    # ---------------- 주문 (실제 돈이 움직임 — main.py 안전장치를 모두 통과했을 때만 호출)
    def market_order(self, side, symbol, exch_id, qty):
        q = int(qty)
        if q <= 0 or q != qty:
            raise MeritzError(f"주문 수량은 1주 이상 정수만 ({qty})")
        if not exch_id:
            raise MeritzError("거래소 번호(exch_id) 없음")
        body = {"ovrs_stck_symb_iscd": symbol, "ovrs_exch_vndr_idno": str(exch_id), "oder_cls_code": "05",
                "oder_cond_cls_code": "0", "odqt": q, "ovrs_stck_oder_prc": "0"}
        path = f"/trading/v1/overseas/orders/{'buy' if side == 'BUY' else 'sell'}"
        d = self._call("POST", path, body=body)
        data = d.get("data") or {}
        warn = str(data.get("warn_cls_code", "0")).strip()
        if warn and warn != "0":
            raise WarnNeeded(str(data.get("warn_msg") or f"경고코드 {warn}"))
        no = data.get("oder_no", "")
        no = str(int(no)) if isinstance(no, float) and no.is_integer() else str(no).strip()
        return {"no": no, "body": body}


class MeritzDcaClient:
    """3번 엔진이 부르던 함수 이름을 메리츠 호출로. 모든 호출은 asyncio.to_thread 로 (스케줄러를 막지 않음).
    종목별 시세 거래소(mrkt)·주문 벤더번호(exch_id)는 market_hint 로 받거나, OQ→NY→AX 순서로 찾아 캐시."""

    def __init__(self, api: MeritzApi, market_hint=None):
        self.api = api
        self.market_hint = market_hint or (lambda sym: (None, None))
        self._mk = {}          # sym -> (mrkt, exch_id)
        self._vendor = None
        self._last_info = {}

    def _known(self, sym):
        c, h = self._mk.get(sym) or (None, None), self.market_hint(sym) or (None, None)
        return (c[0] or h[0]), (c[1] or h[1])

    async def _t(self, fn, *a):
        return await asyncio.to_thread(fn, *a)

    async def vendor_map(self):
        if self._vendor is None:
            try:
                self._vendor = dict(VENDOR_FALLBACK, **(await self._t(self.api.exchanges)))
            except Exception:
                self._vendor = dict(VENDOR_FALLBACK)
        return self._vendor

    async def resolve(self, symbol):
        """(시세 거래소 구분, 주문 벤더번호, 시세 dict). 못 찾으면 MeritzError"""
        sym = str(symbol).strip().upper()
        mk, ex = self._known(sym)
        tried = [mk] if mk else []
        tried += [m for m in PRICE_MARKETS if m not in tried]
        last = None
        for m in tried:
            try:
                p = await self._t(self.api.price, sym, m)
            except MeritzError as e:
                last = e
                continue
            ex = ex or (await self.vendor_map()).get(m)
            self._mk[sym] = (m, ex)
            self._last_info[sym] = p
            return m, ex, p
        raise MeritzError(f"{sym} 미국 시세를 찾지 못함 ({last})")

    async def get_stock_info(self, symbol):
        sym = str(symbol).strip().upper()
        m, ex, p = await self.resolve(sym)
        return {"symbol": sym, "name": p.get("name") or sym, "currency": p.get("currency") or "USD",
                "market_country": "US", "status": p.get("status", ""), "mrkt": m, "exch_id": ex}

    async def get_current_price(self, symbol):
        sym = str(symbol).strip().upper()
        mk, _ = self._known(sym)
        if mk:
            try:
                p = await self._t(self.api.price, sym, mk)
                self._last_info[sym] = p
                return float(p["price"])
            except MeritzError:
                self._mk.pop(sym, None)
        _, _, p = await self.resolve(sym)
        return float(p["price"])

    async def get_symbol_holdings(self, symbol):
        """증권사 잔고 (수량·매도가능·거래소번호). 평단은 봇 장부가 기준이라 avg_price 는 일부러 0"""
        sym = str(symbol).strip().upper()
        row = await self._t(self.api.holding_row, sym)
        if row.get("exch_id"):                       # 잔고 행의 거래소 번호가 가장 정확함 → 캐시
            self._mk[sym] = ((self._mk.get(sym) or (None, None))[0], row["exch_id"])
        return {"qty": row["qty"], "sellable": row["sellable"], "exch_id": row["exch_id"],
                "broker_avg": row["broker_avg"], "name": row["name"]}

    async def get_sellable_quantity(self, symbol):
        return float((await self.get_symbol_holdings(symbol)).get("sellable") or 0.0)

    async def get_all_holdings(self):
        rows = await self._t(self.api.holdings)
        out = {}
        for r in rows:
            sym = str(r.get("ovrs_stck_symb_iscd") or "").strip().upper()
            if not sym or str(r.get("rmnd_clcd", "1")) == "3" or str(r.get("crcd", "USD")).upper() != "USD":
                continue
            out.setdefault(sym, {"symbol": sym, "name": str(r.get("isnm") or sym).strip(), "qty": 0.0})
            out[sym]["qty"] = round(out[sym]["qty"] + _num(r.get("rmnd_dqty")), 6)
        return list(out.values())

    async def get_buying_power(self, currency="USD"):
        if str(currency).upper() != "USD":
            return 0.0
        return float(await self._t(self.api.usd_cash_or_zero))

    async def us_market_status(self):
        return await self._t(self.api.us_market_status)

    async def get_candles_1d(self, symbol, count=200, before=None):
        """N7용. 3번 toss_api.get_candles_1d 와 같은 모양: ([{"date":YYYYMMDD,"close":종가}], None) — 한 번에 약 330일치"""
        sym = str(symbol).strip().upper()
        mk, _, _ = await self.resolve(sym)
        today = datetime.now(EST_TZ).date()
        rows = await self._t(self.api.daily_closes, sym, mk,
                             (today - timedelta(days=330)).strftime("%Y%m%d"), today.strftime("%Y%m%d"))
        return [{"date": d, "close": c} for d, c in rows], None

    async def open_orders_today(self, symbol):
        return await self._t(self.api.open_orders_today, str(symbol).strip().upper())

    async def fills(self, date_from, date_to):
        return await self._t(self.api.fills, date_from, date_to)

    async def market_order(self, side, symbol, qty):
        sym = str(symbol).strip().upper()
        mk, ex = self._known(sym)
        if not ex:
            mk, ex, _ = await self.resolve(sym)
        return await self._t(self.api.market_order, side, sym, ex, qty)

    def cached_market(self, symbol):
        return self._mk.get(str(symbol).strip().upper(), (None, None))
