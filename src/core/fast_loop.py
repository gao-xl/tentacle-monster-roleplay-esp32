"""
Fast Loop Decision Engine for OpenHaptic-Roleplay
Translates millisecond-level vision events (coverage, struggle) into physical haptic impacts.
"""

import time
import logging
from typing import Optional
from ..drivers.base import BaseDeviceDriver
from ..vision.yolo_tracker import PoseAnalysisResult

logger = logging.getLogger("FastLoopEngine")


class FastLoopEngine:
    def __init__(
        self,
        driver: BaseDeviceDriver,
        max_power_limit: float = 75.0,
        hit_cooldown_sec: float = 0.6
    ):
        self.driver = driver
        self.max_power_limit = max_power_limit
        self.hit_cooldown_sec = hit_cooldown_sec
        
        self._last_hit_time = 0.0
        self._is_struggling_active = False

    def update(self, pose: PoseAnalysisResult):
        """Called on every video frame (30+ FPS)."""
        now = time.time()

        if not pose.has_person:
            return

        # 1. Trigger Rule: Hands Covering Core (Breach Attack)
        if pose.hands_covering_core:
            if now - self._last_hit_time > self.hit_cooldown_sec:
                # Deliver a sharp impact to force breach / punish defense
                hit_power = min(self.max_power_limit, 65.0)
                logger.info(f"[TRIGGER] Core defense detected -> Delivering HIT ({hit_power}%)")
                self.driver.hit(channel=0, power=hit_power, decay_ms=450)
                self._last_hit_time = now

        # 2. Trigger Rule: Struggling / Rapid Agitation
        elif pose.struggle_index > 40.0:
            if not self._is_struggling_active:
                self._is_struggling_active = True
                # Dynamically scale wave intensity based on struggle index
                wave_min = 15.0
                wave_max = min(self.max_power_limit, 25.0 + (pose.struggle_index * 0.4))
                logger.info(f"[TRIGGER] Struggle agitation ({pose.struggle_index:.1f}%) -> Triggering WAVE")
                self.driver.wave(channel=0, freq_hz=2.0, min_power=wave_min, max_power=wave_max)

        # 3. Trigger Rule: Hands Covering Chest
        elif pose.hands_covering_chest:
            if now - self._last_hit_time > 1.2:
                logger.info("[TRIGGER] Chest defense -> Gentle warning vibration")
                self.driver.vibrate(channel=0, intensity=25.0)
                self._last_hit_time = now

        # 4. Return to Neutral / Idle
        else:
            if self._is_struggling_active:
                self._is_struggling_active = False
                self.driver.vibrate(channel=0, intensity=0.0)
