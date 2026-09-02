"""
Base Game Mode & RPG Stats Engine for OpenHaptic-Roleplay
Defines life cycles, health/armor points, sanity dynamics, and multi-modal event listeners.
"""

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.gender_tuning import GenderTuningProfile, UserGender
from ..core.quad_channel_sequencer import QuadChannelSequencer, QuadHapticPattern
from ..core.electrode_topology import ElectrodeZone

logger = logging.getLogger("GameModeBase")


@dataclass
class PlayerCombatStats:
    armor_hp: float = 100.0              # 战衣护甲值 (100 -> 0)
    magic_overload: float = 0.0          # 魔法传导器过载 (0 -> 100)
    sanity_level: float = 100.0          # 意志与理智度 (100 -> 0)
    is_defeated: bool = False            # 是否完全战败
    is_begging_mercy: bool = False       # 是否处于求饶姿态
    score_points: int = 0
    current_combo: int = 0
    stage_title: str = "战斗准备中"
    status_prompt: str = ""


class BaseGameMode(ABC):
    """Abstract Base Class for all interactive roleplay and minigame modes."""

    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.sequencer = sequencer
        self.profile = profile
        self.on_event_broadcast = on_event_broadcast
        self.stats = PlayerCombatStats()
        self.is_active = False
        self.start_time = time.time()
        self._last_tick_time = time.time()

    @abstractmethod
    def start(self):
        """Initialize and start the gameplay session."""
        self.is_active = True
        self.start_time = time.time()
        self._last_tick_time = time.time()

    @abstractmethod
    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        """Frame update hook called at 30+ FPS."""
        pass

    @abstractmethod
    def stop(self):
        """Safely terminate game session."""
        self.is_active = False
        self.sequencer.driver.stop_all()

    def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        if self.on_event_broadcast:
            self.on_event_broadcast({"type": event_type, "data": data, "timestamp": time.time()})
