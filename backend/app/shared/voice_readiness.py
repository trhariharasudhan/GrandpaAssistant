"""Voice stack readiness summary for desktop runtime and diagnostics."""

from __future__ import annotations

import os
import shutil
from typing import Any

from utils.config import get_setting


def _module_is_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def _compact(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _pyttsx3_status() -> dict[str, Any]:
    ready = _module_is_available("pyttsx3")
    return {
        "id": "pyttsx3_tts",
        "status": "ok" if ready else "warning",
        "ready": ready,
        "detail": "Windows SAPI/pyttsx3 TTS is available." if ready else "pyttsx3 is not installed.",
    }


def _voice_input_status() -> dict[str, Any]:
    speech_ready = _module_is_available("speech_recognition")
    sounddevice_ready = _module_is_available("sounddevice")
    pyaudio_ready = _module_is_available("pyaudio")
    if speech_ready and (sounddevice_ready or pyaudio_ready):
        backend = "sounddevice" if sounddevice_ready else "pyaudio"
        return {
            "id": "voice_input",
            "status": "ok",
            "ready": True,
            "detail": f"Microphone STT ready via SpeechRecognition + {backend}.",
            "speech_recognition": True,
            "sounddevice": sounddevice_ready,
            "pyaudio": pyaudio_ready,
        }
    if speech_ready:
        return {
            "id": "voice_input",
            "status": "warning",
            "ready": False,
            "detail": "SpeechRecognition is installed but no microphone backend (sounddevice/PyAudio) is available.",
            "speech_recognition": True,
            "sounddevice": sounddevice_ready,
            "pyaudio": pyaudio_ready,
        }
    return {
        "id": "voice_input",
        "status": "warning",
        "ready": False,
        "detail": "SpeechRecognition is not installed.",
        "speech_recognition": False,
        "sounddevice": sounddevice_ready,
        "pyaudio": pyaudio_ready,
    }


def _piper_status() -> dict[str, Any]:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    candidates = [
        _compact(os.getenv("PIPER_PATH", "")),
        os.path.join(project_root, ".python311", "Scripts", "piper.exe"),
        os.path.join(project_root, ".venv", "Scripts", "piper.exe"),
        shutil.which("piper.exe") or "",
        shutil.which("piper") or "",
    ]
    executable = next((path for path in candidates if path and os.path.exists(path)), "")
    model_path = _compact(os.getenv("PIPER_MODEL_PATH", "")) or _compact(get_setting("voice.piper_model_path", ""))
    if executable and model_path and os.path.exists(model_path):
        return {
            "id": "piper_tts",
            "status": "ok",
            "ready": True,
            "detail": f"Piper TTS ready ({os.path.basename(model_path)}).",
            "executable": executable,
            "model_path": model_path,
        }
    if executable:
        return {
            "id": "piper_tts",
            "status": "warning",
            "ready": False,
            "detail": "Piper executable found but voice model path is missing or invalid.",
            "executable": executable,
            "model_path": model_path,
        }
    return {
        "id": "piper_tts",
        "status": "warning",
        "ready": False,
        "detail": "Piper executable was not found.",
        "executable": "",
        "model_path": model_path,
    }


def _voice_runtime_status() -> dict[str, Any]:
    enabled = _compact(os.getenv("GRANDPA_VOICE_RUNTIME_ENABLED", "")).lower() in {"1", "true", "yes", "on"}
    wake_word = _compact(os.getenv("GRANDPA_WAKE_WORD", "")) or _compact(get_setting("wake_word", "hey grandpa")) or "hey grandpa"
    return {
        "id": "voice_runtime",
        "status": "ok" if enabled else "warning",
        "ready": enabled,
        "detail": "Background voice runtime is enabled." if enabled else "Set GRANDPA_VOICE_RUNTIME_ENABLED=1 to enable background voice runtime.",
        "wake_word": wake_word,
    }


def collect_voice_readiness() -> dict[str, Any]:
    """Return STT/TTS/runtime readiness without starting voice threads."""
    components = [
        _voice_input_status(),
        _pyttsx3_status(),
        _piper_status(),
        _voice_runtime_status(),
    ]
    ready_count = sum(1 for item in components if item.get("ready"))
    warning_count = sum(1 for item in components if item.get("status") == "warning")
    return {
        "ok": ready_count >= 2,
        "ready_count": ready_count,
        "warning_count": warning_count,
        "components": components,
        "summary": f"{ready_count} voice component(s) ready, {warning_count} warning(s).",
    }
