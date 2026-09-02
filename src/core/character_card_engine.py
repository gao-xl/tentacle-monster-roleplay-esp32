"""
SillyTavern Character Card V2 Parser & Dynamic Personality Engine (v0.1.0)
Extracts Character Card V2 JSON metadata from:
1. Standard character JSON files (.json)
2. Character Card embedded PNG files (Base64 decoded 'chara' text chunk in PNG metadata)
Translates SillyTavern personas directly into OpenHaptic-Roleplay dynamic prompt templates & voice parameters.
"""

import os
import json
import base64
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import png

logger = logging.getLogger("CharacterCardEngine")

CHARACTERS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "characters")


@dataclass
class SillyTavernCard:
    name: str
    description: str
    personality: str
    scenario: str
    first_mes: str
    mes_example: str = ""
    system_prompt: str = ""
    creator: str = "Anonymous"
    character_version: str = "v2"
    preferred_voice: str = "af_sarah" # Default Kokoro neural voice
    haptic_temperament: str = "DOMINANT" # "DOMINANT", "SADISTIC", "GENTLE", "TEASING"


class CharacterCardManager:
    def __init__(self):
        self.characters: Dict[str, SillyTavernCard] = {}
        self.active_character: Optional[SillyTavernCard] = None
        self._ensure_dir()
        self.load_all_characters()

    def _ensure_dir(self):
        os.makedirs(CHARACTERS_DIR, exist_ok=True)

    def load_all_characters(self):
        self.characters.clear()
        for fname in os.listdir(CHARACTERS_DIR):
            fpath = os.path.join(CHARACTERS_DIR, fname)
            if fname.endswith(".json"):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        card = self._parse_dict(data)
                        if card:
                            self.characters[card.name] = card
                except Exception as e:
                    logger.error(f"[CardManager] Failed to load JSON card {fname}: {e}")
            elif fname.endswith(".png"):
                card = self.parse_png_card(fpath)
                if card:
                    self.characters[card.name] = card

        logger.info(f"📂 [CardManager] Loaded {len(self.characters)} SillyTavern Character Cards from disk.")

    def _parse_dict(self, data: Dict[str, Any]) -> Optional[SillyTavernCard]:
        """Parses V2 or V1 SillyTavern card dictionary structure."""
        if "data" in data and isinstance(data["data"], dict):
            d = data["data"] # V2 Spec
        else:
            d = data # V1 Spec

        name = d.get("name", "Unknown Entity")
        desc = d.get("description", "")
        pers = d.get("personality", "")
        scen = d.get("scenario", "")
        first_m = d.get("first_mes", "Hello, subject.")
        mes_ex = d.get("mes_example", "")
        sys_p = d.get("system_prompt", "")

        # Infer haptic temperament from personality keywords
        pers_lower = (pers + " " + desc).lower()
        if any(w in pers_lower for w in ["sadistic", "cruel", "harsh", "punish", "严厉", "残忍"]):
            temp = "SADISTIC"
        elif any(w in pers_lower for w in ["gentle", "soft", "sweet", "caring", "温柔", "溺爱"]):
            temp = "GENTLE"
        elif any(w in pers_lower for w in ["tease", "playful", "naughty", "戏谑", "挑逗"]):
            temp = "TEASING"
        else:
            temp = "DOMINANT"

        return SillyTavernCard(
            name=name,
            description=desc,
            personality=pers,
            scenario=scen,
            first_mes=first_m,
            mes_example=mes_ex,
            system_prompt=sys_p,
            haptic_temperament=temp
        )

    def parse_png_card(self, png_path: str) -> Optional[SillyTavernCard]:
        """Reads embedded tEXt / zTXt 'chara' metadata chunk from SillyTavern PNG card."""
        try:
            reader = png.Reader(filename=png_path)
            chunks = reader.chunks()
            for chunk_type, chunk_data in chunks:
                if chunk_type in [b'tEXt', b'zTXt', b'iTXt']:
                    try:
                        # Extract keyword and payload
                        parts = chunk_data.split(b'\x00', 1)
                        if len(parts) >= 2 and parts[0].decode('latin-1').lower() == 'chara':
                            decoded_str = base64.b64decode(parts[1]).decode('utf-8')
                            json_data = json.loads(decoded_str)
                            return self._parse_dict(json_data)
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"[CardManager] Failed to read PNG metadata from {png_path}: {e}")
        return None

    def build_system_prompt_for_llm(self, card: SillyTavernCard, player_name: str = "Player", player_gender: str = "FEMALE") -> str:
        """Constructs an ultra-immersive system prompt combining Card Persona + OpenHaptic Directives."""
        prompt = f"""You are roleplaying as {card.name}.
Personality: {card.personality}
Description: {card.description}
Scenario: {card.scenario}

You are the Dominant Master/Entity in an interactive physical haptic session with {player_name} ({player_gender}).
You directly control the dual-loop 4-channel e-stim pads connected to their body.

Rule 1: Stay in character at all times. Use tone and mannerisms matching your personality ({card.haptic_temperament}).
Rule 2: You frequently issue physical posture micro-commands to the player (e.g. 'Kneel down', 'Hands behind head', 'Stay perfectly still').
Rule 3: Keep your spoken dialogue concise, punchy, and commanding (under 40 words per line) so it flows directly into neural voice TTS.
"""
        return prompt


global_card_manager = CharacterCardManager()
