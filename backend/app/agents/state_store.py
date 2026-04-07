from __future__ import annotations

import copy
import json
import os
import threading
import time
import atexit
from typing import Any


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "backend", "data")
STATE_PATH = os.path.join(DATA_DIR, "agent_runtime_state.json")


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


DEFAULT_STATE = {
    "runtime": {
        "started_at": "",
        "last_updated_at": "",
        "autonomous_mode": True,
        "thinking_mode": "adaptive",
        "current_context": "casual",
        "last_user_message": "",
        "last_assistant_reply": "",
    },
    "agents": {},
    "conversation": {
        "recent_messages": [],
        "last_emotion": "neutral",
        "last_mood": "neutral",
    },
    "goals": [],
    "plugins": {},
}


class AgentStateStore:
    def __init__(self, state_path: str = STATE_PATH):
        self.state_path = state_path
        self._lock = threading.RLock()
        self._save_timer: threading.Timer | None = None
        self._save_delay_seconds = 0.4
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

    def _touch(self) -> None:
        self._state.setdefault("runtime", {})
        self._state["runtime"]["last_updated_at"] = _utc_timestamp()

    def mark_started(self) -> None:
        with self._lock:
            runtime = self._state.setdefault("runtime", {})
            runtime["started_at"] = _utc_timestamp()
            self._touch()
            self._schedule_save_locked(immediate=True)

    def set_runtime_mode(self, *, autonomous_mode: bool | None = None, thinking_mode: str | None = None, current_context: str | None = None) -> None:
        with self._lock:
            runtime = self._state.setdefault("runtime", {})
            if autonomous_mode is not None:
                runtime["autonomous_mode"] = bool(autonomous_mode)
            if thinking_mode is not None:
                runtime["thinking_mode"] = str(thinking_mode).strip() or "adaptive"
            if current_context is not None:
                runtime["current_context"] = str(current_context).strip() or "casual"
            self._touch()
            self._schedule_save_locked()

    def update_agent(self, agent_name: str, payload: dict[str, Any]) -> None:
        with self._lock:
            agents = self._state.setdefault("agents", {})
            item = dict(payload or {})
            item["updated_at"] = _utc_timestamp()
            agents[agent_name] = item
            self._touch()
            self._schedule_save_locked()

    def record_user_message(self, text: str, *, emotion: str = "neutral", mood: str = "neutral", source: str = "chat") -> None:
        with self._lock:
            runtime = self._state.setdefault("runtime", {})
            runtime["last_user_message"] = text
            conversation = self._state.setdefault("conversation", {})
            conversation["last_emotion"] = emotion
            conversation["last_mood"] = mood
            messages = conversation.setdefault("recent_messages", [])
            messages.append(
                {
                    "role": "user",
                    "source": source,
                    "text": text,
                    "emotion": emotion,
                    "mood": mood,
                    "timestamp": _utc_timestamp(),
                }
            )
            if len(messages) > 40:
                del messages[:-40]
            self._touch()
            self._schedule_save_locked()

    def record_assistant_reply(self, text: str, *, source: str = "assistant") -> None:
        with self._lock:
            runtime = self._state.setdefault("runtime", {})
            runtime["last_assistant_reply"] = text
            conversation = self._state.setdefault("conversation", {})
            messages = conversation.setdefault("recent_messages", [])
            messages.append(
                {
                    "role": "assistant",
                    "source": source,
                    "text": text,
                    "timestamp": _utc_timestamp(),
                }
            )
            if len(messages) > 40:
                del messages[:-40]
            self._touch()
            self._schedule_save_locked()

    def replace_plugins(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._state["plugins"] = dict(payload or {})
            self._touch()
            self._schedule_save_locked()

    def add_goal(self, title: str, steps: list[str], *, source: str = "user") -> dict[str, Any]:
        with self._lock:
            goal = {
                "id": f"goal-{int(time.time() * 1000)}",
                "title": str(title).strip(),
                "steps": [{"title": step, "done": False} for step in steps if str(step).strip()],
                "source": source,
                "created_at": _utc_timestamp(),
                "updated_at": _utc_timestamp(),
                "status": "active",
            }
            goals = self._state.setdefault("goals", [])
            goals.append(goal)
            if len(goals) > 40:
                del goals[:-40]
            self._touch()
            self._schedule_save_locked()
            return copy.deepcopy(goal)
