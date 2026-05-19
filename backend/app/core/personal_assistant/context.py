from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any


MAX_CONTEXT_EVENTS = 12


def _utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


@dataclass
class AssistantActionPlan:
    intent: str
    action: str = ""
    tool_name: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    target: str = ""
    missing_details: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    risk_level: str = "LOW"
    reason: str = ""
    source_message: str = ""


@dataclass
class ConversationContext:
    session_id: str
    user_goal: str = ""
    active_task: str = ""
    pending_question: str = ""
    target_object: str = ""
    target_app: str = ""
    missing_details: list[str] = field(default_factory=list)
    chosen_action: str = ""
    reminder_details: dict[str, Any] = field(default_factory=dict)
    pending_memory_conflict: dict[str, Any] = field(default_factory=dict)
    pending_plan: AssistantActionPlan | None = None
    last_executed_action: dict[str, Any] = field(default_factory=dict)
    last_intent: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str = field(default_factory=_utc_now)

    def remember_event(self, *, user_message: str, intent: str, outcome: str, target: str = "") -> None:
        self.events.append(
            {
                "timestamp": _utc_now(),
                "user_message": compact_text(user_message),
                "intent": compact_text(intent),
                "outcome": compact_text(outcome),
                "target": compact_text(target),
            }
        )
        self.events = self.events[-MAX_CONTEXT_EVENTS:]
        self.last_intent = compact_text(intent)
        self.updated_at = _utc_now()


_CONTEXTS: dict[str, ConversationContext] = {}


def normalize_session_id(session_id: str | None) -> str:
    return compact_text(session_id) or "default"


def get_conversation_context(session_id: str | None = None) -> ConversationContext:
    normalized = normalize_session_id(session_id)
    context = _CONTEXTS.get(normalized)
    if context is None:
        context = ConversationContext(session_id=normalized)
        _CONTEXTS[normalized] = context
    return context


def reset_conversation_context(session_id: str | None = None) -> None:
    _CONTEXTS.pop(normalize_session_id(session_id), None)


def clear_personal_assistant_contexts_for_tests() -> None:
    _CONTEXTS.clear()
