"""
BDSM Sensory Conditioning & Dominance/Submission (D/s) Engine for OpenHaptic-Roleplay (v0.1.0)
Features:
1. Strict Posture Discipline (Kneeling, Hands Behind Back, Total Exposure)
2. Heavy Orgasm Denial & Ruined Spasm Penalties
3. Spanking / Shock Punishment Counter (simulates heavy whip strikes on Loop A/B)
4. Offline SafeWord Hardware Failsafe (SafeWord: "RED", "红色", "PINEAPPLE")
5. Gentle Aftercare & Recovery Mode
"""

import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any, List
from .game_mode_base import BaseGameMode, PlayerCombatStats
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.quad_channel_sequencer import QuadChannelSequencer, QuadHapticPattern
from ..core.gender_tuning import GenderTuningProfile
from ..core.kokoro_engine import InterruptibleVoiceEngine, VoicePriority

logger = logging.getLogger("BDSMEngine")


class BDSMPostureRule(str, Enum):
    KNEEL_SUBMISSION = "KNEEL_SUBMISSION"           # 绝对跪姿臣服 (双膝触地/躯干直立)
    HANDS_BEHIND_BACK = "HANDS_BEHIND_BACK"         # 双手背负 (严禁双手前伸遮挡)
    ABSOLUTE_FREEZE = "ABSOLUTE_FREEZE"             # 绝对禁动受罚 (微动即追加惩戒)


@dataclass
class BDSMStats(PlayerCombatStats):
    punishment_count: int = 0                       # 当前累计受罚抽击次数
    endurance_seconds: float = 0.0                  # 姿态达标维持时间
    is_aftercare_active: bool = False               # 是否处于事后温柔抚慰状态
    safeword_triggered: bool = False


class BDSMConditioningMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.current_rule = BDSMPostureRule.KNEEL_SUBMISSION
        self.bdsm_stats = BDSMStats()
        self.rule_start_time = time.time()
        self.rule_duration = 30.0
        self._last_violation_time = 0.0

    def start(self):
        super().start()
        self.bdsm_stats = BDSMStats(
            stage_title="⛓️ BDSM 规训阶段一：跪姿臣服，双手背在身后！"
        )
        self.current_rule = BDSMPostureRule.KNEEL_SUBMISSION
        self.rule_start_time = time.time()
        
        # Dominant opening announcement
        self.voice_engine.speak(
            "规训程序启动。跪好，双手背到身后，没有主人的允许，不准动一下。",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("BDSM_START", {"rule": self.current_rule.value})

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person or self.bdsm_stats.is_aftercare_active:
            return self.bdsm_stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        # ==========================================
        # 1. 严格姿态检测与违规判定
        # ==========================================
        is_violating = False
        violation_reason = ""

        # A. Hands Behind Back Check (Wrists must not be in front of hips or torso)
        l_wr, r_wr = pose.keypoints[9], pose.keypoints[10]
        if pose.hands_covering_core or pose.hands_extended_to_camera:
            is_violating = True
            violation_reason = "⚠️ 擅自防守！双手立刻背到身后！"

        # B. Kneeling Posture Check
        if self.current_rule == BDSMPostureRule.KNEEL_SUBMISSION:
            if not pose.is_kneeling and not pose.is_spine_collapsed:
                is_violating = True
                violation_reason = "⚠️ 姿态不端！立刻双膝下跪！"

        # ==========================================
        # 2. 违规抽击惩戒 (Punishment Strike)
        # ==========================================
        if is_violating:
            if now - self._last_violation_time > 1.8: # Cooldown between strikes
                self._last_violation_time = now
                self.bdsm_stats.punishment_count += 1
                self.bdsm_stats.magic_overload = min(100.0, self.bdsm_stats.magic_overload + 8.0)
                self.bdsm_stats.sanity_level = max(0.0, self.bdsm_stats.sanity_level - 10.0)

                # Heavy Shock Pulse simulating whip strike (88% of calibrated Tmax)
                strike_power = min(self.profile.safety_power_ceiling, 65.0)
                self.sequencer.driver.hit(channel=0, power=strike_power, decay_ms=180)
                self.sequencer.driver.hit(channel=1, power=strike_power * 0.9, decay_ms=180)

                # Preemptive Dominant Voice
                punish_lines = [
                    f"第 {self.bdsm_stats.punishment_count} 次违规惩戒！给我老实受着！",
                    f"擅自乱动，加罚一次！姿态重新摆好！",
                    f"还不长记性吗？双手给我背过去！"
                ]
                text = punish_lines[(self.bdsm_stats.punishment_count - 1) % len(punish_lines)]
                self.voice_engine.speak(text, priority=VoicePriority.HIGH_REACTION, interrupt_now=True)

                self.broadcast_event("BDSM_PUNISH", {
                    "count": self.bdsm_stats.punishment_count,
                    "power": strike_power,
                    "reason": violation_reason
                })
        else:
            # Posture compliant: slowly build endurance
            self.bdsm_stats.endurance_seconds += dt
            self.bdsm_stats.status_prompt = f"✅ 规训姿态保持达标中: {self.bdsm_stats.endurance_seconds:.0f}s"

        # ==========================================
        # 3. 达到极限后自动进入 Aftercare 抚慰阶段
        # ==========================================
        if self.bdsm_stats.endurance_seconds >= 60.0 or self.bdsm_stats.punishment_count >= 8:
            self.enter_aftercare()

        return self.bdsm_stats

    def enter_aftercare(self):
        """Transition into gentle Aftercare recovery mode."""
        self.bdsm_stats.is_aftercare_active = True
        self.bdsm_stats.stage_title = "💖 规训结束：进入事后温柔抚慰阶段 (Aftercare Mode)"
        
        # Gentle dual-loop wave soothing
        self.sequencer.driver.vibrate(channel=0, intensity=15.0)
        self.sequencer.driver.vibrate(channel=1, intensity=10.0)

        self.voice_engine.speak(
            "今天的规训表现得很乖……现在放松身体，主人会好好抚慰你的。",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("AFTERCARE_START", {})
        logger.info("💖 [BDSM Engine] Entered Aftercare soothing phase.")

    def trigger_safeword(self):
        """Hard emergency SafeWord triggered by offline voice or physical button."""
        self.bdsm_stats.safeword_triggered = True
        self.is_active = False
        self.sequencer.driver.stop_all() # HARD ZERO
        self.voice_engine.speak("安全词触发。所有硬件输出已立即切断，规训终止。", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
        self.broadcast_event("SAFEWORD_TRIGGERED", {})
        logger.warning("🚨 [BDSM SafeWord] HARD SHUTDOWN EXECUTED.")
