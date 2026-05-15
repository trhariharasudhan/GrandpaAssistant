from __future__ import annotations

from ..context import CommandContext
from ..result import CommandResult
from ..summaries import interface as interface_summaries


STARTUP_STATUS_COMMANDS = {
    "startup status",
    "assistant startup status",
    "startup launch status",
}
AUTO_LAUNCH_STATUS_COMMANDS = {
    "auto launch status",
    "auto-launch status",
    "startup auto launch status",
}
TRAY_MODE_STATUS_COMMANDS = {
    "tray mode status",
    "tray startup status",
    "background mode status",
}
INTERFACE_MODE_STATUS_COMMANDS = {
    "interface mode status",
    "startup interface status",
    "terminal mode status",
}
DESKTOP_BACKEND_MODE_COMMANDS = {
    "desktop mode status",
    "backend mode status",
    "desktop backend mode",
    "desktop backend mode summary",
}
LAUNCHER_READINESS_COMMANDS = {
    "launcher readiness status",
    "launcher status",
    "desktop launcher status",
    "backend launcher status",
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
    "launch ",
    "open ",
    "start ",
    "stop ",
    "run ",
    "close ",
)


def handle_interface_status_command(command: str, context: CommandContext) -> CommandResult:
    """Handle read-only startup/interface/launcher status commands only."""
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()
    if normalized in STARTUP_STATUS_COMMANDS:
        return CommandResult(True, interface_summaries.startup_status_summary(), route="interface_status.startup")
    if normalized in AUTO_LAUNCH_STATUS_COMMANDS:
        return CommandResult(True, context.startup_auto_launch_status_summary(), route="interface_status.auto_launch")
    if normalized in TRAY_MODE_STATUS_COMMANDS:
        return CommandResult(True, interface_summaries.tray_mode_status_summary(), route="interface_status.tray")
    if normalized in INTERFACE_MODE_STATUS_COMMANDS:
        return CommandResult(True, interface_summaries.interface_mode_status_summary(), route="interface_status.interface")
    if normalized in DESKTOP_BACKEND_MODE_COMMANDS:
        return CommandResult(True, interface_summaries.desktop_backend_mode_summary(), route="interface_status.desktop_backend")
    if normalized in LAUNCHER_READINESS_COMMANDS:
        return CommandResult(True, interface_summaries.launcher_readiness_status_summary(), route="interface_status.launcher")
    return CommandResult.not_handled()
