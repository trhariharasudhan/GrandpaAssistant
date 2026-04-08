from __future__ import annotations

import copy
import json
import os
import socket
import threading
import time
import uuid
import atexit
from typing import Any, Callable

from utils.paths import backend_data_dir, backend_data_path

DATA_DIR = backend_data_dir()
STATE_PATH = backend_data_path("cognition_state.json")
_LOCK = threading.RLock()
_CACHE: dict[str, Any] | None = None
_SAVE_TIMER: threading.Timer | None = None
_SAVE_DELAY_SECONDS = 0.35


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _build_device_id() -> str:
    host = "".join(char for char in socket.gethostname().lower() if char.isalnum()) or "device"
    return f"{host}-{uuid.uuid4().hex[:8]}"


def _default_state() -> dict[str, Any]:
    return {
        "learning": {
            "interactions": [],
            "strategy_scores": {},
            "feedback_count": 0,
            "positive_feedback": 0,
            "negative_feedback": 0,
            "best_responses": [],
            "failed_responses": [],
            "user_preferences": {
                "scores": {},
                "last_updated_at": "",
            },
            "behavior_profile": {
                "active_windows": {},
                "contexts": {},
                "routes": {},
                "models": {},
                "topics": {},
                "response_lengths": {},
                "last_updated_at": "",
            },
            "last_updated_at": "",
        },
        "workflows": {
            "custom_workflows": [],
            "run_history": [],
        },
        "recovery": {
            "errors": [],
            "fingerprints": {},
            "last_updated_at": "",
        },
        "sync": {
            "enabled": False,
            "api_base_url": "",
            "device_id": _build_device_id(),
            "last_exported_at": "",
            "last_imported_at": "",
            "queued_events": [],
        },
        "proactive": {
            "last_idle_nudge_at": "",
            "last_idle_nudge_text": "",
            "suggestions": [],
        },
    }


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _merge_defaults(payload: dict[str, Any] | None) -> dict[str, Any]:
    merged = _default_state()
    if not isinstance(payload, dict):
        return merged
    for key, value in payload.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    if not merged.get("sync", {}).get("device_id"):
        merged["sync"]["device_id"] = _build_device_id()
    return merged


def _write_state(payload: dict[str, Any]) -> None:
    _ensure_data_dir()
    temp_path = f"{STATE_PATH}.tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    os.replace(temp_path, STATE_PATH)


def _persist_locked() -> None:
    if _CACHE is None:
        return
    _write_state(copy.deepcopy(_CACHE))


def flush() -> None:
    global _SAVE_TIMER
    with _LOCK:
        timer = _SAVE_TIMER
        _SAVE_TIMER = None
        if timer is not None and timer.is_alive():
            timer.cancel()
        _persist_locked()


def _schedule_write_locked(*, immediate: bool = False) -> None:
    global _SAVE_TIMER
    if immediate:
        _persist_locked()
        return
    timer = _SAVE_TIMER
    if timer is not None and timer.is_alive():
        return
    _SAVE_TIMER = threading.Timer(_SAVE_DELAY_SECONDS, flush)
    _SAVE_TIMER.daemon = True
    _SAVE_TIMER.start()


def _load_state() -> dict[str, Any]:
    _ensure_data_dir()
    if not os.path.exists(STATE_PATH):
        payload = _default_state()
        _write_state(payload)
        return payload
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        payload = _default_state()
        _write_state(payload)
        return payload
    normalized = _merge_defaults(payload)
    if normalized != payload:
        _write_state(normalized)
    return normalized


def snapshot() -> dict[str, Any]:
    global _CACHE
    with _LOCK:
        if _CACHE is None:
            _CACHE = _load_state()
        return copy.deepcopy(_CACHE)


def load_section(name: str, default: Any = None) -> Any:
    state = snapshot()
    return copy.deepcopy(state.get(name, default))


def replace_section(name: str, payload: Any) -> Any:
    global _CACHE
    with _LOCK:
        if _CACHE is None:
            _CACHE = _load_state()
        _CACHE[name] = payload
        _schedule_write_locked()
        return copy.deepcopy(_CACHE[name])


def update_section(name: str, updater: Callable[[Any], Any]) -> Any:
    global _CACHE
    with _LOCK:
        if _CACHE is None:
            _CACHE = _load_state()
        current = copy.deepcopy(_CACHE.get(name))
        updated = updater(current)
        _CACHE[name] = updated
        _schedule_write_locked()
        return copy.deepcopy(updated)


def utc_now() -> str:
    return _utc_now()


atexit.register(flush)
