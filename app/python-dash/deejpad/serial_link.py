"""Serial reader thread for the deejpad hardware.

Expected line format (pipe separated):
    slider1|slider2|slider3|slider4|slider5|button1|...|button8
i.e. 13 integers. Lines with only the 5 sliders are also accepted.
"""
import threading
import time

import serial


class SerialLink:
    def __init__(self, cfg, on_line):
        self.cfg = cfg
        self.on_line = on_line          # callback(list_of_ints)
        self.connected = False
        self.error = ""
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        ser = None
        while not self._stop.is_set():
            try:
                if ser is None:
                    port = self.cfg.get("port", "COM4")
                    baud = int(self.cfg.get("baud", 9600))
                    ser = serial.Serial(port, baud, timeout=1)
                    ser.reset_input_buffer()
                    self.connected = True
                    self.error = ""
                    print(f"[serial] connected {port} @ {baud}")
                line = ser.readline()
                if line:
                    try:
                        text = line.decode("ascii", "ignore").strip()
                    except Exception:
                        text = ""
                    if text:
                        self.on_line(text)
            except Exception as e:
                self.connected = False
                self.error = str(e)
                if ser is not None:
                    try:
                        ser.close()
                    except Exception:
                        pass
                    ser = None
                    print(f"[serial] {e} - retrying in 3s")
                time.sleep(3)
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass


def parse_line(text):
    """Return list of ints, or None if the line isn't valid."""
    parts = [p.strip() for p in text.replace(",", "|").split("|")]
    if not parts or any(p == "" for p in parts):
        return None
    try:
        values = [int(float(p)) for p in parts]
    except ValueError:
        return None
    if len(values) < 5 or len(values) > 13:
        return None
    if len(values) < 13:
        values = values + [0] * (13 - len(values))
    return values
