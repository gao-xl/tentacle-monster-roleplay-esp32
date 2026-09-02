"""
Adaptive Dynamic Regulation Engine for OpenHaptic-Roleplay (v0.1.0)
Implements 4-tier closed-loop adaptation:
1. Anti-Habituation Dynamic Frequency Jitter (prevents nerve desensitization)
2. Bio-Feedback Safety Damping (auto-tempers power on high pain/fatigue)
3. Vision Exposure & Scale Compensation
4. Dynamic AI Voice Cadence Modulation
"""

import time
import math
import logging
from dataclasses import dataclass
from typing import Tuple, Dict, Any
from ..vision.pose26_tracker import Pose26AnalysisResult

logger = logging.getLogger("AdaptiveController")


@dataclass
class AdaptiveState:
    tolerance_gain: float = 1.0          # 疲劳代偿增益 (1.0 -> 1.3)
    safety_damping_factor: float = 1.0   # 生理安全阻尼 (1.0 -> 0.6)
    active_freq_hz: float = 80.0         # 动态防脱敏抖动频率
    ai_voice_speed: float = 1.0          # 自适应语速
    adaptive_hud_message: str = "自适应调控状态正常"


class AdaptiveController:
    def __init__(self, baseline_freq_hz: float = 80.0, max_safe_power: float = 70.0):
        self.baseline_freq = baseline_freq_hz
        self.max_safe_power = max_safe_power
        self.state = AdaptiveState(active_freq_hz=baseline_freq_hz)
        
        self._session_start_time = time.time()
        self._last_high_pain_time = 0.0
        self._continuous_stim_seconds = 0.0

    def compute_adaptive_power(
        self,
        raw_power_a: float,
        raw_power_b: float,
        pose: Pose26AnalysisResult,
        is_stimulating: bool
    ) -> Tuple[float, float, AdaptiveState]:
        """
        Calculates adapted power levels for Loop A & Loop B based on real-time physiology.
        """
        now = time.time()
        elapsed_min = (now - self._session_start_time) / 60.0

        # ==========================================
        # 1. 神经抗习惯化 / 疲劳代偿 (Anti-Habituation)
        # ==========================================
        if is_stimulating:
            self._continuous_stim_seconds += 0.033
            # Jitter frequency +/- 8Hz as a sine wave to continuously surprise sensory nerves
            freq_offset = math.sin(now * 3.0) * 8.0
            self.state.active_freq_hz = max(30.0, self.baseline_freq + freq_offset)
        else:
            self._continuous_stim_seconds = max(0.0, self._continuous_stim_seconds - 0.05)

        # Slowly increase gain (up to +20%) over 15 minutes of play to compensate for sensory numbing
        self.state.tolerance_gain = min(1.20, 1.0 + (elapsed_min / 15.0) * 0.20)

        # ==========================================
        # 2. 生理安全负反馈阻尼 (Bio-Feedback Damping)
        # ==========================================
        # If player displays extreme struggle (>70) or severe pain facial expression:
        if pose.struggle_score > 70.0 or "PAIN" in pose.face_emotion.upper() or pose.is_face_shaking:
            self._last_high_pain_time = now
            # Instant damping: reduce output to 70% to protect the player
            self.state.safety_damping_factor = max(0.65, self.state.safety_damping_factor - 0.08)
            self.state.adaptive_hud_message = "🛡️ 捕捉到剧烈生理挣扎/痛苦微表情: 触发自适应阻尼保护"
        else:
            # Gradually restore damping factor back to 1.0 over 4 seconds
            if now - self._last_high_pain_time > 3.0:
                self.state.safety_damping_factor = min(1.0, self.state.safety_damping_factor + 0.04)
                self.state.adaptive_hud_message = "✨ 生理自适应巡航中"

        # ==========================================
        # 3. 自适应语速调节 (Adaptive Voice Cadence)
        # ==========================================
        if pose.is_surrendering or pose.toe_curl_index > 40.0:
            # Player is overwhelmed -> slow, teasing whisper
            self.state.ai_voice_speed = 0.90
        elif pose.struggle_score > 50.0:
            # High action -> fast, commanding voice
            self.state.ai_voice_speed = 1.15
        else:
            self.state.ai_voice_speed = 1.0

        # ==========================================
        # 4. 计算最终自适应输出功率 (Final Clamped Power)
        # ==========================================
        adapted_a = raw_power_a * self.state.tolerance_gain * self.state.safety_damping_factor
        adapted_b = raw_power_b * self.state.tolerance_gain * self.state.safety_damping_factor

        # Strict safety clamping
        final_a = min(self.max_safe_power, max(0.0, adapted_a))
        final_b = min(self.max_safe_power, max(0.0, adapted_b))

        return final_a, final_b, self.state
