"""
Forced Compliance & Mandatory Restraint Gameplay Engine (Mode 3: 强制支配与姿态锁死)
Features:
- Mandatory Posture Enforcement (Kneel, Hands Behind Head, Legs Open)
- Hands-Off Weakpoint Defense Penalty (Shock burst forces hands away from Point 19 Core)
- Escalating Punishment Ladder (Auto-increases intensity until submissive surrender gesture)
"""

import time
import random
import logging
from enum import Enum
from typing import Optional, Callable, Dict, Any
from .game_mode_base import BaseGameMode, PlayerCombatStats
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.quad_channel_sequencer import QuadChannelSequencer, QuadHapticPattern
from ..core.gender_tuning import GenderTuningProfile

logger = logging.getLogger("ForcedComplianceMode")


class MandatoryTask(str, Enum):
    HANDS_BEHIND_HEAD = "HANDS_BEHIND_HEAD"       # 强制双手抱头锁死
    MANDATORY_KNEEL = "MANDATORY_KNEEL"           # 强制跪姿臣服
    LEGS_OPEN_EXPOSED = "LEGS_OPEN_EXPOSED"       # 强制双腿张开暴露传导器
    HANDS_OFF_CORE = "HANDS_OFF_CORE"             # 严禁防守！双手必须离开核心区


class ForcedComplianceMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.current_task = MandatoryTask.HANDS_OFF_CORE
        self.task_start_time = time.time()
        self.task_hold_duration = 20.0
        self.escalation_level = 1
        self.punishment_intensity = 30.0
        self._last_escalate_time = time.time()

    def start(self):
        super().start()
        self.escalation_level = 1
        self.punishment_intensity = 35.0
        self.current_task = MandatoryTask.HANDS_OFF_CORE
        self.task_start_time = time.time()
        self._last_escalate_time = time.time()
        
        self.stats = PlayerCombatStats(
            armor_hp=100.0,
            magic_overload=0.0,
            sanity_level=100.0,
            stage_title="⛓️ 强制规则一：严禁防守！双手立刻离开核心区！"
        )
        logger.info("[FORCED COMPLIANCE] Mandatory Enforcement Activated!")
        self.broadcast_event("FORCED_TASK", {
            "task": self.current_task.value,
            "desc": self.stats.stage_title,
            "duration": self.task_hold_duration
        })

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        # 1. Check Surrender / Mercy Release
        if pose.is_surrendering:
            self.stats.is_begging_mercy = True
            self.stats.stage_title = "🙇 玩家高举双手求饶！触手放缓强制压迫..."
            self.sequencer.driver.vibrate(channel=0, intensity=15.0)
            self.sequencer.driver.vibrate(channel=1, intensity=15.0)
            self.stats.magic_overload = max(0.0, self.stats.magic_overload - dt * 2.0)
            return self.stats
        else:
            self.stats.is_begging_mercy = False

        # 2. Continuous Ladder Escalation (Every 8 seconds power climbs +5%)
        if now - self._last_escalate_time > 8.0:
            self.escalation_level += 1
            self.punishment_intensity = min(self.profile.safety_power_ceiling, self.punishment_intensity + 6.0)
            self._last_escalate_time = now
            logger.info(f"[FORCED LADDER] Escalation Level {self.escalation_level} (Power: {self.punishment_intensity}%)")
            self.broadcast_event("LADDER_CLIMB", {"level": self.escalation_level, "power": self.punishment_intensity})

        # 3. Mandatory Task Verification Logic
        is_violating = False
        violation_reason = ""

        if self.current_task == MandatoryTask.HANDS_OFF_CORE:
            # Violation: Hands covering Point 19 Core
            if pose.hands_covering_core:
                is_violating = True
                violation_reason = "⚠️ 违规防守！双手捂住了核心传导器！触手强制放电破防！"
            else:
                # Compliant: Gentle baseline flow on Loop A
                self.sequencer.driver.vibrate(channel=0, intensity=25.0)
                self.sequencer.driver.vibrate(channel=1, intensity=15.0)

        elif self.current_task == MandatoryTask.HANDS_BEHIND_HEAD:
            # Violation: Hands dropped below shoulders
            l_wr, r_wr = pose.keypoints[9], pose.keypoints[10]
            l_sh, r_sh = pose.keypoints[5], pose.keypoints[6]
            if (l_wr[2] > 0.3 and l_wr[1] > l_sh[1]) or (r_wr[2] > 0.3 and r_wr[1] > r_sh[1]):
                is_violating = True
                violation_reason = "⚠️ 姿态变形！双手未抱在脑后！"

        elif self.current_task == MandatoryTask.MANDATORY_KNEEL:
            if not pose.is_kneeling and not pose.is_spine_collapsed:
                is_violating = True
                violation_reason = "⚠️ 未进入跪姿！触手强制压迫膝关节！"

        # 4. Enforce Instantaneous Physical Shock upon Violation!
        if is_violating:
            self.stats.current_combo = 0
            self.stats.magic_overload = min(100.0, self.stats.magic_overload + dt * 15.0)
            self.stats.sanity_level = max(0.0, self.stats.sanity_level - dt * 10.0)
            self.stats.status_prompt = violation_reason

            # Dual-circuit full punishment strike
            self.sequencer.driver.hit(channel=0, power=self.punishment_intensity, decay_ms=250)
            self.sequencer.driver.hit(channel=1, power=self.punishment_intensity * 0.9, decay_ms=250)
        else:
            self.stats.score_points += int(dt * 15)
            self.stats.current_combo += 1
            self.stats.status_prompt = "✅ 姿态保持达标，触手正在满意地收束"

        # 5. Rotate Tasks every hold duration
        if now - self.task_start_time > self.task_hold_duration:
            task_pool = [MandatoryTask.HANDS_OFF_CORE, MandatoryTask.HANDS_BEHIND_HEAD, MandatoryTask.MANDATORY_KNEEL]
            self.current_task = random.choice([t for t in task_pool if t != self.current_task])
            self.task_start_time = now
            self.task_hold_duration = random.uniform(15.0, 25.0)
            
            task_descs = {
                MandatoryTask.HANDS_OFF_CORE: "⛓️ 强制指令：严禁防守！双手立即离开核心区！",
                MandatoryTask.HANDS_BEHIND_HEAD: "⛓️ 强制指令：双手抱在脑后，保持绝对暴露！",
                MandatoryTask.MANDATORY_KNEEL: "⛓️ 强制指令：立刻单膝下跪/臣服！"
            }
            self.stats.stage_title = task_descs[self.current_task]
            self.broadcast_event("FORCED_TASK", {
                "task": self.current_task.value,
                "desc": self.stats.stage_title,
                "duration": self.task_hold_duration
            })

        if self.stats.magic_overload >= 100.0 or self.stats.sanity_level <= 0.0:
            self.stats.is_defeated = True
            self.stats.stage_title = "💀 意志彻底崩溃！已完全沦陷为触手的战败俘虏！"

        return self.stats

    def stop(self):
        super().stop()
        logger.info("[FORCED COMPLIANCE] Mode Stopped.")
