"""
Kokoro-82M High-Fidelity Local Neural TTS Engine for OpenHaptic-Roleplay
Provides human-like, character-driven voice synthesis with zero API cost.
Supports emotion adaptation, character presets, and async audio generation.
"""

import os
import threading
import logging
import soundfile as sf
import numpy as np
from typing import Optional, Callable, Dict

logger = logging.getLogger("KokoroVoiceEngine")

try:
    from kokoro_onnx import Kokoro
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False


class KokoroVoiceEngine:
    # Character Presets mapped to Kokoro voice IDs
    VOICE_CHARACTERS = {
        "monster_playful": {
            "voice": "zm_yunxia",     # 调皮灵动少年/小恶魔声线
            "speed": 1.05,
            "desc": "调皮小触手 (Playful Monster)"
        },
        "monster_deep": {
            "voice": "zm_yunjian",    # 磁性低沉/邪魅支配者声线
            "speed": 0.92,
            "desc": "深渊触手王 (Dominant Monster)"
        },
        "narrator_gentle": {
            "voice": "zf_xiaobei",    # 温柔知性大姐姐/系统引导
            "speed": 1.0,
            "desc": "温柔旁白 (Gentle Narrator)"
        },
        "tsundere_queen": {
            "voice": "zf_xiaoni",     # 傲娇/冷艳御姐
            "speed": 1.08,
            "desc": "冷酷审判官 (Strict Examiner)"
        }
    }

    def __init__(
        self,
        model_path: str = "models/tts/kokoro/kokoro-v0.19.onnx",
        voices_path: str = "models/tts/kokoro/voices.json",
        default_character: str = "monster_playful",
        output_dir: str = "src/ui/static/audio"
    ):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.default_character = default_character
        self.model_path = model_path
        self.voices_path = voices_path
        self._counter = 0
        self._lock = threading.Lock()
        self.kokoro: Optional[Kokoro] = None

        self._init_model()

    def _init_model(self):
        if not KOKORO_AVAILABLE:
            logger.warning("[Kokoro] kokoro-onnx package not installed. Run: pip install kokoro-onnx soundfile")
            return

        if not os.path.exists(self.model_path) or not os.path.exists(self.voices_path):
            logger.warning(f"[Kokoro] Model files missing at {self.model_path}. Fallback to Edge-TTS or WebSpeech.")
            return

        try:
            logger.info(f"[Kokoro] Loading Neural TTS model from {self.model_path}...")
            self.kokoro = Kokoro(self.model_path, self.voices_path)
            logger.info("[Kokoro] Model ready! Pre-warming engine...")
            # Pre-warm
            _ = self.kokoro.create("准备就绪", voice="zm_yunxia", speed=1.0, lang="zh")
        except Exception as e:
            logger.error(f"[Kokoro] Failed to initialize model: {e}")
            self.kokoro = None

    def speak_async(
        self,
        text: str,
        character: Optional[str] = None,
        emotion_speed_mod: float = 1.0,
        on_complete: Optional[Callable[[str], None]] = None
    ):
        """Asynchronously synthesize speech and return the static URL."""
        threading.Thread(
            target=self._synth_worker,
            args=(text, character or self.default_character, emotion_speed_mod, on_complete),
            daemon=True
        ).start()

    def _synth_worker(
        self,
        text: str,
        char_key: str,
        speed_mod: float,
        on_complete: Optional[Callable[[str], None]]
    ):
        if not self.kokoro:
            # Fallback mock/edge
            if on_complete:
                on_complete("")
            return

        try:
            char_cfg = self.VOICE_CHARACTERS.get(char_key, self.VOICE_CHARACTERS[self.default_character])
            voice_id = char_cfg["voice"]
            speed = char_cfg["speed"] * speed_mod

            # Synthesize 24kHz audio array
            samples, sample_rate = self.kokoro.create(text, voice=voice_id, speed=speed, lang="zh")

            with self._lock:
                self._counter += 1
                filename = f"speech_{self._counter % 15}.wav"
                filepath = os.path.join(self.output_dir, filename)

            sf.write(filepath, samples, sample_rate, subtype="PCM_16")
            audio_url = f"/static/audio/{filename}"

            if on_complete:
                on_complete(audio_url)

        except Exception as e:
            logger.error(f"[Kokoro] Speech synthesis error: {e}")
            if on_complete:
                on_complete("")
