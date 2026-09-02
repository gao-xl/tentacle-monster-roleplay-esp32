"""
Quad-Electrode (4-Pad / Dual-Loop) Spatial Haptic Sequencer for OpenHaptic-Roleplay
Controls 4 physical electrode pads (Loop A: Pads 1-2, Loop B: Pads 3-4):
- Traveling Wave (Ankles -> Pelvic Core ascending crawl)
- Alternating Assault (Left vs Right or Upper vs Lower alternating strikes)
- Evasion Chase (Shifts electric current away from guarded body parts)
- Synchronized Overload Burst
"""

import time
import math
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from ..drivers.base import BaseDeviceDriver
from ..vision.pose26_tracker import Pose26AnalysisResult

logger = logging.getLogger("QuadChannelSequencer")


class QuadPadLayout(str, Enum):
    TRAVELING_VERTICAL = "TRAVELING_VERTICAL"   # A: 核心区(1-2), B: 小腿/足弓(3-4) -> 纵向攀爬
    BILATERAL_THIGHS = "BILATERAL_THIGHS"       # A: 左大腿(1-2), B: 右大腿(3-4) -> 左右夹击
    CROSS_CORE_BACK = "CROSS_CORE_BACK"         # A: 核心前方(1-2), B: 后腰(3-4) -> 前后对穿
    CONCENTRATED_CORE = "CONCENTRATED_CORE"     # A: 核心左(1-2), B: 核心右(3-4) -> 核心矩阵包围


class QuadHapticPattern(str, Enum):
    IDLE = "IDLE"
    TRAVELING_ASCEND = "TRAVELING_ASCEND"       # 下向上一路攀爬放电
    ALTERNATING = "ALTERNATING"                 # A/B 交替戏谑放电
    EVASION_CHASE = "EVASION_CHASE"             # 追击未设防区域
    FULL_BURST = "FULL_BURST"                   # 四极点全域爆发过载


@dataclass
class QuadPadPlacementConfig:
    layout: QuadPadLayout = QuadPadLayout.TRAVELING_VERTICAL
    loop_a_name: str = "通道 A (Pads 1-2: 魔法传导器核心区)"
    loop_b_name: str = "通道 B (Pads 3-4: 双侧小腿与足弓)"
    max_power_a: float = 65.0
    max_power_b: float = 75.0


class QuadChannelSequencer:
    """Manages real-time 4-pad spatial haptic orchestration."""

    def __init__(self, driver: BaseDeviceDriver, config: Optional[QuadPadPlacementConfig] = None):
        self.driver = driver
        self.config = config or QuadPadPlacementConfig()
        self.current_pattern = QuadHapticPattern.IDLE
        self._pattern_start_time = 0.0
        self._last_step_time = 0.0

    def set_layout(self, layout: QuadPadLayout):
        self.config.layout = layout
        if layout == QuadPadLayout.TRAVELING_VERTICAL:
            self.config.loop_a_name = "通道 A (Pads 1-2: 核心区)"
            self.config.loop_b_name = "通道 B (Pads 3-4: 小腿足弓)"
            self.config.max_power_a = 65.0
            self.config.max_power_b = 75.0
        elif layout == QuadPadLayout.BILATERAL_THIGHS:
            self.config.loop_a_name = "通道 A (Pads 1-2: 左大腿内侧)"
            self.config.loop_b_name = "通道 B (Pads 3-4: 右大腿内侧)"
            self.config.max_power_a = 70.0
            self.config.max_power_b = 70.0
        elif layout == QuadPadLayout.CROSS_CORE_BACK:
            self.config.loop_a_name = "通道 A (Pads 1-2: 下腹核心前方)"
            self.config.loop_b_name = "通道 B (Pads 3-4: 后腰中轴区)"
            self.config.max_power_a = 65.0
            self.config.max_power_b = 80.0

        logger.info(f"[QuadSequencer] Layout updated: {self.config.layout.value}")

    def trigger_pattern(self, pattern: QuadHapticPattern, duration_sec: float = 2.0):
        self.current_pattern = pattern
        self._pattern_start_time = time.time()
        logger.info(f"[QuadSequencer] Triggered Pattern: {pattern.value}")

    def update(self, pose: Pose26AnalysisResult):
        """Called every frame to calculate 4-pad real-time dual-loop outputs."""
        now = time.time()

        # 1. Automatic Evasion Chase based on YOLO-Pose 26
        # If player covers Point 19 Core, shift attack to Loop B (Legs/Back)!
        if pose.hands_covering_core and self.current_pattern == QuadHapticPattern.IDLE:
            # Shift power to Loop B to bypass hand defense
            power_b = min(self.config.max_power_b, 60.0)
            self.driver.hit(channel=1, power=power_b, decay_ms=400)
            self.driver.vibrate(channel=0, intensity=15.0) # Light distraction on Loop A
            return

        # 2. Process Active Dynamic Patterns
        if self.current_pattern == QuadHapticPattern.TRAVELING_ASCEND:
            elapsed = now - self._pattern_start_time
            # Wave ascends from Loop B (Legs) -> Loop A (Core) over 0.8s cycle
            cycle = (elapsed % 0.8) / 0.8
            if cycle < 0.4:
                # Phase 1: Loop B (Legs/Pads 3-4) fires
                self.driver.vibrate(channel=1, intensity=self.config.max_power_b * 0.8)
                self.driver.vibrate(channel=0, intensity=0.0)
            else:
                # Phase 2: Loop A (Core/Pads 1-2) fires with surge
                self.driver.vibrate(channel=1, intensity=self.config.max_power_b * 0.2)
                self.driver.vibrate(channel=0, intensity=self.config.max_power_a * 0.9)

            if elapsed > 3.0: # Auto finish after 3s
                self.current_pattern = QuadHapticPattern.IDLE
                self.driver.stop_all()

        elif self.current_pattern == QuadHapticPattern.ALTERNATING:
            elapsed = now - self._pattern_start_time
            phase = int(elapsed * 4.0) % 2 # 2Hz alternating toggle
            if phase == 0:
                self.driver.vibrate(channel=0, intensity=self.config.max_power_a * 0.7)
                self.driver.vibrate(channel=1, intensity=0.0)
            else:
                self.driver.vibrate(channel=0, intensity=0.0)
                self.driver.vibrate(channel=1, intensity=self.config.max_power_b * 0.7)

            if elapsed > 2.5:
                self.current_pattern = QuadHapticPattern.IDLE
                self.driver.stop_all()

        elif self.current_pattern == QuadHapticPattern.FULL_BURST:
            elapsed = now - self._pattern_start_time
            self.driver.vibrate(channel=0, intensity=self.config.max_power_a)
            self.driver.vibrate(channel=1, intensity=self.config.max_power_b)
            if elapsed > 1.2:
                self.current_pattern = QuadHapticPattern.IDLE
                self.driver.stop_all()
