"""
Sensory Cleaning & Posture Inspection Chamber (v0.1.0)
A deeply thematic SM Conditioning & Cleaning Discipline ritual:
- Phase 1: Cleansing Preparation & Posture Unveiling (Hands on head, spine upright, total exposure inspection)
- Phase 2: Dual-Loop Spatial Wipe & Purification (Traveling wave sweeping from legs up to core)
- Phase 3: Tremor & Compliance Audit (Any involuntary flinching/squirming triggers immediate chastisement pulse)
- Phase 4: Sanctified Purity Seal & Gentle Aftercare (Soothing recovery wave once fully cleansed)
"""

import time
import math
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List
from .game_mode_base import BaseGameMode, PlayerCombatStats
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.quad_channel_sequencer import QuadChannelSequencer, QuadHapticPattern
from ..core.gender_tuning import GenderTuningProfile
from ..core.kokoro_engine import InterruptibleVoiceEngine, VoicePriority

logger = logging.getLogger("CleaningDiscipline")


class CleaningPhase(str, Enum):
    INSPECTION_UNVEIL = "INSPECTION_UNVEIL"     # 阶段一：姿态呈检与完全暴露 (双手抱头/严禁遮挡)
    PURIFICATION_SWEEP = "PURIFICATION_SWEEP"   # 阶段二：双路空间涤荡清洗 (由下至上的流动清洗波)
    TREMOR_AUDIT = "TREMOR_AUDIT"               # 阶段三：静止受洗与微动稽查 (稍有颤抖即刻追加惩戒)
    SANCTIFIED_SEAL = "SANCTIFIED_SEAL"         # 阶段四：洗礼圆满与余韵封印


@dataclass
class CleaningStats(PlayerCombatStats):
    current_phase: CleaningPhase = CleaningPhase.INSPECTION_UNVEIL
    cleanliness_percent: float = 0.0            # 净化清洁进度 (0 - 100%)
    flinch_violations: int = 0                  # 洗礼过程中不规矩微动/躲闪惩罚次数
    hold_still_sec: float = 0.0


class CleaningDisciplineMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.clean_stats = CleaningStats()
        self.phase_start_time = time.time()
        self._last_flinch_shock = 0.0

    def start(self):
        super().start()
        self.clean_stats = CleaningStats(
            current_phase=CleaningPhase.INSPECTION_UNVEIL,
            stage_title="🧴 SM 侍奉与清洁调教启动：双手抱头，完全展开身体，接受清洁审视！"
        )
        self.phase_start_time = time.time()

        self.voice_engine.speak(
            "洗礼程序启动。双手抱在脑后，双膝跪好，把身体完全展现出来。洗礼过程中，一毫米都不准躲闪。",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("CLEANING_PHASE_START", {
            "phase": self.clean_stats.current_phase.value,
            "title": "姿态呈检与完全暴露"
        })

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.clean_stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        # =========================================================================
        # 阶段 1：姿态呈检与完全暴露 (双手必须抱头，严禁遮挡下腹核心)
        # =========================================================================
        if self.clean_stats.current_phase == CleaningPhase.INSPECTION_UNVEIL:
            l_wr, r_wr = pose.keypoints[9], pose.keypoints[10]
            l_ear, r_ear = pose.keypoints[3], pose.keypoints[4]
            
            # Hands behind head check: Wrists near/above ears
            hands_behind_head = (l_wr[2] > 0.3 and r_wr[2] > 0.3 and l_wr[1] < l_ear[1] + 40 and r_wr[1] < r_ear[1] + 40)
            
            if hands_behind_head and not pose.hands_covering_core:
                self.clean_stats.hold_still_sec += dt
                self.clean_stats.status_prompt = f"✨ 呈检姿态达标：受洗前审视中 ({self.clean_stats.hold_still_sec:.1f}s / 8s)"
                
                if self.clean_stats.hold_still_sec >= 8.0:
                    self.transition_to(CleaningPhase.PURIFICATION_SWEEP)
            else:
                self.clean_stats.hold_still_sec = max(0.0, self.clean_stats.hold_still_sec - dt)
                self.clean_stats.status_prompt = "⚠️ 姿态不合格！双手死死抱在脑后，不准遮挡身体！"

        # =========================================================================
        # 阶段 2：双路空间涤荡清洗 (空间流动波由下至上逐段清洗)
        # =========================================================================
        elif self.clean_stats.current_phase == CleaningPhase.PURIFICATION_SWEEP:
            self.clean_stats.cleanliness_percent = min(100.0, self.clean_stats.cleanliness_percent + dt * 4.0)

            # Cycle traveling wave sweeping from Loop B (Legs) up to Loop A (Core)
            sweep_cycle = (time.time() * 1.2) % 2.0
            if sweep_cycle < 1.0:
                # Sweep lower legs
                pwr = 25.0 + sweep_cycle * 15.0
                self.sequencer.driver.vibrate(channel=1, intensity=pwr)
                self.sequencer.driver.vibrate(channel=0, intensity=10.0)
                self.clean_stats.status_prompt = f"🌊 【触手清洁液擦拭下肢与足弓...】 ({self.clean_stats.cleanliness_percent:.0f}%)"
            else:
                # Sweep core
                pwr = 30.0 + (sweep_cycle - 1.0) * 20.0
                self.sequencer.driver.vibrate(channel=0, intensity=pwr)
                self.sequencer.driver.vibrate(channel=1, intensity=10.0)
                self.clean_stats.status_prompt = f"🌊 【触手清洗液深入核心区涤荡...】 ({self.clean_stats.cleanliness_percent:.0f}%)"

            if self.clean_stats.cleanliness_percent >= 50.0:
                self.transition_to(CleaningPhase.TREMOR_AUDIT)

        # =========================================================================
        # 阶段 3：静止受洗与微动稽查 (严禁任何扭动/躲闪/微动，违规即追加电击)
        # =========================================================================
        elif self.clean_stats.current_phase == CleaningPhase.TREMOR_AUDIT:
            self.clean_stats.cleanliness_percent = min(100.0, self.clean_stats.cleanliness_percent + dt * 3.5)

            # Flinch / Squirm Check (High speed movement or covering core)
            is_flinching = (pose.hands_covering_core or pose.struggle_velocity > 40.0)

            if is_flinching:
                if now - self._last_flinch_shock > 1.8:
                    self._last_flinch_shock = now
                    self.clean_stats.flinch_violations += 1
                    self.clean_stats.magic_overload = min(100.0, self.clean_stats.magic_overload + 15.0)

                    # Chastisement zap for moving during cleaning
                    strike_power = min(self.profile.safety_power_ceiling, 65.0)
                    self.sequencer.driver.hit(channel=0, power=strike_power, decay_ms=200)
                    
                    self.voice_engine.speak("不准乱躲！清洗时擅自扭动，加罚一次！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
                    self.clean_stats.status_prompt = f"💥 躲闪违规惩戒！第 {self.clean_stats.flinch_violations} 次记过！"
            else:
                # Compliant deep pulsing clean
                self.sequencer.driver.vibrate(channel=0, intensity=35.0)
                self.sequencer.driver.vibrate(channel=1, intensity=30.0)
                self.clean_stats.status_prompt = f"🧼 深度受洗中：身体保持绝对静止... ({self.clean_stats.cleanliness_percent:.0f}%)"

            if self.clean_stats.cleanliness_percent >= 100.0:
                self.transition_to(CleaningPhase.SANCTIFIED_SEAL)

        # =========================================================================
        # 阶段 4：洗礼圆满与余韵封印 (Aftercare & Seal)
        # =========================================================================
        elif self.clean_stats.current_phase == CleaningPhase.SANCTIFIED_SEAL:
            self.sequencer.driver.vibrate(channel=0, intensity=10.0)
            self.sequencer.driver.vibrate(channel=1, intensity=8.0)
            self.clean_stats.stage_title = "💖 洗礼圆满：身心已彻底净化，铭刻纯洁契约！"
            self.clean_stats.status_prompt = "✨ 洗礼完成：非常干净……现在你是主人最乖顺纯洁的私有物了。"

        return self.clean_stats

    def transition_to(self, phase: CleaningPhase):
        self.clean_stats.current_phase = phase
        speech_map = {
            CleaningPhase.PURIFICATION_SWEEP: "呈检合格。现在开始注入清洁流动液，从小腿到核心，好好体会全身被涤荡的感觉……",
            CleaningPhase.TREMOR_AUDIT: "接下来是深层净化。不管有多酥麻，一毫米都不准躲闪。乱动一下，立刻受罚。",
            CleaningPhase.SANCTIFIED_SEAL: "洗礼圆满完成……现在全身都变得干干净净、彻底顺从了呢。好好享受这份余韵吧。"
        }
        if phase in speech_map:
            self.voice_engine.speak(speech_map[phase], priority=VoicePriority.HIGH_REACTION, interrupt_now=True)

        logger.info(f"🧼 [Cleaning Discipline] Phase -> {phase.value}")
        self.broadcast_event("CLEANING_PHASE_START", {"phase": phase.value})

    def stop(self):
        super().stop()
        logger.info("[CleaningDisciplineMode] Stopped.")
