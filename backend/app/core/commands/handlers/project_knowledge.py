from __future__ import annotations

from core.commands.context import CommandContext
from core.commands.result import CommandResult


RAG_LIBRARY_COMMANDS = {
    "rag library",
    "rag library summary",
    "show rag library",
}

KNOWLEDGE_REVIEW_COMMANDS = {
    "show knowledge review queue",
    "knowledge misses",
}

STORAGE_STATUS_COMMANDS = {
    "storage status",
    "disk space",
    "storage report",
}

STORAGE_CLEANUP_COMMANDS = {
    "storage cleanup suggestion",
    "cleanup suggestion",
    "how should i clean storage",
}

MUTATING_PROJECT_KNOWLEDGE_PREFIXES = (
    "add knowledge answer",
    "clear knowledge review item",
    "delete knowledge",
    "remove knowledge",
    "index ",
    "reindex ",
    "refresh index",
    "write embedding",
    "build embedding",
    "create file",
    "edit file",
    "delete file",
    "move file",
    "rename file",
    "tag document",
    "move document",
    "send document",
    "ask document",
    "search document",
)


def handle_project_knowledge_command(
    command: str,
    context: CommandContext,
    *,
    allow_library: bool = True,
    allow_storage: bool = True,
) -> CommandResult:
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized or normalized.startswith(MUTATING_PROJECT_KNOWLEDGE_PREFIXES):
        return CommandResult.not_handled()

    if allow_library:
        if normalized in RAG_LIBRARY_COMMANDS:
            return CommandResult(True, context.rag_library_summary(), route="project_knowledge.rag_library")
        if normalized in KNOWLEDGE_REVIEW_COMMANDS:
            return CommandResult(True, context.knowledge_review_queue_summary(), route="project_knowledge.review")

    if allow_storage:
        if normalized in STORAGE_STATUS_COMMANDS:
            return CommandResult(
                True,
                context.storage_report_summary(),
                route="project_knowledge.storage_report",
                metadata={"set_last_result": True},
            )
        if normalized in STORAGE_CLEANUP_COMMANDS:
            return CommandResult(
                True,
                context.storage_cleanup_suggestion_summary(),
                route="project_knowledge.storage_cleanup",
                metadata={"set_last_result": True},
            )

    return CommandResult.not_handled()
