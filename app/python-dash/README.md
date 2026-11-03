# deejpad dashboard

Controller for a custom 5-slider / 8-button macro pad on **COM4**, with a browser dashboard to configure everything live.

## Run it

```
pip install -r requirements.txt
python run.py
```

The dashboard opens at **http://127.0.0.1:8420**. The app auto-reconnects to COM4 if the board drops out. Everything you configure is saved to `config.json`.

A **tray icon** lives in the system tray while the app runs:

- **Open dashboard** (also the double-click action) — starts the dashboard if needed, then opens a tab
- **Stop web dashboard** / **Start web dashboard** — shuts down or brings back the web UI only; the board keeps reading and applying volume / brightness / macro mappings regardless
- **Quit** — full shutdown

For autostart on login, put a shortcut to `pythonw.exe run.py` (working dir = this folder) into `shell:startup`.

## Hardware serial format

Your board sends one line per update, pipe-separated, 13 values:

```
slider1|slider2|slider3|slider4|slider5|btn1|btn2|btn3|btn4|btn5|btn6|btn7|btn8
```

- Sliders: raw `~888` = 0%, `0` = 100% (handled by the default **invert** + calibration).
- Buttons: `0` = up, `1` = pressed (fires once on the edge, not while held — unless "hold" mode).

## Dashboard features

- **Sliders** tab — per slider:
  - `None`, `Master volume`, `App volume` (list exe names like `spotify.exe`), or `Monitor brightness` (pick one monitor or all)
  - Invert toggle, live raw readout, `Capture min` / `Capture max` calibration buttons
  - Auto-calibration (on by default) widens the range as you move the sliders
- **Macro pad** tab — per button: fire on press or release, hold-to-hold (keyboard combos **and mouse buttons**), and an action:
  - Key combo (`ctrl+shift+v`, with a ⏺ key-recorder), typed text, media key, **mouse click** (left/right/middle and doubles via `left,2`), launch a program, master mute, brightness up/down nudge
  - **Launch program** — dropdown lists all currently running programs; just start typing if it's not shown
  - Media keys (`play`, `next`, `prev`, `stop`, `vol_up`, `vol_down`, `mute`) are sent via Windows SendInput so they work everywhere
  - **Multi-step sequence** — a visual step editor (`+ Add step`): send keys / mouse click / mouse down (hold) / mouse up / mouse move dx,dy / scroll / type text / media key / launch program / wait delay / mute / brightness nudge, reorderable with ▲▼ and removable with ✕. Steps run top to bottom when the button fires — so you can build mouse-button sequences (e.g. hold right + move) easily with **Mouse down (hold)** and **Mouse up** steps.
  - `▶ Test` button to try actions without touching the hardware
- Header: serial port/baud settings, serial connection status, `Save`.

## Default config

`config.default.json` holds the starter mapping and is used when no local `config.json` exists yet:

| Slider | Target |
|--------|--------|
| 1 | master volume |
| 2 | spotify.exe |
| 3 | brave / chrome / firefox / chromium / florp |
| 4 | discord / signal |
| 5 | all monitors' brightness |

Button 1 toggles the master mute. Calibrations default to raw 0–888 inverted (the board reads `~888` at 0%, `~0` at 100%).

## Compiling to an exe

```
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name deejpad ^
  --add-data "static;static" --add-data "config.default.json;." ^
  --collect-all pycaw --collect-all screen_brightness_control --collect-all pystray ^
  --collect-all keyboard --collect-all mouse --hidden-import comtypes.gen ^
  --hidden-import pystray._win32 run.py
```

Result: `dist/deejpad.exe` (single file, no console). Drop the exe anywhere; `config.json` lives next to the exe. The `deejpad.spec` file keeps the exact build settings.

## Notes

- Only one program can hold COM4. Close any Arduino IDE serial monitor or other terminal using the port, or the app reports "access denied" and keeps retrying.
- Media keys recognize: `play`, `next`, `prev`, `stop`, `vol_up`, `vol_down`, `mute`.
- App volume uses Windows audio sessions via pycaw; app names are lowercase exe names (the dashboard shows which apps currently have audio running).
