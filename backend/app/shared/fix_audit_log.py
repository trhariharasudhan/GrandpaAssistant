from __future__ import annotations

import datetime
import json
import os
import re
from typing import Any

try:
    from utils.paths import backend_data_path
except Exception:
    backend_data_path = None


FIX_AUDIT_LOG_PATH = (
    backend_data_path("audit", "fix_audit.jsonl")
    if backend_data_path
    else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "audit", "fix_audit.jsonl"))
)
MAX_TEXT_LENGTH = 1200
SECRET_PATTERNS = (
    re.compile(r"(?i)(password|passwd|token|secret|credential|api[_-]?key)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
)


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _redact_text(value: Any) -> str:
    text = str(value or "")
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.lower().startswith("(?i)(bearer"):
            text = pattern.sub(r"\1[REDACTED]", text)
        else:
            text = pattern.sub(r"\1=[REDACTED]", text)
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH] + "...[truncated]"
    return text


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in ("password", "token", "secret", "credential", "api_key", "apikey")):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value[:50]]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _approval_summary(approval: dict[str, Any] | None) -> dict[str, Any] | None:
    if not approval:
        return None
    payload = approval.get("payload") or {}
    return _redact(
        {
            "id": approval.get("id"),
            "action_type": approval.get("action_type"),
            "status": approval.get("status"),
            "command": payload.get("command"),
            "description": payload.get("description"),
            "reason": approval.get("reason") or payload.get("reason"),
            "validation": approval.get("validation"),
        }
    )


def _ensure_log_dir() -> None:
    os.makedirs(os.path.dirname(FIX_AUDIT_LOG_PATH), exist_ok=True)


def append_fix_audit_event(event_type, approval=None, result=None, message="", metadata=None):
    event = {
        "timestamp": _utc_now(),
        "event_type": _compact_text(event_type),
        "approval": _approval_summary(approval),
        "result": _redact(result or {}),
        "message": _redact_text(message),
        "metadata": _redact(metadata or {}),
    }
    _ensure_log_dir()
    with open(FIX_AUDIT_LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")
    return event


def list_fix_audit_events(limit=50):
    try:
        limit_value = max(1, int(limit))
    except Exception:
        limit_value = 50
    if not os.path.exists(FIX_AUDIT_LOG_PATH):
        return []
    events = []
    with open(FIX_AUDIT_LOG_PATH, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events[-limit_value:][::-1]


def clear_fix_audit_log_for_tests():
    if os.path.exists(FIX_AUDIT_LOG_PATH):
        os.remove(FIX_AUDIT_LOG_PATH)


def summarize_fix_audit_log(limit=10, language: str = "auto"):
    events = list_fix_audit_events(limit=limit)
    tamil = str(language or "").lower() in {"ta", "tamil"}
    if not events:
        return "Fix audit log empty-a irukku." if tamil else "No fix audit events have been recorded yet."
    parts = []
    for event in events:
        approval = event.get("approval") or {}
        command = approval.get("command") or approval.get("description") or approval.get("action_type") or "fix action"
        parts.append(f"{event.get('event_type')} {approval.get('id') or ''}: {command}".strip())
    prefix = "Recent fix audit events: " if not tamil else "Recent fix audit events: "
    return prefix + " | ".join(parts)
