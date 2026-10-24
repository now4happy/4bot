# =====================================================================
# FILE: toss_api.py
# 목적: 토스증권 Open API 통신 모듈 (한국주식 1주 단위 & 미국주식 소수점 주문 통합 지원)
# =====================================================================

import asyncio
import aiohttp
import time
import html
import json
from datetime import datetime
from zoneinfo import ZoneInfo

KST_TZ = ZoneInfo("Asia/Seoul")
EST_TZ = ZoneInfo("America/New_York")


class GlobalThrottle:
    _api_lock = asyncio.Lock()
    _last_api_call = 0.0
    _file_locks = {}

    @classmethod
    async def wait_api_sync(cls):
        async with cls._api_lock:
            now = time.monotonic()
            elapsed = now - cls._last_api_call
            if elapsed < 0.18:
                await asyncio.sleep(0.18 - elapsed)
            cls._last_api_call = time.monotonic()

    @classmethod
    def get_file_lock(cls, filepath: str) -> asyncio.Lock:
        if filepath not in cls._file_locks:
            cls._file_locks[filepath] = asyncio.Lock()
        return cls._file_locks[filepath]


class _NonRetryableApiError(Exception):
    pass


class TossApiClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://openapi.tossinvest.com"
        self.token = None
        self.account_seq = None
        self._auth_lock = asyncio.Lock()

    def _get_headers(self, requires_account: bool = False) -> dict:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if requires_account and self.account_seq:
            headers["X-Tossinvest-Account"] = str(self.account_seq)
        return headers

    async def authenticate(self):
        async with self._auth_lock:
            await self._do_authenticate()

    async def _do_authenticate(self):
        url = f"{self.base_url}/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        await GlobalThrottle.wait_api_sync()
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, timeout=10.0) as resp:
                if resp.status >= 400:
                    err_text = await resp.text()
                    raise Exception(f"Auth HTTP {resp.status}: {html.escape(err_text[:200])}")
                data = await resp.json()
                if isinstance(data, dict):
                    self.token = data.get("access_token")

    async def _request(
        self,
        method: str,
        endpoint: str,
        headers: dict = None,
        json_data: dict = None,
        timeout: float = 10.0,
    ):
        url = f"{self.base_url}{endpoint}"
        req_headers = dict(headers) if headers else {}

        effective_json = json_data
        if method.upper() in ("POST", "PUT", "PATCH") and effective_json is None:
            effective_json = {}

        for attempt in range(3):
            await GlobalThrottle.wait_api_sync()

            if not self.token:
                await self.authenticate()
            if self.token:
                req_headers["Authorization"] = f"Bearer {self.token}"

            try:
                async with aiohttp.ClientSession() as session:
                    kwargs = {"headers": req_headers, "timeout": timeout}
                    if method.upper() in ("POST", "PUT", "PATCH"):
                        kwargs["json"] = effective_json
                    async with session.request(method, url, **kwargs) as resp:
                        if resp.status == 401:
                            if attempt == 2:
                                raise _NonRetryableApiError("API HTTP 401: Unauthorized")
                            async with self._auth_lock:
                                await self._do_authenticate()
                            continue

                        if resp.status == 429:
                            if attempt == 2:
                                raise Exception("API HTTP 429: Rate Limit Exceeded")
                            retry_after = int(resp.headers.get("Retry-After", 2 ** attempt))
                            await asyncio.sleep(retry_after)
                            continue

                        if resp.status == 204:
                            return {}

                        if resp.status >= 400:
                            err_text = await resp.text()
                            try:
                                err_json = json.loads(err_text)
                                if isinstance(err_json, dict):
                                    err_obj = err_json.get("error", {})
                                    if isinstance(err_obj, dict):
                                        err_code = err_obj.get("code", "")
                                        err_msg = err_obj.get("message", err_text)
                                        if err_code:
                                            err_msg = f"[{err_code}] {err_msg}"
                                    else:
                                        err_msg = err_json.get("error_description", str(err_obj))
                                else:
                                    err_msg = err_text
                                safe_err = html.escape(str(err_msg))
                            except Exception:
                                safe_err = html.escape(err_text)

                            full_err_msg = f"API HTTP {resp.status}: {safe_err}"
                            if 400 <= resp.status < 500:
                                raise _NonRetryableApiError(full_err_msg)
                            raise Exception(full_err_msg)

                        return await resp.json()
            except _NonRetryableApiError as non_retry_err:
                raise Exception(str(non_retry_err))
            except Exception as e:
                if attempt == 2 or (method.upper() == "POST" and "/orders" in endpoint):
                    raise e   # 주문은 응답이 끊겨도 체결됐을 수 있으므로 자동 재전송하지 않음
                await asyncio.sleep(2 ** attempt)

    async def fetch_account_seq(self):
        data = await self._request("GET", "/api/v1/accounts", headers=self._get_headers())
        accounts = (data.get("result") if isinstance(data, dict) else None) or []
        for acc in accounts:
            if isinstance(acc, dict) and acc.get("accountType") == "BROKERAGE":
                self.account_seq = acc.get("accountSeq")
                break
        if not self.account_seq and accounts and isinstance(accounts[0], dict):
            self.account_seq = accounts[0].get("accountSeq")

    async def get_stock_info(self, symbol: str) -> dict:
        """종목 코드(005930, AAPL 등)로 종목명, 통화(KRW/USD), 시장 정보를 조회합니다."""
        sym = str(symbol).strip().upper()
        data = await self._request("GET", f"/api/v1/stocks?symbols={sym}", headers=self._get_headers())
        res_list = (data.get("result") if isinstance(data, dict) else None) or []
        if res_list and isinstance(res_list[0], dict):
            item = res_list[0]
            currency = str(item.get("currency") or ("KRW" if sym.isdigit() else "USD")).upper()
            market_country = "KR" if currency == "KRW" else "US"
            return {
                "symbol": str(item.get("symbol") or sym).upper(),
                "name": str(item.get("name") or sym),
                "currency": currency,
                "market_country": market_country,
                "status": str(item.get("status") or "ACTIVE"),
            }
        return {}

    async def get_current_price(self, symbol: str) -> float:
        sym = str(symbol).strip().upper()
        data = await self._request("GET", f"/api/v1/prices?symbols={sym}", headers=self._get_headers())
        res_list = (data.get("result") if isinstance(data, dict) else None) or []
        if res_list and isinstance(res_list[0], dict):
            p = res_list[0].get("lastPrice")
            return float(p) if p is not None else 0.0
        return 0.0

    async def get_symbol_holdings(self, symbol: str) -> dict:
        """해당 종목의 보유 수량(qty), 평단가(avg_price), 수익률(profit_rate) 조회"""
        if not self.account_seq:
            await self.fetch_account_seq()
        sym = str(symbol).strip().upper()
        data = await self._request(
            "GET",
            f"/api/v1/holdings?symbol={sym}",
            headers=self._get_headers(requires_account=True),
        )
        res_dict = (data.get("result") if isinstance(data, dict) else None) or {}
        items = res_dict.get("items") or []
        if not items or not isinstance(items[0], dict):
            return {"qty": 0.0, "avg_price": 0.0, "last_price": 0.0, "profit_pct": 0.0}

        item = items[0]
        qty = float(item.get("quantity") or 0.0)
        avg_price = float(item.get("averagePurchasePrice") or 0.0)
        last_price = float(item.get("lastPrice") or 0.0)
        profit_pct = ((last_price / avg_price - 1.0) * 100.0) if (avg_price > 0 and last_price > 0) else 0.0
        return {
            "qty": qty,
            "avg_price": avg_price,
            "last_price": last_price,
            "profit_pct": profit_pct,
        }

    async def get_buying_power(self, currency: str = "USD") -> float:
        if not self.account_seq:
            await self.fetch_account_seq()
        cur = str(currency).strip().upper()
        data = await self._request(
            "GET",
            f"/api/v1/buying-power?currency={cur}",
            headers=self._get_headers(requires_account=True),
        )
        res_dict = (data.get("result") if isinstance(data, dict) else None) or {}
        bp = res_dict.get("cashBuyingPower")
        return float(bp) if bp is not None else 0.0

    async def get_sellable_quantity(self, symbol: str) -> float:
        if not self.account_seq:
            await self.fetch_account_seq()
        sym = str(symbol).strip().upper()
        data = await self._request(
            "GET",
            f"/api/v1/sellable-quantity?symbol={sym}",
            headers=self._get_headers(requires_account=True),
        )
        res_dict = (data.get("result") if isinstance(data, dict) else None) or {}
        sq = res_dict.get("sellableQuantity")
        return float(sq) if sq is not None else 0.0

    async def is_regular_market_open(self, market_country: str) -> tuple[bool, str]:
        """정규장 개장 여부 확인 (KR: KST 기준, US: EST 정규장 소수점 주문 가능 시간 확인)"""
        mc = str(market_country).strip().upper()
        try:
            if mc == "KR":
                today_str = datetime.now(KST_TZ).strftime("%Y-%m-%d")
                data = await self._request("GET", f"/api/v1/market-calendar/KR?date={today_str}", headers=self._get_headers())
                res = (data.get("result") if isinstance(data, dict) else None) or {}
                today_obj = res.get("today") or {}
                reg = (today_obj.get("integrated") or {}).get("regularMarket") or (today_obj.get("krx") or {}).get("regularMarket")
                if not reg:
                    return False, "국내 정규장 휴장일"
                now_kst = datetime.now(KST_TZ)
                start = datetime.fromisoformat(reg["startTime"]).astimezone(KST_TZ)
                end = datetime.fromisoformat(reg["endTime"]).astimezone(KST_TZ)
                if start <= now_kst <= end:
                    return True, "KR_REGULAR_OPEN"
                return False, f"국내 정규장 시간 외 ({start.strftime('%H:%M')}~{end.strftime('%H:%M')} KST)"
            else:
                now_est = datetime.now(EST_TZ)
                today_str = now_est.strftime("%Y-%m-%d")
                data = await self._request("GET", f"/api/v1/market-calendar/US?date={today_str}", headers=self._get_headers())
                res = (data.get("result") if isinstance(data, dict) else None) or {}
                today_obj = res.get("today") or {}
                reg = today_obj.get("regularMarket")
                if not reg:
                    return False, "미국 정규장 휴장일"
                start = datetime.fromisoformat(reg["startTime"]).astimezone(EST_TZ)
                end = datetime.fromisoformat(reg["endTime"]).astimezone(EST_TZ)
                if start <= now_est <= end:
                    return True, "US_REGULAR_OPEN"
                return False, f"미국 정규장 시간 외 ({start.strftime('%H:%M')}~{end.strftime('%H:%M')} EST)"
        except Exception:
            if mc == "KR":
                now_kst = datetime.now(KST_TZ)
                hm = now_kst.hour * 100 + now_kst.minute
                if now_kst.weekday() < 5 and 900 <= hm <= 1520:
                    return True, "KR_FALLBACK_OPEN"
                return False, "국내 정규장 시간 외(폴백)"
            else:
                now_est = datetime.now(EST_TZ)
                hm = now_est.hour * 100 + now_est.minute
                if now_est.weekday() < 5 and 930 <= hm <= 1500:
                    return True, "US_FALLBACK_OPEN"
                return False, "미국 정규장 소수점 시간 외(폴백)"

    async def place_us_fractional_buy(self, symbol: str, amount_usd: float, client_order_id: str) -> dict:
        """미국 주식 소수점 금액 시장가 매수 (orderType=MARKET, orderAmount=달러금액)"""
        if not self.account_seq:
            await self.fetch_account_seq()
        payload = {
            "clientOrderId": str(client_order_id)[:36],
            "symbol": str(symbol).strip().upper(),
            "side": "BUY",
            "orderType": "MARKET",
            "orderAmount": f"{round(float(amount_usd), 2):.2f}",
        }
        return await self._request(
            "POST",
            "/api/v1/orders",
            headers=self._get_headers(requires_account=True),
            json_data=payload,
        )

    async def place_us_fractional_sell(self, symbol: str, quantity: float, client_order_id: str) -> dict:
        """미국 주식 소수점/정수 수량 시장가 매도 (소수점 최대 6자리)"""
        if not self.account_seq:
            await self.fetch_account_seq()
        qty_str = f"{float(quantity):.6f}".rstrip("0").rstrip(".")
        payload = {
            "clientOrderId": str(client_order_id)[:36],
            "symbol": str(symbol).strip().upper(),
            "side": "SELL",
            "orderType": "MARKET",
            "quantity": qty_str,
        }
        return await self._request(
            "POST",
            "/api/v1/orders",
            headers=self._get_headers(requires_account=True),
            json_data=payload,
        )

    async def place_kr_integer_order(self, symbol: str, side: str, quantity: int, client_order_id: str) -> dict:
        """한국 주식 1주 단위(정수) 시장가 매수/매도"""
        if not self.account_seq:
            await self.fetch_account_seq()
        payload = {
            "clientOrderId": str(client_order_id)[:36],
            "symbol": str(symbol).strip().upper(),
            "side": str(side).strip().upper(),
            "orderType": "MARKET",
            "quantity": str(int(quantity)),
        }
        return await self._request(
            "POST",
            "/api/v1/orders",
            headers=self._get_headers(requires_account=True),
            json_data=payload,
        )


    async def get_all_holdings(self, symbol: str='') -> list:
        """해당 종목의 보유 수량(qty), 평단가(avg_price), 수익률(profit_rate) 조회"""
        if not self.account_seq:
            await self.fetch_account_seq()
        sym = str(symbol).strip().upper()
        data = await self._request('GET', '/api/v1/holdings', headers=self._get_headers(requires_account=True))
        result = data.get('result') if isinstance(data, dict) else None
        if not isinstance(result, dict) or not isinstance(result.get('items'), list):
            raise ValueError('Unexpected holdings response')
        return result['items']
