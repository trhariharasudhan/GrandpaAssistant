from __future__ import annotations

import datetime
from typing import Any

from screen_awareness import summarize_screen_context
from window_awareness import summarize_active_window


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _looks_tamil(text: str) -> bool:
    raw = str(text or "")
    return any("\u0b80" <= char <= "\u0bff" for char in raw) or any(
        token in raw.lower()
        for token in (" enna ", " pannalam", " sollu", "screen la", "udhavi", "help pann")
    )


def _resolve_language(language: str, text: str = "") -> str:
    requested = str(language or "auto").strip().lower()
    if requested in {"ta", "tamil"}:
        return "ta"
    if requested in {"en", "english"}:
        return "en"
    return "ta" if _looks_tamil(text) else "en"


def _active_window_from_payload(window_payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = window_payload or {}
    active_window = payload.get("active_window")
    if isinstance(active_window, dict):
        return active_window
    return payload


def _screen_has_error(screen_payload: dict[str, Any] | None) -> bool:
    payload = screen_payload or {}
    error_detection = payload.get("error_detection")
    if isinstance(error_detection, dict):
        return bool(error_detection.get("has_error_like_text"))
    return False


def _suggestion(kind: str, has_error: bool, language: str) -> tuple[str, str, str]:
    tamil = language == "ta"
    if kind == "editor" and has_error:
        if tamil:
            return (
                "debug_error",
                "Editor-la error mathiri text irukku. Naan adhai explain panni debugging steps suggest pannalaam.",
                "Active app is an editor and the screen contains error-like text.",
            )
        return (
            "debug_error",
            "I can help explain the error on this editor screen and suggest debugging steps.",
            "Active app is an editor and the screen contains error-like text.",
        )
    if kind == "terminal" and has_error:
        if tamil:
            return (
                "troubleshoot_terminal",
                "Terminal output-la error mathiri irukku. Naan command output-ai troubleshoot panna help pannalaam.",
                "Active app is a terminal and the screen contains error-like text.",
            )
        return (
            "troubleshoot_terminal",
            "I can help troubleshoot the terminal output and explain the likely failure.",
            "Active app is a terminal and the screen contains error-like text.",
        )
    if kind == "browser":
        if tamil:
            return (
                "summarize_page",
                "Browser open irukku. Visible page text-ai short-a summarize panna sollunga.",
                "Active app appears to be a browser.",
            )
        return (
            "summarize_page",
            "I can summarize the visible browser page text or help you understand what is open.",
            "Active app appears to be a browser.",
        )
    if kind == "file_explorer":
        if tamil:
            return (
                "file_help",
                "File Explorer open irukku. Files search, organize, illa folder path explain panna help pannalaam.",
                "Active app appears to be File Explorer.",
            )
        return (
            "file_help",
            "I can help search, organize, or explain the files in this File Explorer window.",
            "Active app appears to be File Explorer.",
        )
    if tamil:
        return (
            "no_strong_suggestion",
            "Ippo strong-a oru next action theriyala. Neenga enna panna try panreenga nu sollunga, naan help pannuren.",
            "No strong screen or window signal is available.",
        )
    return (
        "no_strong_suggestion",
        "No strong suggestion right now. Tell me what you are trying to do, and I can help from here.",
        "No strong screen or window signal is available.",
    )


def suggestion_from_screen_and_window(
    screen_payload: dict[str, Any] | None,
    window_payload: dict[str, Any] | None,
    language: str = "auto",
) -> dict[str, Any]:
    resolved = _resolve_language(language)
    active_window = _active_window_from_payload(window_payload)
    kind = _compact_text(active_window.get("kind")).lower() or "unknown"
    has_error = _screen_has_error(screen_payload)
    action, suggestion, reason = _suggestion(kind, has_error, resolved)
    useful = action != "no_strong_suggestion"
    return {
        "ok": True,
        "language": resolved,
        "action": action,
        "suggestion": suggestion,
        "suggestions": [suggestion],
        "confidence": "medium" if useful else "low",
        "reason": reason,
        "no_action_executed": True,
        "screen": {
            "ok": bool((screen_payload or {}).get("ok")),
            "warning": bool((screen_payload or {}).get("warning")),
            "has_error_like_text": has_error,
        },
        "active_window": {
            "ok": bool(active_window.get("ok")),
            "kind": kind,
            "app_name": _compact_text(active_window.get("app_name")),
            "title": _compact_text(active_window.get("title")),
        },
        "timestamp": _utc_now(),
    }


def build_context_suggestions(language: str = "auto") -> dict[str, Any]:
    resolved = _resolve_language(language, "enna next pannalam" if str(language).lower() in {"ta", "tamil"} else "")
    try:
        screen_payload = summarize_screen_context(language=resolved)
    except Exception as error:
        screen_payload = {"ok": False, "warning": True, "detail": _compact_text(error)}
    try:
        window_payload = summarize_active_window(language=resolved)
    except Exception as error:
        window_payload = {"ok": False, "warning": True, "detail": _compact_text(error)}
    return suggestion_from_screen_and_window(screen_payload, window_payload, language=resolved)


def summarize_context_suggestions(language: str = "auto") -> str:
    payload = build_context_suggestions(language=language)
    return payload.get("suggestion") or "No strong suggestion right now."
