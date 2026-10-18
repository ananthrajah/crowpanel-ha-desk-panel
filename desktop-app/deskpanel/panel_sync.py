"""Push the CrowPanel layout (pages marked "Show on CrowPanel") to Home Assistant.

HA package 3.0.0 stores it in sensor.desk_panel_layout_store (survives restarts) and
publishes sensor.desk_panel_layout, which the CrowPanel (firmware 3.x) renders live.
"""
from __future__ import annotations

PANEL_PAGES = 4
PANEL_SLOTS = 12
STORE_ENTITY = "sensor.desk_panel_layout_store"
EVENT = "desk_panel_layout_set"


def panel_layout(cfg: dict) -> list[dict]:
    pages = [p for p in cfg.get("pages", []) if p.get("panel")][:PANEL_PAGES]
    return [{"name": p.get("name", ""),
             "tiles": [{"entity_id": t["entity_id"], "label": t.get("label", "")}
                       for t in p.get("tiles", [])[:PANEL_SLOTS]]}
            for p in pages]


def needs_push(cfg: dict, store) -> bool:
    current = store.attr(STORE_ENTITY, "pages")
    return current != panel_layout(cfg)


def push(cfg: dict, client) -> None:
    client.fire_event(EVENT, {"pages": panel_layout(cfg)})
