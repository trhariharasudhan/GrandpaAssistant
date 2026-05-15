from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .context import CommandContext
from .result import CommandResult


CommandHandler = Callable[[str, CommandContext], CommandResult]
DEFAULT_READONLY_GROUPS = (
    "knowledge",
    "memory",
    "diagnostics",
    "debug",
    "status",
    "productivity",
    "knowledge_services",
    "device_status",
    "awareness",
    "contacts",
    "planning",
    "project_knowledge",
    "system_health",
    "iot_status",
    "security_status",
    "emergency_status",
    "profile_status",
    "developer_status",
    "notification_status",
    "audio_status",
    "overlay_status",
    "interface_status",
    "config_status",
)


@dataclass
class CommandHandlerRegistry:
    handlers: list[CommandHandler]

    def __init__(self, handlers: Iterable[CommandHandler] | None = None) -> None:
        self.handlers = list(handlers or [])

    def register(self, handler: CommandHandler) -> None:
        self.handlers.append(handler)

    def handle(self, command: str, context: CommandContext) -> CommandResult:
        for handler in self.handlers:
            result = handler(command, context)
            if result.handled:
                return result
        return CommandResult.not_handled()


def _readonly_handler_for_group(group: str) -> CommandHandler:
    from .handlers.audio_status import handle_audio_status_command
    from .handlers.awareness import handle_awareness_command
    from .handlers.config_status import handle_config_status_command
    from .handlers.contacts import handle_contacts_command
    from .handlers.debug import handle_debug_command
    from .handlers.device_status import handle_device_status_command
    from .handlers.diagnostics import handle_diagnostics_command
    from .handlers.developer_status import handle_developer_status_command
    from .handlers.emergency_status import handle_emergency_status_command
    from .handlers.knowledge import handle_knowledge_command
    from .handlers.knowledge_services import handle_knowledge_services_command
    from .handlers.notification_status import handle_notification_status_command
    from .handlers.overlay_status import handle_overlay_status_command
    from .handlers.iot_status import handle_iot_status_command
    from .handlers.interface_status import handle_interface_status_command
    from .handlers.memory import handle_memory_command
    from .handlers.planning import handle_planning_command
    from .handlers.profile_status import handle_profile_status_command
    from .handlers.project_knowledge import handle_project_knowledge_command
    from .handlers.productivity import handle_productivity_command
    from .handlers.security_status import handle_security_status_command
    from .handlers.status import handle_status_command
    from .handlers.system_health import handle_system_health_command

    handlers: dict[str, CommandHandler] = {
        "knowledge": handle_knowledge_command,
        "memory": handle_memory_command,
        "memory_personal": lambda text, ctx: handle_memory_command(text, ctx, allow_semantic=False),
        "semantic_memory": lambda text, ctx: handle_memory_command(text, ctx, allow_personal=False),
        "diagnostics": handle_diagnostics_command,
        "diagnostics_status": lambda text, ctx: handle_diagnostics_command(text, ctx, allow_health=False),
        "diagnostics_health": lambda text, ctx: handle_diagnostics_command(text, ctx, allow_security_voice=False),
        "debug": handle_debug_command,
        "debug_session": lambda text, ctx: handle_debug_command(text, ctx, allow_fix_read_only=False, allow_history=False),
        "debug_history": lambda text, ctx: handle_debug_command(text, ctx, allow_session_dashboard=False, allow_fix_read_only=False),
        "status": handle_status_command,
        "productivity": handle_productivity_command,
        "knowledge_services": handle_knowledge_services_command,
        "device_status": handle_device_status_command,
        "awareness": handle_awareness_command,
        "contacts": handle_contacts_command,
        "planning": handle_planning_command,
        "planning_google": lambda text, ctx: handle_planning_command(text, ctx, allow_local_calendar=False),
        "planning_calendar": lambda text, ctx: handle_planning_command(text, ctx, allow_google_calendar=False),
        "project_knowledge": handle_project_knowledge_command,
        "project_knowledge_library": lambda text, ctx: handle_project_knowledge_command(text, ctx, allow_storage=False),
        "project_knowledge_storage": lambda text, ctx: handle_project_knowledge_command(text, ctx, allow_library=False),
        "system_health": handle_system_health_command,
        "system_health_core": lambda text, ctx: handle_system_health_command(text, ctx, allow_hardware=False),
        "system_health_hardware": lambda text, ctx: handle_system_health_command(text, ctx, allow_core=False),
        "system_health_battery": lambda text, ctx: handle_system_health_command(
            text,
            ctx,
            allow_hardware=False,
            allow_battery_contains=True,
        ),
        "iot_status": handle_iot_status_command,
        "security_status": handle_security_status_command,
        "emergency_status": handle_emergency_status_command,
        "profile_status": handle_profile_status_command,
        "developer_status": handle_developer_status_command,
        "notification_status": handle_notification_status_command,
        "audio_status": handle_audio_status_command,
        "overlay_status": handle_overlay_status_command,
        "interface_status": handle_interface_status_command,
        "config_status": handle_config_status_command,
    }
    try:
        return handlers[group]
    except KeyError as error:
        valid = ", ".join(sorted(handlers))
        raise ValueError(f"Unknown read-only command handler group: {group}. Valid groups: {valid}") from error


def build_readonly_registry(
    context: CommandContext | None = None,
    groups: Iterable[str] | None = None,
) -> CommandHandlerRegistry:
    """Build an ordered registry for extracted read-only command handlers.

    The context argument is accepted so callers can use one consistent builder
    shape near dispatch sites; the registry still receives context at handle time.
    """
    del context
    ordered_groups = tuple(groups or DEFAULT_READONLY_GROUPS)
    return CommandHandlerRegistry(_readonly_handler_for_group(group) for group in ordered_groups)
