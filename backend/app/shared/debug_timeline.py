from __future__ import annotations

import re
from typing import Any

from debug_session import get_current_debug_session, list_debug_sessions


MAX_TEXT_LENGTH = 900
SECRET_PATTERNS = (
    re.compile(r"(?i)(password|passwd|token|secret|credential|api[_-]?key)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
)


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
        output = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in ("password", "token", "secret", "credential", "api_key", "apikey", "screenshot", "raw_binary")):
                output[key] = "[REDACTED]"
            else:
                output[key] = _redact(item)
        return output
    if isinstance(value, list):
        return [_redact(item) for item in value[:50]]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _timestamp(payload: dict[str, Any], fallback: str = "") -> str:
    return _compact_text(payload.get("timestamp") or payload.get("created_at") or payload.get("updated_at") or payload.get("executed_at") or fallback)


def _event(event_type: str, title: str, summary: str, timestamp: str = "", safety_flag: str = "read_only") -> dict[str, Any]:
    return {
        "timestamp": _redact_text(timestamp),
        "type": event_type,
        "title": _redact_text(title),
        "summary": _redact_text(summary),
        "safety_flag": safety_flag,
    }


def timeline_event_from_debug_report(report):
    report = _redact(report or {})
    return _event(
        "debug_report",
        "Debug report captured",
        report.get("summary") or report.get("error_text") or "Debug report recorded.",
        _timestamp(report),
        "no_command_executed" if report.get("no_command_executed", True) else "review",
    )


def timeline_event_from_fix_plan(plan):
    plan = _redact(plan or {})
    return _event(
        "fix_plan",
        "Fix plan generated",
        plan.get("summary") or "Fix plan recorded.",
        _timestamp(plan),
        "no_command_executed" if plan.get("no_command_executed", True) and plan.get("no_file_edited", True) else "review",
    )


def timeline_event_from_approval(approval):
    approval = _redact(approval or {})
    payload = approval.get("payload") or {}
    command = payload.get("command") or payload.get("description") or approval.get("action_type") or "fix action"
    return _event(
        "fix_approval",
        f"Fix approval {approval.get('id') or ''}".strip(),
        f"Approval requested for: {command}",
        _timestamp(approval),
        "approval_required",
    )


def timeline_event_from_audit_event(event):
    event = _redact(event or {})
    approval = event.get("approval") or {}
    command = approval.get("command") or event.get("message") or "fix action"
    event_type = event.get("event_type") or "audit"
    return _event(
        "audit_event",
        f"Audit event: {event_type}",
        f"{event_type}: {command}",
        _timestamp(event),
        "executed_if_audit_says_so" if event_type == "executed" else "recorded",
    )


def _session_for_timeline(session=None):
    if session:
        return session
    current = get_current_debug_session()
    if current:
        return current
    sessions = list_debug_sessions(limit=1)
    return sessions[0] if sessions else None


def build_debug_timeline(session=None, limit=50, language="auto"):
    session = _session_for_timeline(session)
    if not session:
        return {"ok": False, "session_id": None, "items": [], "message": "No debug session is available."}
    fallback = session.get("created_at") or session.get("updated_at") or ""
    items = []
    for report in session.get("debug_reports", []) or []:
        item = timeline_event_from_debug_report(report)
        item["timestamp"] = item["timestamp"] or fallback
        items.append(item)
    for plan in session.get("fix_plans", []) or []:
        item = timeline_event_from_fix_plan(plan)
        item["timestamp"] = item["timestamp"] or fallback
        items.append(item)
    for approval in session.get("fix_approvals", []) or []:
        item = timeline_event_from_approval(approval)
        item["timestamp"] = item["timestamp"] or fallback
        items.append(item)
    for event in session.get("audit_events", []) or []:
        item = timeline_event_from_audit_event(event)
        item["timestamp"] = item["timestamp"] or fallback
        items.append(item)
    try:
        limit_value = max(1, int(limit))
    except Exception:
        limit_value = 50
    items = sorted(items, key=lambda item: item.get("timestamp", ""))[:limit_value]
    return {
        "ok": True,
        "session_id": session.get("id"),
        "status": session.get("status"),
        "language": language or "auto",
        "items": items,
    }


def get_current_debug_timeline(language="auto"):
    return build_debug_timeline(language=language)


def format_debug_timeline(timeline, language="auto"):
    timeline = timeline or {}
    items = timeline.get("items") or []
    tamil = str(language or timeline.get("language") or "").lower() in {"ta", "tamil"}
    if not items:
        return "Debug timeline empty-a irukku." if tamil else "No debug timeline events are available."
    prefix = "Debug timeline: "
    parts = []
    for index, item in enumerate(items[:10], start=1):
        parts.append(f"{index}. {item.get('timestamp') or 'unknown'} - {item.get('title')}: {item.get('summary')}")
    return prefix + " | ".join(parts)
