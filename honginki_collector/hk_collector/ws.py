"""키움 실시간 WebSocket 수집 (직접 작성). LOGIN → REG, PING 에코, 끊기면 재접속·재등록."""
import asyncio
import json
import time

import websockets

from . import config as C
from .store import now_kst

SYMBOL_TYPES = ["0B", "0D", "0w"]
GLOBAL_TYPES = ["0s", "1h"]


class WsCollector:
    def __init__(self, store, rest, builders, on_reconnect=None):
        self.store = store
        self.rest = rest
        self.builders = builders
        self.on_reconnect = on_reconnect
        self.symbols = []          # 등록 순서 유지
        self._pending = asyncio.Queue()
        self.ws = None
        self.stop = asyncio.Event()
        self.disconnects = 0
        self.gap_s = 0.0
        self.connected_once = False

    def add_symbols(self, codes):
        new = [c for c in codes if c not in self.symbols]
        room = C.MAX_SUBS - len(self.symbols)
        if len(new) > room:
            self.store.event("sub_cap", dropped=len(new) - max(room, 0), cap=C.MAX_SUBS)
            new = new[:max(room, 0)]
        if new:
            self.symbols.extend(new)
            self._pending.put_nowait(new)
        return new

    async def _send(self, obj):
        await self.ws.send(json.dumps(obj))

    async def _reg(self, items, types):
        await self._send({"trnm": "REG", "grp_no": "1", "refresh": "1",
                          "data": [{"item": items, "type": types}]})
        self.store.event("ws_reg", n=len(items), types=types)

    async def _reg_all(self):
        await self._reg([""], GLOBAL_TYPES)
        for i in range(0, len(self.symbols), C.REG_CHUNK):
            await self._reg(self.symbols[i:i + C.REG_CHUNK], SYMBOL_TYPES)

    def _handle(self, raw):
        try:
            msg = json.loads(raw)
        except ValueError:
            self.store.write("ws_sys", {"raw": raw if isinstance(raw, str) else repr(raw)})
            return None
        trnm = msg.get("trnm") if isinstance(msg, dict) else None
        if trnm == "PING":
            return "PING"
        if trnm != "REAL":
            self.store.write("ws_sys", {"msg": msg})
            return trnm
        for d in msg.get("data") or []:
            typ, item, vals = d.get("type"), d.get("item"), d.get("values") or {}
            ex = vals.get("20") or vals.get("21") or vals.get("1223")
            self.store.write(f"ws_{typ}", {"type": typ, "item": item, "ex_tm": ex, "values": vals})
            if typ == "0B":
                for b in self.builders:
                    b.tick(item, vals)
        return "REAL"

    async def _session(self):
        token = await asyncio.to_thread(self.rest.token)
        async with websockets.connect(C.WS_URL, ping_interval=None, open_timeout=15,
                                      max_size=None, user_agent_header=C.UA) as ws:
            self.ws = ws
            await self._send({"trnm": "LOGIN", "token": token})   # 보낸 패킷은 저장하지 않음
            ack = json.loads(await asyncio.wait_for(ws.recv(), 15))
            self.store.write("ws_sys", {"msg": ack})
            if ack.get("trnm") != "LOGIN" or int(ack.get("return_code") or 0) != 0:
                self.rest.invalidate_token()
                raise RuntimeError(f"WS 로그인 실패 code={ack.get('return_code')} "
                                   f"msg={ack.get('return_msg')}")
            await self._reg_all()
            while not self._pending.empty():      # 방금 전체 등록했으므로 대기분은 비운다
                self._pending.get_nowait()
            self.store.event("ws_connected", symbols=len(self.symbols),
                             reconnect=self.connected_once)
            if self.connected_once and self.on_reconnect:
                self.on_reconnect()
            self.connected_once = True
            adder = asyncio.create_task(self._adder())
            try:
                async for raw in ws:
                    if self._handle(raw) == "PING":
                        await ws.send(raw)
                    if self.stop.is_set():
                        break
            finally:
                adder.cancel()

    async def _adder(self):
        while True:
            new = await self._pending.get()
            for i in range(0, len(new), C.REG_CHUNK):
                await self._reg(new[i:i + C.REG_CHUNK], SYMBOL_TYPES)

    async def run(self):
        backoff = 1
        while not self.stop.is_set():
            t0 = time.monotonic()
            err = None
            try:
                await self._session()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - 끊김 사유를 전부 기록
                err = f"{type(e).__name__}: {e}"
            if self.stop.is_set():
                break
            down_at = now_kst()
            self.disconnects += 1
            self.store.event("ws_disconnect", err=err, up_s=round(time.monotonic() - t0, 1))
            backoff = 1 if time.monotonic() - t0 > 60 else min(backoff * 2, 60)
            try:
                await asyncio.wait_for(self.stop.wait(), backoff)
            except asyncio.TimeoutError:
                pass
            self._gap_from = down_at

    def note_gap_closed(self):
        """재접속 직후 호출: 단절 구간을 봉에 표시하고 길이를 누적."""
        a = getattr(self, "_gap_from", None)
        if a is None:
            return None
        b = now_kst()
        self._gap_from = None
        self.gap_s += (b - a).total_seconds()
        for bb in self.builders:
            bb.mark_gap(a, b)
        self.store.event("ws_gap", start=a.isoformat(), end=b.isoformat(),
                         seconds=round((b - a).total_seconds(), 1))
        return a, b

    async def close(self):
        self.stop.set()
        if self.ws is not None:
            await self.ws.close()
