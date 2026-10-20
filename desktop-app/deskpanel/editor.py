"""Layout editor: pages (tabs) and the entities on them. Saves to config.json and the
main window rebuilds instantly — no restart, nothing to flash."""
from __future__ import annotations

import copy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout)

from . import dialogs

from .theme import DOMAIN_ICON
from .tiles import domain_of

ADDABLE = ["light", "switch", "fan", "input_boolean", "climate", "scene", "script",
           "cover", "lock", "sensor", "binary_sensor", "media_player", "button",
           "input_button", "automation", "humidifier", "vacuum"]


class EntityPicker(QDialog):
    """Search every HA entity by name or id, filter by type, pick one or many."""

    def __init__(self, store, exclude: set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add entities")
        self.resize(520, 560)
        self.store, self.exclude = store, exclude
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.q = QLineEdit(placeholderText="Search name or entity_id…  (e.g. guest, kitchen, light.)")
        self.q.textChanged.connect(self._fill)
        self.dom = QComboBox()
        self.dom.addItem("All types", "")
        for d in ADDABLE:
            self.dom.addItem(f"{DOMAIN_ICON.get(d, '●')} {d}", d)
        self.dom.currentIndexChanged.connect(self._fill)
        top.addWidget(self.q, 1)
        top.addWidget(self.dom)
        lay.addLayout(top)
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.ExtendedSelection)
        self.list.itemDoubleClicked.connect(lambda _: self.accept())
        lay.addWidget(self.list, 1)
        hint = QLabel("Tip: Ctrl/Shift-click to add several at once. Current state is shown in [brackets].")
        hint.setProperty("muted", True)
        lay.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Add")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._fill()
        self.q.setFocus()

    def _fill(self):
        q = self.q.text().strip().lower()
        d = self.dom.currentData()
        self.list.clear()
        rows = []
        for eid, s in self.store.states.items():
            dom = domain_of(eid)
            if dom not in ADDABLE or eid in self.exclude or (d and dom != d):
                continue
            name = s.get("attributes", {}).get("friendly_name", eid)
            if q and q not in eid.lower() and q not in name.lower():
                continue
            rows.append((name.lower(), name, eid, dom, s["state"]))
        for _, name, eid, dom, state in sorted(rows)[:400]:
            it = QListWidgetItem(f"{DOMAIN_ICON.get(dom, '●')}  {name}    —  {eid}   [{state}]")
            it.setData(Qt.UserRole, eid)
            self.list.addItem(it)

    def selected(self) -> list[str]:
        return [it.data(Qt.UserRole) for it in self.list.selectedItems()]


HOME_SLOTS = 8
DEFAULT_HOME = {"tiles": [], "timeout": 30, "temp_entity": ""}


