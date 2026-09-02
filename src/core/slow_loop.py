"""
AI Narrative Engine (Slow Loop) for OpenHaptic-Roleplay
Aggregates multimodal telemetry (YOLO Pose, Gyro IMU, Device Output)
and calls LLMs (DeepSeek / OpenAI / Ollama / Claude) to generate in-character narrative & tactics.
"""

import os
import time
import json
import logging
import threading
from typing import Optional, Callable, Dict, Any
import requests

from .sensor_fusion import FusedPlayerState
from ..drivers.base import DeviceTelemetry

logger = logging.getLogger("SlowLoopEngine")


class SlowLoopEngine:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        system_prompt: Optional[str] = None,
        interval_sec: float = 6.0
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.interval_sec = interval_sec
        self.system_prompt = system_prompt or "你是一个调皮的触手小怪物NPC，观察玩家的姿态与反应并进行生动角色扮演。"
        
        self._last_call_time = 0.0
        self._is_generating = False
        self.on_narrative_generated: Optional[Callable[[str], None]] = None

    def tick(
        self,
        player_state: FusedPlayerState,
        device_telemetry: Optional[DeviceTelemetry] = None
    ) -> None:
        """Called regularly by the main loop. Triggers async LLM call if cooldown has elapsed."""
        now = time.time()
        if now - self._last_call_time < self.interval_sec or self._is_generating:
            return

        self._last_call_time = now
        self._is_generating = True

        # Build context prompt
        context = self._build_context_prompt(player_state, device_telemetry)
        
        # Fire asynchronous LLM generation
        threading.Thread(target=self._call_llm_async, args=(context,), daemon=True).start()

    def _build_context_prompt(self, p: FusedPlayerState, t: Optional[DeviceTelemetry]) -> str:
        lines = ["[当前现场传感器读数与战况]"]
        lines.append(f"- 玩家姿态: {p.posture_label}")
        lines.append(f"- 手部防御: 核心弱点区={'已遮挡' if p.hands_covering_core else '暴露'}, 胸部={'已遮挡' if p.hands_covering_chest else '暴露'}")
        lines.append(f"- 挣扎与抗拒指数: {p.struggle_score:.0f}/100")
        lines.append(f"- 生理抽搐/痉挛指数: {p.tremor_intensity:.0f}/100")
        lines.append(f"- 身体平衡: {'【已倒地/翻滚】' if p.is_collapsed else '保持姿态'}")

        if t and t.is_connected:
            powers_str = ", ".join([f"CH{k}:{v:.0f}%" for k, v in t.channel_powers.items()])
            lines.append(f"- 硬件反馈输出: {powers_str}")
            if t.battery_level is not None:
                lines.append(f"- 设备电量: {t.battery_level}%")
            if not t.skin_contact:
                lines.append("- ⚠️ 警报: 玩家贴片脱落/接触不良！可能在试图摆脱控制！")

        lines.append("
请根据以上现场真实状态，以触手怪物的语气给出 2~3 句生动的剧情台词与动作描述。")
        return "
".join(lines)

    def _call_llm_async(self, user_content: str):
        try:
            if not self.api_key:
                # Built-in Mock Generation if no API key provided
                narrative = self._generate_rule_fallback(user_content)
            else:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        "temperature": 0.8,
                        "max_tokens": 200
                    },
                    timeout=10.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    narrative = data["choices"][0]["message"]["content"].strip()
                else:
                    logger.warning(f"LLM API returned error {resp.status_code}: {resp.text}")
                    narrative = self._generate_rule_fallback(user_content)

            logger.info(f"[AI Narrator] {narrative}")
            if self.on_narrative_generated:
                self.on_narrative_generated(narrative)

        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            narrative = self._generate_rule_fallback(user_content)
            if self.on_narrative_generated:
                self.on_narrative_generated(narrative)
        finally:
            self._is_generating = False

    def _generate_rule_fallback(self, content: str) -> str:
        """Fallback dynamic dialog generator when offline or no API key."""
        if "已遮挡" in content and "核心弱点区=已遮挡" in content:
            return "“嘻嘻~ 这么急着护住魔法传导器？触手的吸盘可是最喜欢这种紧绷的战衣张力了呢！”"
        elif "【已倒地/翻滚】" in content:
            return "“哎呀，站不稳倒在地上了吗？那触手们可要趁机把你完全缠紧啰~”"
        elif "挣扎与抗拒指数: 7" in content or "挣扎与抗拒指数: 8" in content:
            return "“挣扎得这么剧烈，魔力负荷只会上升得更快哦！乖乖接受触手们的魔法检查吧！”"
        elif "警报: 玩家贴片脱落" in content:
            return "“咦？想偷偷把魔法电极摘掉逃跑？小触手可不会允许作弊的行为呢，加倍惩罚！”"
        else:
            return "“触手在小屋的阴影中慢慢蠕动……正在试探着战败冒险家的防御薄弱点。”"
