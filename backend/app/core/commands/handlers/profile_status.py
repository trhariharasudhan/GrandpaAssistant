from __future__ import annotations

from core.commands.context import CommandContext
from core.commands.result import CommandResult


PROFILE_SUMMARY_COMMANDS = {
    "tell me about myself",
    "summarize my profile",
    "my profile summary",
    "who am i really",
}

PERSONAL_SNAPSHOT_COMMANDS = {
    "personal snapshot",
    "summarize my personal details",
    "personal details snapshot",
}

PREFERRED_LANGUAGE_COMMANDS = {
    "what is my preferred language",
    "my preferred language",
    "preferred language",
}

PREFERRED_TONE_COMMANDS = {
    "what is my preferred tone",
    "my preferred tone",
    "preferred tone",
}

DANGEROUS_PROFILE_PREFIXES = (
    "set ",
    "change ",
    "update ",
    "save ",
    "remember ",
    "forget ",
    "delete ",
    "remove ",
    "clear ",
    "reset ",
    "edit ",
)


def handle_profile_status_command(command: str, context: CommandContext) -> CommandResult:
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized or normalized.startswith(DANGEROUS_PROFILE_PREFIXES):
        return CommandResult.not_handled()

    if normalized in PROFILE_SUMMARY_COMMANDS:
        return CommandResult(True, context.profile_summary(), route="profile_status.profile")
    if normalized in PERSONAL_SNAPSHOT_COMMANDS:
        return CommandResult(True, context.personal_snapshot_summary(), route="profile_status.personal_snapshot")
    if normalized in PREFERRED_LANGUAGE_COMMANDS:
        return CommandResult(True, context.preferred_language_summary(), route="profile_status.preferred_language")
    if normalized in PREFERRED_TONE_COMMANDS:
        return CommandResult(True, context.preferred_tone_summary(), route="profile_status.preferred_tone")
    return CommandResult.not_handled()
