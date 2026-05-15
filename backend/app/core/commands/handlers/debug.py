from __future__ import annotations

from collections.abc import Callable

from ..context import CommandContext
from ..result import CommandResult


DEBUG_SESSION_COMMANDS = {
    "current debug session",
    "debug session summary",
}
DEBUG_DASHBOARD_COMMANDS = {
    "debug dashboard",
    "debug health",
    "debug status",
    "troubleshooting dashboard",
}
FIX_APPROVAL_SUMMARY_COMMANDS = {
    "show fix approvals",
}
FIX_AUDIT_COMMANDS = {
    "show fix audit log",
    "fix audit",
    "last fix actions",
}
DEBUG_TIMELINE_COMMANDS = {
    "debug timeline",
    "show debug timeline",
    "what happened in debug session",
    "debug history",
}
REUSE_SUGGESTION_COMMANDS = {
    "seen this before",
    "similar debug history",
    "previous fix for this",
    "idhu munnadi vandhucha",
}
DEBUG_LEARNING_COMMANDS = {
    "debug learning summary",
    "what did we learn from debug history",
    "common debug errors",
    "repeated issues",
    "debug insights",
}
DEBUG_CHECKLIST_COMMANDS = {
    "run debug checklist",
    "preflight debug check",
    "preventive debug check",
    "debug checklist",
    "issue varama check pannu",
}
DANGEROUS_PREFIXES = (
    "apply fix",
    "apply suggested fix",
    "dismiss fix",
    "approve",
    "allow",
    "confirm",
    "run fix",
    "rollback fix",
    "execute",
)


def handle_debug_command(
    command: str,
    context: CommandContext | None = None,
    *,
    current_debug_session_summary: Callable[[], str] | None = None,
    debug_dashboard_summary: Callable[[], str] | None = None,
    fix_approval_summary: Callable[[], str] | None = None,
    fix_audit_summary: Callable[[], str] | None = None,
    debug_timeline_summary: Callable[[], str] | None = None,
    debug_search_summary: Callable[[str], str] | None = None,
    reuse_suggestions_summary: Callable[..., str] | None = None,
    debug_learning_summary: Callable[[], str] | None = None,
    debug_checklist_summary: Callable[..., str] | None = None,
    allow_session_dashboard: bool = True,
    allow_fix_read_only: bool = True,
    allow_history: bool = True,
) -> CommandResult:
    """Handle read-only debug/fix summary commands only."""
    if context is not None:
        current_debug_session_summary = context.current_debug_session_summary
        debug_dashboard_summary = context.debug_dashboard_summary
        fix_approval_summary = context.fix_approval_summary
        fix_audit_summary = context.fix_audit_summary
        debug_timeline_summary = context.debug_timeline_summary
        debug_search_summary = context.debug_search_summary
        reuse_suggestions_summary = context.reuse_suggestions_summary
        debug_learning_summary = context.debug_learning_summary
        debug_checklist_summary = context.debug_checklist_summary
    if (
        current_debug_session_summary is None
        or debug_dashboard_summary is None
        or fix_approval_summary is None
        or fix_audit_summary is None
    ):
        raise ValueError("Debug handler requires command context or callbacks.")
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()

    if allow_session_dashboard:
        if normalized in DEBUG_SESSION_COMMANDS:
            return CommandResult(True, current_debug_session_summary(), route="debug.session_summary")
        if normalized in DEBUG_DASHBOARD_COMMANDS:
            return CommandResult(True, debug_dashboard_summary(), route="debug.dashboard")

    if allow_history:
        if normalized in DEBUG_TIMELINE_COMMANDS and debug_timeline_summary is not None:
            return CommandResult(True, debug_timeline_summary(), route="debug.timeline")
        if debug_search_summary is not None:
            search_prefixes = (
                "search debug sessions for ",
                "find debug session ",
                "old debug issue ",
                "previous error ",
            )
            for prefix in search_prefixes:
                if normalized.startswith(prefix):
                    return CommandResult(True, debug_search_summary(normalized[len(prefix):]), route="debug.search")
        if normalized in REUSE_SUGGESTION_COMMANDS and reuse_suggestions_summary is not None:
            language = "ta" if normalized == "idhu munnadi vandhucha" else "auto"
            return CommandResult(True, reuse_suggestions_summary(language=language), route="debug.reuse")
        if normalized in DEBUG_LEARNING_COMMANDS and debug_learning_summary is not None:
            return CommandResult(True, debug_learning_summary(), route="debug.learning")
        if normalized in DEBUG_CHECKLIST_COMMANDS and debug_checklist_summary is not None:
            language = "ta" if normalized == "issue varama check pannu" else "auto"
            return CommandResult(True, debug_checklist_summary(language=language), route="debug.checklist")

    if allow_fix_read_only:
        if normalized in FIX_APPROVAL_SUMMARY_COMMANDS:
            return CommandResult(True, fix_approval_summary(), route="debug.fix_approvals")
        if normalized in FIX_AUDIT_COMMANDS:
            return CommandResult(True, fix_audit_summary(), route="debug.fix_audit")

    return CommandResult.not_handled()
