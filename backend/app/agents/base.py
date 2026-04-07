from __future__ import annotations

from typing import Any


class BaseAgent:
    def __init__(self, agent_id: str, name: str, description: str, capabilities: list[str] | None = None):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.capabilities = list(capabilities or [])
        self.runtime = None

    def attach_runtime(self, runtime) -> None:
        self.runtime = runtime

    def startup(self) -> None:
        return

    def shutdown(self) -> None:
        return

    def refresh_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "ready": True,
        }

    def handle_event(self, event: dict[str, Any]) -> dict[str, Any] | None:
        return None

    def summary(self) -> dict[str, Any]:
        payload = self.refresh_status()
        payload.setdefault("name", self.name)
        payload.setdefault("description", self.description)
        payload.setdefault("capabilities", list(self.capabilities))
        return payload
