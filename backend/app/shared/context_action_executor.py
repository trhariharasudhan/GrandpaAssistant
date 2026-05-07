from __future__ import annotations

import datetime
from typing import Any

from debug_assistant import build_debug_report, format_debug_report
from screen_awareness import summarize_screen_context


SAFE_READ_ONLY_ACTIONS = {
    "debug_error",
    "troubleshoot_terminal",
    "summarize_page",
    "file_help",
    "no_strong_suggestion",
}


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _looks_tamil(text: str) -> bool:
    raw = str(text or "")
    return any("\u0b80" <= char <= "\u0bff" for char in raw) or any(
        token in raw.lower()
        for token in (" enna ", " pannalam", " pannu", "seri", "sollu", "udhavi")
    )


def _resolve_language(language: str, text: str = "") -> str:
    requested = str(language or "auto").strip().lower()
    if requested in {"ta", "tamil"}:
        return "ta"
    if requested in {"en", "english"}:
        return "en"
    return "ta" if _looks_tamil(text) else "en"


def _screen_payload(language: str) -> dict[str, Any]:
    try:
        return summarize_screen_context(language=language)
    except Exception as error:
        return {
            "ok": False,
            "warning": True,
            "summary": "I cannot read the screen right now.",
            "detail": _compact_text(error),
            "text": "",
            "lines": [],
            "error_detection": {"has_error_like_text": False, "lines": []},
        }


def _preview_lines(payload: dict[str, Any], limit: int = 5) -> list[str]:
    lines = payload.get("lines")
    if isinstance(lines, list):
        clean_lines = [_compact_text(line) for line in lines if _compact_text(line)]
    else:
        clean_lines = [_compact_text(line) for line in str(payload.get("text") or "").splitlines() if _compact_text(line)]
    return clean_lines[:limit]


def _error_lines(payload: dict[str, Any]) -> list[str]:
    error_detection = payload.get("error_detection")
    if isinstance(error_detection, dict):
        lines = error_detection.get("lines")
        if isinstance(lines, list):
            return [_compact_text(line) for line in lines if _compact_text(line)][:5]
    return _preview_lines(payload, limit=3)


def is_safe_read_only_action(action: str | None) -> bool:
    return _compact_text(action).lower() in SAFE_READ_ONLY_ACTIONS


def explain_screen_error(language: str = "auto") -> dict[str, Any]:
    resolved = _resolve_language(language)
    report = build_debug_report(language=resolved)
    message = format_debug_report(report, language=resolved)
    return {
        "ok": bool(report.get("ok")),
        "executed": True,
        "action": "debug_error",
        "read_only": True,
        "message": message,
        "debug_report": report,
        "timestamp": _utc_now(),
    }


def summarize_visible_screen_text(language: str = "auto") -> dict[str, Any]:
    resolved = _resolve_language(language)
    payload = _screen_payload(resolved)
    lines = _preview_lines(payload, limit=6)
    if not payload.get("ok"):
        message = (
            "Ippo screen text-ai summarize panna mudiyala; OCR/screenshot ready illa."
            if resolved == "ta"
            else "I cannot summarize the screen text right now because OCR or screenshot capture is not ready."
        )
    elif lines:
        preview = "; ".join(lines)
        message = (
            f"Screen-la idhu theriyuthu: {preview}"
            if resolved == "ta"
            else f"Here is a short summary of the visible screen text: {preview}"
        )
    else:
        message = (
            "Screen-la readable text romba clear-a theriyala."
            if resolved == "ta"
            else "I cannot see clear readable text on the screen right now."
        )
    return {
        "ok": bool(payload.get("ok")),
        "executed": True,
        "action": "summarize_page",
        "read_only": True,
        "message": message,
        "timestamp": _utc_now(),
    }


def handle_file_explorer_help(language: str = "auto") -> dict[str, Any]:
    resolved = _resolve_language(language)
    message = (
        "File Explorer-ku help panna, neenga file search panna venduma, folder organize panna venduma, illa path explain panna venduma?"
        if resolved == "ta"
        else "I can help with File Explorer safely. Do you want help finding a file, organizing a folder, or understanding the current path?"
    )
    return {
        "ok": True,
        "executed": True,
        "action": "file_help",
        "read_only": True,
        "message": message,
        "timestamp": _utc_now(),
    }


def execute_suggested_action(
    action_payload: dict[str, Any] | None,
    user_confirmation: bool = False,
    language: str = "auto",
) -> dict[str, Any]:
    payload = action_payload or {}
    action = _compact_text(payload.get("action")).lower()
    resolved = _resolve_language(language or payload.get("language", "auto"))
    if not action:
        return {
            "ok": False,
            "executed": False,
            "action": "",
            "message": "Ask me for a suggestion first, then say do it.",
            "timestamp": _utc_now(),
        }
    if not is_safe_read_only_action(action):
        return {
            "ok": False,
            "executed": False,
            "action": action,
            "requires_confirmation": True,
            "message": "That action is not a safe read-only context action, so I will not execute it automatically.",
            "timestamp": _utc_now(),
        }
    if action == "debug_error":
        return explain_screen_error(language=resolved)
    if action == "troubleshoot_terminal":
        result = explain_screen_error(language=resolved)
        result["action"] = "troubleshoot_terminal"
        if resolved == "ta":
            result["message"] = "Terminal troubleshooting: " + result.get("message", "")
        else:
            result["message"] = "Terminal troubleshooting: " + result.get("message", "")
        return result
    if action == "summarize_page":
        return summarize_visible_screen_text(language=resolved)
    if action == "file_help":
        return handle_file_explorer_help(language=resolved)
    message = (
        "Ippo strong-a execute panna safe action illa. Neenga enna panna try panreenga nu sollunga."
        if resolved == "ta"
        else "There is no strong safe action to execute right now. Tell me what you are trying to do."
    )
    return {
        "ok": True,
        "executed": False,
        "action": "no_strong_suggestion",
        "read_only": True,
        "message": message,
        "timestamp": _utc_now(),
    }
