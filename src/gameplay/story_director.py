"""
Narrative Story Director & Multi-Scenario Campaign Engine for OpenHaptic-Roleplay
Deeply integrates RPG Storyline Lore, Dialogue Progression, Multi-Branch Choices,
and Biometric Gameplay States (Denial/Forced Climax, Armor HP, Pose 26).
"""

import os
import time
import logging
import yaml
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from ..vision.pose26_tracker import Pose26AnalysisResult
from ..core.gender_tuning import GenderTuningProfile, UserGender
from ..core.electrode_topology import ElectrodeZone, ElectrodeTopologyManager
from .game_mode_base import PlayerCombatStats

logger = logging.getLogger("StoryDirector")


@dataclass
class StoryNode:
    node_id: str
    title: str
    narrative_text: str
    monster_voice_line: str
    character_tone: str              # "monster_playful", "monster_deep", "tsundere_queen"
    required_gameplay_mode: str      # "dungeon", "red_light", "forced", "denial", "forced_climax"
    target_overload_trigger: float   # Overload threshold to advance
    next_node_default: str
    branch_choices: List[Dict[str, str]] = field(default_factory=list)


class ScenarioCampaignEngine:
    """Manages multi-act immersive roleplay campaigns with deep story progression."""

    STORY_NODES: Dict[str, StoryNode] = {
        # === ACT 1: 战败初入废弃小屋 ===
        "ACT1_ENTRY": StoryNode(
            node_id="ACT1_ENTRY",
            title="第一幕：战败逃入废弃小屋",
            narrative_text="你刚经历了一场惨烈的魔物讨伐战，法力值彻底见底，战衣破损。你跌跌撞撞地躲进这座看似废弃的林中小屋想整理装备，却没注意到阴影里正蠕动着数条湿漉漉的幽暗触手……",
            monster_voice_line="“哎呀呀……看看是谁自己送上门来了？战衣都破成这样了，魔法传导器还在微弱地闪烁呢~”",
            character_tone="monster_playful",
            required_gameplay_mode="dungeon",
            target_overload_trigger=25.0,
            next_node_default="ACT2_PROBING"
        ),

        # === ACT 2: 战衣张力与弱点试探 ===
        "ACT2_PROBING": StoryNode(
            node_id="ACT2_PROBING",
            title="第二幕：战衣贴合与弱点试探",
            narrative_text="调皮的小触手悄无声息地贴上了你的身体，细微的电流开始在贴身战服的魔力回路中游移。小怪物好奇地注视着你双手护住的位置，开始试探你的防守底线。",
            monster_voice_line="“这么急着捂住那里？战服在魔法传导器核心区绷得这么紧，是害怕被触手碰到吗？”",
            character_tone="monster_playful",
            required_gameplay_mode="dungeon",
            target_overload_trigger=55.0,
            next_node_default="ACT3_RED_LIGHT_INSPECTION"
        ),

        # === ACT 3: 强制检查：绝对不许动 ===
        "ACT3_RED_LIGHT_INSPECTION": StoryNode(
            node_id="ACT3_RED_LIGHT_INSPECTION",
            title="第三幕：触手木头人检查",
            narrative_text="触手小怪物爬到了你的正前方，晃动着吸盘对你下达命令：在它注视时必须绝对静止接受魔力扫描，稍微有一丝颤抖就会遭到电浆惩罚！",
            monster_voice_line="“现在是检查时间！本触手盯着你的时候，一根手指都不准动哦！动一下就电你一次~”",
            character_tone="tsundere_queen",
            required_gameplay_mode="red_light",
            target_overload_trigger=75.0,
            next_node_default="ACT4_DENIAL_TRIAL"
        ),

        # === ACT 4: 临界折磨：禁止高潮调教 ===
        "ACT4_DENIAL_TRIAL": StoryNode(
            node_id="ACT4_DENIAL_TRIAL",
            title="第四幕：魔力传导器边缘调教",
            narrative_text="随着双路流动波的持续刺激，传导器的魔力负荷直逼临界点，你的身体不由自主地紧绷起来。然而小触手却在最高点瞬间抽离了电流，戏谑地逼你把快感硬生生憋回去！",
            monster_voice_line="“脚趾都蜷起来了呢……想高潮？小怪物可没允许你解脱哦！给我乖乖憋回去受着~”",
            character_tone="monster_deep",
            required_gameplay_mode="denial",
            target_overload_trigger=90.0,
            next_node_default="ACT5_FINAL_SUBJUGATION"
        ),

        # === ACT 5: 终幕：强制过载与彻底沦陷 ===
        "ACT5_FINAL_SUBJUGATION": StoryNode(
            node_id="ACT5_FINAL_SUBJUGATION",
            title="第五幕：传导器彻底过载与完全俘获",
            narrative_text="所有的抵抗都已宣告无效，四条粗壮的触手将你完全缠绕。全域魔力爆发瞬间淹没了你的理智，你在剧烈的痉挛中彻底沦陷，成为废弃小屋里属于触手的战败俘虏……",
            monster_voice_line="“太棒了……传导器完全过载了呢！从现在开始，你就是本触手最心爱的小战利品啰~”",
            character_tone="monster_deep",
            required_gameplay_mode="forced_climax",
            target_overload_trigger=100.0,
            next_node_default="ACT5_FINAL_SUBJUGATION"
        )
    }

    def __init__(
        self,
        profile: GenderTuningProfile,
        on_story_progress: Optional[Callable[[StoryNode], None]] = None
    ):
        self.profile = profile
        self.current_node_id = "ACT1_ENTRY"
        self.on_story_progress = on_story_progress
        self.node_start_time = time.time()

    def get_current_node(self) -> StoryNode:
        return self.STORY_NODES[self.current_node_id]

    def update(self, stats: PlayerCombatStats, pose: Pose26AnalysisResult) -> StoryNode:
        node = self.get_current_node()

        # Check Node Transition condition
        if stats.magic_overload >= node.target_overload_trigger and node.node_id != "ACT5_FINAL_SUBJUGATION":
            self.advance_to_node(node.next_node_default)

        return self.get_current_node()

    def advance_to_node(self, target_node_id: str):
        if target_node_id in self.STORY_NODES:
            logger.info(f"[CAMPAIGN PROGRESS] {self.current_node_id} -> {target_node_id}")
            self.current_node_id = target_node_id
            self.node_start_time = time.time()
            if self.on_story_progress:
                self.on_story_progress(self.get_current_node())

    def get_llm_story_context(self) -> str:
        """Returns rich lore prompt to feed into Slow-Loop LLM."""
        node = self.get_current_node()
        return (
            f"【当前剧情幕数】: {node.title}
"
            f"【剧情背景情境】: {node.narrative_text}
"
            f"【触手怪兽当前目标】: 正在执行【{node.required_gameplay_mode}】玩法。
"
            f"【台词风格指示】: 以【{node.character_tone}】语态，结合玩家现场的姿态防御、脚趾蜷缩与电极贴片位置，"
            f"说出符合本幕剧情的 2~3 句生动戏谑台词。"
        )
