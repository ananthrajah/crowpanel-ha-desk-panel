"""Layout + settings storage.

Everything the user can change at runtime lives in one JSON file:
  %APPDATA%\\DeskPanelTray\\config.json   (Windows)
  ~/.config/DeskPanelTray/config.json    (elsewhere)

The HA access token is NOT stored here — it goes to Windows Credential Manager
via `keyring` (falls back to the JSON file only if no keyring backend exists).
"""
from __future__ import annotations

import copy
import json
import logging
import os
import sys
from pathlib import Path

from . import APP_ID

log = logging.getLogger(__name__)

CONFIG_VERSION = 2
KEYRING_SERVICE = APP_ID
KEYRING_USER = "ha_token"

# First-run layout: one empty page that is also shown on the CrowPanel.
# Add buttons with the "＋ Add" tile or ✎ Edit layout.
DEFAULT_CONFIG = {
    "config_version": CONFIG_VERSION,
    "ha_url": "http://homeassistant.local:8123",
    "pages": [
        {"name": "Page 1", "panel": True, "tiles": []},
    ],
    # CrowPanel home screen (firmware 3.2+, HA package 3.1+)
    "home": {"tiles": [], "timeout": 30, "temp_entity": ""},
    "music": {
        "enabled": True,
        "player": "",  # empty = first Music Assistant player found
        # entities created by the Desk Panel HA package (optional — features hide if missing)
        "source_select": "input_select.desk_panel_source",
        "playlists_sensor": "sensor.desk_panel_playlists",
    },
    "window": {"pinned": False, "columns": 3},
}


def config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    override = os.environ.get("DESKPANEL_CONFIG_DIR")
    d = Path(override) if override else base / APP_ID
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return config_dir() / "config.json"


def _merge_defaults(cfg: dict) -> dict:
    out = copy.deepcopy(DEFAULT_CONFIG)
    for k, v in cfg.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def load() -> dict:
    p = config_path()
    if not p.exists():
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        save(cfg)
        return cfg
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        cfg = _merge_defaults(raw)
        if raw.get("config_version", 1) < 2:  # v0.1 → v0.2: first two pages go on the CrowPanel
            for page in cfg.get("pages", [])[:2]:
                page.setdefault("panel", True)
            cfg["config_version"] = 2
            save(cfg)
        return cfg
    except Exception as e:  # corrupt file: keep a copy, start fresh
        log.error("config.json unreadable (%s) — backing up and using defaults", e)
        p.rename(p.with_suffix(".broken.json"))
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        save(cfg)
        return cfg


def save(cfg: dict) -> None:
    p = config_path()
    tmp = p.with_suffix(".tmp")
    data = {k: v for k, v in cfg.items() if k != "_token_fallback" or v}
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)  # atomic on Windows + POSIX


# ── token storage ──────────────────────────────────────────────────────────
def get_token(cfg: dict) -> str:
    env = os.environ.get("DESKPANEL_TOKEN")
    if env:
        return env
    try:
        import keyring
        t = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
        if t:
            return t
    except Exception as e:
        log.warning("keyring unavailable: %s", e)
    return cfg.get("_token_fallback", "")


def set_token(cfg: dict, token: str) -> bool:
    """Returns True if stored in Credential Manager, False if it fell back to the file."""
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, KEYRING_USER, token)
        cfg.pop("_token_fallback", None)
        return True
    except Exception as e:
        log.warning("keyring unavailable (%s) — storing token in config.json", e)
        cfg["_token_fallback"] = token
        return False
