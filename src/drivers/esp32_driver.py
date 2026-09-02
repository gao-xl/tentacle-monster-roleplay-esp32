"""
ESP32-S3 / ESP32-C3 Serial Driver for OpenHaptic-Roleplay
Handles USB-CDC Serial communication, background heartbeats, IMU Gyro parsing, and failsafe watchdog.
"""

import time
import threading
import logging
from typing import Optional, List, Dict
import serial
import serial.tools.list_ports

from .base import BaseDeviceDriver, DeviceTelemetry, IMUMotionData, DeviceType

logger = logging.getLogger("ESP32Driver")


class ESP32Driver(BaseDeviceDriver):
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200, num_channels: int = 4):
        super().__init__(name="ESP32-C3/S3-Controller", device_type=DeviceType.ESP32)
        self.port = port
        self.baudrate = baudrate
        self.num_channels = num_channels
        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        
        # State tracking
        self._current_telemetry = DeviceTelemetry(
            device_name=self.name,
            device_type=self.device_type,
            is_connected=False,
            channel_powers={i: 0.0 for i in range(num_channels)},
            channel_limits={i: 100.0 for i in range(num_channels)},
            skin_contact=True,
            imu=IMUMotionData()
        )
        
        self._running = False
        self._rx_thread: Optional[threading.Thread] = None
        self._last_heartbeat_time = 0.0

    @staticmethod
    def auto_detect_port() -> Optional[str]:
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            desc = (p.description or "").lower()
            hwid = (p.hwid or "").lower()
            if "303a" in hwid or "esp" in desc or "usb jtag" in desc or "usb-enhanced-serial" in desc:
                logger.info(f"Auto-detected ESP32 device on port: {p.device} ({p.description})")
                return p.device
        if ports:
            return ports[0].device
        return None

    def connect(self) -> bool:
        if not self.port:
            self.port = self.auto_detect_port()

        if not self.port:
            logger.error("No serial port specified or detected!")
            return False

        try:
            logger.info(f"Connecting to ESP32 on {self.port} at {self.baudrate} baud...")
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                write_timeout=1.0
            )
            time.sleep(1.0)
            
            self._send_raw("PING")
            time.sleep(0.1)
            
            self.is_connected = True
            self._running = True
            self._current_telemetry.is_connected = True
            
            # Start background RX and heartbeat thread
            self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
            self._rx_thread.start()
            
            logger.info("Successfully connected to ESP32 controller!")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ESP32 on {self.port}: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        self._running = False
        if self.is_connected:
            self.stop_all()
        with self._lock:
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None
        self.is_connected = False
        logger.info("ESP32 disconnected.")

    def _send_raw(self, cmd: str) -> bool:
        with self._lock:
            if not self._serial or not self._serial.is_open:
                return False
            try:
                msg = (cmd.strip() + "\n").encode("utf-8")
                self._serial.write(msg)
                self._serial.flush()
                self._last_heartbeat_time = time.time()
                return True
            except Exception as e:
                logger.error(f"Serial write error: {e}")
                self.is_connected = False
                return False

    def _rx_loop(self):
        """Read serial responses, parse IMU telemetry, and send periodic PING."""
        while self._running:
            now = time.time()
            # Send PING if idle for 800ms
            if now - self._last_heartbeat_time > 0.8:
                self._send_raw("PING")

            # Read incoming lines
            try:
                if self._serial and self._serial.in_waiting > 0:
                    line = self._serial.readline().decode("utf-8", errors="ignore").strip()
                    if line.startswith("IMU "):
                        # Parse: "IMU <roll> <pitch> <yaw> <accel>"
                        parts = line.split()
                        if len(parts) >= 5:
                            roll = float(parts[1])
                            pitch = float(parts[2])
                            yaw = float(parts[3])
                            accel = float(parts[4])
                            
                            if self._current_telemetry.imu is None:
                                self._current_telemetry.imu = IMUMotionData()
                            self._current_telemetry.imu.roll = roll
                            self._current_telemetry.imu.pitch = pitch
                            self._current_telemetry.imu.yaw = yaw
                            self._current_telemetry.imu.accel_z = accel
                            self.emit_telemetry(self._current_telemetry)
            except Exception as e:
                logger.debug(f"Serial read error: {e}")

            time.sleep(0.01)

    def vibrate(self, channel: int = 0, intensity: float = 0.0, duration_ms: Optional[int] = None) -> bool:
        intensity = max(0.0, min(100.0, float(intensity)))
        ch = max(0, min(self.num_channels - 1, channel))
        self._current_telemetry.channel_powers[ch] = intensity
        return self._send_raw(f"SET {ch} {int(intensity)}")

    def hit(self, channel: int = 0, power: float = 50.0, decay_ms: int = 400) -> bool:
        power = max(0.0, min(100.0, float(power)))
        ch = max(0, min(self.num_channels - 1, channel))
        self._current_telemetry.channel_powers[ch] = power
        return self._send_raw(f"HIT {ch} {int(power)} {int(decay_ms)}")

    def wave(self, channel: int = 0, freq_hz: float = 1.0, min_power: float = 0.0, max_power: float = 50.0) -> bool:
        ch = max(0, min(self.num_channels - 1, channel))
        return self._send_raw(f"WAVE {ch} {freq_hz:.2f} {int(min_power)} {int(max_power)}")

    def shock(self, channel: int = 0, intensity: float = 0.0, waveform: str = "pulse") -> bool:
        return self.hit(channel=channel, power=intensity, decay_ms=200)

    def stop_all(self) -> bool:
        for ch in self._current_telemetry.channel_powers:
            self._current_telemetry.channel_powers[ch] = 0.0
        return self._send_raw("STOP")

    def get_telemetry(self) -> DeviceTelemetry:
        return self._current_telemetry
