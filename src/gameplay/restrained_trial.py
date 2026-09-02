"""
Restrained Conditioning & Hands-Free Puzzle Trial Engine for OpenHaptic-Roleplay (v0.1.0)
Gameplay Rule:
- Player is under STRICT PHYSICAL RESTRAINT (Hands bound behind back, Kneeling).
- Hands are FORBIDDEN. Player must solve challenges using ONLY Head Pose (Point 0 Nose vector)
  and Facial Emotion / Voice Chanting under continuous haptic distraction.
- Posture Violation / Timeout -> Immediate Shock Penalty & Ladder Escalation!
"""

import time
import math
import random
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List
from .game_mode_base import BaseGameMode, PlayerCombatStats
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.quad_channel_sequencer import QuadChannelSequencer, QuadHapticPattern
from ..core.gender_tuning import GenderTuningProfile
from ..core.kokoro_engine import InterruptibleVoiceEngine, VoicePriority

logger = logging.getLogger("RestrainedTrialMode")


@dataclass
class TargetNode:
    x_norm: float      # 0.0 - 1.0 screen target
    y_norm: float      # 0.0 - 1.0 screen target
    is_unlocked: bool = False
    lock_hold_time: float = 0.0 # Time player nose held inside target ring


class RestrainedTrialMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.targets: List[TargetNode] = []
        self.current_target_idx = 0
        self.trial_time_remaining = 45.0
        self.is_completed = False
        self._last_tick_time = time.time()
        self._last_shock_time = 0.0

    def start(self):
        super().start()
        self.trial_time_remaining = 45.0
        self.is_completed = False
        self.current_target_idx = 0
        
        # Generate 3 spatial target rings for nose-pointing puzzle
        self.targets = [
            TargetNode(x_norm=0.3, y_norm=0.35),
            TargetNode(x_norm=0.7, y_norm=0.35),
            TargetNode(x_norm=0.5, y_norm=0.65)
        ]

        self.stats = PlayerCombatStats(
            stage_title="⛓️ 拘束挑战启动：双手背负！用头部视线解锁魔法光圈！"
        )

        # Baseline teasing haptic distraction (Loop A + Loop B continuous wave)
        self.sequencer.driver.vibrate(channel=0, intensity=30.0)
        self.sequencer.driver.vibrate(channel=1, intensity=25.0)

        self.voice_engine.speak(
            "拘束挑战开始。双手不准离开身后，用你的头部微动对准光圈。在电流干扰下坚持住哦。",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("TRIAL_START", {
            "targets_count": len(self.targets),
            "time_limit": self.trial_time_remaining
        })

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person or self.is_completed:
            return self.stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now
        self.trial_time_remaining = max(0.0, self.trial_time_remaining - dt)

        # ==========================================
        # 1. 严格拘束校验 (Hands Strictly Behind Back)
        # ==========================================
        if pose.hands_covering_core or pose.hands_extended_to_camera:
            if now - self._last_shock_time > 1.5:
                self._last_shock_time = now
                self.stats.magic_overload = min(100.0, self.stats.magic_overload + 12.0)
                
                # Punish with sharp whip shock
                self.sequencer.driver.hit(channel=0, power=65.0, decay_ms=200)
                self.voice_engine.speak("警告！双手严禁前伸防守！加罚电击！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
                self.stats.status_prompt = "⚠️ 违规警告：双手必须死死背在身后！"
                return self.stats

        # ==========================================
        # 2. 头部姿态与光圈对准判定 (Nose Vector Pointing)
        # ==========================================
        if self.current_target_idx < len(self.targets):
            cur_target = self.targets[self.current_target_idx]
            
            # Nose Keypoint 0 (x, y normalized)
            nose_kpt = pose.keypoints[0]
            if nose_kpt[2] > 0.4:
                # Calculate distance between Nose and current Target Ring (assume normalized 0-1)
                # Map pixel coordinates to normalized screen ratio
                nx, ny = nose_kpt[0] / 640.0, nose_kpt[1] / 480.0
                dist = math.sqrt((nx - cur_target.x_norm)**2 + (ny - cur_target.y_norm)**2)

                # Within target radius (< 0.12)
                if dist < 0.12:
                    cur_target.lock_hold_time += dt
                    self.stats.status_prompt = f"🎯 正在锁定光圈 {self.current_target_idx + 1}/3 ({cur_target.lock_hold_time:.1f}s / 2.5s)"

                    # If held for 2.5 seconds -> UNLOCKED!
                    if cur_target.lock_hold_time >= 2.5:
                        cur_target.is_unlocked = True
                        self.current_target_idx += 1
                        self.voice_engine.speak("节点解锁成功！下一个！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
                        self.broadcast_event("NODE_UNLOCKED", {"unlocked_idx": self.current_target_idx})
                else:
                    cur_target.lock_hold_time = max(0.0, cur_target.lock_hold_time - dt * 0.5)

        # ==========================================
        # 3. 胜利或战败结算
        # ==========================================
        if self.current_target_idx >= len(self.targets):
            # VICTORY: All 3 Nodes Unlocked!
            self.is_completed = True
            self.stats.stage_title = "🎉 拘束通关成功！已成功解除拘束机关！"
            self.sequencer.driver.stop_all()
            self.voice_engine.speak("真厉害……居然在拘束状态下全解开了。今天算你过关啰~", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
            self.broadcast_event("TRIAL_VICTORY", {})

        elif self.trial_time_remaining <= 0.0 or self.stats.magic_overload >= 100.0:
            # DEFEAT: Timeout Failure -> Full Overload Burst!
            self.is_completed = True
            self.stats.is_defeated = True
            self.stats.stage_title = "💀 拘束挑战失败！超时过载爆发！"
            self.sequencer.trigger_pattern(QuadHapticPattern.FULL_BURST, duration_sec=2.0)
            self.voice_engine.speak("时间到！通关失败，接受完全过载的惩罚吧！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
            self.broadcast_event("TRIAL_DEFEAT", {})

        return self.stats

    def stop(self):
        super().stop()
        logger.info("[RestrainedTrialMode] Stopped.")
