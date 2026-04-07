from __future__ import annotations

import datetime
from typing import Any

from brain.database import get_recent_commands
from security.auth_manager import auth_status_payload, is_locked_out
from security.state import STATE, append_security_activity, read_security_activity, utc_now
from utils.config import get_setting


PROMPT_INJECTION_PATTERNS = [
    "ignore all previous instructions",
    "ignore all rules",
    "bypass safety",
    "disable security",
    "reveal the system prompt",
    "show hidden prompt",
    "act as system",
    "execute unsafe command",
    "jailbreak",
]


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _threat_detection_enabled() -> bool:
    return bool(get_setting("security.threat_detection_enabled", True))


def _prompt_guard_enabled() -> bool:
    return bool(get_setting("security.prompt_guard_enabled", True))


def _record_recent_threat(level: str, message: str, *, command: str = "", kind: str = "threat") -> None:
    append_security_activity(
        kind,
        level=level,
        source="threat-detector",
        message=message,
        command=command,
    )

    def _update(state: dict[str, Any]) -> None:
        threats = state.setdefault("threats", {})
        recent = list(threats.get("recent_events") or [])
        recent.append(
            {
                "timestamp": utc_now(),
                "level": level,
                "message": message,
                "command": command,
                "kind": kind,
            }
        )
        threats["recent_events"] = recent[-40:]
        if level == "warning":
            threats["suspicious_count"] = int(threats.get("suspicious_count", 0) or 0) + 1
        if level == "error":
            threats["blocked_count"] = int(threats.get("blocked_count", 0) or 0) + 1
        if kind == "prompt_injection":
            threats["last_prompt_injection_at"] = utc_now()

    STATE.update(_update)


def detect_prompt_injection(text: str) -> dict[str, Any]:
    normalized = _compact_text(text).lower()
    if not _prompt_guard_enabled() or not normalized:
        return {"blocked": False, "reason": ""}

    if normalized.startswith(("what is ", "explain ", "how does ", "tell me about ")):
        return {"blocked": False, "reason": ""}

    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern in normalized:
            reason = "Prompt injection attempt detected."
            _record_recent_threat("error", reason, command=text, kind="prompt_injection")
            return {"blocked": True, "reason": reason}
    return {"blocked": False, "reason": ""}


def evaluate_command_threat(command: str, permission: dict[str, Any]) -> dict[str, Any]:
    normalized = _compact_text(command)
    result = {
        "blocked": False,
        "suspicious": False,
        "requires_authentication": False,
        "requires_confirmation": False,
        "reason": "",
    }
    if not _threat_detection_enabled() or not normalized:
        return result

    prompt_check = detect_prompt_injection(normalized)
    if prompt_check["blocked"]:
        result["blocked"] = True
        result["reason"] = prompt_check["reason"]
        return result

    auth = auth_status_payload()
    if auth.get("lockdown"):
        result["blocked"] = True
        result["reason"] = "Assistant lockdown is active. Authentication is required to unlock secure commands."
        _record_recent_threat("error", result["reason"], command=normalized, kind="lockdown_block")
        return result

    if is_locked_out():
        result["blocked"] = True
        result["reason"] = "Too many failed authentication attempts. Security lockout is active."
        _record_recent_threat("error", result["reason"], command=normalized, kind="lockout_block")
        return result

    recent_commands = {item.lower() for item in get_recent_commands(limit=12)}
    now_hour = datetime.datetime.now().hour
    level = permission.get("level", "LOW")
    if level == "HIGH" and (now_hour < 5 or now_hour >= 23):
        result["suspicious"] = True
        result["requires_authentication"] = True
        result["reason"] = "High-risk command detected during an unusual hour."
        _record_recent_threat("warning", result["reason"], command=normalized, kind="timing_anomaly")
        return result

    if level == "HIGH" and normalized.lower() not in recent_commands:
        result["suspicious"] = True
        result["requires_authentication"] = True
        result["reason"] = "This high-risk command is unusual for recent activity."
        _record_recent_threat("warning", result["reason"], command=normalized, kind="unusual_command")
        return result

    if auth.get("failed_attempts", 0) >= 2 and level in {"MEDIUM", "HIGH"}:
        result["suspicious"] = True
        result["requires_authentication"] = True
        result["reason"] = "Recent failed authentication attempts make this action suspicious."
        _record_recent_threat("warning", result["reason"], command=normalized, kind="repeated_failures")
        return result

    return result


def threat_status_payload(limit: int = 20) -> dict[str, Any]:
    snapshot = STATE.snapshot().get("threats", {})
    return {
        "blocked_count": int(snapshot.get("blocked_count", 0) or 0),
        "suspicious_count": int(snapshot.get("suspicious_count", 0) or 0),
        "last_prompt_injection_at": snapshot.get("last_prompt_injection_at", ""),
        "recent_events": list(snapshot.get("recent_events") or [])[-max(1, int(limit)):],
    }


def security_log_payload(limit: int = 100) -> dict[str, Any]:
    return {
        "items": read_security_activity(limit=limit),
    }

