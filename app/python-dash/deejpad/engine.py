"""Core engine: owns serial link, applies slider mappings, detects button presses."""
import threading
import time

from . import actions, config as appconfig
from .serial_link import SerialLink, parse_line

APPLY_INTERVAL = 1.0 / 10        # apply mapped values at 10 Hz
DEBOUNCE = 3                     # ignore slider jumps smaller than this (raw counts)


class Engine:
    def __init__(self):
        self.cfg = appconfig.load()
        self.raw = [0] * 13
        self.pct = [0.0] * 5          # normalised 0..100
        self.buttons = [0] * 8
        self.held = {}                # button index -> combo being held
        self._lock = threading.Lock()
        self._applied = [None] * 5    # last value applied per slider
        self._link = SerialLink(self.cfg, self._on_line)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._apply_loop, daemon=True)
        self.dirty = False            # config needs saving (auto-calibration)

    # -------------------------------------------------- serial ingest

    def _on_line(self, text):
        values = parse_line(text)
        if values is None:
            return
        with self._lock:
            for i, v in enumerate(values):
                self.raw[i] = v
            self._normalise()
            for i in range(8):
                state = 1 if values[5 + i] else 0
                prev = self.buttons[i]
                self.buttons[i] = state
                if state != prev:
                    self._on_button_edge(i, state)

    def _normalise(self):
        sliders = self.cfg.get("sliders", [])
        for i, s in enumerate(sliders[:5]):
            lo = float(s.get("min", 0))
            hi = float(s.get("max", 888))
            if hi - lo < 1:
                hi = lo + 1
            raw = self.raw[i]
            if s.get("auto_calibrate") or self.cfg.get("auto_calibrate"):
                margin = 8
                changed = False
                if raw < lo - margin:
                    lo, changed = float(raw), True
                elif raw < lo:
                    lo, changed = float(raw), True
                if raw > hi + margin:
                    hi, changed = float(raw), True
                elif raw > hi:
                    hi, changed = float(raw), True
                if changed:
                    s["min"], s["max"] = int(lo), int(hi)
                    self.dirty = True
                    self.raw[i] = raw
            norm = (self.raw[i] - lo) / (hi - lo)
            norm = max(0.0, min(1.0, norm))
            if s.get("invert", True):
                norm = 1.0 - norm
            self.pct[i] = round(norm * 100, 1)

    def _on_button_edge(self, index, state):
        buttons = self.cfg.get("buttons", [])
        if index >= len(buttons):
            return
        b = buttons[index]
        action = b.get("action") or {}
        if action.get("type") == "none" or not action:
            if index in self.held:
                del self.held[index]
            return
        trigger = b.get("trigger", "press")
        is_press = state == 1
        if trigger == "press" and not is_press:
            if index in self.held:
                actions.combo_up(self.held.pop(index)["combo"])
            return
        if trigger == "release" and is_press:
            return
        t = action.get("type")
        v = action.get("value", "")
        if b.get("hold") and t == "combo" and is_press:
            self.held[index] = action
            actions.combo_down(str(v))
            return
        if index in self.held:
            del self.held[index]
        if t in ("combo", "media", "text", "launch", "mute", "brightness_up", "brightness_down"):
            actions.execute_steps([{"type": t, "value": v, "display": action.get("display", "all")}])
        elif t == "steps":
            steps = action.get("steps") or []
            if steps:
                actions.execute_steps(steps)
        elif t == "app_mute":
            for name in action.get("apps", []) or []:
                actions.toggle_app_mute(name)

    # -------------------------------------------------- apply loop

    def _apply_loop(self):
        while not self._stop.is_set():
            t0 = time.time()
            with self._lock:
                pct = list(self.pct)
                sliders = [dict(s) for s in self.cfg.get("sliders", [])[:5]]
            for i, s in enumerate(sliders):
                mode = s.get("mode", "none")
                if mode == "none":
                    self._applied[i] = None
                    continue
                if abs(pct[i] - (self._applied[i] if self._applied[i] is not None else -999)) < 0.5:
                    continue
                self._applied[i] = pct[i]
                if mode == "master":
                    actions.set_master_volume(pct[i])
                elif mode == "apps":
                    apps = s.get("apps") or []
                    if apps:
                        for name in apps:
                            actions.set_app_volume(name.lower(), pct[i])
                    else:
                        actions.set_master_volume(pct[i])
                elif mode == "brightness":
                    actions.set_brightness(pct[i], s.get("display", "all"))
                elif mode == "mute":
                    if self._applied[i] >= 99:
                        pass
            elapsed = time.time() - t0
            wait = max(0.0, APPLY_INTERVAL - elapsed)
            self._stop.wait(wait)

    # we keep mute handled via buttons; slider 'mute' mode is a pass-through no-op
    def start(self):
        self._link.start()
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._link.stop()

    def save_if_dirty(self):
        if self.dirty:
            appconfig.save(self.cfg)
            self.dirty = False

    def snapshot(self):
        with self._lock:
            raw = list(self.raw)
            pct = list(self.pct)
            buttons = list(self.buttons)
        state = {
            "connected": self._link.connected,
            "error": self._link.error,
            "raw": {"sliders": raw[:5], "buttons": raw[5:13]},
            "pct": pct,
            "buttons": buttons,
            "master": actions.master_state(),
            "apps": actions.active_app_names(),
            "brightness": actions.get_brightness(),
        }
        return state


engine = Engine()
