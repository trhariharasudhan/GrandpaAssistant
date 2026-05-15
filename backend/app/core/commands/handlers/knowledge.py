from __future__ import annotations

from collections.abc import Callable

from ..context import CommandContext
from ..result import CommandResult


GREETING_COMMANDS = {
    "hi",
    "hello",
    "hey",
    "hi odin",
    "hello odin",
    "hey odin",
    "hi grandpa",
    "hello grandpa",
    "hey grandpa",
}

PERIOD_WORDS = ("morning", "afternoon", "evening", "night")
WIKIPEDIA_PREFIXES = (
    "who is",
    "who was",
    "what is",
    "what are",
    "tell me about",
    "how is",
    "how are",
    "latest about",
    "latest on",
    "news about",
)
DANGEROUS_PREFIXES = (
    "close",
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


def handle_knowledge_command(
    command: str,
    context: CommandContext | None = None,
    *,
    get_period: Callable[[], str] | None = None,
    tell_joke: Callable[[], str] | None = None,
    wikipedia_search: Callable[[str], str] | None = None,
) -> CommandResult:
    """Handle low-risk local knowledge replies without performing side effects."""
    if context is not None:
        get_period = context.get_period
        tell_joke = context.tell_joke
        wikipedia_search = context.wikipedia_search
    if get_period is None or tell_joke is None or wikipedia_search is None:
        raise ValueError("Knowledge handler requires command context or callbacks.")
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()
    if normalized in GREETING_COMMANDS:
        return CommandResult(True, "Hey! I am doing good. How are you?", route="knowledge.greeting")
    if "how are you" in normalized:
        return CommandResult(True, "I am doing great! Thank you for asking.", route="knowledge.basic_reply")
    if any(word in normalized for word in PERIOD_WORDS):
        return CommandResult(True, get_period(), route="knowledge.period")
    if "joke" in normalized:
        return CommandResult(True, tell_joke(), route="knowledge.joke")
    if normalized.startswith(WIKIPEDIA_PREFIXES):
        return CommandResult(True, wikipedia_search(normalized), route="knowledge.wikipedia")
    return CommandResult.not_handled()
