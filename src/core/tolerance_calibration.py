"""
Tolerance Calibration Suite (Phase 0: Pre-Game Endurance Testing)
Allows players to interactively establish:
1. Sensory Threshold (T0: Barely perceptible tingling)
2. Comfort Working Range (T1: Moderate teasing / wave haptics)
3. Maximum Tolerable Limit (Tmax: Pain threshold / punishment ceiling)

The measured Tmax is used to mathematically scale:
- Punishment shocks (e.g., Ruined Orgasm / Violation HIT = 85% of Tmax)
- Orgasm Denial climbing curves (e.g., Climbing = T0 -> 90% of Tmax)
- Safety Ceiling (Hard clamp at 100% of Tmax)
"""

import time
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable
from ..core.gender_tuning import GenderTuningProfile

logger = logging.getLogger("ToleranceCalibration")


@dataclass
class UserToleranceProfile:
    is_tested: bool = False
    channel_a_t0: float = 15.0     # 阈值感知起步点 (Loop A: 核心)
    channel_a_tmax: float = 60.0   # 极限耐受点 (Loop A: 核心)
    channel_b_t0: float = 15.0     # 阈值感知起步点 (Loop B: 腿部)
    channel_b_tmax: float = 70.0   # 极限耐受点 (Loop B: 腿部)
    timestamp: float = 0.0

    def get_punishment_power(self, channel: int = 0) -> float:
        """Returns the scaled punishment strike (88% of Tmax)."""
        tmax = self.channel_a_tmax if channel == 0 else self.channel_b_tmax
        return tmax * 0.88

    def get_edge_ceiling_power(self, channel: int = 0) -> float:
        """Returns the edge climbing ceiling (92% of Tmax)."""
        tmax = self.channel_a_tmax if channel == 0 else self.channel_b_tmax
        return tmax * 0.92


class ToleranceTestRunner:
    def __init__(self, on_output_cmd: Callable[[int, float], None]):
        self.on_output_cmd = on_output_cmd
        self.profile = UserToleranceProfile()
        self.is_testing = False
        self.current_test_channel = 0
        self.current_ramp_power = 0.0
        self._ramp_start_time = 0.0

    def start_calibration(self, channel: int = 0):
        self.is_testing = True
        self.current_test_channel = channel
        self.current_ramp_power = 5.0
        self._ramp_start_time = time.time()
        self.on_output_cmd(channel, self.current_ramp_power)
        logger.info(f"[Tolerance Calibration] Starting Ramp Test on Channel {channel}...")

    def step_increase(self, step: float = 3.0) -> float:
        """Manually or automatically step up output power."""
        if not self.is_testing:
            return 0.0
        self.current_ramp_power = min(90.0, self.current_ramp_power + step)
        self.on_output_cmd(self.current_test_channel, self.current_ramp_power)
        return self.current_ramp_power

    def confirm_max_limit(self) -> UserToleranceProfile:
        """Player hits 'STOP / CONFIRM' when reaching maximum tolerable endurance."""
        self.is_testing = False
        self.on_output_cmd(self.current_test_channel, 0.0) # Instant cut-off

        if self.current_test_channel == 0:
            self.profile.channel_a_tmax = max(20.0, self.current_ramp_power)
            logger.info(f"✅ [Tolerance Calibration] Loop A (Core) Tmax Confirmed: {self.profile.channel_a_tmax:.0f}%")
        else:
            self.profile.channel_b_tmax = max(20.0, self.current_ramp_power)
            logger.info(f"✅ [Tolerance Calibration] Loop B (Legs) Tmax Confirmed: {self.profile.channel_b_tmax:.0f}%")

        self.profile.is_tested = True
        self.profile.timestamp = time.time()
        return self.profile
