# deejpad dashboard

Controller for a custom 5-slider / 8-button macro pad on **COM4**, with a browser dashboard to configure everything live.

## Run it

```
pip install -r requirements.txt
python run.py
```

The dashboard opens at **http://127.0.0.1:8420**. The app auto-reconnects to COM4 if the board drops out. Everything you configure is saved to `config.json`.

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
- **Macro pad** tab — per button: fire on press or release, hold-to-repeat for key combos, and an action:
  - Key combo (`ctrl+shift+v`), typed text, media key, launch a program, master mute, brightness up/down nudge, or a **multi-step sequence** (one step per line: `combo: …`, `text: …`, `delay: 0.2`, `launch: …`, `media: …`, `brightness_up: 10`)
  - `▶ Test` button to try actions without touching the hardware
- Header: serial port/baud settings, serial connection status, `Save`.

## Notes

- Only one program can hold COM4. Close any Arduino IDE serial monitor or other terminal using the port, or the app reports "access denied" and keeps retrying.
- Media keys recognize: `play`, `next`, `prev`, `stop`, `vol_up`, `vol_down`, `mute`.
- App volume uses Windows audio sessions via pycaw; app names are lowercase exe names (the dashboard shows which apps currently have audio running).
