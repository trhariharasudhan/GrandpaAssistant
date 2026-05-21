from __future__ import annotations

import logging
import threading
import time
from typing import Any

from .conversation_state import ConversationStateManager
from .settings import JarvisVoiceSettings, load_voice_settings, save_voice_settings, update_voice_settings
from .speech_pipeline import SpeechPipeline, SpeechPipelineAdapters
from .streaming_router import StreamingVoiceRouter
from .wake_word import WakeWordEngine


logger = logging.getLogger(__name__)


def _compact_text(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


class VoiceManager:
    def __init__(
        self,
        *,
        settings: JarvisVoiceSettings | None = None,
        pipeline: SpeechPipeline | None = None,
        router: StreamingVoiceRouter | None = None,
        state_manager: ConversationStateManager | None = None,
    ) -> None:
        self.settings = settings or load_voice_settings()
        self.state_manager = state_manager or ConversationStateManager()
        self.pipeline = pipeline or SpeechPipeline(self.settings)
        self.router = router or StreamingVoiceRouter(self.settings, self.state_manager)
        self.wake_word_engine = WakeWordEngine(self.settings.wake_words)
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._last_event = ""
        self._last_error = ""
        self._wake_count = 0
        self._command_count = 0
        self._interrupt_count = 0
        self._last_latency_ms = 0.0

    def start(self, *, enabled: bool | None = None) -> bool:
        should_start = self.settings.enabled if enabled is None else bool(enabled)
        if not should_start:
            self._last_event = "disabled"
            return False
        with self._lock:
            if self.is_running():
                self._last_event = "already_running"
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="GrandpaJarvisVoice", daemon=True)
            self._thread.start()
            self._last_event = "started"
            logger.info("Jarvis voice manager started.")
            return True

    def stop(self, *, timeout: float = 5.0) -> bool:
        with self._lock:
            thread = self._thread
            if thread is None:
                self._last_event = "stopped"
                return True
            self._stop_event.set()
        thread.join(timeout=max(0.1, timeout))
        stopped = not thread.is_alive()
        if stopped:
            with self._lock:
                if self._thread is thread:
                    self._thread = None
            self._last_event = "stopped"
        else:
            self._last_error = "Voice manager did not stop before timeout."
        return stopped

    def is_running(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())

    def interrupt(self, *, session_id: str = "jarvis-voice") -> dict[str, Any]:
        self._interrupt_count += 1
        self.state_manager.mark_interrupted(session_id)
        stop_result = self.pipeline.stop_speaking()
        self._last_event = "interrupted"
        return {"ok": bool(stop_result.get("ok", True)), "event": "interrupted", "stop_result": stop_result}

    def set_muted(self, muted: bool, *, session_id: str = "jarvis-voice") -> dict[str, Any]:
        self.pipeline.auto_mute(muted)
        self.state_manager.set_muted(session_id, muted)
        self._last_event = "muted" if muted else "unmuted"
        return {"ok": True, "muted": bool(muted)}

    def process_transcript(self, transcript: str, *, session_id: str = "jarvis-voice", source: str = "voice") -> dict[str, Any]:
        text = _compact_text(transcript)
        if not text:
            self._last_event = "empty_transcript"
            return {"ok": False, "event": "empty_transcript", "reply": "I did not hear a command."}
        start = time.perf_counter()
        if self.settings.interruptible:
            self.pipeline.stop_speaking()
        result = self.router.route_text(text, session_id=session_id, source=source)
        emotion = self.state_manager.get(session_id).emotion_hint
        speech = self.pipeline.speak(result.get("reply", ""), emotion=emotion)
        self._command_count += 1
        self._last_event = "command_processed"
        self._last_latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {**result, "event": self._last_event, "speech": speech, "latency_ms": self._last_latency_ms}

    def push_to_talk(self, transcript: str | None = None, *, session_id: str = "jarvis-ptt") -> dict[str, Any]:
        command = _compact_text(transcript) or self.pipeline.listen_for_command(push_to_talk=True)
        return self.process_transcript(command, session_id=session_id, source="push_to_talk")

    def run_once(self, *, session_id: str = "jarvis-voice") -> dict[str, Any]:
        heard = self.pipeline.listen_for_wake()
        wake = self.wake_word_engine.extract_command(heard)
        if not wake["wake_detected"]:
            self._last_event = "wake_not_detected"
            return {"ok": True, "event": self._last_event, "handled": False}
        self._wake_count += 1
        command = _compact_text(wake.get("command")) or self.pipeline.listen_for_command()
        if not command:
            self._last_event = "command_missing"
            return {"ok": False, "event": self._last_event, "handled": False, "missing": "command_transcript"}
        result = self.process_transcript(command, session_id=session_id, source="wake_word")
        return {**result, "handled": True, "wake": wake}

    def stream_transcript(self, transcript: str, *, session_id: str = "jarvis-voice", source: str = "voice") -> list[dict[str, Any]]:
        if self.settings.interruptible:
            self.pipeline.stop_speaking()
        events = list(self.router.stream_text(transcript, session_id=session_id, source=source))
        final = next((event for event in reversed(events) if event.get("type") == "done"), {})
        if final.get("reply"):
            self.pipeline.speak(final["reply"], emotion=self.state_manager.get(session_id).emotion_hint)
        return events

    def update_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        self.settings = update_voice_settings(updates)
        self.pipeline.settings = self.settings
        self.router.settings = self.settings
        self.wake_word_engine = WakeWordEngine(self.settings.wake_words)
        return self.status()

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "enabled": self.settings.enabled,
            "running": self.is_running(),
            "wake_words": list(self.settings.wake_words),
            "continuous_listening": self.settings.continuous_listening,
            "push_to_talk_enabled": self.settings.push_to_talk_enabled,
            "interruptible": self.settings.interruptible,
            "streaming_enabled": self.settings.streaming_enabled,
            "auto_mute": self.settings.auto_mute,
            "voice_profile": self.settings.voice_profile,
            "language": self.settings.language,
            "multilingual": self.settings.multilingual,
            "wake_count": self._wake_count,
            "command_count": self._command_count,
            "interrupt_count": self._interrupt_count,
            "last_event": self._last_event,
            "last_error": self._last_error,
            "last_latency_ms": self._last_latency_ms,
            "pipeline": self.pipeline.status(),
            "state": self.state_manager.snapshot("jarvis-voice"),
        }

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
                self._last_error = ""
            except Exception as error:
                self._last_error = _compact_text(error, 240)
                logger.warning("Jarvis voice loop failed: %s", self._last_error)
            self._stop_event.wait(self.settings.idle_sleep_seconds)


_GLOBAL_MANAGER: VoiceManager | None = None
_GLOBAL_LOCK = threading.RLock()


def get_global_voice_manager() -> VoiceManager:
    global _GLOBAL_MANAGER
    with _GLOBAL_LOCK:
        if _GLOBAL_MANAGER is None:
            _GLOBAL_MANAGER = VoiceManager()
        return _GLOBAL_MANAGER


def start_global_voice_manager() -> dict[str, Any]:
    manager = get_global_voice_manager()
    started = manager.start()
    return {"ok": True, "started": started, "status": manager.status()}


def stop_global_voice_manager() -> dict[str, Any]:
    manager = get_global_voice_manager()
    stopped = manager.stop()
    return {"ok": bool(stopped), "stopped": stopped, "status": manager.status()}


def save_global_voice_settings(updates: dict[str, Any]) -> dict[str, Any]:
    return get_global_voice_manager().update_settings(updates)
