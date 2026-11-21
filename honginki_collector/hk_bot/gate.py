"""통과 판정 (순수 함수) [v2]. 판 2: 최소 거래 수 + 비용 반영 후 플러스 + 이웃 고원. 월별·낙폭 기준 없음(사용자 결정).

MIN_TRADES 는 F 백테스트의 변형별 쌍 수 분포를 보고, B·C 수익률을 보기 전에 정해 넣는다.
정해 넣은 뒤에는 바꾸지 않는다. 지금은 None 이라 판정을 부르면 멈춘다 (중단 장치).
backtest.run() 에는 아직 연결하지 않았다 (연결 방식은 Muse 검토 뒤).
"""
MIN_TRADES = None   # 미확정


def trade_pairs(trades):
    """한 변형의 거래 목록 -> 서로 다른 (진입일, 종목) 쌍 수. 진입일 = entry_t 앞 10자(YYYY-MM-DD)."""
    return len({(t["entry_t"][:10], t["code"]) for t in trades})


def is_positive(trades):
    """최소 거래 수 + 비용 반영 후 플러스. net 은 거래 기록의 net (수수료·세금·슬리피지 반영 후)."""
    if MIN_TRADES is None:
        raise RuntimeError("MIN_TRADES 미확정 — 값을 정한 뒤 실행")
    return trade_pairs(trades) >= MIN_TRADES and sum(t["net"] for t in trades) > 0


def passes(vid, trades_by_variant, neighbors_of):
    """통과 = 자기 자신과 이웃이 모두 is_positive. neighbors_of(vid): 이웃 변형 id 목록."""
    if not is_positive(trades_by_variant.get(vid, [])):
        return False
    nbrs = neighbors_of(vid)
    return bool(nbrs) and all(is_positive(trades_by_variant.get(n, [])) for n in nbrs)
