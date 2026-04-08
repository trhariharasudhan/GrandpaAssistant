import copy
import datetime
import importlib.util
import os
import shutil
import sys
import time
from typing import Any

import requests

from iot_registry import summarize_iot_config
from utils.config import get_last_settings_validation, get_setting, load_settings
from utils.paths import config_path, data_path, logs_path, project_path


PROJECT_ROOT = project_path()
BACKEND_DATA_DIR = data_path()
BACKEND_LOG_DIR = logs_path()
DEFAULT_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
DEFAULT_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
REQUIRED_MODELS = {
    "general": os.getenv("OLLAMA_GENERAL_MODEL", "mistral:7b"),
    "fast": os.getenv("OLLAMA_FAST_MODEL", "phi3:mini"),
    "coding": os.getenv("OLLAMA_CODING_MODEL", "deepseek-coder:6.7b"),
}
OPTIONAL_MODULES = {
    "cv2": "OpenCV",
    "pytesseract": "pytesseract",
    "speech_recognition": "SpeechRecognition",
    "pyaudio": "PyAudio",
    "sounddevice": "sounddevice",
    "whisper": "Whisper",
    "sentence_transformers": "sentence-transformers",
    "faiss": "faiss-cpu",
    "fasttext": "fastText",
    "vaderSentiment": "vaderSentiment",
    "transformers": "transformers",
    "paho.mqtt.client": "paho-mqtt",
    "pyudev": "pyudev",
    "wmi": "WMI",
}
_CACHE_TTL_SECONDS = 5.0
_CACHE = {
    "checked_at": 0.0,
    "payload": None,
}


def _item(key: str, status: str, title: str, detail: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "key": key,
        "status": status,
        "title": title,
        "detail": detail,
    }
    payload.update(extra)
    return payload


def _module_is_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, AttributeError, ValueError):
        return False


