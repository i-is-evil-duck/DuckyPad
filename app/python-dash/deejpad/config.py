"""Configuration load/save for deejpad. Stored as config.json next to the app."""
import json
import os
import sys
import threading

def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)      # next to the .exe
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(_base_dir(), "config.json")
_DEFAULT_CFG_PATH = (
    os.path.join(sys._MEIPASS, "config.default.json")
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
    else os.path.join(_base_dir(), "config.default.json")
)
_lock = threading.Lock()

NUM_SLIDERS = 5
NUM_BUTTONS = 8


def defaults():
    sliders = []
    for i in range(NUM_SLIDERS):
        sliders.append({
            "id": i,
            "mode": "none",            # none | master | apps | brightness | mute
            "apps": [],                # exe names like ["chrome.exe"] (empty + mode=apps => all sessions? no: empty = master)
            "display": "all",          # monitor index (int) or "all" for brightness mode
            "invert": True,            # raw 888 at 0% -> invert so high raw = low output
            "min": 0,                  # raw value at one end (auto-calibrated)
            "max": 888,                # raw value at the other end
        })
    buttons = []
    for i in range(NUM_BUTTONS):
        buttons.append({
            "id": i,
            "label": f"B{i + 1}",
            "trigger": "press",        # press | release
            "hold": False,             # hold = send while held (only for combo type)
            "action": {"type": "none", "value": "", "steps": []},
        })
    return {
        "port": "COM4",
        "baud": 9600,
        "poll_hz": 30,
        "auto_calibrate": True,
        "sliders": sliders,
        "buttons": buttons,
    }


def load():
    path = CONFIG_PATH
    if not os.path.exists(path):
        path = _DEFAULT_CFG_PATH
    cfg = defaults()
    try:
        with open(path, "r", encoding="utf-8") as f:
            user = json.load(f)
        # shallow-merge top level, replace lists wholesale
        for k, v in user.items():
            if k in ("sliders", "buttons") and isinstance(v, list):
                base = cfg[k]
                for i, item in enumerate(v):
                    if i < len(base) and isinstance(item, dict):
                        if not isinstance(item.get("apps"), list):
                            item["apps"] = []
                        base[i].update(item)
            else:
                cfg[k] = v
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[config] failed to load {path}: {e}")
    cfg['port'] = cfg.get('port') or 'COM4'
    return cfg


def save(cfg):
    with _lock:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
