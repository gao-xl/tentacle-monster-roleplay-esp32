"""
Neural Parkour: Abyssal Escape - Ultra-Fluid Continuous Gameplay Engine (v0.1.0)
Non-Stop Seamless Flow Mechanics:
- Continuous obstacle stream synced to high-tempo rhythmic beats (Squat, High-Jump, Lean Left, Lean Right, Core Grab)
- Dynamic Combo Ladder: High combo triggers euphoric rhythmic traveling wave haptics
- Instant Non-Interrupting Stumble: Collision triggers crisp shock penalty and monster proximity escalation without stopping the run
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

logger = logging.getLogger("NeuralParkour")


class ObstacleType(str, Enum):
    HIGH_BEAM = "HIGH_BEAM"         # 顶部横木: 必须深蹲滑铲 (Squat)
    GROUND_LASER = "GROUND_LASER"   # 地面激光: 必须高抬腿/跳跃 (High Jump/Leg)
    LEAN_LEFT = "LEAN_LEFT"         # 左侧触手: 身体向右侧倾斜闪避 (Lean Right)
    LEAN_RIGHT = "LEAN_RIGHT"       # 右侧触手: 身体向左侧倾斜闪避 (Lean Left)
    CORE_ORB = "CORE_ORB"           # 核心能量球: 双手交叉护住 Point 19 吸收 (Core Grab)


@dataclass
class ObstacleEntity:
    id: str
    obs_type: ObstacleType
    spawn_time: float
    target_hit_time: float          # Time when obstacle reaches player (exact QTE moment)
    is_cleared: bool = False
    is_failed: bool = False


@dataclass
class ParkourStats(PlayerCombatStats):
    combo_count: int = 0
    max_combo: int = 0
    distance_meters: float = 0.0
    monster_distance_m: float = 25.0 # Monster chasing player (0m = caught & game over)
    current_bpm: float = 128.0


class NeuralParkourMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.parkour_stats = ParkourStats()
        self.obstacles: List[ObstacleEntity] = []
        self._last_spawn_time = time.time()
        self._spawn_interval = 1.8   # Generates an obstacle every 1.8 seconds (continuous flow)
        self._beat_timer = 0.0

    def start(self):
        super().start()
        self.parkour_stats = ParkourStats(
            stage_title="🏃 深渊神经连续跑酷启动：音乐已起，连贯闪避，一秒都不要停！"
        )
        self.obstacles.clear()
        self._last_spawn_time = time.time()

        self.voice_engine.speak(
            "深渊逃亡开始！跟上音乐的节拍，连贯做出深蹲、跳跃与侧倾闪避，不要停下来！",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("PARKOUR_START", {
            "initial_distance": self.parkour_stats.distance_meters,
            "monster_distance": self.parkour_stats.monster_distance_m
        })

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person:
            return self.parkour_stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        # Progress distance and beat clock
        self.parkour_stats.distance_meters += dt * 15.0 # 15 m/s running speed
        self._beat_timer += dt

        # =========================================================================
        # 1. 连续节拍生成障碍物 (Continuous Obstacle Spawner)
        # =========================================================================
        if now - self._last_spawn_time >= self._spawn_interval:
            self._last_spawn_time = now
            obs_type = random.choice([
                ObstacleType.HIGH_BEAM,
                ObstacleType.GROUND_LASER,
                ObstacleType.LEAN_LEFT,
                ObstacleType.LEAN_RIGHT,
                ObstacleType.CORE_ORB
            ])
            obs_id = f"obs_{int(now * 1000)}"
            new_obs = ObstacleEntity(
                id=obs_id,
                obs_type=obs_type,
                spawn_time=now,
                target_hit_time=now + 1.2 # 1.2 seconds flying time towards player
            )
            self.obstacles.append(new_obs)
            self.broadcast_event("OBSTACLE_SPAWNED", {
                "id": obs_id,
                "type": obs_type.value,
                "duration": 1.2
            })

        # =========================================================================
        # 2. 毫秒级姿态匹配与连贯命中判定 (Continuous Action Evaluator)
        # =========================================================================
        for obs in self.obstacles:
            if obs.is_cleared or obs.is_failed:
                continue

            time_to_hit = obs.target_hit_time - now
            
            # Active reaction window: [-0.25s, +0.25s] around exact hit time
            if -0.25 <= time_to_hit <= 0.25:
                is_matched = False

                if obs.obs_type == ObstacleType.HIGH_BEAM:
                    # Squat / Duck check
                    if pose.is_kneeling or pose.is_spine_collapsed:
                        is_matched = True

                elif obs.obs_type == ObstacleType.GROUND_LASER:
                    # High Leg / Jump (Ankles higher than normal)
                    l_ank, r_ank = pose.keypoints[15], pose.keypoints[16]
                    if l_ank[2] > 0.3 and r_ank[2] > 0.3:
                        # If either ankle is significantly raised
                        if l_ank[1] < 380 or r_ank[1] < 380:
                            is_matched = True

                elif obs.obs_type == ObstacleType.LEAN_LEFT:
                    # Lean Body to Right (Nose X shifts right)
                    nose = pose.keypoints[0]
                    if nose[2] > 0.4 and nose[0] > 360: # Screen right
                        is_matched = True

                elif obs.obs_type == ObstacleType.LEAN_RIGHT:
                    # Lean Body to Left (Nose X shifts left)
                    nose = pose.keypoints[0]
                    if nose[2] > 0.4 and nose[0] < 280: # Screen left
                        is_matched = True

                elif obs.obs_type == ObstacleType.CORE_ORB:
                    # Hands Covering Core (Point 19)
                    if pose.hands_covering_core:
                        is_matched = True

                # --- SUCCESS: Perfect Clear ---
                if is_matched:
                    obs.is_cleared = True
                    self.parkour_stats.combo_count += 1
                    self.parkour_stats.max_combo = max(self.parkour_stats.max_combo, self.parkour_stats.combo_count)
                    self.parkour_stats.score_points += 100 * (1 + self.parkour_stats.combo_count // 5)
                    self.parkour_stats.monster_distance_m = min(35.0, self.parkour_stats.monster_distance_m + 0.8)

                    # Dynamic Combo Haptic Resonance (Higher combo = richer rhythmic waves)
                    rhythm_intensity = min(40.0, 15.0 + self.parkour_stats.combo_count * 1.2)
                    self.sequencer.driver.vibrate(channel=0, intensity=rhythm_intensity)
                    self.sequencer.driver.vibrate(channel=1, intensity=rhythm_intensity * 0.8)

                    self.parkour_stats.status_prompt = f"🔥 COMBO x{self.parkour_stats.combo_count}! 完美闪避！"
                    self.broadcast_event("OBSTACLE_CLEARED", {
                        "id": obs.id,
                        "combo": self.parkour_stats.combo_count
                    })

            # --- FAILURE: Missed Obstacle ---
            elif time_to_hit < -0.25 and not obs.is_cleared and not obs.is_failed:
                obs.is_failed = True
                self.parkour_stats.combo_count = 0 # Combo broken
                self.parkour_stats.monster_distance_m = max(0.0, self.parkour_stats.monster_distance_m - 6.0)
                self.parkour_stats.magic_overload = min(100.0, self.parkour_stats.magic_overload + 15.0)

                # Instant Non-Interrupting Stumble Shock (55% Power zap)
                strike_power = min(self.profile.safety_power_ceiling, 58.0)
                self.sequencer.driver.hit(channel=0, power=strike_power, decay_ms=180)
                self.sequencer.driver.hit(channel=1, power=strike_power * 0.8, decay_ms=180)

                self.parkour_stats.status_prompt = "💥 撞击绊倒！失误受击！触手怪逼近中！"
                self.broadcast_event("OBSTACLE_MISSED", {
                    "id": obs.id,
                    "monster_dist": self.parkour_stats.monster_distance_m
                })

        # Cleanup old obstacles
        self.obstacles = [o for o in self.obstacles if now - o.target_hit_time < 2.0]

        # =========================================================================
        # 3. 终结判定：被追上战败 或 跑酷通关
        # =========================================================================
        if self.parkour_stats.monster_distance_m <= 0.0 or self.parkour_stats.magic_overload >= 100.0:
            self.parkour_stats.is_defeated = True
            self.parkour_stats.stage_title = "💀 逃亡失败：被深渊触手完全追上吞噬！"
            self.sequencer.trigger_pattern(QuadHapticPattern.FULL_BURST, duration_sec=2.5)
            self.voice_engine.speak("被追上了！沦陷在深渊中吧！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
            self.broadcast_event("PARKOUR_DEFEAT", {})

        return self.parkour_stats
