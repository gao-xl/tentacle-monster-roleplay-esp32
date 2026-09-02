"""
Extreme Exhibition & High-Leg Exposure Chamber (v0.1.0)
High-Intensity Psychological Shame & Skeletal Kinematic Inspection:
- Posture 1: Asymmetrical Single High-Leg Lift (One foot grounded, one knee/ankle lifted to chest/hip height, total core exposure)
- Posture 2: Standing Deep M-Squat & Outward Pelvic Thrust (Wide stance, hips lowered below knees, core unveiled)
- Posture 3: Lying Butterfly / Wall Leg Spread (Back on ground, legs spread wide against camera/wall)
- Strict YOLO-Pose 26 Kinematic Checking: Joint angles, thigh elevation, hip-ankle height ratio.
- Involuntary defensive knee drops or hand covering -> Instant heavy shock strike!
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

logger = logging.getLogger("ExtremeExhibition")


class ExhibitionStage(str, Enum):
    STAGE1_LEFT_LEG_LIFT = "STAGE1_LEFT_LEG_LIFT"     # 阶段一: 单腿站立·左腿高抬大开 (抬腿暴露)
    STAGE2_RIGHT_LEG_LIFT = "STAGE2_RIGHT_LEG_LIFT"   # 阶段二: 单腿站立·右腿高抬大开 (换腿暴露)
    STAGE3_STANDING_M_SPLIT = "STAGE3_STANDING_M_SPLIT" # 阶段三: 站姿深M下蹲·骨盆前挺露出 (大开暴露)
    STAGE4_BUTTERFLY_RELEASE = "STAGE4_BUTTERFLY_RELEASE" # 阶段四: 仰卧蝴蝶大开·大高潮爆发 (绝对暴露大释放)
    STAGE5_AFTERCARE = "STAGE5_AFTERCARE"             # 阶段五: 瘫软受抚·余韵抚慰


@dataclass
class ExhibitionStats(PlayerCombatStats):
    current_stage: ExhibitionStage = ExhibitionStage.STAGE1_LEFT_LEG_LIFT
    stage_hold_sec: float = 0.0
    violation_count: int = 0
    leg_lift_height_ratio: float = 0.0


class ExtremeExhibitionMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.ex_stats = ExhibitionStats()
        self.stage_start_time = time.time()
        self._last_shock_time = 0.0

    def start(self):
        super().start()
        self.ex_stats = ExhibitionStats(
            current_stage=ExhibitionStage.STAGE1_LEFT_LEG_LIFT,
            stage_title="🦵 阶段一：单腿站立·左腿高高抬起大开，核心区完全呈检暴露！"
        )
        self.stage_start_time = time.time()
        self._last_shock_time = time.time()

        self.voice_engine.speak(
            "高阶露出呈检仪轨启动。双手抱在脑后，把左腿高高抬起，向镜头完全展开你的核心防线。没有允许，不准放下来。",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("EXHIBITION_STAGE_START", {
            "stage": self.ex_stats.current_stage.value,
            "title": "单腿站立·左腿高抬露出"
        })

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.ex_stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        is_compliant = True
        violation_reason = ""

        # Keypoints
        l_hip, r_hip = pose.keypoints[11], pose.keypoints[12]
        l_knee, r_knee = pose.keypoints[13], pose.keypoints[14]
        l_ank, r_ank = pose.keypoints[15], pose.keypoints[16]
        l_wr, r_wr = pose.keypoints[9], pose.keypoints[10]

        # 0. Global Defense Breach Check: Hands strictly forbidden from covering core
        if pose.hands_covering_core:
            is_compliant = False
            violation_reason = "⚠️ 擅自防守！双手立刻抱在脑后，不准遮挡露出部位！"

        # =========================================================================
        # 阶段一：单腿站立·左腿高抬大开 (Left Leg Lift)
        # =========================================================================
        elif self.ex_stats.current_stage == ExhibitionStage.STAGE1_LEFT_LEG_LIFT:
            # Check left ankle significantly higher than right ankle (Left leg lifted above knee height)
            if l_ank[2] > 0.3 and r_ank[2] > 0.3:
                # Left ankle Y must be noticeably higher (smaller pixel value) than right ankle
                height_diff = r_ank[1] - l_ank[1]
                if height_diff < 70.0: # Lifted less than ~70px
                    is_compliant = False
                    violation_reason = "⚠️ 抬得不够高！把左腿给我高高抬起来大开！"
                else:
                    self.ex_stats.leg_lift_height_ratio = height_diff
            else:
                is_compliant = False

            if is_compliant:
                # Flow pulse climbing through lifted leg
                self.sequencer.driver.vibrate(channel=1, intensity=28.0) # Leg Loop
                self.sequencer.driver.vibrate(channel=0, intensity=20.0) # Core Loop
                self.ex_stats.stage_hold_sec += dt
                self.ex_stats.status_prompt = f"✨ 左腿高抬保持良好：受审中 ({self.ex_stats.stage_hold_sec:.0f}s / 20s)"
                if self.ex_stats.stage_hold_sec >= 20.0:
                    self.transition_to(ExhibitionStage.STAGE2_RIGHT_LEG_LIFT)

        # =========================================================================
        # 阶段二：单腿站立·右腿高抬大开 (Right Leg Lift)
        # =========================================================================
        elif self.ex_stats.current_stage == ExhibitionStage.STAGE2_RIGHT_LEG_LIFT:
            # Check right ankle significantly higher than left ankle
            if l_ank[2] > 0.3 and r_ank[2] > 0.3:
                height_diff = l_ank[1] - r_ank[1]
                if height_diff < 70.0:
                    is_compliant = False
                    violation_reason = "⚠️ 换腿太慢！把右腿高高抬起展开！"
                else:
                    self.ex_stats.leg_lift_height_ratio = height_diff
            else:
                is_compliant = False

            if is_compliant:
                self.sequencer.driver.vibrate(channel=1, intensity=35.0)
                self.sequencer.driver.vibrate(channel=0, intensity=28.0)
                self.ex_stats.stage_hold_sec += dt
                self.ex_stats.status_prompt = f"✨ 右腿高抬保持良好：受审中 ({self.ex_stats.stage_hold_sec:.0f}s / 20s)"
                if self.ex_stats.stage_hold_sec >= 20.0:
                    self.transition_to(ExhibitionStage.STAGE3_STANDING_M_SPLIT)

        # =========================================================================
        # 阶段三：站姿深M下蹲·骨盆前挺大开露出 (Deep M-Squat Pelvic Exposure)
        # =========================================================================
        elif self.ex_stats.current_stage == ExhibitionStage.STAGE3_STANDING_M_SPLIT:
            # Squat + Wide Legs: Knees lower, hips sink, wide distance between ankles
            ank_dist = abs(l_ank[0] - r_ank[0])
            is_squatting = (pose.is_kneeling or pose.is_spine_collapsed or (l_hip[1] > 260 and r_hip[1] > 260))

            if not is_squatting or ank_dist < 120.0:
                is_compliant = False
                violation_reason = "⚠️ 姿态不端！双腿大角度分开深蹲，把骨盆完全挺出来！"

            if is_compliant:
                # Heavy Rising Traveling Wave (35 - 65%)
                progress = min(1.0, self.ex_stats.stage_hold_sec / 25.0)
                pwr = 35.0 + progress * 30.0
                self.sequencer.driver.vibrate(channel=0, intensity=pwr)
                self.sequencer.driver.vibrate(channel=1, intensity=pwr * 0.9)
                self.ex_stats.stage_hold_sec += dt
                self.ex_stats.status_prompt = f"🌊 深M露出受训中：电流向核心强力汇聚... ({pwr:.0f}%)"
                if self.ex_stats.stage_hold_sec >= 25.0:
                    self.transition_to(ExhibitionStage.STAGE4_BUTTERFLY_RELEASE)

        # =========================================================================
        # 阶段四：仰卧/大开·大高潮神圣释放 (Grand Climax in Total Exposure)
        # =========================================================================
        elif self.ex_stats.current_stage == ExhibitionStage.STAGE4_BUTTERFLY_RELEASE:
            # 100% Full Burst in Absolute Exposure
            pwr = min(self.profile.safety_power_ceiling, 85.0)
            self.sequencer.driver.vibrate(channel=0, intensity=pwr)
            self.sequencer.driver.vibrate(channel=1, intensity=pwr)
            self.ex_stats.stage_hold_sec += dt
            self.ex_stats.status_prompt = "🌋 【完全露出状态下的大高潮！】神圣许可已赐予！彻底释放吧！"
            if self.ex_stats.stage_hold_sec >= 20.0:
                self.transition_to(ExhibitionStage.STAGE5_AFTERCARE)

        # =========================================================================
        # 阶段五：事后抚慰 (Aftercare)
        # =========================================================================
        elif self.ex_stats.current_stage == ExhibitionStage.STAGE5_AFTERCARE:
            self.sequencer.driver.vibrate(channel=0, intensity=8.0)
            self.sequencer.driver.vibrate(channel=1, intensity=6.0)
            self.ex_stats.stage_title = "💖 露出仪轨圆满：身心彻底臣服，享受神圣余韵 (Aftercare)"
            self.ex_stats.status_prompt = "✨ 调教完成：完全展开身体的样子非常乖顺……现在放松休息吧。"

        # =========================================================================
        # 违规惩罚抽击 (Chastisement Shock on Violation)
        # =========================================================================
        if not is_compliant:
            self.ex_stats.status_prompt = violation_reason
            if now - self._last_shock_time > 1.8:
                self._last_shock_time = now
                self.ex_stats.violation_count += 1
                self.ex_stats.magic_overload = min(100.0, self.ex_stats.magic_overload + 14.0)

                # Heavy strike
                strike_power = min(self.profile.safety_power_ceiling, 65.0)
                self.sequencer.driver.hit(channel=0, power=strike_power, decay_ms=220)
                self.voice_engine.speak("不准放下来！擅自防守或合拢，惩罚抽击！给我把腿抬高！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)

        return self.ex_stats

    def transition_to(self, stage: ExhibitionStage):
        self.ex_stats.current_stage = stage
        self.ex_stats.stage_hold_sec = 0.0

        speech_map = {
            ExhibitionStage.STAGE2_RIGHT_LEG_LIFT: "左腿呈检合格。现在……换右腿高高抬起！把身体完全展现出来！",
            ExhibitionStage.STAGE3_STANDING_M_SPLIT: "很好……现在双腿大角度深蹲分开，腰部下沉，骨盆前挺。让电流浪潮毫无阻碍地灌满核心！",
            ExhibitionStage.STAGE4_BUTTERFLY_RELEASE: "所有防线已彻底瓦解！在完全展开的姿态下……主人赐予你大高潮许可！全面爆发吧！",
            ExhibitionStage.STAGE5_AFTERCARE: "嘘……结束了。双腿放平瘫软下来吧。今天的你，顺从得极度纯粹。"
        }
        if stage in speech_map:
            self.voice_engine.speak(speech_map[stage], priority=VoicePriority.HIGH_REACTION, interrupt_now=True)

        logger.info(f"🦵 [Extreme Exhibition] Stage -> {stage.value}")
        self.broadcast_event("EXHIBITION_STAGE_START", {"stage": stage.value})

    def stop(self):
        super().stop()
        logger.info("[ExtremeExhibitionMode] Stopped.")
