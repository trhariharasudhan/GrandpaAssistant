from __future__ import annotations

import re
from collections.abc import Callable

from ..context import CommandContext
from ..result import CommandResult


NAME_QUERY_COMMANDS = ("what is my name", "who am i", "tell my name")
SEMANTIC_STATUS_COMMANDS = {
    "semantic memory status",
    "memory semantic status",
    "semantic search status",
}
DANGEROUS_PREFIXES = (
    "clear memory",
    "delete",
    "remove",
    "shutdown",
    "shut down",
    "restart",
    "sleep",
    "sign out",
    "logout",
    "lock",
    "open ",
    "start ",
    "launch ",
)


def handle_memory_command(
    command: str,
    context: CommandContext | None = None,
    *,
    get_memory: Callable[[str], str | None] | None = None,
    set_memory: Callable[[str, str], object] | None = None,
    semantic_memory_summary: Callable[[], str] | None = None,
    semantic_memory_lookup: Callable[[str], str] | None = None,
    allow_personal: bool = True,
    allow_semantic: bool = True,
) -> CommandResult:
    """Handle low-risk memory commands without owning destructive memory actions."""
    if context is not None:
        get_memory = context.get_memory
        set_memory = context.set_memory
        semantic_memory_summary = context.semantic_memory_summary
        semantic_memory_lookup = context.semantic_memory_lookup
    if get_memory is None or set_memory is None or semantic_memory_summary is None or semantic_memory_lookup is None:
        raise ValueError("Memory handler requires command context or callbacks.")
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()

    if allow_personal:
        if "my name is" in normalized:
            name = normalized.replace("my name is", "").strip()
            set_memory("personal.identity.name", name)
            return CommandResult(True, f"Okay, I will remember that your name is {name}", route="memory.save_name")

        if any(pattern in normalized for pattern in NAME_QUERY_COMMANDS):
            name = get_memory("personal.identity.name")
            if name:
                return CommandResult(True, f"You are {name}", route="memory.read_name")
            return CommandResult(True, "I don't know your name yet.", route="memory.read_name")

    if allow_semantic:
        if normalized in SEMANTIC_STATUS_COMMANDS:
            reply = semantic_memory_summary()
            return CommandResult(True, reply, route="memory.semantic_status", metadata={"set_last_result": True})

        semantic_search_match = re.match(
            r"^(?:search|find|look\s+up)\s+(?:my\s+)?memory\s+(?:for\s+)?(.+)$",
            normalized,
        )
        if semantic_search_match:
            reply = semantic_memory_lookup(semantic_search_match.group(1).strip())
            return CommandResult(True, reply, route="memory.semantic_search", metadata={"set_last_result": True})

    return CommandResult.not_handled()
