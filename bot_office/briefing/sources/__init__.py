# briefing/sources — 소스별 어댑터. 반환 형식은 모두 같다:
# {"status": "ok|partial|unavailable",
#  "accounts": {계좌키: {"status": "ok|unavailable", "holdings": {티커: 수량}, "note": str}}}
class SourceError(Exception):
    pass


def acct_ok(holdings, note=""):
    return {"status": "ok", "holdings": holdings, "note": note}


def acct_fail(note):
    return {"status": "unavailable", "holdings": {}, "note": note}


def overall(accounts):
    sts = [a["status"] for a in accounts.values()]
    if sts and all(s == "ok" for s in sts):
        return "ok"
    if any(s == "ok" for s in sts):
        return "partial"
    return "unavailable"


_TICKER_KEYS = ("ticker", "symbol", "code", "stock_code", "종목코드")
_QTY_KEYS = ("quantity", "qty", "holding_qty", "hold_qty", "수량")


def normalize_holdings(raw):
    """{티커: 수량} 또는 [{ticker/symbol/..., quantity/qty/...}] 를 {티커: 수량(float)} 로.
    실제 반환 형식은 미확인이라 두 모양만 받고, 그 밖이면 SourceError."""
    out = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise SourceError("수량 형식 이상: %r" % (k,))
            out[str(k)] = float(v)
        return out
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                raise SourceError("보유 항목 형식 이상")
            t = next((item[k] for k in _TICKER_KEYS if k in item), None)
            q = next((item[k] for k in _QTY_KEYS if k in item), None)
            if t is None or isinstance(q, bool) or not isinstance(q, (int, float, str)):
                raise SourceError("보유 항목에 티커/수량 없음")
            try:
                out[str(t)] = out.get(str(t), 0.0) + float(q)
            except ValueError:
                raise SourceError("수량 숫자 아님")
        return out
    raise SourceError("보유 반환 형식 미확인")
