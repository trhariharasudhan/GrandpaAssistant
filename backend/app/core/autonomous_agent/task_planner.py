from __future__ import annotations

from .action_schema import AgentPlan, AgentStep, compact_text
from .goal_parser import parse_goal
from .safety_review import review_steps


def _blocked_step(reason: str) -> AgentStep:
    return AgentStep(
        step_id="blocked_1",
        action="blocked",
        title="Blocked autonomous action",
        safety="blocked",
        blocked_reason=reason,
    )


def create_plan(goal: str) -> AgentPlan:
    parsed = parse_goal(goal)
    intent = parsed.get("intent")
    slots = dict(parsed.get("slots") or {})
    steps: list[AgentStep]
    if intent == "blocked":
        reasons = parsed.get("blocked_reasons") or []
        reason = "; ".join(compact_text(item.get("reason"), 300) for item in reasons if isinstance(item, dict)) or "Blocked autonomous action."
        steps = [_blocked_step(reason)]
    elif intent == "open_application":
        steps = [AgentStep(step_id="open_application_1", action="open_application", title="Open application", params={"app": slots.get("app", "")})]
    elif intent == "open_url":
        steps = [AgentStep(step_id="open_url_1", action="open_url", title="Open URL", params={"url": slots.get("url", "")})]
    elif intent == "take_screenshot":
        steps = [AgentStep(step_id="take_screenshot_1", action="take_screenshot", title="Take a screenshot")]
    elif intent == "read_safe_system_status":
        steps = [AgentStep(step_id="read_status_1", action="read_safe_system_status", title="Read safe system status")]
    elif intent == "list_safe_directory_metadata":
        steps = [AgentStep(step_id="list_directory_1", action="list_safe_directory_metadata", title="List safe directory metadata", params={"path": slots.get("path", "")})]
    elif intent == "create_reminder":
        steps = [
            AgentStep(
                step_id="create_reminder_1",
                action="create_reminder",
                title="Create reminder",
                params={"reminder_text": slots.get("reminder_text", ""), "time_text": slots.get("time_text", "")},
            )
        ]
    else:
        steps = [AgentStep(step_id="clarify_1", action="clarify", title="Ask for a more specific goal")]
    return AgentPlan(understood_goal=parsed.get("goal") or goal, steps=review_steps(steps))
