from __future__ import annotations

from ..context import CommandContext
from ..result import CommandResult
from ..summaries import overlay as overlay_summaries


OVERLAY_STATUS_COMMANDS = {
    "overlay status",
    "overlay summary",
    "quick command overlay status",
}
QUICK_OVERLAY_STATUS_COMMANDS = {
    "quick overlay status",
    "quick overlay summary",
}
PINNED_COMMANDS_COMMANDS = {
    "list pinned commands",
    "show pinned commands",
    "pinned commands",
    "pinned command summary",
}
HOTKEY_STATUS_COMMANDS = {
    "hotkey status",
    "hotkeys status",
    "overlay hotkey status",
    "quick overlay hotkey status",
    "ocr hotkey status",
}
OVERLAY_HELP_COMMANDS = {
    "overlay help",
    "quick overlay help",
    "quick command overlay help",
}
DANGEROUS_PREFIXES = (
    "pin command",
    "unpin command",
    "move pinned command",
    "enable ",
    "disable ",
    "turn on ",
    "turn off ",
    "toggle ",
    "set ",
    "change ",
    "update ",
    "open ",
    "close ",
    "hide ",
    "show quick overlay",
    "show quick command overlay",
    "click ",
    "type ",
)


def handle_overlay_status_command(command: str, context: CommandContext) -> CommandResult:
    """Handle read-only overlay, hotkey, and pinned-command summaries only."""
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()
    if normalized in OVERLAY_STATUS_COMMANDS:
        return CommandResult(True, overlay_summaries.overlay_status_summary(), route="overlay_status.overlay")
    if normalized in QUICK_OVERLAY_STATUS_COMMANDS:
        return CommandResult(True, overlay_summaries.quick_overlay_status_summary(), route="overlay_status.quick_overlay")
    if normalized in PINNED_COMMANDS_COMMANDS:
        return CommandResult(True, overlay_summaries.pinned_commands_summary(), route="overlay_status.pinned_commands")
    if normalized in HOTKEY_STATUS_COMMANDS:
        return CommandResult(True, overlay_summaries.hotkey_status_summary(), route="overlay_status.hotkeys")
    if normalized in OVERLAY_HELP_COMMANDS:
        return CommandResult(True, overlay_summaries.overlay_help_summary(), route="overlay_status.help")
    return CommandResult.not_handled()
