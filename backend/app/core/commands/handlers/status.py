from __future__ import annotations

from ..context import CommandContext
from ..result import CommandResult


OFFLINE_MODE_COMMANDS = {
    "offline mode status",
    "is offline mode on",
    "what works offline",
}
OFFLINE_HELP_COMMANDS = {
    "offline help",
    "offline quick help",
    "offline commands",
}
OFFLINE_AI_COMMANDS = {
    "offline ai status",
    "local ai status",
    "is local ai ready",
}
FOCUS_MODE_COMMANDS = {
    "focus mode status",
    "is focus mode on",
}
VOICE_TRAINER_COMMANDS = {
    "voice trainer status",
    "voice trainer",
}
PIPER_SETUP_COMMANDS = {
    "piper setup status",
    "piper voice setup",
    "piper status",
}
CUSTOM_VOICE_SETUP_COMMANDS = {
    "my voice setup",
    "my voice setup status",
    "own voice setup",
    "custom voice setup",
    "voice clone setup",
}
CUSTOM_VOICE_LICENSE_COMMANDS = {
    "my voice license status",
    "custom voice license status",
    "voice license status",
    "coqui license status",
}
CUSTOM_VOICE_SAMPLES_COMMANDS = {
    "list my voice samples",
    "list custom voice samples",
    "show custom voice samples",
    "available custom voice samples",
}
VOICE_STATUS_COMMANDS = {
    "voice status",
    "voice recognition status",
    "current voice profile",
}
DANGEROUS_PREFIXES = (
    "enable ",
    "disable ",
    "turn on ",
    "turn off ",
    "set ",
    "change ",
    "update ",
    "use ",
    "switch ",
    "start ",
    "stop ",
    "clear ",
    "remove ",
    "reset ",
    "open ",
    "shutdown",
    "restart",
)


def handle_status_command(command: str, context: CommandContext) -> CommandResult:
    """Handle read-only voice/offline/backend status commands only."""
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()
    if normalized in OFFLINE_MODE_COMMANDS:
        return CommandResult(True, context.offline_mode_status_summary(), route="status.offline_mode")
    if normalized in OFFLINE_HELP_COMMANDS:
        return CommandResult(True, context.offline_help_summary(), route="status.offline_help")
    if normalized in OFFLINE_AI_COMMANDS:
        return CommandResult(True, context.offline_ai_status_summary(), route="status.offline_ai")
    if normalized in FOCUS_MODE_COMMANDS:
        return CommandResult(True, context.focus_mode_status_summary(), route="status.focus_mode")
    if normalized in VOICE_TRAINER_COMMANDS:
        return CommandResult(True, context.voice_trainer_status_summary(), route="status.voice_trainer")
    if normalized in PIPER_SETUP_COMMANDS:
        return CommandResult(True, context.piper_setup_summary(), route="status.piper_setup")
    if normalized in CUSTOM_VOICE_SETUP_COMMANDS:
        return CommandResult(True, context.custom_voice_setup_summary(), route="status.custom_voice_setup")
    if normalized in CUSTOM_VOICE_LICENSE_COMMANDS:
        return CommandResult(True, context.custom_voice_license_status_summary(), route="status.custom_voice_license")
    if normalized in CUSTOM_VOICE_SAMPLES_COMMANDS:
        return CommandResult(True, context.custom_voice_samples_summary(), route="status.custom_voice_samples")
    if normalized in VOICE_STATUS_COMMANDS:
        return CommandResult(True, context.voice_status_summary(), route="status.voice_profile")
    return CommandResult.not_handled()
