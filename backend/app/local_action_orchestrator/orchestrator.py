from __future__ import annotations

from typing import Any

from .intent_mapper import IntentMapper
from .models import DomainClassification, LocalActionPlan, compact_text


RISKY_TERMS = {
    "send",
    "reply",
    "mute",
    "book",
    "order",
    "buy",
    "pay",
    "ticket",
    "submit",
    "apply",
    "delete",
    "close",
    "click",
}
HIGH_RISK_TERMS = {"pay", "buy", "purchase", "ticket", "order", "book", "submit", "apply"}


class LocalActionOrchestrator:
    """Plan-only router across browser/chat/visual/agent systems."""

    def __init__(self, mapper: IntentMapper | None = None) -> None:
        self.mapper = mapper or IntentMapper()

    def plan(self, command: str) -> dict[str, Any]:
        classification = self.mapper.classify(command)
        return self._plan_for_domain(classification).to_dict()

    def classify(self, command: str) -> dict[str, Any]:
        return self.mapper.classify(command).to_dict()

    def _plan_for_domain(self, classification: DomainClassification) -> LocalActionPlan:
        command = compact_text(classification.command, 2000)
        normalized = command.lower()
        risk_level = self._risk_level(classification.detected_domain, normalized)
        requires_confirmation = risk_level in {"medium_confirmation", "high_confirmation"}
        if classification.detected_domain == "browser":
            steps = [
                {"step": "1", "system": "browser_automation", "action": "build_browser_plan", "details": "Create a browser plan without submitting forms or payments.", "requires_confirmation": False},
                {"step": "2", "system": "browser_automation", "action": "wait_for_approval_if_risky", "details": "Require user confirmation before booking, ordering, applying, payment, or form submission.", "requires_confirmation": requires_confirmation},
            ]
            next_action = "preview_browser_plan" if requires_confirmation else "safe_to_execute_after_user_review"
        elif classification.detected_domain == "chat":
            steps = [
                {"step": "1", "system": "chat_integrations", "action": "prepare_draft_or_query", "details": "Use local chat integration memory/adapters to draft, read, summarize, or search contacts.", "requires_confirmation": False},
                {"step": "2", "system": "chat_integrations", "action": "require_message_approval", "details": "Never send messages, media, voice notes, or mute groups without approval.", "requires_confirmation": True},
            ]
            requires_confirmation = True
            risk_level = "medium_confirmation" if risk_level == "safe_local_action" else risk_level
            next_action = "ask_approval_or_missing_contact_details"
        elif classification.detected_domain == "visual_desktop":
            steps = [
                {"step": "1", "system": "visual_desktop", "action": "analyze_screen_if_explicit", "details": "Capture/inspect screen only for explicit screen or UI request.", "requires_confirmation": False},
                {"step": "2", "system": "visual_desktop", "action": "plan_ui_action", "details": "Use OCR/UI detection and confidence scoring before any click.", "requires_confirmation": requires_confirmation},
            ]
            next_action = "analyze_screen_or_request_confirmation"
        elif classification.detected_domain == "autonomous_agent":
            steps = [
                {"step": "1", "system": "autonomous_agent", "action": "decompose_goal", "details": "Create task graph with human-in-the-loop checkpoints.", "requires_confirmation": False},
                {"step": "2", "system": "autonomous_agent", "action": "pause_at_checkpoint", "details": "Ask before booking, ordering, sending, paying, or submitting.", "requires_confirmation": True},
            ]
            requires_confirmation = True
            risk_level = "high_confirmation" if any(term in normalized for term in HIGH_RISK_TERMS) else "medium_confirmation"
            next_action = "create_task_graph_and_wait_for_confirmation"
        else:
            steps = [{"step": "1", "system": "chat_service", "action": "normal_reply", "details": "Handle as normal conversation; no local action system needed.", "requires_confirmation": False}]
            requires_confirmation = False
            risk_level = "safe_read"
            next_action = "normal_chat_response"
        return LocalActionPlan(
            command=command,
            detected_domain=classification.detected_domain,
            confidence=classification.confidence,
            plan_steps=steps,
            requires_confirmation=requires_confirmation,
            risk_level=risk_level,
            next_action=next_action,
            reason=classification.reason,
        )

    def _risk_level(self, domain: str, normalized: str) -> str:
        if any(term in normalized for term in HIGH_RISK_TERMS):
            return "high_confirmation"
        if any(term in normalized for term in RISKY_TERMS):
            return "medium_confirmation"
        if domain in {"browser", "visual_desktop"}:
            return "safe_local_action"
        if domain == "chat":
            return "medium_confirmation"
        if domain == "autonomous_agent":
            return "medium_confirmation"
        return "safe_read"


_GLOBAL_ORCHESTRATOR: LocalActionOrchestrator | None = None


def get_local_action_orchestrator() -> LocalActionOrchestrator:
    global _GLOBAL_ORCHESTRATOR
    if _GLOBAL_ORCHESTRATOR is None:
        _GLOBAL_ORCHESTRATOR = LocalActionOrchestrator()
    return _GLOBAL_ORCHESTRATOR
