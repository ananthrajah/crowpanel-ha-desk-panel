"""Entry point: tray icon, single-instance lock, HA connection."""
from __future__ import annotations

import logging
import os
import sys

from PySide6.QtCore import QLockFile, QRect, Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import APP_ID, APP_NAME, __version__
from . import config as configmod
from .ha_client import HAClient
from .store import StateStore
from .theme import GREEN, STYLE, WARN, ERROR
from .window import PanelWindow


def make_icon(color: str = GREEN) -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#0B0C0E"))
    p.setPen(QColor(color))
    p.drawRoundedRect(4, 4, 56, 56, 14, 14)
    p.setBrush(QColor(color))
    p.setPen(Qt.NoPen)
    for i, (x, y) in enumerate(((14, 14), (36, 14), (14, 36), (36, 36))):
        p.setOpacity(1.0 if i != 3 else 0.45)
        p.drawRoundedRect(x, y, 14, 14, 4, 4)
    p.end()
    return QIcon(pm)


class TrayApp:
    def __init__(self, app: QApplication):
        self.app = app
        self.cfg = configmod.load()
        self.store = StateStore()
        self.client = HAClient()
        self.client.states_loaded.connect(self.store.on_states_loaded)
        self.client.states_loaded.connect(lambda _s: self.win.sync_panel())
        self.client.state_changed.connect(self.store.on_state_changed)

        self.win = PanelWindow(self.cfg, self.store, self.client, self.connect)
        self.client.status.connect(self._status)

        self.icons = {"ok": make_icon(GREEN), "warn": make_icon(WARN), "error": make_icon(ERROR)}
        self.tray = QSystemTrayIcon(self.icons["warn"])
        self.tray.setToolTip(f"{APP_NAME} v{__version__}")
        menu = QMenu()
        for text, fn in (("Open", self.show), ("Edit layout…", lambda: (self.show(), self.win.edit_layout())),
                         ("Settings…", lambda: (self.show(), self.win.open_settings())), (None, None),
                         ("Reconnect", self.connect), ("Quit", self.quit)):
            if text is None:
                menu.addSeparator()
                continue
            a = QAction(text, menu)
            a.triggered.connect(fn)
            menu.addAction(a)
        self.menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._activated)
        self.tray.show()

        if not configmod.get_token(self.cfg):
            self.win.open_settings()  # first run: just the Settings window, centred
        self.connect()

    def connect(self):
        tok = configmod.get_token(self.cfg)
        if not tok or not self.cfg.get("ha_url"):
            self._status("error", "Not set up — open Settings (⚙)")
            return
        self.client.start(self.cfg["ha_url"], tok)

    def _status(self, level, msg):
        self.win.set_status(level, msg)
        self.tray.setIcon(self.icons.get(level, self.icons["warn"]))
        self.tray.setToolTip(f"{APP_NAME} — {msg}")

    def _activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.win.isVisible():
                self.win.hide()
            else:
                self.show()

    def show(self):
        self.win.show_near(self.tray.geometry() if self.tray.geometry().isValid() else QRect())

    def quit(self):
        self.client.stop()
        self.tray.hide()
        self.win.hide()
        self.app.quit()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_ID)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI", 10))

    lock = QLockFile(str(configmod.config_dir() / "instance.lock"))
    if not lock.tryLock(100):
        from .dialogs import info
        info(None, APP_NAME, "Desk Panel is already running — look for its icon in the system tray.")
        return 0
    if not QSystemTrayIcon.isSystemTrayAvailable():
        logging.warning("No system tray detected; showing the window instead")

    tray = TrayApp(app)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        tray.show()
    rc = app.exec()
    tray.client.stop()  # make sure the network thread is gone before Qt tears down
    # Everything is saved synchronously, so skip Qt/Python teardown (avoids rare
    # crash-on-exit dialogs from Qt objects being destroyed in the wrong order).
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)


if __name__ == "__main__":
    sys.exit(main())
