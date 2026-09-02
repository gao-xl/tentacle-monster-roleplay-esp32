"""
Procedural Audio & SFX Generator for Web Audio API & Roleplay Feedback
Generates or describes real-time sound cues (shock zaps, whip strikes, heartbeat pulses).
"""

from typing import Dict, Any


class SoundEffectsRegistry:
    """Provides sound triggers and synthesizer parameters for Web Audio API."""

    @staticmethod
    def get_sfx_for_event(event_name: str) -> Dict[str, Any]:
        """Returns procedural audio parameters to be rendered instantly by browser AudioContext."""
        sfx_map = {
            "hit": {
                "type": "impact",
                "freq_start": 350,
                "freq_end": 40,
                "duration": 0.25,
                "noise": 0.4,
                "label": "💥 物理打击"
            },
            "shock": {
                "type": "electric_zap",
                "freq_start": 800,
                "freq_end": 120,
                "duration": 0.35,
                "noise": 0.8,
                "label": "⚡ 电弧放电"
            },
            "wave": {
                "type": "resonance",
                "freq_start": 90,
                "freq_end": 180,
                "duration": 0.8,
                "noise": 0.1,
                "label": "🌊 缠绕共振"
            },
            "defense_breach": {
                "type": "glass_shatter",
                "freq_start": 1200,
                "freq_end": 300,
                "duration": 0.45,
                "noise": 0.6,
                "label": "🛡️ 护甲破防"
            },
            "heartbeat": {
                "type": "sub_bass",
                "freq_start": 60,
                "freq_end": 30,
                "duration": 0.15,
                "noise": 0.0,
                "label": "💓 心跳重击"
            }
        }
        return sfx_map.get(event_name, sfx_map["hit"])
