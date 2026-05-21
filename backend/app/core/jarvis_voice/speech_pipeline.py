from __future__ import annotations

import audioop
import importlib.util
from dataclasses import dataclass
from typing import Any, Callable

from .settings import JarvisVoiceSettings


def _compact_text(value: Any, limit: int = 1200) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


TranscriptListener = Callable[..., str | None]
SpeechOutput = Callable[[str], None]
StopSpeech = Callable[[], None]


@dataclass
class SpeechPipelineAdapters:
    listen: TranscriptListener | None = None
    speak: SpeechOutput | None = None
    stop_speaking: StopSpeech | None = None


class SpeechPipeline:
    def __init__(self, settings: JarvisVoiceSettings, adapters: SpeechPipelineAdapters | None = None) -> None:
        self.settings = settings
        self.adapters = adapters or SpeechPipelineAdapters()
        self.last_stt_error = ""
        self.last_tts_error = ""
        self.last_backend_used = ""
        self.muted = False

    def listen_for_wake(self) -> str:
        return self._listen(for_wake_word=True)

    def listen_for_command(self, *, push_to_talk: bool = False) -> str:
        return self._listen(for_follow_up=not push_to_talk)

    def _listen(self, **kwargs: Any) -> str:
        try:
            listener = self.adapters.listen
            if listener is None:
                from voice.listen import listen

                listener = listen
            transcript = listener(**kwargs)
            self.last_stt_error = ""
            self.last_backend_used = self.settings.stt_backend
            return _compact_text(transcript)
        except Exception as error:
            self.last_stt_error = _compact_text(error, 240)
            return ""

    def speak(self, text: str, *, emotion: str = "neutral") -> dict[str, Any]:
        if self.muted:
            return {"ok": True, "muted": True, "spoken": False, "backend": self.settings.tts_backend, "error": ""}
        safe_text = _compact_text(text, self.settings.max_reply_chars_for_voice)
        if not safe_text:
            return {"ok": True, "muted": False, "spoken": False, "backend": self.settings.tts_backend, "error": ""}
        try:
            speaker = self.adapters.speak
            if speaker is None:
                from voice.speak import speak

                speaker = speak
            speaker(safe_text)
            self.last_tts_error = ""
            return {"ok": True, "muted": False, "spoken": True, "backend": self.settings.tts_backend, "emotion": emotion, "error": ""}
        except Exception as error:
            self.last_tts_error = _compact_text(error, 240)
            return {"ok": False, "muted": False, "spoken": False, "backend": self.settings.tts_backend, "emotion": emotion, "error": self.last_tts_error}

    def stop_speaking(self) -> dict[str, Any]:
        try:
            stopper = self.adapters.stop_speaking
            if stopper is None:
                from voice.speak import stop_speaking

                stopper = stop_speaking
            stopper()
            return {"ok": True, "error": ""}
        except Exception as error:
            return {"ok": False, "error": _compact_text(error, 240)}

    def auto_mute(self, muted: bool) -> None:
        self.muted = bool(muted)

    def voice_activity_detected(self, audio_bytes: bytes, *, sample_width: int = 2, threshold: int = 350) -> bool:
        if not self.settings.vad_enabled or not audio_bytes:
            return False
        try:
            return audioop.rms(audio_bytes, sample_width) >= threshold
        except Exception:
            return False

    def suppress_noise(self, audio_bytes: bytes) -> bytes:
        if not self.settings.noise_suppression_enabled:
            return audio_bytes
        # Lightweight local placeholder: preserve audio while keeping the hook explicit and testable.
        return audio_bytes or b""

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "stt_backend": self.settings.stt_backend,
            "tts_backend": self.settings.tts_backend,
            "fallback_tts_backend": self.settings.fallback_tts_backend,
            "whisper_available": importlib.util.find_spec("whisper") is not None,
            "piper_available": importlib.util.find_spec("piper") is not None,
            "xtts_available": importlib.util.find_spec("TTS") is not None,
            "vad_enabled": self.settings.vad_enabled,
            "noise_suppression_enabled": self.settings.noise_suppression_enabled,
            "muted": self.muted,
            "last_stt_error": self.last_stt_error,
            "last_tts_error": self.last_tts_error,
            "last_backend_used": self.last_backend_used,
        }
