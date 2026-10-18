"""Music page: player picker, Spotify/YouTube source, now playing, controls, playlists.

Works with any HA media_player. Music Assistant players get the extras
(playlists from sensor.desk_panel_playlists, radio mode) when the Desk Panel
HA package is installed; those controls hide themselves if it isn't.
"""
from __future__ import annotations

import time
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QListWidget,
                               QPushButton, QSlider, QVBoxLayout, QWidget)

ART = 96


def _fmt(sec: float) -> str:
    sec = max(0, int(sec))
    return f"{sec // 60}:{sec % 60:02d}"


class MusicPage(QWidget):
    def __init__(self, cfg: dict, store, client, base_url_fn, save_cfg_fn, parent=None):
        super().__init__(parent)
        self.cfg, self.store, self.client = cfg, store, client
        self.base_url_fn, self.save_cfg = base_url_fn, save_cfg_fn
        self.mcfg = cfg.setdefault("music", {})
        self._art_url = None
        self._seeking = False
        self._net = QNetworkAccessManager(self)
        self._net.finished.connect(self._art_loaded)

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(8)

        # row 1: speaker + source
        r1 = QHBoxLayout()
        self.player_cb = QComboBox()
        self.player_cb.setMinimumWidth(190)
        self.player_cb.currentIndexChanged.connect(self._player_picked)
        r1.addWidget(self.player_cb, 1)
        self.src_btns = {}
        for name, label in (("Spotify", "Spotify"), ("YouTube Music", "YouTube")):
            b = QPushButton(label, checkable=True)
            b.clicked.connect(lambda _=False, n=name: self._set_source(n))
            self.src_btns[name] = b
            r1.addWidget(b)
        root.addLayout(r1)

        # row 2: art + title
        r2 = QHBoxLayout()
        self.art = QLabel("🎵")
        self.art.setFixedSize(ART, ART)
        self.art.setAlignment(Qt.AlignCenter)
        self.art.setStyleSheet("border:1px solid #3A3D44; border-radius:10px; font-size:34px;")
        r2.addWidget(self.art)
        info = QVBoxLayout()
        self.title = QLabel("Nothing playing")
        self.title.setStyleSheet("font-size:15px; font-weight:600;")
        self.title.setWordWrap(True)
        self.artist = QLabel("")
        self.artist.setProperty("muted", True)
        info.addWidget(self.title)
        info.addWidget(self.artist)
        info.addStretch(1)
        r2.addLayout(info, 1)
        root.addLayout(r2)

        # progress
        self.prog = QSlider(Qt.Horizontal)
        self.prog.setRange(0, 1000)
        self.prog.sliderPressed.connect(lambda: setattr(self, "_seeking", True))
        self.prog.sliderReleased.connect(self._seek)
        root.addWidget(self.prog)
        tr = QHBoxLayout()
        self.t_el, self.t_rem = QLabel("0:00"), QLabel("--:--")
        for l in (self.t_el, self.t_rem):
            l.setProperty("muted", True)
        tr.addWidget(self.t_el)
        tr.addStretch(1)
        tr.addWidget(self.t_rem)
        root.addLayout(tr)

        # transport
        r3 = QHBoxLayout()
        self.shuffle_b = QPushButton("🔀", checkable=True)
        self.shuffle_b.clicked.connect(self._toggle_shuffle)
        prev_b = QPushButton("⏮")
        prev_b.clicked.connect(lambda: self._svc("media_previous_track"))
        self.play_b = QPushButton("▶")
        self.play_b.setObjectName("Primary")
        self.play_b.setMinimumWidth(64)
        self.play_b.clicked.connect(self._play_pause)
        next_b = QPushButton("⏭")
        next_b.clicked.connect(lambda: self._svc("media_next_track"))
        self.repeat_b = QPushButton("🔁", checkable=True)
        self.repeat_b.clicked.connect(self._cycle_repeat)
        for b in (self.shuffle_b, prev_b, self.play_b, next_b, self.repeat_b):
            b.setStyleSheet("font-size:16px;")
            r3.addWidget(b)
        root.addLayout(r3)

        # volume
        r4 = QHBoxLayout()
        r4.addWidget(QLabel("🔉"))
        self.vol = QSlider(Qt.Horizontal)
        self.vol.setRange(0, 100)
        self.vol.sliderReleased.connect(self._set_volume)
        r4.addWidget(self.vol, 1)
        self.vol_lbl = QLabel("--%")
        self.vol_lbl.setFixedWidth(40)
        r4.addWidget(self.vol_lbl)
        root.addLayout(r4)

        # radio
        r5 = QHBoxLayout()
        self.radio_track = QPushButton("📻 Track radio")
        self.radio_track.clicked.connect(lambda: self._radio("track"))
        self.radio_artist = QPushButton("📻 Artist radio")
        self.radio_artist.clicked.connect(lambda: self._radio("artist"))
        r5.addWidget(self.radio_track)
        r5.addWidget(self.radio_artist)
        root.addLayout(r5)

        # playlists
        ph = QHBoxLayout()
        self.pl_title = QLabel("Playlists")
        self.pl_title.setObjectName("Title")
        ph.addWidget(self.pl_title)
        ph.addStretch(1)
        self.pl_refresh = QPushButton("⟳")
        self.pl_refresh.setToolTip("Reload playlists from Music Assistant")
        self.pl_refresh.clicked.connect(
            lambda: self.client.fire_event("esphome.desk_panel_refresh_playlists"))
        ph.addWidget(self.pl_refresh)
        root.addLayout(ph)
        self.pl_list = QListWidget()
        self.pl_list.setToolTip("Double-click to play")
        self.pl_list.itemDoubleClicked.connect(self._play_playlist)
        root.addWidget(self.pl_list, 1)

        self._tick = QTimer(self, interval=1000, timeout=self._update_progress)
        self._tick.start()
        self.store.reloaded.connect(self._fill_players)
        self.store.changed.connect(self._maybe_new_player)
        self.rewire()

    # ── wiring ────────────────────────────────────────────────────────────
    @property
    def player(self) -> str:
        return self.mcfg.get("player", "")

    def rewire(self):
        """(Re)register watchers — called on start and whenever the main window rebuilds."""
        for eid in (self.player, self.mcfg.get("source_select"), self.mcfg.get("playlists_sensor")):
            if eid:
                self.store.watch(eid, self.refresh)
        self._fill_players()

    def _players(self) -> list[str]:
        mps = [e for e in self.store.states if e.startswith("media_player.")]
        # Music Assistant players first, then the rest
        mps.sort(key=lambda e: (self.store.attr(e, "mass_player_type") is None,
                                self.store.name(e).lower()))
        return mps

    def _fill_players(self):
        players = self._players()
        self.player_cb.blockSignals(True)
        self.player_cb.clear()
        for e in players:
            tag = "" if self.store.attr(e, "mass_player_type") else "  (not Music Assistant)"
            self.player_cb.addItem(self.store.name(e) + tag, e)
        idx = self.player_cb.findData(self.player)
        if idx < 0 and players:
            idx = 0
            self.mcfg["player"] = players[0]
        self.player_cb.setCurrentIndex(max(idx, 0))
        self.player_cb.blockSignals(False)
        self.store.watch(self.player, self.refresh)
        self.refresh()

    def _maybe_new_player(self, eid: str):
        if eid.startswith("media_player.") and self.player_cb.findData(eid) < 0:
            self._fill_players()

    def _player_picked(self, idx: int):
        eid = self.player_cb.itemData(idx)
        if eid and eid != self.player:
            self.mcfg["player"] = eid
            self.save_cfg()
            self.store.watch(eid, self.refresh)
            self.refresh()

    # ── rendering ─────────────────────────────────────────────────────────
    def refresh(self):
        p, st = self.player, self.store
        a = (st.get(p) or {}).get("attributes", {})
        state = st.state(p)
        self.title.setText(a.get("media_title") or ("Nothing playing" if state not in ("unavailable",) else "Player unavailable"))
        self.artist.setText(a.get("media_artist") or "")
        self.play_b.setText("⏸" if state == "playing" else "▶")
        self.shuffle_b.setChecked(bool(a.get("shuffle")))
        rep = a.get("repeat", "off")
        self.repeat_b.setChecked(rep in ("all", "one"))
        self.repeat_b.setText("🔂" if rep == "one" else "🔁")
        if not self.vol.isSliderDown() and a.get("volume_level") is not None:
            v = round(a["volume_level"] * 100)
            self.vol.setValue(v)
            self.vol_lbl.setText(f"{v}%")
        is_ma = a.get("mass_player_type") is not None
        self.radio_track.setVisible(is_ma)
        self.radio_artist.setVisible(is_ma)

        src_ent = self.mcfg.get("source_select")
        src = st.state(src_ent, "") if src_ent else ""
        have_src = bool(src_ent and st.get(src_ent))
        for name, b in self.src_btns.items():
            b.setVisible(have_src)
            b.setChecked(src == name)

        pl_ent = self.mcfg.get("playlists_sensor")
        names = (st.attr(pl_ent, "names") or "") if pl_ent else ""
        uris = (st.attr(pl_ent, "uris") or "") if pl_ent else ""
        pairs = [(n, u) for n, u in zip(names.split("\n"), uris.split("\n")) if n and u]
        have_pl = bool(pl_ent and st.get(pl_ent))
        for w in (self.pl_title, self.pl_refresh, self.pl_list):
            w.setVisible(have_pl)
        current = [self.pl_list.item(i).data(Qt.UserRole) for i in range(self.pl_list.count())]
        if [u for _, u in pairs] != current:
            self.pl_list.clear()
            for n, u in pairs:
                self.pl_list.addItem(n)
                self.pl_list.item(self.pl_list.count() - 1).setData(Qt.UserRole, u)
        self.pl_title.setText(f"Playlists · {src}" if src else "Playlists")

        pic = a.get("entity_picture_local") or a.get("entity_picture")
        if pic and not pic.startswith("http"):
            pic = self.base_url_fn().rstrip("/") + pic
        if pic != self._art_url:
            self._art_url = pic
            if pic:
                self._net.get(QNetworkRequest(QUrl(pic)))
            else:
                self.art.setPixmap(QPixmap())
                self.art.setText("🎵")
        self._update_progress()

    def _art_loaded(self, reply):
        if reply.url().toString() != (self._art_url or ""):
            reply.deleteLater()
            return
        pm = QPixmap()
        if reply.error() == reply.NetworkError.NoError and pm.loadFromData(reply.readAll()):
            self.art.setPixmap(pm.scaled(ART, ART, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        else:
            self.art.setText("🎵")
        reply.deleteLater()

    def _position(self) -> tuple[float, float]:
        a = (self.store.get(self.player) or {}).get("attributes", {})
        dur = float(a.get("media_duration") or 0)
        pos = float(a.get("media_position") or 0)
        upd = a.get("media_position_updated_at")
        if self.store.state(self.player) == "playing" and upd:
            try:
                pos += time.time() - datetime.fromisoformat(upd).timestamp()
            except ValueError:
                pass
        return min(max(pos, 0), dur) if dur else pos, dur

    def _update_progress(self):
        pos, dur = self._position()
        if not self._seeking:
            self.prog.setValue(int(pos * 1000 / dur) if dur else 0)
        self.t_el.setText(_fmt(pos))
        self.t_rem.setText(f"-{_fmt(dur - pos)}" if dur else "--:--")

    # ── actions ───────────────────────────────────────────────────────────
    def _svc(self, service: str, data: dict | None = None):
        self.client.call_service("media_player", service, data, entity_id=self.player)

    def _play_pause(self):
        state = self.store.state(self.player)
        if state in ("playing", "paused"):
            self._svc("media_play_pause")
            return
        # empty queue: start the first playlist of the current source (shuffled)
        if self.pl_list.count():
            self.client.call_service("media_player", "shuffle_set", {"shuffle": True}, entity_id=self.player)
            self._play_uri(self.pl_list.item(0).data(Qt.UserRole))
        else:
            self._svc("media_play")

    def _play_uri(self, uri: str):
        self.client.call_service("music_assistant", "play_media",
                                 {"media_id": uri, "media_type": "playlist", "enqueue": "replace"},
                                 entity_id=self.player)

    def _play_playlist(self, item):
        self._play_uri(item.data(Qt.UserRole))

    def _toggle_shuffle(self):
        self._svc("shuffle_set", {"shuffle": self.shuffle_b.isChecked()})

    def _cycle_repeat(self):
        cur = self.store.attr(self.player, "repeat", "off")
        self._svc("repeat_set", {"repeat": {"off": "all", "all": "one"}.get(cur, "off")})

    def _set_volume(self):
        v = self.vol.value()
        self.vol_lbl.setText(f"{v}%")
        self._svc("volume_set", {"volume_level": v / 100})

    def _seek(self):
        _, dur = self._position()
        if dur:
            self._svc("media_seek", {"seek_position": self.prog.value() * dur / 1000})
        self._seeking = False

    def _set_source(self, name: str):
        ent = self.mcfg.get("source_select")
        if ent:
            self.client.call_service("input_select", "select_option", {"option": name}, entity_id=ent)

    def _radio(self, mode: str):
        a = (self.store.get(self.player) or {}).get("attributes", {})
        if mode == "track" and a.get("media_content_id"):
            data = {"media_id": a["media_content_id"], "media_type": "track"}
        elif a.get("media_artist"):
            data = {"media_id": a["media_artist"], "media_type": "artist"}
        else:
            return
        self.client.call_service("music_assistant", "play_media",
                                 {**data, "radio_mode": True, "enqueue": "replace"}, entity_id=self.player)
