from __future__ import annotations

import re
from collections import Counter
from typing import Any

from debug_session import list_debug_sessions


KNOWN_ERROR_FAMILIES = {
    "module_not_found",
    "import_error",
    "port_in_use",
    "permission_denied",
    "file_not_found",
    "git",
    "npm_node",
}
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


def _normalized_pattern(value: Any) -> str:
    return _redact_text(_compact_text(value))


def extract_error_family_counts(sessions):
    counter: Counter[str] = Counter()
    for session in sessions or []:
        for report in session.get("debug_reports", []) or []:
            for family in report.get("error_families") or []:
                normalized = _compact_text(family).lower()
                if normalized in KNOWN_ERROR_FAMILIES:
                    counter[normalized] += 1
    return [
        {"family": family, "count": count}
        for family, count in counter.most_common()
    ]


def extract_repeated_fix_patterns(sessions):
    safe_step_counts: Counter[str] = Counter()
    summary_counts: Counter[str] = Counter()
    command_counts: Counter[str] = Counter()
    command_reasons: dict[str, str] = {}
    for session in sessions or []:
        for plan in session.get("fix_plans", []) or []:
            summary = _normalized_pattern(plan.get("summary"))
            if summary:
                summary_counts[summary] += 1
            for step in plan.get("safe_checks") or []:
                pattern = _normalized_pattern(step)
                if pattern:
                    safe_step_counts[pattern] += 1
            for command in plan.get("suggested_commands") or []:
                command_text = _normalized_pattern(command.get("command"))
                if command_text:
                    command_counts[command_text] += 1
                    command_reasons.setdefault(command_text, _redact_text(command.get("reason") or "Previously suggested command."))
    repeated = []
    for text, count in summary_counts.most_common():
        if count > 1:
            repeated.append({"type": "fix_plan_summary", "text": text, "count": count})
    for text, count in safe_step_counts.most_common():
        if count > 1:
            repeated.append({"type": "safe_check", "text": text, "count": count})
    for command, count in command_counts.most_common():
        if count > 1:
            repeated.append({
                "type": "suggested_command",
                "command": command,
                "reason": command_reasons.get(command, ""),
                "count": count,
                "suggestion_only": True,
                "requires_confirmation": True,
            })
    return sorted(repeated, key=lambda item: item.get("count", 0), reverse=True)[:20]


def extract_prevention_suggestions(summary):
    families = {item.get("family"): item.get("count", 0) for item in (summary or {}).get("common_error_families", [])}
    suggestions = []
    if families.get("module_not_found", 0) or families.get("import_error", 0):
        suggestions.append("Keep dependency lists current and verify the active virtual environment before debugging imports.")
    if families.get("port_in_use", 0):
        suggestions.append("Add a port-readiness check before starting backend services.")
    if families.get("permission_denied", 0):
        suggestions.append("Document which folders, ports, or actions need elevated permissions.")
    if families.get("file_not_found", 0):
        suggestions.append("Prefer project-root-relative paths and validate generated files before use.")
    if families.get("git", 0):
        suggestions.append("Check git status before pull/rebase/push workflows and avoid force operations.")
    if families.get("npm_node", 0):
        suggestions.append("Keep Node dependency and script checks separate from backend validation.")
    if not suggestions:
        suggestions.append("Keep recording debug sessions so repeated patterns can emerge safely over time.")
    repeated = (summary or {}).get("repeated_fix_patterns") or []
    if repeated:
        suggestions.append("Turn the most repeated safe checks into a documented preflight checklist.")
    return [_redact_text(item) for item in suggestions[:10]]


def build_debug_learning_summary(limit=100, language="auto"):
    try:
        limit_value = max(1, int(limit))
    except Exception:
        limit_value = 100
    sessions = list_debug_sessions(limit=limit_value)
    summary = {
        "ok": True,
        "language": language or "auto",
        "total_sessions_analyzed": len(sessions),
        "common_error_families": extract_error_family_counts(sessions),
        "repeated_fix_patterns": extract_repeated_fix_patterns(sessions),
        "no_command_executed": True,
    }
    summary["prevention_suggestions"] = extract_prevention_suggestions(summary)
    return summary


def summarize_debug_learning(payload, language="auto"):
    payload = payload or {}
    tamil = str(language or payload.get("language") or "").lower() in {"ta", "tamil"}
    total = int(payload.get("total_sessions_analyzed") or 0)
    if total <= 0:
        return "Debug history-la sessions illa. Innum sessions record pannina patterns kandupidikkalaam." if tamil else "No debug sessions are available yet, so there are no repeated patterns to summarize."
    families = payload.get("common_error_families") or []
    patterns = payload.get("repeated_fix_patterns") or []
    suggestions = payload.get("prevention_suggestions") or []
    parts = [f"Analyzed {total} debug session(s)."]
    if families:
        parts.append("Common errors: " + " | ".join(f"{item['family']} ({item['count']})" for item in families[:5]))
    else:
        parts.append("No repeated known error families yet.")
    if patterns:
        rendered = []
        for item in patterns[:5]:
            rendered.append(item.get("command") or item.get("text") or item.get("type"))
        parts.append("Repeated safe fixes: " + " | ".join(_redact_text(item) for item in rendered if item))
    if suggestions:
        parts.append("Prevention: " + " | ".join(suggestions[:3]))
    parts.append("No commands were run.")
    return " ".join(parts)
