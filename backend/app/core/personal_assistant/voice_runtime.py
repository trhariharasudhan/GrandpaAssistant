from __future__ import annotations

import logging
import os
import threading
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from .context import compact_text


logger = logging.getLogger(__name__)

VOICE_RUNTIME_ENABLED_ENV = "GRANDPA_VOICE_RUNTIME_ENABLED"
WAKE_WORD_ENV = "GRANDPA_WAKE_WORD"
VOICE_LISTEN_TIMEOUT_ENV = "GRANDPA_VOICE_LISTEN_TIMEOUT_SECONDS"
VOICE_IDLE_SLEEP_ENV = "GRANDPA_VOICE_IDLE_SLEEP_SECONDS"
DEFAULT_WAKE_WORD = "Grandpa"
DEFAULT_LISTEN_TIMEOUT_SECONDS = 8.0
DEFAULT_IDLE_SLEEP_SECONDS = 0.25
TRUE_VALUES = {"1", "true", "yes", "on"}


TranscriptListener = Callable[[], str | None]
SpeechOutput = Callable[[str], None]
CommandHandler = Callable[[str], dict[str, Any]]
StatusProvider = Callable[[], dict[str, Any]]


def is_voice_runtime_enabled() -> bool:
    return compact_text(os.getenv(VOICE_RUNTIME_ENABLED_ENV)).lower() in TRUE_VALUES


def configured_wake_word() -> str:
    return compact_text(os.getenv(WAKE_WORD_ENV)) or DEFAULT_WAKE_WORD


def configured_listen_timeout_seconds() -> float:
    raw_value = compact_text(os.getenv(VOICE_LISTEN_TIMEOUT_ENV))
    if not raw_value:
        return DEFAULT_LISTEN_TIMEOUT_SECONDS
    try:
        return max(1.0, float(raw_value))
    except Exception:
        return DEFAULT_LISTEN_TIMEOUT_SECONDS


def configured_idle_sleep_seconds() -> float:
    raw_value = compact_text(os.getenv(VOICE_IDLE_SLEEP_ENV))
    if not raw_value:
        return DEFAULT_IDLE_SLEEP_SECONDS
    try:
        return max(0.01, float(raw_value))
    except Exception:
        return DEFAULT_IDLE_SLEEP_SECONDS


def normalize_phrase(value: Any) -> str:
    return compact_text(value).lower().strip(" ,.!?")


def wake_words() -> list[str]:
    base = configured_wake_word()
    words = {base, "Hey " + base}
    return [normalize_phrase(item) for item in words if normalize_phrase(item)]


def detect_wake_word(transcript: str) -> bool:
    normalized = normalize_phrase(transcript)
    if not normalized:
        return False
    return any(normalized == wake or normalized.startswith(wake + " ") for wake in wake_words())


def strip_wake_word(transcript: str) -> str:
    normalized = normalize_phrase(transcript)
    original = compact_text(transcript)
    for wake in sorted(wake_words(), key=len, reverse=True):
        if normalized == wake:
            return ""
        if normalized.startswith(wake + " "):
            return compact_text(original[len(wake) :])
    return original


def default_listen_for_wake() -> str | None:
    try:
        from voice.listen import listen

        return listen(for_wake_word=True)
    except Exception as error:
        logger.warning("Voice wake listener unavailable: %s", compact_text(error))
        return None


def default_listen_for_command() -> str | None:
    try:
        from voice.listen import listen

        return listen(for_follow_up=True)
    except Exception as error:
        logger.warning("Voice command listener unavailable: %s", compact_text(error))
        return None


def default_speak(text: str) -> None:
    try:
        from voice.speak import speak

        speak(text)
    except Exception as error:
        logger.warning("Voice output unavailable: %s", compact_text(error))


def default_stt_status() -> dict[str, Any]:
    try:
        from voice.listen import stt_backend_payload

        payload = stt_backend_payload()
        return {"available": True, **payload}
    except Exception as error:
        return {"available": False, "last_error": compact_text(error), "resolved_backend": "unavailable"}


def default_handle_command(command: str) -> dict[str, Any]:
    from core import chat_service

    return chat_service.build_chat_reply(command, session_id="voice-runtime-" + uuid.uuid4().hex[:8])


@dataclass
class VoiceRuntimeAdapters:
    listen_for_wake: TranscriptListener = default_listen_for_wake
    listen_for_command: TranscriptListener = default_listen_for_command
    speak: SpeechOutput = default_speak
    handle_command: CommandHandler = default_handle_command
    stt_status: StatusProvider = default_stt_status


