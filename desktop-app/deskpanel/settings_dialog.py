"""Connection + app settings."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
                               QLabel, QLineEdit, QSpinBox, QVBoxLayout)

from . import __version__, APP_ID
from . import config as configmod

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _launch_command() -> str:
    if getattr(sys, "frozen", False):  # PyInstaller .exe
        return f'"{sys.executable}"'
    from pathlib import Path
    exe = sys.executable.replace("python.exe", "pythonw.exe")
    launcher = Path(__file__).resolve().parent.parent / "run_deskpanel.py"
    return f'"{exe}" "{launcher}"'


def autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, APP_ID)
            return True
    except OSError:
        return False


def set_autostart(on: bool):
    if sys.platform != "win32":
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, APP_ID, 0, winreg.REG_SZ, _launch_command())
        else:
            try:
                winreg.DeleteValue(k, APP_ID)
            except OSError:
                pass


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Settings")
        self.resize(520, 300)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.url = QLineEdit(cfg.get("ha_url", ""))
        self.url.setPlaceholderText("http://192.168.1.10:8123")
        form.addRow("Home Assistant URL", self.url)
        self.token = QLineEdit(configmod.get_token(cfg))
        self.token.setEchoMode(QLineEdit.Password)
        self.token.setPlaceholderText("Long-lived access token")
        form.addRow("Access token", self.token)
        how = QLabel("HA → your profile (bottom-left) → Security → Long-lived access tokens → Create token.")
        how.setWordWrap(True)
        how.setProperty("muted", True)
        form.addRow("", how)
        self.cols = QSpinBox(minimum=2, maximum=6, value=cfg.get("window", {}).get("columns", 3))
        form.addRow("Buttons per row", self.cols)
        self.autostart = QCheckBox("Start Desk Panel when I sign in to Windows")
        self.autostart.setChecked(autostart_enabled())
        self.autostart.setEnabled(sys.platform == "win32")
        form.addRow("", self.autostart)
        lay.addLayout(form)
        ver = QLabel(f"Desk Panel Tray v{__version__}  ·  layout file: {configmod.config_path()}")
        ver.setProperty("muted", True)
        ver.setWordWrap(True)
        lay.addWidget(ver)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def apply(self) -> bool:
        """Write settings. Returns True if the connection details changed."""
        url, tok = self.url.text().strip(), self.token.text().strip()
        changed = url != self.cfg.get("ha_url") or tok != configmod.get_token(self.cfg)
        self.cfg["ha_url"] = url
        self.cfg.setdefault("window", {})["columns"] = self.cols.value()
        if tok:
            configmod.set_token(self.cfg, tok)
        set_autostart(self.autostart.isChecked())
        configmod.save(self.cfg)
        return changed