class HomeEditor(QDialog):
    """CrowPanel home screen: favourite buttons, return-to-home timeout, temperature."""

    def __init__(self, home: dict, store, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CrowPanel home screen")
        self.resize(600, 560)
        self.store = store
        self.home = copy.deepcopy({**DEFAULT_HOME, **(home or {})})
        lay = QVBoxLayout(self)
        t = QLabel(f"Favourite buttons (up to {HOME_SLOTS})")
        t.setObjectName("Title")
        lay.addWidget(t)
        self.list = QListWidget()
        self.list.setDragDropMode(QListWidget.InternalMove)
        self.list.model().rowsMoved.connect(self._sync_order)
        self.list.itemDoubleClicked.connect(lambda _: self._rename())
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        for txt, fn in (("＋ Add", self._add), ("Rename", self._rename),
                        ("▲", lambda: self._move(-1)), ("▼", lambda: self._move(1)),
                        ("🗑 Remove", self._remove)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)

        form = QFormLayout()
        self.timeout = QSpinBox()
        self.timeout.setRange(0, 600)
        self.timeout.setSingleStep(5)
        self.timeout.setSuffix(" s")
        self.timeout.setSpecialValueText("never")
        self.timeout.setValue(int(self.home.get("timeout", 30)))
        form.addRow("Return to home after", self.timeout)
        self.temp = QComboBox()
        self.temp.addItem("(don't show)", "")
        temps = []
        for eid, st in store.states.items():
            a = st.get("attributes", {})
            if eid.startswith("climate.") or (eid.startswith("sensor.") and a.get("device_class") == "temperature"):
                temps.append((a.get("friendly_name", eid).lower(), a.get("friendly_name", eid), eid, st.get("state")))
        cur = self.home.get("temp_entity", "")
        if cur and cur not in {t[2] for t in temps}:
            temps.append((cur, cur, cur, "not in HA"))
        for _, name, eid, state in sorted(temps):
            self.temp.addItem(f"{name}  —  {eid}  [{state}]", eid)
        i = self.temp.findData(cur)
        self.temp.setCurrentIndex(i if i >= 0 else 0)
        form.addRow("Temperature shown", self.temp)
        lay.addLayout(form)
        hint = QLabel("The panel starts on this screen. Any page except Music goes back to it after the "
                      "time above without a touch (\"never\" turns that off). Shortcuts to every page are "
                      "added automatically. Changes reach the panel when you press Save in Edit layout.")
        hint.setWordWrap(True)
        hint.setProperty("muted", True)
        lay.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._fill()

    def _fill(self, select: int | None = None):
        self.list.clear()
        for t in self.home["tiles"]:
            eid = t["entity_id"]
            label = t.get("label") or self.store.name(eid)
            ok = self.store.get(eid) is not None
            it = QListWidgetItem(f"{DOMAIN_ICON.get(domain_of(eid), '●')}  {label}    —  {eid}"
                                 + ("" if ok else "   ⚠ not in HA"))
            it.setData(Qt.UserRole, t)
            self.list.addItem(it)
        if select is not None and 0 <= select < self.list.count():
            self.list.setCurrentRow(select)

    def _sync_order(self, *_):
        self.home["tiles"] = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]

    def _add(self):
        free = HOME_SLOTS - len(self.home["tiles"])
        if free <= 0:
            dialogs.info(self, "Home screen", f"The home screen holds {HOME_SLOTS} favourites. Remove one first.")
            return
        dlg = EntityPicker(self.store, {t["entity_id"] for t in self.home["tiles"]}, self)
        if dialogs.run(dlg, self):
            picked = dlg.selected()
            for eid in picked[:free]:
                self.home["tiles"].append({"entity_id": eid, "label": ""})
            if len(picked) > free:
                dialogs.info(self, "Home screen", f"Only the first {free} were added (limit {HOME_SLOTS}).")
            self._fill(len(self.home["tiles"]) - 1)

    def _rename(self):
        r = self.list.currentRow()
        if r < 0:
            return
        t = self.home["tiles"][r]
        name, ok = dialogs.ask_text(self, "Rename button", "Label (empty = HA name):",
                                    t.get("label") or self.store.name(t["entity_id"]))
        if ok:
            t["label"] = name.strip()
            self._fill(r)

    def _move(self, d):
        r = self.list.currentRow()
        tl = self.home["tiles"]
        if r >= 0 and 0 <= r + d < len(tl):
            tl[r], tl[r + d] = tl[r + d], tl[r]
            self._fill(r + d)

    def _remove(self):
        r = self.list.currentRow()
        if r >= 0:
            self.home["tiles"].pop(r)
            self._fill(min(r, len(self.home["tiles"]) - 1))

    def home_result(self) -> dict:
        return {"tiles": self.home["tiles"][:HOME_SLOTS], "timeout": self.timeout.value(),
                "temp_entity": self.temp.currentData() or ""}


