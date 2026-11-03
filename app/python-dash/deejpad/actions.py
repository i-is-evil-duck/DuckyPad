"""System control: master/per-app volume, monitor brightness, macros."""
import os
import shutil
import time
import threading

import psutil

# ---------------------------------------------------------------- volume

_master = None
_master_ts = 0.0
_MASTER_TTL = 3600


def _get_master():
    global _master, _master_ts
    if _master is None or time.time() - _master_ts > _MASTER_TTL:
        from pycaw.pycaw import AudioUtilities
        # newer pycaw: GetSpeakers() returns an AudioDevice with an EndpointVolume property
        _master = AudioUtilities.GetSpeakers().EndpointVolume
        _master_ts = time.time()
    return _master


def set_master_volume(pct):
    try:
        _get_master().SetMasterVolumeLevelScalar(max(0.0, min(1.0, pct / 100.0)), None)
    except Exception as e:
        print(f"[volume] master error: {e}")


def toggle_master_mute():
    try:
        m = _get_master()
        m.SetMute(0 if m.GetMute() else 1, None)
    except Exception as e:
        print(f"[volume] mute error: {e}")


def master_state():
    try:
        m = _get_master()
        return {"volume": int(round(m.GetMasterVolumeLevelScalar() * 100)), "muted": bool(m.GetMute())}
    except Exception:
        return None


_proc_cache = {}
_proc_cache_lock = threading.Lock()


def _exe_name(pid):
    with _proc_cache_lock:
        hit = _proc_cache.get(pid)
        if hit and time.time() - hit[1] < 30:
            return hit[0]
    try:
        name = psutil.Process(pid).name().lower()
    except Exception:
        name = ""
    with _proc_cache_lock:
        _proc_cache[pid] = (name, time.time())
    return name


_proc_names_cache = None
_proc_names_ts = 0.0


def active_app_names():
    """Lowercase exe names of apps with active audio sessions."""
    global _proc_names_cache, _proc_names_ts
    if _proc_names_cache is not None and time.time() - _proc_names_ts < 3:
        return _proc_names_cache
    names = []
    try:
        from pycaw.pycaw import AudioUtilities
        for s in AudioUtilities.GetAllSessions():
            if s.Process is not None:
                n = _exe_name(s.Process.pid)
                if n and n not in names:
                    names.append(n)
    except Exception:
        pass
    _proc_names_cache = names
    _proc_names_ts = time.time()
    return names


def _session_volume_for(name):
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    for s in AudioUtilities.GetAllSessions():
        if s.Process is not None and _exe_name(s.Process.pid) == name:
            return s._ctl.QueryInterface(ISimpleAudioVolume)
    return None


def set_app_volume(name, pct):
    try:
        v = _session_volume_for(name)
        if v is not None:
            v.SetMasterVolume(max(0.0, min(1.0, pct / 100.0)), None)
    except Exception as e:
        print(f"[volume] {name} error: {e}")


def toggle_app_mute(name):
    try:
        v = _session_volume_for(name)
        if v is not None:
            v.SetMute(0 if v.GetMute() else 1, None)
    except Exception as e:
        print(f"[volume] {name} mute error: {e}")


_proc_cache_ts = 0.0
_programs_cache = None


def list_programs():
    """Unique exe names of installed/running programs, system processes filtered out."""
    global _programs_cache, _proc_cache_ts
    if _programs_cache is not None and time.time() - _proc_cache_ts < 10:
        return _programs_cache
    out = set()
    for p in psutil.process_iter(["name", "exe"]):
        try:
            exe = (p.info.get("exe") or "").lower().replace("/", "\\")
            if not exe or exe.startswith("c:\\windows\\"):
                continue
            name = p.info.get("name")
            if name:
                out.add(name.lower())
        except Exception:
            continue
    _programs_cache = sorted(out)
    _proc_cache_ts = time.time()
    return _programs_cache


