from __future__ import annotations

from collections.abc import Callable

from ..context import CommandContext
from ..result import CommandResult


VOICE_DIAGNOSTICS_COMMANDS = {
    "voice diagnostics",
    "voice tuning status",
    "voice debug",
}
ASSISTANT_DOCTOR_COMMANDS = {
    "assistant doctor",
    "startup doctor",
    "system doctor",
    "check assistant health",
    "assistant health check",
}
BACKEND_STABILITY_COMMANDS = {
    "backend health summary",
    "backend stability summary",
    "backend release lock",
    "release lock status",
    "backend stability dashboard",
}
DANGEROUS_PREFIXES = (
    "shutdown",
    "shut down",
    "restart",
    "sleep",
    "sign out",
    "logout",
    "lock",
    "delete",
    "remove",
    "open ",
    "start ",
    "launch ",
)


def handle_diagnostics_command(
    command: str,
    context: CommandContext | None = None,
    *,
    assistant_doctor_summary: Callable[..., str] | None = None,
    backend_stability_summary: Callable[[], str] | None = None,
    security_status_summary: Callable[[], str] | None = None,
    voice_diagnostics_summary: Callable[[], str] | None = None,
    allow_security_voice: bool = True,
    allow_health: bool = True,
) -> CommandResult:
    """Handle read-only diagnostics/status commands without owning actions."""
    if context is not None:
        assistant_doctor_summary = context.assistant_doctor_summary
        backend_stability_summary = context.backend_stability_summary
        security_status_summary = context.security_status_summary
        voice_diagnostics_summary = context.voice_diagnostics_summary
    if (
        assistant_doctor_summary is None
        or backend_stability_summary is None
        or security_status_summary is None
        or voice_diagnostics_summary is None
    ):
        raise ValueError("Diagnostics handler requires command context or callbacks.")
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()

    if allow_security_voice:
        if normalized in VOICE_DIAGNOSTICS_COMMANDS:
            return CommandResult(True, voice_diagnostics_summary(), route="diagnostics.voice")

    if allow_health:
        if normalized in ASSISTANT_DOCTOR_COMMANDS:
            return CommandResult(
                True,
                assistant_doctor_summary(include_ready=False),
                route="diagnostics.assistant_doctor",
            )
        if normalized in BACKEND_STABILITY_COMMANDS:
            return CommandResult(True, backend_stability_summary(), route="diagnostics.backend_stability")

    return CommandResult.not_handled()
