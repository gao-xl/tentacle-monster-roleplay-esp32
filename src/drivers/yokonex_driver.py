"""
YOKONEX (役次元) Bi-directional Driver for OpenHaptic-Roleplay
Communicates with YOKONEX API-bridge (WebSocket / HTTP), sends game commands,
and listens to real-time status, connection events, and APP-side feedback.
"""

import json
import time
import threading
import logging
from typing import Optional, Dict, Any
import requests

from .base import BaseDeviceDriver, DeviceTelemetry, DeviceType

logger = logging.getLogger("YokonexDriver")


class YokonexDriver(BaseDeviceDriver):
    def __init__(
        self,
        bridge_http_url: str = "http://127.0.0.1:3001",
        bridge_ws_url: str = "ws://127.0.0.1:3001",
        uid: Optional[str] = None,
        token: Optional[str] = None
    ):
        super().__init__(name="YOKONEX-IM-Controller", device_type=DeviceType.YOKONEX)
        self.bridge_http_url = bridge_http_url.rstrip("/")
        self.bridge_ws_url = bridge_ws_url
        self.uid = uid
        self.token = token
        
        self._current_telemetry = DeviceTelemetry(
            device_name=self.name,
            device_type=self.device_type,
            is_connected=False,
            channel_powers={0: 0.0},
            channel_limits={0: 100.0},
            skin_contact=True
        )
        
        self._ws = None
        self._ws_thread = None
        self._running = False

    def connect(self) -> bool:
        """Connect to API-bridge and login if credentials are provided."""
        logger.info(f"Connecting to YOKONEX API-bridge at {self.bridge_http_url}...")
        try:
            # Check Health
            resp = requests.get(f"{self.bridge_http_url}/health", timeout=3.0)
            if resp.status_code != 200:
                logger.error(f"YOKONEX bridge health check failed: {resp.text}")
                return False
            
            # Login if credentials provided
            if self.uid and self.token:
                logger.info(f"Logging into YOKONEX IM with UID={self.uid}...")
                login_resp = requests.post(
                    f"{self.bridge_http_url}/api/login",
                    json={"uid": self.uid, "token": self.token},
                    timeout=5.0
                )
                if login_resp.status_code != 200:
                    logger.warning(f"Login failed: {login_resp.text}")

            self.is_connected = True
            self._running = True
            
            # Start WebSocket background listener for real-time telemetry
            self._start_ws_listener()
            
            logger.info("YOKONEX Driver connected and telemetry listener active!")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to YOKONEX bridge: {e}")
            self.is_connected = False
            return False

    def _start_ws_listener(self):
        try:
            import websocket
        except ImportError:
            logger.warning("websocket-client not installed. Telemetry push disabled. Run: pip install websocket-client")
            return

        def on_message(ws, message):
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "status":
                    is_ready = data.get("data", {}).get("isReady", False)
                    self._current_telemetry.is_connected = is_ready
                    self._current_telemetry.raw_data = data
                    self.emit_telemetry(self._current_telemetry)

                elif msg_type == "message":
                    # Pushed message from mobile app
                    msgs = data.get("data", {}).get("messages", [])
                    for m in msgs:
                        payload = m.get("payload", {})
                        logger.info(f"[YOKONEX Feedback] Received IM msg: {payload}")
                        self._current_telemetry.last_event = str(payload.get("text", ""))
                        self.emit_telemetry(self._current_telemetry)

                elif msg_type == "error":
                    logger.error(f"[YOKONEX Error] {data.get('message')}")
            except Exception as e:
                logger.debug(f"Error parsing YOKONEX WS message: {e}")

        def run_ws():
            while self._running:
                try:
                    self._ws = websocket.WebSocketApp(
                        self.bridge_ws_url,
                        on_message=on_message,
                        on_error=lambda ws, err: logger.debug(f"YOKONEX WS err: {err}"),
                        on_close=lambda ws, code, msg: logger.info("YOKONEX WS closed")
                    )
                    self._ws.run_forever()
                except Exception:
                    pass
                time.sleep(3)

        self._ws_thread = threading.Thread(target=run_ws, daemon=True)
        self._ws_thread.start()

    def disconnect(self) -> None:
        self._running = False
        if self._ws:
            self._ws.close()
        self.stop_all()
        self.is_connected = False
        logger.info("YOKONEX Driver disconnected.")

    def send_command_id(self, command_id: str) -> bool:
        """Send specific configured game command ID to Yokonex App."""
        try:
            resp = requests.post(
                f"{self.bridge_http_url}/api/send-command",
                json={"commandId": command_id},
                timeout=3.0
            )
            ok = resp.status_code == 200 and resp.json().get("success", False)
            if ok:
                self._current_telemetry.last_event = command_id
                self.emit_telemetry(self._current_telemetry)
            return ok
        except Exception as e:
            logger.error(f"Error sending command {command_id}: {e}")
            return False

    def vibrate(self, channel: int = 0, intensity: float = 0.0, duration_ms: Optional[int] = None) -> bool:
        self._current_telemetry.channel_powers[channel] = intensity
        if intensity > 60:
            return self.send_command_id("vibrate_high")
        elif intensity > 25:
            return self.send_command_id("vibrate_med")
        elif intensity > 0:
            return self.send_command_id("vibrate_low")
        else:
            return self.send_command_id("vibrate_stop")

    def hit(self, channel: int = 0, power: float = 50.0, decay_ms: int = 400) -> bool:
        self._current_telemetry.channel_powers[channel] = power
        return self.send_command_id("hit_shock")

    def wave(self, channel: int = 0, freq_hz: float = 1.0, min_power: float = 0.0, max_power: float = 50.0) -> bool:
        return self.send_command_id("wave_pattern")

    def shock(self, channel: int = 0, intensity: float = 0.0, waveform: str = "pulse") -> bool:
        self._current_telemetry.channel_powers[channel] = intensity
        return self.send_command_id("electric_shock")

    def stop_all(self) -> bool:
        self._current_telemetry.channel_powers = {0: 0.0}
        return self.send_command_id("_stop_all")

    def get_telemetry(self) -> DeviceTelemetry:
        return self._current_telemetry
