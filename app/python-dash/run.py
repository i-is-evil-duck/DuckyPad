"""Start deejpad: web dashboard at http://127.0.0.1:8420 + system-tray icon."""
import os
import sys
import threading
import webbrowser

# pythonw.exe (used for startup without a console) has no stdout/stderr; print() would crash
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import uvicorn

from deejpad.engine import engine
from deejpad.server import app

HOST = "127.0.0.1"
PORT = 8420
URL = f"http://{HOST}:{PORT}"

_icon = None
_browser_opened = False


def _make_icon():
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, 62, 62], 10, fill=(27, 30, 39, 255), outline=(78, 161, 255, 255), width=2)
    heights = [14, 24, 34, 44, 54]
    for i, x in enumerate([7, 17, 27, 37, 47]):
        h = heights[i]
        d.rounded_rectangle([x, 58 - h, x + 9, 56], 3, fill=(139, 92, 246, 255))
    return img


def open_dashboard(icon=None, item=None):
    global _browser_opened
    webbrowser.open(URL)
    _browser_opened = True


def toggle_serial(icon=None, item=None):
    if engine.link_enabled:
        engine.stop_serial()
    else:
        engine.start_serial()


def _serial_label(_=None):
    return "Stop reading board" if engine.link_enabled else "Start reading board"


def quit_app(icon=None, item=None):
    try:
        engine.save_if_dirty()
        engine.stop()
    finally:
        if _icon is not None:
            _icon.stop()
        threading.Timer(0.5, lambda: os._exit(0)).start()


def main():
    engine.start()
    threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": HOST, "port": PORT, "log_level": "warning"},
        daemon=True,
    ).start()

    import pystray
    from PIL import Image

    menu = pystray.Menu(
        pystray.MenuItem("Open dashboard", open_dashboard, default=True),
        pystray.MenuItem(_serial_label, toggle_serial),
        pystray.MenuItem("Quit", quit_app),
    )
    icon = pystray.Icon("deejpad", _make_icon(), "DuckyPad deej", menu)
    global _icon
    _icon = icon

    threading.Timer(1.2, open_dashboard).start()
    icon.run()   # blocks until quit selected


if __name__ == "__main__":
    main()
