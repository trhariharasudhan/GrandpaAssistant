from __future__ import annotations

import re
from typing import Any

try:
    from shared import window_awareness
except ImportError:  # pragma: no cover - direct script import shape
    import window_awareness  # type: ignore

try:
    from shared import screen_awareness
except Exception:  # pragma: no cover - optional OCR/screenshot stack may be absent
    try:
        import screen_awareness  # type: ignore
    except Exception:  # pragma: no cover
        screen_awareness = None

from .context import compact_text


MEDIA_HINTS = ("youtube", "spotify", "netflix", "prime video", "hotstar", "vlc", "music", "video")
FOOD_HINTS = ("swiggy", "zomato", "ubereats", "food delivery")
CHAT_HINTS = ("whatsapp", "telegram", "slack", "teams", "discord", "chat")
SHOPPING_HINTS = ("amazon", "flipkart", "cart", "checkout", "payment")


def _domain_from_title(title: str) -> str:
    cleaned = compact_text(title).lower()
    match = re.search(r"\b([a-z0-9-]+\.(?:com|in|org|net|io|ai|dev))\b", cleaned)
    if match:
        return match.group(1)
    for domain in ("youtube.com", "spotify.com", "swiggy.com", "zomato.com", "google.com"):
        if domain.split(".", 1)[0] in cleaned:
            return domain
    return ""


def _activity_from_window(active_window: dict[str, Any]) -> str:
    title = compact_text(active_window.get("title")).lower()
    app_name = compact_text(active_window.get("app_name")).lower()
    kind = compact_text(active_window.get("kind")).lower()
    haystack = " ".join([title, app_name, kind])
    if kind == "editor" or any(token in haystack for token in ("visual studio code", "vscode", "pycharm", "cursor", ".py", ".js", ".ts")):
        return "coding"
    if any(token in haystack for token in MEDIA_HINTS):
        return "media"
    if any(token in haystack for token in FOOD_HINTS):
        return "food_ordering"
    if any(token in haystack for token in CHAT_HINTS):
        return "chatting"
    if any(token in haystack for token in SHOPPING_HINTS):
        return "shopping"
    if kind == "browser":
        return "browsing"
    if kind == "terminal":
        return "terminal"
    return kind or "unknown"


def get_screen_context(*, include_screenshot: bool = False, language: str = "auto") -> dict[str, Any]:
    try:
        window_payload = window_awareness.safe_window_context_payload()
    except Exception as error:
        window_payload = {"ok": False, "warning": True, "detail": compact_text(error)}

    activity = _activity_from_window(window_payload) if window_payload.get("ok") else "unknown"
    context = {
        "active_window": {
            "ok": bool(window_payload.get("ok")),
            "app_name": compact_text(window_payload.get("app_name")),
            "title": compact_text(window_payload.get("title")),
            "kind": compact_text(window_payload.get("kind")) or "unknown",
            "domain": _domain_from_title(compact_text(window_payload.get("title"))),
            "activity": activity,
        },
        "screen_context": {
            "activity": activity,
            "source": "active_window" if window_payload.get("ok") else "unavailable",
        },
        "screenshot": None,
    }
    if include_screenshot:
        if screen_awareness is None:
            screen_payload = {"ok": False, "summary": "I cannot read the screen right now.", "detail": "screen awareness adapter unavailable", "lines": []}
        else:
            try:
                screen_payload = screen_awareness.summarize_screen_context(language=language)
            except Exception as error:
                screen_payload = {"ok": False, "summary": "I cannot read the screen right now.", "detail": compact_text(error), "lines": []}
        context["screenshot"] = {
            "ok": bool(screen_payload.get("ok")),
            "summary": compact_text(screen_payload.get("summary") or screen_payload.get("message")),
            "line_count": len(screen_payload.get("lines") or []),
            "error_like": bool((screen_payload.get("error_detection") or {}).get("has_error_like_text")),
        }
    return context


def summarize_for_debug(screen_context: dict[str, Any] | None) -> dict[str, Any]:
    payload = screen_context if isinstance(screen_context, dict) else {}
    active = payload.get("active_window") if isinstance(payload.get("active_window"), dict) else {}
    screenshot = payload.get("screenshot") if isinstance(payload.get("screenshot"), dict) else None
    return {
        "active_window": {
            "ok": bool(active.get("ok")),
            "app_name": compact_text(active.get("app_name")),
            "kind": compact_text(active.get("kind")),
            "domain": compact_text(active.get("domain")),
            "activity": compact_text(active.get("activity")),
        },
        "screenshot": screenshot,
    }
