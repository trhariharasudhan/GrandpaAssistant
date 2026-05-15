from __future__ import annotations

from ..context import CommandContext
from ..result import CommandResult
from ..summaries import notification as notification_summaries


NOTIFICATION_STATUS_COMMANDS = {
    "notification status",
    "notifications status",
    "show notification status",
    "notification summary",
    "notifications summary",
}
NOTIFICATION_HELP_COMMANDS = {
    "notification help",
    "notifications help",
    "popup help",
    "alert help",
}
POPUP_ALERT_STATUS_COMMANDS = {
    "popup status",
    "popup alert status",
    "alert popup status",
    "popup summary",
    "alert status summary",
}
REMINDER_NOTIFICATION_COMMANDS = {
    "reminder notification summary",
    "reminder notification status",
    "reminder popup status",
    "event notification status",
}
NOTIFICATION_HISTORY_COMMANDS = {
    "notification history",
    "notification list",
    "show notification history",
    "show notifications",
    "recent notifications",
}
DANGEROUS_PREFIXES = (
    "send ",
    "show popup",
    "show alert",
    "create ",
    "add ",
    "update ",
    "change ",
    "delete ",
    "remove ",
    "enable ",
    "disable ",
    "turn on ",
    "turn off ",
    "set ",
    "clear ",
)


def handle_notification_status_command(command: str, context: CommandContext) -> CommandResult:
    """Handle read-only notification, popup, and reminder-notification summaries."""
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()
    if normalized in NOTIFICATION_STATUS_COMMANDS:
        return CommandResult(True, notification_summaries.notification_status_summary(), route="notification_status.summary")
    if normalized in NOTIFICATION_HELP_COMMANDS:
        return CommandResult(True, notification_summaries.notification_help_summary(), route="notification_status.help")
    if normalized in POPUP_ALERT_STATUS_COMMANDS:
        return CommandResult(True, notification_summaries.popup_alert_status_summary(), route="notification_status.popup_alerts")
    if normalized in REMINDER_NOTIFICATION_COMMANDS:
        return CommandResult(True, notification_summaries.reminder_notification_summary(), route="notification_status.reminders")
    if normalized in NOTIFICATION_HISTORY_COMMANDS:
        return CommandResult(True, notification_summaries.notification_history_summary(), route="notification_status.history")
    return CommandResult.not_handled()
