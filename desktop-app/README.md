# Desk Panel Tray — v0.2.2

A Windows system-tray control panel for Home Assistant. It works alongside the CrowPanel
desk panel (same pages + a Music tab), but the layout lives in a settings file you edit **inside
the app**: add, remove, rename or reorder buttons and they appear instantly — nothing
to rebuild, nothing to flash.

## Get it running

1. **Create an HA token**
   In HA, click your profile (bottom-left) → **Security** → **Long-lived access tokens** →
   **Create token**. Name it `Desk Panel Tray` and copy it.
2. **Build the app** (needs Python 3.11+ from python.org, with "Add to PATH" ticked)
   Double-click **`build.bat`**. After a few minutes you get `dist\DeskPanel.exe`.
   (Or double-click **`run.bat`** to run straight from source without building.)
3. **Start it.** The first time, the Settings window opens:
   - **Home Assistant URL:** your HA's address, e.g. `http://192.168.1.10:8123` or `http://homeassistant.local:8123`.
     Your Nabu Casa `https://…ui.nabu.casa` URL also works when you're away from home.
   - **Access token:** paste the token from step 1. It's stored in **Windows Credential
     Manager**, not in a file.
   - Tick **Start Desk Panel when I sign in to Windows** if you want it at login.
4. Click the green icon in the system tray (you may need to drag it out of the `^`
   overflow area so it's always visible).

## Using it

| Action | How |
|---|---|
| Toggle a light/switch | Click its button (green = on, black = off) |
| Dim a light | Scroll the mouse wheel over its button |
| Thermostat | − / + on the button change the target temperature |
| Scene / script / button | Click to run |
| **Add buttons** | Click the **＋ Add** tile on any page → search → pick one or many |
| Rename / move / remove one button | **Right-click** the button |
| Add/rename/reorder/delete **pages**, bulk edits | **✎** in the header (Edit layout) |
| Keep the window open | **📌** in the header (then drag it by the header) |
| Music | Pick the speaker, Spotify/YouTube, playlists (double-click to play), seek, volume, radio |

Supported entity types: light, switch, fan, input_boolean, climate, scene, script, cover,
lock, sensor, binary_sensor, media_player, button, input_button, automation, humidifier,
vacuum.

Buttons for entities that don't exist (or are disabled) in HA show dashed with
"not found in HA", so a typo or a disabled Meross switch is obvious.

## Editing the CrowPanel from here

In **✎ Edit layout**, select a page and click **📟 On CrowPanel** (under the page list) so it
reads **YES** — up to 4 pages. Press
**Save** — the panel's first four tabs update within a second or two (first 12 buttons
of each page, 4×3). Rename, reorder, add or remove buttons the same way; nothing to flash.
Needs CrowPanel firmware 3.x and the HA package 3.0.0. The footer shows
"📟 CrowPanel layout sent HH:MM" after each update.

## Music tab

Works with any HA media player. The **Spotify/YouTube buttons, playlist list and refresh**
use the entities created by the Desk Panel HA package (`input_select.desk_panel_source`,
`sensor.desk_panel_playlists`) — the same ones the CrowPanel uses, so both stay in sync.
If the package isn't installed those controls simply hide.

## Where things are stored

- Layout & settings: `%APPDATA%\DeskPanelTray\config.json` (plain JSON — safe to back up
  or copy to another PC). Its path is shown at the bottom of **Settings**.
- HA token: Windows Credential Manager → *Windows Credentials* → `DeskPanelTray`.

## Testing (developers)

`python -m tests.smoke_test` runs the app headless against a fake Home Assistant and
checks connecting, painting states, toggling, live updates, the thermostat, adding/removing
buttons, the music page, and bad-token handling.
