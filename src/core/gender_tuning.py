"""
Gender-Tailored Persona & Biometric Tuning Engine for OpenHaptic-Roleplay
Customizes:
- Anatomical weakpoint focus (Female: Chest/Pelvis; Male: Conductor Core/Abdomen)
- Haptic waveform pulse dynamics & sensitivity curve
- AI Roleplay narrative tone, character diction, and immersion terminology
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List


class UserGender(str, Enum):
    FEMALE = "FEMALE"   # 女性特调模式
    MALE = "MALE"       # 男性特调模式
    NEUTRAL = "NEUTRAL" # 通用中性模式


class SensitivityLevel(str, Enum):
    DELICATE = "DELICATE"       # 极敏感 (低阈值，细腻微弱脉冲)
    STANDARD = "STANDARD"       # 标准冒险家
    HARDCORE = "HARDCORE"       # 强忍耐受 (高冲击、深度压制)


@dataclass
class GenderTuningProfile:
    gender: UserGender
    sensitivity: SensitivityLevel = SensitivityLevel.STANDARD
    
    # Biometric & Vision Weights
    chest_defense_weight: float = 1.0     # Importance of chest covering detection
    core_defense_weight: float = 1.0      # Importance of pelvic core covering detection
    toe_curl_spasm_weight: float = 1.0    # Foot toe-curling reaction weight
    
    # Haptic Waveform Constants
    preferred_pulse_freq: float = 80.0    # Hz
    safety_power_ceiling: float = 70.0    # Max power limit %
    decay_speed_ms: int = 400
    
    # AI System Prompt Injections
    narrative_persona_prompt: str = ""
    weakpoint_terminology: str = ""


class GenderProfileManager:
    @staticmethod
    def get_profile(gender: UserGender, sensitivity: SensitivityLevel = SensitivityLevel.STANDARD) -> GenderTuningProfile:
        if gender == UserGender.FEMALE:
            prof = GenderTuningProfile(
                gender=UserGender.FEMALE,
                sensitivity=sensitivity,
                chest_defense_weight=1.3,
                core_defense_weight=1.4,
                toe_curl_spasm_weight=1.5,
                preferred_pulse_freq=100.0, # Higher frequency for smoother, tingling sensations
                safety_power_ceiling=60.0 if sensitivity == SensitivityLevel.DELICATE else 70.0,
                decay_speed_ms=500,
                weakpoint_terminology="贴身战衣最下方的魔法传导器核心区与胸前防护甲",
                narrative_persona_prompt=(
                    "【女性冒险家特调模式】：
"
                    "- 玩家是一位魔力耗尽的女性战败冒险家，战衣贴合紧绷。
"
                    "- 触手小怪物特别喜欢观察她双手捂住胸口或紧闭双腿的害羞防守动作。
"
                    "- 当检测到脚尖蜷缩或双腿发软时，戏谑地调侃她的身体诚实反应与战服贴合痕迹。
"
                    "- 保持调皮、坏笑的捉弄感，多描写细腻的电流酥麻感与战服张力变化。"
                )
            )
        elif gender == UserGender.MALE:
            prof = GenderTuningProfile(
                gender=UserGender.MALE,
                sensitivity=sensitivity,
                chest_defense_weight=0.8,
                core_defense_weight=1.6, # Strong focus on pelvic conductor prominence
                toe_curl_spasm_weight=1.1,
                preferred_pulse_freq=50.0, # Lower frequency for deeper, punchier muscle contractions
                safety_power_ceiling=65.0 if sensitivity == SensitivityLevel.DELICATE else 80.0,
                decay_speed_ms=350,
                weakpoint_terminology="贴身战衣最下方根部的魔法传导器核心凸起区与腹肌收束层",
                narrative_persona_prompt=(
                    "【男性冒险家特调模式】：
"
                    "- 玩家是一位体力耗尽但仍试图强撑的男性战败冒险家。
"
                    "- 贴身战服在贴身最下方、双腿根部中央因魔力流动和护甲张力自然形成明显凸起（魔法传导器核心区）。
"
                    "- 触手小怪物喜欢嘲弄他‘嘴上逞强但传导器核心张力已经过载’的倔强反抗。
"
                    "- 当检测到身体剧烈挣扎或下腹部紧绷时，实施强力破防打击，强迫他放下防守。"
                )
            )
        else:
            prof = GenderTuningProfile(
                gender=UserGender.NEUTRAL,
                sensitivity=sensitivity,
                chest_defense_weight=1.0,
                core_defense_weight=1.2,
                toe_curl_spasm_weight=1.0,
                preferred_pulse_freq=75.0,
                safety_power_ceiling=70.0,
                decay_speed_ms=400,
                weakpoint_terminology="战服魔法传导器核心区",
                narrative_persona_prompt="【标准冒险家模式】：观察玩家姿态防御与挣扎，进行中性沉浸式RPG主持。"
            )
        return prof
