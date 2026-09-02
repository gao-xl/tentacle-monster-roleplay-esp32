"""
Fast Loop Decision Engine for OpenHaptic-Roleplay (YOLO-Pose 26 Native)
Translates millisecond-level vision events (Point 19 core coverage, struggle, toe spasm)
into physical haptic impacts.
"""

import time
import logging
from typing import Optional
from ..drivers.base import BaseDeviceDriver
from ..vision.pose26_tracker import Pose26AnalysisResult

logger = logging.getLogger("FastLoopEngine")


class FastLoopEngine:
    def __init__(
        self,
        driver: BaseDeviceDriver,
        max_power_limit: float = 75.0,
        hit_cooldown_sec: float = 0.5
    ):
        self.driver = driver
        self.max_power_limit = max_power_limit
        self.hit_cooldown_sec = hit_cooldown_sec
        
        self._last_hit_time = 0.0
        self._is_struggling_active = False

    def update(self, pose: Pose26AnalysisResult):
        """Called on every video frame (30+ FPS)."""
        now = time.time()

        if not pose.has_person:
            return

        # 1. Trigger Rule: Hands Covering Point 19 Core Conductor (Breach Attack)
        if pose.hands_covering_core:
            if now - self._last_hit_time > self.hit_cooldown_sec:
                hit_power = min(self.max_power_limit, 68.0)
                logger.info(f"[TRIGGER] Point 19 Core defense detected -> Delivering HIT ({hit_power}%)")
                self.driver.hit(channel=0, power=hit_power, decay_ms=450)
                self._last_hit_time = now

        # 2. Trigger Rule: Severe Struggle / Foot Toe Spasm
        elif pose.struggle_score > 40.0 or pose.toe_curl_index > 50.0:
            if not self._is_struggling_active:
                self._is_struggling_active = True
                wave_min = 20.0
                wave_max = min(self.max_power_limit, 30.0 + (pose.struggle_score * 0.45))
                logger.info(f"[TRIGGER] Agitation / Foot Spasm -> Triggering WAVE ({wave_min:.0f}-{wave_max:.0f}%)")
                self.driver.wave(channel=0, freq_hz=2.2, min_power=wave_min, max_power=wave_max)

        # 3. Trigger Rule: Hands Covering Chest or Neck
        elif pose.hands_covering_chest or pose.hands_covering_neck:
            if now - self._last_hit_time > 1.0:
                logger.info("[TRIGGER] Upper body defense -> Gentle warning pulse")
                self.driver.vibrate(channel=0, intensity=28.0)
                self._last_hit_time = now

        # 4. Return to Neutral / Idle
        else:
            if self._is_struggling_active:
                self._is_struggling_active = False
                self.driver.vibrate(channel=0, intensity=0.0)
