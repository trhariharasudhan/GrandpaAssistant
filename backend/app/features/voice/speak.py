import contextlib
import base64
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import winsound
import importlib.util
from xml.sax.saxutils import escape

import pyttsx3
import win32com.client
from colorama import Fore, Style, init

from utils.config import get_setting, update_setting
from utils.mood_memory import mood_status_payload


init(autoreset=True)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
BACKEND_DATA_DIR = os.path.join(PROJECT_ROOT, "backend", "data")
PIPER_AUDIO_DIR = os.path.join(BACKEND_DATA_DIR, "tts_audio")
PIPER_MODEL_DIR = os.path.join(BACKEND_DATA_DIR, "piper")
PIPER_VOICES_DIR = os.path.join(BACKEND_DATA_DIR, "voices")
CUSTOM_VOICE_DIR = os.path.join(BACKEND_DATA_DIR, "voice_profiles")
COQUI_RUNTIME_DIR = os.path.join(BACKEND_DATA_DIR, "runtime", "coqui")
DEFAULT_TTS_RATE = 170
DEFAULT_TTS_VOLUME = 1.0

_engine = None
_sapi_voice = None
_engine_lock = threading.Lock()
_stream_lock = threading.Lock()
_response_mode = "hybrid"
_mirror_voice_replies = True
_stream_active = False
_last_tts_backend_used = ""
_last_tts_error = ""
_piper_process = None
_coqui_tts = None
_coqui_model_name = ""

SVS_FLAGS_ASYNC = 1
SVS_FPURGE_BEFORE_SPEAK = 2
SVS_FLAGS_IS_XML = 8


def _compact_text(value):
    return " ".join(str(value or "").split()).strip()


def _preferred_language():
    output_language = _compact_text(get_setting("assistant.output_language", "english")).lower()
    if output_language == "english":
        return "en-US"
    try:
        from brain.memory_engine import get_memory

        value = get_memory("personal.assistant.preferred_response_language") or "en-US"
    except ImportError:
        value = "en-US"
    return _compact_text(value) or "en-US"


def _voice_character_style():
    value = _compact_text(get_setting("voice.character_style", "male_deep")).lower() or "male_deep"
    return value if value in {"default", "grandpa", "male_deep"} else "male_deep"


def _custom_voice_model_name():
    return (
        _compact_text(
            get_setting("voice.custom_voice_model_name", "tts_models/multilingual/multi-dataset/xtts_v2")
        )
        or "tts_models/multilingual/multi-dataset/xtts_v2"
    )


def _custom_voice_language():
    return _compact_text(get_setting("voice.custom_voice_language", "en")) or "en"


def _setting_is_truthy(value):
    if isinstance(value, bool):
        return value
    normalized = _compact_text(value).lower()
    return normalized in {"1", "true", "yes", "y", "on"}


def _custom_voice_model_cache_dir(model_name=""):
    parts = [part for part in _compact_text(model_name or _custom_voice_model_name()).split("/") if part]
    if len(parts) != 4:
        return ""
    model_type, lang, dataset, model = parts
    return os.path.join(COQUI_RUNTIME_DIR, model_type, f"{model_type}--{lang}--{dataset}--{model}")


def _custom_voice_tos_path():
    cache_dir = _custom_voice_model_cache_dir()
    if not cache_dir:
        return ""
    return os.path.join(cache_dir, "tos_agreed.txt")


def _custom_voice_model_cached():
    cache_dir = _custom_voice_model_cache_dir()
    if not cache_dir or not os.path.isdir(cache_dir):
        return False
    for _, _, files in os.walk(cache_dir):
        if files:
            return True
    return False


def _custom_voice_tos_agreed():
    if os.environ.get("COQUI_TOS_AGREED") == "1":
        return True
    if _setting_is_truthy(get_setting("voice.custom_voice_tos_agreed", False)):
        return True
    tos_path = _custom_voice_tos_path()
    return bool(tos_path and os.path.exists(tos_path))


def _apply_custom_voice_tos_state(agreed):
    if agreed:
        os.environ["COQUI_TOS_AGREED"] = "1"
        tos_path = _custom_voice_tos_path()
        if tos_path:
            os.makedirs(os.path.dirname(tos_path), exist_ok=True)
            with open(tos_path, "w", encoding="utf-8") as handle:
                handle.write("I have read, understood and agreed to the Terms and Conditions.")
    else:
        os.environ.pop("COQUI_TOS_AGREED", None)
        tos_path = _custom_voice_tos_path()
        if tos_path and os.path.exists(tos_path):
            with contextlib.suppress(OSError):
                os.remove(tos_path)


def _tts_rate():
    try:
        return int(float(get_setting("voice.tts_rate", DEFAULT_TTS_RATE)))
    except Exception:
        return DEFAULT_TTS_RATE


def _emotion_tone_enabled():
    return bool(get_setting("voice.emotion_tone_enabled", True))


def _current_mood_for_voice():
    try:
        return _compact_text(mood_status_payload(limit=1).get("last_mood", "neutral")).lower() or "neutral"
    except Exception:
        return "neutral"


