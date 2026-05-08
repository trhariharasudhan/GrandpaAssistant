from __future__ import annotations

import re
from typing import Any

from debug_knowledge_reuse import build_reuse_suggestions
from debug_learning_summary import build_debug_learning_summary
from debug_preflight_checklist import run_preflight_checklist
from debug_session import get_current_debug_session
from debug_session_export import list_debug_exports
from debug_timeline import get_current_debug_timeline
from fix_approval_flow import list_pending_fix_approvals
from fix_audit_log import list_fix_audit_events


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
            if any(marker in lowered for marker in ("password", "passwd", "token", "secret", "credential", "api_key", "apikey")):
                output[key] = "[REDACTED]"
            else:
                output[key] = _redact(item)
        return output
    if isinstance(value, list):
        return [_redact(item) for item in value[:60]]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _safe_call(name: str, func, fallback: Any) -> tuple[Any, list[str]]:
    try:
        return func(), []
    except Exception as error:
        return fallback, [f"{name} unavailable: {_redact_text(error)}"]


def _active_session_summary(session: dict[str, Any] | None) -> dict[str, Any] | None:
    if not session:
        return None
    return _redact(
        {
            "id": session.get("id"),
            "title": session.get("title"),
            "status": session.get("status"),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
            "debug_reports_count": len(session.get("debug_reports") or []),
            "fix_plans_count": len(session.get("fix_plans") or []),
            "fix_approvals_count": len(session.get("fix_approvals") or []),
            "audit_events_count": len(session.get("audit_events") or []),
        }
    )


def _preflight_status(preflight: dict[str, Any]) -> dict[str, Any]:
    results = preflight.get("check_results") or []
    errors = [item for item in results if item.get("status") == "error" and not item.get("optional")]
    warnings = preflight.get("warnings") or [item for item in results if item.get("status") == "warning"]
    return _redact(
        {
            "ok": not errors,
            "checked_count": len(results),
            "warning_count": len(warnings),
            "error_count": len(errors),
            "warnings": warnings[:8],
            "recommended_next_steps": preflight.get("recommended_next_steps") or [],
            "no_destructive_action": bool(preflight.get("no_destructive_action", True)),
        }
    )


def compact_debug_health_status(payload):
    payload = payload or {}
    return _redact(
        {
            "overall_ok": bool(payload.get("overall_ok")),
            "active_session_id": (payload.get("active_session") or {}).get("id"),
            "pending_approvals_count": int(payload.get("pending_approvals_count") or 0),
            "recent_audit_count": int(payload.get("recent_audit_count") or 0),
            "timeline_count": int(payload.get("timeline_count") or 0),
            "export_count": int(payload.get("export_count") or 0),
            "warning_count": len(payload.get("warnings") or []),
            "no_destructive_action": bool(payload.get("no_destructive_action", True)),
        }
    )


def build_debug_health_dashboard(language="auto"):
    warnings: list[Any] = []
    session, new_warnings = _safe_call("debug session", get_current_debug_session, None)
    warnings.extend(new_warnings)
    timeline, new_warnings = _safe_call("debug timeline", lambda: get_current_debug_timeline(language=language), {"events": []})
    warnings.extend(new_warnings)
    learning, new_warnings = _safe_call("debug learning summary", lambda: build_debug_learning_summary(language=language), {})
    warnings.extend(new_warnings)
    preflight, new_warnings = _safe_call("debug preflight checklist", lambda: run_preflight_checklist(language=language), {})
    warnings.extend(new_warnings)
    approvals, new_warnings = _safe_call("fix approvals", lambda: list_pending_fix_approvals(limit=20), [])
    warnings.extend(new_warnings)
    audit_events, new_warnings = _safe_call("fix audit log", lambda: list_fix_audit_events(limit=20), [])
    warnings.extend(new_warnings)
    exports, new_warnings = _safe_call("debug exports", lambda: list_debug_exports(limit=20), [])
    warnings.extend(new_warnings)
    reuse, new_warnings = _safe_call("debug reuse suggestions", lambda: build_reuse_suggestions(language=language), {})
    warnings.extend(new_warnings)

    preflight_summary = _preflight_status(preflight)
    warnings.extend(preflight_summary.get("warnings") or [])
    timeline_events = timeline.get("events") if isinstance(timeline, dict) else timeline
    recommended = []
    if not session:
        recommended.append("Start a debug session before troubleshooting a new issue.")
    if approvals:
        recommended.append("Review pending fix approvals and allow or dismiss each one explicitly.")
    recommended.extend(preflight_summary.get("recommended_next_steps") or [])
    if reuse.get("similar_sessions"):
        recommended.append("Review similar past debug sessions before applying a fix.")
    if not recommended:
        recommended.append("Run the debug checklist before making release or troubleshooting changes.")

    payload = {
        "ok": True,
        "overall_ok": bool(preflight_summary.get("ok", True)),
        "language": language or "auto",
        "active_session": _active_session_summary(session),
        "pending_approvals_count": len(approvals or []),
        "recent_audit_count": len(audit_events or []),
        "timeline_count": len(timeline_events or []),
        "learning_summary": learning,
        "preflight_status": preflight_summary,
        "export_count": len(exports or []),
        "reuse_suggestions": {
            "confidence": reuse.get("confidence", "low"),
            "similar_sessions_count": len(reuse.get("similar_sessions") or []),
            "previous_fix_plan_snippets": (reuse.get("previous_fix_plan_snippets") or [])[:3],
            "previous_commands_suggested": (reuse.get("previous_commands_suggested") or [])[:3],
            "no_command_executed": bool(reuse.get("no_command_executed", True)),
        },
        "warnings": warnings,
        "recommended_next_steps": list(dict.fromkeys(_redact_text(item) for item in recommended if _compact_text(item))),
        "no_destructive_action": True,
    }
    payload["compact_status"] = compact_debug_health_status(payload)
    return _redact(payload)


def summarize_debug_health_dashboard(payload, language="auto"):
    payload = payload or {}
    tamil = str(language or payload.get("language") or "").lower() in {"ta", "tamil"}
    status = "OK" if payload.get("overall_ok") else "needs attention"
    if tamil:
        status_text = "seri" if payload.get("overall_ok") else "konjam paarunga"
        prefix = f"Debug dashboard {status_text}."
    else:
        prefix = f"Debug dashboard is {status}."
    parts = [
        prefix,
        f"Pending approvals: {int(payload.get('pending_approvals_count') or 0)}.",
        f"Recent audit events: {int(payload.get('recent_audit_count') or 0)}.",
        f"Timeline events: {int(payload.get('timeline_count') or 0)}.",
        f"Exports: {int(payload.get('export_count') or 0)}.",
    ]
    warnings = payload.get("warnings") or []
    if warnings:
        parts.append(f"Warnings: {len(warnings)}.")
    next_steps = payload.get("recommended_next_steps") or []
    if next_steps:
        parts.append("Next: " + _redact_text(next_steps[0]))
    parts.append("No destructive actions were run.")
    return " ".join(parts)
