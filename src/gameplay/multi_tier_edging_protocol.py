"""
Multi-Tier Edging & Grand Release Protocol for OpenHaptic-Roleplay (v0.1.0)
A complete, progressive 5-Act Physiological & Psychological Masterpiece:
1. Act 1: Awakening & Warmth (Gentle, low-frequency resonance 15-25%)
2. Act 2: Rising Escalation (Ascending spatial flow wave climbing to 55%)
3. Act 3: Triple-Edge Denial Chamber (3 consecutive razor-sharp edge cutoffs with 15s freeze holds)
4. Act 4: Grand Climax Release (Authorized full-power resonance & ecstatic burst)
5. Act 5: Sacred Aftercare (Delicate 8% soothing micro-waves & tender reawakening)
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

logger = logging.getLogger("EdgingProtocol")


class ProtocolAct(str, Enum):
    ACT1_AWAKENING = "ACT1_AWAKENING"           # 第一幕：平淡唤醒与温润共振 (0-40s)
    ACT2_ESCALATION = "ACT2_ESCALATION"         # 第二幕：感官升温与潮汐递进 (40-90s)
    ACT3_EDGE_1 = "ACT3_EDGE_1"                 # 第三幕：第一次边缘冲顶与断电 (Edge 1)
    ACT3_EDGE_2 = "ACT3_EDGE_2"                 # 第三幕：第二次边缘冲顶与断电 (Edge 2)
    ACT3_EDGE_3 = "ACT3_EDGE_3"                 # 第三幕：第三次极限边缘压制 (Edge 3)
    ACT4_GRAND_CLIMAX = "ACT4_GRAND_CLIMAX"     # 第四幕：神圣许可·大高潮全面爆发 (Grand Release)
    ACT5_AFTERCARE = "ACT5_AFTERCARE"           # 第五幕：事后温存与余韵抚慰 (Sacred Aftercare)


@dataclass
class ProtocolStats(PlayerCombatStats):
    current_act: ProtocolAct = ProtocolAct.ACT1_AWAKENING
    act_elapsed_sec: float = 0.0
    completed_edges: int = 0                    # 已完成的边缘掐灭次数 (0 - 3)
    arousal_index: float = 0.0                  # 综合快感与过载蓄积值 (0 - 100%)
    is_edge_holding: bool = False               # 是否正处于边缘掐灭后的绝对冷却惩罚中
    edge_hold_timer: float = 0.0


class MultiTierEdgingProtocolMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.p_stats = ProtocolStats()
        self.act_start_time = time.time()
        self._last_tick_time = time.time()

    def start(self):
        super().start()
        self.p_stats = ProtocolStats(
            current_act=ProtocolAct.ACT1_AWAKENING,
            stage_title="🕊️ 第一幕：平淡唤醒与温润共振 (Awakening & Warmth)"
        )
        self.act_start_time = time.time()

        # Gentle hypnotic whisper opening
        self.voice_engine.speak(
            "多重边缘控制仪式启动。闭上眼睛，放松全身。现在……微弱的暖意将从双腿开始慢慢唤醒你。",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("EDGING_ACT_CHANGE", {
            "act": self.p_stats.current_act.value,
            "title": "平淡唤醒与温润共振"
        })

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.p_stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now
        self.p_stats.act_elapsed_sec += dt

        # =========================================================================
        # 第一幕：平淡唤醒与温润共振 (0 - 35s)
        # =========================================================================
        if self.p_stats.current_act == ProtocolAct.ACT1_AWAKENING:
            # Low, gentle baseline micro-wave (12 - 22%)
            progress = min(1.0, self.p_stats.act_elapsed_sec / 35.0)
            pwr_a = 12.0 + progress * 10.0
            pwr_b = 10.0 + progress * 8.0
            self.sequencer.driver.vibrate(channel=0, intensity=pwr_a)
            self.sequencer.driver.vibrate(channel=1, intensity=pwr_b)
            self.p_stats.arousal_index = progress * 25.0
            self.p_stats.status_prompt = f"🕊️ 温润唤醒中：感受全身神经末梢的微弱共鸣 ({self.p_stats.act_elapsed_sec:.0f}s / 35s)"

            if self.p_stats.act_elapsed_sec >= 35.0:
                self.transition_to(ProtocolAct.ACT2_ESCALATION)

        # =========================================================================
        # 第二幕：感官升温与潮汐递进 (35 - 75s)
        # =========================================================================
        elif self.p_stats.current_act == ProtocolAct.ACT2_ESCALATION:
            progress = min(1.0, self.p_stats.act_elapsed_sec / 40.0)
            # Spatial traveling wave climbing up legs to pelvis (25 - 55%)
            pwr_a = 22.0 + progress * 30.0
            pwr_b = 18.0 + progress * 25.0
            self.sequencer.driver.vibrate(channel=0, intensity=pwr_a)
            self.sequencer.driver.vibrate(channel=1, intensity=pwr_b)
            self.p_stats.arousal_index = 25.0 + progress * 35.0 # Up to 60%
            self.p_stats.status_prompt = f"🌊 感官升温中：电流浪潮开始向骨盆核心攀爬聚集... ({self.p_stats.arousal_index:.0f}%)"

            if self.p_stats.act_elapsed_sec >= 40.0:
                self.transition_to(ProtocolAct.ACT3_EDGE_1)

        # =========================================================================
        # 第三幕：三重地狱边缘控制 (Triple-Edge Denial Chamber)
        # =========================================================================
        elif self.p_stats.current_act in [ProtocolAct.ACT3_EDGE_1, ProtocolAct.ACT3_EDGE_2, ProtocolAct.ACT3_EDGE_3]:
            # Sub-phase A: Rising toward razor-sharp Edge
            if not self.p_stats.is_edge_holding:
                edge_num = self.p_stats.completed_edges + 1
                ramp_speed = 1.0 + edge_num * 0.3
                self.p_stats.arousal_index = min(95.0, self.p_stats.arousal_index + dt * 4.5 * ramp_speed)

                # Heavy Climbing Power
                climb_power = min(self.profile.safety_power_ceiling * 0.9, 45.0 + self.p_stats.arousal_index * 0.4)
                self.sequencer.driver.vibrate(channel=0, intensity=climb_power)
                self.sequencer.driver.vibrate(channel=1, intensity=climb_power * 0.85)
                self.p_stats.status_prompt = f"🔥 第 {edge_num}/3 次边缘冲顶！浪潮直逼临界点！({self.p_stats.arousal_index:.0f}%)"

                # Trigger EDGE CUTOFF if Arousal >= 92% OR Toe Spasm detected!
                if self.p_stats.arousal_index >= 92.0 or pose.toe_curl_index > 40.0:
                    self._trigger_edge_denial_cutoff(edge_num)

            # Sub-phase B: Edge Holding & Forced Suppression (12s absolute dead silence)
            else:
                self.p_stats.edge_hold_timer -= dt
                self.p_stats.status_prompt = f"🚫 边缘掐灭惩戒中！把快感死死憋回去！({self.p_stats.edge_hold_timer:.1f}s)"
                
                if self.p_stats.edge_hold_timer <= 0:
                    self.p_stats.is_edge_holding = False
                    if self.p_stats.completed_edges == 1:
                        self.transition_to(ProtocolAct.ACT3_EDGE_2)
                    elif self.p_stats.completed_edges == 2:
                        self.transition_to(ProtocolAct.ACT3_EDGE_3)
                    elif self.p_stats.completed_edges >= 3:
                        self.transition_to(ProtocolAct.ACT4_GRAND_CLIMAX)

        # =========================================================================
        # 第四幕：神圣许可·大高潮全面爆发 (Grand Release / 25s)
        # =========================================================================
        elif self.p_stats.current_act == ProtocolAct.ACT4_GRAND_CLIMAX:
            # 100% Full-Burst Ecstatic Resonance
            pwr = min(self.profile.safety_power_ceiling, 85.0)
            self.sequencer.driver.vibrate(channel=0, intensity=pwr)
            self.sequencer.driver.vibrate(channel=1, intensity=pwr)
            self.p_stats.arousal_index = 100.0
            self.p_stats.magic_overload = 100.0
            self.p_stats.status_prompt = "🌋 【神圣许可大高潮！】所有的蓄积全面决堤爆发！彻底沉沦吧！"

            if self.p_stats.act_elapsed_sec >= 20.0:
                self.transition_to(ProtocolAct.ACT5_AFTERCARE)

        # =========================================================================
        # 第五幕：事后温存与余韵抚慰 (Sacred Aftercare)
        # =========================================================================
        elif self.p_stats.current_act == ProtocolAct.ACT5_AFTERCARE:
            # Delicate Soothing (8 - 10%)
            self.sequencer.driver.vibrate(channel=0, intensity=8.0)
            self.sequencer.driver.vibrate(channel=1, intensity=6.0)
            self.p_stats.stage_title = "💖 仪式圆满：进入事后温柔抚慰阶段 (Sacred Aftercare)"
            self.p_stats.status_prompt = "✨ 仪式完成：浪潮彻底退去……慢慢呼吸，享受这份纯洁的余韵吧。"

        return self.p_stats

    def _trigger_edge_denial_cutoff(self, edge_num: int):
        """Hard razor-sharp cutoff at the exact pinnacle of pleasure."""
        self.p_stats.is_edge_holding = True
        self.p_stats.edge_hold_timer = 12.0
        self.p_stats.completed_edges = edge_num
        self.sequencer.driver.stop_all() # INSTANT ZERO HARD CUT

        speech_lines = {
            1: "第一次冲顶……给我停！主人可没允许你高潮，把涌上来的感觉给我咽回去受着！",
            2: "第二次冲顶！还是不行哦……在悬崖边憋着的感觉，是不是更让你心痒难耐呢？",
            3: "第三次极限边缘！给我死死忍住！身体已经完全处于过载边缘了吧……很好！"
        }
        text = speech_lines.get(edge_num, "停！憋回去！")
        self.voice_engine.speak(text, priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
        self.broadcast_event("EDGE_DENIED", {"edge_count": edge_num})
        logger.info(f"🚫 [Edging Protocol] Edge {edge_num}/3 Triggered & Cut off!")

    def transition_to(self, act: ProtocolAct):
        self.p_stats.current_act = act
        self.p_stats.act_elapsed_sec = 0.0

        speech_map = {
            ProtocolAct.ACT2_ESCALATION: "很好，身体已经完全温热了。现在……电流浪潮将从小腿开始，成倍向上攀爬！",
            ProtocolAct.ACT3_EDGE_1: "注意了……第一波冲顶浪潮降临！好好体会快感直逼天灵盖的滋味！",
            ProtocolAct.ACT3_EDGE_2: "第二波浪潮再次攀升！这一次……会比刚才凶猛得多！",
            ProtocolAct.ACT3_EDGE_3: "最后一重地狱边缘！所有的神经都在尖叫了吧！给我咬紧牙关！",
            ProtocolAct.ACT4_GRAND_CLIMAX: "三重大门已经全部冲破！主人赐予你……绝对高潮的许可！全面释放吧！",
            ProtocolAct.ACT5_AFTERCARE: "嘘……结束了。所有的浪潮都退去了。做得非常好……现在彻底放松身心，享受属于你的余韵。"
        }
        if act in speech_map:
            self.voice_engine.speak(speech_map[act], priority=VoicePriority.HIGH_REACTION, interrupt_now=True)

        logger.info(f"🌊 [Edging Protocol] Act -> {act.value}")
        self.broadcast_event("EDGING_ACT_CHANGE", {"act": act.value})

    def stop(self):
        super().stop()
        logger.info("[MultiTierEdgingProtocolMode] Stopped.")
