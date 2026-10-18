"""Home Assistant WebSocket client running on its own thread + asyncio loop.

Talks to the UI only through Qt signals (thread-safe, queued), so the window
never blocks on the network. Reconnects automatically with backoff.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import itertools
import json
import logging
import threading

from PySide6.QtCore import QObject, Signal
from websockets.asyncio.client import connect

log = logging.getLogger(__name__)


def ws_url(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    if base.startswith("https://"):
        base = "wss://" + base[len("https://"):]
    elif base.startswith("http://"):
        base = "ws://" + base[len("http://"):]
    elif not base.startswith(("ws://", "wss://")):
        base = "ws://" + base
    return base + "/api/websocket"


class AuthError(Exception):
    pass


class HAClient(QObject):
    status = Signal(str, str)            # level ("ok"|"warn"|"error"), message
    states_loaded = Signal(dict)         # {entity_id: state_obj}
    state_changed = Signal(str, object)  # entity_id, state_obj (None = removed)

    def __init__(self):
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ws = None
        self._ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future] = {}
        self._url = ""
        self._token = ""
        self._stopping = False
        self._wake: asyncio.Event | None = None
        self._main_task: asyncio.Task | None = None

    def _emit(self, sig, *args):
        # never emit once stop() has begun: the Qt receivers may already be gone
        if not self._stopping:
            sig.emit(*args)

    # ── lifecycle ─────────────────────────────────────────────────────────
    def start(self, base_url: str, token: str):
        self.stop()
        self._url, self._token, self._stopping = ws_url(base_url), token, False
        self._thread = threading.Thread(target=self._thread_main, name="ha-ws", daemon=True)
        self._thread.start()

    def stop(self):
        self._stopping = True
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._shutdown)
        if self._thread:
            self._thread.join(timeout=5)
        self._thread = None
        self._loop = None

    def _shutdown(self):
        if self._wake:
            self._wake.set()
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()  # also aborts a pending connect / recv

    def _thread_main(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._main_task = self._loop.create_task(self._run_forever())
            self._loop.run_until_complete(self._main_task)
        except asyncio.CancelledError:
            pass
        finally:
            try:
                pending = asyncio.all_tasks(self._loop)
                for t in pending:
                    t.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            finally:
                self._loop.close()

    async def _run_forever(self):
        backoff = 1
        self._wake = asyncio.Event()
        while not self._stopping:
            try:
                await self._session()
                backoff = 1
            except AuthError as e:
                self._emit(self.status, "error", f"Login failed: {e}. Check the token in Settings.")
                return  # don't hammer HA with a bad token
            except Exception as e:  # network errors etc.
                if self._stopping:
                    break
                self._emit(self.status, "warn", f"Disconnected ({e.__class__.__name__}) — retrying in {backoff}s")
            for f in self._pending.values():
                if not f.done():
                    f.set_exception(ConnectionError("disconnected"))
            self._pending.clear()
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, 30)

    async def _session(self):
        self._emit(self.status, "warn", "Connecting to Home Assistant…")
        async with connect(self._url, max_size=None, ping_interval=30, open_timeout=10) as ws:
            self._ws = ws
            msg = json.loads(await ws.recv())
            if msg.get("type") != "auth_required":
                raise ConnectionError(f"unexpected hello {msg.get('type')}")
            await ws.send(json.dumps({"type": "auth", "access_token": self._token}))
            msg = json.loads(await ws.recv())
            if msg.get("type") != "auth_ok":
                raise AuthError(msg.get("message", "invalid token"))

            reader = asyncio.create_task(self._reader(ws))
            try:
                states = await self._request({"type": "get_states"})
                self._emit(self.states_loaded, {s["entity_id"]: s for s in states})
                await self._request({"type": "subscribe_events", "event_type": "state_changed"})
                self._emit(self.status, "ok", f"Connected · HA {msg.get('ha_version', '')}".strip())
                await reader
            finally:
                reader.cancel()
                self._ws = None

    async def _reader(self, ws):
        async for raw in ws:
            msg = json.loads(raw)
            # HA may coalesce messages into a JSON array
            for m in (msg if isinstance(msg, list) else [msg]):
                t = m.get("type")
                if t == "result":
                    fut = self._pending.pop(m.get("id"), None)
                    if fut and not fut.done():
                        if m.get("success"):
                            fut.set_result(m.get("result"))
                        else:
                            err = m.get("error") or {}
                            fut.set_exception(RuntimeError(err.get("message", "request failed")))
                elif t == "event":
                    ev = m.get("event", {})
                    if ev.get("event_type") == "state_changed":
                        d = ev.get("data", {})
                        self._emit(self.state_changed, d.get("entity_id"), d.get("new_state"))

    async def _request(self, payload: dict, timeout: float = 15):
        if self._ws is None:
            raise ConnectionError("not connected")
        mid = next(self._ids)
        fut = asyncio.get_running_loop().create_future()
        self._pending[mid] = fut
        await self._ws.send(json.dumps({"id": mid, **payload}))
        return await asyncio.wait_for(fut, timeout)

    # ── API used by the UI (any thread) ───────────────────────────────────
    def call_service(self, domain: str, service: str, data: dict | None = None,
                     entity_id: str | None = None) -> concurrent.futures.Future | None:
        if not self._loop or not self._loop.is_running():
            self._emit(self.status, "warn", "Not connected — command not sent")
            return None
        payload = {"type": "call_service", "domain": domain, "service": service,
                   "service_data": dict(data or {})}
        if entity_id:
            payload["target"] = {"entity_id": entity_id}
        fut = asyncio.run_coroutine_threadsafe(self._request(payload), self._loop)

        def _done(f):
            exc = f.exception()
            if exc:
                self._emit(self.status, "error", f"{domain}.{service} failed: {exc}")
        fut.add_done_callback(_done)
        return fut

    def fire_event(self, event_type: str, data: dict | None = None):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._request({"type": "fire_event", "event_type": event_type,
                               "event_data": data or {}}), self._loop)
