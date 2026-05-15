from __future__ import annotations

from ..context import CommandContext
from ..result import CommandResult


PHONE_LINK_STATUS_COMMANDS = {
    "phone link status",
}
FACE_SECURITY_STATUS_COMMANDS = {
    "face security status",
    "face verification status",
    "face status",
    "is my face enrolled",
}
DANGEROUS_PREFIXES = (
    "enroll ",
    "register ",
    "save my face",
    "verify ",
    "authenticate ",
    "lock ",
    "unlock ",
    "enable ",
    "disable ",
    "turn on ",
    "turn off ",
    "switch on ",
    "switch off ",
    "pair ",
    "connect ",
    "run ",
    "open ",
    "launch ",
    "start ",
    "stop ",
    "set ",
    "change ",
    "update ",
    "delete ",
    "remove ",
)


def handle_device_status_command(command: str, context: CommandContext) -> CommandResult:
    """Handle read-only device, readiness, and setup-summary commands only."""
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()
    if normalized in PHONE_LINK_STATUS_COMMANDS:
        return CommandResult(True, context.phone_link_status_summary(), route="device_status.phone_link")
    if normalized in FACE_SECURITY_STATUS_COMMANDS:
        return CommandResult(True, context.face_security_status_summary(), route="device_status.face_security")
    return CommandResult.not_handled()
