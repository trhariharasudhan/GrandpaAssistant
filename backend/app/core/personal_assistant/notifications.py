from __future__ import annotations

import logging
from typing import Any

from .context import compact_text


logger = logging.getLogger(__name__)


def build_reminder_notification_text(reminder: dict[str, Any]) -> str:
    title = compact_text(reminder.get("title") or reminder.get("topic")) or "Untitled reminder"
    due_label = compact_text(reminder.get("due_label"))
    if due_label:
        return f"Reminder: {title} at {due_label}."
    return f"Reminder: {title}."


def deliver_reminder_notification(reminder: dict[str, Any], *, use_windows_toast: bool = True) -> dict[str, Any]:
    """Deliver a local reminder notification with a safe logging fallback."""

    message = build_reminder_notification_text(reminder)
    toast_error = ""
    if use_windows_toast:
        try:
            from winotify import Notification  # type: ignore

            notification = Notification(app_id="GrandpaAssistant", title="GrandpaAssistant Reminder", msg=message)
            notification.show()
            return {"ok": True, "channel": "windows_toast", "message": message, "error": ""}
        except Exception as error:  # pragma: no cover - depends on optional local package/OS state
            toast_error = compact_text(error)

    logger.info("GrandpaAssistant reminder notification: %s", message)
    return {"ok": True, "channel": "log", "message": message, "error": toast_error}
