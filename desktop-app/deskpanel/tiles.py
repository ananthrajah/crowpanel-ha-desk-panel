"""Entity tiles. One class handles every domain; behaviour is picked by domain."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMenu, QToolButton,
                               QVBoxLayout)

from .theme import DOMAIN_ICON

TOGGLE_DOMAINS = {"light", "switch", "fan", "input_boolean", "automation", "siren",
                  "humidifier", "cover", "lock", "media_player"}
RUN_DOMAINS = {"scene": ("scene", "turn_on"), "script": ("script", "turn_on"),
               "button": ("button", "press"), "input_button": ("input_button", "press")}
ON_STATES = {"on", "open", "unlocked", "playing", "heat", "cool", "heat_cool", "auto",
             "dry", "fan_only", "home"}


def domain_of(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]


class Tile(QFrame):
    """Signals let the page/editor react to quick-edit actions from the right-click menu."""
    remove_requested = Signal(object)
    rename_requested = Signal(object)
    move_requested = Signal(object, int)  # tile, delta

    def __init__(self, tile_cfg: dict, store, client, parent=None):
        super().__init__(parent)
        self.cfg = tile_cfg
        self.entity_id = tile_cfg["entity_id"]
        self.domain = domain_of(self.entity_id)
        self.store, self.client = store, client
        self.setObjectName("Tile")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(132, 96)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)
        top = QHBoxLayout()
        self.icon = QLabel(DOMAIN_ICON.get(self.domain, "●"))
        self.icon.setStyleSheet("font-size: 20px;")
        top.addWidget(self.icon)
        top.addStretch(1)
        lay.addLayout(top)
        lay.addStretch(1)
        self.name_lbl = QLabel()
        self.name_lbl.setStyleSheet("font-size: 14px; font-weight: 600;")
        self.name_lbl.setWordWrap(True)
        lay.addWidget(self.name_lbl)
        self.state_lbl = QLabel()
        self.state_lbl.setProperty("muted", True)
        self.state_lbl.setStyleSheet("font-size: 12px;")
        lay.addWidget(self.state_lbl)

        if self.domain == "climate":  # inline − / + for the target temperature
            row = QHBoxLayout()
            for sign, txt in ((-1, "−"), (1, "+")):
                b = QToolButton(text=txt)
                b.setStyleSheet("font-size: 18px; font-weight: 600;")
                b.clicked.connect(lambda _=False, s=sign: self._nudge_temp(s))
                row.addWidget(b)
            top.addLayout(row)

        # optimistic UI: show the new state immediately, re-sync from HA shortly after
        self._resync = QTimer(self, singleShot=True, interval=2000, timeout=self.refresh)
        store.watch(self.entity_id, self.refresh)
        self.refresh()

    # ── rendering ─────────────────────────────────────────────────────────
    def refresh(self):
        st = self.store.get(self.entity_id)
        label = self.cfg.get("label") or self.store.name(self.entity_id)
        self.name_lbl.setText(label)
        if st is None:
            self._set_props(on=False, avail=False)
            self.state_lbl.setText("not found in HA")
            self.setToolTip(f"{self.entity_id}\nThis entity doesn't exist (or is disabled) in Home Assistant.")
            return
        s, a = st["state"], st.get("attributes", {})
        avail = s not in ("unavailable", "unknown") or self.domain in RUN_DOMAINS
        on = s in ON_STATES
        self._set_props(on=on and self.domain not in ("sensor",), avail=avail)
        self.state_lbl.setText(self._describe(s, a))
        self.setToolTip(f"{self.store.name(self.entity_id)}\n{self.entity_id}\n\n"
                        "Click: " + self._click_hint() +
                        ("\nScroll: brightness" if self.domain == "light" else "") +
                        "\nRight-click: rename / move / remove")

    def _describe(self, s: str, a: dict) -> str:
        d = self.domain
        if s in ("unavailable", "unknown"):
            return s
        if d == "light" and s == "on" and a.get("brightness") is not None:
            return f"On · {round(a['brightness'] / 2.55)}%"
        if d == "climate":
            cur, tgt = a.get("current_temperature"), a.get("temperature")
            parts = [s]
            if cur is not None:
                parts.append(f"{cur}°")
            if tgt is not None:
                parts.append(f"→ {tgt}°")
            return " · ".join(parts)
        if d in ("sensor",):
            unit = a.get("unit_of_measurement", "")
            return f"{s} {unit}".strip()
        if d == "media_player":
            title = a.get("media_title")
            return f"{s} · {title}" if title else s
        if d in RUN_DOMAINS:
            return "Tap to run"
        return s.capitalize()

    def _click_hint(self) -> str:
        if self.domain in RUN_DOMAINS:
            return "run"
        if self.domain in ("sensor", "binary_sensor", "climate", "camera"):
            return "nothing (display only)"
        if self.domain == "media_player":
            return "play / pause"
        return "toggle"

    def _set_props(self, on: bool, avail: bool):
        changed = self.property("on") != on or self.property("avail") != avail
        self.setProperty("on", on)
        self.setProperty("avail", avail)
        if changed:
            self.style().unpolish(self)
            self.style().polish(self)
            for w in self.findChildren(QLabel):
                w.style().unpolish(w)
                w.style().polish(w)

    # ── actions ───────────────────────────────────────────────────────────
    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton and self.rect().contains(ev.position().toPoint()):
            self.activate()
        super().mouseReleaseEvent(ev)

    def activate(self):
        d, eid = self.domain, self.entity_id
        if d in RUN_DOMAINS:
            dom, svc = RUN_DOMAINS[d]
            self.client.call_service(dom, svc, entity_id=eid)
            return
        if d == "media_player":
            self.client.call_service("media_player", "media_play_pause", entity_id=eid)
            return
        if d in ("lock",):
            svc = "unlock" if self.store.state(eid) == "locked" else "lock"
            self.client.call_service("lock", svc, entity_id=eid)
            return
        if d in TOGGLE_DOMAINS:
            self.client.call_service("homeassistant", "toggle", entity_id=eid)
            self._set_props(on=not bool(self.property("on")), avail=True)  # instant feedback
            self._resync.start()

    def wheelEvent(self, ev):
        if self.domain != "light":
            return super().wheelEvent(ev)
        step = 10 if ev.angleDelta().y() > 0 else -10
        self.client.call_service("light", "turn_on", {"brightness_step_pct": step}, entity_id=self.entity_id)
        ev.accept()

    def _nudge_temp(self, sign: int):
        tgt = self.store.attr(self.entity_id, "temperature")
        if tgt is None:
            return
        step = self.store.attr(self.entity_id, "target_temp_step") or 0.5
        self.client.call_service("climate", "set_temperature",
                                 {"temperature": round(float(tgt) + sign * float(step), 1)},
                                 entity_id=self.entity_id)

    def contextMenuEvent(self, ev):
        m = QMenu(self)
        for text, fn in (("Rename…", lambda: self.rename_requested.emit(self)),
                         ("Move left", lambda: self.move_requested.emit(self, -1)),
                         ("Move right", lambda: self.move_requested.emit(self, 1)),
                         ("Remove from page", lambda: self.remove_requested.emit(self))):
            act = QAction(text, m)
            act.triggered.connect(fn)
            m.addAction(act)
        m.exec(ev.globalPos())
