from __future__ import annotations

from core.commands.context import CommandContext
from core.commands.result import CommandResult


EMERGENCY_MODE_STATUS_COMMANDS = {
    "emergency mode status",
    "what is emergency mode",
    "emergency help",
}

EMERGENCY_QUICK_RESPONSE_COMMANDS = {
    "emergency quick response",
    "emergency quick responses",
    "quick response system",
}

EMERGENCY_PROTOCOL_INFO_COMMANDS = {
    "emergency protocol status",
    "what is emergency protocol",
}

DANGEROUS_EMERGENCY_PREFIXES = (
    "start emergency",
    "trigger emergency",
    "send emergency",
    "emergency alert",
    "alert emergency",
    "send sos",
    "send i am safe",
    "send safe",
    "share my location",
    "share saved location",
    "send my location",
    "call emergency",
    "emergency call",
    "lockdown",
    "assistant lockdown",
    "security lockdown",
    "lock ",
    "unlock ",
    "enable emergency",
    "disable emergency",
    "turn on emergency",
    "turn off emergency",
    "clear ",
    "delete ",
)


def handle_emergency_status_command(command: str, context: CommandContext) -> CommandResult:
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized or normalized.startswith(DANGEROUS_EMERGENCY_PREFIXES):
        return CommandResult.not_handled()

    if normalized in EMERGENCY_MODE_STATUS_COMMANDS:
        return CommandResult(True, context.emergency_mode_status_summary(), route="emergency_status.mode")
    if normalized in EMERGENCY_QUICK_RESPONSE_COMMANDS:
        return CommandResult(True, context.emergency_quick_response_summary(), route="emergency_status.quick_response")
    if normalized in EMERGENCY_PROTOCOL_INFO_COMMANDS:
        return CommandResult(True, context.emergency_protocol_summary(), route="emergency_status.protocol")
    return CommandResult.not_handled()
