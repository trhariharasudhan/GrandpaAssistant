from __future__ import annotations

import datetime
import json
import os
import re
import uuid
from typing import Any

try:
    from utils.paths import backend_data_path
except Exception:
    backend_data_path = None


DEBUG_SESSIONS_PATH = (
    backend_data_path("debug", "debug_sessions.jsonl")
    if backend_data_path
    else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "debug", "debug_sessions.jsonl"))
)
MAX_TEXT_LENGTH = 1500
_CURRENT_DEBUG_SESSION: dict[str, Any] | None = None

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


def _ensure_dir() -> None:
    os.makedirs(os.path.dirname(DEBUG_SESSIONS_PATH), exist_ok=True)


def _write_snapshot(session: dict[str, Any]) -> None:
    _ensure_dir()
    with open(DEBUG_SESSIONS_PATH, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(_redact(session), ensure_ascii=True, sort_keys=True) + "\n")


def _ensure_current_session(source="auto", language="auto") -> dict[str, Any]:
    session = get_current_debug_session()
    if session:
        return session
    return start_debug_session(title="Debug session", source=source, language=language)


def start_debug_session(title="", source="manual", language="auto"):
    global _CURRENT_DEBUG_SESSION
    now = _utc_now()
    _CURRENT_DEBUG_SESSION = {
        "id": uuid.uuid4().hex[:10],
        "title": _compact_text(title) or "Debug session",
        "source": _compact_text(source) or "manual",
        "language": language or "auto",
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "closed_at": None,
        "note": "",
        "debug_reports": [],
        "fix_plans": [],
        "fix_approvals": [],
        "audit_events": [],
    }
    _write_snapshot(_CURRENT_DEBUG_SESSION)
    return _redact(_CURRENT_DEBUG_SESSION)


def get_current_debug_session():
    if not _CURRENT_DEBUG_SESSION or _CURRENT_DEBUG_SESSION.get("status") != "active":
        return None
    return _redact(_CURRENT_DEBUG_SESSION)


def _attach(kind: str, value: Any):
    global _CURRENT_DEBUG_SESSION
    session = _ensure_current_session(source="auto")
    raw_session = _CURRENT_DEBUG_SESSION
    raw_session[kind].append(_redact(value))
    raw_session[kind] = raw_session[kind][-25:]
    raw_session["updated_at"] = _utc_now()
    _write_snapshot(raw_session)
    return _redact(raw_session)


def attach_debug_report(report):
    return _attach("debug_reports", report)


def attach_fix_plan(plan):
    return _attach("fix_plans", plan)


def attach_fix_approval(approval):
    return _attach("fix_approvals", approval)


def attach_audit_event(event):
    if not get_current_debug_session():
        return None
    return _attach("audit_events", event)


def close_debug_session(status="closed", note=""):
    global _CURRENT_DEBUG_SESSION
    if not _CURRENT_DEBUG_SESSION:
        return None
    _CURRENT_DEBUG_SESSION["status"] = _compact_text(status) or "closed"
    _CURRENT_DEBUG_SESSION["note"] = _redact_text(note)
    _CURRENT_DEBUG_SESSION["closed_at"] = _utc_now()
    _CURRENT_DEBUG_SESSION["updated_at"] = _CURRENT_DEBUG_SESSION["closed_at"]
    snapshot = _redact(_CURRENT_DEBUG_SESSION)
    _write_snapshot(_CURRENT_DEBUG_SESSION)
    _CURRENT_DEBUG_SESSION = None
    return snapshot


def list_debug_sessions(limit=20):
    try:
        limit_value = max(1, int(limit))
    except Exception:
        limit_value = 20
    if not os.path.exists(DEBUG_SESSIONS_PATH):
        return []
    by_id = {}
    with open(DEBUG_SESSIONS_PATH, "r", encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except Exception:
                continue
            if item.get("id"):
                by_id[item["id"]] = item
    return sorted(by_id.values(), key=lambda item: item.get("updated_at", ""), reverse=True)[:limit_value]


def summarize_current_debug_session(language="auto"):
    session = get_current_debug_session()
    tamil = str(language or "").lower() in {"ta", "tamil"}
    if not session:
        return "Active debug session illa." if tamil else "No active debug session."
    return (
        f"Debug session {session.get('id')} is active. "
        f"Reports: {len(session.get('debug_reports', []))}. "
        f"Fix plans: {len(session.get('fix_plans', []))}. "
        f"Approvals: {len(session.get('fix_approvals', []))}. "
        f"Audit events: {len(session.get('audit_events', []))}."
    )


def clear_debug_sessions_for_tests():
    global _CURRENT_DEBUG_SESSION
    _CURRENT_DEBUG_SESSION = None
    if os.path.exists(DEBUG_SESSIONS_PATH):
        os.remove(DEBUG_SESSIONS_PATH)
