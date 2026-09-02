"""
TTS Voice Engine for OpenHaptic-Roleplay
Generates spoken audio lines for AI Monster / RPG Narrator using edge-tts.
"""

import os
import asyncio
import logging
import threading
from typing import Optional, Callable

logger = logging.getLogger("TTSEngine")


class TTSEngine:
    def __init__(self, voice: str = "zh-CN-YunxiNeural", output_dir: str = "src/ui/static/audio"):
        self.voice = voice
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self._counter = 0

    def speak_async(self, text: str, on_complete: Optional[Callable[[str], None]] = None) -> None:
        """Non-blocking text-to-speech synthesis."""
        threading.Thread(target=self._speak_worker, args=(text, on_complete), daemon=True).start()

    def _speak_worker(self, text: str, on_complete: Optional[Callable[[str], None]]):
        try:
            import edge_tts
            self._counter += 1
            filename = f"speech_{self._counter % 20}.mp3"
            filepath = os.path.join(self.output_dir, filename)

            async def _run():
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(filepath)

            asyncio.run(_run())
            audio_url = f"/static/audio/{filename}"
            if on_complete:
                on_complete(audio_url)
        except ImportError:
            logger.debug("edge-tts not installed. Browser Web Speech API fallback will be used.")
            if on_complete:
                on_complete("")
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            if on_complete:
                on_complete("")
