"""
DG-LAB (郊狼) Coyote Bi-directional Driver for OpenHaptic-Roleplay
Supports WebSocket protocol (V2/V3), parsing dual-channel strength (A/B),
battery telemetry, skin contact detachment detection, and sending e-stim pulses.
"""

import json
import time
import threading
import logging
from typing import Optional, Dict, Any

from .base import BaseDeviceDriver, DeviceTelemetry, DeviceType

logger = logging.getLogger("DGLabDriver")


class DGLabDriver(BaseDeviceDriver):
    def __init__(
        self,
        ws_url: str = "ws://127.0.0.1:8989",
        channel_a_limit: float = 80.0,
        channel_b_limit: float = 80.0
    ):
        super().__init__(name="DG-LAB-Coyote", device_type=DeviceType.DGLAB)
        self.ws_url = ws_url
        self.channel_limits = {0: channel_a_limit, 1: channel_b_limit}
        
        self._current_telemetry = DeviceTelemetry(
            device_name=self.name,
            device_type=self.device_type,
            is_connected=False,
            channel_powers={0: 0.0, 1: 0.0},
            channel_limits=self.channel_limits,
            skin_contact=True
        )
        
        self._ws = None
        self._ws_thread = None
        self._running = False
        self._client_id = None
        self._target_id = None

    def connect(self) -> bool:
        logger.info(f"Connecting to DG-LAB Coyote WebSocket at {self.ws_url}...")
        self._running = True
        self._start_ws()
        time.sleep(1.0)
        return self.is_connected

    def _start_ws(self):
        try:
            import websocket
        except ImportError:
            logger.warning("websocket-client not installed. Run: pip install websocket-client")
            return

        def on_open(ws):
            logger.info("DG-LAB WebSocket connection established.")
            self.is_connected = True
            self._current_telemetry.is_connected = True
            self.emit_telemetry(self._current_telemetry)

        def on_message(ws, message):
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "bind":
                    # Device bound with mobile APP
                    self._target_id = data.get("clientId")
                    logger.info(f"DG-LAB bound to mobile app targetId: {self._target_id}")

                elif msg_type == "msg":
                    content = str(data.get("message", ""))
                    # Parse DG-LAB Telemetry: "strength-A-25", "battery-85", "break-A"
                    if "battery" in content:
                        parts = content.split("-")
                        if len(parts) >= 2 and parts[1].isdigit():
                            self._current_telemetry.battery_level = int(parts[1])
                            logger.info(f"[DG-LAB Telemetry] Battery: {self._current_telemetry.battery_level}%")
                    
                    elif "strength" in content:
                        # e.g. "strength-A-35" or "strength-B-20"
                        parts = content.split("-")
                        if len(parts) >= 3:
                            ch_idx = 0 if parts[1].upper() == "A" else 1
                            val = float(parts[2])
                            self._current_telemetry.channel_powers[ch_idx] = val
                            logger.info(f"[DG-LAB Telemetry] CH_{parts[1]}: {val}")
                    
                    elif "break" in content:
                        # Electrode pad detached (Skin contact lost!)
                        self._current_telemetry.skin_contact = False
                        logger.warning("[DG-LAB ALERT] Electrode pad detached! Skin contact lost.")
                    
                    elif "attach" in content or "restore" in content:
                        self._current_telemetry.skin_contact = True
                        logger.info("[DG-LAB OK] Electrode re-attached.")

                    self._current_telemetry.raw_data = data
                    self.emit_telemetry(self._current_telemetry)

            except Exception as e:
                logger.debug(f"Error parsing DG-LAB msg: {e}")

        def run():
            while self._running:
                try:
                    self._ws = websocket.WebSocketApp(
                        self.ws_url,
                        on_open=on_open,
                        on_message=on_message,
                        on_error=lambda ws, err: logger.debug(f"DG-LAB WS err: {err}"),
                        on_close=lambda ws, code, msg: logger.info("DG-LAB WS closed")
                    )
                    self._ws.run_forever()
                except Exception:
                    pass
                time.sleep(3)

        self._ws_thread = threading.Thread(target=run, daemon=True)
        self._ws_thread.start()

    def disconnect(self) -> None:
        self._running = False
        if self._ws:
            self._ws.close()
        self.stop_all()
        self.is_connected = False
        logger.info("DG-LAB Coyote Driver disconnected.")

    def _send_dg_msg(self, msg_str: str) -> bool:
        if not self._ws or not self.is_connected:
            return False
        payload = {
            "type": "msg",
            "targetId": self._target_id,
            "message": msg_str
        }
        try:
            self._ws.send(json.dumps(payload))
            return True
        except Exception as e:
            logger.error(f"DG-LAB send failed: {e}")
            return False

    def shock(self, channel: int = 0, intensity: float = 0.0, waveform: str = "pulse") -> bool:
        ch_name = "A" if channel == 0 else "B"
        clamped = min(self.channel_limits.get(channel, 100.0), intensity)
        self._current_telemetry.channel_powers[channel] = clamped
        # Send DG-LAB strength command: "set-A:30"
        return self._send_dg_msg(f"set-{ch_name}:{int(clamped)}")

    def hit(self, channel: int = 0, power: float = 50.0, decay_ms: int = 400) -> bool:
        # Deliver a short pulse shock
        self.shock(channel=channel, intensity=power)
        # Schedule auto-reset after decay_ms
        def decay_reset():
            time.sleep(decay_ms / 1000.0)
            self.shock(channel=channel, intensity=0.0)
        threading.Thread(target=decay_reset, daemon=True).start()
        return True

    def vibrate(self, channel: int = 0, intensity: float = 0.0, duration_ms: Optional[int] = None) -> bool:
        return self.shock(channel=channel, intensity=intensity)

    def wave(self, channel: int = 0, freq_hz: float = 1.0, min_power: float = 0.0, max_power: float = 50.0) -> bool:
        # Send waveform pattern
        ch_name = "A" if channel == 0 else "B"
        return self._send_dg_msg(f"wave-{ch_name}:{int(min_power)}-{int(max_power)}")

    def stop_all(self) -> bool:
        self._send_dg_msg("clear-A")
        self._send_dg_msg("clear-B")
        self._current_telemetry.channel_powers = {0: 0.0, 1: 0.0}
        self.emit_telemetry(self._current_telemetry)
        return True

    def get_telemetry(self) -> DeviceTelemetry:
        return self._current_telemetry
