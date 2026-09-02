"""
Souls-Like Boss Battle with Physical Haptic Parry & Dodge (v0.1.0)
A real hardcore video game deeply wired with YOLO-Pose 26 and Dual-Loop E-Stim:
- Boss Attacks:
  1. SWEEP (Horizontal Tentacle Lash) -> Player must SQUAT / DUCK within 0.8s
  2. PIERCE (Core Drill Strike) -> Player must PARRY by covering Point 19 Core within 0.6s
  3. THUNDER_STORM -> Player must RAISE HANDS OVER HEAD within 1.0s
- Success: Boss enters Stagger state; gentle haptic reward wave
- Failure: Player takes heavy damage + INSTANT REAL PHYSICAL ELECTRIC SHOCK!
"""

import time
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

logger = logging.getLogger("SoulsBossBattle")


class BossAttackType(str, Enum):
    IDLE = "IDLE"
    SWEEP_LASH = "SWEEP_LASH"           # 横扫: 必须快速深蹲/下潜闪避 (Duck/Squat)
    CORE_PIERCE = "CORE_PIERCE"         # 穿刺: 必须在0.6s内双手护住 Point 19 完美弹反 (Parry)
    THUNDER_STORM = "THUNDER_STORM"     # 雷暴: 必须双手高举过头顶避雷 (High Hands)


@dataclass
class BossEntity:
    name: str = "深渊触手魔皇 (Abyssal Tentacle Lord)"
    max_hp: float = 1000.0
    current_hp: float = 1000.0
    is_staggered: bool = False
    stagger_timer: float = 0.0


class SoulsBossBattleMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.boss = BossEntity()
        self.current_attack = BossAttackType.IDLE
        self.attack_warning_time = 0.0
        self.reaction_window_sec = 0.8
        self.is_reaction_evaluated = False
        self._last_attack_time = time.time()

    def start(self):
        super().start()
        self.boss = BossEntity()
        self.current_attack = BossAttackType.IDLE
        self._last_attack_time = time.time()
        self.is_reaction_evaluated = False

        self.stats = PlayerCombatStats(
            armor_hp=100.0,
            magic_overload=0.0,
            sanity_level=100.0,
            stage_title="⚔️ BOSS 战开始：深渊触手魔皇降临！观察前摇准备闪避与弹反！"
        )

        self.voice_engine.speak(
            "愚蠢的冒险家，看清本座的攻击前摇！躲慢了，身体就准备迎接雷霆吧！",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("BOSS_SPAWN", {
            "boss_name": self.boss.name,
            "boss_hp": self.boss.current_hp,
            "player_hp": self.stats.armor_hp
        })

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        # ==========================================
        # 1. Boss 处于虚弱硬直状态 (Stagger)
        # ==========================================
        if self.boss.is_staggered:
            self.boss.stagger_timer -= dt
            self.stats.status_prompt = f"✨ BOSS 虚弱硬直中！反击时刻！({self.boss.stagger_timer:.1f}s)"
            if self.boss.stagger_timer <= 0:
                self.boss.is_staggered = False
                self._last_attack_time = now
            return self.stats

        # ==========================================
        # 2. Boss 攻击前摇生成器 (Attack Scheduler)
        # ==========================================
        if self.current_attack == BossAttackType.IDLE:
            if now - self._last_attack_time > random.uniform(3.5, 6.0):
                # Choose random attack
                self.current_attack = random.choice([
                    BossAttackType.SWEEP_LASH,
                    BossAttackType.CORE_PIERCE,
                    BossAttackType.THUNDER_STORM
                ])
                self.attack_warning_time = now
                self.is_reaction_evaluated = False
                
                warnings = {
                    BossAttackType.SWEEP_LASH: "🔴 [警告: 横扫重击] 0.8秒内立刻【下蹲/深蹲闪避】！",
                    BossAttackType.CORE_PIERCE: "🟣 [警告: 核心穿刺] 0.6秒内立刻【双手护住核心弹反】！",
                    BossAttackType.THUNDER_STORM: "⚡ [警告: 全屏雷暴] 1.0秒内立刻【双手高举避雷】！"
                }
                self.stats.stage_title = warnings[self.current_attack]
                self.reaction_window_sec = 0.8 if self.current_attack != BossAttackType.CORE_PIERCE else 0.6
                
                self.broadcast_event("BOSS_ATTACK_WARN", {
                    "attack": self.current_attack.value,
                    "window": self.reaction_window_sec
                })

        # ==========================================
        # 3. 玩家动作实时判定 (Parry / Dodge Evaluator)
        # ==========================================
        elif not self.is_reaction_evaluated:
            elapsed = now - self.attack_warning_time

            is_success = False
            # Check Action based on Pose 26
            if self.current_attack == BossAttackType.SWEEP_LASH:
                # Success if spine collapsed / kneeling / squatting (neck lower)
                if pose.is_kneeling or pose.is_spine_collapsed:
                    is_success = True

            elif self.current_attack == BossAttackType.CORE_PIERCE:
                # Success if hands covering Point 19 Core
                if pose.hands_covering_core:
                    is_success = True

            elif self.current_attack == BossAttackType.THUNDER_STORM:
                # Success if hands raised above shoulders
                l_wr, r_wr = pose.keypoints[9], pose.keypoints[10]
                l_sh, r_sh = pose.keypoints[5], pose.keypoints[6]
                if l_wr[2] > 0.3 and r_wr[2] > 0.3 and l_wr[1] < l_sh[1] and r_wr[1] < r_sh[1]:
                    is_success = True

            # If player successfully performed the counter within window:
            if is_success:
                self.is_reaction_evaluated = True
                self._handle_player_success()

            # If time window expired and player FAILED:
            elif elapsed > self.reaction_window_sec:
                self.is_reaction_evaluated = True
                self._handle_player_failure()

        return self.stats

    def _handle_player_success(self):
        """Player dodged/parried successfully! Boss takes massive damage."""
        damage = random.uniform(150.0, 220.0)
        self.boss.current_hp = max(0.0, self.boss.current_hp - damage)
        self.boss.is_staggered = True
        self.boss.stagger_timer = 3.0
        self.current_attack = BossAttackType.IDLE
        self.stats.score_points += 100

        # Gentle pleasant reward haptics
        self.sequencer.driver.vibrate(channel=0, intensity=10.0)
        self.sequencer.driver.vibrate(channel=1, intensity=10.0)

        self.voice_engine.speak("可恶……竟然被你完美弹反了！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
        self.broadcast_event("PARRY_SUCCESS", {
            "damage_dealt": damage,
            "boss_hp_remaining": self.boss.current_hp
        })

        if self.boss.current_hp <= 0:
            self._handle_boss_defeated()

    def _handle_player_failure(self):
        """Player failed! Takes real physical damage & shock penalty."""
        self.stats.armor_hp = max(0.0, self.stats.armor_hp - 25.0)
        self.stats.magic_overload = min(100.0, self.stats.magic_overload + 20.0)
        self.stats.sanity_level = max(0.0, self.stats.sanity_level - 15.0)
        self.current_attack = BossAttackType.IDLE
        self._last_attack_time = time.time()

        # 💥 REAL PHYSICAL ELECTRIC STRIKE (Heavy punishment shock)
        strike_power = min(self.profile.safety_power_ceiling, 70.0)
        self.sequencer.driver.hit(channel=0, power=strike_power, decay_ms=300)
        self.sequencer.driver.hit(channel=1, power=strike_power * 0.9, decay_ms=300)

        self.voice_engine.speak("慢了！硬吃本座一记重击吧！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
        self.broadcast_event("DODGE_FAILED", {
            "remaining_player_hp": self.stats.armor_hp,
            "shock_power": strike_power
        })

        if self.stats.armor_hp <= 0:
            self.stats.is_defeated = True
            self.stats.stage_title = "💀 护甲破损殆尽：战败被俘！"
            self.sequencer.trigger_pattern(QuadHapticPattern.FULL_BURST, duration_sec=2.0)
            self.voice_engine.speak("哈哈哈哈！你的护甲彻底碎裂了，沦为战败的俘虏吧！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)

    def _handle_boss_defeated(self):
        self.stats.stage_title = "🏆 史诗大捷：深渊触手魔皇已被成功讨伐！"
        self.sequencer.driver.stop_all()
        self.voice_engine.speak("不可能……本座竟然被你这种冒险家给……呃啊啊！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
        self.broadcast_event("BOSS_VICTORY", {})
