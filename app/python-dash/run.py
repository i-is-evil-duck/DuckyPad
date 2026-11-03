"""Start deejpad: opens the dashboard at http://127.0.0.1:8420"""
import sys
import threading
import time
import webbrowser

# pythonw.exe (used for startup without a console) has no stdout/stderr; print() would crash
import os
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


def main():
    engine.start()
    threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": HOST, "port": PORT, "log_level": "warning"},
        daemon=True,
    ).start()
    time.sleep(1.0)
    print(f"deejpad dashboard: {URL}  (Ctrl+C to quit)")
    try:
        webbrowser.open(URL)
    except Exception:
        pass
    try:
        while True:
            time.sleep(1)
            engine.save_if_dirty()
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        print("bye")


if __name__ == "__main__":
    main()
