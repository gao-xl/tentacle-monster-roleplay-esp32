"""
Electrode Placement Topology & Adaptive Haptic Mapping Engine
Allows players to define physical electrode patch positions, automatically adjusting:
- YOLO-Pose 26 focal focus anchors (Point 19, Points 20-25, Points 11-14)
- AI Narrative context (anatomically accurate tentacle descriptions)
- Adaptive safety power ceilings per body zone
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


class ElectrodeZone(str, Enum):
    CORE_PELVIS = "CORE_PELVIS"       # 魔法传导器核心区 (Point 19 - 极度敏感)
    LOWER_LEGS = "LOWER_LEGS"         # 小腿与足底 (Points 13-16, 20-25 - 脚趾痉挛)
    THIGHS_INNER = "THIGHS_INNER"     # 大腿内侧 (Points 11-14 - 腿部夹紧)
    LOWER_BACK = "LOWER_BACK"         # 后腰与腹部 (Spine Midpoint - 腰部挺直)
    DUAL_TRAVELING = "DUAL_TRAVELING" # 双通道流动 (CH_A: 脚踝 -> CH_B: 核心)


@dataclass
class ZoneConfig:
    name: str
    description: str
    target_kpt_indices: List[int]     # Focal keypoint indices in Halpe-26
    safety_max_power: float           # Recommended hardware ceiling (0-100%)
    narrative_body_part: str          # Text description for LLM prompts
    sensation_cue: str                # Sensory feeling (muscle twitch, electric wave, toe curl)


class ElectrodeTopologyManager:
    ZONE_REGISTRY: Dict[ElectrodeZone, ZoneConfig] = {
        ElectrodeZone.CORE_PELVIS: ZoneConfig(
            name="魔法传导器核心区 (Pelvic Core)",
            description="贴附于双腿根部连接处/传导器核心区。手部捂住该区域将触发高敏防守破防打击。",
            target_kpt_indices=[19],
            safety_max_power=60.0,    # Highly sensitive zone
            narrative_body_part="贴身战衣最下方的魔法传导器核心区",
            sensation_cue="核心区产生阵阵麻痹收缩与魔力过载"
        ),
        ElectrodeZone.LOWER_LEGS: ZoneConfig(
            name="双侧小腿与足弓 (Lower Legs & Feet)",
            description="贴附于小腿肚或足弓。系统将重点捕捉脚趾蜷缩 (Toe Curl) 与踮脚抽搐反应。",
            target_kpt_indices=[13, 14, 15, 16, 20, 21, 22, 23, 24, 25],
            safety_max_power=75.0,
            narrative_body_part="战靴上方的小腿与足弓紧绷区域",
            sensation_cue="小腿肌肉不由自主紧绷，脚尖产生明显向下蜷曲与痉挛"
        ),
        ElectrodeZone.THIGHS_INNER: ZoneConfig(
            name="大腿内侧与股四头肌 (Inner Thighs)",
            description="贴附于双侧大腿。系统将重点追踪双腿夹紧防守 vs 分开暴露的开合度。",
            target_kpt_indices=[11, 12, 13, 14],
            safety_max_power=70.0,
            narrative_body_part="贴身战服包裹的双侧大腿内侧肌群",
            sensation_cue="大腿肌肉在魔力脉冲下阵阵微颤与夹紧"
        ),
        ElectrodeZone.LOWER_BACK: ZoneConfig(
            name="后腰与下腹部 (Lower Back / Abdomen)",
            description="贴附于腰部或下腹。系统将重点监测脊椎挺直与身体塌陷倒地状态。",
            target_kpt_indices=[18, 19],
            safety_max_power=80.0,
            narrative_body_part="腰部战服收束区与下腹防护层",
            sensation_cue="腰部不由自主弓起，产生深层穿透性震颤"
        ),
        ElectrodeZone.DUAL_TRAVELING: ZoneConfig(
            name="双通道流动模式 (Dual Traveling Wave)",
            description="通道A贴脚踝，通道B贴核心区。触手将从下向上实施交替流动式脉冲打击！",
            target_kpt_indices=[19, 20, 22, 23, 25],
            safety_max_power=65.0,
            narrative_body_part="从小腿一路蔓延至魔法传导器核心的完整回路",
            sensation_cue="两路触手交替放电，形成向上攀爬的流动波"
        )
    }

    def __init__(self, default_zone: ElectrodeZone = ElectrodeZone.CORE_PELVIS):
        self.active_zone = default_zone

    def set_zone(self, zone: ElectrodeZone) -> ZoneConfig:
        if zone in self.ZONE_REGISTRY:
            self.active_zone = zone
        return self.get_config()

    def get_config(self) -> ZoneConfig:
        return self.ZONE_REGISTRY[self.active_zone]

    def get_prompt_context(self) -> str:
        cfg = self.get_config()
        return (
            f"- 物理电极贴片配置: 位于【{cfg.narrative_body_part}】
"
            f"- 预期生理反应: {cfg.sensation_cue}
"
            f"- 剧情提示: 触手的所有缠绕、触碰和放电动作请严格围绕【{cfg.narrative_body_part}】展开，"
            f"根据玩家是否有遮挡或抽搐做出针对性剧情反应。"
        )
