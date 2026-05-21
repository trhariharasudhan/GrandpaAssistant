from __future__ import annotations

from typing import Any

from .state import compact_text


HIGH_CONFIRMATION_GOALS = ("order", "book", "send", "message", "email", "pay", "purchase", "apply", "submit")


class ToolSelector:
    def select_tool(self, step: dict[str, Any]) -> str:
        action = compact_text(step.get("action")).lower()
        if action in {"ask_user", "approval_checkpoint"}:
            return action
        if action == "open_browser":
            return "browser_automation"
        if action == "send_message":
            return "chat_integrations"
        if action == "prepare_notes":
            return "local_note_draft"
        return "unsupported_action"


class GoalPlanner:
    """Deterministic decomposition layer; future LLM planners must still validate here."""

    def decompose_goal(self, goal: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
        text = compact_text(goal, 2000)
        normalized = text.lower()
        steps: list[dict[str, Any]]
        if "hungry" in normalized or "food" in normalized:
            steps = [
                {"step_id": "ask_food_preference", "action": "ask_user", "prompt": "What food or restaurant do you prefer?"},
                {"step_id": "open_food_app", "action": "open_browser", "request": "Order food", "requires_confirmation": True},
                {"step_id": "approval_before_order", "action": "approval_checkpoint", "reason": "Food ordering requires user confirmation before checkout."},
            ]
        elif "cab" in normalized or "taxi" in normalized:
            steps = [
                {"step_id": "ask_pickup_drop", "action": "ask_user", "prompt": "What pickup and drop location should I use?"},
                {"step_id": "open_cab_site", "action": "open_browser", "request": "Book a cab", "requires_confirmation": True},
                {"step_id": "approval_before_booking", "action": "approval_checkpoint", "reason": "Cab booking requires user confirmation before final booking."},
            ]
        elif "report" in normalized and ("send" in normalized or "manager" in normalized):
            steps = [
                {"step_id": "prepare_report_message", "action": "prepare_notes", "prompt": "Draft today's report from available context."},
                {"step_id": "approval_before_send", "action": "approval_checkpoint", "reason": "Sending work communication requires confirmation."},
                {"step_id": "send_report", "action": "send_message", "requires_confirmation": True},
            ]
        elif "meeting notes" in normalized or "prepare notes" in normalized:
            steps = [
                {"step_id": "collect_meeting_context", "action": "ask_user", "prompt": "Which meeting should I prepare notes for?"},
                {"step_id": "prepare_meeting_notes", "action": "prepare_notes", "prompt": "Prepare structured meeting notes."},
            ]
        else:
            steps = [{"step_id": "clarify_goal", "action": "ask_user", "prompt": "What outcome should I complete for you?"}]
        risk = "high_confirmation" if any(term in normalized for term in HIGH_CONFIRMATION_GOALS) else "medium_confirmation"
        return {"ok": True, "goal": text, "risk_level": risk, "steps": steps, "context_used": bool(context)}


class TaskGraphEngine:
    def build_graph(self, plan: dict[str, Any]) -> dict[str, Any]:
        steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
        nodes = []
        edges = []
        previous = ""
        selector = ToolSelector()
        for index, step in enumerate(steps):
            node = {
                "node_id": compact_text(step.get("step_id")) or f"step_{index + 1}",
                "action": compact_text(step.get("action")),
                "tool_name": selector.select_tool(step),
                "status": "pending",
                "requires_confirmation": bool(step.get("requires_confirmation") or step.get("action") == "approval_checkpoint"),
                "prompt": compact_text(step.get("prompt") or step.get("reason")),
                "request": compact_text(step.get("request")),
            }
            nodes.append(node)
            if previous:
                edges.append({"from": previous, "to": node["node_id"]})
            previous = node["node_id"]
        return {"nodes": nodes, "edges": edges, "risk_level": compact_text(plan.get("risk_level"))}
