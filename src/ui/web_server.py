"""
FastAPI Dashboard & WebRTC Gateway Server for OpenHaptic-Roleplay (v2.0)
Endpoints:
- /api/webrtc_offer: WebRTC SDP Negotiation
- /video_feed: Real-time MJPEG debug stream
- /ws: Biometric telemetry broadcast
"""

import os
import json
import asyncio
import logging
from typing import Optional, Callable
import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .webrtc_manager import WebRTCManager

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
    app = FastAPI(title="OpenHaptic-Roleplay v2.0")

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Broadcast websocket connections
    active_websockets = set()
    latest_jpeg_frame = None

    @app.get("/", response_class=HTMLResponse)
    async def index():
        with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
            return f.read()

    @app.get("/phone", response_class=HTMLResponse)
    async def phone():
        with open(os.path.join(static_dir, "phone.html"), "r", encoding="utf-8") as f:
            return f.read()

    @app.post("/api/webrtc_offer")
    async def webrtc_offer(payload: WebRTCOfferPayload):
        answer = await webrtc_mgr.handle_offer(payload.sdp, payload.type)
        return answer

    @app.post("/api/command")
    async def handle_command(cmd: CommandPayload):
        if on_command:
            on_command(cmd.dict())
        return {"status": "ok"}

    @app.post("/api/switch_mode")
    async def handle_mode(payload: ModePayload):
        if on_mode_switch:
            on_mode_switch(payload.mode)
        return {"status": "ok", "mode": payload.mode}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        active_websockets.add(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            active_websockets.discard(ws)

    # Frame generator for debug UI
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
