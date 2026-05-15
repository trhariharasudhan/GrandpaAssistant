from __future__ import annotations

from ..context import CommandContext
from ..result import CommandResult


LANGUAGE_STATUS_COMMANDS = {
    "language mode status",
    "current language mode",
    "language mode",
}
MEETING_SUMMARY_COMMANDS = {
    "meeting summary",
    "meeting mode summary",
    "show meeting summary",
}
PROACTIVE_SUGGESTION_COMMANDS = {
    "show proactive suggestions",
    "proactive suggestions",
    "assistant suggestions",
}
LEARNING_STATUS_COMMANDS = {
    "learning status",
    "self learning status",
    "self improvement status",
    "what have you learned",
}
DANGEROUS_PREFIXES = (
    "set ",
    "change ",
    "use ",
    "switch ",
    "preview ",
    "test ",
    "capture ",
    "save ",
    "tag ",
    "move ",
    "send ",
    "create ",
    "add ",
    "clear ",
    "delete ",
    "remove ",
    "index ",
    "reindex ",
    "refresh ",
    "update ",
    "enable ",
    "disable ",
    "start ",
    "stop ",
)


def handle_knowledge_services_command(command: str, context: CommandContext) -> CommandResult:
    """Handle read-only language, meeting, RAG, suggestion, and learning summaries."""
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()
    if normalized in LANGUAGE_STATUS_COMMANDS:
        return CommandResult(True, context.language_mode_status_summary(), route="knowledge_services.language")
    if normalized in MEETING_SUMMARY_COMMANDS:
        return CommandResult(True, context.meeting_mode_summary(), route="knowledge_services.meeting")
    if normalized in PROACTIVE_SUGGESTION_COMMANDS:
        return CommandResult(True, context.proactive_suggestions_summary(), route="knowledge_services.proactive")
    if normalized in LEARNING_STATUS_COMMANDS:
        return CommandResult(True, context.learning_status_summary(), route="knowledge_services.learning")
    return CommandResult.not_handled()
