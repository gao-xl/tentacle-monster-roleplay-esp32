"""
AI Narrative Engine (Slow Loop) for OpenHaptic-Roleplay
Deeply integrates Multimodal Biometrics (YOLO Pose 26, Gyro, Quad-Pads, Gender)
with Story Campaign Acts to generate in-character voice dialogues via Kokoro TTS.
"""

import os
import time
import json
import logging
import threading
from typing import Optional, Callable, Dict, Any
import requests

from .sensor_fusion import FusedPlayerState
from .gender_tuning import GenderTuningProfile, UserGender
from .electrode_topology import ElectrodeTopologyManager
from ..gameplay.story_director import ScenarioCampaignEngine, StoryNode
from ..drivers.base import DeviceTelemetry

logger = logging.getLogger("SlowLoopEngine")


class SlowLoopEngine:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        profile: Optional[GenderTuningProfile] = None,
        campaign: Optional[ScenarioCampaignEngine] = None,
        interval_sec: float = 6.0
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.profile = profile or GenderTuningProfile(gender=UserGender.NEUTRAL)
        self.campaign = campaign
        self.interval_sec = interval_sec
        
        self._last_call_time = 0.0
        self._is_generating = False
        self.on_narrative_generated: Optional[Callable[[str], None]] = None

    def tick(
        self,
        player_state: FusedPlayerState,
        device_telemetry: Optional[DeviceTelemetry] = None
    ) -> None:
        now = time.time()
        if now - self._last_call_time < self.interval_sec or self._is_generating:
            return

        self._last_call_time = now
        self._is_generating = True

        # Build Rich Narrative Prompt combining Story Lore + Biometrics + Gender
        context = self._build_context_prompt(player_state, device_telemetry)
        threading.Thread(target=self._call_llm_async, args=(context,), daemon=True).start()

    def _build_context_prompt(self, p: FusedPlayerState, t: Optional[DeviceTelemetry]) -> str:
        lines = []
        
        # 1. Story Campaign Lore Context
        if self.campaign:
            lines.append(self.campaign.get_llm_story_context())
            lines.append("------------------------------------------")

        # 2. Gender & Persona Injections
        lines.append(self.profile.narrative_persona_prompt)
        lines.append("------------------------------------------")

        # 3. Live Biometric Sensor Telemetry
        lines.append("[当前现场真实传感器与姿态读数]:")
        lines.append(f"- 身体姿态状态: {p.posture_label}")
        lines.append(f"- 核心防御: 魔法传导器(Point 19)={'【双手死死捂住】' if p.hands_covering_core else '暴露打开'}, 胸口={'【捂住防护】' if p.hands_covering_chest else '无防护'}")
        lines.append(f"- 足底生理痉挛指数: {p.toe_curl_spasm:.0f}% (脚趾蜷缩/脚尖紧绷程度)")
        lines.append(f"- 身体剧烈挣扎指数: {p.struggle_score:.0f}/100")
        lines.append(f"- 身体平衡: {'【已失去平衡彻底倒地/跪倒】' if p.is_collapsed else '仍在勉强支撑姿态'}")
        
        # Add Privacy-Safe Vision Context Cues
        lines.append("[环境与微表情细节 (Local Vision)]:")
        lines.append(f"- 环境光线: {p.env_brightness}")
        lines.append(f"- 玩家衣着: 穿着 {p.clothes_color} 战服")
        lines.append(f"- 玩家面部表情: {p.face_emotion}")
        if p.is_face_shaking:
            lines.append("- ⚠️ 玩家正在剧烈喘息摇晃，画面出现模糊！")

        if t and t.is_connected:
            powers_str = ", ".join([f"回路{k}:{v:.0f}%" for k, v in t.channel_powers.items()])
            lines.append(f"- 4贴片双路硬件输出: {powers_str}")
            if not t.skin_contact:
                lines.append("- ⚠️ 警报: 玩家电极贴片脱落！试图逃脱束缚！")

        lines.append("
请根据剧情幕数、骨骼姿态以及【环境光线、衣服颜色、脸部痛苦表情】，以调皮戏谑的触手语气说出 2~3 句生动台词。要求巧妙点出玩家的衣服颜色或此刻的痛苦表情以增加打破次元壁的压迫感！")
        return "
".join(lines)

    def _call_llm_async(self, user_content: str):
        try:
            if not self.api_key:
                narrative = self._generate_campaign_fallback(user_content)
            else:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是一个沉浸式RPG剧情主持人和调皮爱捉弄人的触手小怪物NPC。"},
                            {"role": "user", "content": user_content}
                        ],
                        "temperature": 0.85,
                        "max_tokens": 180
                    },
                    timeout=8.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    narrative = data["choices"][0]["message"]["content"].strip()
                else:
                    narrative = self._generate_campaign_fallback(user_content)

            logger.info(f"[AI Lore Dialogue] {narrative}")
            if self.on_narrative_generated:
                self.on_narrative_generated(narrative)

        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            narrative = self._generate_campaign_fallback(user_content)
            if self.on_narrative_generated:
                self.on_narrative_generated(narrative)
        finally:
            self._is_generating = False

    def _generate_campaign_fallback(self, content: str) -> str:
        """Campaign-aware fallback dialogue generator."""
        if self.campaign:
            node = self.campaign.get_current_node()
            return node.monster_voice_line
        return "“触手在废弃小屋的阴影中慢慢收拢……战败冒险家的防御正在瓦解。”"