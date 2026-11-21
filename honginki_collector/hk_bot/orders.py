"""주문 의도(기록용 자료)만 만든다. 전송 기능은 이 패키지 어디에도 없다."""


def intent(side, code, qty, kind, price=None):
    """side: buy|sell, kind: limit|market. 돌려주는 값은 기록에만 쓰인다."""
    assert side in ("buy", "sell") and kind in ("limit", "market")
    return {"side": side, "code": code, "qty": int(qty), "kind": kind,
            "price": None if price is None else float(price), "sent": False}
