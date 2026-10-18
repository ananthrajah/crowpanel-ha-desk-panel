"""The pop-up panel shown from the tray icon."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QScrollArea, QStackedWidget, QTabBar,
                               QToolButton, QVBoxLayout, QWidget)

from . import APP_NAME, __version__
from . import config as configmod
from . import dialogs
from .editor import EntityPicker, LayoutEditor
from . import panel_sync
from .music import MusicPage
from .settings_dialog import SettingsDialog
from .tiles import Tile

W, H = 480, 640


class AddTile(QFrame):
    def __init__(self, on_click, parent=None):
        super().__init__(parent)
        self.setObjectName("Tile")
        self.setMinimumSize(132, 96)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Add entities to this page")
        lay = QVBoxLayout(self)
        l = QLabel("＋\nAdd")
        l.setAlignment(Qt.AlignCenter)
        l.setProperty("muted", True)
        l.setStyleSheet("font-size: 15px;")
        lay.addWidget(l)
        self._cb = on_click

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._cb()


class PanelWindow(QWidget):
    def __init__(self, cfg, store, client, on_reconnect):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.cfg, self.store, self.client = cfg, store, client
        self._reconnect = on_reconnect
        self._drag: QPoint | None = None
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(W, H)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.root = QWidget(objectName="Root")
        outer.addWidget(self.root)
        lay = QVBoxLayout(self.root)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(8)

        # header
        hdr = QHBoxLayout()
        t = QLabel(APP_NAME)
        t.setObjectName("Title")
        hdr.addWidget(t)
        self.status = QLabel("…", objectName="Status")
        self.status.setStyleSheet("font-size: 11px;")
        hdr.addWidget(self.status, 1)
        self.pin_b = self._tool("📌", "Keep open (don't hide when clicking elsewhere)", self._toggle_pin, checkable=True)
        self.pin_b.setChecked(cfg.get("window", {}).get("pinned", False))
        for w in (self._tool("✎", "Edit layout", self.edit_layout),
                  self._tool("⚙", "Settings", self.open_settings),
                  self.pin_b,
                  self._tool("✕", "Hide", self.hide)):
            hdr.addWidget(w)
        lay.addLayout(hdr)

        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.setDrawBase(False)
        self.tabs.currentChanged.connect(lambda i: self.stack.setCurrentIndex(i))
        lay.addWidget(self.tabs)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)

        self.foot = foot = QLabel(f"v{__version__} · right-click a button to rename / move / remove")
        foot.setProperty("muted", True)
        foot.setStyleSheet("font-size: 10px;")
        lay.addWidget(foot)

        self.music: MusicPage | None = None
        self.rebuild()

    @staticmethod
    def _tool(txt, tip, fn, checkable=False):
        b = QToolButton(text=txt, toolTip=tip, checkable=checkable)
        b.setStyleSheet("font-size: 15px;")
        b.clicked.connect(fn)
        return b

    # ── layout from config ────────────────────────────────────────────────
    def rebuild(self):
        cur = self.tabs.currentIndex()
        self.store.clear_watchers()
        while self.tabs.count():
            self.tabs.removeTab(0)
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()
        self.music = None

        cols = max(2, int(self.cfg.get("window", {}).get("columns", 3)))
        for pi, page in enumerate(self.cfg.get("pages", [])):
            area = QScrollArea()
            area.setWidgetResizable(True)
            body = QWidget()
            grid = QGridLayout(body)
            grid.setSpacing(10)
            grid.setContentsMargins(2, 4, 2, 4)
            tiles = page.get("tiles", [])
            for i, tcfg in enumerate(tiles):
                tile = Tile(tcfg, self.store, self.client)
                tile.remove_requested.connect(lambda t, p=pi: self._quick_remove(p, t))
                tile.rename_requested.connect(lambda t, p=pi: self._quick_rename(p, t))
                tile.move_requested.connect(lambda t, d, p=pi: self._quick_move(p, t, d))
                grid.addWidget(tile, i // cols, i % cols)
            n = len(tiles)
            grid.addWidget(AddTile(lambda p=pi: self._quick_add(p)), n // cols, n % cols)
            grid.setRowStretch(n // cols + 1, 1)
            area.setWidget(body)
            self.stack.addWidget(area)
            self.tabs.addTab(page["name"])

        if self.cfg.get("music", {}).get("enabled", True):
            self.music = MusicPage(self.cfg, self.store, self.client,
                                   lambda: self.cfg.get("ha_url", ""), lambda: configmod.save(self.cfg))
            self.stack.addWidget(self.music)
            self.tabs.addTab("🎵 Music")
        if self.tabs.count():
            self.tabs.setCurrentIndex(min(max(cur, 0), self.tabs.count() - 1))

    def _save_and_rebuild(self):
        configmod.save(self.cfg)
        self.rebuild()
        self.sync_panel()

    def sync_panel(self, force: bool = False):
        """Send the 📟 pages to HA for the CrowPanel when they differ from HA's copy."""
        if not self.store.states:
            return  # not connected yet — runs again when states arrive
        has_panel_pages = any(p.get("panel") for p in self.cfg.get("pages", []))
        if not has_panel_pages and self.store.get(panel_sync.STORE_ENTITY) is None:
            return
        if force or panel_sync.needs_push(self.cfg, self.store):
            panel_sync.push(self.cfg, self.client)
            from datetime import datetime
            self.foot.setText(f"v{__version__} · 📟 CrowPanel layout sent {datetime.now():%H:%M}")

    def _quick_add(self, page_idx):
        page = self.cfg["pages"][page_idx]
        dlg = EntityPicker(self.store, {t["entity_id"] for t in page["tiles"]}, self)
        if self._exec(dlg):
            page["tiles"] += [{"entity_id": e, "label": ""} for e in dlg.selected()]
            self._save_and_rebuild()

    def _find(self, page_idx, tile):
        tiles = self.cfg["pages"][page_idx]["tiles"]
        return tiles, tiles.index(tile.cfg)

    def _quick_remove(self, page_idx, tile):
        tiles, i = self._find(page_idx, tile)
        tiles.pop(i)
        self._save_and_rebuild()

    def _quick_rename(self, page_idx, tile):
        tiles, i = self._find(page_idx, tile)
        cur = tiles[i].get("label") or self.store.name(tile.entity_id)
        name, ok = self._ask_text("Rename button", "Label (empty = HA name):", cur)
        if ok:
            tiles[i]["label"] = name.strip()
            self._save_and_rebuild()

    def _quick_move(self, page_idx, tile, d):
        tiles, i = self._find(page_idx, tile)
        j = i + d
        if 0 <= j < len(tiles):
            tiles[i], tiles[j] = tiles[j], tiles[i]
            self._save_and_rebuild()

    # ── dialogs ───────────────────────────────────────────────────────────
    def _exec(self, dlg) -> int:
        """Open a dialog in front of the panel. While it's open the panel stops being
        always-on-top (and never auto-hides), so the dialog can't end up behind it."""
        self._dialog_open = True
        was_top = bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
        visible = self.isVisible()
        if was_top:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            if visible:
                self.show()
        try:
            return dialogs.run(dlg, self if visible else None)
        finally:
            self._dialog_open = False
            if was_top:
                self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
                if visible:
                    self.show()
                    self.raise_()

    def _ask_text(self, title, label, text=""):
        self._dialog_open = True
        try:
            return dialogs.ask_text(self, title, label, text)
        finally:
            self._dialog_open = False

    def edit_layout(self):
        dlg = LayoutEditor(self.cfg, self.store, self)
        if self._exec(dlg):
            pages, music_on = dlg.result_config()
            self.cfg["pages"] = pages
            self.cfg.setdefault("music", {})["enabled"] = music_on
            self._save_and_rebuild()

    def open_settings(self):
        dlg = SettingsDialog(self.cfg, self)
        if self._exec(dlg):
            if dlg.apply():
                self._reconnect()
            self.rebuild()

    # ── status / behaviour ────────────────────────────────────────────────
    def set_status(self, level: str, msg: str):
        self.status.setText("● " + msg)
        self.status.setProperty("level", level)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _toggle_pin(self):
        self.cfg.setdefault("window", {})["pinned"] = self.pin_b.isChecked()
        configmod.save(self.cfg)

    def show_near(self, anchor: QRect | None):
        scr = QGuiApplication.screenAt(anchor.center()) if anchor and anchor.isValid() else None
        avail = (scr or QGuiApplication.primaryScreen()).availableGeometry()
        x = avail.right() - self.width() - 12
        y = avail.bottom() - self.height() - 12
        if anchor and anchor.isValid() and anchor.top() < avail.center().y():  # taskbar at top
            y = avail.top() + 12
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def changeEvent(self, ev):
        super().changeEvent(ev)
        if ev.type() == ev.Type.ActivationChange and not self.isActiveWindow():
            QTimer.singleShot(150, self._maybe_autohide)

    def _maybe_autohide(self):
        """Hide when the user clicks elsewhere — but not while one of our dialogs is open."""
        if self.pin_b.isChecked() or not self.isVisible() or getattr(self, "_dialog_open", False):
            return
        aw = QApplication.activeWindow()
        if QApplication.activeModalWidget() is not None or (aw is not None and aw is not self):
            return
        if not self.isActiveWindow():
            self.hide()

    # drag the window by its header when pinned
    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton and ev.position().y() < 44:
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, ev):
        if self._drag is not None:
            self.move(ev.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, ev):
        self._drag = None
