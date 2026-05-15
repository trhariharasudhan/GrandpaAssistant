from __future__ import annotations

from ..context import CommandContext
from ..result import CommandResult


PLANNER_FOCUS_COMMANDS = {
    "planner focus",
    "planner focus summary",
    "today focus suggestions",
    "focus suggestions",
    "what should i focus on today",
}
REMINDER_TIMELINE_COMMANDS = {
    "reminder timeline",
    "today reminder timeline",
    "upcoming reminder timeline",
}
HABIT_DASHBOARD_COMMANDS = {
    "habit dashboard",
    "habit summary",
    "show habit dashboard",
    "habit status",
}
GOAL_DASHBOARD_COMMANDS = {
    "goal board",
    "goal board summary",
    "goal summary",
    "show goals",
}
SMART_REMINDER_COMMANDS = {
    "smart reminder priority",
    "smart reminders",
    "prioritize reminders",
    "reminder priority",
}
AUTOMATION_HISTORY_COMMANDS = {
    "automation history",
    "automation run history",
    "show automation history",
}
MOBILE_STATUS_COMMANDS = {
    "mobile companion status",
    "mobile status",
    "show mobile companion status",
}
DANGEROUS_PREFIXES = (
    "add ",
    "create ",
    "delete ",
    "remove ",
    "update ",
    "change ",
    "edit ",
    "complete ",
    "finish ",
    "mark ",
    "run ",
    "execute ",
    "test ",
    "enable ",
    "disable ",
    "setup ",
    "set up ",
    "connect ",
    "send ",
)


def handle_productivity_command(command: str, context: CommandContext) -> CommandResult:
    """Handle read-only productivity and automation summary commands only."""
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()
    if normalized in PLANNER_FOCUS_COMMANDS:
        return CommandResult(True, context.planner_focus_summary(), route="productivity.planner_focus")
    if normalized in REMINDER_TIMELINE_COMMANDS:
        return CommandResult(True, context.reminder_timeline_summary(), route="productivity.reminder_timeline")
    if normalized in HABIT_DASHBOARD_COMMANDS:
        return CommandResult(True, context.habit_dashboard_summary(), route="productivity.habit_dashboard")
    if normalized in GOAL_DASHBOARD_COMMANDS:
        return CommandResult(True, context.goal_board_summary(), route="productivity.goal_board")
    if normalized in SMART_REMINDER_COMMANDS:
        return CommandResult(True, context.smart_reminder_priority_summary(), route="productivity.smart_reminders")
    if normalized in AUTOMATION_HISTORY_COMMANDS:
        return CommandResult(True, context.automation_history_summary(), route="productivity.automation_history")
    if normalized in MOBILE_STATUS_COMMANDS:
        return CommandResult(True, context.mobile_companion_status_summary(), route="productivity.mobile_status")
    return CommandResult.not_handled()
