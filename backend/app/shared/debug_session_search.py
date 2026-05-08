from __future__ import annotations

import re
from typing import Any

from debug_session import list_debug_sessions


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


def _tokens(query: str) -> list[str]:
    return [token for token in re.split(r"\W+", str(query or "").lower()) if token]


def _append(parts: list[tuple[str, str, int]], field: str, value: Any, weight: int) -> None:
    if isinstance(value, list):
        for item in value:
            _append(parts, field, item, weight)
        return
    if isinstance(value, dict):
        for item in value.values():
            _append(parts, field, item, weight)
        return
    text = _compact_text(value)
    if text:
        parts.append((field, text, weight))


def _session_parts(session: dict[str, Any]) -> list[tuple[str, str, int]]:
    parts: list[tuple[str, str, int]] = []
    _append(parts, "title", session.get("title"), 8)
    _append(parts, "status", session.get("status"), 1)
    for report in session.get("debug_reports", []) or []:
        _append(parts, "debug_report_summary", report.get("summary"), 6)
        _append(parts, "error_text", report.get("error_text"), 5)
        _append(parts, "error_families", report.get("error_families"), 9)
    for plan in session.get("fix_plans", []) or []:
        _append(parts, "fix_plan_summary", plan.get("summary"), 6)
        _append(parts, "safe_checks", plan.get("safe_checks"), 3)
        _append(parts, "suggested_file_checks", plan.get("suggested_file_checks"), 3)
        _append(parts, "suggested_commands", plan.get("suggested_commands"), 4)
    for approval in session.get("fix_approvals", []) or []:
        payload = approval.get("payload") or {}
        _append(parts, "approval_command", payload.get("command") or payload.get("description"), 5)
        _append(parts, "approval_reason", approval.get("reason") or payload.get("reason"), 3)
    for event in session.get("audit_events", []) or []:
        _append(parts, "audit_event", event.get("event_type"), 3)
        _append(parts, "audit_event", event.get("message"), 3)
        _append(parts, "audit_event", event.get("approval"), 3)
    return parts


def build_search_index_text(session):
    return _redact_text(" ".join(text for _field, text, _weight in _session_parts(session or {})))


def _snippet(text: str, tokens: list[str]) -> str:
    lowered = text.lower()
    start = 0
    for token in tokens:
        index = lowered.find(token)
        if index >= 0:
            start = max(0, index - 60)
            break
    return _redact_text(text[start : start + 220])


def match_debug_session(session, query):
    session = session or {}
    query_tokens = _tokens(query)
    if not query_tokens:
        return None
    matched_fields = []
    snippets = []
    score = 0
    for field, text, weight in _session_parts(session):
        lowered = text.lower()
        field_matches = sum(1 for token in query_tokens if token in lowered)
        if field_matches:
            score += field_matches * weight
            matched_fields.append(field)
            snippets.append(_snippet(text, query_tokens))
    if score <= 0:
        return None
    return {
        "session_id": session.get("id"),
        "title": _redact_text(session.get("title") or "Debug session"),
        "status": session.get("status"),
        "updated_at": session.get("updated_at") or session.get("created_at") or "",
        "matched_fields": sorted(set(matched_fields)),
        "snippet": _redact_text(" | ".join(snippets[:3])),
        "score": score,
    }


def search_debug_sessions(query, limit=20, language="auto"):
    try:
        limit_value = max(1, int(limit))
    except Exception:
        limit_value = 20
    results = []
    for session in list_debug_sessions(limit=200):
        match = match_debug_session(session, query)
        if match:
            results.append(match)
    results.sort(key=lambda item: (item.get("score", 0), item.get("updated_at", "")), reverse=True)
    return {
        "ok": True,
        "query": _redact_text(query),
        "language": language or "auto",
        "results": results[:limit_value],
    }


def summarize_debug_search_results(results, language="auto"):
    payload = results if isinstance(results, dict) else {"results": results or []}
    items = payload.get("results") or []
    tamil = str(language or payload.get("language") or "").lower() in {"ta", "tamil"}
    if not items:
        return "Matching debug sessions illa." if tamil else "No matching debug sessions found."
    lines = []
    for item in items[:5]:
        lines.append(
            f"{item.get('session_id')}: {item.get('title')} "
            f"(score {item.get('score')}) - {item.get('snippet')}"
        )
    return ("Debug search results: " if not tamil else "Debug search results: ") + " | ".join(lines)