class VoiceRuntimeManager:
    def __init__(self, *, adapters: VoiceRuntimeAdapters | None = None, idle_sleep_seconds: float | None = None) -> None:
        self.adapters = adapters or VoiceRuntimeAdapters()
        self._idle_sleep_seconds = max(0.01, float(idle_sleep_seconds if idle_sleep_seconds is not None else configured_idle_sleep_seconds()))
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._last_event = ""
        self._last_error = ""
        self._last_transcript = ""
        self._last_command = ""
        self._last_result: dict[str, Any] = {}
        self._wake_events = 0
        self._commands_handled = 0

    def start(self, *, enabled: bool | None = None) -> bool:
        should_start = is_voice_runtime_enabled() if enabled is None else bool(enabled)
        if not should_start:
            logger.info("Voice runtime disabled by configuration.")
            return False
        with self._lock:
            if self.is_running():
                logger.info("Voice runtime already running.")
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="GrandpaVoiceRuntime", daemon=True)
            self._thread.start()
            self._last_event = "started"
            logger.info("Voice runtime started wake_word=%s", configured_wake_word())
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
            logger.info("Voice runtime stopped.")
        else:
            self._last_error = "Voice runtime did not stop before timeout."
            logger.warning(self._last_error)
        return stopped

    def is_running(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())

    def run_once(self) -> dict[str, Any]:
        try:
            wake_transcript = compact_text(self.adapters.listen_for_wake())
            self._last_transcript = wake_transcript
            if not wake_transcript:
                self._last_event = "no_wake_transcript"
                return {"ok": True, "event": self._last_event, "handled": False}
            if not detect_wake_word(wake_transcript):
                self._last_event = "wake_not_detected"
                return {"ok": True, "event": self._last_event, "handled": False, "transcript": wake_transcript}
            self._wake_events += 1
            command = strip_wake_word(wake_transcript)
            if not command:
                command = compact_text(self.adapters.listen_for_command())
            if not command:
                self._last_event = "command_missing"
                return {"ok": False, "event": self._last_event, "handled": False, "missing_adapter": "speech_to_text"}
            result = self._handle_voice_command(command)
            return result
        except Exception as error:
            self._last_error = compact_text(error)
            self._last_event = "error"
            logger.warning("Voice runtime tick failed: %s", self._last_error)
            return {"ok": False, "event": "error", "handled": False, "error": self._last_error}

    def status(self) -> dict[str, Any]:
        stt_status = self.adapters.stt_status()
        return {
            "enabled": is_voice_runtime_enabled(),
            "running": self.is_running(),
            "wake_word": configured_wake_word(),
            "listen_timeout_seconds": configured_listen_timeout_seconds(),
            "idle_sleep_seconds": self._idle_sleep_seconds,
            "wake_events": self._wake_events,
            "commands_handled": self._commands_handled,
            "last_event": self._last_event,
            "last_error": self._last_error,
            "last_transcript": self._last_transcript,
            "last_command": self._last_command,
            "last_intent": compact_text(self._last_result.get("intent")) if isinstance(self._last_result, dict) else "",
            "last_selected_tool": compact_text(((self._last_result.get("debug") or {}).get("selected_tool")) if isinstance(self._last_result.get("debug"), dict) else ""),
            "stt_provider": stt_status,
            "env_var": VOICE_RUNTIME_ENABLED_ENV,
            "wake_word_env_var": WAKE_WORD_ENV,
            "listen_timeout_env_var": VOICE_LISTEN_TIMEOUT_ENV,
        }

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(self._idle_sleep_seconds)

    def _handle_voice_command(self, command: str) -> dict[str, Any]:
        self._last_command = compact_text(command)
        result = self.adapters.handle_command(self._last_command)
        if not isinstance(result, dict):
            result = {"reply": compact_text(result), "ok": True, "handled": True}
        reply = compact_text(result.get("reply"))
        if reply:
            self.adapters.speak(reply)
        self._commands_handled += 1
        self._last_event = "command_handled"
        self._last_result = result
        logger.info("Voice runtime handled command intent=%s provider=%s", result.get("intent"), result.get("provider"))
        return {"ok": bool(result.get("ok", True)), "event": self._last_event, "handled": True, "command": self._last_command, "result": result}


_GLOBAL_VOICE_RUNTIME = VoiceRuntimeManager()


def get_global_voice_runtime() -> VoiceRuntimeManager:
    return _GLOBAL_VOICE_RUNTIME


def start_global_voice_runtime(*, enabled: bool | None = None) -> bool:
    return _GLOBAL_VOICE_RUNTIME.start(enabled=enabled)


def stop_global_voice_runtime(*, timeout: float = 5.0) -> bool:
    return _GLOBAL_VOICE_RUNTIME.stop(timeout=timeout)


def run_voice_runtime_once() -> dict[str, Any]:
    return _GLOBAL_VOICE_RUNTIME.run_once()


def get_voice_runtime_status() -> dict[str, Any]:
    return _GLOBAL_VOICE_RUNTIME.status()


def enable_voice_runtime() -> dict[str, Any]:
    os.environ[VOICE_RUNTIME_ENABLED_ENV] = "1"
    started = start_global_voice_runtime(enabled=True)
    message = "Voice runtime enabled and listening for the wake word." if started or _GLOBAL_VOICE_RUNTIME.is_running() else "Voice runtime is enabled, but it was already running."
    return {"ok": True, "enabled": True, "running": _GLOBAL_VOICE_RUNTIME.is_running(), "message": message, "status": get_voice_runtime_status()}


def disable_voice_runtime() -> dict[str, Any]:
    os.environ.pop(VOICE_RUNTIME_ENABLED_ENV, None)
    stopped = stop_global_voice_runtime()
    message = "Voice runtime disabled." if stopped else "Voice runtime disable requested, but shutdown did not complete cleanly."
    return {"ok": bool(stopped), "enabled": False, "running": _GLOBAL_VOICE_RUNTIME.is_running(), "message": message, "status": get_voice_runtime_status()}
