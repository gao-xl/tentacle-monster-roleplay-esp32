"""
Guided Sensory Hypnosis & Interactive Conditioning Master for OpenHaptic-Roleplay (v0.1.0)
A deeply immersive, step-by-step psychological & physical conditioning experience:
1. Stage 0: Breathing Synchronization & Hypnotic Induction (4-7-8 Breath Resonance with gentle haptic swell)
2. Stage 1: Tactile Focus & Body Scan (Directing attention to specific pad clusters)
3. Stage 2: Micro-Command Obedience (Head nod/tilt, blink synchronization, posture calibration)
4. Stage 3: Sensory Calibration & Submission Contract (Pacing pulse building toward climax threshold)
5. Stage 4: Sensory Climax & Post-Hypnotic Aftercare Soothing
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

logger = logging.getLogger("GuidedConditioning")


class GuidedPhase(str, Enum):
    INDUCTION_BREATH = "INDUCTION_BREATH"       # 阶段一：催眠呼吸同调 (4-7-8 呼吸引导)
    BODY_SCAN_FOCUS = "BODY_SCAN_FOCUS"         # 阶段二：感官身体扫描 (意识引导与贴片触觉聚焦)
    OBEDIENCE_CALIBRATION = "OBEDIENCE"         # 阶段三：微指令绝对服从 (点头/闭眼/微动校准)
    SENSORY_ASCENT = "SENSORY_ASCENT"           # 阶段四：感官层层递进攀升 (循序渐进的支配波)
    AFTERCARE_TRANQUIL = "AFTERCARE_TRANQUIL"   # 阶段五：深度唤醒与温柔余韵抚慰


@dataclass
class GuidedStats(PlayerCombatStats):
    current_phase: GuidedPhase = GuidedPhase.INDUCTION_BREATH
    phase_progress_sec: float = 0.0
    breath_cycle_phase: str = "INHALE"          # "INHALE" (吸气), "HOLD" (屏息), "EXHALE" (呼气)
    breath_cycle_sec: float = 0.0
    obedience_score: int = 0
    whisper_prompt: str = ""


class GuidedConditioningMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.guided_stats = GuidedStats()
        self.phase_start_time = time.time()
        self.breath_timer = 0.0
        self._last_whisper_time = 0.0

    def start(self):
        super().start()
        self.guided_stats = GuidedStats(
            current_phase=GuidedPhase.INDUCTION_BREATH,
            stage_title="🧘 引导调教阶段一：呼吸同调与意识沉降 (Hypnotic Breath Sync)"
        )
        self.phase_start_time = time.time()
        self.breath_timer = 0.0
        self._last_whisper_time = time.time()

        # Hypnotic warm whisper
        self.voice_engine.speak(
            "闭上双眼，把所有的杂念都抛在脑后……现在，跟着我的声音和身体上的微弱起伏，深深地吸气……",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("GUIDED_PHASE_CHANGE", {
            "phase": self.guided_stats.current_phase.value,
            "title": "呼吸同调与意识沉降"
        })

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.guided_stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now
        self.guided_stats.phase_progress_sec += dt
        self.breath_timer += dt

        # =========================================================================
        # 阶段 1：呼吸同调与感官共振 (Breath Synchronization & Swell Haptics)
        # =========================================================================
        if self.guided_stats.current_phase == GuidedPhase.INDUCTION_BREATH:
            # 19-second cycle (Inhale 4s, Hold 7s, Exhale 8s)
            cycle_pos = self.breath_timer % 19.0
            
            if cycle_pos < 4.0:
                self.guided_stats.breath_cycle_phase = "INHALE"
                # Gentle rising haptic swell matching inhale
                progress = cycle_pos / 4.0
                intensity = 10.0 + progress * 15.0
                self.sequencer.driver.vibrate(channel=0, intensity=intensity)
                self.sequencer.driver.vibrate(channel=1, intensity=intensity * 0.8)
                self.guided_stats.status_prompt = f"🌬️ 【深深吸气...】 (感官随气息慢慢唤醒: {cycle_pos:.1f}s / 4s)"
                
            elif cycle_pos < 11.0:
                self.guided_stats.breath_cycle_phase = "HOLD"
                # Stable warm pulsing resonance
                self.sequencer.driver.vibrate(channel=0, intensity=25.0)
                self.sequencer.driver.vibrate(channel=1, intensity=20.0)
                self.guided_stats.status_prompt = f"🧘 【屏住呼吸，感受身体的温热与微麻...】 ({cycle_pos - 4.0:.1f}s / 7s)"
                
            else:
                self.guided_stats.breath_cycle_phase = "EXHALE"
                # Fading release haptics
                progress = (cycle_pos - 11.0) / 8.0
                intensity = max(5.0, 25.0 * (1.0 - progress))
                self.sequencer.driver.vibrate(channel=0, intensity=intensity)
                self.sequencer.driver.vibrate(channel=1, intensity=intensity * 0.7)
                self.guided_stats.status_prompt = f"💨 【缓缓呼气... 身体彻底放松下来...】 ({cycle_pos - 11.0:.1f}s / 8s)"

            # Advance to Phase 2 after 3 complete breath cycles (approx 38s)
            if self.guided_stats.phase_progress_sec >= 38.0:
                self.transition_to_phase(GuidedPhase.BODY_SCAN_FOCUS)

        # =========================================================================
        # 阶段 2：感官身体扫描 (Body Scan & Pad Focus)
        # =========================================================================
        elif self.guided_stats.current_phase == GuidedPhase.BODY_SCAN_FOCUS:
            # Alternate focus between Loop A (Core) and Loop B (Legs)
            scan_cycle = int(self.guided_stats.phase_progress_sec) % 10
            if scan_cycle < 5:
                # Focus Loop B (Legs)
                self.sequencer.driver.vibrate(channel=0, intensity=0.0)
                self.sequencer.driver.vibrate(channel=1, intensity=28.0)
                self.guided_stats.status_prompt = "✨ 【把注意力集中到你的小腿和脚踝... 感受电流的微微跳动】"
            else:
                # Focus Loop A (Core)
                self.sequencer.driver.vibrate(channel=0, intensity=32.0)
                self.sequencer.driver.vibrate(channel=1, intensity=0.0)
                self.guided_stats.status_prompt = "✨ 【把注意力上移到双腿根部与核心区... 感受逐渐聚集的温热与紧绷】"

            if self.guided_stats.phase_progress_sec >= 30.0:
                self.transition_to_phase(GuidedPhase.OBEDIENCE_CALIBRATION)

        # =========================================================================
        # 阶段 3：微指令互动服从 (Micro-Command Obedience)
        # =========================================================================
        elif self.guided_stats.current_phase == GuidedPhase.OBEDIENCE_CALIBRATION:
            # Instruct player to nod head slowly
            nose = pose.keypoints[0]
            self.guided_stats.status_prompt = "🙇 【慢慢低下头，向主人致以顺从的微俯首...】"
            
            # Detect head tilt downward (Nose Y lower than neutral)
            if nose[2] > 0.4 and pose.is_spine_collapsed:
                self.guided_stats.obedience_score += 1
                self.guided_stats.status_prompt = "✅ 【非常乖……很好地遵从了指令。】"
                self.sequencer.driver.vibrate(channel=0, intensity=15.0)

            if self.guided_stats.phase_progress_sec >= 25.0:
                self.transition_to_phase(GuidedPhase.SENSORY_ASCENT)

        # =========================================================================
        # 阶段 4：感官层层递进攀升 (Sensory Climbing Wave)
        # =========================================================================
        elif self.guided_stats.current_phase == GuidedPhase.SENSORY_ASCENT:
            # Gradually ramp up spatial traveling wave toward calibrated Tmax
            progress = min(1.0, self.guided_stats.phase_progress_sec / 40.0)
            power_a = 20.0 + progress * (self.profile.calibrated_tmax_a * 0.85 - 20.0)
            power_b = 15.0 + progress * (self.profile.calibrated_tmax_b * 0.85 - 15.0)

            # Modulate spatial wave
            self.sequencer.driver.vibrate(channel=0, intensity=power_a)
            self.sequencer.driver.vibrate(channel=1, intensity=power_b)
            self.guided_stats.magic_overload = progress * 100.0
            self.guided_stats.status_prompt = f"🌊 【感官攀升中... 不要抗拒，把身心完全交出来...】 (过载: {self.guided_stats.magic_overload:.0f}%)"

            if self.guided_stats.phase_progress_sec >= 40.0:
                self.transition_to_phase(GuidedPhase.AFTERCARE_TRANQUIL)

        # =========================================================================
        # 阶段 5：深度唤醒与温柔抚慰 (Aftercare & Reawakening)
        # =========================================================================
        elif self.guided_stats.current_phase == GuidedPhase.AFTERCARE_TRANQUIL:
            # Softest, delicate afterglow
            self.sequencer.driver.vibrate(channel=0, intensity=10.0)
            self.sequencer.driver.vibrate(channel=1, intensity=8.0)
            self.guided_stats.status_prompt = "💖 【引导完成：慢慢睁开双眼，感受全身通透的宁静与余韵...】"

        return self.guided_stats

    def transition_to_phase(self, new_phase: GuidedPhase):
        """Smoothly transitions to next guided hypnotic phase with tailored voice narration."""
        self.guided_stats.current_phase = new_phase
        self.guided_stats.phase_progress_sec = 0.0

        speech_map = {
            GuidedPhase.BODY_SCAN_FOCUS: "做得很好……现在，把你的全部意识，转移到小腿与核心传导器上。感受电流在皮肤深处的微弱脉动。",
            GuidedPhase.OBEDIENCE_CALIBRATION: "很好，你的呼吸已经完全平静下来了。现在，听从指令，微微低下头，表示你的完全顺从……",
            GuidedPhase.SENSORY_ASCENT: "很好……现在，允许自己彻底沉浸。无论浪潮变得多么汹涌，都不要抵抗，乖乖接纳所有涌上来的感觉……",
            GuidedPhase.AFTERCARE_TRANQUIL: "嘘……结束了。所有的浪潮都退去了。慢慢睁开眼睛，今天的你……表现得非常完美。"
        }

        if new_phase in speech_map:
            self.voice_engine.speak(speech_map[new_phase], priority=VoicePriority.HIGH_REACTION, interrupt_now=True)

        logger.info(f"🧘 [Guided Conditioning] Transitioned to phase: {new_phase.value}")
        self.broadcast_event("GUIDED_PHASE_CHANGE", {
            "phase": new_phase.value,
            "title": str(new_phase.value)
        })

    def stop(self):
        super().stop()
        logger.info("[GuidedConditioningMode] Stopped.")
