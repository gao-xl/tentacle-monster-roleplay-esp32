"""
Scenario State Machine & Roleplay Progression Engine
Controls RPG game stages (Exploration -> Defense Break -> Overload -> Subjugation),
manages event triggers, and computes dynamic penalty and feedback multipliers.
"""

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from ..vision.advanced_classifier import DetailedPoseMetrics
from ..drivers.base import DeviceTelemetry

logger = logging.getLogger("ScenarioStateMachine")


class RoleplayStage(str, Enum):
    STAGE_1_EXPLORATION = "STAGE_1_EXPLORATION"     # 阶段一：初遇试探（弱触碰，试探防守）
    STAGE_2_DEFENSE_BREAK = "STAGE_2_DEFENSE_BREAK" # 阶段二：破防攻坚（针对双手遮挡进行破防打击）
    STAGE_3_OVERLOAD = "STAGE_3_OVERLOAD"           # 阶段三：魔力过载（高频波动，全面缠绕）
    STAGE_4_SUBJUGATION = "STAGE_4_SUBJUGATION"     # 阶段四：彻底战败（臣服调戏，持续低频压制）


@dataclass
class StageConfig:
    name: str
    description: str
    base_power: float
    max_power: float
    tactics_prompt: str
    transition_score_thresh: float


@dataclass
class GameStateSnapshot:
    current_stage: RoleplayStage
    stage_progress: float = 0.0          # 0.0 - 100.0%
    player_sanity: float = 100.0         # 理智值 / 防御耐久度 (100 -> 0)
    magic_overload_level: float = 0.0    # 传导器魔力负荷 (0 -> 100)
    total_hits_delivered: int = 0
    stage_duration_sec: float = 0.0
    last_action_desc: str = "触手正在暗中观察..."


class ScenarioStateMachine:
    STAGE_DEFS: Dict[RoleplayStage, StageConfig] = {
        RoleplayStage.STAGE_1_EXPLORATION: StageConfig(
            name="初入废弃小屋 (Exploration)",
            description="小触手好奇地试探玩家的装备与弱点，寻找防守破绽。",
            base_power=20.0,
            max_power=40.0,
            tactics_prompt="保持好奇和玩闹，轻微试探玩家的护甲与身体姿态，不要用力过猛。",
            transition_score_thresh=30.0
        ),
        RoleplayStage.STAGE_2_DEFENSE_BREAK: StageConfig(
            name="护甲破防攻坚 (Defense Break)",
            description="触手发现玩家双手护住核心弱点，开始针对性施加破防脉冲！",
            base_power=45.0,
            max_power=70.0,
            tactics_prompt="玩家正在顽强抵抗，集中力量对玩家双手捂住的部位进行突袭破防！",
            transition_score_thresh=60.0
        ),
        RoleplayStage.STAGE_3_OVERLOAD: StageConfig(
            name="传导器魔力过载 (Magic Overload)",
            description="玩家防御被撕开，触手大量涌出，引发魔力传导器高频共振与过载！",
            base_power=55.0,
            max_power=85.0,
            tactics_prompt="玩家已经露出破绽，施展连续缠绕与波形打击，将魔力负荷推向极限！",
            transition_score_thresh=90.0
        ),
        RoleplayStage.STAGE_4_SUBJUGATION: StageConfig(
            name="完全臣服与俘获 (Subjugation)",
            description="玩家体力与魔力彻底耗尽，进入跪地/求饶状态，小怪物满意地享受战果。",
            base_power=30.0,
            max_power=60.0,
            tactics_prompt="玩家已经彻底战败求饶，用戏谑、得意的语气调戏玩家，维持有节制的收束与轻抚。",
            transition_score_thresh=999.0
        ),
    }

    def __init__(self, on_stage_changed: Optional[Callable[[RoleplayStage], None]] = None):
        self.stage = RoleplayStage.STAGE_1_EXPLORATION
        self.sanity = 100.0
        self.overload = 0.0
        self.hits_count = 0
        self.stage_start_time = time.time()
        self.on_stage_changed = on_stage_changed
        self._last_tick_time = time.time()

    def update(
        self,
        pose: DetailedPoseMetrics,
        telemetry: Optional[DeviceTelemetry] = None
    ) -> GameStateSnapshot:
        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        stage_cfg = self.STAGE_DEFS[self.stage]
        stage_time = now - self.stage_start_time

        # 1. Calculate Overload & Sanity Dynamics based on Pose
        if pose.has_person:
            # When exposed or struggling, overload increases, sanity decreases
            if pose.weakpoint_exposure > 0.5:
                self.overload += dt * 2.5 * pose.weakpoint_exposure
                self.sanity -= dt * 1.5 * pose.weakpoint_exposure
            
            if pose.struggle_intensity > 30.0:
                self.overload += dt * 1.8 * (pose.struggle_intensity / 100.0)

            # Surrender / Submission quickly drains sanity
            if pose.is_surrendering or pose.is_hands_behind_head or pose.is_kneeling:
                self.sanity -= dt * 3.0

        # Clamp values
        self.sanity = max(0.0, min(100.0, self.sanity))
        self.overload = max(0.0, min(100.0, self.overload))

        # 2. Check Stage Progression & Transitions
        prev_stage = self.stage
        if self.stage == RoleplayStage.STAGE_1_EXPLORATION:
            if self.overload > 25.0 or pose.hands_covering_core or stage_time > 45.0:
                self._transition_to(RoleplayStage.STAGE_2_DEFENSE_BREAK)

        elif self.stage == RoleplayStage.STAGE_2_DEFENSE_BREAK:
            if self.overload > 60.0 or pose.weakpoint_exposure > 0.75 or stage_time > 60.0:
                self._transition_to(RoleplayStage.STAGE_3_OVERLOAD)

        elif self.stage == RoleplayStage.STAGE_3_OVERLOAD:
            if self.sanity < 15.0 or pose.is_surrendering or pose.is_hands_behind_head or (pose.is_kneeling and self.overload > 85.0):
                self._transition_to(RoleplayStage.STAGE_4_SUBJUGATION)

        # 3. Compute current stage progress %
        progress = (self.overload if self.stage != RoleplayStage.STAGE_4_SUBJUGATION else (100.0 - self.sanity))

        return GameStateSnapshot(
            current_stage=self.stage,
            stage_progress=min(100.0, progress),
            player_sanity=self.sanity,
            magic_overload_level=self.overload,
            total_hits_delivered=self.hits_count,
            stage_duration_sec=stage_time,
            last_action_desc=stage_cfg.name
        )

    def _transition_to(self, new_stage: RoleplayStage):
        if self.stage != new_stage:
            logger.info(f"[STAGE TRANSITION] {self.stage.value} -> {new_stage.value}")
            self.stage = new_stage
            self.stage_start_time = time.time()
            if self.on_stage_changed:
                self.on_stage_changed(new_stage)

    def get_stage_config(self) -> StageConfig:
        return self.STAGE_DEFS[self.stage]
