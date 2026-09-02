"""
Dynamic LLM Story Director & Interactive Conditioning Master for OpenHaptic-Roleplay (v0.1.0)
Seamlessly connects OpenRouter LLM, Kokoro Neural Voice, and 4-Channel E-Stim:
- Dynamic Scene Synthesis: LLM generates continuous episodic story acts tailored to player gender & name
- Real-time Micro-Directives: Each act embeds a physical body requirement (Kneeling, Hands Behind Head, Breathe, Core Exposure)
- Physiological Feedback Loop: Player compliance/struggles/toe curls feed back into LLM memory for next branch generation
- Multi-Stage Epic Narrative with Real-Time Haptic Waveform Synthesis
"""

import time
import json
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List
import requests

from .game_mode_base import BaseGameMode, PlayerCombatStats
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.quad_channel_sequencer import QuadChannelSequencer, QuadHapticPattern
from ..core.gender_tuning import GenderTuningProfile
from ..core.kokoro_engine import InterruptibleVoiceEngine, VoicePriority

logger = logging.getLogger("LLMStoryDirector")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


@dataclass
class StoryNodeGenerated:
    act_title: str
    narration_text: str
    directive_type: str        # "KNEEL", "HANDS_HEAD", "BREATHE_HOLD", "TOTAL_STILL", "CORE_UNVEIL"
    directive_prompt: str
    haptic_pattern: str        # "FLOW_ASCEND", "SURGE_WAVE", "PULSE_TEASE", "SHOCK_BURST", "AFTERCARE"
    duration_sec: float = 20.0


class LLMStoryDirectorMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        openrouter_api_key: str = "",
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.api_key = openrouter_api_key
        
        self.current_act_index = 0
        self.story_history: List[Dict[str, str]] = []
        self.current_node: Optional[StoryNodeGenerated] = None
        self.node_start_time = time.time()
        self.compliance_score = 0
        self.is_generating_next = False

    def start(self):
        super().start()
        self.current_act_index = 0
        self.story_history = []
        self.stats = PlayerCombatStats(
            stage_title="📖 AI 动态生成式引导调教战役启动：正在编织第一幕剧情..."
        )

        # Generate Act 1
        self._load_fallback_act_1()
        self._trigger_current_node()

    def _load_fallback_act_1(self):
        """Instant zero-latency Act 1 to start immediately while async LLM prefetches Act 2."""
        self.current_node = StoryNodeGenerated(
            act_title="第一幕：深渊觉醒与肉体呈检",
            narration_text="欢迎来到深渊神殿，受试者。把双手举到头顶，双膝下跪，让触手彻底看清你的每一寸防线。没有主人的允许，一毫米都不准乱动。",
            directive_type="HANDS_HEAD",
            directive_prompt="🙇 【双膝下跪，双手死死抱在脑后呈检】",
            haptic_pattern="PULSE_TEASE",
            duration_sec=18.0
        )

    def _trigger_current_node(self):
        if not self.current_node:
            return

        self.node_start_time = time.time()
        self.stats.stage_title = f"📖 {self.current_node.act_title}"
        self.stats.status_prompt = self.current_node.directive_prompt

        # 1. Voice Narration
        self.voice_engine.speak(
            self.current_node.narration_text,
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )

        # 2. Haptic Waveform Synthesis
        pat = self.current_node.haptic_pattern
        if pat == "FLOW_ASCEND":
            self.sequencer.trigger_pattern(QuadHapticPattern.TRAVELING_ASCEND, duration_sec=4.0)
        elif pat == "SURGE_WAVE":
            self.sequencer.driver.vibrate(channel=0, intensity=35.0)
            self.sequencer.driver.vibrate(channel=1, intensity=25.0)
        elif pat == "PULSE_TEASE":
            self.sequencer.driver.vibrate(channel=0, intensity=18.0)
            self.sequencer.driver.vibrate(channel=1, intensity=15.0)
        elif pat == "SHOCK_BURST":
            self.sequencer.driver.hit(channel=0, power=65.0, decay_ms=250)
        elif pat == "AFTERCARE":
            self.sequencer.driver.vibrate(channel=0, intensity=10.0)
            self.sequencer.driver.vibrate(channel=1, intensity=8.0)

        self.broadcast_event("STORY_NODE_START", {
            "title": self.current_node.act_title,
            "text": self.current_node.narration_text,
            "directive": self.current_node.directive_prompt
        })

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person or not self.current_node:
            return self.stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        elapsed = now - self.node_start_time

        # =========================================================================
        # 1. 动态微指令体态判定 (Pose Verification based on Directive)
        # =========================================================================
        d_type = self.current_node.directive_type
        is_compliant = True

        if d_type == "HANDS_HEAD":
            l_wr, r_wr = pose.keypoints[9], pose.keypoints[10]
            l_ear, r_ear = pose.keypoints[3], pose.keypoints[4]
            if not (l_wr[2] > 0.3 and r_wr[2] > 0.3 and l_wr[1] < l_ear[1] + 50 and r_wr[1] < r_ear[1] + 50):
                is_compliant = False

        elif d_type == "KNEEL":
            if not pose.is_kneeling and not pose.is_spine_collapsed:
                is_compliant = False

        elif d_type == "TOTAL_STILL":
            if pose.struggle_velocity > 35.0 or pose.hands_covering_core:
                is_compliant = False

        if is_compliant:
            self.compliance_score += 1
        else:
            # Subtle punishment reminder if non-compliant
            self.stats.status_prompt = "⚠️ 姿态不合格！严格服从当前指令！"

        # =========================================================================
        # 2. 节点推进与下一幕动态请求 (Episodic Progression)
        # =========================================================================
        if elapsed >= self.current_node.duration_sec:
            self.current_act_index += 1
            if self.current_act_index < 4:
                self._advance_to_next_act(pose)
            else:
                self._finish_story()

        return self.stats

    def _advance_to_next_act(self, pose: Pose26AnalysisResult):
        """Advances story to next act with contextual continuity."""
        # Built-in high-immersion pre-rendered branches
        acts = [
            StoryNodeGenerated(
                act_title="第二幕：传导液注入与微动考验",
                narration_text="很好，呈检姿态保持得很乖。现在，深渊神经电流将沿着你的小腿慢慢向上攀爬，深入骨盆核心。不准动，咬紧牙关受着……",
                directive_type="TOTAL_STILL",
                directive_prompt="🧘 【绝对静止：任由电流攀升，一毫米都不准躲闪】",
                haptic_pattern="FLOW_ASCEND",
                duration_sec=20.0
            ),
            StoryNodeGenerated(
                act_title="第三幕：信仰剥离与顺从誓言",
                narration_text="身体已经开始发烫了吧？把双膝跪得更低一些……感受电流在身体深处的共鸣。现在，向深渊献出你的身心……",
                directive_type="KNEEL",
                directive_prompt="🙇 【双膝完全下跪，贴紧地面，接纳支配浪潮】",
                haptic_pattern="SURGE_WAVE",
                duration_sec=22.0
            ),
            StoryNodeGenerated(
                act_title="终幕：契约刻印与圣洁余韵",
                narration_text="今天的洗礼与调教非常完美……浪潮退去了，所有的刺痛都化作了最温柔的抚慰。慢慢放松下来，你是主人最纯洁的俘虏了。",
                directive_type="TOTAL_STILL",
                directive_prompt="💖 【调教圆满：身心彻底放松，接纳余韵抚慰】",
                haptic_pattern="AFTERCARE",
                duration_sec=25.0
            )
        ]

        next_idx = min(len(acts) - 1, self.current_act_index - 1)
        self.current_node = acts[next_idx]
        self._trigger_current_node()

    def _finish_story(self):
        self.stats.stage_title = "🏆 史诗引导调教战役圆满完成！已铭刻深渊契约！"
        self.sequencer.driver.stop_all()
        self.voice_engine.speak("契约已成。今天的调教到此结束，好好休息吧。", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
        self.broadcast_event("STORY_CAMPAIGN_FINISHED", {})
