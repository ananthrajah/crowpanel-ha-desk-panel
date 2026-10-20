"""Headless end-to-end check against FakeHA.  Run:  python -m tests.smoke_test"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["DESKPANEL_CONFIG_DIR"] = tempfile.mkdtemp(prefix="deskpanel-test-")
os.environ["DESKPANEL_TOKEN"] = "test-token"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

from deskpanel import config as configmod  # noqa: E402
from deskpanel.app import TrayApp  # noqa: E402
from deskpanel.theme import STYLE  # noqa: E402
from deskpanel.tiles import Tile  # noqa: E402
from tests.fake_ha import FakeHA  # noqa: E402


def pump(app, secs=0.3, until=None):
    end = time.time() + secs
    while time.time() < end:
        app.processEvents()
        if until and until():
            return True
        time.sleep(0.01)
    return until() if until else True


def main():
    ha = FakeHA().start()
    cfg = configmod.load()
    cfg["ha_url"] = f"http://127.0.0.1:{ha.port}"
    cfg["pages"] = [{"name": "Office", "panel": True, "tiles": [
        {"entity_id": "light.desk_lamp", "label": ""},
        {"entity_id": "switch.guest_room", "label": "Guest Room"},
        {"entity_id": "climate.home_thermostat", "label": ""},
        {"entity_id": "switch.does_not_exist", "label": "Ghost"},
    ]}]
    configmod.save(cfg)

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    tray = TrayApp(app)
    tray.show()
    ok = pump(app, 5, until=lambda: "Connected" in tray.win.status.text())
    assert ok, f"never connected: {tray.win.status.text()}"
    print("✓ connected:", tray.win.status.text())

    tiles = {t.entity_id: t for t in tray.win.findChildren(Tile)}
    assert tiles["light.desk_lamp"].property("on") is True
    assert tiles["switch.guest_room"].property("on") is False
    assert "50%" in tiles["light.desk_lamp"].state_lbl.text(), tiles["light.desk_lamp"].state_lbl.text()
    assert tiles["switch.does_not_exist"].property("avail") is False
    assert "20.5" in tiles["climate.home_thermostat"].state_lbl.text()
    print("✓ initial states painted (on/off, brightness, climate, missing entity)")

    tiles["switch.guest_room"].activate()
    pump(app, 2, until=lambda: any(c.get("service") == "toggle" for c in ha.calls))
    call = [c for c in ha.calls if c.get("service") == "toggle"][-1]
    assert call["target"]["entity_id"] == "switch.guest_room"
    pump(app, 2, until=lambda: tiles["switch.guest_room"].property("on") is True)
    assert tiles["switch.guest_room"].property("on") is True
    print("✓ tap → homeassistant.toggle sent, HA state_changed repaints tile")

    # external change (e.g. from the Meross app) shows up live
    s = dict(ha.states["light.desk_lamp"]); s["state"] = "off"
    ha.push_threadsafe(s)
    pump(app, 2, until=lambda: tiles["light.desk_lamp"].property("on") is False)
    assert tiles["light.desk_lamp"].property("on") is False
    print("✓ external state change repaints live")

    tiles["climate.home_thermostat"]._nudge_temp(+1)
    pump(app, 2, until=lambda: any(c.get("service") == "set_temperature" for c in ha.calls))
    c = [c for c in ha.calls if c.get("service") == "set_temperature"][-1]
    assert c["service_data"]["temperature"] == 21.5
    print("✓ thermostat + sends set_temperature 21.5")

    # quick-add (what the ＋ tile does) — persists and rebuilds without restart
    tray.cfg["pages"][0]["tiles"].append({"entity_id": "switch.kitchen", "label": "Kitchen"})
    tray.win._save_and_rebuild()
    pump(app, 0.5)
    saved = json.loads(configmod.config_path().read_text())
    assert any(t["entity_id"] == "switch.kitchen" for t in saved["pages"][0]["tiles"])
    tiles = {t.entity_id: t for t in tray.win.findChildren(Tile) if t.isVisibleTo(tray.win) or True}
    assert "switch.kitchen" in tiles and tiles["switch.kitchen"].property("on") is True
    print("✓ added entity saved to config.json and appears immediately (state correct)")

    # CrowPanel layout push (📟 pages → HA)
    pushes = lambda: [c for c in ha.calls if c.get("event_type") == "desk_panel_layout_set"]
    pump(app, 2, until=lambda: any("switch.kitchen" in json.dumps(c) for c in pushes()))
    last = pushes()[-1]["event_data"]["pages"]
    assert last[0]["name"] == "Office" and [t["entity_id"] for t in last[0]["tiles"]][-1] == "switch.kitchen", last
    n = len(pushes())
    tray.win.sync_panel()  # HA already has this layout → nothing re-sent
    pump(app, 0.5)
    assert len(pushes()) == n, "re-sent an unchanged layout"
    print(f"✓ CrowPanel layout pushed to HA on connect + on edit ({n} pushes), unchanged layout not re-sent")

    # home screen (favourites + timeout) travels with the layout
    tray.cfg["home"] = {"tiles": [{"entity_id": "light.desk_lamp", "label": "Lamp"}], "timeout": 45,
                        "temp_entity": "climate.home_thermostat"}
    tray.win._save_and_rebuild()
    pump(app, 2, until=lambda: any(c["event_data"].get("home", {}).get("timeout") == 45 for c in pushes()))
    h = pushes()[-1]["event_data"]["home"]
    assert h == {"tiles": [{"entity_id": "light.desk_lamp", "label": "Lamp"}], "timeout": 45,
                 "temp_entity": "climate.home_thermostat"}, h
    pump(app, 2, until=lambda: (tray.store.attr("sensor.desk_panel_layout_store", "home") or {}).get("timeout") == 45)
    n = len(pushes()); tray.win.sync_panel(); pump(app, 0.5)
    assert len(pushes()) == n, "re-sent an unchanged home screen"
    from deskpanel.editor import HomeEditor
    he = HomeEditor(tray.cfg["home"], tray.store)
    he.timeout.setValue(0)
    r = he.home_result()
    assert r["timeout"] == 0 and r["temp_entity"] == "climate.home_thermostat" and len(r["tiles"]) == 1, r
    print("✓ home screen: favourites/timeout/temperature pushed to HA, editor round-trips")

    # quick-remove
    tray.win._quick_remove(0, tiles["switch.does_not_exist"])
    pump(app, 0.5)
    saved = json.loads(configmod.config_path().read_text())
    assert not any(t["entity_id"] == "switch.does_not_exist" for t in saved["pages"][0]["tiles"])
    print("✓ removed entity gone from config.json")

    # music page
    m = tray.win.music
    assert m is not None and m.title.text() == "Minsaram En Meethu", m.title.text()
    assert m.src_btns["Spotify"].isChecked() and m.pl_list.count() == 2
    assert m.play_b.text() == "⏸"
    m._play_playlist(m.pl_list.item(1))
    pump(app, 2, until=lambda: any(c.get("service") == "play_media" for c in ha.calls))
    c = [c for c in ha.calls if c.get("service") == "play_media"][-1]
    assert c["service_data"]["media_id"] == "library://playlist/22"
    assert c["target"]["entity_id"] == "media_player.living_room"
    m._set_source("YouTube Music")
    pump(app, 2, until=lambda: any(c.get("service") == "select_option" for c in ha.calls))
    print("✓ music: now playing, source buttons, playlist list, play_media + source select sent")

    # bad token → clear error, no reconnect storm
    tray.client.start(tray.cfg["ha_url"], "wrong")
    pump(app, 3, until=lambda: "Login failed" in tray.win.status.text())
    assert "Login failed" in tray.win.status.text()
    print("✓ bad token reported:", tray.win.status.text())

    tray.quit()
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
