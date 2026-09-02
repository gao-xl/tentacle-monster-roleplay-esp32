"""
Devil's Roulette & Strict Decibel Stealth Mode (The Ultimate High-Tension Gameplay)
Features:
1. Russian Roulette Chamber (1 in 6 chance of firing an extreme 95% Tmax punishment burst)
2. Decibel Noise Trap (Web Audio microphone monitors breathing; groan > 45dB triggers instant strike)
3. Sensory Blackout Ambush (Random screen blackout followed by zero-warning dual-loop hit)
"""

import time
import random
import logging
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any, List
from .game_mode_base import BaseGameMode, PlayerCombatStats
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.quad_channel_sequencer import QuadChannelSequencer, QuadHapticPattern
from ..core.gender_tuning import GenderTuningProfile
from ..core.kokoro_engine import InterruptibleVoiceEngine, VoicePriority

logger = logging.getLogger("DevilRouletteMode")


class DevilRouletteMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.chamber_capacity = 6
        self.current_chamber = 0
        self.live_bullet_index = random.randint(0, 5)
        self.survival_rounds = 0
        self.is_blackout = False
        self._last_blackout_time = time.time()
        self._blackout_duration = 4.0
        self._noise_threshold_db = 45.0
        self._last_noise_penalty = 0.0

    def start(self):
        super().start()
        self.chamber_capacity = 6
        self.current_chamber = 0
        self.live_bullet_index = random.randint(0, 5)
        self.survival_rounds = 0
        self.is_blackout = False
        self._last_blackout_time = time.time()

        self.stats = PlayerCombatStats(
            stage_title="🎰 恶魔轮盘赌启动：6发弹巢已装填！严禁发出任何声音！"
        )

        self.voice_engine.speak(
            "恶魔轮盘赌开始。弹巢已经转动，六分之一的几率是极限过载。咬紧牙关，一声都不准哼哦。",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("ROULETTE_START", {
            "chambers": self.chamber_capacity,
            "round": 1
        })

    def pull_trigger(self) -> bool:
        """Pulls the roulette trigger. Returns True if live bullet fires!"""
        is_live = (self.current_chamber == self.live_bullet_index)
        logger.info(f"[Devil Roulette] Chamber {self.current_chamber + 1}/6: {'💥 BANG (LIVE)' if is_live else '✨ CLICK (BLANK)'}")
        
        if is_live:
            # 💥 LIVE BULLET EXPLOSION (95% of safety ceiling)
            power = min(self.profile.safety_power_ceiling, 85.0)
            self.sequencer.trigger_pattern(QuadHapticPattern.FULL_BURST, duration_sec=1.8)
            self.stats.magic_overload = min(100.0, self.stats.magic_overload + 35.0)
            self.stats.sanity_level = max(0.0, self.stats.sanity_level - 30.0)

            self.voice_engine.speak("中奖了！极刑过载爆发！给我乖乖抽搐吧！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
            self.broadcast_event("ROULETTE_BANG", {"power": power, "chamber": self.current_chamber + 1})

            # Reload a new random bullet
            self.current_chamber = 0
            self.live_bullet_index = random.randint(0, 5)
            return True
        else:
            # Blank click (safe)
            self.survival_rounds += 1
            self.stats.score_points += 50
            self.current_chamber = (self.current_chamber + 1) % 6
            self.voice_engine.speak("空枪……运气不错嘛，但下一发呢？", priority=VoicePriority.LOW_LORE)
            self.broadcast_event("ROULETTE_BLANK", {"survived": self.survival_rounds, "next_chamber": self.current_chamber + 1})
            return False

    def on_noise_detected(self, decibel: float):
        """Called when microphone detects a gasp, moan, or scream above threshold."""
        now = time.time()
        if decibel > self._noise_threshold_db and now - self._last_noise_penalty > 2.0:
            self._last_noise_penalty = now
            self.stats.magic_overload = min(100.0, self.stats.magic_overload + 10.0)
            
            # Punishment zap
            self.sequencer.driver.hit(channel=0, power=60.0, decay_ms=200)
            self.voice_engine.speak("叫出声了！违规娇喘，惩罚电击！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
            self.broadcast_event("NOISE_VIOLATION", {"db": decibel})

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        # ==========================================
        # 1. 周期性黑屏视线剥夺与无预警偷袭 (Sensory Blackout)
        # ==========================================
        if not self.is_blackout and (now - self._last_blackout_time > 18.0):
            # Enter Blackout
            self.is_blackout = True
            self._last_blackout_time = now
            self._blackout_duration = random.uniform(3.0, 6.0)
            self.sequencer.driver.stop_all() # Complete dead silence
            self.stats.stage_title = "🌑 视线剥夺 (BLACKOUT)：全屏全黑，死寂降临... 准备迎接无预警偷袭！"
            self.broadcast_event("BLACKOUT_ENTER", {"duration": self._blackout_duration})

        elif self.is_blackout and (now - self._last_blackout_time > self._blackout_duration):
            # Blackout Ends with AMBUSH HIT!
            self.is_blackout = False
            self._last_blackout_time = now
            self.stats.stage_title = "💥 虚空偷袭！触手在黑暗中猛烈贯穿！"
            self.sequencer.trigger_pattern(QuadHapticPattern.TRAVELING_ASCEND, duration_sec=1.5)
            self.voice_engine.speak("黑暗中的触手……喜欢吗？", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
            self.broadcast_event("BLACKOUT_EXIT", {})
            
            # Auto pull roulette trigger after blackout!
            self.pull_trigger()

        # Check Defeat
        if self.stats.magic_overload >= 100.0 or self.stats.sanity_level <= 0.0:
            self.stats.is_defeated = True
            self.stats.stage_title = "💀 恶魔轮盘赌战败：被完全击溃！"

        return self.stats

    def stop(self):
        super().stop()
        logger.info("[DevilRouletteMode] Stopped.")
