from __future__ import annotations

import datetime
import os
import re
from typing import Any

from debug_session import get_current_debug_session, list_debug_sessions

try:
    from utils.paths import backend_data_path
except Exception:
    backend_data_path = None


DEBUG_EXPORTS_DIR = (
    backend_data_path("debug", "exports")
    if backend_data_path
    else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "debug", "exports"))
)
MAX_TEXT_LENGTH = 1500
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
        output = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in ("password", "token", "secret", "credential", "api_key", "apikey")):
                output[key] = "[REDACTED]"
            else:
                output[key] = _redact(item)
        return output
    if isinstance(value, list):
        return [_redact(item) for item in value[:60]]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _ensure_export_dir() -> None:
    os.makedirs(DEBUG_EXPORTS_DIR, exist_ok=True)


def _line(value: Any, fallback: str = "") -> str:
    return _redact_text(_compact_text(value) or fallback)


def _bullet_lines(items: list[Any], formatter) -> list[str]:
    if not items:
        return ["- None recorded."]
    return [f"- {formatter(item)}" for item in items[:20]]


def safe_export_filename(session) -> str:
    session = session or {}
    session_id = re.sub(r"[^A-Za-z0-9_-]+", "-", str(session.get("id") or "debug-session")).strip("-")
    timestamp = re.sub(r"[^0-9TZ]+", "", str(session.get("updated_at") or _utc_now()))[:15]
    return f"debug-session-{session_id}-{timestamp}.md"


def build_debug_session_markdown(session) -> str:
    session = _redact(session or {})
    lines = [
        "# GrandpaAssistant Debug Session Report",
        "",
        "Safety note: No commands were run unless shown in audit events.",
        "Safety note: This export does not include raw screenshots or binary data.",
        "",
        "## Session",
        f"- ID: {_line(session.get('id'), 'unknown')}",
        f"- Title: {_line(session.get('title'), 'Debug session')}",
        f"- Status: {_line(session.get('status'), 'unknown')}",
        f"- Source: {_line(session.get('source'), 'unknown')}",
        f"- Created: {_line(session.get('created_at'), 'unknown')}",
        f"- Updated: {_line(session.get('updated_at'), 'unknown')}",
        "",
        "## Debug Reports",
    ]
    lines.extend(_bullet_lines(session.get("debug_reports") or [], lambda item: _line(item.get("summary") or item.get("error_text"), "Debug report")))
    lines.extend(["", "## Fix Plans"])
    lines.extend(_bullet_lines(session.get("fix_plans") or [], lambda item: _line(item.get("summary"), "Fix plan")))
    lines.extend(["", "## Approvals"])
    lines.extend(
        _bullet_lines(
            session.get("fix_approvals") or [],
            lambda item: _line(
                f"{item.get('id')}: {((item.get('payload') or {}).get('command') or (item.get('payload') or {}).get('description') or item.get('action_type'))}",
                "Fix approval",
            ),
        )
    )
    lines.extend(["", "## Audit Events"])
    lines.extend(
        _bullet_lines(
            session.get("audit_events") or [],
            lambda item: _line(
                f"{item.get('timestamp')} {item.get('event_type')}: {((item.get('approval') or {}).get('command') or item.get('message'))}",
                "Audit event",
            ),
        )
    )
    lines.extend(
        [
            "",
            "## Safety Notes",
            "- Secrets, tokens, passwords, credentials, and long text are redacted or truncated.",
            "- Suggested commands in fix plans are suggestions only unless an audit event records an approved execution.",
            "- No screenshots or raw binary data are exported.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_markdown(session) -> dict[str, Any]:
    _ensure_export_dir()
    filename = safe_export_filename(session)
    path = os.path.join(DEBUG_EXPORTS_DIR, filename)
    markdown = build_debug_session_markdown(session)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(markdown)
    return {
        "ok": True,
        "format": "markdown",
        "path": path,
        "filename": filename,
        "session_id": (session or {}).get("id"),
        "created_at": _utc_now(),
    }


def export_current_debug_session(format="markdown"):
    if str(format or "markdown").lower() != "markdown":
        return {"ok": False, "message": "Only markdown export is supported."}
    session = get_current_debug_session()
    if not session:
        sessions = list_debug_sessions(limit=1)
        session = sessions[0] if sessions else None
    if not session:
        return {"ok": False, "message": "No debug session is available to export."}
    return _write_markdown(session)


def export_debug_session(session_id, format="markdown"):
    if str(format or "markdown").lower() != "markdown":
        return {"ok": False, "message": "Only markdown export is supported."}
    target = _compact_text(session_id)
    session = next((item for item in list_debug_sessions(limit=200) if item.get("id") == target), None)
    if not session:
        return {"ok": False, "message": "Debug session was not found."}
    return _write_markdown(session)


def list_debug_exports(limit=20):
    try:
        limit_value = max(1, int(limit))
    except Exception:
        limit_value = 20
    if not os.path.isdir(DEBUG_EXPORTS_DIR):
        return []
    items = []
    for name in os.listdir(DEBUG_EXPORTS_DIR):
        path = os.path.join(DEBUG_EXPORTS_DIR, name)
        if not os.path.isfile(path) or not name.lower().endswith(".md"):
            continue
        stat = os.stat(path)
        items.append({
            "filename": name,
            "path": path,
            "size": stat.st_size,
            "modified_at": datetime.datetime.utcfromtimestamp(stat.st_mtime).isoformat(timespec="seconds") + "Z",
        })
    return sorted(items, key=lambda item: item["modified_at"], reverse=True)[:limit_value]
