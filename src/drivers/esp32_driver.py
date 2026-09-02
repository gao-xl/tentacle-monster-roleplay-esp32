"""
ESP32 Driver with Secure Rolling Heartbeat (v3.0)
Ensures continuous 100ms hardware validation.
"""
import time
import serial
import threading
import logging
from .base import BaseDeviceDriver

logger = logging.getLogger("ESP32Driver")

class ESP32SecureDriver(BaseDeviceDriver):
    def __init__(self, port: str, baudrate: int = 115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        
        self._target_a = 0.0
        self._target_b = 0.0
        
        self.token = 0
        self._running = False
        self._thread = None

    def connect(self) -> bool:
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            self._running = True
            self.token = 0
            self.is_connected = True
            
            # Start high-priority 50ms heartbeat thread
            self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self._thread.start()
            logger.info("[ESP32] Secure driver connected with Rolling Heartbeat.")
            return True
        except Exception as e:
            logger.error(f"[ESP32] Connection failed: {e}")
            return False

    def _heartbeat_loop(self):
        while self._running and self.ser and self.ser.is_open:
            # Send Sync: SYNC <token> <lvl_A> <lvl_B>
            cmd = f"SYNC {self.token} {int(self._target_a)} {int(self._target_b)}\n"
            try:
                self.ser.write(cmd.encode())
                self.token = (self.token + 1) % 256
            except:
                self._running = False
                self.is_connected = False
            
            time.sleep(0.05)  # 50ms pulse to satisfy 150ms hardware watchdog

    def set_channel(self, channel: int, power: float):
        if channel == 0: self._target_a = min(100.0, max(0.0, power))
        if channel == 1: self._target_b = min(100.0, max(0.0, power))

    def stop_all(self):
        self._target_a = 0.0
        self._target_b = 0.0

    def disconnect(self):
        self._running = False
        if self._thread: self._thread.join(timeout=1.0)
        if self.ser: self.ser.close()
        self.is_connected = False
