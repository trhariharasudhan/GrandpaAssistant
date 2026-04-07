from __future__ import annotations

from cognition.context_engine import build_contextual_memory_boost
from cognition.decision_engine import compare_options
from cognition.graph_engine import build_knowledge_graph
from cognition.insight_engine import generate_user_insights
from cognition.learning_engine import (
    build_learning_prompt_boost,
    learning_status_payload,
    observe_user_reaction,
    record_interaction,
    submit_feedback,
)
from cognition.personality_engine import personality_status_payload, resolve_personality_mode
from cognition.proactive_engine import proactive_conversation_status
from cognition.recovery_engine import recovery_status_payload
from cognition.sync_engine import queue_sync_event, sync_status_payload


def _compact_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def observe_user_turn(text: str, *, context: str = "casual", emotion: str = "neutral", mood: str = "neutral", source: str = "chat") -> dict:
    del context, emotion, mood, source
    status = observe_user_reaction(text)
    return {"learning": status}


def record_assistant_turn(
    user_text: str,
    assistant_reply: str,
    *,
    context: str = "casual",
    emotion: str = "neutral",
    mood: str = "neutral",
    source: str = "chat",
    route: str = "",
    model: str = "",
) -> dict:
    personality_mode = resolve_personality_mode(context=context, emotion=emotion, user_text=user_text)
    interaction = record_interaction(
        user_text,
        assistant_reply,
        context=context,
        emotion=emotion,
        mood=mood,
        personality_mode=personality_mode,
        source=source,
        route=route,
        model=model,
    )
    queue_sync_event("interaction", f"Captured assistant interaction in {context} mode.", interaction.get("id", ""))
    return interaction


def submit_response_feedback(interaction_id: str, reaction: str, note: str = "", source: str = "user") -> dict | None:
    updated = submit_feedback(interaction_id, reaction, note=note, source=source)
    if updated:
        queue_sync_event("feedback", f"Recorded {reaction} feedback.", interaction_id)
    return updated


def build_intelligence_prompt_boost(user_text: str, context: str = "casual", emotion: str = "neutral", mood: dict | None = None) -> str | None:
    del mood
    parts = []
    personality = personality_status_payload(context=context, emotion=emotion, user_text=user_text)
    if personality.get("instruction"):
        parts.append(personality["instruction"])
    learning = build_learning_prompt_boost(user_text, context=context, emotion=emotion)
    if learning:
        parts.append(learning)
    recall = build_contextual_memory_boost(user_text, context=context)
    if recall:
        parts.append(recall)
    if not parts:
        return None
    return "\n".join(parts)


def intelligence_status_payload(runtime_snapshot: dict | None = None) -> dict:
    from cognition.workflow_engine import workflow_status_payload

    graph = build_knowledge_graph(limit=60)
    learning = learning_status_payload()
    return {
        "learning": learning,
        "response_memory": learning.get("response_memory", {}),
        "behavior_learning": learning.get("behavior_learning", {}),
        "prompt_optimization": learning.get("prompt_optimization", {}),
        "automation_suggestions": learning.get("automation_suggestions", []),
        "insights": generate_user_insights(),
        "personality": personality_status_payload(
            context=_compact_text(((runtime_snapshot or {}).get("runtime") or {}).get("current_context")) or "casual",
            emotion=_compact_text(((runtime_snapshot or {}).get("conversation") or {}).get("last_emotion")) or "neutral",
        ),
        "knowledge_graph": {
            "node_count": graph.get("node_count", 0),
            "edge_count": graph.get("edge_count", 0),
            "summary": graph.get("summary", ""),
        },
        "decision_support": {
            "ready": True,
            "summary": "Decision engine can compare options using user preferences and graph context.",
        },
        "workflows": workflow_status_payload(),
        "recovery": recovery_status_payload(),
        "sync": sync_status_payload(),
        "proactive_conversation": proactive_conversation_status(runtime_snapshot or {}),
        "summary": "Advanced cognition layer is active: learning, insights, contextual recall, decisions, workflows, recovery, sync, and proactive assistance.",
    }


def quick_decision_payload(question: str, options: list[str] | None = None) -> dict:
    return compare_options(question, options=options)
