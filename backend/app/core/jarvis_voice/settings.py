from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from typing import Any

try:
    from utils.paths import backend_data_path
except Exception:  # pragma: no cover
    backend_data_path = None


SETTINGS_PATH_ENV = "GRANDPA_JARVIS_VOICE_SETTINGS_PATH"
RUNTIME_ENABLED_ENV = "GRANDPA_JARVIS_VOICE_ENABLED"
TRUE_VALUES = {"1", "true", "yes", "on"}


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _settings_path() -> str:
    configured = _compact_text(os.getenv(SETTINGS_PATH_ENV))
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    if backend_data_path is not None:
        return backend_data_path("jarvis_voice_settings.json")
    return os.path.abspath(os.path.join("runtime", "data", "jarvis_voice_settings.json"))


@dataclass
class JarvisVoiceSettings:
    enabled: bool = False
    wake_words: list[str] = field(default_factory=lambda: ["hey grandpa"])
    continuous_listening: bool = True
    push_to_talk_enabled: bool = True
    stt_backend: str = "whisper"
    tts_backend: str = "piper"
    fallback_tts_backend: str = "xtts"
    voice_profile: str = "grandpa"
    language: str = "auto"
    multilingual: bool = True
    vad_enabled: bool = True
    noise_suppression_enabled: bool = True
    auto_mute: bool = True
    interruptible: bool = True
    streaming_enabled: bool = True
    emotion_aware: bool = True
    listen_timeout_seconds: float = 8.0
    idle_sleep_seconds: float = 0.05
    response_latency_target_ms: int = 700
    max_reply_chars_for_voice: int = 1200


def _coerce_settings(payload: dict[str, Any] | None) -> JarvisVoiceSettings:
    data = payload if isinstance(payload, dict) else {}
    defaults = asdict(JarvisVoiceSettings())
    merged = {**defaults, **{key: value for key, value in data.items() if key in defaults}}
    wake_words = merged.get("wake_words")
    if isinstance(wake_words, str):
        wake_words = [wake_words]
    if not isinstance(wake_words, list):
        wake_words = defaults["wake_words"]
    merged["wake_words"] = [_compact_text(item).lower() for item in wake_words if _compact_text(item)] or defaults["wake_words"]
    for key in ("listen_timeout_seconds", "idle_sleep_seconds"):
        try:
            merged[key] = max(0.01, float(merged[key]))
        except Exception:
            merged[key] = defaults[key]
    try:
        merged["response_latency_target_ms"] = max(100, int(merged["response_latency_target_ms"]))
    except Exception:
        merged["response_latency_target_ms"] = defaults["response_latency_target_ms"]
    try:
        merged["max_reply_chars_for_voice"] = max(120, int(merged["max_reply_chars_for_voice"]))
    except Exception:
        merged["max_reply_chars_for_voice"] = defaults["max_reply_chars_for_voice"]
    return JarvisVoiceSettings(**merged)


def load_voice_settings() -> JarvisVoiceSettings:
    path = _settings_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        payload = {}
    except Exception:
        payload = {}
    settings = _coerce_settings(payload)
    if _compact_text(os.getenv(RUNTIME_ENABLED_ENV)).lower() in TRUE_VALUES:
        settings.enabled = True
    return settings


def save_voice_settings(settings: JarvisVoiceSettings | dict[str, Any]) -> JarvisVoiceSettings:
    coerced = settings if isinstance(settings, JarvisVoiceSettings) else _coerce_settings(settings)
    path = _settings_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".jarvis-voice-", suffix=".json", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(asdict(coerced), handle, indent=2, sort_keys=True)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
    return coerced


def update_voice_settings(updates: dict[str, Any]) -> JarvisVoiceSettings:
    current = asdict(load_voice_settings())
    for key, value in (updates or {}).items():
        if key in current:
            current[key] = value
    return save_voice_settings(current)


def voice_settings_status() -> dict[str, Any]:
    settings = load_voice_settings()
    return {
        "ok": True,
        "path": _settings_path(),
        "enabled": settings.enabled,
        "wake_words": list(settings.wake_words),
        "continuous_listening": settings.continuous_listening,
        "push_to_talk_enabled": settings.push_to_talk_enabled,
        "stt_backend": settings.stt_backend,
        "tts_backend": settings.tts_backend,
        "fallback_tts_backend": settings.fallback_tts_backend,
        "voice_profile": settings.voice_profile,
        "language": settings.language,
        "multilingual": settings.multilingual,
        "vad_enabled": settings.vad_enabled,
        "noise_suppression_enabled": settings.noise_suppression_enabled,
        "auto_mute": settings.auto_mute,
        "interruptible": settings.interruptible,
        "streaming_enabled": settings.streaming_enabled,
        "emotion_aware": settings.emotion_aware,
        "response_latency_target_ms": settings.response_latency_target_ms,
    }
