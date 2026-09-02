"""
Unified Hardware Abstraction Layer (HAL) for OpenHaptic-Roleplay
Defines bi-directional control, IMU/Gyroscope motion data, and telemetry interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List, Tuple
from enum import Enum


class DeviceType(str, Enum):
    ESP32 = "esp32"
    YOKONEX = "yokonex"
    DGLAB = "dglab"
    BUTTPLUG = "buttplug"
    MOBILE_PHONE = "mobile_phone"
    VIRTUAL = "virtual"


@dataclass
class IMUMotionData:
    """Gyroscope, Orientation and Accelerometer telemetry."""
    roll: float = 0.0          # Pitch/Roll/Yaw in degrees (-180 to 180)
    pitch: float = 0.0
    yaw: float = 0.0
    accel_x: float = 0.0       # Linear acceleration in G or m/s^2
    accel_y: float = 0.0
    accel_z: float = 0.0
    tremor_index: float = 0.0  # High-frequency muscle twitch / tremor score (0-100)
    is_fallen: bool = False    # Rolled over / collapsed on floor


@dataclass
class DeviceTelemetry:
    device_name: str
    device_type: DeviceType
    is_connected: bool
    battery_level: Optional[int] = None          # 0 - 100%
    channel_powers: Dict[int, float] = field(default_factory=dict)   # Channel -> Actual Output %
    channel_limits: Dict[int, float] = field(default_factory=dict)   # Channel -> Safety Limit %
    skin_contact: bool = True                     # Electrode contact
    imu: Optional[IMUMotionData] = None           # Real-time Gyroscope / Motion data
    last_event: Optional[str] = None              # Last event label
    raw_data: Optional[Dict[str, Any]] = None     # Raw protocol payload


class BaseDeviceDriver(ABC):
    """Abstract Base Class for all bi-directional haptic drivers."""

    def __init__(self, name: str = "GenericDevice", device_type: DeviceType = DeviceType.VIRTUAL):
        self.name = name
        self.device_type = device_type
        self.is_connected = False
        self._telemetry_callbacks: List[Callable[[DeviceTelemetry], None]] = []

    def register_telemetry_callback(self, callback: Callable[[DeviceTelemetry], None]) -> None:
        if callback not in self._telemetry_callbacks:
            self._telemetry_callbacks.append(callback)

    def unregister_telemetry_callback(self, callback: Callable[[DeviceTelemetry], None]) -> None:
        if callback in self._telemetry_callbacks:
            self._telemetry_callbacks.remove(callback)

    def emit_telemetry(self, telemetry: DeviceTelemetry) -> None:
        for cb in self._telemetry_callbacks:
            try:
                cb(telemetry)
            except Exception as e:
                print(f"[{self.name}] Error in telemetry callback: {e}")

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def vibrate(self, channel: int = 0, intensity: float = 0.0, duration_ms: Optional[int] = None) -> bool:
        pass

    @abstractmethod
    def hit(self, channel: int = 0, power: float = 50.0, decay_ms: int = 400) -> bool:
        pass

    @abstractmethod
    def wave(self, channel: int = 0, freq_hz: float = 1.0, min_power: float = 0.0, max_power: float = 50.0) -> bool:
        pass

    @abstractmethod
    def shock(self, channel: int = 0, intensity: float = 0.0, waveform: str = "pulse") -> bool:
        pass

    @abstractmethod
    def stop_all(self) -> bool:
        pass

    @abstractmethod
    def get_telemetry(self) -> DeviceTelemetry:
        pass