def _emotion_rate_override(emotion):
    emotion = _compact_text(emotion).lower() or "neutral"
    default_overrides = {
        "happy": 185,
        "sad": 145,
        "angry": 150,
    }
    setting_key = {
        "happy": "voice.emotion_rate_happy",
        "sad": "voice.emotion_rate_sad",
        "angry": "voice.emotion_rate_angry",
    }.get(emotion)
    if not setting_key:
        return _tts_rate()
    try:
        return int(float(get_setting(setting_key, default_overrides[emotion])))
    except Exception:
        return default_overrides[emotion]


def _effective_tts_rate(emotion=None):
    base_rate = _tts_rate()
    current_emotion = _compact_text(emotion or _current_mood_for_voice()).lower() or "neutral"
    if not _emotion_tone_enabled():
        return base_rate
    if current_emotion in {"happy", "sad", "angry"}:
        return _emotion_rate_override(current_emotion)
    return base_rate


def _emotion_sapi_adjustment(emotion):
    current_emotion = _compact_text(emotion or _current_mood_for_voice()).lower() or "neutral"
    if current_emotion == "happy":
        return 1, 1
    if current_emotion == "sad":
        return -1, -1
    if current_emotion == "angry":
        return 0, -1
    return 0, 0


def _tts_volume():
    try:
        value = float(get_setting("voice.tts_volume", DEFAULT_TTS_VOLUME))
    except Exception:
        value = DEFAULT_TTS_VOLUME
    return max(0.0, min(2.0, value))


def _configured_tts_backend():
    backend = _compact_text(get_setting("voice.tts_backend", "auto")).lower() or "auto"
    return backend if backend in {"auto", "sapi", "pyttsx3", "piper", "coqui"} else "auto"


def _custom_voice_roots():
    return [
        CUSTOM_VOICE_DIR,
        os.path.join(PIPER_VOICES_DIR, "custom"),
        os.path.join(PROJECT_ROOT, "models", "voice_profiles"),
    ]


def _project_custom_voice_candidates():
    candidates = []
    for root in _custom_voice_roots():
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if not filename.lower().endswith(".wav"):
                    continue
                candidates.append(os.path.join(dirpath, filename))
    return sorted(set(candidates))


def _project_piper_model_candidates():
    roots = [
        PIPER_MODEL_DIR,
        PIPER_VOICES_DIR,
        os.path.join(PROJECT_ROOT, "models", "piper"),
    ]
    candidates = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                lowered = filename.lower()
                if not lowered.endswith(".onnx"):
                    continue
                full_path = os.path.join(dirpath, filename)
                if "\\site-packages\\piper\\tashkeel\\" in full_path.lower():
                    continue
                candidates.append(full_path)
    return sorted(set(candidates))


def _project_piper_roots():
    return [
        PIPER_MODEL_DIR,
        PIPER_VOICES_DIR,
        os.path.join(PROJECT_ROOT, "models", "piper"),
    ]


def available_piper_models():
    models = []
    for model_path in _project_piper_model_candidates():
        config_path = _configured_piper_config_path(model_path)
        try:
            size_bytes = os.path.getsize(model_path)
        except OSError:
            size_bytes = 0
        models.append(
            {
                "name": os.path.basename(model_path),
                "model_path": os.path.abspath(model_path),
                "config_path": os.path.abspath(config_path) if config_path else "",
                "size_mb": round(size_bytes / (1024 * 1024), 1) if size_bytes else 0.0,
                "ready": bool(config_path),
            }
        )
    return models


def choose_piper_model(model_name_or_path):
    query = _compact_text(model_name_or_path)
    if not query:
        return False, "Please provide a Piper model name or full path."

    normalized_query = query.lower()
    for item in available_piper_models():
        model_path = item["model_path"]
        if normalized_query in {
            model_path.lower(),
            os.path.basename(model_path).lower(),
            item["name"].lower(),
        }:
            update_setting("voice.piper_model_path", model_path)
            if item["config_path"]:
                update_setting("voice.piper_config_path", item["config_path"])
            return True, f"Piper is now configured with {item['name']}."

    return False, "I could not find that Piper model in the local voice folders."


def autoconfigure_piper_model():
    models = available_piper_models()
    if not models:
        return False, "No Piper voice models were found yet. Put a .onnx model in backend/data/piper or backend/data/voices."

    chosen = models[0]
    update_setting("voice.piper_model_path", chosen["model_path"])
    if chosen["config_path"]:
        update_setting("voice.piper_config_path", chosen["config_path"])
    return True, f"Piper is now configured with {chosen['name']}."


def piper_setup_payload():
    runtime = _piper_runtime_status()
    models = available_piper_models()
    return {
        "ready": runtime["ready"],
        "binary_ready": runtime["binary_ready"],
        "model_ready": runtime["model_ready"],
        "config_ready": runtime["config_ready"],
        "configured_model_path": runtime["model_path"],
        "configured_config_path": runtime["config_path"],
        "executable": runtime["executable"],
        "available_models": models,
        "recommended_directories": [os.path.abspath(path) for path in _project_piper_roots()],
    }