def _app_paths_lookup(name):
    """Windows App Paths registry: how the Start menu resolves bare exe names."""
    import winreg, os as _os
    base = name[:-4] if name.lower().endswith(".exe") else name
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for key in (f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{base}.exe",
                    f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{base}"):
            try:
                k = winreg.OpenKey(root, key)
                val, _ = winreg.QueryValueEx(k, None)
                val = _os.path.expandvars(str(val).strip('"'))
                if _os.path.isfile(val):
                    return val
            except OSError:
                continue
    return None


def _find_lnk(name):
    """Find a matching Start Menu shortcut for the given program name."""
    import os as _os
    base = name.lower().removesuffix(".exe")
    prof = _os.environ.get("USERPROFILE", "")
    dirs = [
        _os.path.join(prof, "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs"),
        "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs",
    ]
    best = None
    for d in dirs:
        for root, _dirs, files in _os.walk(d):
            for f in files:
                low = f.lower()
                if low.endswith(".lnk") and (low == f"{base}.lnk" or low.startswith(f"{base}.")):
                    path = _os.path.join(root, f)
                    if best is None or len(path) < len(best):
                        best = path
    return best


def _launch(v):
    """Launch by name or path. Tries: direct path → App Paths → Start Menu shortcut → PATH."""
    import os as _os
    import subprocess
    v = str(v).strip()
    if not v:
        return
    if _os.path.isfile(v) or ("\\" in v or "/" in v):
        _os.startfile(v)
        return
    for cand in (_app_paths_lookup(v), _find_lnk(v)):
        if cand:
            _os.startfile(cand)
            return
    which = shutil.which(v) or shutil.which(f"{v}.exe")
    if which:
        subprocess.Popen([which])
        return
    _os.startfile(v)  # last resort – raise the original error


# ---------------------------------------------------------------- brightness

_sbc_lock = threading.Lock()
_last_brightness = {}          # display -> value
_last_write = 0.0


def list_monitors():
    try:
        import screen_brightness_control as sbc
        out = []
        for m in sbc.list_monitors_info():
            out.append({
                "index": m.get("index"),
                "name": m.get("name") or m.get("model") or f"Display {m.get('index')}",
                "serial": str(m.get("serial") or ""),
            })
        return out
    except Exception as e:
        print(f"[brightness] list error: {e}")
        return []


def set_brightness(value, display="all"):
    """value 0..100. display: int index or 'all'."""
    global _last_write
    with _sbc_lock:
        now = time.time()
        if now - _last_write < 0.05:
            return
        _last_write = now
    try:
        import screen_brightness_control as sbc
        disp = None if display == "all" else display
        key = "all" if display == "all" else display
        if _last_brightness.get(key) == value:
            return
        _last_brightness[key] = value
        sbc.set_brightness(int(max(0, min(100, value))), display=disp)
    except Exception as e:
        print(f"[brightness] set error: {e}")


def get_brightness(display=None):
    try:
        import screen_brightness_control as sbc
        vals = sbc.get_brightness(display=display)
        if vals:
            return vals[0]
    except Exception:
        pass
    return None


def nudge_brightness(delta, display="all"):
    try:
        import screen_brightness_control as sbc
        disp = None if display == "all" else display
        cur = get_brightness(disp)
        base = cur if cur is not None else 50
        set_brightness(max(0, min(100, base + delta)), display)
    except Exception as e:
        print(f"[brightness] nudge error: {e}")


# ---------------------------------------------------------------- mouse

MOUSE_BUTTONS = ("left", "right", "middle")


def _split_mouse(value):
    parts = [p.strip() for p in str(value or "").replace(" ", ",").split(",") if p.strip()]
    button = parts[0].lower() if parts and parts[0].lower() in MOUSE_BUTTONS else "left"
    return button, parts


def mouse_click(value="left"):
    import mouse
    button, parts = _split_mouse(value)
    clicks = 1
    if len(parts) > 1 and parts[1].isdigit() and int(parts[1]) > 0:
        clicks = int(parts[1])
    mouse.click(button, clicks)


def mouse_down(value="left"):
    import mouse
    mouse.press(_split_mouse(value)[0])


def mouse_up(value="left"):
    import mouse
    mouse.release(_split_mouse(value)[0])


def mouse_move(value):
    parts = [p.strip() for p in str(value or "0,0").split(",")][:2]
    dx = int(parts[0]) if parts and parts[0].lstrip("-").isdigit() else 0
    dy = int(parts[1]) if len(parts) > 1 and parts[1].lstrip("-").isdigit() else 0
    import mouse
    mouse.move(dx, dy, absolute=False, duration=0)


def mouse_wheel(value):
    parts = [p.strip() for p in str(value or "0").split(",")]
    n = float(parts[0]) if parts and parts[0].lstrip("-").replace(".", "", 1).isdigit() else 0.0
    import mouse
    mouse.wheel(n)


# ---------------------------------------------------------------- macros

KEY_ALIASES = {
    "play/pause": "play/pause", "playpause": "play/pause", "play": "play/pause", "pause": "play/pause",
    "next": "next", "nexttrack": "next",
    "prev": "prev", "previous": "prev", "prevtrack": "prev",
    "stop": "stop", "stopmedia": "stop",
    "vol_up": "volume_up", "volup": "volume_up", "volume_up": "volume_up",
    "vol_down": "volume_down", "voldown": "volume_down", "volume_down": "volume_down",
    "mute": "volume_mute", "volume_mute": "volume_mute",
}

# virtual-key codes (winuser.h): NEXT=0xB0, PREV=0xB1, STOP=0xB2, PLAY=0xB3,
# VOLUMEs 0xAD-0xAF. (0xB4-0xB7 are launch-mail/app1/app2 - not media keys.)
MEDIA_VK = {
    "play/pause": 0xB3, "play": 0xB3,
    "next": 0xB0, "prev": 0xB1, "stop": 0xB2,
    "volume_up": 0xAF, "volume_down": 0xAE, "volume_mute": 0xAD,
}
# extended-key scancodes — kept for reference/verification only (plain-VK path is the
# one that actually delivers proper extended media events on Windows)
MEDIA_SCAN = {0xB3: 0x22, 0xB0: 0x19, 0xB1: 0x10, 0xB2: 0x24}

def _normalise_key(k):
    k = (k or "").strip().lower().replace(" ", "_").replace("-", "_")
    return KEY_ALIASES.get(k, k)


def _send_vk(vk):
    """Send a press+release of a virtual key directly via SendInput."""
    import ctypes
    import ctypes.wintypes as wt
    PUL = ctypes.POINTER(ctypes.c_ulong)

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                    ("time", wt.DWORD), ("dwExtraInfo", PUL)]

    class INPUTUNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("padding", ctypes.c_ubyte * 32)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wt.DWORD), ("union", INPUTUNION)]

    def _event(flags):
        i = INPUT()
        i.type = 1  # INPUT_KEYBOARD
        i.union.ki.wVk = vk
        i.union.ki.dwFlags = flags
        return i

    arr = (INPUT * 2)(_event(0), _event(2))  # 0=down, 2=KEYEVENTF_KEYUP
    ctypes.windll.user32.SendInput(2, arr, ctypes.sizeof(INPUT))


