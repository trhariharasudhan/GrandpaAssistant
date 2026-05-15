from __future__ import annotations

from ..context import CommandContext
from ..result import CommandResult
from ..summaries import config as config_summaries


CONFIG_STATUS_COMMANDS = {
    "config status",
    "configuration status",
    "backend config status",
}
SETTINGS_STATUS_COMMANDS = {
    "settings status",
    "assistant settings status",
}
ASSISTANT_SETTINGS_COMMANDS = {
    "show settings",
    "show config",
    "settings",
    "assistant settings summary",
    "settings summary",
}
ENVIRONMENT_READINESS_COMMANDS = {
    "environment config readiness",
    "environment readiness",
    "config readiness",
    "backend config readiness",
}
FEATURE_TOGGLE_COMMANDS = {
    "feature toggle summary",
    "feature toggles",
    "feature toggle status",
    "feature status summary",
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
    "write ",
    "save ",
    "delete ",
    "remove ",
    "clear ",
    "reset ",
    "run as ",
    "start admin",
    "admin mode on",
    "full control",
    "full settings access",
)


def handle_config_status_command(command: str, context: CommandContext) -> CommandResult:
    """Handle read-only config/settings status commands only."""
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()
    if normalized in CONFIG_STATUS_COMMANDS:
        return CommandResult(True, config_summaries.config_status_summary(), route="config_status.config")
    if normalized in SETTINGS_STATUS_COMMANDS:
        return CommandResult(True, config_summaries.settings_status_summary(), route="config_status.settings")
    if normalized in ASSISTANT_SETTINGS_COMMANDS:
        return CommandResult(True, config_summaries.assistant_settings_summary(), route="config_status.assistant_settings")
    if normalized in ENVIRONMENT_READINESS_COMMANDS:
        return CommandResult(True, config_summaries.environment_config_readiness_summary(), route="config_status.environment")
    if normalized in FEATURE_TOGGLE_COMMANDS:
        return CommandResult(True, config_summaries.feature_toggle_summary(), route="config_status.features")
    return CommandResult.not_handled()
