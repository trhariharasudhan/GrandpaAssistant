from __future__ import annotations

from core.commands.context import CommandContext
from core.commands.result import CommandResult


SYSTEM_STATUS_COMMANDS = {
    "system status",
    "health status",
    "system health",
    "pc health",
}

CPU_STATUS_COMMANDS = {
    "cpu usage",
    "cpu status",
}

RAM_STATUS_COMMANDS = {
    "ram usage",
    "memory usage",
    "ram status",
    "memory status",
}

DISK_STATUS_COMMANDS = {
    "disk usage",
    "disk status",
}

BATTERY_STATUS_COMMANDS = {
    "battery status",
    "battery health",
}

HARDWARE_STATUS_COMMANDS = {
    "hardware status",
    "device status",
    "connected hardware",
    "what hardware is connected",
    "what devices are connected",
}

HARDWARE_EVENT_COMMANDS = {
    "recent hardware events",
    "hardware events",
    "recent device events",
    "device events",
}

MUTATING_OR_ACTION_PREFIXES = (
    "cleanup ",
    "clean up ",
    "delete ",
    "remove ",
    "move ",
    "change ",
    "set ",
    "update ",
    "enable ",
    "disable ",
    "turn on ",
    "turn off ",
    "shutdown",
    "shut down",
    "restart",
    "sleep",
    "lock",
    "open ",
    "close ",
    "launch ",
    "run ",
    "execute ",
    "scan ",
    "rescan ",
    "refresh ",
    "capture ",
    "take screenshot",
    "read screen",
)


def handle_system_health_command(
    command: str,
    context: CommandContext,
    *,
    allow_core: bool = True,
    allow_hardware: bool = True,
    allow_battery_contains: bool = False,
) -> CommandResult:
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized or normalized.startswith(MUTATING_OR_ACTION_PREFIXES):
        return CommandResult.not_handled()

    if allow_hardware:
        if normalized in HARDWARE_STATUS_COMMANDS:
            return CommandResult(True, context.hardware_status_summary(), route="system_health.hardware")
        if normalized in HARDWARE_EVENT_COMMANDS:
            return CommandResult(True, context.hardware_event_history_summary(), route="system_health.hardware_events")

    if allow_core:
        if normalized in SYSTEM_STATUS_COMMANDS:
            return CommandResult(True, context.system_status_summary(), route="system_health.system")
        if normalized in CPU_STATUS_COMMANDS:
            return CommandResult(True, context.cpu_status_summary(), route="system_health.cpu")
        if normalized in RAM_STATUS_COMMANDS:
            return CommandResult(True, context.ram_status_summary(), route="system_health.ram")
        if normalized in DISK_STATUS_COMMANDS:
            return CommandResult(True, context.disk_status_summary(), route="system_health.disk")
        if normalized in BATTERY_STATUS_COMMANDS or (allow_battery_contains and "battery" in normalized):
            return CommandResult(True, context.battery_status_summary(), route="system_health.battery")

    return CommandResult.not_handled()
