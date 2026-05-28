from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


SafetyClassification = Literal["safe_read", "needs_confirmation", "blocked"]
StepStatus = Literal["pending", "executed", "skipped", "blocked", "warning", "failed"]


def compact_text(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def new_plan_id() -> str:
    return "agent-plan-" + uuid.uuid4().hex[:12]


@dataclass
class AgentStep:
    step_id: str
    action: str
    title: str
    params: dict[str, Any] = field(default_factory=dict)
    safety: SafetyClassification = "safe_read"
    requires_confirmation: bool = False
    blocked_reason: str = ""
    status: StepStatus = "pending"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["step_id"] = compact_text(payload.get("step_id"), 120)
        payload["action"] = compact_text(payload.get("action"), 120)
        payload["title"] = compact_text(payload.get("title"), 300)
        payload["blocked_reason"] = compact_text(payload.get("blocked_reason"), 500)
        payload["requires_confirmation"] = bool(payload.get("requires_confirmation"))
        payload["params"] = dict(payload.get("params") or {})
        return payload


@dataclass
class AgentPlan:
    understood_goal: str
    steps: list[AgentStep]
    plan_id: str = field(default_factory=new_plan_id)
    created_at: float = field(default_factory=time.time)
    agent_version: str = "autonomous_desktop_agent_v1"
    dry_run: bool = True
    executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        proposed_steps = [step.to_dict() for step in self.steps]
        blocked_reasons = [step.blocked_reason for step in self.steps if step.safety == "blocked" and step.blocked_reason]
        return {
            "agent_version": self.agent_version,
            "plan_id": self.plan_id,
            "understood_goal": compact_text(self.understood_goal, 2000),
            "proposed_steps": proposed_steps,
            "safety_classification": summarize_safety(proposed_steps),
            "confirmation_needed": any(step.requires_confirmation for step in self.steps if step.safety != "blocked"),
            "blocked_reasons": blocked_reasons,
            "dry_run": self.dry_run,
            "executed": self.executed,
            "created_at": self.created_at,
        }


def summarize_safety(steps: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"safe_read": 0, "needs_confirmation": 0, "blocked": 0}
    for step in steps:
        safety = compact_text(step.get("safety")) or "safe_read"
        if safety not in counts:
            safety = "safe_read"
        counts[safety] += 1
    overall = "blocked" if counts["blocked"] else ("needs_confirmation" if counts["needs_confirmation"] else "safe_read")
    return {"overall": overall, "counts": counts}


def plan_from_dict(payload: dict[str, Any]) -> AgentPlan:
    steps = []
    for index, item in enumerate(payload.get("proposed_steps") or payload.get("steps") or []):
        if not isinstance(item, dict):
            continue
        steps.append(
            AgentStep(
                step_id=compact_text(item.get("step_id")) or f"step_{index + 1}",
                action=compact_text(item.get("action")),
                title=compact_text(item.get("title")),
                params=dict(item.get("params") or {}),
                safety=compact_text(item.get("safety")) if compact_text(item.get("safety")) in {"safe_read", "needs_confirmation", "blocked"} else "safe_read",
                requires_confirmation=bool(item.get("requires_confirmation")),
                blocked_reason=compact_text(item.get("blocked_reason")),
                status=compact_text(item.get("status")) if compact_text(item.get("status")) in {"pending", "executed", "skipped", "blocked", "warning", "failed"} else "pending",
            )
        )
    return AgentPlan(
        plan_id=compact_text(payload.get("plan_id")) or new_plan_id(),
        understood_goal=compact_text(payload.get("understood_goal") or payload.get("goal"), 2000),
        steps=steps,
        created_at=float(payload.get("created_at") or time.time()),
        dry_run=bool(payload.get("dry_run", True)),
        executed=bool(payload.get("executed", False)),
    )
