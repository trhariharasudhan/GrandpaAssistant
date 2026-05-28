from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from utils.paths import runtime_path
except Exception:  # pragma: no cover
    runtime_path = None

from .action_schema import AgentPlan, compact_text, plan_from_dict


def default_state_path() -> str:
    if runtime_path is not None:
        return runtime_path("autonomous_agent_v1", "plans.json")
    return os.path.join("runtime", "autonomous_agent_v1", "plans.json")


class AgentStateStore:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or default_state_path()

    def load(self) -> dict[str, Any]:
        try:
            if not os.path.exists(self.path):
                return {"plans": []}
            payload = json.loads(Path(self.path).read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {"plans": []}
        except Exception:
            return {"plans": [], "warning": "agent_v1_state_unreadable"}

    def save(self, payload: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        Path(tmp).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    def save_plan(self, plan: AgentPlan) -> dict[str, Any]:
        payload = self.load()
        plans = [item for item in payload.get("plans", []) if item.get("plan_id") != plan.plan_id]
        plans.append(plan.to_dict())
        payload["plans"] = plans[-100:]
        self.save(payload)
        return plan.to_dict()

    def save_plan_payload(self, plan_payload: dict[str, Any]) -> dict[str, Any]:
        payload = self.load()
        plan_id = compact_text(plan_payload.get("plan_id"))
        plans = [item for item in payload.get("plans", []) if item.get("plan_id") != plan_id]
        plans.append(plan_payload)
        payload["plans"] = plans[-100:]
        self.save(payload)
        return plan_payload

    def get_plan(self, plan_id: str) -> AgentPlan | None:
        wanted = compact_text(plan_id)
        for item in self.load().get("plans", []):
            if item.get("plan_id") == wanted:
                return plan_from_dict(item)
        return None