def _existing_python_runtime() -> tuple[bool, str]:
    candidates = [
        os.path.join(PROJECT_ROOT, ".python311", "python.exe"),
        os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe"),
        sys.executable,
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return True, candidate
    return False, "No local Python runtime found in .python311, .venv, or sys.executable."


def _data_dir_status(allow_create_dirs: bool) -> tuple[str, str]:
    if os.path.isdir(BACKEND_DATA_DIR):
        if os.access(BACKEND_DATA_DIR, os.W_OK):
            return "ok", f"Runtime data directory is writable at {BACKEND_DATA_DIR}."
        return "warning", f"Runtime data directory exists but is not writable: {BACKEND_DATA_DIR}."

    if allow_create_dirs:
        try:
            os.makedirs(BACKEND_DATA_DIR, exist_ok=True)
            return "ok", f"Runtime data directory created at {BACKEND_DATA_DIR}."
        except OSError as error:
            return "error", f"Could not create runtime data directory: {error}"

    return "warning", f"Runtime data directory is missing: {BACKEND_DATA_DIR}."


def _log_dir_status(allow_create_dirs: bool) -> tuple[str, str]:
    if os.path.isdir(BACKEND_LOG_DIR):
        if os.access(BACKEND_LOG_DIR, os.W_OK):
            return "ok", f"Backend log directory is writable at {BACKEND_LOG_DIR}."
        return "warning", f"Backend log directory exists but is not writable: {BACKEND_LOG_DIR}."

    if allow_create_dirs:
        try:
            os.makedirs(BACKEND_LOG_DIR, exist_ok=True)
            return "ok", f"Backend log directory created at {BACKEND_LOG_DIR}."
        except OSError as error:
            return "error", f"Could not create backend log directory: {error}"

    return "warning", f"Backend log directory is missing: {BACKEND_LOG_DIR}."


def _settings_status() -> dict[str, Any]:
    load_settings()
    validation = get_last_settings_validation()
    warnings = list(validation.get("warnings", []))
    corrected_paths = list(validation.get("corrected_paths", []))
    unknown_paths = list(validation.get("unknown_paths", []))
    restored_defaults = bool(validation.get("restored_defaults", False))

    if restored_defaults:
        detail = warnings[0] if warnings else "Settings were restored to defaults."
        return _item(
            "settings_config",
            "warning",
            "Settings Validation",
            detail,
            warnings=warnings,
            corrected_paths=corrected_paths,
            unknown_paths=unknown_paths,
        )

    if warnings:
        detail_parts = []
        if corrected_paths:
            detail_parts.append(f"{len(corrected_paths)} setting value(s) were auto-corrected")
        if unknown_paths:
            detail_parts.append(f"{len(unknown_paths)} custom setting path(s) were preserved")
        detail = ". ".join(detail_parts) + "."
        return _item(
            "settings_config",
            "warning",
            "Settings Validation",
            detail,
            warnings=warnings,
            corrected_paths=corrected_paths,
            unknown_paths=unknown_paths,
        )

    return _item(
        "settings_config",
        "ok",
        "Settings Validation",
        "settings.json matches the expected assistant configuration schema.",
        warnings=[],
        corrected_paths=[],
        unknown_paths=[],
    )


def _ollama_status() -> tuple[dict[str, Any], list[str]]:
    endpoint = f"{DEFAULT_OLLAMA_BASE_URL}/api/tags"
    try:
        response = requests.get(endpoint, timeout=3)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.ConnectionError:
        return (
            _item(
                "ollama_api",
                "error",
                "Ollama API",
                f"Ollama is not responding at {endpoint}. Start 'ollama serve' or the Ollama desktop app.",
            ),
            [],
        )
    except requests.RequestException as error:
        return (
            _item(
                "ollama_api",
                "error",
                "Ollama API",
                f"Could not query Ollama at {endpoint}: {error}",
            ),
            [],
        )

    models = payload.get("models", [])
    names = []
    for model in models:
        if not isinstance(model, dict):
            continue
        name = str(model.get("model") or model.get("name") or "").strip()
        if name:
            names.append(name)

    return (
        _item(
            "ollama_api",
            "ok",
            "Ollama API",
            f"Ollama is reachable at {endpoint} with {len(names)} installed model(s).",
            installed_models=names,
        ),
        names,
    )


def _ollama_model_status(installed_models: list[str]) -> dict[str, Any]:
    if not installed_models:
        return _item(
            "ollama_models",
            "warning",
            "Required Ollama Models",
            "Model check skipped because the Ollama API is not available.",
            required_models=REQUIRED_MODELS,
            missing_models=list(REQUIRED_MODELS.values()),
        )

    missing = [model for model in REQUIRED_MODELS.values() if model not in installed_models]
    if missing:
        return _item(
            "ollama_models",
            "error",
            "Required Ollama Models",
            "Missing required local models: " + ", ".join(missing),
            required_models=REQUIRED_MODELS,
            missing_models=missing,
        )

    return _item(
        "ollama_models",
        "ok",
        "Required Ollama Models",
        "General, fast, and coding Ollama models are installed.",
        required_models=REQUIRED_MODELS,
        missing_models=[],
    )


def _tesseract_status() -> dict[str, Any]:
    candidates = []
    env_path = os.getenv("TESSERACT_PATH", "").strip()
    if env_path:
        candidates.append(env_path)
    candidates.append(DEFAULT_TESSERACT_PATH)
    which_path = shutil.which("tesseract")
    if which_path:
        candidates.append(which_path)

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return _item(
                "tesseract",
                "ok",
                "Tesseract OCR",
                f"Tesseract OCR is available at {candidate}.",
                path=candidate,
            )

    return _item(
        "tesseract",
        "warning",
        "Tesseract OCR",
        "Tesseract OCR was not found in the default Windows path or PATH.",
        path="",
    )


def _module_status() -> dict[str, Any]:
    optional_modules = dict(OPTIONAL_MODULES)
    if os.name == "nt":
        optional_modules.pop("pyudev", None)
    else:
        optional_modules.pop("wmi", None)

    missing = []
    available = []
    for module_name, label in optional_modules.items():
        if not _module_is_available(module_name):
            missing.append(label)
        else:
            available.append(label)

    if missing:
        return _item(
            "python_modules",
            "warning",
            "Assistant Python Modules",
            "Missing optional modules: " + ", ".join(missing),
            missing_modules=missing,
            available_modules=available,
        )

    return _item(
        "python_modules",
        "ok",
        "Assistant Python Modules",
        "Core assistant Python modules are available for AI, OCR, voice, and memory features.",
        missing_modules=[],
        available_modules=available,
    )


def _launcher_status() -> dict[str, Any]:
    scripts = {
        "admin_launcher": os.path.join(PROJECT_ROOT, "scripts", "windows", "start_assistant_admin.cmd"),
        "offline_setup": os.path.join(PROJECT_ROOT, "scripts", "windows", "setup_offline_ai_stack.ps1"),
    }
    missing = [label for label, path in scripts.items() if not os.path.exists(path)]
    if missing:
        return _item(
            "launchers",
            "warning",
            "Windows Launchers",
            "Missing helper scripts: " + ", ".join(missing),
            missing_scripts=missing,
        )

    return _item(
        "launchers",
        "ok",
        "Windows Launchers",
        "Admin launcher and offline setup scripts are available.",
        missing_scripts=[],
    )


def _iot_config_status() -> dict[str, Any]:
    status = summarize_iot_config()
    if not status.get("configured"):
        return _item(
            "iot_config",
            "warning",
            "Smart Home Config",
            f"IoT control config is not set up yet. Add {config_path('iot_credentials.json')} to enable local smart-home control.",
            configured=False,
            enabled=False,
            command_count=0,
        )

    if status.get("placeholder_count"):
        return _item(
            "iot_config",
            "warning",
            "Smart Home Config",
            status.get("summary", "Smart Home config has placeholder commands."),
            configured=True,
            enabled=bool(status.get("enabled")),
            command_count=int(status.get("command_count") or 0),
        )

    return _item(
        "iot_config",
        "ok" if status.get("enabled") else "warning",
        "Smart Home Config",
        status.get("summary", "Smart Home config is available."),
        configured=True,
        enabled=bool(status.get("enabled")),
        command_count=int(status.get("command_count") or 0),
    )


def _piper_status() -> dict[str, Any]:
    candidates = [
        str(os.getenv("PIPER_PATH", "")).strip(),
        os.path.join(PROJECT_ROOT, ".python311", "Scripts", "piper.exe"),
        os.path.join(PROJECT_ROOT, ".venv", "Scripts", "piper.exe"),
        shutil.which("piper.exe") or "",
        shutil.which("piper") or "",
    ]
    executable = ""
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            executable = candidate
            break

    model_path = str(os.getenv("PIPER_MODEL_PATH", "")).strip() or str(get_setting("voice.piper_model_path", "")).strip()
    config_path = str(os.getenv("PIPER_CONFIG_PATH", "")).strip() or str(get_setting("voice.piper_config_path", "")).strip()

    if not executable:
        return _item(
            "piper_tts",
            "warning",
            "Piper TTS",
            "Piper executable was not found yet.",
            executable="",
            model_path=model_path,
            config_path=config_path,
        )

    if model_path and not os.path.exists(model_path):
        return _item(
            "piper_tts",
            "warning",
            "Piper TTS",
            f"Piper executable is ready, but the configured voice model is missing: {model_path}",
            executable=executable,
            model_path=model_path,
            config_path=config_path,
        )

    if not model_path:
        return _item(
            "piper_tts",
            "warning",
            "Piper TTS",
            "Piper executable is ready, but no voice model is configured yet.",
            executable=executable,
            model_path="",
            config_path=config_path,
        )

    return _item(
        "piper_tts",
        "ok",
        "Piper TTS",
        f"Piper is ready with voice model {model_path}.",
        executable=executable,
        model_path=model_path,
        config_path=config_path if os.path.exists(config_path) else "",
    )


def collect_startup_diagnostics(*, use_cache: bool = True, allow_create_dirs: bool = False) -> dict[str, Any]:
    now = time.time()
    if use_cache and _CACHE["payload"] and now - _CACHE["checked_at"] <= _CACHE_TTL_SECONDS:
        return copy.deepcopy(_CACHE["payload"])

    items = []

    python_ok, python_detail = _existing_python_runtime()
    items.append(
        _item(
            "python_runtime",
            "ok" if python_ok else "error",
            "Python Runtime",
            python_detail,
        )
    )

    data_status, data_detail = _data_dir_status(allow_create_dirs=allow_create_dirs)
    items.append(_item("data_dir", data_status, "Runtime Data Directory", data_detail))
    log_status, log_detail = _log_dir_status(allow_create_dirs=allow_create_dirs)
    items.append(_item("log_dir", log_status, "Backend Log Directory", log_detail))
    items.append(_settings_status())

    ollama_item, installed_models = _ollama_status()
    items.append(ollama_item)
    items.append(_ollama_model_status(installed_models))
    items.append(_tesseract_status())
    items.append(_module_status())
    items.append(_iot_config_status())
    items.append(_piper_status())
    items.append(_launcher_status())

    counts = {
        "ok": sum(1 for item in items if item["status"] == "ok"),
        "warning": sum(1 for item in items if item["status"] == "warning"),
        "error": sum(1 for item in items if item["status"] == "error"),
    }
    summary = (
        f"{counts['ok']} ready, {counts['warning']} warning, {counts['error']} error."
    )
    payload = {
        "ok": counts["error"] == 0,
        "checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "counts": counts,
        "items": items,
    }

    _CACHE["checked_at"] = now
    _CACHE["payload"] = payload
    return copy.deepcopy(payload)


def format_startup_diagnostics_report(
    diagnostics: dict[str, Any],
    *,
    include_ready: bool = False,
) -> list[str]:
    lines = [f"Startup doctor: {diagnostics.get('summary', 'No summary available.')}"]
    for item in diagnostics.get("items", []):
        if not include_ready and item.get("status") == "ok":
            continue
        prefix = {
            "ok": "[OK]",
            "warning": "[WARN]",
            "error": "[ERR]",
        }.get(item.get("status"), "[INFO]")
        lines.append(f"{prefix} {item.get('title', 'Check')}: {item.get('detail', '')}")
    return lines
