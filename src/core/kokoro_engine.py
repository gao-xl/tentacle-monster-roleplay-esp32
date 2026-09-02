"""
Interruptible Neural TTS Voice Engine for OpenHaptic-Roleplay (v4.0)
Features:
- Priority-based Event Preemption (HIGH: Pain/Breach/Caught, LOW: Background Lore)
- Instant Flush & Play: Drops current queued speech when high-priority reaction occurs
- Real-time Subprocess Audio Piping for sub-50ms voice reactions
"""

import os
import time
import queue
import logging
import threading
import subprocess
from enum import IntEnum
from typing import Optional, Dict, Any, Callable
import soundfile as sf
import numpy as np

logger = logging.getLogger("InterruptibleVoiceEngine")


class VoicePriority(IntEnum):
    LOW_LORE = 1          # Background storytelling / ambient dialogue
    MEDIUM_STATE = 2      # Normal stage progression comments
    HIGH_REACTION = 3     # Instant breach, red-light catch, surrender reactions


class VoiceTask:
    def __init__(self, text: str, priority: VoicePriority, voice: str = "af_sarah", speed: float = 1.0):
        self.text = text
        self.priority = priority
        self.voice = voice
        self.speed = speed
        self.created_at = time.time()


class InterruptibleVoiceEngine:
    def __init__(self, model_path: str = "models/kokoro-v0_19.onnx", voices_path: str = "models/voices.bin"):
        self.model_path = model_path
        self.voices_path = voices_path
        self.kokoro = None
        self._init_kokoro()

        self.speech_queue = queue.PriorityQueue()
        self.is_playing = False
        self._current_player_proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._running = True

        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

    def _init_kokoro(self):
        try:
            from kokoro_onnx import Kokoro
            if os.path.exists(self.model_path) and os.path.exists(self.voices_path):
                self.kokoro = Kokoro(self.model_path, self.voices_path)
                logger.info("[Kokoro TTS] Local Neural Voice Engine Initialized successfully!")
        except Exception as e:
            logger.warning(f"[Kokoro TTS] Neural TTS not ready: {e}. Running in text-event broadcast mode.")

    def speak(
        self,
        text: str,
        priority: VoicePriority = VoicePriority.LOW_LORE,
        voice: str = "af_sarah",
        speed: float = 1.0,
        interrupt_now: bool = False
    ):
        """Queue a voice utterance. If interrupt_now is True, immediately kills current audio."""
        if interrupt_now or priority == VoicePriority.HIGH_REACTION:
            self.flush_and_stop_current()

        # Priority queue sorts lowest value first -> we invert priority to (-priority)
        task = (-int(priority), time.time(), VoiceTask(text, priority, voice, speed))
        self.speech_queue.put(task)
        logger.info(f"[Voice In] [{priority.name}] {text}")

    def flush_and_stop_current(self):
        """Immediately cut off current playing audio and clear background queue."""
        with self._lock:
            # 1. Kill playing audio process
            if self._current_player_proc is not None:
                try:
                    self._current_player_proc.terminate()
                    self._current_player_proc.kill()
                except Exception:
                    pass
                self._current_player_proc = None

            # 2. Clear remaining low-priority queue items
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                except queue.Empty:
                    break

            logger.info("⚡ [Voice Engine] PREEMPTION FLUSH: Audio instantly stopped for High-Priority Event!")

    def _speech_worker(self):
        while self._running:
            try:
                item = self.speech_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            _, _, task = item
            self._synthesize_and_play(task)

    def _synthesize_and_play(self, task: VoiceTask):
        if not self.kokoro:
            return

        try:
            samples, sample_rate = self.kokoro.create(task.text, voice=task.voice, speed=task.speed, lang="zh")
            tmp_wav = f"/tmp/kokoro_{int(time.time()*1000)}.wav" if os.name != 'nt' else f"temp_kokoro_{int(time.time()*1000)}.wav"
            sf.write(tmp_wav, samples, sample_rate)

            # Play using ffplay or aplay
            player_cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_wav]
            with self._lock:
                self._current_player_proc = subprocess.Popen(player_cmd)

            self._current_player_proc.wait()

            # Clean up temp file
            if os.path.exists(tmp_wav):
                try: os.remove(tmp_wav)
                except Exception: pass

        except Exception as e:
            logger.error(f"[Voice Synth Error]: {e}")
        finally:
            with self._lock:
                self._current_player_proc = None
