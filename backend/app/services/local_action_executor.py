from __future__ import annotations

import datetime
import contextlib
import json
import os
import re
import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from utils.paths import artifacts_path, logs_path, runtime_path
except ImportError:
    from backend.app.shared.utils.paths import artifacts_path, logs_path, runtime_path


AUDIT_LOG_PATH = logs_path("local_actions.jsonl")
SHELL_INJECTION_PATTERN = re.compile(r"[;&|`$<>]|(\r|\n)|(\.\.[\\/])")
ALLOWED_APPS = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "calc": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "mspaint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
}
SUPPORTED_ACTIONS = {
    "open_app",
    "open_url",
    "take_screenshot",
    "adjust_volume",
    "close_app",
    "media_key",
    "create_folder",
    "copy_file",
    "move_file",
    "start_obs_recording",
    "stop_obs_recording",
}
ALLOWED_CLOSE_PROCESSES = {
    "calculator": ["calc.exe", "calculatorapp.exe"],
    "calc": ["calc.exe", "calculatorapp.exe"],
    "notepad": ["notepad.exe"],
    "paint": ["mspaint.exe"],
    "mspaint": ["mspaint.exe"],
}
UNSAVED_WORK_APPS = {"notepad", "paint", "mspaint"}
DEFAULT_SAFE_ROOTS = [
    str(Path.home() / "Desktop"),
    str(Path.home() / "Documents"),
    str(Path.home() / "Downloads"),
    runtime_path(),
]
SAFE_ROOTS = [
    os.path.abspath(os.path.expanduser(path))
    for path in os.getenv("LOCAL_ACTION_SAFE_ROOTS", os.pathsep.join(DEFAULT_SAFE_ROOTS)).split(os.pathsep)
    if str(path or "").strip()
]


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _response(ok: bool, action: str, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"ok": bool(ok), "action": action, "message": message, "data": data or {}}


def _redact_for_audit(value: Any) -> Any:
    text = str(value or "")
    text = re.sub(r"(?i)(password|token|secret|credential|api[_-]?key)=?[^\s,;]+", r"\1=[REDACTED]", text)
    if len(text) > 500:
        return text[:500] + "...[truncated]"
    return text


