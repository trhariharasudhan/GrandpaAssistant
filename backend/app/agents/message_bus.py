from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable


def _topic_matches(pattern: str, topic: str) -> bool:
    if pattern in {"*", topic}:
        return True
    if pattern.endswith(".*"):
        prefix = pattern[:-2]
        return topic == prefix or topic.startswith(prefix + ".")
    return False


class AgentMessageBus:
    def __init__(self, history_limit: int = 200):
        self._history_limit = max(20, int(history_limit))
        self._events: list[dict[str, Any]] = []
        self._subscribers: list[tuple[str, str, Callable[[dict[str, Any]], Any]]] = []
        self._lock = threading.RLock()

    def subscribe(self, pattern: str, callback: Callable[[dict[str, Any]], Any], owner: str = "system") -> None:
        with self._lock:
            self._subscribers.append((pattern or "*", owner, callback))

    def publish(self, topic: str, payload: dict[str, Any] | None = None, *, source: str = "system", target: str = "broadcast") -> dict[str, Any]:
        event = {
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "topic": str(topic or "assistant.unknown"),
            "source": str(source or "system"),
            "target": str(target or "broadcast"),
            "payload": dict(payload or {}),
        }
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._history_limit:
                del self._events[:-self._history_limit]
            subscribers = list(self._subscribers)

        for pattern, owner, callback in subscribers:
            if not _topic_matches(pattern, event["topic"]):
                continue
            try:
                callback(event)
            except Exception:
                continue
        return event

    def recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._events[-max(1, int(limit)):])

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "subscriber_count": len(self._subscribers),
                "event_count": len(self._events),
                "history_limit": self._history_limit,
            }
