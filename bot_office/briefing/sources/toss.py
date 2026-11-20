# briefing/sources/toss.py — 토스 보유 수량. 읽기 전용 (toss_sniper/ 는 수정하지 않는다).
# Q18 (live_board.py 발췌 기준): TossApiClient(base_dir=TOSS_DIR) 로 만들고, await client.<메서드>() 로 부르고,
# 끝에 await client.close() 를 부른다. 공유 토큰 로직은 toss_api.py 안에 있다 → 여기서 toss_token_share.try_acquire 를
# 직접 부르지 않는다 (앞 판의 가정 정정). 40초 제한·실패해도 close 하는 모양은 live_board 와 같다.
# ※ get_holdings 의 이름·반환 모양은 live_board 발췌에 없다(미확인). 있다고 가정하고, 없거나 모양이 다르면 SourceError →
#    '확인 불가 ⚠️' 로만 나오고 다른 소스는 정상. 공유 토큰 복원(a) 미적용이어도 재시도 최대 1회, 강제 재발급 반복 금지.
import asyncio
import inspect
import sys

from . import SourceError, acct_fail, acct_ok, normalize_holdings, overall

ACCOUNT = "토스"
TIMEOUT_SEC = 40


async def _holdings(client):
    fn = getattr(client, "get_holdings", None)
    if fn is None:
        raise SourceError("TossApiClient.get_holdings 없음")
    res = fn()
    if inspect.isawaitable(res):
        res = await res
    return res


def _real_get_holdings(cfg):
    d = cfg["paths"].get("toss_dir")
    if d and d not in sys.path:
        sys.path.insert(0, d)
    try:
        import toss_api  # noqa: WPS433
        client = toss_api.TossApiClient(base_dir=d)
    except Exception as e:
        raise SourceError("토스 클라이언트 만들기 실패: %s" % type(e).__name__)

    async def run():
        try:
            return await asyncio.wait_for(_holdings(client), TIMEOUT_SEC)
        except asyncio.TimeoutError:
            raise SourceError("토스 시간초과") from None
        finally:
            try:
                await client.close()
            except Exception:
                pass

    try:
        return asyncio.run(run())
    except SourceError:
        raise
    except Exception as e:
        raise SourceError("토스 조회 실패: %s" % type(e).__name__)


def fetch(cfg, get_holdings=None):
    fn = get_holdings or (lambda: _real_get_holdings(cfg))
    last = None
    for _ in range(2):  # 최초 1회 + 재시도 최대 1회
        try:
            accounts = {ACCOUNT: acct_ok(normalize_holdings(fn()))}
            return {"status": "ok", "accounts": accounts}
        except SourceError as e:
            last = str(e)
        except Exception as e:  # 어떤 오류도 다른 소스를 막지 않는다
            last = type(e).__name__
    accounts = {ACCOUNT: acct_fail(last or "알 수 없음")}
    return {"status": overall(accounts), "accounts": accounts}
