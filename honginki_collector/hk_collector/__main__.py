"""홍인기 단타 수집기 (단계 0). 실행: python3 -m hk_collector  |  점검: python3 -m hk_collector --check
데이터만 모은다. 주문·신호 평가 코드 없음."""
import asyncio
import json
import signal
import sys
from datetime import datetime, time as dtime

from . import config as C
from .bars import BarBuilder
from .rest import Rest, load_keys
from .store import Store, now_kst
from .ws import WsCollector


def hhmm(s):
    h, m = s.split(":")
    return dtime(int(h), int(m))


def in_session(now=None):
    now = now or now_kst()
    return now.weekday() < 5 and hhmm(C.SESSION_START) <= now.time() < hhmm(C.SESSION_END)


def poll_once(rest):
    """REST 한 바퀴 (6건). 거래대금 상위 종목코드 목록을 돌려준다."""
    r32 = rest.call("ka10032", {"mrkt_tp": "000", "mang_stk_incls": "1", "stex_tp": "1"},
                    max_pages=C.PAGES_10032)
    for mk in ("P00101", "P10102"):
        for aq in ("1", "2"):   # 1:금액 2:수량 — 수량 모드 응답 필드는 미확인이라 둘 다 저장
            rest.call("ka90003", {"trde_upper_tp": "2", "amt_qty_tp": aq, "mrkt_tp": mk,
                                  "stex_tp": "1"})
    rest.call("ka10063", {"mrkt_tp": "000", "amt_qty_tp": "1", "invsr": "7", "frgn_all": "0",
                          "smtm_netprps_tp": "0", "stex_tp": "1"}, max_pages=C.PAGES_10063)
    codes = []
    for code, text in r32:
        if code != 0:
            continue
        for row in json.loads(text).get("trde_prica_upper") or []:
            cd = str(row.get("stk_cd", "")).split("_")[0]
            if cd and cd not in codes:
                codes.append(cd)
    return codes[:C.TOP_N]


def resync(rest, symbols, tag):
    """재접속 뒤 1분봉 재조회 (단절 구간 대조용 원문 저장)."""
    day = now_kst().strftime("%Y%m%d")
    for cd in symbols:
        rest.call("ka10080", {"stk_cd": cd, "tic_scope": "1", "upd_stkpc_tp": "1",
                              "base_dt": day}, tag=tag)


def daily(rest, symbols):
    day = now_kst().strftime("%Y%m%d")
    for cd in symbols:
        rest.call("ka10081", {"stk_cd": cd, "base_dt": day, "upd_stkpc_tp": "1"}, tag="eod")


async def run_session(store, rest):
    builders = [BarBuilder(m, lambda b: store.write(f"bars_{b['m']}m", b), C.BAR_GRACE_S)
                for m in C.BAR_MINUTES]
    tasks = set()

    def on_reconnect():
        ws.note_gap_closed()
        t = asyncio.create_task(asyncio.to_thread(resync, rest, list(ws.symbols), "resync"))
        tasks.add(t)
        t.add_done_callback(tasks.discard)

    ws = WsCollector(store, rest, builders, on_reconnect)
    ws_task = asyncio.create_task(ws.run())
    store.event("session_start", poll_s=C.POLL_S, top_n=C.TOP_N, gap_s=C.REST_MIN_GAP_S)

    async def sweeper():
        while True:
            await asyncio.sleep(1)
            for b in builders:
                b.sweep()
            store.flush()

    sw = asyncio.create_task(sweeper())
    try:
        while in_session() and not STOP.is_set():
            t0 = asyncio.get_running_loop().time()
            try:
                ws.add_symbols(await asyncio.to_thread(poll_once, rest))
            except Exception as e:  # noqa: BLE001
                store.event("poll_error", err=f"{type(e).__name__}: {e}")
            left = C.POLL_S - (asyncio.get_running_loop().time() - t0)
            try:
                await asyncio.wait_for(STOP.wait(), max(left, 1))
            except asyncio.TimeoutError:
                pass
    finally:
        sw.cancel()
        await ws.close()
        ws_task.cancel()
        await asyncio.gather(ws_task, *tasks, return_exceptions=True)
        for b in builders:
            b.flush_all()
        if not STOP.is_set():
            try:
                await asyncio.to_thread(daily, rest, list(ws.symbols))
            except Exception as e:  # noqa: BLE001
                store.event("eod_error", err=f"{type(e).__name__}: {e}")
        summary = {"day": store.day, "written": dict(store.counts),
                   "rest_codes": dict(rest.codes), "ws_disconnects": ws.disconnects,
                   "ws_gap_seconds": round(ws.gap_s, 1), "symbols": len(ws.symbols),
                   "late_ticks": {str(b.m): b.late for b in builders},
                   "settings": {"poll_s": C.POLL_S, "rest_min_gap_s": C.REST_MIN_GAP_S,
                                "top_n": C.TOP_N, "max_subs": C.MAX_SUBS}}
        store.event("session_end", **summary)
        store.flush()
        store.write_summary(summary)


async def main():
    global STOP
    STOP = asyncio.Event()
    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, STOP.set)
    appkey, secret, loose = load_keys(C.KEY_FILE)
    store = Store(C.DATA_DIR)
    if loose:
        store.event("key_file_perm_warn")
    rest = Rest(store, appkey, secret)
    if "--check" in sys.argv:   # 토큰 + REST 한 바퀴만 돌려 보고 끝낸다
        codes = await asyncio.to_thread(poll_once, rest)
        store.close()
        print("check ok", "top", len(codes), "rest_codes", dict(rest.codes))
        return
    while not STOP.is_set():
        if in_session():
            await run_session(store, rest)
        else:
            try:
                await asyncio.wait_for(STOP.wait(), 20)
            except asyncio.TimeoutError:
                pass
    store.close()


STOP = None
if __name__ == "__main__":
    asyncio.run(main())
