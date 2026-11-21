# briefing/sources/meritz.py — 메리츠 적립(MeritzDcaClient.get_all_holdings: NKE·QLD·SGOV)과
# 탑쌓기(MeritzApi.holding("SOXL")) 을 따로 try 한다. 한쪽 실패가 다른 쪽을 막지 않는다.
# ※ 호출 간격(global_throttle.py) 규칙과 클래스 생성 인자는 미확인 → 어댑터는 가정 기반이며 실패 시 '비교 불가'.
import sys

from . import SourceError, acct_fail, acct_ok, normalize_holdings, overall

DCA = "메리츠 적립"
LAOER = "메리츠 탑쌓기"


def _real_dca(cfg):
    d = cfg["paths"].get("meritz_dca_dir")
    if d and d not in sys.path:
        sys.path.insert(0, d)
    try:
        import meritz_dca_client  # noqa: WPS433  (모듈 이름 미확인)
        return meritz_dca_client.MeritzDcaClient().get_all_holdings()
    except Exception as e:
        raise SourceError("메리츠 적립 조회 실패: %s" % type(e).__name__)


def _real_laoer(cfg):
    d = cfg["paths"].get("meritz_laoer_dir")
    if d and d not in sys.path:
        sys.path.insert(0, d)
    try:
        import meritz_api  # noqa: WPS433  (모듈 이름 미확인)
        q = meritz_api.MeritzApi().holding("SOXL")
        return {"SOXL": q}
    except Exception as e:
        raise SourceError("메리츠 탑쌓기 조회 실패: %s" % type(e).__name__)


def fetch(cfg, dca=None, laoer=None):
    dca = dca or (lambda: _real_dca(cfg))
    laoer = laoer or (lambda: _real_laoer(cfg))
    accounts = {}
    for key, fn in ((DCA, dca), (LAOER, laoer)):
        try:
            accounts[key] = acct_ok(normalize_holdings(fn()))
        except SourceError as e:
            accounts[key] = acct_fail(str(e))
        except Exception as e:
            accounts[key] = acct_fail(type(e).__name__)
    return {"status": overall(accounts), "accounts": accounts}
