from __future__ import annotations

import datetime
import os
import re
from typing import Any

try:
    from system import window_context_module
except Exception:
    window_context_module = None

try:
    import win32gui
    import win32process
    import psutil
except Exception:
    win32gui = None
    win32process = None
    psutil = None


BROWSER_HINTS = ("chrome", "edge", "msedge", "firefox", "brave", "opera", "browser", "safari")
EDITOR_HINTS = ("visual studio code", "vscode", "code.exe", "pycharm", "notepad++", "sublime", "vim", "emacs", "cursor")
TERMINAL_HINTS = ("powershell", "pwsh", "cmd", "terminal", "windows terminal", "console", "bash", "wsl")
EXPLORER_HINTS = ("file explorer", "explorer.exe", "explorer")
MEDIA_HINTS = ("youtube", "spotify", "netflix", "prime video", "hotstar", "vlc")
FOOD_HINTS = ("swiggy", "zomato", "food delivery")


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _looks_tamil(text: str) -> bool:
    raw = str(text or "")
    return any("\u0b80" <= char <= "\u0bff" for char in raw) or any(
        token in raw.lower()
        for token in (" enna ", " panren", " use panren", " iruku", " enga work")
    )


def _resolve_language(language: str, text: str = "") -> str:
    requested = str(language or "auto").strip().lower()
    if requested in {"ta", "tamil"}:
        return "ta"
    if requested in {"en", "english"}:
        return "en"
    return "ta" if _looks_tamil(text) else "en"


def _warning(detail: str, *, language: str = "en") -> dict[str, Any]:
    resolved = _resolve_language(language)
    message = (
        "செயலில் உள்ள window விவரம் இப்போது கிடைக்கவில்லை."
        if resolved == "ta"
        else "I cannot detect the active window right now."
    )
    return {
        "ok": False,
        "warning": True,
        "message": message,
        "detail": _compact_text(detail),
        "timestamp": _utc_now(),
    }


def _process_name_from_active_window() -> str:
    if win32gui is None or win32process is None or psutil is None:
        return ""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return ""
        _thread_id, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return ""
        return _compact_text(psutil.Process(pid).name())
    except Exception:
        return ""


def _infer_kind(title: str, app_name: str = "", process_name: str = "") -> str:
    app_process = " ".join([app_name, process_name]).lower()
    title_text = str(title or "").lower()
    if any(hint in app_process for hint in EDITOR_HINTS):
        return "editor"
    if any(hint in app_process for hint in BROWSER_HINTS):
        return "browser"
    if any(hint in app_process for hint in TERMINAL_HINTS):
        return "terminal"
    if any(hint in app_process for hint in EXPLORER_HINTS):
        return "file_explorer"
    if any(hint in title_text for hint in BROWSER_HINTS):
        return "browser"
    if any(hint in title_text for hint in EDITOR_HINTS):
        return "editor"
    if any(hint in title_text for hint in TERMINAL_HINTS):
        return "terminal"
    if any(hint in title_text for hint in EXPLORER_HINTS):
        return "file_explorer"
    return "unknown"


def _infer_domain(title: str) -> str:
    text = str(title or "").lower()
    match = re.search(r"\b([a-z0-9-]+\.(?:com|in|org|net|io|ai|dev))\b", text)
    if match:
        return match.group(1)
    for domain in ("youtube.com", "spotify.com", "swiggy.com", "zomato.com", "google.com"):
        if domain.split(".", 1)[0] in text:
            return domain
    return ""


def _infer_activity(kind: str, title: str, app_name: str, process_name: str) -> str:
    haystack = " ".join([str(kind or ""), str(title or ""), str(app_name or ""), str(process_name or "")]).lower()
    if kind == "editor" or any(token in haystack for token in ("visual studio code", "vscode", ".py", ".js", ".ts")):
        return "coding"
    if any(token in haystack for token in MEDIA_HINTS):
        return "media"
    if any(token in haystack for token in FOOD_HINTS):
        return "food_ordering"
    if kind == "browser":
        return "browsing"
    if kind == "terminal":
        return "terminal"
    return kind or "unknown"


