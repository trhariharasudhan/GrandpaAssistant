from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


REQUIRED_FIELDS = {
    "mode",
    "user_request",
    "system_prompt",
    "memory_context_included",
    "execution_allowed",
    "tools_allowed",
    "requires_confirmation",
    "risk_level",
    "risks",
    "metadata",
}
VALID_RISK_LEVELS = {"low", "medium", "high"}


@dataclass
class PlannerPayloadVerificationResult:
    valid: bool = False
    safe_to_use_for_llm: bool = False
    safe_to_execute: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    risk_level: str = "unknown"
    requires_confirmation: bool = False
    checked_fields: list[str] = field(default_factory=list)


def _result(
    *,
    errors: list[str],
    warnings: list[str],
    risk_level: str,
    requires_confirmation: bool,
    checked_fields: list[str],
) -> dict[str, Any]:
    valid = not errors
    return asdict(
        PlannerPayloadVerificationResult(
            valid=valid,
            safe_to_use_for_llm=valid,
            safe_to_execute=False,
            errors=errors,
            warnings=warnings,
            risk_level=risk_level if risk_level in VALID_RISK_LEVELS else "unknown",
            requires_confirmation=bool(requires_confirmation),
            checked_fields=checked_fields,
        )
    )


def verify_planner_payload(payload: dict) -> dict[str, Any]:
    """Verify a planner payload without exposing prompt or request text."""
    errors: list[str] = []
    warnings: list[str] = []
    checked_fields: list[str] = []
    try:
        if not isinstance(payload, dict):
            return _result(
                errors=["payload must be a dict"],
                warnings=[],
                risk_level="unknown",
                requires_confirmation=False,
                checked_fields=[],
            )

        missing = sorted(REQUIRED_FIELDS.difference(payload.keys()))
        checked_fields = sorted(REQUIRED_FIELDS.intersection(payload.keys()))
        if missing:
            errors.append(f"missing required fields: {', '.join(missing)}")

        mode = payload.get("mode")
        if mode != "planning":
            errors.append("mode must be planning")

        if not payload.get("system_prompt"):
            errors.append("system_prompt is required")

        if payload.get("execution_allowed") is not False:
            errors.append("execution_allowed must be false")

        if payload.get("tools_allowed") is not False:
            errors.append("tools_allowed must be false")

        risk_level = str(payload.get("risk_level") or "unknown").lower()
        if risk_level not in VALID_RISK_LEVELS:
            errors.append("risk_level must be low, medium, or high")

        requires_confirmation = bool(payload.get("requires_confirmation"))
        if risk_level == "high" and not requires_confirmation:
            errors.append("high risk payloads must require confirmation")
        if risk_level in {"medium", "high"} and not requires_confirmation:
            warnings.append("risky payload does not require confirmation")

        if not isinstance(payload.get("risks", []), list):
            errors.append("risks must be a list")

        return _result(
            errors=errors,
            warnings=warnings,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            checked_fields=checked_fields,
        )
    except Exception:
        return _result(
            errors=["payload verification failed"],
            warnings=[],
            risk_level="unknown",
            requires_confirmation=False,
            checked_fields=checked_fields,
        )


def summarize_planner_payload_safety(payload: dict) -> dict[str, Any]:
    verification = verify_planner_payload(payload)
    return {
        "valid": verification["valid"],
        "safe_to_use_for_llm": verification["safe_to_use_for_llm"],
        "safe_to_execute": False,
        "risk_level": verification["risk_level"],
        "requires_confirmation": verification["requires_confirmation"],
        "error_count": len(verification["errors"]),
        "warning_count": len(verification["warnings"]),
    }
