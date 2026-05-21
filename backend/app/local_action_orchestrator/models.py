from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ActionDomain = Literal["browser", "chat", "visual_desktop", "autonomous_agent", "general"]
RiskLevel = Literal["safe_read", "safe_local_action", "medium_confirmation", "high_confirmation", "blocked"]


def compact_text(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


@dataclass
class DomainClassification:
    command: str
    detected_domain: ActionDomain
    confidence: float
    reason: str
    slots: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["command"] = compact_text(payload.get("command"), 2000)
        payload["confidence"] = round(float(payload.get("confidence") or 0.0), 3)
        return payload


@dataclass
class LocalActionPlan:
    command: str
    detected_domain: ActionDomain
    confidence: float
    plan_steps: list[dict[str, Any]]
    requires_confirmation: bool
    risk_level: RiskLevel
    next_action: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["command"] = compact_text(payload.get("command"), 2000)
        payload["confidence"] = round(float(payload.get("confidence") or 0.0), 3)
        payload["plan_steps"] = [self._safe_step(step) for step in self.plan_steps[:20]]
        return payload

    def _safe_step(self, step: dict[str, Any]) -> dict[str, Any]:
        return {
            "step": compact_text(step.get("step"), 120),
            "system": compact_text(step.get("system"), 80),
            "action": compact_text(step.get("action"), 120),
            "details": compact_text(step.get("details"), 500),
            "requires_confirmation": bool(step.get("requires_confirmation")),
        }
