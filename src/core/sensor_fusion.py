"""
Sensor Fusion Module for OpenHaptic-Roleplay
Combines Computer Vision (YOLO-Pose) and Hardware/Phone Gyroscope (IMU)
to calculate Involuntary Tremor Index, Orientation, and Collapse/Fallen States.
"""

import time
import math
import numpy as np
from dataclasses import dataclass
from typing import Optional
from ..vision.yolo_tracker import PoseAnalysisResult
from ..drivers.base import IMUMotionData


@dataclass
class FusedPlayerState:
    posture_label: str = "Neutral"
    hands_covering_core: bool = False
    hands_covering_chest: bool = False
    
    # Combined Physical Dynamics
    struggle_score: float = 0.0      # 0 - 100 (Overall struggle agitation)
    tremor_intensity: float = 0.0    # 0 - 100 (High-frequency muscle spasm / shaking)
    is_collapsed: bool = False       # True if fallen, knocked down, or lying on ground
    
    # Raw Subsystem Readings
    vision_struggle: float = 0.0
    imu_roll: float = 0.0
    imu_pitch: float = 0.0


class SensorFusionEngine:
    def __init__(self):
        self._accel_history = []
        self._last_update_time = time.time()

    def fuse(
        self,
        vision_result: Optional[PoseAnalysisResult],
        imu_data: Optional[IMUMotionData]
    ) -> FusedPlayerState:
        """Fuse visual pose and gyro telemetry into holistic player state."""
        state = FusedPlayerState()

        # 1. Process Vision Data
        if vision_result and vision_result.has_person:
            state.hands_covering_core = vision_result.hands_covering_core
            state.hands_covering_chest = vision_result.hands_covering_chest
            state.vision_struggle = vision_result.struggle_index
            state.posture_label = vision_result.posture_label

        # 2. Process Gyroscope / IMU Data
        if imu_data:
            state.imu_roll = imu_data.roll
            state.imu_pitch = imu_data.pitch
            
            # Detect Tremors / Muscle Spasms (High-frequency Gyro acceleration energy)
            accel_mag = math.sqrt(imu_data.accel_x**2 + imu_data.accel_y**2 + imu_data.accel_z**2)
            self._accel_history.append(accel_mag)
            if len(self._accel_history) > 15:
                self._accel_history.pop(0)

            # High variance in acceleration indicates involuntary trembling/twitching
            if len(self._accel_history) >= 5:
                accel_std = float(np.std(self._accel_history))
                state.tremor_intensity = min(100.0, accel_std * 50.0)

            # Detect Collapse / Fallen over (Orientation angle > 65 degrees)
            if abs(imu_data.pitch) > 65.0 or abs(imu_data.roll) > 65.0 or imu_data.is_fallen:
                state.is_collapsed = True
                state.posture_label = "Collapsed / Knocked Down"

        # 3. Fuse Struggle Score (Weighted blend of Vision motion + IMU vibration)
        state.struggle_score = min(
            100.0,
            (state.vision_struggle * 0.6) + (state.tremor_intensity * 0.4)
        )

        return state
