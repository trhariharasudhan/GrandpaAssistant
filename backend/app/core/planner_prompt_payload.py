from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .prompt_builder import build_system_prompt
from .prompt_memory_context import build_safe_memory_context


MAX_RISK_TEXT_CHARS = 120
SENSITIVE_TERMS = {"credential", "password", "token", "secret", "api key", "api_key", "otp", "pin"}
HIGH_RISK_TERMS = {
    "delete": "destructive file/data action",
    "remove files": "destructive file/data action",
    "format": "destructive storage action",
    "shutdown": "system power action",
    "restart": "system power action",
    "registry": "Windows registry action",
    "payment": "payment or financial action",
    "transfer": "financial transfer action",
    "credential": "credential handling",
    "password": "credential handling",
    "token": "secret handling",
    "secret": "secret handling",
    "api key": "secret handling",
    "api_key": "secret handling",
    "otp": "one-time code handling",
    "pin": "PIN handling",
}
MEDIUM_RISK_TERMS = {
    "install": "software installation",
    "uninstall": "software removal",
    "modify system settings": "system settings change",
    "system settings": "system settings change",
    "browser automation": "browser automation",
    "ui click": "UI click automation",
    "click automation": "UI click automation",
    "email": "communication action",
    "send message": "communication action",
    "network scan": "network scanning",
    "network scanning": "network scanning",
}


@dataclass
class PlannerPromptPayload:
    mode: str = "planning"
    user_request: str = ""
    system_prompt: str = ""
    memory_context_included: bool = False
    execution_allowed: bool = False
    tools_allowed: bool = False
    requires_confirmation: bool = False
    risk_level: str = "low"
    risks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _sanitize_request(user_request: Any, max_request_chars: int) -> tuple[str, bool]:
    raw_lines = str(user_request or "").splitlines()
    removed_sensitive = False
    safe_lines: list[str] = []
    for line in raw_lines or [str(user_request or "")]:
        lowered = line.lower()
        if any(term in lowered for term in SENSITIVE_TERMS):
            removed_sensitive = True
            continue
        compact = _compact_text(line)
        if compact:
            safe_lines.append(compact)
    text = "\n".join(safe_lines)
    if len(text) > max_request_chars:
        return text[:max_request_chars].rstrip(), True or removed_sensitive
    return text, removed_sensitive


def _matched_risks(text: str, terms: dict[str, str]) -> list[str]:
    lowered = text.lower()
    risks = []
    for term, label in terms.items():
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            risks.append(label)
    return sorted(set(risks))


def classify_planning_risk(user_request: str) -> tuple[str, list[str], bool]:
    """Classify planning risk without executing anything."""
    text = _compact_text(user_request).lower()[:MAX_RISK_TEXT_CHARS * 20]
    high = _matched_risks(text, HIGH_RISK_TERMS)
    if high:
        return "high", high, True
    medium = _matched_risks(text, MEDIUM_RISK_TERMS)
    if medium:
        return "medium", medium, True
    return "low", [], False


def build_planner_prompt_payload(
    user_request: str,
    memory_context=None,
    extra_context=None,
    max_request_chars: int = 4000,
) -> dict[str, Any]:
    """Build an internal planner payload without calling providers or tools."""
    safe_request, sanitized = _sanitize_request(user_request, max(1, max_request_chars))
    safe_memory_context = build_safe_memory_context(memory_context)
    risk_level, risks, requires_confirmation = classify_planning_risk(safe_request)
    system_prompt = build_system_prompt(
        "planning",
        memory_context=safe_memory_context or None,
        extra_context=_compact_text(extra_context) or None,
    )
    payload = PlannerPromptPayload(
        user_request=safe_request,
        system_prompt=system_prompt,
        memory_context_included=bool(safe_memory_context),
        requires_confirmation=requires_confirmation,
        risk_level=risk_level,
        risks=risks,
        metadata={
            "request_truncated": len(safe_request) >= max(1, max_request_chars),
            "sensitive_content_removed": sanitized,
            "system_prompt_length": len(system_prompt),
        },
    )
    return asdict(payload)


def build_and_verify_planner_payload(
    user_request: str,
    memory_context=None,
    extra_context=None,
    max_request_chars: int = 4000,
) -> dict[str, Any]:
    from .planner_payload_verifier import verify_planner_payload

    payload = build_planner_prompt_payload(
        user_request,
        memory_context=memory_context,
        extra_context=extra_context,
        max_request_chars=max_request_chars,
    )
    return {"payload": payload, "verification": verify_planner_payload(payload)}
