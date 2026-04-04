import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import winsound

import pyttsx3
import win32com.client
from colorama import Fore, Style, init

from utils.config import get_setting, update_setting


init(autoreset=True)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
BACKEND_DATA_DIR = os.path.join(PROJECT_ROOT, "backend", "data")
PIPER_AUDIO_DIR = os.path.join(BACKEND_DATA_DIR, "tts_audio")
PIPER_MODEL_DIR = os.path.join(BACKEND_DATA_DIR, "piper")
PIPER_VOICES_DIR = os.path.join(BACKEND_DATA_DIR, "voices")
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

SVS_FLAGS_ASYNC = 1
SVS_FPURGE_BEFORE_SPEAK = 2


def _compact_text(value):
    return " ".join(str(value or "").split()).strip()


def _preferred_language():
    try:
        from brain.memory_engine import get_memory

        value = get_memory("personal.assistant.preferred_response_language") or "en-US"
    except ImportError:
        value = "en-US"
    return _compact_text(value) or "en-US"


def _tts_rate():
    try:
        return int(float(get_setting("voice.tts_rate", DEFAULT_TTS_RATE)))
    except Exception:
        return DEFAULT_TTS_RATE


def _tts_volume():
    try:
        value = float(get_setting("voice.tts_volume", DEFAULT_TTS_VOLUME))
    except Exception:
        value = DEFAULT_TTS_VOLUME
    return max(0.0, min(2.0, value))


def _configured_tts_backend():
    backend = _compact_text(get_setting("voice.tts_backend", "auto")).lower() or "auto"
    return backend if backend in {"auto", "sapi", "pyttsx3", "piper"} else "auto"


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


def autoconfigure_piper_model():
    models = available_piper_models()
    if not models:
        return False, "No Piper voice models were found yet. Put a .onnx model in backend/data/piper or backend/data/voices."

    chosen = models[0]
    update_setting("voice.piper_model_path", chosen["model_path"])
    if chosen["config_path"]:
        update_setting("voice.piper_config_path", chosen["config_path"])
    if _find_piper_executable():
        update_setting("voice.tts_backend", "piper")
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
    return {
        "piper": piper["ready"],
        "sapi": True,
        "pyttsx3": True,
        "piper_status": piper,
    }


def _tts_backend_order():
    configured = _configured_tts_backend()
    if configured == "piper":
        return ["piper", "sapi", "pyttsx3"]
    if configured == "sapi":
        return ["sapi", "pyttsx3", "piper"]
    if configured == "pyttsx3":
        return ["pyttsx3", "sapi", "piper"]

    availability = _backend_availability()
    if availability["piper"]:
        return ["piper", "sapi", "pyttsx3"]
    return ["sapi", "pyttsx3", "piper"]


def current_tts_backend():
    return _configured_tts_backend()


def set_tts_backend(backend_name):
    normalized = _compact_text(backend_name).lower()
    if normalized not in {"auto", "sapi", "pyttsx3", "piper"}:
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
    fallback_order = _tts_backend_order()
    return {
        "configured_backend": _configured_tts_backend(),
        "resolved_backend": _resolved_tts_backend(),
        "fallback_order": fallback_order,
        "rate": _tts_rate(),
        "volume": _tts_volume(),
        "preferred_language": _preferred_language(),
        "last_backend_used": _last_tts_backend_used or _resolved_tts_backend(),
        "last_error": _last_tts_error,
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
    return (
        f"Speech output backend is set to {payload['configured_backend']}. "
        f"Current priority is {payload['resolved_backend']}. "
        f"Fallback order is {fallback_order}. "
        f"Preferred language is {payload['preferred_language']}. "
        f"TTS rate is {payload['rate']}. "
        f"TTS volume is {payload['volume']}. "
        f"Piper is {piper_state}."
    )


def voice_output_status_summary():
    return tts_backend_status_summary()


def _get_sapi_voice():
    global _sapi_voice

    if _sapi_voice is None:
        lang = _preferred_language()
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        lang_base = lang.split("-")[0].lower()

        sapi_voices = voice.GetVoices()
        for index in range(sapi_voices.Count):
            description = sapi_voices.Item(index).GetDescription().lower()
            if lang.lower() in description or lang_base in description:
                voice.Voice = sapi_voices.Item(index)
                break

        voice.Rate = max(-5, min(5, int(round((_tts_rate() - DEFAULT_TTS_RATE) / 20.0))))
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
            for voice in voices:
                languages = str(getattr(voice, "languages", "")).lower()
                voice_name = str(getattr(voice, "name", "")).lower()
                if lang.lower() in languages or lang_base in voice_name:
                    selected_voice = voice.id
                    break
            engine.setProperty("voice", selected_voice)

        engine.setProperty("rate", _tts_rate())
        engine.setProperty("volume", min(1.0, _tts_volume()))
        _engine = engine

    return _engine


def _speak_with_sapi(text):
    voice = _get_sapi_voice()
    voice.Speak("", SVS_FLAGS_ASYNC | SVS_FPURGE_BEFORE_SPEAK)
    voice.Speak(text)


def _speak_with_pyttsx3(text):
    engine = _get_engine()
    engine.stop()
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


def _speak_with_backend(backend, text):
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

    should_print = _response_mode in {"text", "hybrid"} or (
        _response_mode == "voice" and _mirror_voice_replies
    )

    if should_print and not already_printed:
        typing_effect(text)

    if _response_mode not in {"voice", "hybrid"}:
        return

    with _engine_lock:
        for backend in _tts_backend_order():
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
