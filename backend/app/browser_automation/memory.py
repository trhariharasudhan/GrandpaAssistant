from __future__ import annotations

import json
import os
import tempfile
import time
from typing import Any

from .config import browser_runtime_dir


def _compact_text(value: Any, limit: int = 500) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


class BrowserMemory:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.path.join(browser_runtime_dir(), "browser_memory.json")

    def load(self) -> dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except FileNotFoundError:
            payload = {}
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        return {
            "schema_version": 1,
            "sessions": dict(payload.get("sessions") or {}),
            "recent_tasks": list(payload.get("recent_tasks") or [])[-50:],
            "site_preferences": dict(payload.get("site_preferences") or {}),
        }

    def save(self, payload: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix=".browser-memory-", suffix=".json", dir=os.path.dirname(self.path))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
            os.replace(temp_path, self.path)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def remember_task(self, *, task: str, session_id: str, browser: str, url: str = "") -> None:
        payload = self.load()
        payload["recent_tasks"].append(
            {
                "task": _compact_text(task),
                "session_id": _compact_text(session_id, 120),
                "browser": _compact_text(browser, 40),
                "url": _compact_text(url, 1000),
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        payload["recent_tasks"] = payload["recent_tasks"][-50:]
        self.save(payload)

    def remember_session(self, session_id: str, data: dict[str, Any]) -> None:
        payload = self.load()
        payload["sessions"][_compact_text(session_id, 120)] = {
            "browser": _compact_text(data.get("browser"), 40),
            "last_url": _compact_text(data.get("last_url"), 1000),
            "last_title": _compact_text(data.get("last_title"), 300),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self.save(payload)

    def status(self) -> dict[str, Any]:
        payload = self.load()
        return {
            "ok": True,
            "path": self.path,
            "session_count": len(payload.get("sessions") or {}),
            "recent_task_count": len(payload.get("recent_tasks") or []),
            "site_preference_count": len(payload.get("site_preferences") or {}),
            "private_content_exposed": False,
        }
