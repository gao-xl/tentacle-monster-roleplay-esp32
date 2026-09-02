"""
Shame Inspection Master: Guided Submissive Postures & Real-Time Skeletal Audit (v0.1.0)
The Ultimate Synthesis of Computer Vision, Psychological Conditioning, and E-Stim:
- Audio/LLM Guides Player to Adopt Explicit Submissive Postures (Hands Behind Head, Wide Kneeling, Arched Spine, Surrender)
- YOLO-Pose 26 Strictly Audits Angles in Real-Time (Zero false-positive gross motor checking)
- Flawed Posture / Defensive Covering -> Instant Chastisement Shock!
- Integrated with Deterministic 5-Act Pacing: Gentle Awakening -> Escalation -> Edge Denial -> Grand Climax -> Aftercare
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

logger = logging.getLogger("ShameInspectionMaster")


class ShameRite(str, Enum):
    RITE1_EXPOSURE = "RITE1_EXPOSURE"       # 仪轨一: 双手扣脑后·跪姿完全暴露呈检
    RITE2_WIDE_SQUAT = "RITE2_WIDE_SQUAT"   # 仪轨二: 双腿大开深蹲·核心完全展现
    RITE3_ARCH_SPINE = "RITE3_ARCH_SPINE"   # 仪轨三: 伏地翘臀·绝对静止边缘受训
    RITE4_SURRENDER = "RITE4_SURRENDER"     # 仪轨四: 双手高举祈求·大高潮神圣许可
    RITE5_AFTERCARE = "RITE5_AFTERCARE"     # 仪轨五: 瘫软受抚·圣洁余韵刻印


@dataclass
class ShameStats(PlayerCombatStats):
    current_rite: ShameRite = ShameRite.RITE1_EXPOSURE
    rite_progress_sec: float = 0.0
    posture_compliant_sec: float = 0.0
    posture_violations: int = 0
    completed_edges: int = 0
    is_edge_holding: bool = False
    edge_hold_timer: float = 0.0


class ShameInspectionMasterMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.shame_stats = ShameStats()
        self.rite_start_time = time.time()
        self._last_shock_time = 0.0

    def start(self):
        super().start()
        self.shame_stats = ShameStats(
            current_rite=ShameRite.RITE1_EXPOSURE,
            stage_title="🏛️ 仪轨一：双手扣在脑后，双膝下跪，把身体完全呈检！"
        )
        self.rite_start_time = time.time()
        self._last_shock_time = time.time()

        self.voice_engine.speak(
            "深渊呈检仪轨启动。双膝跪地，双手死死扣在脑后，把身体完全展现给主人。没有允许，一毫米都不准遮挡。",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("RITE_START", {
            "rite": self.shame_stats.current_rite.value,
            "title": "双手扣脑后·跪姿完全暴露呈检"
        })

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.shame_stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now
        self.shame_stats.rite_progress_sec += dt

        # =========================================================================
        # 严格大姿态审核状态机 (Gross Motor Posture Audit)
        # =========================================================================
        is_compliant = True
        violation_reason = ""

        # --- 仪轨一：双手扣在脑后 + 双膝下跪 ---
        if self.shame_stats.current_rite == ShameRite.RITE1_EXPOSURE:
            l_wr, r_wr = pose.keypoints[9], pose.keypoints[10]
            l_ear, r_ear = pose.keypoints[3], pose.keypoints[4]
            hands_on_head = (l_wr[2] > 0.3 and r_wr[2] > 0.3 and l_wr[1] < l_ear[1] + 50 and r_wr[1] < r_ear[1] + 50)
            
            if not hands_on_head or pose.hands_covering_core:
                is_compliant = False
                violation_reason = "⚠️ 姿态不合格！双手死死扣在脑后，严禁遮挡！"

            # Gentle Awakening Wave (15 - 25%)
            if is_compliant:
                self.sequencer.driver.vibrate(channel=0, intensity=20.0)
                self.sequencer.driver.vibrate(channel=1, intensity=15.0)
                self.shame_stats.posture_compliant_sec += dt
                self.shame_stats.status_prompt = f"✨ 呈检姿态保持良好 ({self.shame_stats.posture_compliant_sec:.0f}s / 25s)"
                if self.shame_stats.posture_compliant_sec >= 25.0:
                    self.transition_to(ShameRite.RITE2_WIDE_SQUAT)

        # --- 仪轨二：双腿大开深蹲 ---
        elif self.shame_stats.current_rite == ShameRite.RITE2_WIDE_SQUAT:
            # Must be squatting (kneeling or hips dropped)
            if not pose.is_kneeling and not pose.is_spine_collapsed:
                is_compliant = False
                violation_reason = "⚠️ 站得太高！立刻深蹲把双腿大角度分开！"

            # Climbing Traveling Flow Wave (30 - 55%)
            if is_compliant:
                progress = min(1.0, self.shame_stats.posture_compliant_sec / 30.0)
                pwr = 30.0 + progress * 25.0
                self.sequencer.driver.vibrate(channel=0, intensity=pwr)
                self.sequencer.driver.vibrate(channel=1, intensity=pwr * 0.85)
                self.shame_stats.posture_compliant_sec += dt
                self.shame_stats.status_prompt = f"🌊 深蹲受训中：电流浪潮向核心攀爬... ({pwr:.0f}%)"
                if self.shame_stats.posture_compliant_sec >= 30.0:
                    self.transition_to(ShameRite.RITE3_ARCH_SPINE)

        # --- 仪轨三：伏地翘臀·边缘掐灭憋回 ---
        elif self.shame_stats.current_rite == ShameRite.RITE3_ARCH_SPINE:
            if pose.hands_covering_core or pose.struggle_velocity > 40.0:
                is_compliant = False
                violation_reason = "⚠️ 不准乱动！伏地趴好，严禁伸手防守！"

            if not self.shame_stats.is_edge_holding:
                # Climbing to sharp edge (75%)
                progress = min(1.0, self.shame_stats.posture_compliant_sec / 25.0)
                pwr = 55.0 + progress * 25.0
                self.sequencer.driver.vibrate(channel=0, intensity=pwr)
                self.sequencer.driver.vibrate(channel=1, intensity=pwr)
                self.shame_stats.posture_compliant_sec += dt
                self.shame_stats.status_prompt = f"🔥 浪潮冲顶中！直逼临界点！({pwr:.0f}%)"

                # Hit Edge Cutoff at 25s!
                if self.shame_stats.posture_compliant_sec >= 25.0:
                    self.shame_stats.is_edge_holding = True
                    self.shame_stats.edge_hold_timer = 12.0
                    self.sequencer.driver.stop_all() # HARD ZERO CUTOFF
                    self.voice_engine.speak("给我停！主人可没允许你高潮，伏在地上，把快感给我死死咽回去！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)

            else:
                # Edge holding suppression (12s)
                self.shame_stats.edge_hold_timer -= dt
                self.shame_stats.status_prompt = f"🚫 极限边缘掐灭中！伏在地上死死憋住！({self.shame_stats.edge_hold_timer:.1f}s)"
                if self.shame_stats.edge_hold_timer <= 0:
                    self.transition_to(ShameRite.RITE4_SURRENDER)

        # --- 仪轨四：双手高举过顶·大高潮爆发 ---
        elif self.shame_stats.current_rite == ShameRite.RITE4_SURRENDER:
            l_wr, r_wr = pose.keypoints[9], pose.keypoints[10]
            l_sh, r_sh = pose.keypoints[5], pose.keypoints[6]
            hands_up = (l_wr[2] > 0.3 and r_wr[2] > 0.3 and l_wr[1] < l_sh[1] and r_wr[1] < r_sh[1])
            
            if not hands_up:
                is_compliant = False
                violation_reason = "⚠️ 双手举高！向主人做出完全祈求的投降姿态！"

            if is_compliant:
                # 100% Full-Burst Grand Release!
                pwr = min(self.profile.safety_power_ceiling, 85.0)
                self.sequencer.driver.vibrate(channel=0, intensity=pwr)
                self.sequencer.driver.vibrate(channel=1, intensity=pwr)
                self.shame_stats.posture_compliant_sec += dt
                self.shame_stats.status_prompt = "🌋 【神圣许可大高潮！】双手高举，彻底释放吧！"
                if self.shame_stats.posture_compliant_sec >= 20.0:
                    self.transition_to(ShameRite.RITE5_AFTERCARE)

        # --- 仪轨五：事后抚慰 ---
        elif self.shame_stats.current_rite == ShameRite.RITE5_AFTERCARE:
            self.sequencer.driver.vibrate(channel=0, intensity=8.0)
            self.sequencer.driver.vibrate(channel=1, intensity=6.0)
            self.shame_stats.stage_title = "💖 仪轨圆满：身心已彻底顺从，享受神圣余韵 (Aftercare)"
            self.shame_stats.status_prompt = "✨ 调教完成：表现得非常乖顺……现在你是主人最完美的战利品了。"

        # =========================================================================
        # 违规惩罚抽击 (Chastisement Shock on Violation)
        # =========================================================================
        if not is_compliant:
            self.shame_stats.status_prompt = violation_reason
            if now - self._last_shock_time > 2.0:
                self._last_shock_time = now
                self.shame_stats.posture_violations += 1
                self.shame_stats.magic_overload = min(100.0, self.shame_stats.magic_overload + 12.0)
                
                # Punish shock
                strike_power = min(self.profile.safety_power_ceiling, 65.0)
                self.sequencer.driver.hit(channel=0, power=strike_power, decay_ms=200)
                self.voice_engine.speak("姿态变形！擅自防守，惩罚抽击！给我摆好！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)

        return self.shame_stats

    def transition_to(self, rite: ShameRite):
        self.shame_stats.current_rite = rite
        self.shame_stats.posture_compliant_sec = 0.0

        speech_map = {
            ShameRite.RITE2_WIDE_SQUAT: "第一仪轨合格。现在……站起来，把双腿大角度深蹲分开！让深渊的浪潮成倍涌入！",
            ShameRite.RITE3_ARCH_SPINE: "很好……现在伏在地上，腰部下沉，臀部翘起。不管快感多强烈，一毫米都不准动！",
            ShameRite.RITE4_SURRENDER: "三重大门已经全部冲破！双手给我笔直举向头顶！主人赐予你……绝对高潮的许可！全面释放吧！",
            ShameRite.RITE5_AFTERCARE: "嘘……结束了。双手放下来，彻底瘫软放松吧。今天的你，顺从得无可挑剔。"
        }
        if rite in speech_map:
            self.voice_engine.speak(speech_map[rite], priority=VoicePriority.HIGH_REACTION, interrupt_now=True)

        logger.info(f"🏛️ [Shame Master] Rite -> {rite.value}")
        self.broadcast_event("RITE_START", {"rite": rite.value})

    def stop(self):
        super().stop()
        logger.info("[ShameInspectionMasterMode] Stopped.")