def piper_setup_status_summary():
    payload = piper_setup_payload()
    if payload["ready"]:
        return f"Piper is ready with model {os.path.basename(payload['configured_model_path'])}."
    if payload["available_models"]:
        names = ", ".join(item["name"] for item in payload["available_models"][:4])
        return (
            f"Piper executable is {'ready' if payload['binary_ready'] else 'missing'}, "
            f"and I found model candidates: {names}. "
            "Say auto configure piper to use the first detected model."
        )
    return (
        f"Piper is not ready yet. Put a voice model in {os.path.abspath(PIPER_MODEL_DIR)} "
        "or backend/data/voices, then say auto configure piper."
    )


def list_piper_models_summary():
    models = available_piper_models()
    if not models:
        return "I could not find any Piper voice models yet."
    return "Available Piper models: " + " | ".join(
        f"{item['name']} ({item['size_mb']} MB)" for item in models[:6]
    )


def choose_piper_model_summary(model_name_or_path):
    return choose_piper_model(model_name_or_path)[1]


def prefer_piper_backend():
    runtime = _piper_runtime_status()
    if runtime["ready"]:
        update_setting("voice.tts_backend", "piper")
        return True, "Piper is now the preferred speech output backend."
    success, message = autoconfigure_piper_model()
    if success:
        update_setting("voice.tts_backend", "piper")
        return True, "Piper is now the preferred speech output backend."
    return False, message


def available_custom_voice_samples():
    samples = []
    for sample_path in _project_custom_voice_candidates():
        try:
            size_bytes = os.path.getsize(sample_path)
        except OSError:
            size_bytes = 0
        samples.append(
            {
                "name": os.path.basename(sample_path),
                "sample_path": os.path.abspath(sample_path),
                "size_mb": round(size_bytes / (1024 * 1024), 2) if size_bytes else 0.0,
            }
        )
    return samples


def choose_custom_voice_sample(sample_name_or_path):
    query = _compact_text(sample_name_or_path)
    if not query:
        return False, "Please provide a reference voice sample path."

    resolved_query = os.path.abspath(query)
    if os.path.exists(resolved_query) and resolved_query.lower().endswith(".wav"):
        update_setting("voice.custom_voice_sample_path", resolved_query)
        return True, f"Your custom voice sample is now set to {resolved_query}."

    normalized_query = query.lower()
    for item in available_custom_voice_samples():
        sample_path = item["sample_path"]
        if normalized_query in {
            sample_path.lower(),
            os.path.basename(sample_path).lower(),
            item["name"].lower(),
        }:
            update_setting("voice.custom_voice_sample_path", sample_path)
            return True, f"Your custom voice sample is now set to {item['name']}."

    return False, "I could not find that custom voice sample in the local voice profile folders."


def set_custom_voice_sample_path(sample_name_or_path):
    return choose_custom_voice_sample(sample_name_or_path)


def clear_custom_voice_sample_path():
    update_setting("voice.custom_voice_sample_path", "")
    return True, "Cleared the saved custom voice sample path."


def autoconfigure_custom_voice_sample():
    samples = available_custom_voice_samples()
    if not samples:
        return False, "No custom voice sample was found yet. Put a clean WAV sample in backend/data/voice_profiles."

    chosen = samples[0]
    update_setting("voice.custom_voice_sample_path", chosen["sample_path"])
    return True, f"Your custom voice sample is now set to {chosen['name']}."


def _configured_custom_voice_sample_path():
    configured = _compact_text(get_setting("voice.custom_voice_sample_path", ""))
    if configured and os.path.exists(configured) and configured.lower().endswith(".wav"):
        return os.path.abspath(configured)

    candidates = _project_custom_voice_candidates()
    if len(candidates) == 1:
        return os.path.abspath(candidates[0])
    return ""


def _coqui_package_available():
    return importlib.util.find_spec("TTS") is not None


def _custom_voice_runtime_status():
    sample_path = _configured_custom_voice_sample_path()
    model_name = _custom_voice_model_name()
    tos_agreed = _custom_voice_tos_agreed()
    return {
        "package_installed": _coqui_package_available(),
        "sample_path": sample_path,
        "sample_ready": bool(sample_path),
        "model_name": model_name,
        "language": _custom_voice_language(),
        "model_cached": _custom_voice_model_cached(),
        "tos_agreed": tos_agreed,
        "license_pending": bool(_coqui_package_available() and sample_path and not tos_agreed),
        "ready": bool(_coqui_package_available() and sample_path and tos_agreed),
    }


def custom_voice_setup_payload():
    runtime = _custom_voice_runtime_status()
    return {
        "ready": runtime["ready"],
        "package_installed": runtime["package_installed"],
        "sample_ready": runtime["sample_ready"],
        "configured_sample_path": runtime["sample_path"],
        "model_name": runtime["model_name"],
        "language": runtime["language"],
        "model_cached": runtime["model_cached"],
        "tos_agreed": runtime["tos_agreed"],
        "license_pending": runtime["license_pending"],
        "available_samples": available_custom_voice_samples(),
        "recommended_directories": [os.path.abspath(path) for path in _custom_voice_roots()],
    }


