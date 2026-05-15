from __future__ import annotations

from core.commands.context import CommandContext
from core.commands.result import CommandResult


SMART_HOME_STATUS_COMMANDS = {
    "smart home status",
    "iot status",
    "smart home devices",
    "list smart home devices",
}

IOT_INVENTORY_COMMANDS = {
    "iot inventory",
    "iot overview",
    "smart home inventory",
    "what iot devices are connected",
    "what smart devices are connected",
    "list iot devices",
}

IOT_HISTORY_COMMANDS = {
    "iot action history",
    "smart home history",
    "smart home action history",
    "recent smart home actions",
}

IOT_SETUP_COMMANDS = {
    "smart home setup help",
    "iot setup help",
    "smart home setup",
    "iot config help",
}

DANGEROUS_OR_LIVE_PREFIXES = (
    "turn on ",
    "turn off ",
    "switch on ",
    "switch off ",
    "run ",
    "execute ",
    "pair ",
    "connect ",
    "validate ",
    "iot validate",
    "smart home validation",
    "update ",
    "set ",
    "change ",
    "delete ",
    "remove ",
    "add ",
    "create ",
    "enable ",
    "disable ",
    "refresh ",
    "rescan ",
    "scan ",
)


def handle_iot_status_command(command: str, context: CommandContext) -> CommandResult:
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized or normalized.startswith(DANGEROUS_OR_LIVE_PREFIXES):
        return CommandResult.not_handled()

    if normalized in SMART_HOME_STATUS_COMMANDS:
        return CommandResult(True, context.smart_home_status_summary(), route="iot_status.smart_home")
    if normalized in IOT_INVENTORY_COMMANDS:
        return CommandResult(True, context.iot_awareness_summary(), route="iot_status.inventory")
    if normalized in IOT_HISTORY_COMMANDS:
        return CommandResult(True, context.iot_action_history_summary(), route="iot_status.history")
    if normalized in IOT_SETUP_COMMANDS:
        return CommandResult(True, context.smart_home_setup_summary(), route="iot_status.setup")
    return CommandResult.not_handled()
