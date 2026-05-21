from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

try:
    from utils.paths import runtime_path
except Exception:  # pragma: no cover
    runtime_path = None


def _state_path() -> str:
    if runtime_path is not None:
        return runtime_path("autonomous_agent", "tasks.json")
    return os.path.join("runtime", "autonomous_agent", "tasks.json")


def compact_text(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


class ContextManager:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or _state_path()

    def load(self) -> dict[str, Any]:
        try:
            if not os.path.exists(self.path):
                return {"tasks": []}
            payload = json.loads(Path(self.path).read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {"tasks": []}
        except Exception:
            return {"tasks": [], "error": "task_state_unreadable"}

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        Path(tmp).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)
        return {"ok": True, "path": self.path}

    def create_task(self, goal: str, graph: dict[str, Any]) -> dict[str, Any]:
        payload = self.load()
        task = {
            "task_id": "task-" + uuid.uuid4().hex[:10],
            "goal": compact_text(goal, 2000),
            "status": "planned",
            "created_at": time.time(),
            "updated_at": time.time(),
            "graph": graph,
            "action_history": [],
        }
        payload.setdefault("tasks", []).append(task)
        self.save(payload)
        return task

    def update_task(self, task_id: str, **updates: Any) -> dict[str, Any]:
        payload = self.load()
        found = {}
        for task in payload.get("tasks", []):
            if task.get("task_id") == task_id:
                task.update(updates)
                task["updated_at"] = time.time()
                found = task
                break
        self.save(payload)
        return found

    def status(self) -> dict[str, Any]:
        payload = self.load()
        counts: dict[str, int] = {}
        for task in payload.get("tasks", []):
            status = compact_text(task.get("status")) or "unknown"
            counts[status] = counts.get(status, 0) + 1
        return {"ok": True, "path": self.path, "task_count": len(payload.get("tasks", [])), "task_count_by_status": counts}
