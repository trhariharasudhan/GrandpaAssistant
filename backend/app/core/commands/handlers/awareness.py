from __future__ import annotations

from ..context import CommandContext
from ..result import CommandResult


ACTIVE_WINDOW_COMMANDS = {
    "what app am i in",
    "what app am i using",
    "what window is active",
    "current window",
    "active window",
    "naan enna app use panren",
    "where am i working",
}
CAPTURE_OR_ACTION_PREFIXES = (
    "take ",
    "capture ",
    "scan ",
    "read ",
    "ocr ",
    "detect ",
    "click ",
    "type ",
    "execute ",
    "start ",
    "stop ",
    "open ",
    "run ",
)
CAPTURE_OR_ACTION_COMMANDS = {
    "what is on my screen",
    "explain my screen",
    "screen la enna iruku",
    "read my screen",
    "any error on screen",
    "summarize this screen",
    "what should i do next",
    "suggest next action",
    "context suggestion",
    "enna next pannalam",
    "help me with this screen",
    "what objects do you see",
    "what objects can you see",
    "detected objects",
    "object detection status",
    "what do you see on camera",
}


def handle_awareness_command(command: str, context: CommandContext) -> CommandResult:
    """Handle cached/read-only context awareness summaries only."""
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized in CAPTURE_OR_ACTION_COMMANDS or normalized.startswith(CAPTURE_OR_ACTION_PREFIXES):
        return CommandResult.not_handled()
    if normalized in ACTIVE_WINDOW_COMMANDS:
        language = "ta" if normalized == "naan enna app use panren" else "auto"
        return CommandResult(True, context.active_window_summary(language), route="awareness.active_window")
    return CommandResult.not_handled()
