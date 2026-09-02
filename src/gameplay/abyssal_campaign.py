"""
The Abyssal Covenant: Interactive Haptic Story Campaign (v0.1.0)
A cinematic RPG campaign seamlessly merging:
- Hardcore Souls Boss Battles (Duck, Parry, Jump)
- Deep Narrative Lore & Act Progression
- Dynamic In-Combat Story Choices with Voice Responses
- 3 Multi-Branch Endings (Hero Victory, Corrupted Vessel, Eternal Submission)
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

logger = logging.getLogger("AbyssalCampaign")


class CampaignAct(str, Enum):
    PROLOGUE = "PROLOGUE"                   # 序幕：破损的圣殿骑士
    ACT1_SHATTERED_ARMOR = "ACT1_ARMOR"     # 第一章：战铠剥离与信仰动摇
    ACT2_MIND_CHOICE = "ACT2_CHOICE"        # 第二章：深渊抉择（剧情分支博弈）
    ACT3_FINAL_CLIMAX = "ACT3_CLIMAX"       # 第三章：决战与结局收束


@dataclass
class StoryChoice:
    choice_id: str
    text: str
    reaction_voice: str
    effect_type: str                         # "ENRAGE_BOSS", "SUBMISSION_EDGE"


class AbyssalCampaignMode(BaseGameMode):
    def __init__(
        self,
        sequencer: QuadChannelSequencer,
        profile: GenderTuningProfile,
        voice_engine: InterruptibleVoiceEngine,
        on_event_broadcast: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        super().__init__(sequencer, profile, on_event_broadcast)
        self.voice_engine = voice_engine
        self.current_act = CampaignAct.PROLOGUE
        self.boss_hp = 1000.0
        self.boss_max_hp = 1000.0
        self.is_boss_enraged = False
        self.pending_choices: List[StoryChoice] = []
        self.is_waiting_choice = False

        self._attack_timer = time.time()
        self._current_qte_type: Optional[str] = None
        self._qte_deadline = 0.0

    def start(self):
        super().start()
        self.current_act = CampaignAct.PROLOGUE
        self.boss_hp = 1000.0
        self.is_boss_enraged = False
        self.is_waiting_choice = False
        
        self.stats = PlayerCombatStats(
            armor_hp=100.0,
            magic_overload=0.0,
            sanity_level=100.0,
            stage_title="🏛️ 序幕：破损的圣殿骑士 - 地宫深处的阴影触手缓缓缠上你的战甲..."
        )

        # Epic Prologue Speech
        self.voice_engine.speak(
            "看看是谁闯进了本座的圣殿？堂堂圣殿骑士，圣剑断裂、铠甲破损……你那点微末的圣光，还护得住最核心的魔力传导器吗？",
            priority=VoicePriority.HIGH_REACTION,
            interrupt_now=True
        )
        self.broadcast_event("ACT_START", {
            "act": self.current_act.value,
            "title": "序幕：破损的圣殿骑士",
            "lore": "你被无数湿漉漉的触手抵在冰冷的石柱上，战衣核心阵阵发烫。"
        })

    def make_story_choice(self, choice_id: str):
        """Player makes an in-combat narrative choice via Web UI or Voice."""
        if not self.is_waiting_choice:
            return

        self.is_waiting_choice = False
        for c in self.pending_choices:
            if c.choice_id == choice_id:
                logger.info(f"[Story Choice Made] {c.text}")
                
                # Boss reacts to player's choice
                self.voice_engine.speak(c.reaction_voice, priority=VoicePriority.HIGH_REACTION, interrupt_now=True)

                if c.effect_type == "ENRAGE_BOSS":
                    self.is_boss_enraged = True
                    self.stats.stage_title = "🔥 触手魔皇暴怒！攻击频率与电击伤害大幅飙升！"
                    self.current_act = CampaignAct.ACT3_FINAL_CLIMAX
                elif c.effect_type == "SUBMISSION_EDGE":
                    self.stats.stage_title = "💖 屈辱臣服：魔皇戏谑地施加高频禁断边缘调教..."
                    self.sequencer.trigger_pattern(QuadHapticPattern.TRAVELING_ASCEND, duration_sec=3.0)
                    self.current_act = CampaignAct.ACT3_FINAL_CLIMAX

                self.broadcast_event("CHOICE_RESOLVED", {"choice": c.choice_id, "act": self.current_act.value})
                break

    def update(self, pose: Pose26AnalysisResult) -> PlayerCombatStats:
        if not self.is_active or not pose.has_person or self.is_waiting_choice:
            return self.stats

        now = time.time()
        dt = max(0.01, now - self._last_tick_time)
        self._last_tick_time = now

        # ==========================================
        # 1. 剧情幕数转换与叙事事件
        # ==========================================
        if self.current_act == CampaignAct.PROLOGUE and self.boss_hp <= 750.0:
            self.current_act = CampaignAct.ACT1_SHATTERED_ARMOR
            self.stats.stage_title = "⚡ 第一章：战铠剥离 - 魔皇触手刺破了你的贴身防护层！"
            self.voice_engine.speak(
                "铠甲已经碎裂了呢！你紧闭双腿颤抖的样子，真是比你嘴上的信仰可爱多了！",
                priority=VoicePriority.HIGH_REACTION,
                interrupt_now=True
            )
            self.broadcast_event("ACT_START", {"act": self.current_act.value, "title": "第一章：战铠剥离"})

        elif self.current_act == CampaignAct.ACT1_SHATTERED_ARMOR and self.boss_hp <= 500.0:
            # Trigger Story Decision Point (Act 2 Choice)
            self.current_act = CampaignAct.ACT2_MIND_CHOICE
            self.is_waiting_choice = True
            self.pending_choices = [
                StoryChoice(
                    choice_id="RESIST_DEFIANT",
                    text="【誓死不从】: 呸！深渊的杂碎，有种就直接杀了我！",
                    reaction_voice="狂妄！本座会一根根碾碎你的傲骨，让你在雷霆中求饶！",
                    effect_type="ENRAGE_BOSS"
                ),
                StoryChoice(
                    choice_id="SUBMIT_BEG",
                    text="【咬唇臣服】: 放开我……只要别再电了，你要什么我都答应……",
                    reaction_voice="哼哼哼……很好，乖顺的猎物才有被本座调教的价值~",
                    effect_type="SUBMISSION_EDGE"
                )
            ]
            self.stats.stage_title = "⚖️ 命运抉择时刻：面对魔皇的低语，做出你的选择！"
            self.voice_engine.speak("还要继续撑下去吗，圣殿骑士？是要彻底粉身碎骨，还是乖乖向本座献出你的誓言？", priority=VoicePriority.HIGH_REACTION)
            self.broadcast_event("STORY_CHOICE_PROMPT", {
                "choices": [{"id": c.choice_id, "text": c.text} for c in self.pending_choices]
            })
            return self.stats

        # ==========================================
        # 2. 核心战斗循环与 QTE 闪避判定
        # ==========================================
        if self._current_qte_type is None:
            interval = 2.5 if self.is_boss_enraged else 4.5
            if now - self._attack_timer > interval:
                self._current_qte_type = random.choice(["SWEEP", "PIERCE", "STORM"])
                self._qte_deadline = now + (0.6 if self.is_boss_enraged else 0.8)
                self._attack_timer = now

                qte_descs = {
                    "SWEEP": "🔴 触手魔皇横扫！立刻【下蹲闪避】！",
                    "PIERCE": "🟣 触手魔皇直刺传导器！立刻【双手护住核心弹反】！",
                    "STORM": "⚡ 全屏深渊雷暴！立刻【双手高举避雷】！"
                }
                self.stats.status_prompt = qte_descs[self._current_qte_type]
                self.broadcast_event("QTE_ALERT", {"type": self._current_qte_type, "window": 0.8})

        else:
            # Evaluate QTE
            is_success = False
            if self._current_qte_type == "SWEEP" and (pose.is_kneeling or pose.is_spine_collapsed):
                is_success = True
            elif self._current_qte_type == "PIERCE" and pose.hands_covering_core:
                is_success = True
            elif self._current_qte_type == "STORM":
                l_wr, r_wr = pose.keypoints[9], pose.keypoints[10]
                l_sh, r_sh = pose.keypoints[5], pose.keypoints[6]
                if l_wr[2] > 0.3 and r_wr[2] > 0.3 and l_wr[1] < l_sh[1] and r_wr[1] < r_sh[1]:
                    is_success = True

            if is_success:
                # Player Hit Boss
                self.boss_hp = max(0.0, self.boss_hp - 180.0)
                self._current_qte_type = None
                self.stats.status_prompt = "✨ 完美弹反破招！触手魔皇陷入硬直！"
                self.broadcast_event("PARRY_SUCCESS", {"boss_hp": self.boss_hp})

            elif now > self._qte_deadline:
                # Player Missed -> Heavy Shock!
                pwr = 75.0 if self.is_boss_enraged else 60.0
                self.stats.armor_hp = max(0.0, self.stats.armor_hp - 25.0)
                self.stats.magic_overload = min(100.0, self.stats.magic_overload + 20.0)
                self.sequencer.driver.hit(channel=0, power=pwr, decay_ms=250)
                self.sequencer.driver.hit(channel=1, power=pwr * 0.9, decay_ms=250)
                self._current_qte_type = None
                self.stats.status_prompt = f"💥 闪避失败！遭受深渊重击 ({pwr:.0f}%)！"
                self.broadcast_event("DODGE_FAIL", {"player_hp": self.stats.armor_hp})

        # ==========================================
        # 3. 三大史诗结局判定 (Multi-Endings)
        # ==========================================
        if self.boss_hp <= 0:
            # Ending 1: Hero Victory
            self.stats.stage_title = "🏆 史诗结局一：【弑神破晓】(Dawn of the Paladin) - 你斩断了所有触手，地宫重见光明！"
            self.is_active = False
            self.sequencer.driver.stop_all()
            self.voice_engine.speak("不可能……圣殿骑士的力量，竟然斩碎了深渊……呃啊啊！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
            self.broadcast_event("ENDING_REACHED", {"ending": "HERO_VICTORY"})

        elif self.stats.armor_hp <= 0:
            # Ending 2: Corrupted Vessel
            self.stats.stage_title = "💀 史诗结局二：【堕落受肉】(Corrupted Vessel) - 战甲彻底粉碎，你被完全拖入深渊..."
            self.is_active = False
            self.sequencer.trigger_pattern(QuadHapticPattern.FULL_BURST, duration_sec=3.0)
            self.voice_engine.speak("沉沦吧，战败的骑士……从今往后，你的身体与灵魂，皆归深渊所有！", priority=VoicePriority.HIGH_REACTION, interrupt_now=True)
            self.broadcast_event("ENDING_REACHED", {"ending": "CORRUPTED_VESSEL"})

        return self.stats
