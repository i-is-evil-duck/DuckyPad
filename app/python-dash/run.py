"""Start deejpad: web dashboard at http://127.0.0.1:8420 + system-tray icon.

The tray item stops/starts ONLY the web dashboard; the board keeps reading and
applying volume / brightness / macros regardless.
"""
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
_server = None                 # uvicorn.Server instance (swappable)
_server_thread = None
_server_on = False
_server_lock = threading.Lock()


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


def server_running():
    return _server_on


def start_server(icon=None, item=None):
    global _server, _server_thread, _server_on
    with _server_lock:
        if _server_on:
            return
        cfg = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning", access_log=False)
        _server = uvicorn.Server(cfg)
        _server_on = True
        _server_thread = threading.Thread(target=_server.run, daemon=True)
        _server_thread.start()


def stop_server(icon=None, item=None):
    global _server_on
    global _server, _server_thread
    with _server_lock:
        if not _server_on:
            return
        _server_on = False
        srv = _server
        thr = _server_thread
    if srv is not None:
        srv.should_exit = True   # uvicorn exits gracefully on its own thread
    if thr is not None and thr.is_alive():
        thr.join(timeout=5)


def open_dashboard(icon=None, item=None):
    start_server()          # make sure it's running, then open a tab
    webbrowser.open(URL)


def _dash_label(_=None):
    return "Stop web dashboard" if _server_on else "Start web dashboard"


def quit_app(icon=None, item=None):
    try:
        engine.save_if_dirty()
        engine.stop()
        with _server_lock:
            _server_on = False
        if _server is not None:
            _server.should_exit = True
    finally:
        if _icon is not None:
            _icon.stop()
        threading.Timer(0.5, lambda: os._exit(0)).start()


def main():
    # board reading + applying volume/brightness/macros runs for the whole session
    engine.start()
    start_server()

    import pystray
    menu = pystray.Menu(
        pystray.MenuItem("Open dashboard", open_dashboard, default=True),
        pystray.MenuItem(_dash_label, lambda icon, item: (stop_server() if _server_on else start_server())),
        pystray.MenuItem("Quit", quit_app),
    )
    icon = pystray.Icon("deejpad", _make_icon(), "DuckyPad deej", menu)
    global _icon
    _icon = icon

    threading.Timer(1.2, lambda: webbrowser.open(URL)).start()
    icon.run()   # blocks until quit selected


if __name__ == "__main__":
    main()