def custom_voice_status_summary():
    payload = custom_voice_setup_payload()
    if payload["ready"]:
        if payload["model_cached"]:
            return (
                f"Your own voice is ready using {os.path.basename(payload['configured_sample_path'])}. "
                "Say use my voice to make it the preferred speech voice."
            )
        return (
            f"Your own voice is ready using {os.path.basename(payload['configured_sample_path'])}. "
            "The first cloned reply may take a little longer while the local voice model prepares."
        )
    if not payload["package_installed"]:
        return (
            "Your own voice is not ready yet because the Coqui TTS cloning package is not installed. "
            f"After installing it, put a clean WAV sample in {os.path.abspath(CUSTOM_VOICE_DIR)}."
        )
    if payload["sample_ready"] and payload["license_pending"]:
        return (
            f"I found your voice sample {os.path.basename(payload['configured_sample_path'])}, "
            "but I still need your one-time Coqui voice license approval before I can actually speak with your voice. "
            "Say accept my voice license if you want to continue."
        )
    if payload["available_samples"]:
        names = ", ".join(item["name"] for item in payload["available_samples"][:4])
        return (
            f"I found voice sample candidates: {names}. "
            "Say auto configure my voice to use the first detected sample."
        )
    return (
        f"Your own voice is not ready yet. Put a clean WAV sample in {os.path.abspath(CUSTOM_VOICE_DIR)} "
        "and then say auto configure my voice."
    )


def list_custom_voice_samples_summary():
    samples = available_custom_voice_samples()
    if not samples:
        return "I could not find any custom voice samples yet."
    return "Available custom voice samples: " + " | ".join(
        f"{item['name']} ({item['size_mb']} MB)" for item in samples[:6]
    )


def choose_custom_voice_sample_summary(sample_name_or_path):
    return choose_custom_voice_sample(sample_name_or_path)[1]


def prefer_custom_voice_backend():
    runtime = _custom_voice_runtime_status()
    if runtime["ready"]:
        update_setting("voice.tts_backend", "coqui")
        return True, "Your own voice is now the preferred speech output backend."
    success, message = autoconfigure_custom_voice_sample()
    if success and _custom_voice_runtime_status()["ready"]:
        update_setting("voice.tts_backend", "coqui")
        return True, "Your own voice is now the preferred speech output backend."
    pending_runtime = _custom_voice_runtime_status()
    if pending_runtime["sample_ready"] and pending_runtime["license_pending"]:
        return (
            False,
            "I found your voice sample, but I still need your one-time Coqui voice license approval. "
            "Say accept my voice license first.",
        )
    if success:
        return False, custom_voice_status_summary()
    return False, message


def accept_custom_voice_license():
    update_setting("voice.custom_voice_tos_agreed", True)
    _apply_custom_voice_tos_state(True)
    runtime = _custom_voice_runtime_status()
    if runtime["sample_ready"]:
        return True, (
            "Recorded your one-time Coqui voice license approval. "
            "Now say use my voice and I will try your custom voice."
        )
    return True, (
        "Recorded your one-time Coqui voice license approval. "
        "Now add a clean WAV sample and say use my voice."
    )


def custom_voice_license_status_summary():
    runtime = _custom_voice_runtime_status()
    if runtime["tos_agreed"]:
        return "Your one-time Coqui voice license approval is already recorded."
    if runtime["sample_ready"]:
        return (
            "Your voice sample is ready, but the one-time Coqui voice license approval is still pending. "
            "Say accept my voice license to continue."
        )
    return (
        "The one-time Coqui voice license approval is still pending. "
        "After you add a voice sample, say accept my voice license to continue."
    )


