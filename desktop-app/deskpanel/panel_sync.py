"""Push the CrowPanel layout to Home Assistant.

What is sent (event `desk_panel_layout_set`):
  pages: the pages marked "On CrowPanel" (up to 4, first 12 buttons each)
  home:  the CrowPanel home screen - up to 8 favourite buttons, seconds before an idle
         page returns home (0 = never) and the temperature entity to show.
HA package 3.1 stores it in sensor.desk_panel_layout_store (survives restarts) and
publishes sensor.desk_panel_layout, which the CrowPanel renders live.
"""
from __future__ import annotations

PANEL_PAGES = 4
PANEL_SLOTS = 12
HOME_SLOTS = 8
STORE_ENTITY = "sensor.desk_panel_layout_store"
EVENT = "desk_panel_layout_set"


def panel_layout(cfg: dict) -> list[dict]:
    pages = [p for p in cfg.get("pages", []) if p.get("panel")][:PANEL_PAGES]
    return [{"name": p.get("name", ""),
             "tiles": [{"entity_id": t["entity_id"], "label": t.get("label", "")}
                       for t in p.get("tiles", [])[:PANEL_SLOTS]]}
            for p in pages]


def home_layout(cfg: dict) -> dict:
    h = cfg.get("home") or {}
    try:
        timeout = int(h.get("timeout", 30))
    except (TypeError, ValueError):
        timeout = 30
    return {"tiles": [{"entity_id": t["entity_id"], "label": t.get("label", "")}
                      for t in h.get("tiles", [])[:HOME_SLOTS]],
            "timeout": max(0, min(600, timeout)),
            "temp_entity": h.get("temp_entity", "") or ""}


def needs_push(cfg: dict, store) -> bool:
    return (store.attr(STORE_ENTITY, "pages") != panel_layout(cfg)
            or store.attr(STORE_ENTITY, "home") != home_layout(cfg))


def push(cfg: dict, client) -> None:
    client.fire_event(EVENT, {"pages": panel_layout(cfg), "home": home_layout(cfg)})