def send_media(name):
    k = _normalise_key(name)
    vk = MEDIA_VK.get(k)
    if vk is None:
        return False
    _send_vk(vk)
    return True


def _do_combo(combo):
    import keyboard
    keys = [_normalise_key(k) for k in combo.replace(",", "+").split("+")]
    keys = [k for k in keys if k]
    if not keys:
        return
    if len(keys) == 1 and keys[0] in MEDIA_VK:
        # single media key names route through the VK path
        send_media(keys[0])
        return
    keyboard.send("+".join(keys))


def execute_steps(steps):
    thread = threading.Thread(target=_run_steps, args=(steps,), daemon=True)
    thread.start()


def _run_steps(steps):
    import keyboard
    if isinstance(steps, dict):
        steps = [steps]
    for step in steps:
        try:
            t = step.get("type", "combo")
            v = step.get("value", "")
            if t == "combo":
                _do_combo(str(v))
            elif t == "text":
                keyboard.write(str(v))
            elif t == "media":
                k = KEY_ALIASES.get(str(v).strip().lower(), "play/pause")
                if not send_media(k):
                    keyboard.send(k)
            elif t == "launch":
                _launch(v)
            elif t == "delay":
                time.sleep(float(v))
            elif t == "brightness_up":
                nudge_brightness(int(v) if str(v).strip() else 5, step.get("display", "all"))
            elif t == "brightness_down":
                nudge_brightness(-(int(v) if str(v).strip() else 5), step.get("display", "all"))
            elif t == "mute":
                toggle_master_mute()
            elif t == "mouse_click":
                mouse_click(v)
            elif t == "mouse_down":
                mouse_down(v)
            elif t == "mouse_up":
                mouse_up(v)
            elif t == "mouse_move":
                mouse_move(v)
            elif t == "wheel":
                mouse_wheel(v)
        except Exception as e:
            print(f"[macro] step {step} failed: {e}")


# hold support: send combo down / up
def combo_down(combo):
    import keyboard
    keys = [_normalise_key(k) for k in combo.replace(",", "+").split("+") if k]
    for k in keys:
        try:
            keyboard.press(k)
        except Exception:
            pass


def combo_up(combo):
    import keyboard
    keys = [_normalise_key(k) for k in combo.replace(",", "+").split("+") if k]
    for k in reversed(keys):
        try:
            keyboard.release(k)
        except Exception:
            pass
