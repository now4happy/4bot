"""홍인기 단타 매매봇 (단계 1). 주문은 내지 않는다.

python3 -m hk_bot fetch [일수]   과거 자료 받기 (기본 30 거래일) — 키움 조회 호출
python3 -m hk_bot backtest       받은 자료로 백테스트 (호출 없음)
python3 -m hk_bot shadow         그림자 모드 (수집기 자료를 읽어 가상 매매 기록)
"""
import json
import sys


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fetch":
        from . import hist
        print(json.dumps(hist.fetch_all(int(sys.argv[2]) if len(sys.argv) > 2 else 30),
                         ensure_ascii=False))
    elif cmd == "backtest":
        from . import backtest
        out = backtest.run()
        print(json.dumps({k: out[k] for k in ("window", "trading_days", "funnel", "candidates",
                                              "n_variants", "summary")}, ensure_ascii=False))
        print("근사:", *out["approximations"], sep="\n- ")
    elif cmd == "shadow":
        from . import shadow
        shadow.main()
    else:
        print(__doc__)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
