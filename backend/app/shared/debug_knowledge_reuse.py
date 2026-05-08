from __future__ import annotations

import re
from typing import Any

from debug_session import get_current_debug_session, list_debug_sessions
from debug_session_search import search_debug_sessions


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


def _session_by_id() -> dict[str, dict[str, Any]]:
    return {item.get("id"): item for item in list_debug_sessions(limit=200) if item.get("id")}


def extract_reuse_query_from_report(report):
    report = report or {}
    parts = []
    parts.extend(str(item) for item in report.get("error_families") or [] if item)
    for key in ("summary", "error_text"):
        value = _compact_text(report.get(key))
        if value:
            parts.append(value[:300])
    active_window = report.get("active_window") or {}
    kind = _compact_text(active_window.get("kind"))
    if kind:
        parts.append(kind)
    return _redact_text(" ".join(parts))


def _fix_plan_snippets(session: dict[str, Any]) -> list[str]:
    snippets = []
    for plan in session.get("fix_plans", []) or []:
        text = _compact_text(plan.get("summary"))
        if text:
            snippets.append(_redact_text(text))
        for check in (plan.get("safe_checks") or [])[:3]:
            snippets.append(_redact_text(check))
    return snippets[:5]


def _suggested_commands(session: dict[str, Any]) -> list[dict[str, Any]]:
    commands = []
    for plan in session.get("fix_plans", []) or []:
        for item in (plan.get("suggested_commands") or [])[:5]:
            command = _compact_text(item.get("command"))
            if command:
                commands.append({
                    "command": _redact_text(command),
                    "reason": _redact_text(item.get("reason") or "Previously suggested command."),
                    "suggestion_only": True,
                    "requires_confirmation": True,
                })
    return commands[:8]


def find_similar_debug_sessions(report=None, query="", limit=5, language="auto"):
    search_query = _compact_text(query) or extract_reuse_query_from_report(report or {})
    if not search_query:
        return {"ok": True, "query": "", "similar_sessions": [], "no_command_executed": True}
    current_id = (get_current_debug_session() or {}).get("id")
    search_payload = search_debug_sessions(search_query, limit=max(int(limit or 5) + 3, 8), language=language)
    sessions = _session_by_id()
    similar = []
    for item in search_payload.get("results", []):
        if current_id and item.get("session_id") == current_id:
            continue
        session = sessions.get(item.get("session_id")) or {}
        enriched = {
            **item,
            "previous_fix_plan_snippets": _fix_plan_snippets(session),
            "previous_commands_suggested": _suggested_commands(session),
        }
        similar.append(enriched)
        if len(similar) >= int(limit or 5):
            break
    return {
        "ok": True,
        "query": _redact_text(search_query),
        "similar_sessions": similar,
        "no_command_executed": True,
    }


def build_reuse_suggestions(report=None, language="auto"):
    similar_payload = find_similar_debug_sessions(report=report, limit=5, language=language)
    similar = similar_payload.get("similar_sessions") or []
    fix_snippets = []
    commands = []
    for item in similar:
        fix_snippets.extend(item.get("previous_fix_plan_snippets") or [])
        commands.extend(item.get("previous_commands_suggested") or [])
    confidence = "high" if similar and (fix_snippets or commands) else "medium" if similar else "low"
    return {
        "ok": True,
        "query": similar_payload.get("query", ""),
        "similar_sessions": similar,
        "previous_fix_plan_snippets": fix_snippets[:8],
        "previous_commands_suggested": commands[:8],
        "confidence": confidence,
        "no_command_executed": True,
    }


def summarize_reuse_suggestions(payload, language="auto"):
    payload = payload or {}
    tamil = str(language or "").lower() in {"ta", "tamil"}
    similar = payload.get("similar_sessions") or []
    if not similar:
        return "Similar old debug history kidaikkala." if tamil else "I did not find a similar previous debug session."
    pieces = []
    for item in similar[:3]:
        pieces.append(f"{item.get('session_id')}: {item.get('title')} - {item.get('snippet')}")
    extra = ""
    snippets = payload.get("previous_fix_plan_snippets") or []
    if snippets:
        extra = " Previous fix hint: " + snippets[0]
    commands = payload.get("previous_commands_suggested") or []
    if commands:
        extra += " Suggested previously, not executed now: " + commands[0].get("command", "")
    return ("Similar debug history: " if not tamil else "Similar debug history: ") + " | ".join(pieces) + extra
