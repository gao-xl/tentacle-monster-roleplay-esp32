"""
FastAPI + WebSocket Web Dashboard & Mobile Stream Server for OpenHaptic-Roleplay
Serves the Cyberpunk HUD, streams annotated video, handles mobile camera upload with Gyro IMU,
and broadcasts real-time telemetry & AI dialogues.
"""

import os
import json
import time
import asyncio
import logging
import cv2
import numpy as np
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger("WebServer")

app = FastAPI(title="OpenHaptic-Roleplay Dashboard")

# Global Shared State Reference
shared_state = {
    "current_frame": None,          # Raw/Annotated BGR image
    "annotated_frame": None,
    "fused_state": None,            # FusedPlayerState
    "device_telemetry": None,       # DeviceTelemetry
    "ai_dialogues": [],             # List of recent dialogue lines
    "driver": None,                 # BaseDeviceDriver instance
    "phone_imu": None               # Latest IMUMotionData from phone
}

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

active_websockets: List[WebSocket] = []


class CommandPayload(BaseModel):
    action: str                     # "set", "hit", "wave", "stop"
    channel: int = 0
    power: float = 50.0
    decay_ms: int = 400
    freq_hz: float = 1.0


@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>OpenHaptic-Roleplay Dashboard</h1>"


@app.get("/phone", response_class=HTMLResponse)
async def get_phone_page():
    phone_path = os.path.join(STATIC_DIR, "phone.html")
    if os.path.exists(phone_path):
        with open(phone_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Mobile Stream Client</h1>"


@app.post("/api/command")
async def handle_command(cmd: CommandPayload):
    driver = shared_state.get("driver")
    if not driver:
        return {"ok": False, "error": "No driver attached"}

    if cmd.action == "stop":
        driver.stop_all()
    elif cmd.action == "hit":
        driver.hit(channel=cmd.channel, power=cmd.power, decay_ms=cmd.decay_ms)
    elif cmd.action == "set":
        driver.vibrate(channel=cmd.channel, intensity=cmd.power)
    elif cmd.action == "wave":
        driver.wave(channel=cmd.channel, freq_hz=cmd.freq_hz, min_power=10, max_power=cmd.power)

    return {"ok": True, "action": cmd.action}


@app.post("/api/phone_frame")
async def handle_phone_frame(req: Request):
    """Receive JPEG Base64 + Gyroscope IMU JSON from iPhone Safari."""
    try:
        data = await req.json()
        img_b64 = data.get("image", "")
        imu_json = data.get("imu", None)

        if imu_json:
            from ..drivers.base import IMUMotionData
            shared_state["phone_imu"] = IMUMotionData(
                roll=float(imu_json.get("gamma", 0)),
                pitch=float(imu_json.get("beta", 0)),
                yaw=float(imu_json.get("alpha", 0)),
                accel_x=float(imu_json.get("acc_x", 0)),
                accel_y=float(imu_json.get("acc_y", 0)),
                accel_z=float(imu_json.get("acc_z", 0))
            )

        if img_b64.startswith("data:image"):
            import base64
            img_bytes = base64.b64decode(img_b64.split(",")[1])
            nparr = np.frombuffer(img_bytes, np.uint8)
            img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img_np is not None:
                shared_state["current_frame"] = img_np

        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def generate_mjpeg():
    """MJPEG stream generator for web browser view."""
    while True:
        frame = shared_state.get("annotated_frame")
        if frame is None:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "WAITING FOR CAMERA STREAM...", (100, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2)

        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if ret:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        time.sleep(0.04)  # ~25 FPS stream


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    logger.info("New WebSocket client connected to Dashboard.")
    try:
        while True:
            # Broadcast state packet every 100ms
            p_state = shared_state.get("fused_state")
            t_data = shared_state.get("device_telemetry")
            
            payload = {
                "type": "telemetry",
                "player": {
                    "posture": p_state.posture_label if p_state else "Searching...",
                    "hands_core": p_state.hands_covering_core if p_state else False,
                    "hands_chest": p_state.hands_covering_chest if p_state else False,
                    "struggle": p_state.struggle_score if p_state else 0,
                    "tremor": p_state.tremor_intensity if p_state else 0,
                    "is_collapsed": p_state.is_collapsed if p_state else False,
                    "imu_roll": p_state.imu_roll if p_state else 0,
                    "imu_pitch": p_state.imu_pitch if p_state else 0
                } if p_state else None,
                "device": {
                    "name": t_data.device_name if t_data else "None",
                    "type": t_data.device_type.value if t_data else "none",
                    "connected": t_data.is_connected if t_data else False,
                    "battery": t_data.battery_level if t_data else 100,
                    "powers": t_data.channel_powers if t_data else {},
                    "skin_contact": t_data.skin_contact if t_data else True
                } if t_data else None,
                "dialogues": shared_state.get("ai_dialogues", [])[-6:]
            }

            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        active_websockets.remove(websocket)
    except Exception as e:
        if websocket in active_websockets:
            active_websockets.remove(websocket)


def broadcast_ai_dialogue(text: str, audio_url: str = ""):
    """Helper to push new dialogue to history and clients."""
    item = {"text": text, "audio": audio_url, "time": time.strftime("%H:%M:%S")}
    shared_state["ai_dialogues"].append(item)
