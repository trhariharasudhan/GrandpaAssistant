from __future__ import annotations

import re

from brain.memory_engine import get_memory
from cognition.graph_engine import knowledge_graph_context
from utils.config import get_setting


def _compact_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _tokenize(text: str) -> set[str]:
    tokens = set()
    for raw in _compact_text(text).lower().split():
        cleaned = "".join(char for char in raw if char.isalnum())
        if len(cleaned) >= 3:
            tokens.add(cleaned)
    return tokens


def _parse_options(question: str, options: list[str] | None) -> list[str]:
    provided = [_compact_text(item) for item in (options or []) if _compact_text(item)]
    if provided:
        return provided
    text = _compact_text(question)
    if " vs " in text.lower():
        return [_compact_text(item) for item in re.split(r"\bvs\b", text, flags=re.IGNORECASE) if _compact_text(item)]
    if " or " in text.lower():
        return [_compact_text(item) for item in re.split(r"\bor\b", text, flags=re.IGNORECASE) if _compact_text(item)]
    if "," in text:
        return [_compact_text(item) for item in text.split(",") if _compact_text(item)]
    return []


def _preference_tokens() -> set[str]:
    candidates = [
        get_memory("professional.goal_timeline.one_year_goal"),
        get_memory("professional.learning_path.current_focus"),
        get_memory("personal.favorites.favorite_code_editor"),
        get_memory("personal.favorites.favorite_browser"),
        get_memory("personal.routine.best_productive_time"),
    ]
    tokens = set()
    for value in candidates:
        if isinstance(value, list):
            for item in value:
                tokens |= _tokenize(item)
        else:
            tokens |= _tokenize(value)
    return tokens


def compare_options(question: str, options: list[str] | None = None) -> dict:
    prompt = _compact_text(question)
    parsed_options = _parse_options(prompt, options)
    if len(parsed_options) < 2:
        return {
            "question": prompt,
            "options": [],
            "recommended": "",
            "summary": "I need at least two clear options to compare.",
        }

    preference_tokens = _preference_tokens()
    graph_hints = knowledge_graph_context(prompt, limit=2)
    question_tokens = _tokenize(prompt)
    offline_bias = bool(get_setting("assistant.offline_mode_enabled", False))
    urgency = any(token in prompt.lower() for token in ("quick", "fast", "urgent", "asap"))
    deep = any(token in prompt.lower() for token in ("best", "important", "long term", "careful"))

    ranked = []
    for option in parsed_options:
        option_tokens = _tokenize(option)
        score = 1.0
        pros = []
        cons = []

        preference_overlap = option_tokens & preference_tokens
        if preference_overlap:
            score += 1.3 + (0.2 * len(preference_overlap))
            pros.append("Matches your saved preferences or focus areas.")
        if option_tokens & question_tokens:
            score += 0.5
            pros.append("Stays close to the way you framed the decision.")
        if offline_bias and option_tokens & {"offline", "local", "private"}:
            score += 0.8
            pros.append("Fits your current offline-first setup.")
        if urgency and option_tokens & {"quick", "fast", "simple", "small"}:
            score += 0.6
            pros.append("Looks faster to act on right now.")
        if deep and option_tokens & {"deep", "longterm", "thorough", "stable"}:
            score += 0.6
            pros.append("Looks stronger for the longer-term outcome.")
        if len(option_tokens) > 6:
            cons.append("May take more effort to execute cleanly.")
        if not preference_overlap:
            cons.append("Does not strongly match saved preferences yet.")

        ranked.append(
            {
                "option": option,
                "score": round(score, 2),
                "pros": pros[:3],
                "cons": cons[:2],
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    recommended = ranked[0]["option"]
    summary = (
        f"I would lean toward {recommended}. "
        f"It scores best against your current context and saved preferences."
    )
    if graph_hints:
        summary += " Related context: " + " | ".join(graph_hints[:2]) + "."

    return {
        "question": prompt,
        "options": ranked,
        "recommended": recommended,
        "summary": summary,
    }