def _find_piper_executable():
    candidates = [
        _compact_text(os.getenv("PIPER_PATH", "")),
        os.path.join(PROJECT_ROOT, ".python311", "Scripts", "piper.exe"),
        os.path.join(PROJECT_ROOT, ".venv", "Scripts", "piper.exe"),
        shutil.which("piper.exe") or "",
        shutil.which("piper") or "",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return ""


def _configured_piper_model_path():
    configured = _compact_text(get_setting("voice.piper_model_path", "")) or _compact_text(
        os.getenv("PIPER_MODEL_PATH", "")
    )
    if configured and os.path.exists(configured):
        return os.path.abspath(configured)

    candidates = _project_piper_model_candidates()
    if len(candidates) == 1:
        return os.path.abspath(candidates[0])
    return ""


def _configured_piper_config_path(model_path=""):
    configured = _compact_text(get_setting("voice.piper_config_path", "")) or _compact_text(
        os.getenv("PIPER_CONFIG_PATH", "")
    )
    if configured and os.path.exists(configured):
        return os.path.abspath(configured)

    model_path = model_path or _configured_piper_model_path()
    if not model_path:
        return ""

    sibling_json = model_path + ".json"
    if os.path.exists(sibling_json):
        return os.path.abspath(sibling_json)

    stem, _ = os.path.splitext(model_path)
    alternate_json = stem + ".onnx.json"
    if os.path.exists(alternate_json):
        return os.path.abspath(alternate_json)
    return ""


def _piper_runtime_status():
    executable = _find_piper_executable()
    model_path = _configured_piper_model_path()
    config_path = _configured_piper_config_path(model_path)
    return {
        "executable": executable,
        "model_path": model_path,
        "config_path": config_path,
        "binary_ready": bool(executable),
        "model_ready": bool(model_path),
        "config_ready": bool(config_path),
        "ready": bool(executable and model_path),
    }


def _backend_availability():
    piper = _piper_runtime_status()
    custom_voice = _custom_voice_runtime_status()
    return {
        "coqui": custom_voice["ready"],
        "piper": piper["ready"],
        "sapi": True,
        "pyttsx3": True,
        "custom_voice_status": custom_voice,
        "piper_status": piper,
    }


def _tts_backend_order():
    configured = _configured_tts_backend()
    if configured == "coqui":
        return ["coqui", "sapi", "pyttsx3", "piper"]
    if configured == "piper":
        return ["piper", "sapi", "pyttsx3", "coqui"]
    if configured == "sapi":
        return ["sapi", "pyttsx3", "piper", "coqui"]
    if configured == "pyttsx3":
        return ["pyttsx3", "sapi", "piper", "coqui"]

    availability = _backend_availability()
    if availability["piper"]:
        return ["piper", "sapi", "pyttsx3", "coqui"]
    return ["sapi", "pyttsx3", "piper", "coqui"]


def current_tts_backend():
    return _configured_tts_backend()


def set_tts_backend(backend_name):
    normalized = _compact_text(backend_name).lower()
    if normalized not in {"auto", "sapi", "pyttsx3", "piper", "coqui"}:
        return False
    update_setting("voice.tts_backend", normalized)
    return True


def set_piper_model_path(model_path):
    resolved = os.path.abspath(_compact_text(model_path))
    if not resolved or not os.path.exists(resolved):
        return False, "I could not find that Piper model file."
    if not resolved.lower().endswith(".onnx"):
        return False, "Piper model files should end with .onnx."
    update_setting("voice.piper_model_path", resolved)
    return True, f"Piper model path set to {resolved}."


def clear_piper_model_path():
    update_setting("voice.piper_model_path", "")
    return True, "Cleared the saved Piper model path."


def set_piper_config_path(config_path):
    resolved = os.path.abspath(_compact_text(config_path))
    if not resolved or not os.path.exists(resolved):
        return False, "I could not find that Piper config file."
    if not resolved.lower().endswith(".json"):
        return False, "Piper config files should end with .json."
    update_setting("voice.piper_config_path", resolved)
    return True, f"Piper config path set to {resolved}."


def clear_piper_config_path():
    update_setting("voice.piper_config_path", "")
    return True, "Cleared the saved Piper config path."


def _resolved_tts_backend():
    availability = _backend_availability()
    for backend in _tts_backend_order():
        if availability.get(backend):
            return backend
    return "sapi"


def tts_backend_payload():
    availability = _backend_availability()
    piper = availability["piper_status"]
    custom_voice = availability["custom_voice_status"]
    fallback_order = _tts_backend_order()
    current_mood = _current_mood_for_voice()
    return {
        "configured_backend": _configured_tts_backend(),
        "resolved_backend": _resolved_tts_backend(),
        "fallback_order": fallback_order,
        "rate": _tts_rate(),
        "effective_rate": _effective_tts_rate(current_mood),
        "volume": _tts_volume(),
        "preferred_language": _preferred_language(),
        "emotion_tone_enabled": _emotion_tone_enabled(),
        "current_mood": current_mood,
        "last_backend_used": _last_tts_backend_used or _resolved_tts_backend(),
        "last_error": _last_tts_error,
        "custom_voice": {
            "package_installed": custom_voice["package_installed"],
            "sample_path": custom_voice["sample_path"],
            "sample_ready": custom_voice["sample_ready"],
            "model_name": custom_voice["model_name"],
            "language": custom_voice["language"],
            "model_cached": custom_voice["model_cached"],
            "tos_agreed": custom_voice["tos_agreed"],
            "license_pending": custom_voice["license_pending"],
            "ready": custom_voice["ready"],
            "setup": custom_voice_setup_payload(),
        },
        "piper": {
            "executable": piper["executable"],
            "model_path": piper["model_path"],
            "config_path": piper["config_path"],
            "binary_ready": piper["binary_ready"],
            "model_ready": piper["model_ready"],
            "config_ready": piper["config_ready"],
            "ready": piper["ready"],
            "setup": piper_setup_payload(),
        },
    }


def tts_backend_status_summary():
    payload = tts_backend_payload()
    fallback_order = ", ".join(payload["fallback_order"])
    piper = payload["piper"]
    piper_state = "ready" if piper["ready"] else "not ready"
    custom_voice = payload["custom_voice"]
    if custom_voice["ready"]:
        custom_voice_state = "ready"
    elif custom_voice.get("license_pending"):
        custom_voice_state = "license approval pending"
    else:
        custom_voice_state = "not ready"
    return (
        f"Speech output backend is set to {payload['configured_backend']}. "
        f"Current priority is {payload['resolved_backend']}. "
        f"Fallback order is {fallback_order}. "
        f"Preferred language is {payload['preferred_language']}. "
        f"TTS rate is {payload['rate']}. "
        f"Emotion-aware speech is {'on' if payload['emotion_tone_enabled'] else 'off'}, "
        f"with current mood {payload['current_mood']} and effective rate {payload['effective_rate']}. "
        f"TTS volume is {payload['volume']}. "
        f"Your own voice is {custom_voice_state}. "
        f"Piper is {piper_state}. "
        f"Last successful speech backend was {payload['last_backend_used']}."
    )


def voice_output_status_summary():
    return tts_backend_status_summary()


def _get_sapi_voice():
    global _sapi_voice

    if _sapi_voice is None:
        lang = _preferred_language()
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        lang_base = lang.split("-")[0].lower()
        preferred_description_tokens = []
        if _voice_character_style() == "grandpa":
            preferred_description_tokens = ["david", "male"]
        elif _voice_character_style() == "male_deep":
            preferred_description_tokens = ["david", "male"]

        sapi_voices = voice.GetVoices()
        matching_voices = []
        for index in range(sapi_voices.Count):
            description = sapi_voices.Item(index).GetDescription().lower()
            if lang.lower() in description or lang_base in description:
                matching_voices.append((description, sapi_voices.Item(index)))

        selected_voice = None
        for description, sapi_voice in matching_voices:
            if any(token in description for token in preferred_description_tokens):
                selected_voice = sapi_voice
                break
        if selected_voice is None and matching_voices:
            selected_voice = matching_voices[0][1]
        if selected_voice is not None:
            voice.Voice = selected_voice

        voice.Rate = max(-5, min(5, int(round((_effective_tts_rate() - DEFAULT_TTS_RATE) / 20.0))))
        voice.Volume = max(0, min(100, int(round(_tts_volume() * 100))))
        _sapi_voice = voice

    return _sapi_voice


def _get_engine():
    global _engine

    if _engine is None:
        lang = _preferred_language()
        engine = pyttsx3.init("sapi5")
        voices = engine.getProperty("voices")
        if voices:
            selected_voice = voices[0].id
            lang_base = lang.split("-")[0].lower()
            style = _voice_character_style()
            preferred_name_tokens = ["david", "male"] if style in {"grandpa", "male_deep"} else []
            for voice in voices:
                languages = str(getattr(voice, "languages", "")).lower()
                voice_name = str(getattr(voice, "name", "")).lower()
                if preferred_name_tokens and any(token in voice_name for token in preferred_name_tokens):
                    selected_voice = voice.id
                    break
                if lang.lower() in languages or lang_base in voice_name:
                    selected_voice = voice.id
                    break
            engine.setProperty("voice", selected_voice)

        engine.setProperty("rate", _effective_tts_rate())
        engine.setProperty("volume", min(1.0, _tts_volume()))
        _engine = engine

    return _engine


def _sapi_styled_payload(text, emotion=None):
    style = _voice_character_style()
    pitch_delta, rate_delta = _emotion_sapi_adjustment(emotion)
    if style == "default":
        base_pitch = 0
        base_rate = 0
    elif style == "male_deep":
        base_pitch = -2
        base_rate = -1
    else:
        base_pitch = -4
        base_rate = -2

    final_pitch = max(-6, min(4, base_pitch + pitch_delta))
    final_rate = max(-4, min(3, base_rate + rate_delta))
    if final_pitch == 0 and final_rate == 0:
        return text, SVS_FLAGS_ASYNC | SVS_FPURGE_BEFORE_SPEAK

    safe_text = escape(text)
    xml_text = (
        f"<pitch middle='{final_pitch}'>"
        f"<rate speed='{final_rate}'>"
        f"{safe_text}"
        "</rate>"
        "</pitch>"
    )
    return xml_text, SVS_FLAGS_ASYNC | SVS_FPURGE_BEFORE_SPEAK | SVS_FLAGS_IS_XML


def _speak_with_sapi(text):
    emotion = _current_mood_for_voice()
    voice = _get_sapi_voice()
    voice.Rate = max(-5, min(5, int(round((_effective_tts_rate(emotion) - DEFAULT_TTS_RATE) / 20.0))))
    voice.Volume = max(0, min(100, int(round(_tts_volume() * 100))))
    voice.Speak("", SVS_FLAGS_ASYNC | SVS_FPURGE_BEFORE_SPEAK)
    payload, flags = _sapi_styled_payload(text, emotion=emotion)
    voice.Speak(payload, flags)


def _speak_with_pyttsx3(text):
    emotion = _current_mood_for_voice()
    engine = _get_engine()
    engine.stop()
    engine.setProperty("rate", _effective_tts_rate(emotion))
    engine.setProperty("volume", min(1.0, _tts_volume()))
    engine.say(text)
    engine.runAndWait()


def _piper_command(text, output_file):
    payload = _piper_runtime_status()
    if not payload["ready"]:
        raise RuntimeError("Piper is not ready because the executable or model path is missing.")

    command = [
        payload["executable"],
        "-m",
        payload["model_path"],
        "-f",
        output_file,
        "--volume",
        str(_tts_volume()),
        "--sentence-silence",
        str(float(get_setting("voice.piper_sentence_silence", 0.15) or 0.15)),
    ]
    if payload["config_path"]:
        command.extend(["-c", payload["config_path"]])

    speaker = get_setting("voice.piper_speaker", None)
    if speaker not in {None, ""}:
        try:
            command.extend(["-s", str(int(speaker))])
        except Exception:
            pass

    return command


def _speak_with_piper(text):
    global _piper_process

    os.makedirs(PIPER_AUDIO_DIR, exist_ok=True)
    fd, output_path = tempfile.mkstemp(prefix="piper_", suffix=".wav", dir=PIPER_AUDIO_DIR)
    os.close(fd)
    try:
        command = _piper_command(text, output_path)
        _piper_process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout_text, stderr_text = _piper_process.communicate(text, timeout=120)
        if _piper_process.returncode != 0:
            raise RuntimeError((stderr_text or stdout_text or "Unknown Piper error").strip())
        winsound.PlaySound(output_path, winsound.SND_FILENAME)
    finally:
        _piper_process = None
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass


def _get_coqui_tts():
    global _coqui_tts, _coqui_model_name

    if not _coqui_package_available():
        raise RuntimeError("Coqui TTS is not installed yet.")
    if not _custom_voice_tos_agreed():
        raise RuntimeError(
            "The one-time Coqui voice license approval is still pending. Say accept my voice license first."
        )

    model_name = _custom_voice_model_name()
    if _coqui_tts is not None and _coqui_model_name == model_name:
        return _coqui_tts

    os.makedirs(COQUI_RUNTIME_DIR, exist_ok=True)
    os.environ["TTS_HOME"] = COQUI_RUNTIME_DIR
    os.environ.setdefault("XDG_DATA_HOME", COQUI_RUNTIME_DIR)
    _apply_custom_voice_tos_state(True)

    from TTS.utils import generic_utils as tts_generic_utils

    def _workspace_tts_data_dir(appname):
        base_dir = os.path.abspath(COQUI_RUNTIME_DIR)
        os.makedirs(base_dir, exist_ok=True)
        path = os.path.join(base_dir, str(appname or "tts"))
        os.makedirs(path, exist_ok=True)
        return path

    tts_generic_utils.get_user_data_dir = _workspace_tts_data_dir

    from TTS.api import TTS

    _coqui_tts = TTS(model_name=model_name, progress_bar=False, gpu=False)
    _coqui_model_name = model_name
    return _coqui_tts


def _speak_with_coqui(text):
    runtime = _custom_voice_runtime_status()
    if not runtime["sample_ready"]:
        raise RuntimeError("Your custom voice sample is not configured yet.")

    os.makedirs(PIPER_AUDIO_DIR, exist_ok=True)
    fd, output_path = tempfile.mkstemp(prefix="custom_voice_", suffix=".wav", dir=PIPER_AUDIO_DIR)
    os.close(fd)
    try:
        tts = _get_coqui_tts()
        kwargs = {
            "text": text,
            "file_path": output_path,
            "speaker_wav": runtime["sample_path"],
        }
        language = runtime["language"]
        if language:
            kwargs["language"] = language
        try:
            tts.tts_to_file(**kwargs)
        except TypeError:
            kwargs.pop("language", None)
            tts.tts_to_file(**kwargs)
        winsound.PlaySound(output_path, winsound.SND_FILENAME)
    finally:
        if os.path.exists(output_path):
            with contextlib.suppress(OSError):
                os.remove(output_path)


def _synthesize_with_piper_to_file(text, output_path):
    command = _piper_command(text, output_path)
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout_text, stderr_text = process.communicate(text, timeout=120)
    if process.returncode != 0:
        raise RuntimeError((stderr_text or stdout_text or "Unknown Piper error").strip())
    return output_path


def _synthesize_with_coqui_to_file(text, output_path):
    runtime = _custom_voice_runtime_status()
    if not runtime["sample_ready"]:
        raise RuntimeError("Your custom voice sample is not configured yet.")

    tts = _get_coqui_tts()
    kwargs = {
        "text": text,
        "file_path": output_path,
        "speaker_wav": runtime["sample_path"],
    }
    language = runtime["language"]
    if language:
        kwargs["language"] = language
    try:
        tts.tts_to_file(**kwargs)
    except TypeError:
        kwargs.pop("language", None)
        tts.tts_to_file(**kwargs)
    return output_path


def synthesize_speech_to_file(text, preferred_backend=""):
    clean_text = _compact_text(text)
    if not clean_text:
        raise RuntimeError("Text is required to generate speech audio.")

    os.makedirs(PIPER_AUDIO_DIR, exist_ok=True)
    fd, output_path = tempfile.mkstemp(prefix="mobile_tts_", suffix=".wav", dir=PIPER_AUDIO_DIR)
    os.close(fd)

    backend_candidates = []
    preferred = _compact_text(preferred_backend).lower()
    if preferred in {"coqui", "piper"}:
        backend_candidates.append(preferred)
    for candidate in _tts_backend_order():
        if candidate in {"coqui", "piper"} and candidate not in backend_candidates:
            backend_candidates.append(candidate)

    last_error = "No file-capable speech backend is ready."
    try:
        for backend in backend_candidates:
            try:
                if backend == "coqui" and _backend_availability()["coqui"]:
                    _synthesize_with_coqui_to_file(clean_text, output_path)
                    return output_path, backend
                if backend == "piper" and _backend_availability()["piper"]:
                    _synthesize_with_piper_to_file(clean_text, output_path)
                    return output_path, backend
            except Exception as error:
                last_error = str(error)
        raise RuntimeError(last_error)
    except Exception:
        with contextlib.suppress(OSError):
            os.remove(output_path)
        raise


def synthesize_speech_base64(text, preferred_backend=""):
    output_path, backend = synthesize_speech_to_file(text, preferred_backend=preferred_backend)
    try:
        with open(output_path, "rb") as file:
            encoded = base64.b64encode(file.read()).decode("ascii")
        return {
            "audio_base64": encoded,
            "mime_type": "audio/wav",
            "backend": backend,
        }
    finally:
        with contextlib.suppress(OSError):
            os.remove(output_path)


def _speak_with_backend(backend, text):
    if backend == "coqui":
        _speak_with_coqui(text)
        return
    if backend == "piper":
        _speak_with_piper(text)
        return
    if backend == "sapi":
        _speak_with_sapi(text)
        return
    if backend == "pyttsx3":
        _speak_with_pyttsx3(text)
        return
    raise RuntimeError(f"Unknown TTS backend: {backend}")


def typing_effect(text, delay=0.02):
    sys.stdout.write(Fore.GREEN + "Grandpa: " + Style.RESET_ALL)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def start_streaming_reply():
    global _stream_active
    with _stream_lock:
        if _stream_active:
            return
        _stream_active = True
        sys.stdout.write(Fore.GREEN + "Grandpa: " + Style.RESET_ALL)
        sys.stdout.flush()


def append_streaming_reply(text):
    if not text:
        return

    with _stream_lock:
        if not _stream_active:
            sys.stdout.write(Fore.GREEN + "Grandpa: " + Style.RESET_ALL)
        sys.stdout.write(text)
        sys.stdout.flush()


def end_streaming_reply():
    global _stream_active
    with _stream_lock:
        if _stream_active:
            print()
        _stream_active = False


def set_response_mode(mode):
    global _response_mode
    if mode in {"text", "voice", "hybrid"}:
        _response_mode = mode


def speak(text, already_printed=False):
    global _last_tts_backend_used, _last_tts_error

    text = _compact_text(text)
    if not text:
        return

    with contextlib.suppress(Exception):
        from core.followup_memory import set_last_result

        set_last_result(text)

    with contextlib.suppress(Exception):
        from security.state import append_security_activity

        append_security_activity(
            "assistant_response",
            source="voice.speak",
            message="Assistant response emitted.",
            response=text,
            metadata={"mode": _response_mode},
        )

    should_print = _response_mode in {"text", "hybrid"} or (
        _response_mode == "voice" and _mirror_voice_replies
    )

    if should_print and not already_printed:
        typing_effect(text)

    if _response_mode not in {"voice", "hybrid"}:
        return

    with _engine_lock:
        for backend in _tts_backend_order():
            if backend == "coqui" and not _backend_availability()["coqui"]:
                continue
            if backend == "piper" and not _backend_availability()["piper"]:
                continue
            try:
                _speak_with_backend(backend, text)
                _last_tts_backend_used = backend
                _last_tts_error = ""
                return
            except Exception as error:
                _last_tts_error = str(error)

    print("TTS Error:", _last_tts_error or "No speech backend succeeded.")


def stop_speaking():
    global _engine, _sapi_voice, _piper_process

    try:
        with _engine_lock:
            if _piper_process is not None and _piper_process.poll() is None:
                _piper_process.terminate()
                _piper_process = None

            winsound.PlaySound(None, 0)

            if _sapi_voice is not None:
                _sapi_voice.Speak("", SVS_FLAGS_ASYNC | SVS_FPURGE_BEFORE_SPEAK)

            if _engine is not None:
                _engine.stop()
    except Exception as error:
        print("TTS Stop Error:", error)
