from __future__ import annotations

from brain.semantic_memory import search_semantic_memory
from cognition.graph_engine import knowledge_graph_context
from cognition.learning_engine import similar_success_patterns


def _compact_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _time_label(timestamp: str) -> str:
    text = _compact_text(timestamp)
    if not text:
        return "recently"
    if "T" in text:
        return text.split("T", 1)[0]
    return text


def contextual_recall_payload(query: str, context: str = "casual", limit: int = 3) -> dict:
    semantic = search_semantic_memory(query, limit=max(1, min(limit, 3)))
    patterns = similar_success_patterns(query, context=context, limit=max(1, min(limit, 2)))
    graph_hints = knowledge_graph_context(query, limit=max(1, min(limit, 3)))

    lines = []
    for item in semantic[:2]:
        lines.append(f"Saved memory match: {item.get('label')}: {item.get('display_value')}")
    for item in patterns[:2]:
        lines.append(
            "Past successful pattern: "
            f"On {_time_label(item.get('created_at', ''))}, a similar reply used {', '.join(item.get('strategies', [])[:4]) or 'a helpful style'}."
        )
    for item in graph_hints[:2]:
        lines.append(f"Linked user context: {item}")

    return {
        "query": _compact_text(query),
        "context": _compact_text(context).lower() or "casual",
        "semantic_matches": semantic,
        "past_patterns": patterns,
        "graph_hints": graph_hints,
        "summary": " ".join(lines) if lines else "No strong contextual recall was found for that request yet.",
    }


def build_contextual_memory_boost(query: str, context: str = "casual", limit: int = 3) -> str | None:
    payload = contextual_recall_payload(query, context=context, limit=limit)
    lines = []
    for item in payload.get("semantic_matches", [])[:2]:
        lines.append(f"- Saved memory: {item.get('label')}: {item.get('display_value')}")
    for item in payload.get("past_patterns", [])[:2]:
        lines.append(
            f"- A similar past interaction on {_time_label(item.get('created_at', ''))} worked well with a "
            f"{', '.join(item.get('strategies', [])[:3]) or 'helpful'} response style."
        )
    for item in payload.get("graph_hints", [])[:2]:
        lines.append(f"- Linked user context: {item}")
    if not lines:
        return None
    return "Contextual memory boost. Use this only when it genuinely helps.\n" + "\n".join(lines)