def get_active_window_context() -> dict[str, Any]:
    if window_context_module is None:
        return _warning("Window context helper is not available.")
    try:
        info = window_context_module.get_active_window_info()
    except Exception as error:
        return _warning(str(error) or "Window context helper failed.")
    if not info:
        return _warning("No active window was reported.")

    title = _compact_text(info.get("title")) or "Unknown window"
    app_name = _compact_text(info.get("app_name")) or "Unknown application"
    process_name = _process_name_from_active_window()
    kind = _infer_kind(title, app_name, process_name)
    domain = _infer_domain(title)
    activity = _infer_activity(kind, title, app_name, process_name)
    return {
        "ok": True,
        "warning": False,
        "title": title,
        "app_name": app_name,
        "app_key": _compact_text(info.get("app_key")).lower(),
        "process_name": process_name,
        "kind": kind,
        "domain": domain,
        "activity": activity,
        "is_browser": kind == "browser",
        "is_editor": kind == "editor",
        "is_terminal": kind == "terminal",
        "is_file_explorer": kind == "file_explorer",
        "timestamp": _utc_now(),
    }


def detect_browser_context(context: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = context or get_active_window_context()
    return {**payload, "matched": bool(payload.get("ok") and payload.get("kind") == "browser")}


def detect_editor_context(context: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = context or get_active_window_context()
    return {**payload, "matched": bool(payload.get("ok") and payload.get("kind") == "editor")}


def detect_terminal_context(context: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = context or get_active_window_context()
    return {**payload, "matched": bool(payload.get("ok") and payload.get("kind") == "terminal")}


def _kind_label(kind: str) -> str:
    return {
        "browser": "a browser",
        "editor": "a code editor",
        "terminal": "a terminal",
        "file_explorer": "File Explorer",
    }.get(kind, "an application")


def summarize_active_window(language: str = "auto") -> dict[str, Any]:
    context = get_active_window_context()
    resolved = _resolve_language(language, "naan enna app use panren" if str(language).lower() in {"ta", "tamil"} else "")
    if not context.get("ok"):
        warning = _warning(context.get("detail") or context.get("message"), language=resolved)
        return {**warning, "language": resolved, "active_window": safe_window_context_payload(context)}
    kind = context.get("kind", "unknown")
    if resolved == "ta":
        summary = f"நீங்கள் இப்போது {context.get('app_name')} பயன்படுத்துகிறீர்கள். Window title: {context.get('title')}."
        if kind != "unknown":
            summary += f" இது {_kind_label(kind)} போல தெரிகிறது."
    else:
        summary = f"You are currently using {context.get('app_name')}. The active window title is {context.get('title')}."
        if kind != "unknown":
            summary += f" It looks like {_kind_label(kind)}."
    return {
        "ok": True,
        "warning": False,
        "language": resolved,
        "summary": summary,
        "active_window": safe_window_context_payload(context),
        "timestamp": context.get("timestamp"),
    }


def safe_window_context_payload(context: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = context or get_active_window_context()
    if not payload.get("ok"):
        return {
            "ok": False,
            "warning": True,
            "detail": _compact_text(payload.get("detail") or payload.get("message")),
            "timestamp": payload.get("timestamp") or _utc_now(),
        }
    return {
        "ok": True,
        "title": _compact_text(payload.get("title")),
        "app_name": _compact_text(payload.get("app_name")),
        "process_name": os.path.basename(_compact_text(payload.get("process_name"))),
        "kind": _compact_text(payload.get("kind")) or "unknown",
        "domain": _compact_text(payload.get("domain")),
        "activity": _compact_text(payload.get("activity")),
        "is_browser": bool(payload.get("is_browser")),
        "is_editor": bool(payload.get("is_editor")),
        "is_terminal": bool(payload.get("is_terminal")),
        "is_file_explorer": bool(payload.get("is_file_explorer")),
        "timestamp": payload.get("timestamp") or _utc_now(),
    }
