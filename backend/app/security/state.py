from __future__ import annotations

import copy
import json
import os
import threading
import time
import atexit
from typing import Any, Callable

from utils.paths import backend_data_dir, backend_data_path

DATA_DIR = backend_data_dir()
STATE_PATH = backend_data_path("security_state.json")
ACTIVITY_LOG_PATH = backend_data_path("security_activity.jsonl")
VOICE_PROFILE_PATH = backend_data_path("security_voice_profile.json")


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def utc_timestamp() -> float:
    return time.time()


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


DEFAULT_STATE: dict[str, Any] = {
    "auth": {
        "session_expires_at": 0.0,
        "admin_session_expires_at": 0.0,
        "last_auth_method": "",
        "last_successful_auth_at": "",
        "failed_attempts": 0,
        "failed_attempt_window_started_at": "",
        "lockout_until": 0.0,
        "lockdown": False,
        "lockdown_reason": "",
        "last_lockdown_at": "",
        "pin_hash": "",
        "pin_salt": "",
        "pin_configured": False,
    },
    "devices": {
        "inventory": {},
        "trusted_device_ids": [],
        "unknown_device_ids": [],
        "recent_alerts": [],
        "last_synced_at": "",
    },
    "threats": {
        "blocked_count": 0,
        "suspicious_count": 0,
        "recent_events": [],
        "last_prompt_injection_at": "",
    },
    "encryption": {
        "available": False,
        "enabled": False,
        "key_ready": False,
        "protected_targets": [],
        "last_protected_at": "",
    },
}


class SecurityStateStore:
    def __init__(self, state_path: str = STATE_PATH):
        self.state_path = state_path
        self._lock = threading.RLock()
        self._save_timer: threading.Timer | None = None
        self._save_delay_seconds = 0.35
        self._state = self._load()
        atexit.register(self.flush)

    def _load(self) -> dict[str, Any]:
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        if not os.path.exists(self.state_path):
            self._save(DEFAULT_STATE)
            return copy.deepcopy(DEFAULT_STATE)
        try:
            with open(self.state_path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except Exception:
            payload = copy.deepcopy(DEFAULT_STATE)
        if not isinstance(payload, dict):
            payload = copy.deepcopy(DEFAULT_STATE)
        merged = copy.deepcopy(DEFAULT_STATE)
        for key, value in payload.items():
            merged[key] = value
        return merged

    def _save(self, payload: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        temp_path = f"{self.state_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.state_path)

    def _persist_locked(self) -> None:
        self._save(copy.deepcopy(self._state))

    def flush(self) -> None:
        with self._lock:
            timer = self._save_timer
            self._save_timer = None
            if timer is not None and timer.is_alive():
                timer.cancel()
            self._persist_locked()

    def _schedule_save_locked(self, *, immediate: bool = False) -> None:
        if immediate:
            self._persist_locked()
            return
        timer = self._save_timer
        if timer is not None and timer.is_alive():
            return
        self._save_timer = threading.Timer(self._save_delay_seconds, self.flush)
        self._save_timer.daemon = True
        self._save_timer.start()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)

    def update(self, updater: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        with self._lock:
            updater(self._state)
            self._schedule_save_locked()
            return copy.deepcopy(self._state)


STATE = SecurityStateStore()


def append_security_activity(
    event_type: str,
    *,
    level: str = "info",
    source: str = "security",
    message: str = "",
    command: str = "",
    response: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    payload = {
        "timestamp": utc_now(),
        "event_type": _compact_text(event_type),
        "level": _compact_text(level) or "info",
        "source": _compact_text(source) or "security",
        "message": _compact_text(message),
        "command": _compact_text(command),
        "response": _compact_text(response),
        "metadata": metadata or {},
    }
    os.makedirs(os.path.dirname(ACTIVITY_LOG_PATH), exist_ok=True)
    with open(ACTIVITY_LOG_PATH, "a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_security_activity(limit: int = 100) -> list[dict[str, Any]]:
    if not os.path.exists(ACTIVITY_LOG_PATH):
        return []
    try:
        with open(ACTIVITY_LOG_PATH, "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file.readlines() if line.strip()]
    except Exception:
        return []

    items: list[dict[str, Any]] = []
    for line in lines[-max(1, int(limit)):]:
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            items.append(payload)
    return items
