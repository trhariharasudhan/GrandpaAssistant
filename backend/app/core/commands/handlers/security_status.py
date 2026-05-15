from __future__ import annotations

from core.commands.context import CommandContext
from core.commands.result import CommandResult


SECURITY_STATUS_COMMANDS = {
    "security status",
    "assistant security status",
    "system security status",
}

SECURITY_ALERT_COMMANDS = {
    "security alerts",
    "show security alerts",
    "security warnings",
}

SECURITY_LOG_COMMANDS = {
    "security logs",
    "show security logs",
    "recent security logs",
}

VOICE_AUTH_STATUS_COMMANDS = {
    "my voice auth status",
    "voice authentication status",
    "voice auth status",
}

SECURITY_ADMIN_STATUS_COMMANDS = {
    "security admin status",
    "is security admin mode on",
}

ADMIN_PERMISSION_STATUS_COMMANDS = {
    "admin status",
    "administrator status",
    "full control status",
    "settings access status",
}

DANGEROUS_PREFIXES = (
    "authenticate ",
    "verify ",
    "unlock ",
    "lock ",
    "enable ",
    "disable ",
    "trust ",
    "approve ",
    "deny ",
    "set ",
    "create ",
    "change ",
    "update ",
    "delete ",
    "clear ",
    "remove ",
    "emergency",
    "send emergency",
    "trigger emergency",
    "start emergency",
)


def _is_admin_permission_status(normalized: str) -> bool:
    return normalized in ADMIN_PERMISSION_STATUS_COMMANDS or (
        ("admin" in normalized or "administrator" in normalized) and "status" in normalized
    )


def handle_security_status_command(command: str, context: CommandContext) -> CommandResult:
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized or normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()

    if normalized in SECURITY_STATUS_COMMANDS:
        return CommandResult(True, context.security_status_summary(), route="security_status.security")
    if normalized in SECURITY_ALERT_COMMANDS:
        return CommandResult(True, context.security_alerts_summary(), route="security_status.alerts")
    if normalized in SECURITY_LOG_COMMANDS:
        return CommandResult(True, context.security_logs_summary(), route="security_status.logs")
    if normalized in VOICE_AUTH_STATUS_COMMANDS:
        return CommandResult(True, context.voice_auth_status_summary(), route="security_status.voice_auth")
    if normalized in SECURITY_ADMIN_STATUS_COMMANDS:
        return CommandResult(True, context.security_admin_status_summary(), route="security_status.admin")
    if _is_admin_permission_status(normalized):
        return CommandResult(True, context.admin_permission_status_summary(), route="security_status.permission")
    return CommandResult.not_handled()