def append_local_action_audit(event: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    record = {
        "timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        **{key: _redact_for_audit(value) for key, value in event.items()},
    }
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def _has_dangerous_text(value: Any) -> bool:
    return bool(SHELL_INJECTION_PATTERN.search(str(value or "")))


def _safe_path(value: Any, *, must_exist: bool = False) -> str:
    raw = _compact_text(value)
    if not raw:
        raise ValueError("Path is required.")
    if _has_dangerous_text(raw):
        raise ValueError("Path contains unsafe characters.")
    resolved = os.path.abspath(os.path.expanduser(raw))
    allowed = False
    for root in SAFE_ROOTS:
        if not root:
            continue
        with contextlib.suppress(ValueError):
            if os.path.commonpath([resolved, root]) == root:
                allowed = True
                break
    if not allowed:
        raise ValueError("Path is outside the allowed local action folders.")
    if must_exist and not os.path.exists(resolved):
        raise ValueError("Path does not exist.")
    return resolved


def _validate_action_payload(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("Action request must be a JSON object.")
    action = _compact_text(payload.get("action")).lower()
    params = payload.get("params") or {}
    if action not in SUPPORTED_ACTIONS:
        raise ValueError("Unsupported local action.")
    if not isinstance(params, dict):
        raise ValueError("Action params must be an object.")
    for value in params.values():
        if isinstance(value, str) and _has_dangerous_text(value):
            raise ValueError("Action params contain unsafe characters.")
    return action, params


def _handle_open_app(action: str, params: dict[str, Any]) -> dict[str, Any]:
    app = _compact_text(params.get("app")).lower()
    if not app:
        return _response(False, action, "App name is required.")
    command = ALLOWED_APPS.get(app)
    if not command:
        return _response(False, action, "App is not allowlisted for local automation.")
    process = subprocess.Popen(command, shell=False)
    return _response(True, action, f"Opened {app}.", {"app": app, "pid": process.pid})


def _handle_open_url(action: str, params: dict[str, Any]) -> dict[str, Any]:
    url = _compact_text(params.get("url"))
    if not url:
        return _response(False, action, "URL is required.")
    if _has_dangerous_text(url):
        return _response(False, action, "URL contains unsafe characters.")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return _response(False, action, "Only http and https URLs are allowed.")
    opened = bool(webbrowser.open(url, new=2))
    return _response(opened, action, "Opened URL." if opened else "Could not open URL.", {"url": url})


def _handle_take_screenshot(action: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        import pyautogui  # type: ignore
    except Exception as error:
        return _response(False, action, "Screenshot support is not available.", {"error": str(error)})
    output_dir = artifacts_path("local_actions", "screenshots")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    output_path = os.path.join(output_dir, filename)
    pyautogui.screenshot(output_path)
    return _response(True, action, "Screenshot captured.", {"path": output_path})


def _fallback_media_key(key_name: str, repeats: int = 1) -> bool:
    try:
        import pyautogui  # type: ignore
    except Exception:
        return False
    try:
        for _ in range(max(1, int(repeats))):
            pyautogui.press(key_name)
        return True
    except Exception:
        return False


def _get_volume_interface():
    try:
        from ctypes import POINTER, cast

        from comtypes import CLSCTX_ALL  # type: ignore
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception:
        return None


def _handle_adjust_volume(action: str, params: dict[str, Any]) -> dict[str, Any]:
    operation = _compact_text(params.get("operation")).lower()
    step = int(params.get("step") or 10)
    if operation not in {"increase", "decrease", "mute", "unmute"}:
        return _response(False, action, "Volume operation must be increase, decrease, mute, or unmute.")

    volume = _get_volume_interface()
    try:
        if volume is not None:
            if operation == "increase":
                current = float(volume.GetMasterVolumeLevelScalar())
                volume.SetMasterVolumeLevelScalar(min(current + (step / 100), 1.0), None)
                return _response(True, action, "Increased the system volume.", {"operation": operation})
            if operation == "decrease":
                current = float(volume.GetMasterVolumeLevelScalar())
                volume.SetMasterVolumeLevelScalar(max(current - (step / 100), 0.0), None)
                return _response(True, action, "Reduced the system volume.", {"operation": operation})
            if operation == "mute":
                volume.SetMute(1, None)
                return _response(True, action, "Muted the system volume.", {"operation": operation})
            volume.SetMute(0, None)
            return _response(True, action, "Unmuted the system volume.", {"operation": operation})
    except Exception as error:
        return _response(False, action, f"Windows volume control failed: {_compact_text(error)}", {"operation": operation})

    fallback_keys = {
        "increase": ("volumeup", 4, "Increased the system volume."),
        "decrease": ("volumedown", 4, "Reduced the system volume."),
        "mute": ("volumemute", 1, "Muted the system volume."),
        "unmute": ("volumeup", 1, "Unmuted the system volume."),
    }
    key_name, repeats, message = fallback_keys[operation]
    if _fallback_media_key(key_name, repeats=repeats):
        return _response(True, action, message, {"operation": operation, "fallback": "media_key"})
    return _response(False, action, "Windows volume control failed: pycaw/comtypes and pyautogui media-key fallback are unavailable.", {"operation": operation})


def _handle_close_app(action: str, params: dict[str, Any]) -> dict[str, Any]:
    app = _compact_text(params.get("app")).lower()
    assistant_tracked = bool(params.get("assistant_tracked"))
    if not app:
        return _response(False, action, "App name is required.")
    if not assistant_tracked:
        return _response(False, action, "I can only close apps that I opened or tracked in this conversation.", {"app": app})
    process_names = ALLOWED_CLOSE_PROCESSES.get(app)
    if not process_names:
        return _response(False, action, f"I understood you want to close {app}, but it is not in the safe close-app allowlist.", {"app": app})
    pid = params.get("pid")
    try:
        pid = int(pid) if pid not in {None, ""} else None
    except (TypeError, ValueError):
        pid = None
    if pid is None:
        return _response(False, action, f"I know you mean {app}, but I do not have the exact assistant-tracked process id to close safely.", {"app": app})

    try:
        import psutil  # type: ignore
    except Exception as error:
        return _response(False, action, f"Close-app adapter failed: psutil is not available ({_compact_text(error)}).", {"app": app})

    allowed_names = {name.lower() for name in process_names}
    try:
        process = psutil.Process(pid)
        name = _compact_text(process.name()).lower()
        if name not in allowed_names:
            return _response(False, action, f"The tracked process for {app} no longer matches the safe close allowlist.", {"app": app, "pid": pid, "process_name": name})
        process.terminate()
        try:
            process.wait(timeout=2)
        except Exception:
            process.kill()
        return _response(True, action, f"Closed {app}.", {"app": app, "pid": pid})
    except Exception as error:
        return _response(False, action, f"I could not close the tracked {app} process safely: {_compact_text(error)}", {"app": app, "pid": pid})


def _handle_media_key(action: str, params: dict[str, Any]) -> dict[str, Any]:
    operation = _compact_text(params.get("operation")).lower()
    key_map = {
        "play_pause": ("playpause", "Toggled media playback."),
        "pause": ("playpause", "Paused or resumed media playback."),
        "play": ("playpause", "Paused or resumed media playback."),
        "next": ("nexttrack", "Skipped to the next media item."),
        "previous": ("prevtrack", "Returned to the previous media item."),
    }
    key_info = key_map.get(operation)
    if not key_info:
        return _response(False, action, "Media operation must be play, pause, play_pause, next, or previous.")
    key_name, message = key_info
    if _fallback_media_key(key_name, repeats=1):
        return _response(True, action, message, {"operation": operation})
    return _response(False, action, "Media key control failed: pyautogui media-key fallback is unavailable.", {"operation": operation})


def _handle_create_folder(action: str, params: dict[str, Any]) -> dict[str, Any]:
    path = _safe_path(params.get("path"))
    os.makedirs(path, exist_ok=True)
    return _response(True, action, "Folder is ready.", {"path": path})


def _handle_copy_file(action: str, params: dict[str, Any]) -> dict[str, Any]:
    source = _safe_path(params.get("source"), must_exist=True)
    destination = _safe_path(params.get("destination"))
    if not os.path.isfile(source):
        return _response(False, action, "Source must be a file.")
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    shutil.copy2(source, destination)
    return _response(True, action, "File copied.", {"source": source, "destination": destination})


def _handle_move_file(action: str, params: dict[str, Any]) -> dict[str, Any]:
    source = _safe_path(params.get("source"), must_exist=True)
    destination = _safe_path(params.get("destination"))
    if not os.path.isfile(source):
        return _response(False, action, "Source must be a file.")
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    shutil.move(source, destination)
    return _response(True, action, "File moved.", {"source": source, "destination": destination})


def _handle_obs_placeholder(action: str, params: dict[str, Any]) -> dict[str, Any]:
    return _response(
        True,
        action,
        "OBS recording action acknowledged. OBS control is a safe placeholder until an authenticated OBS integration is configured.",
        {"placeholder": True},
    )


ACTION_HANDLERS = {
    "open_app": _handle_open_app,
    "open_url": _handle_open_url,
    "take_screenshot": _handle_take_screenshot,
    "adjust_volume": _handle_adjust_volume,
    "close_app": _handle_close_app,
    "media_key": _handle_media_key,
    "create_folder": _handle_create_folder,
    "copy_file": _handle_copy_file,
    "move_file": _handle_move_file,
    "start_obs_recording": _handle_obs_placeholder,
    "stop_obs_recording": _handle_obs_placeholder,
}


def execute_local_action(payload: dict[str, Any]) -> dict[str, Any]:
    action = _compact_text((payload or {}).get("action")).lower()
    try:
        action, params = _validate_action_payload(payload)
        result = ACTION_HANDLERS[action](action, params)
    except Exception as error:
        result = _response(False, action or "unknown", str(error))
    append_local_action_audit(
        {
            "action": result.get("action"),
            "ok": result.get("ok"),
            "message": result.get("message"),
        }
    )
    return result
