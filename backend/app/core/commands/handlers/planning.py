from __future__ import annotations

from core.commands.context import CommandContext
from core.commands.result import CommandResult


GOOGLE_CALENDAR_STATUS_COMMANDS = {
    "google calendar status",
    "calendar sync status",
}

GOOGLE_CALENDAR_TODAY_COMMANDS = {
    "today in google calendar",
    "google calendar today",
    "today google calendar events",
}

GOOGLE_CALENDAR_UPCOMING_COMMANDS = {
    "upcoming google calendar events",
    "google calendar upcoming events",
}

GOOGLE_CALENDAR_TITLES_COMMANDS = {
    "list google calendar event titles",
    "google calendar titles",
    "show google calendar titles",
}

MUTATING_PLANNING_PREFIXES = (
    "add google calendar event",
    "create google calendar event",
    "schedule google calendar event",
    "delete google calendar event",
    "delete latest google calendar event",
    "remove google calendar event",
    "rename google calendar event",
    "reschedule google calendar event",
    "move google calendar event",
    "update google calendar event",
    "sync google calendar",
    "refresh google calendar",
    "authenticate google",
    "authorize google",
    "create reminder",
    "add reminder",
    "set reminder",
    "delete reminder",
    "update reminder",
    "send notification",
    "notify ",
    "weather",
    "show weather",
    "ai day plan",
    "generate day plan",
)


def _is_mutating_or_external_planning_command(command: str) -> bool:
    return command.startswith(MUTATING_PLANNING_PREFIXES)


def handle_planning_command(
    command: str,
    context: CommandContext,
    *,
    allow_google_calendar: bool = True,
    allow_local_calendar: bool = True,
) -> CommandResult:
    normalized = command.strip().lower()
    if not normalized or _is_mutating_or_external_planning_command(normalized):
        return CommandResult.not_handled()

    if allow_google_calendar:
        if normalized in GOOGLE_CALENDAR_STATUS_COMMANDS:
            return CommandResult(True, context.google_calendar_status_summary(), route="planning.google_calendar_status")
        if normalized in GOOGLE_CALENDAR_TODAY_COMMANDS:
            return CommandResult(True, context.google_calendar_today_summary(), route="planning.google_calendar_today")
        if normalized in GOOGLE_CALENDAR_UPCOMING_COMMANDS:
            return CommandResult(True, context.google_calendar_upcoming_summary(), route="planning.google_calendar_upcoming")
        if normalized in GOOGLE_CALENDAR_TITLES_COMMANDS:
            return CommandResult(True, context.google_calendar_titles_summary(), route="planning.google_calendar_titles")

    if allow_local_calendar:
        reply = context.calendar_query_summary(normalized)
        if reply is not None:
            return CommandResult(True, reply, route="planning.local_calendar")

    return CommandResult.not_handled()