class LayoutEditor(QDialog):
    def __init__(self, cfg: dict, store, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit layout")
        self.resize(720, 520)
        self.store = store
        self.pages = copy.deepcopy(cfg.get("pages", []))
        self.music_enabled = cfg.get("music", {}).get("enabled", True)
        self.home = copy.deepcopy({**DEFAULT_HOME, **(cfg.get("home") or {})})

        root = QHBoxLayout(self)
        # pages column
        left = QVBoxLayout()
        left.addWidget(self._title("Pages (tabs)"))
        self.page_list = QListWidget()
        self.page_list.currentRowChanged.connect(self._show_page)
        left.addWidget(self.page_list, 1)
        pb = QHBoxLayout()
        for txt, fn in (("＋", self._add_page), ("Rename", self._rename_page),
                        ("▲", lambda: self._move_page(-1)), ("▼", lambda: self._move_page(1)),
                        ("🗑", self._del_page)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            pb.addWidget(b)
        left.addLayout(pb)
        self.music_cb = QPushButton("🎵 Music tab: on", checkable=True, checked=self.music_enabled)
        self.music_cb.toggled.connect(lambda on: self.music_cb.setText(f"🎵 Music tab: {'on' if on else 'off'}"))
        self.music_cb.setText(f"🎵 Music tab: {'on' if self.music_enabled else 'off'}")
        left.addWidget(self.music_cb)
        self.panel_cb = QPushButton(checkable=True)
        self.panel_cb.setMinimumHeight(34)
        self.panel_cb.setToolTip("Show this page on the CrowPanel (up to 4 pages, first 12 buttons each)")
        self.panel_cb.toggled.connect(self._panel_toggled)
        self._panel_text(False)
        left.addWidget(self.panel_cb)
        self.home_btn = QPushButton()
        self.home_btn.setMinimumHeight(34)
        self.home_btn.setToolTip("Favourite buttons, return-to-home timeout and temperature for the CrowPanel home screen")
        self.home_btn.clicked.connect(self._edit_home)
        self._home_text()
        left.addWidget(self.home_btn)
        self.panel_info = QLabel()
        self.panel_info.setProperty("muted", True)
        self.panel_info.setWordWrap(True)
        left.addWidget(self.panel_info)
        root.addLayout(left, 2)

        # tiles column
        right = QVBoxLayout()
        self.tiles_title = self._title("Buttons on this page")
        right.addWidget(self.tiles_title)
        self.tile_list = QListWidget()
        self.tile_list.setDragDropMode(QListWidget.InternalMove)
        self.tile_list.model().rowsMoved.connect(self._sync_order)
        self.tile_list.itemDoubleClicked.connect(lambda _: self._rename_tile())
        right.addWidget(self.tile_list, 1)
        tb = QHBoxLayout()
        for txt, fn in (("＋ Add entities", self._add_tiles), ("Rename", self._rename_tile),
                        ("▲", lambda: self._move_tile(-1)), ("▼", lambda: self._move_tile(1)),
                        ("🗑 Remove", self._del_tile)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            tb.addWidget(b)
        right.addLayout(tb)
        hint = QLabel("Drag to reorder. Double-click to rename. Changes apply when you press Save.")
        hint.setProperty("muted", True)
        right.addWidget(hint)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        right.addWidget(bb)
        root.addLayout(right, 4)

        self._fill_pages()

    @staticmethod
    def _title(t):
        l = QLabel(t)
        l.setObjectName("Title")
        return l

    # home screen
    def _home_text(self):
        n, to = len(self.home.get("tiles", [])), int(self.home.get("timeout", 30))
        self.home_btn.setText(f"🏠 CrowPanel home screen…  ({n}/{HOME_SLOTS}, "
                              + ("no auto-return)" if to == 0 else f"back after {to} s)"))

    def _edit_home(self):
        dlg = HomeEditor(self.home, self.store, self)
        if dialogs.run(dlg, self):
            self.home = dlg.home_result()
            self._home_text()

    # pages
    def _fill_pages(self, select: int = 0):
        self.page_list.clear()
        for p in self.pages:
            mark = "📟 " if p.get("panel") else ""
            self.page_list.addItem(f"{mark}{p['name']}   ({len(p.get('tiles', []))})")
        if self.pages:
            self.page_list.setCurrentRow(max(0, min(select, len(self.pages) - 1)))
        else:
            self._show_page(-1)

    def _cur_page(self):
        r = self.page_list.currentRow()
        return self.pages[r] if 0 <= r < len(self.pages) else None

    def _add_page(self):
        name, ok = dialogs.ask_text(self, "New page", "Tab name:")
        if ok and name.strip():
            self.pages.append({"name": name.strip(), "tiles": []})
            self._fill_pages(len(self.pages) - 1)

    def _rename_page(self):
        p = self._cur_page()
        if not p:
            return
        name, ok = dialogs.ask_text(self, "Rename page", "Tab name:", p["name"])
        if ok and name.strip():
            p["name"] = name.strip()
            self._fill_pages(self.page_list.currentRow())

    def _move_page(self, d):
        r = self.page_list.currentRow()
        if 0 <= r + d < len(self.pages) and r >= 0:
            self.pages[r], self.pages[r + d] = self.pages[r + d], self.pages[r]
            self._fill_pages(r + d)

    def _del_page(self):
        p = self._cur_page()
        if p and dialogs.confirm(self, "Delete page",
                                 f"Delete the '{p['name']}' page and its {len(p['tiles'])} buttons?"):
            r = self.page_list.currentRow()
            self.pages.pop(r)
            self._fill_pages(r - 1)

    # tiles
    def _panel_count(self):
        return sum(1 for p in self.pages if p.get("panel"))

    def _panel_text(self, on):
        self.panel_cb.setText("📟 On CrowPanel: YES" if on else "📟 On CrowPanel: no  (click to add)")

    def _panel_toggled(self, on):
        self._panel_text(on)
        p = self._cur_page()
        if not p or bool(p.get("panel")) == on:
            return
        if on and self._panel_count() >= 4:
            dialogs.info(self, "CrowPanel", "The CrowPanel shows up to 4 pages. Untick another page first.")
            self.panel_cb.blockSignals(True)
            self.panel_cb.setChecked(False)
            self.panel_cb.blockSignals(False)
            self._panel_text(False)
            return
        p["panel"] = on
        self._fill_pages(self.page_list.currentRow())

    def _update_panel_info(self, p):
        n = self._panel_count()
        txt = f"CrowPanel pages used: {n}/4 (in tab order)."
        if p and p.get("panel") and len(p.get("tiles", [])) > 12:
            txt += f"  ⚠ This page has {len(p['tiles'])} buttons — the panel shows the first 12."
        self.panel_info.setText(txt)

    def _show_page(self, row):
        self.tile_list.clear()
        p = self._cur_page()
        self.panel_cb.blockSignals(True)
        self.panel_cb.setChecked(bool(p and p.get("panel")))
        self.panel_cb.setEnabled(p is not None)
        self.panel_cb.blockSignals(False)
        self._panel_text(bool(p and p.get("panel")))
        self._update_panel_info(p)
        self.tiles_title.setText(f"Buttons on '{p['name']}'" if p else "No page selected")
        if not p:
            return
        for t in p["tiles"]:
            eid = t["entity_id"]
            exists = self.store.get(eid) is not None
            label = t.get("label") or self.store.name(eid)
            it = QListWidgetItem(f"{DOMAIN_ICON.get(domain_of(eid), '●')}  {label}    —  {eid}"
                                 + ("" if exists else "   ⚠ not in HA"))
            it.setData(Qt.UserRole, t)
            self.tile_list.addItem(it)

    def _sync_order(self, *_):
        p = self._cur_page()
        if p:
            p["tiles"] = [self.tile_list.item(i).data(Qt.UserRole) for i in range(self.tile_list.count())]

    def _add_tiles(self):
        p = self._cur_page()
        if not p:
            dialogs.info(self, "Add entities", "Create a page first.")
            return
        dlg = EntityPicker(self.store, {t["entity_id"] for t in p["tiles"]}, self)
        if dialogs.run(dlg, self):
            for eid in dlg.selected():
                p["tiles"].append({"entity_id": eid, "label": ""})
            self._fill_pages(self.page_list.currentRow())

    def _rename_tile(self):
        p, r = self._cur_page(), self.tile_list.currentRow()
        if not p or r < 0:
            return
        t = p["tiles"][r]
        cur = t.get("label") or self.store.name(t["entity_id"])
        name, ok = dialogs.ask_text(self, "Rename button", "Label (empty = HA name):", cur)
        if ok:
            t["label"] = name.strip()
            self._show_page(None)
            self.tile_list.setCurrentRow(r)

    def _move_tile(self, d):
        p, r = self._cur_page(), self.tile_list.currentRow()
        if p and r >= 0 and 0 <= r + d < len(p["tiles"]):
            p["tiles"][r], p["tiles"][r + d] = p["tiles"][r + d], p["tiles"][r]
            self._show_page(None)
            self.tile_list.setCurrentRow(r + d)

    def _del_tile(self):
        p = self._cur_page()
        if not p:
            return
        rows = sorted({i.row() for i in self.tile_list.selectedIndexes()} or
                      ({self.tile_list.currentRow()} if self.tile_list.currentRow() >= 0 else set()), reverse=True)
        for r in rows:
            p["tiles"].pop(r)
        self._fill_pages(self.page_list.currentRow())

    def result_config(self) -> tuple[list, bool, dict]:
        return self.pages, self.music_cb.isChecked(), self.home
