"""Minimal fake Home Assistant WebSocket API for offline testing."""
from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timezone

from websockets.asyncio.server import serve


def _st(eid, state, **attrs):
    return {"entity_id": eid, "state": state, "attributes": attrs,
            "last_changed": datetime.now(timezone.utc).isoformat()}


class FakeHA:
    TOKEN = "test-token"

    def __init__(self, port=0):
        self.port = port
        self.calls: list[dict] = []
        self.states = {s["entity_id"]: s for s in [
            _st("light.desk_lamp", "on", friendly_name="Desk Lamp", brightness=128),
            _st("switch.guest_room", "off", friendly_name="Guest room light Outlet"),
            _st("switch.kitchen", "on", friendly_name="Kitchen light Outlet"),
            _st("climate.home_thermostat", "heat", friendly_name="Thermostat",
                current_temperature=20.5, temperature=21.0, target_temp_step=0.5),
            _st("media_player.living_room", "playing", friendly_name="2nd floor Display",
                mass_player_type="player", media_title="Minsaram En Meethu", media_artist="A.R. Rahman",
                volume_level=0.7, shuffle=False, repeat="off", media_duration=300, media_position=10,
                media_position_updated_at=datetime.now(timezone.utc).isoformat()),
            _st("media_player.hass", "idle", friendly_name="Hass", mass_player_type="player"),
            _st("input_select.desk_panel_source", "Spotify", options=["Spotify", "YouTube Music", "Mixes"]),
            _st("sensor.desk_panel_playlists", "2", names="Liked Songs\nTamil Party Time",
                uris="library://playlist/14\nlibrary://playlist/22"),
        ]}
        self._clients = set()
        self._loop = None
        self.ready = threading.Event()

    def start(self):
        threading.Thread(target=self._main, daemon=True).start()
        self.ready.wait(5)
        return self

    def _main(self):
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._serve())

    async def _serve(self):
        async with serve(self._handler, "127.0.0.1", self.port) as server:
            self.port = server.sockets[0].getsockname()[1]
            self.ready.set()
            await asyncio.Future()

    async def _handler(self, ws):
        await ws.send(json.dumps({"type": "auth_required", "ha_version": "2026.10.0"}))
        auth = json.loads(await ws.recv())
        if auth.get("access_token") != self.TOKEN:
            await ws.send(json.dumps({"type": "auth_invalid", "message": "Invalid access token"}))
            return
        await ws.send(json.dumps({"type": "auth_ok", "ha_version": "2026.10.0"}))
        self._clients.add(ws)
        try:
            async for raw in ws:
                m = json.loads(raw)
                t, mid = m["type"], m.get("id")
                if t == "get_states":
                    await ws.send(json.dumps({"id": mid, "type": "result", "success": True,
                                              "result": list(self.states.values())}))
                elif t == "subscribe_events":
                    await ws.send(json.dumps({"id": mid, "type": "result", "success": True, "result": None}))
                elif t == "call_service":
                    self.calls.append(m)
                    await ws.send(json.dumps({"id": mid, "type": "result", "success": True,
                                              "result": {"context": {}}}))
                    await self._apply(m)
                elif t == "fire_event":
                    self.calls.append(m)
                    await ws.send(json.dumps({"id": mid, "type": "result", "success": True, "result": {}}))
                    if m.get("event_type") == "desk_panel_layout_set":  # what HA package 3.0 does
                        ed = m.get("event_data", {})
                        h = ed.get("home") or {}
                        await self.push(_st("sensor.desk_panel_layout_store", "2026-10-18T00:00:00",
                                            pages=ed.get("pages", []),
                                            home={"tiles": h.get("tiles", [])[:8],
                                                  "timeout": max(0, min(600, int(h.get("timeout", 30)))),
                                                  "temp_entity": h.get("temp_entity", "") or ""}))
        finally:
            self._clients.discard(ws)

    async def _apply(self, m):
        eid = (m.get("target") or {}).get("entity_id")
        if m["domain"] == "homeassistant" and m["service"] == "toggle" and eid in self.states:
            s = dict(self.states[eid])
            s["state"] = "off" if s["state"] == "on" else "on"
            await self.push(s)

    async def push(self, new_state):
        self.states[new_state["entity_id"]] = new_state
        ev = {"type": "event", "id": 2, "event": {"event_type": "state_changed",
              "data": {"entity_id": new_state["entity_id"], "new_state": new_state}}}
        for c in list(self._clients):
            await c.send(json.dumps(ev))

    def push_threadsafe(self, new_state):
        asyncio.run_coroutine_threadsafe(self.push(new_state), self._loop).result(3)
