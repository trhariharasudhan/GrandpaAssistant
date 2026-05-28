from __future__ import annotations

from .action_schema import AgentStep


SAFE_READ_ACTIONS = {"read_safe_system_status", "list_safe_directory_metadata", "clarify"}
CONFIRMATION_ACTIONS = {"open_application", "open_url", "take_screenshot", "create_reminder"}
BLOCKED_ACTIONS = {
    "delete_files",
    "format_drive",
    "send_message",
    "make_payment",
    "buy_or_order",
    "change_account_security",
    "shutdown_or_restart",
    "blocked",
}


def review_step(step: AgentStep) -> AgentStep:
    if step.action in BLOCKED_ACTIONS:
        step.safety = "blocked"
        step.requires_confirmation = False
        step.blocked_reason = step.blocked_reason or "This action is blocked for Autonomous Desktop Agent v1."
        return step
    if step.action in CONFIRMATION_ACTIONS:
        step.safety = "needs_confirmation"
        step.requires_confirmation = True
        return step
    step.safety = "safe_read" if step.action in SAFE_READ_ACTIONS else "blocked"
    step.requires_confirmation = False
    if step.safety == "blocked":
        step.blocked_reason = "Unsupported autonomous action for v1."
    return step


def review_steps(steps: list[AgentStep]) -> list[AgentStep]:
    return [review_step(step) for step in steps]
