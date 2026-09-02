"""
Headless FastAPI Gateway Server for OpenHaptic-Roleplay (v4.0)
Decoupled Architecture:
- Exposes CORS-enabled REST & WebSocket APIs for any independent frontend (Vue 3 / React)
- Mounts production built static files from 'frontend/dist' if available
"""

import os
import json
import asyncio
import logging
from typing import Optional, Callable
import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .webrtc_manager import WebRTCManager
from ..core.config_manager import global_config_mgr

logger = logging.getLogger("WebServer")


class WebRTCOfferPayload(BaseModel):
    sdp: str
    type: str


class CommandPayload(BaseModel):
    action: str
    channel: int = 0
    power: float = 0.0
    decay_ms: int = 400


class ModePayload(BaseModel):
    mode: str


def create_app(
    webrtc_mgr: WebRTCManager,
    on_command: Optional[Callable[[dict], None]] = None,
    on_mode_switch: Optional[Callable[[str], None]] = None
) -> FastAPI:
    app = FastAPI(title="OpenHaptic Headless API Engine v4.0")

    # Enable full CORS for local Vue/React dev server (e.g. localhost:5173)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    frontend_dist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")

    active_websockets = set()
    latest_jpeg_frame = None

    # 1. Phone Camera Minimal WebRTC Route (Always served)
    @app.get("/phone", response_class=HTMLResponse)
    async def phone():
        phone_html_path = os.path.join(static_dir, "phone.html")
        with open(phone_html_path, "r", encoding="utf-8") as f:
            return f.read()

    # 2. WebRTC SDP Negotiation API
    @app.post("/api/webrtc_offer")
    async def webrtc_offer(payload: WebRTCOfferPayload):
        answer = await webrtc_mgr.handle_offer(payload.sdp, payload.type)
        return answer

    # 3. Action Command API
    @app.post("/api/command")
    async def handle_command(cmd: CommandPayload):
        if on_command:
            on_command(cmd.dict())
        return {"status": "ok"}

    # 3.1 Global Settings API
    @app.get("/api/settings")
    async def get_settings():
        return global_config_mgr.get_dict()

    @app.post("/api/settings")
    async def update_settings(payload: dict):
        success = global_config_mgr.save(payload)
        return {"status": "ok" if success else "error"}

    # 4. Mode Switch API
    @app.post("/api/switch_mode")
    async def handle_mode(payload: ModePayload):
        if on_mode_switch:
            on_mode_switch(payload.mode)
        return {"status": "ok", "mode": payload.mode}

    # 5. High-Frequency Realtime WebSocket Broadcast
    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        active_websockets.add(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            active_websockets.discard(ws)

    # 6. MJPEG Stream Route
    def gen_frames():
        nonlocal latest_jpeg_frame
        while True:
            if latest_jpeg_frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + latest_jpeg_frame + b'\r\n')
            import time
            time.sleep(0.033)

    @app.get("/video_feed")
    def video_feed():
        return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

    # 7. Auto-Mount Built Vue 3 Frontend if 'frontend/dist' exists
    if os.path.exists(frontend_dist_dir):
        app.mount("/", StaticFiles(directory=frontend_dist_dir, html=True), name="frontend")
    else:
        # Fallback to legacy static index if not yet compiled
        @app.get("/", response_class=HTMLResponse)
        async def fallback_index():
            with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
                return f.read()

    app.state.broadcast_telemetry = lambda data: asyncio.create_task(
        _broadcast_json(active_websockets, data)
    )
    
    def set_annotated_frame(frame: np.ndarray):
        nonlocal latest_jpeg_frame
        ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if ret:
            latest_jpeg_frame = buf.tobytes()

    app.state.set_annotated_frame = set_annotated_frame
    return app


async def _broadcast_json(websockets, data):
    msg = json.dumps(data)
    to_remove = set()
    for ws in list(websockets):
        try:
            await ws.send_text(msg)
        except Exception:
            to_remove.add(ws)
    websockets.difference_update(to_remove)