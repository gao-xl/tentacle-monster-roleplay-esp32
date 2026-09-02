"""
Red-Light Pose Freeze Challenge Mode (Mode 2: 触手木头人挑战)
Gameplay Rule:
- GREEN LIGHT: Player is allowed to adjust posture or breathe freely.
- RED LIGHT (Monster Watching!): Player must FREEZE and stay absolutely motionless!
- Motion Violation -> Immediate Electric Shock Penalty (HIT / FLOW)!
"""

import time
import random
import logging
from typing import Optional, Callable, Dict, Any
from .game_mode_base import BaseGameMode, PlayerCombatStats
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.quad_channel_sequencer import QuadChannelSequencer, QuadHapticPattern
from ..core.gender_tuning import GenderTuningProfile

logger = logging.getLogger("RedLightFreezeMode")


class RedLightFreezeMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.is_red_light = False
        self.phase_duration = 4.0
        self.phase_start_time = time.time()
        self.survival_seconds = 0.0
        self.violation_count = 0

    def start(self):
        super().start()
        self.is_red_light = False
        self.phase_duration = random.uniform(3.0, 6.0)
        self.phase_start_time = time.time()
        self.stats = PlayerCombatStats(
            armor_hp=100.0,
            magic_overload=0.0,
            sanity_level=100.0,
            stage_title="🟢 绿灯阶段：允许调整姿势"
        )
        self.broadcast_event("LIGHT_STATE", {"is_red_light": False, "duration": self.phase_duration})

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        # Phase Switcher (Green <-> Red)
        if now - self.phase_start_time > self.phase_duration:
            self.is_red_light = not self.is_red_light
            self.phase_start_time = now
            if self.is_red_light:
                # Turn RED! Monster watching
                self.phase_duration = random.uniform(3.0, 7.0)
                self.stats.stage_title = "🔴 红灯警报！触手正在注视，绝对不许动！"
                self.broadcast_event("LIGHT_STATE", {"is_red_light": True, "duration": self.phase_duration})
            else:
                # Turn GREEN! Free motion
                self.phase_duration = random.uniform(3.0, 5.0)
                self.stats.stage_title = "🟢 绿灯阶段：触手移开视线，允许活动"
                self.sequencer.driver.stop_all()
                self.broadcast_event("LIGHT_STATE", {"is_red_light": False, "duration": self.phase_duration})

        # Evaluate Motion Violation under RED LIGHT
        if self.is_red_light:
            # Struggle / Movement threshold: > 18.0 motion velocity is considered violation!
            if pose.struggle_score > 18.0 or pose.toe_curl_index > 45.0:
                self.violation_count += 1
                self.stats.current_combo = 0
                self.stats.magic_overload = min(100.0, self.stats.magic_overload + 8.0)
                self.stats.sanity_level = max(0.0, self.stats.sanity_level - 6.0)
                
                # Punish with instantaneous electric strike!
                hit_pwr = min(self.profile.safety_power_ceiling, 55.0 + self.violation_count * 3.0)
                logger.info(f"[RED LIGHT VIOLATION] Player moved (Score: {pose.struggle_score:.1f}) -> Punishment HIT ({hit_pwr}%)")
                self.sequencer.driver.hit(channel=0, power=hit_pwr, decay_ms=350)
                self.sequencer.driver.hit(channel=1, power=hit_pwr * 0.8, decay_ms=350)
                self.broadcast_event("VIOLATION", {"count": self.violation_count, "power": hit_pwr})
            else:
                # Perfect Freeze! Score increases
                self.survival_seconds += dt
                self.stats.score_points += int(dt * 10)
                self.stats.current_combo += 1
        else:
            # Under Green light, overload decays slightly
            self.stats.magic_overload = max(0.0, self.stats.magic_overload - dt * 1.5)

        if self.stats.magic_overload >= 100.0 or self.stats.sanity_level <= 0.0:
            self.stats.is_defeated = True
            self.stats.stage_title = "💀 挑战失败：魔力彻底过载战败！"

        return self.stats

    def stop(self):
        super().stop()
        logger.info("[GAMEPLAY] Red Light Freeze Mode Stopped.")
