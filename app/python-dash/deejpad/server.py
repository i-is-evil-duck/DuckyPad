"""Web dashboard server (FastAPI): config API + live websocket + static UI."""
import asyncio
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from . import actions, config as appconfig
from .engine import engine

import os
import sys

app = FastAPI(title="deejpad")

STATIC_DIR = (
    os.path.join(sys._MEIPASS, "static")
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
    else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
)


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/api/config")
async def get_config():
    return engine.cfg


@app.post("/api/config")
async def set_config(cfg: dict):
    # keep serial settings applied to the link object (port/baud picked up on reconnect)
    for k in ("port", "baud", "poll_hz", "auto_calibrate"):
        if k in cfg:
            engine.cfg[k] = cfg[k]
    if "sliders" in cfg:
        for i, s in enumerate(cfg["sliders"][:5]):
            base = engine.cfg["sliders"][i]
            for key in ("mode", "apps", "display", "invert", "min", "max"):
                if key in s:
                    base[key] = s[key]
    if "buttons" in cfg:
        for i, b in enumerate(cfg["buttons"][:8]):
            base = engine.cfg["buttons"][i]
            for key in ("label", "trigger", "hold", "action"):
                if key in b:
                    base[key] = b[key]
    appconfig.save(engine.cfg)
    engine.dirty = False
    return {"ok": True}


@app.get("/api/monitors")
async def monitors():
    return {"monitors": actions.list_monitors()}


@app.get("/api/apps")
async def apps():
    return {"apps": actions.active_app_names()}


@app.get("/api/programs")
async def programs():
    return {"programs": actions.list_programs()}


@app.post("/api/test/button")
async def test_button(body: dict):
    """Execute a button action manually from the dashboard for testing."""
    action = body.get("action") or {}
    t = action.get("type", "none")
    v = action.get("value", "")
    if t == "none":
        return {"ok": False, "error": "no action"}
    if t == "steps":
        steps = action.get("steps") or []
        if steps:
            actions.execute_steps(steps)
        return {"ok": True}
    actions.execute_steps([{"type": t, "value": v, "display": action.get("display", "all")}])
    return {"ok": True}


@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    stop = asyncio.Event()

    async def sender():
        try:
            while not stop.is_set():
                try:
                    await ws.send_json(engine.snapshot())
                except Exception:
                    break
                if getattr(engine, "dirty", False):
                    engine.save_if_dirty()
                await asyncio.sleep(0.1)
        except Exception:
            pass

    task = asyncio.create_task(sender())
    try:
        while True:
            msg = await ws.receive_text()
            # client can request a config push or nothing; ignore unknown messages
            if msg == "save":
                appconfig.save(engine.cfg)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        stop.set()
        task.cancel()
