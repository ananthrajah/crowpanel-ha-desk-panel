# Changelog — Desk Panel Tray

## 0.3.0 — 2026-10-20
- **CrowPanel home screen.** Edit layout → "🏠 CrowPanel home screen…": pick up to 8 favourite
  buttons, how long an idle page waits before going back home (0 = never; the Music page
  never times out) and which temperature to show. Sent to HA with the pages
  (needs HA package 3.1.0 and panel firmware 3.2.0).

## 0.2.2 — 2026-10-18
- Public release clean-up: first run starts with one empty page and asks for your HA URL;
  no personal entities in the defaults.

## 0.2.1 — 2026-10-18
- Fix: the "Show on CrowPanel" tick box was invisible on Windows. It's now a toggle button
  under the page list ("📟 On CrowPanel: YES / no"); checkboxes elsewhere (Settings →
  Start with Windows) now draw a visible box that fills green when ticked.

## 0.2.0 — 2026-10-18
- **CrowPanel layout editing.** Tick "📟 Show this page on the CrowPanel" for up to 4 pages
  in Edit layout. On every save (and on connect) the app sends those pages (first 12
  buttons each) to HA; the panel (firmware 3.x + HA package 3.0.0) redraws within ~1 s.
  Unchanged layouts aren't re-sent.
- Existing configs are migrated: your first two pages are marked for the panel.
- Includes 0.1.1 (dialogs always in front of the panel) and a clean exit on Quit.

## 0.1.1 — 2026-10-17
- Fix: Settings (and every other dialog) could open *behind* the always-on-top panel and
  be unusable. All dialogs now open always-on-top, modal, centred and focused; the panel
  drops its always-on-top while a dialog is open and never auto-hides under one.
- First run opens only the Settings window (centred), not the panel behind it.

## 0.1.0 — 2026-10-17
First release.
- System-tray app with a pop-up panel (auto-hides when you click elsewhere, 📌 to pin).
- Live connection to Home Assistant over its WebSocket API; auto-reconnect with backoff;
  clear "Login failed" message on a bad token (no retry storm).
- Pages and buttons are defined in `config.json` and edited in the app:
  ＋ Add tile with entity search, right-click rename / move / remove, full layout editor
  (pages, drag-to-reorder). Changes apply instantly.
- Tiles for light (wheel = brightness), switch, fan, climate (−/+), scene, script, cover,
  lock, sensor, media_player and more; missing entities flagged.
- Music tab: speaker dropdown (Music Assistant players first), Spotify / YouTube source,
  album art, progress + seek, shuffle / repeat, volume, track & artist radio, playlists.
- Settings: HA URL, token in Windows Credential Manager, buttons per row, start with Windows.
