"""
Central Unified Game Manager for OpenHaptic-Roleplay (v0.1.0)
Solves state-machine fragmentation across multiple modes:
- Atomic hot-swapping between all 7 gameplay modes
- Strict resource disposal & power zeroing on transitions
- Centralized event multiplexer for frontend WebSocket broadcast
"""

import logging
from typing import Optional, Dict, Any, Callable
from .game_mode_base import BaseGameMode, PlayerCombatStats
from .tentacle_dungeon import TentacleDungeonMode
from .red_light_freeze import RedLightFreezeMode
from .forced_compliance import ForcedComplianceMode
from .orgasm_control import OrgasmControlMode, OrgasmSubMode
from .bdsm_conditioning import BDSMConditioningMode
from .restrained_trial import RestrainedTrialMode
from .souls_boss_battle import SoulsBossBattleMode
from .abyssal_campaign import AbyssalCampaignMode
from .guided_conditioning import GuidedConditioningMode
from .neural_parkour import NeuralParkourMode
from .cleaning_discipline import CleaningDisciplineMode
from .llm_story_director import LLMStoryDirectorMode
from .multi_tier_edging_protocol import MultiTierEdgingProtocolMode
from .shame_inspection_master import ShameInspectionMasterMode
from .extreme_exhibition import ExtremeExhibitionMode

from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.quad_channel_sequencer import QuadChannelSequencer
from ..core.gender_tuning import GenderTuningProfile
from ..core.kokoro_engine import InterruptibleVoiceEngine

logger = logging.getLogger("CentralGameManager")


class CentralGameManager:
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.sequencer = sequencer
        self.profile = profile
        self.voice_engine = voice_engine
        self.on_broadcast = on_broadcast

        self.current_mode_key = "abyssal"
        self.active_mode: Optional[BaseGameMode] = None
        self._init_mode("abyssal")

    def switch_mode(self, mode_key: str):
        """Atomically halts previous mode and initializes new game mode."""
        logger.info(f"🔄 [GameManager] Switching Mode: '{self.current_mode_key}' -> '{mode_key}'")
        
        # 1. Safely teardown existing mode
        if self.active_mode:
            self.active_mode.stop()

        # 2. Hardware safety zero
        self.sequencer.driver.stop_all()

        # 3. Instantiate requested mode
        self.current_mode_key = mode_key
        self._init_mode(mode_key)

        if self.on_broadcast:
            self.on_broadcast({"type": "MODE_SWITCHED", "mode": mode_key})

    def _init_mode(self, mode_key: str):
        if mode_key == "dungeon":
            self.active_mode = TentacleDungeonMode(self.sequencer, self.profile, self.on_broadcast)
        elif mode_key == "red_light":
            self.active_mode = RedLightFreezeMode(self.sequencer, self.profile, self.on_broadcast)
        elif mode_key == "forced":
            self.active_mode = ForcedComplianceMode(self.sequencer, self.profile, self.on_broadcast)
        elif mode_key == "denial":
            self.active_mode = OrgasmControlMode(self.sequencer, self.profile, OrgasmSubMode.DENIAL_EDGE, self.on_broadcast)
        elif mode_key == "forced_climax":
            self.active_mode = OrgasmControlMode(self.sequencer, self.profile, OrgasmSubMode.FORCED_CLIMAX, self.on_broadcast)
        elif mode_key == "bdsm":
            self.active_mode = BDSMConditioningMode(self.sequencer, self.profile, self.voice_engine, self.on_broadcast)
        elif mode_key == "restrained":
            self.active_mode = RestrainedTrialMode(self.sequencer, self.profile, self.voice_engine, self.on_broadcast)
        elif mode_key == "souls":
            self.active_mode = SoulsBossBattleMode(self.sequencer, self.profile, self.voice_engine, self.on_broadcast)
        elif mode_key == "exhibition":
            self.active_mode = ExtremeExhibitionMode(self.sequencer, self.profile, self.voice_engine, on_event_broadcast=self.on_broadcast)
        elif mode_key == "shame_master":
            self.active_mode = ShameInspectionMasterMode(self.sequencer, self.profile, self.voice_engine, on_event_broadcast=self.on_broadcast)
        elif mode_key == "edging_protocol":
            self.active_mode = MultiTierEdgingProtocolMode(self.sequencer, self.profile, self.voice_engine, on_event_broadcast=self.on_broadcast)
        elif mode_key == "llm_story":
            self.active_mode = LLMStoryDirectorMode(self.sequencer, self.profile, self.voice_engine, on_event_broadcast=self.on_broadcast)
        elif mode_key == "cleaning":
            self.active_mode = CleaningDisciplineMode(self.sequencer, self.profile, self.voice_engine, self.on_broadcast)
        elif mode_key == "parkour":
            self.active_mode = NeuralParkourMode(self.sequencer, self.profile, self.voice_engine, self.on_broadcast)
        elif mode_key == "guided":
            self.active_mode = GuidedConditioningMode(self.sequencer, self.profile, self.voice_engine, self.on_broadcast)
        elif mode_key == "abyssal":
            self.active_mode = AbyssalCampaignMode(self.sequencer, self.profile, self.voice_engine, self.on_broadcast)
        else:
            self.active_mode = AbyssalCampaignMode(self.sequencer, self.profile, self.voice_engine, self.on_broadcast)

        self.active_mode.start()

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if self.active_mode:
            return self.active_mode.update(pose)
        return PlayerCombatStats()