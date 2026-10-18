"""Main-thread cache of HA states; widgets subscribe per entity."""
from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import QObject, Signal


class StateStore(QObject):
    changed = Signal(str)   # entity_id
    reloaded = Signal()     # full state list replaced

    def __init__(self):
        super().__init__()
        self.states: dict[str, dict] = {}
        self._watchers: dict[str, list] = defaultdict(list)

    def get(self, entity_id: str) -> dict | None:
        return self.states.get(entity_id)

    def state(self, entity_id: str, default: str = "unavailable") -> str:
        s = self.states.get(entity_id)
        return s["state"] if s else default

    def attr(self, entity_id: str, key: str, default=None):
        s = self.states.get(entity_id)
        return (s or {}).get("attributes", {}).get(key, default)

    def name(self, entity_id: str) -> str:
        return self.attr(entity_id, "friendly_name") or entity_id

    def watch(self, entity_id: str, callback):
        self._watchers[entity_id].append(callback)

    def clear_watchers(self):
        self._watchers.clear()

    # slots wired to HAClient
    def on_states_loaded(self, states: dict):
        self.states = states
        self.reloaded.emit()
        for eid, cbs in list(self._watchers.items()):
            for cb in list(cbs):
                cb()

    def on_state_changed(self, entity_id: str, new_state):
        if new_state is None:
            self.states.pop(entity_id, None)
        else:
            self.states[entity_id] = new_state
        for cb in list(self._watchers.get(entity_id, ())):
            cb()
        self.changed.emit(entity_id)
