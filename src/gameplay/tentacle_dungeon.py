"""
Tentacle Dungeon & Armor Breach Gameplay Mode (Mode 1)
Core Battle Loop:
- Stage 1: Probing -> Stage 2: Armor Breach -> Stage 3: Full Overload -> Stage 4: Subjugation
- Real-time defense breach mechanics against Point 19 Core
- Dual-circuit spatial FLOW traveling waves when feet spasm (Points 20-25)
- Begging & Surrender mercy system
"""

import time
import logging
from typing import Optional, Callable, Dict, Any
from .game_mode_base import BaseGameMode, PlayerCombatStats
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.quad_channel_sequencer import QuadChannelSequencer, QuadHapticPattern
from ..core.gender_tuning import GenderTuningProfile, UserGender

logger = logging.getLogger("TentacleDungeonMode")


class TentacleDungeonMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.stage_idx = 1
        self._last_hit_timestamp = 0.0
        self._last_flow_timestamp = 0.0

    def start(self):
        super().start()
        self.stats = PlayerCombatStats(
            armor_hp=100.0,
            magic_overload=0.0,
            sanity_level=100.0,
            stage_title="STAGE 1: 触手初遇试探 (Probing)"
        )
        logger.info("[GAMEPLAY] Tentacle Dungeon Mode Started!")
        self.broadcast_event("STAGE_START", {"stage": 1, "title": self.stats.stage_title})

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        # 1. Evaluate Surrender & Begging Gestures
        if pose.is_surrendering:
            self.stats.is_begging_mercy = True
            # Gentle tease vibration instead of hard hits
            self.sequencer.driver.vibrate(channel=0, intensity=20.0)
            self.sequencer.driver.vibrate(channel=1, intensity=15.0)
            self.stats.sanity_level = max(0.0, self.stats.sanity_level - dt * 2.5)
            self.stats.status_prompt = "双手高举求饶中... 触手放缓了攻势，正在享受战败者的顺从"
            return self.stats
        else:
            self.stats.is_begging_mercy = False

        # 2. Stage Progression Dynamics
        if self.stage_idx == 1:
            # Stage 1: Exploration
            self.stats.stage_title = "STAGE 1: 弱点试探 (Probing)"
            # If player guards Point 19 Core or time > 20s, escalate to Stage 2
            if pose.hands_covering_core or self.stats.magic_overload > 25.0:
                self.stage_idx = 2
                self.stats.stage_title = "STAGE 2: 护甲破防突袭 (Breach Attack!)"
                self.broadcast_event("STAGE_CHANGE", {"stage": 2, "title": self.stats.stage_title})

        elif self.stage_idx == 2:
            # Stage 2: Defense Breach
            # Attack Loop A (Core) or Evasion Chase to Loop B (Legs)
            if pose.hands_covering_core:
                # Player is resisting -> Break Armor!
                if now - self._last_hit_timestamp > 0.6:
                    hit_power = min(self.profile.safety_power_ceiling, 65.0)
                    self.sequencer.driver.hit(channel=0, power=hit_power, decay_ms=self.profile.decay_speed_ms)
                    self.stats.armor_hp = max(0.0, self.stats.armor_hp - 8.0)
                    self.stats.magic_overload = min(100.0, self.stats.magic_overload + 5.0)
                    self._last_hit_timestamp = now
                    self.broadcast_event("ARMOR_HIT", {"remaining_hp": self.stats.armor_hp})
            else:
                # Core exposed!
                self.stats.magic_overload = min(100.0, self.stats.magic_overload + dt * 4.0)

            if self.stats.armor_hp <= 10.0 or self.stats.magic_overload > 60.0:
                self.stage_idx = 3
                self.stats.stage_title = "STAGE 3: 魔力高频过载 (Overload Resonance!)"
                self.broadcast_event("STAGE_CHANGE", {"stage": 3, "title": self.stats.stage_title})

        elif self.stage_idx == 3:
            # Stage 3: Full Overload Traveling Wave
            # Trigger Spatial FLOW wave across 4 pads
            if now - self._last_flow_timestamp > 2.5:
                # Ascending traveling wave from Loop B -> Loop A
                self.sequencer.trigger_pattern(QuadHapticPattern.TRAVELING_ASCEND, duration_sec=2.0)
                self._last_flow_timestamp = now

            # Foot Toe Spasm check (Points 20-25)
            if pose.toe_curl_index > 35.0:
                self.stats.magic_overload = min(100.0, self.stats.magic_overload + dt * 8.0)
                self.stats.sanity_level = max(0.0, self.stats.sanity_level - dt * 5.0)

            if self.stats.magic_overload >= 95.0 or self.stats.sanity_level <= 10.0:
                self.stage_idx = 4
                self.stats.stage_title = "STAGE 4: 彻底战败与完全俘获 (Subjugation)"
                self.stats.is_defeated = True
                self.broadcast_event("STAGE_CHANGE", {"stage": 4, "title": self.stats.stage_title, "defeated": True})

        elif self.stage_idx == 4:
            # Stage 4: Subjugation
            self.stats.sanity_level = 0.0
            # Continuous alternating gentle pulse
            self.sequencer.trigger_pattern(QuadHapticPattern.ALTERNATING, duration_sec=3.0)

        return self.stats

    def stop(self):
        super().stop()
        logger.info("[GAMEPLAY] Tentacle Dungeon Mode Stopped.")
