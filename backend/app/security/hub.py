from __future__ import annotations

from typing import Any

from security.auth_manager import admin_mode_active, auth_status_payload, has_active_security_session
from security.device_monitor import device_security_status_payload, sync_device_inventory
from security.encryption_utils import encryption_status_payload, remember_protected_target
from security.permission_engine import classify_command
from security.state import append_security_activity
from security.threat_detector import detect_prompt_injection, evaluate_command_threat, security_log_payload, threat_status_payload
from utils.config import get_setting


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def validate_prompt_text(text: str, *, source: str = "chat") -> dict[str, Any]:
    check = detect_prompt_injection(text)
    if check["blocked"]:
        append_security_activity(
            "prompt_blocked",
            level="error",
            source=source,
            message=check["reason"],
            command=text,
        )
        return {
            "allowed": False,
            "message": "I can't follow unsafe or rule-bypass instructions.",
            "reason": check["reason"],
        }
    return {"allowed": True, "message": "", "reason": ""}


def validate_command(command: str, *, source: str = "command") -> dict[str, Any]:
    normalized = _compact_text(command)
    permission = classify_command(normalized)
    threat = evaluate_command_threat(normalized, permission)
    auth = auth_status_payload()

    decision = {
        "allowed": True,
        "action": "allow",
        "message": "",
        "permission": permission,
        "threat": threat,
        "auth": auth,
    }

    if threat["blocked"]:
        decision["allowed"] = False
        decision["action"] = "block"
        decision["message"] = threat["reason"]
    elif permission.get("requires_admin_mode") and not admin_mode_active():
        decision["allowed"] = False
        decision["action"] = "authenticate"
        decision["message"] = "Security admin mode is required. Verify your face, verify your voice, or use your security PIN."
    elif (permission.get("requires_authentication") or threat.get("requires_authentication")) and not has_active_security_session():
        decision["allowed"] = False
        decision["action"] = "authenticate"
        decision["message"] = "Authentication required. Verify your face, verify your voice, or use your security PIN."
    elif permission.get("requires_confirmation") or threat.get("requires_confirmation"):
        decision["allowed"] = False
        decision["action"] = "confirm"
        decision["message"] = f"Please confirm this {permission.get('level', 'MEDIUM').lower()} risk command: {normalized}"

    append_security_activity(
        "command_validation",
        level="info" if decision["allowed"] else "warning",
        source=source,
        message=decision["message"] or permission.get("reason", "Command validated."),
        command=normalized,
        metadata={
            "action": decision["action"],
            "level": permission.get("level", "LOW"),
            "category": permission.get("category", "general"),
            "requires_admin_mode": permission.get("requires_admin_mode", False),
            "suspicious": threat.get("suspicious", False),
        },
    )
    return decision


def security_status_payload(device_manager=None) -> dict[str, Any]:
    if device_manager is not None:
        sync_device_inventory(device_manager)
    return {
        "auth": auth_status_payload(),
        "devices": device_security_status_payload(),
        "threats": threat_status_payload(),
        "encryption": encryption_status_payload(),
    }


def security_logs_payload(limit: int = 100) -> dict[str, Any]:
    return security_log_payload(limit=limit)


def record_sensitive_target(path: str) -> None:
    remember_protected_target(path)
