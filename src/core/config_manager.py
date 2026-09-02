"""
Persistent Global Configuration Manager & Settings API for OpenHaptic-Roleplay (v4.3)
Saves user preferences (OpenRouter API keys, Hardware Ceilings, Gender, Electrode Topology)
to 'config/user_settings.json'.
"""

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any

logger = logging.getLogger("ConfigManager")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "user_settings.json")


@dataclass
class UserSettings:
    # 1. AI & LLM Settings
    llm_provider: str = "openrouter"          # "openrouter", "deepseek", "openai", "ollama"
    api_key: str = ""
    api_base_url: str = "https://openrouter.ai/api/v1"
    model_name: str = "deepseek/deepseek-chat"
    voice_character: str = "af_sarah"
    voice_speed: float = 1.0

    # 2. Hardware & Safety
    serial_port: str = "COM3"
    safety_power_ceiling: float = 70.0        # Max %
    rolling_heartbeat_enabled: bool = True

    # 3. Gender & Topology
    user_gender: str = "FEMALE"               # "FEMALE", "MALE", "NEUTRAL"
    sensitivity_level: str = "STANDARD"       # "DELICATE", "STANDARD", "HARDCORE"
    electrode_layout: str = "TRAVELING_VERTICAL" # "TRAVELING_VERTICAL", "BILATERAL_THIGHS", "CROSS_CORE_BACK"

    # 4. Vision
    one_euro_filter_beta: float = 0.04


class ConfigManager:
    def __init__(self):
        self.settings = UserSettings()
        self.load()

    def load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if hasattr(self.settings, k):
                            setattr(self.settings, k, v)
                logger.info(f"[ConfigManager] Loaded settings from {CONFIG_PATH}")
            except Exception as e:
                logger.error(f"[ConfigManager] Failed to read {CONFIG_PATH}: {e}")

    def save(self, new_data: Dict[str, Any]) -> bool:
        try:
            for k, v in new_data.items():
                if hasattr(self.settings, k):
                    setattr(self.settings, k, v)

            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(asdict(self.settings), f, indent=2, ensure_ascii=False)

            logger.info("[ConfigManager] Successfully saved settings.")
            return True
        except Exception as e:
            logger.error(f"[ConfigManager] Save failed: {e}")
            return False

    def get_dict(self) -> Dict[str, Any]:
        return asdict(self.settings)


global_config_mgr = ConfigManager()
