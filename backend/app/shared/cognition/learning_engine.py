from __future__ import annotations

import datetime
import uuid
from collections import Counter

from cognition.state import load_section, update_section, utc_now


MAX_INTERACTIONS = 240
MAX_RESPONSE_MEMORY = 48
POSITIVE_CUES = ("thanks", "thank you", "got it", "perfect", "helpful", "great", "nice", "awesome", "cool")
NEGATIVE_CUES = ("wrong", "not helpful", "bad", "doesn't help", "did not help", "not right", "issue", "problem")
SHORT_RESPONSE_CUES = ("short answer", "briefly", "brief answer", "quick answer", "one line", "keep it short", "concise")
DETAILED_RESPONSE_CUES = ("in detail", "detailed", "explain", "more detail", "deep dive", "step by step", "full answer")
FORMAL_TONE_CUES = ("professional", "formal", "polished")
CASUAL_TONE_CUES = ("casual", "friendly", "chill", "simple", "human")
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "what", "when", "where", "your", "you",
    "about", "would", "there", "want", "could", "should", "please", "tell", "show", "need", "help", "into",
    "make", "like", "just", "keep", "really", "today", "then", "them", "they", "been", "were", "will", "them",
}


def _compact_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _preview(value, limit: int = 220) -> str:
    text = _compact_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _tokenize(text: str) -> set[str]:
    tokens = set()
    for raw in _compact_text(text).lower().split():
        cleaned = "".join(char for char in raw if char.isalnum())
        if len(cleaned) >= 3:
            tokens.add(cleaned)
    return tokens


def _reaction_from_text(text: str) -> str | None:
    lowered = _compact_text(text).lower()
    if not lowered:
        return None
    if any(cue in lowered for cue in POSITIVE_CUES):
        return "good"
    if any(cue in lowered for cue in NEGATIVE_CUES):
        return "bad"
    return None


def _time_window(timestamp: str) -> str:
    text = _compact_text(timestamp)
    if not text:
        return "unknown"
    try:
        parsed = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return "unknown"
    hour = parsed.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def _topic_tags(text: str, limit: int = 4) -> list[str]:
    counter = Counter()
    for token in _tokenize(text):
        if token in STOPWORDS:
            continue
        counter[token] += 1
    return [item[0] for item in counter.most_common(max(1, limit))]


def _request_signal_tags(user_text: str) -> list[str]:
    lowered = _compact_text(user_text).lower()
    tags = []
    if any(cue in lowered for cue in SHORT_RESPONSE_CUES):
        tags.append("concise")
    if any(cue in lowered for cue in DETAILED_RESPONSE_CUES):
        tags.append("detailed")
    if any(cue in lowered for cue in FORMAL_TONE_CUES):
        tags.append("professional")
    if any(cue in lowered for cue in CASUAL_TONE_CUES):
        tags.append("friendly")
    if "next step" in lowered or "what should i do" in lowered:
        tags.append("proactive")
    return tags


def _strategy_tags(user_text: str, reply_text: str, context: str, emotion: str, personality_mode: str) -> list[str]:
    reply = _compact_text(reply_text)
    tags = {f"context:{_compact_text(context).lower() or 'casual'}", f"emotion:{_compact_text(emotion).lower() or 'neutral'}"}
    if len(reply) <= 180:
        tags.add("concise")
    else:
        tags.add("detailed")
    if personality_mode:
        tags.add(f"persona:{_compact_text(personality_mode).lower()}")
    lowered_reply = reply.lower()
    if any(token in lowered_reply for token in ("sorry", "that sounds", "i'm here", "want to talk")):
        tags.add("empathetic")
    if any(token in lowered_reply for token in ("want me", "should i", "you can", "next step")):
        tags.add("proactive")
    if any(token in lowered_reply for token in ("clear", "step", "focus", "recommend")):
        tags.add("direct")
    if _compact_text(context).lower() == "work":
        tags.add("professional")
    if _compact_text(emotion).lower() == "angry":
        tags.add("calm")
    if _compact_text(context).lower() == "casual":
        tags.add("friendly")
    if len(_tokenize(user_text) & _tokenize(reply_text)) >= 2:
        tags.add("grounded")
    return sorted(tags)


def _ensure_learning_defaults(data: dict | None) -> dict:
    payload = data if isinstance(data, dict) else {}
    payload.setdefault("interactions", [])
    payload.setdefault("strategy_scores", {})
    payload.setdefault("feedback_count", 0)
    payload.setdefault("positive_feedback", 0)
    payload.setdefault("negative_feedback", 0)
    payload.setdefault("best_responses", [])
    payload.setdefault("failed_responses", [])
    payload.setdefault("last_updated_at", "")
    preferences = payload.setdefault("user_preferences", {})
    preferences.setdefault("scores", {})
    preferences.setdefault("last_updated_at", "")
    behavior = payload.setdefault("behavior_profile", {})
    behavior.setdefault("active_windows", {})
    behavior.setdefault("contexts", {})
    behavior.setdefault("routes", {})
    behavior.setdefault("models", {})
    behavior.setdefault("topics", {})
    behavior.setdefault("response_lengths", {})
    behavior.setdefault("last_updated_at", "")
    return payload


def _add_score(scores: dict, key: str, delta: float) -> None:
    if not key or not delta:
        return
    scores[key] = round(float(scores.get(key, 0.0) or 0.0) + float(delta), 3)


def _remove_memory_entry(entries: list[dict], interaction_id: str) -> list[dict]:
    target = _compact_text(interaction_id)
    return [item for item in list(entries or []) if _compact_text(item.get("id")) != target]


def _memory_entry_from_interaction(interaction: dict, *, note: str = "", failure_tags: list[str] | None = None) -> dict:
    return {
        "id": interaction.get("id"),
        "created_at": interaction.get("created_at", ""),
        "context": interaction.get("context", "casual"),
        "emotion": interaction.get("emotion", "neutral"),
        "mood": interaction.get("mood", "neutral"),
        "time_window": interaction.get("time_window", "unknown"),
        "topic_tags": list(interaction.get("topic_tags") or []),
        "user_text_preview": interaction.get("user_text_preview", ""),
        "assistant_reply_preview": interaction.get("assistant_reply_preview", ""),
        "strategies": list(interaction.get("strategies") or []),
        "feedback_note": _preview(note, 180),
        "failure_tags": list(failure_tags or []),
    }


def _failure_tags(note: str, interaction: dict) -> list[str]:
    lowered = f"{_compact_text(note).lower()} {_compact_text(interaction.get('assistant_reply_preview')).lower()}"
    tags = set()
    cue_map = {
        "too_long": ("too long", "lengthy", "long answer", "too much", "too many words"),
        "too_short": ("too short", "more detail", "more details", "expand", "not enough"),
        "incorrect": ("wrong", "incorrect", "not right", "mistake", "false"),
        "unclear": ("unclear", "confusing", "confused", "not clear"),
        "generic": ("generic", "vague", "not helpful", "not useful", "did not help"),
        "too_formal": ("formal", "robotic", "stiff"),
        "tone_mismatch": ("tone", "cold", "harsh", "rude"),
    }
    for tag, cues in cue_map.items():
        if any(cue in lowered for cue in cues):
            tags.add(tag)
    strategies = set(interaction.get("strategies") or [])
    if not tags and "detailed" in strategies:
        tags.add("too_long")
    if not tags and "grounded" not in strategies:
        tags.add("generic")
    if not tags:
        tags.add("unhelpful")
    return sorted(tags)


def _record_request_preferences(data: dict, interaction: dict) -> None:
    scores = data.setdefault("user_preferences", {}).setdefault("scores", {})
    for tag in interaction.get("request_signal_tags", []):
        _add_score(scores, tag, 0.35)
    data["user_preferences"]["last_updated_at"] = utc_now()


def _update_behavior_profile(data: dict, interaction: dict) -> None:
    behavior = data.setdefault("behavior_profile", {})
    for bucket, key in (
        ("active_windows", interaction.get("time_window", "unknown")),
        ("contexts", interaction.get("context", "casual")),
        ("routes", interaction.get("route") or "general"),
        ("models", interaction.get("model") or "unknown"),
    ):
        values = behavior.setdefault(bucket, {})
        normalized = _compact_text(key).lower() or "unknown"
        values[normalized] = int(values.get(normalized, 0) or 0) + 1
    response_lengths = behavior.setdefault("response_lengths", {})
    response_key = "short" if "concise" in set(interaction.get("strategies") or []) else "detailed"
    response_lengths[response_key] = int(response_lengths.get(response_key, 0) or 0) + 1
    topics = behavior.setdefault("topics", {})
    for topic in interaction.get("topic_tags", [])[:4]:
        normalized_topic = _compact_text(topic).lower()
        if not normalized_topic:
            continue
        topics[normalized_topic] = int(topics.get(normalized_topic, 0) or 0) + 1
    behavior["last_updated_at"] = utc_now()


def _apply_feedback(data: dict, interaction_index: int, reaction: str, note: str = "", source: str = "user") -> dict:
    if interaction_index < 0 or interaction_index >= len(data["interactions"]):
        return data
    interaction = data["interactions"][interaction_index]
    normalized = "good" if str(reaction).strip().lower() == "good" else "bad"
    previous = _compact_text(interaction.get("feedback", {}).get("reaction")).lower()
    previous_delta = 1.0 if previous == "good" else -1.0 if previous == "bad" else 0.0
    delta = 1.0 if normalized == "good" else -1.0

    interaction["feedback"] = {
        "reaction": normalized,
        "note": _preview(note, 180),
        "source": source,
        "at": utc_now(),
    }

    if previous not in {"good", "bad"}:
        data["feedback_count"] = int(data.get("feedback_count", 0)) + 1
    elif previous != normalized:
        if previous == "good":
            data["positive_feedback"] = max(0, int(data.get("positive_feedback", 0)) - 1)
        else:
            data["negative_feedback"] = max(0, int(data.get("negative_feedback", 0)) - 1)

    if previous != normalized:
        if normalized == "good":
            data["positive_feedback"] = int(data.get("positive_feedback", 0)) + 1
        else:
            data["negative_feedback"] = int(data.get("negative_feedback", 0)) + 1

        score_adjustment = delta - previous_delta
        strategy_scores = data.setdefault("strategy_scores", {})
        preference_scores = data.setdefault("user_preferences", {}).setdefault("scores", {})
        for tag in interaction.get("strategies", []):
            _add_score(strategy_scores, tag, score_adjustment)
            if tag in {"concise", "detailed", "empathetic", "proactive", "direct", "friendly", "professional", "calm"}:
                _add_score(preference_scores, tag, score_adjustment)

    interaction["feedback_score"] = 1 if normalized == "good" else -1
    interaction["failure_tags"] = [] if normalized == "good" else _failure_tags(note, interaction)

    best_responses = _remove_memory_entry(data.get("best_responses", []), interaction.get("id", ""))
    failed_responses = _remove_memory_entry(data.get("failed_responses", []), interaction.get("id", ""))
    if normalized == "good":
        best_responses.append(_memory_entry_from_interaction(interaction, note=note))
        data["best_responses"] = best_responses[-MAX_RESPONSE_MEMORY:]
        data["failed_responses"] = failed_responses[-MAX_RESPONSE_MEMORY:]
    else:
        failed_responses.append(
            _memory_entry_from_interaction(interaction, note=note, failure_tags=interaction.get("failure_tags", []))
        )
        data["failed_responses"] = failed_responses[-MAX_RESPONSE_MEMORY:]
        data["best_responses"] = best_responses[-MAX_RESPONSE_MEMORY:]

    data.setdefault("user_preferences", {})["last_updated_at"] = utc_now()
    data["last_updated_at"] = utc_now()
    return data


def observe_user_reaction(user_text: str) -> dict:
    reaction = _reaction_from_text(user_text)

    def updater(current):
        data = _ensure_learning_defaults(current)
        if not reaction:
            return data
        for index in range(len(data["interactions"]) - 1, -1, -1):
            interaction = data["interactions"][index]
            if _compact_text(interaction.get("feedback", {}).get("reaction")):
                break
            if interaction.get("assistant_reply_preview"):
                return _apply_feedback(data, index, reaction, note=f"Inferred from: {_preview(user_text, 120)}", source="inferred")
        return data

    updated = update_section("learning", updater)
    return learning_status_payload(updated)


def record_interaction(
    user_text: str,
    assistant_reply: str,
    *,
    context: str = "casual",
    emotion: str = "neutral",
    mood: str = "neutral",
    personality_mode: str = "friendly",
    source: str = "chat",
    route: str = "",
    model: str = "",
) -> dict:
    created_at = utc_now()
    record = {
        "id": f"turn-{uuid.uuid4().hex[:10]}",
        "created_at": created_at,
        "source": _compact_text(source) or "chat",
        "context": _compact_text(context).lower() or "casual",
        "emotion": _compact_text(emotion).lower() or "neutral",
        "mood": _compact_text(mood).lower() or "neutral",
        "personality_mode": _compact_text(personality_mode).lower() or "friendly",
        "route": _compact_text(route),
        "model": _compact_text(model),
        "time_window": _time_window(created_at),
        "topic_tags": _topic_tags(user_text),
        "request_signal_tags": _request_signal_tags(user_text),
        "user_text_preview": _preview(user_text),
        "assistant_reply_preview": _preview(assistant_reply),
        "strategies": _strategy_tags(user_text, assistant_reply, context, emotion, personality_mode),
        "feedback": {},
        "feedback_score": 0,
        "failure_tags": [],
    }

    def updater(current):
        data = _ensure_learning_defaults(current)
        interactions = list(data.get("interactions") or [])
        interactions.append(record)
        data["interactions"] = interactions[-MAX_INTERACTIONS:]
        _record_request_preferences(data, record)
        _update_behavior_profile(data, record)
        data["last_updated_at"] = utc_now()
        return data

    update_section("learning", updater)
    return record


def submit_feedback(interaction_id: str, reaction: str, note: str = "", source: str = "user") -> dict | None:
    normalized_id = _compact_text(interaction_id)
    if not normalized_id:
        return None

    updated_record = {"value": None}

    def updater(current):
        data = _ensure_learning_defaults(current)
        for index, interaction in enumerate(data["interactions"]):
            if _compact_text(interaction.get("id")) != normalized_id:
                continue
            result = _apply_feedback(data, index, reaction, note=note, source=source)
            updated_record["value"] = result["interactions"][index]
            return result
        return data

    update_section("learning", updater)
    return updated_record["value"]


def _match_entries(entries: list[dict], query: str, context: str = "casual", limit: int = 3) -> list[dict]:
    query_tokens = _tokenize(query)
    context_key = _compact_text(context).lower() or "casual"
    if not query_tokens:
        return []
    scored = []
    for item in list(entries or []):
        item_tokens = _tokenize(item.get("user_text_preview", "")) | _tokenize(item.get("assistant_reply_preview", ""))
        overlap = len(query_tokens & item_tokens)
        if overlap <= 0:
            continue
        if _compact_text(item.get("context")).lower() == context_key:
            overlap += 1
        topic_overlap = len(set(item.get("topic_tags") or []) & query_tokens)
        overlap += topic_overlap
        scored.append((overlap, item))
    scored.sort(key=lambda entry: (entry[0], entry[1].get("created_at", "")), reverse=True)
    results = []
    for score, item in scored[: max(1, limit)]:
        enriched = dict(item)
        enriched["score"] = score
        results.append(enriched)
    return results


def best_response_matches(query: str, context: str = "casual", limit: int = 3) -> list[dict]:
    data = load_section("learning", {})
    return _match_entries(data.get("best_responses", []), query, context=context, limit=limit)


def similar_failed_patterns(query: str, context: str = "casual", limit: int = 2) -> list[dict]:
    data = load_section("learning", {})
    return _match_entries(data.get("failed_responses", []), query, context=context, limit=limit)


def similar_success_patterns(query: str, context: str = "casual", limit: int = 3) -> list[dict]:
    matches = best_response_matches(query, context=context, limit=limit)
    if matches:
        return matches
    data = load_section("learning", {})
    interactions = list(data.get("interactions") or [])
    positives = [
        _memory_entry_from_interaction(item)
        for item in interactions
        if int(item.get("feedback_score", 0)) > 0
    ]
    return _match_entries(positives, query, context=context, limit=limit)


def _preferred_response_length(data: dict) -> str:
    scores = data.get("user_preferences", {}).get("scores", {})
    concise_score = float(scores.get("concise", 0.0) or 0.0)
    detailed_score = float(scores.get("detailed", 0.0) or 0.0)
    if concise_score - detailed_score >= 1.0:
        return "short"
    if detailed_score - concise_score >= 1.0:
        return "detailed"
    return "adaptive"


def _preferred_tone(data: dict) -> str:
    scores = data.get("user_preferences", {}).get("scores", {})
    tone_keys = ("friendly", "professional", "empathetic", "direct", "calm")
    ranked = sorted(((key, float(scores.get(key, 0.0) or 0.0)) for key in tone_keys), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] <= 0:
        return "adaptive"
    return ranked[0][0]


def _proactive_preference(data: dict) -> str:
    score = float(data.get("user_preferences", {}).get("scores", {}).get("proactive", 0.0) or 0.0)
    if score >= 1.5:
        return "high"
    if score <= -1.0:
        return "low"
    return "balanced"


def _behavior_learning_payload(data: dict) -> dict:
    behavior = data.get("behavior_profile", {}) if isinstance(data, dict) else {}
    active_windows = behavior.get("active_windows", {}) if isinstance(behavior.get("active_windows"), dict) else {}
    contexts = behavior.get("contexts", {}) if isinstance(behavior.get("contexts"), dict) else {}
    routes = behavior.get("routes", {}) if isinstance(behavior.get("routes"), dict) else {}
    topics = behavior.get("topics", {}) if isinstance(behavior.get("topics"), dict) else {}

    def _top_items(items: dict, limit: int = 4) -> list[dict]:
        ranked = sorted(((key, int(value or 0)) for key, value in items.items()), key=lambda item: item[1], reverse=True)
        return [{"name": key, "count": value} for key, value in ranked[:limit] if key]

    top_windows = _top_items(active_windows, limit=3)
    top_topics = _top_items(topics, limit=4)
    top_contexts = _top_items(contexts, limit=3)
    top_routes = _top_items(routes, limit=3)
    active_window = top_windows[0]["name"] if top_windows else "unknown"
    summary_parts = []
    if active_window != "unknown":
        summary_parts.append(f"Most active during the {active_window}.")
    if top_topics:
        summary_parts.append("Common topics: " + ", ".join(item["name"] for item in top_topics[:3]) + ".")
    if top_routes:
        summary_parts.append("Common routes: " + ", ".join(item["name"] for item in top_routes[:2]) + ".")
    if not summary_parts:
        summary_parts.append("Not enough interaction history yet to infer a strong behavior pattern.")
    return {
        "active_time_window": active_window,
        "top_windows": top_windows,
        "top_topics": top_topics,
        "top_contexts": top_contexts,
        "top_routes": top_routes,
        "summary": " ".join(summary_parts),
    }


def _automation_suggestions(data: dict) -> list[dict]:
    interactions = list(data.get("interactions") or [])
    signatures = Counter()
    examples = {}
    for item in interactions:
        text = _compact_text(item.get("user_text_preview")).lower()
        if not text:
            continue
        words = [word for word in text.split() if word not in {"please", "can", "you", "could", "me"}]
        signature = " ".join(words[:4]).strip()
        if not signature:
            continue
        signatures[signature] += 1
        examples.setdefault(signature, text)

    suggestions = []
    for signature, count in signatures.most_common(8):
        if count < 2:
            continue
        example = examples.get(signature, signature)
        if example.startswith("open "):
            target = example[5:].strip()
            message = f"You often open {target}. I can turn that into a one-step workflow."
        elif "weather" in example:
            message = "You often ask for weather updates. I can surface that automatically at the right time."
        elif any(token in example for token in ("plan my day", "today agenda", "what should i do")):
            message = "You often ask for planning help. A morning briefing workflow would fit well."
        else:
            message = f'You repeat "{signature}" quite often. A saved workflow or shortcut could make it instant.'
        suggestions.append(
            {
                "pattern": signature,
                "count": count,
                "message": message,
            }
        )
        if len(suggestions) >= 4:
            break
    return suggestions


def _prompt_optimization_payload(data: dict, query: str = "", context: str = "casual", emotion: str = "neutral") -> dict:
    instructions = []
    avoidance_rules = []
    length_preference = _preferred_response_length(data)
    tone_preference = _preferred_tone(data)
    proactive_preference = _proactive_preference(data)

    if length_preference == "short":
        instructions.append("Keep responses short and concise unless the user asks for more detail.")
    elif length_preference == "detailed":
        instructions.append("Provide a bit more depth when it helps instead of stopping too early.")

    if tone_preference == "professional" and _compact_text(context).lower() == "work":
        instructions.append("Use a more professional tone for work-focused requests.")
    elif tone_preference == "friendly":
        instructions.append("Keep the tone warm, casual, and human.")
    elif tone_preference == "empathetic" and _compact_text(emotion).lower() in {"sad", "angry"}:
        instructions.append("Lead with empathy before giving advice.")
    elif tone_preference == "direct":
        instructions.append("Prefer direct, practical wording.")
    elif tone_preference == "calm" and _compact_text(emotion).lower() == "angry":
        instructions.append("Stay calm and steady to help de-escalate the moment.")

    if proactive_preference == "high":
        instructions.append("When it helps, end with one useful next step or suggestion.")
    elif proactive_preference == "low":
        avoidance_rules.append("Do not add extra suggestions unless the user asks for them.")

    failed = similar_failed_patterns(query, context=context, limit=1) if _compact_text(query) else []
    if failed:
        failure_tags = ", ".join(failed[0].get("failure_tags", [])[:3]) or "an unhelpful answer pattern"
        avoidance_rules.append(f"Avoid repeating a previously unhelpful pattern: {failure_tags}.")
        note = _compact_text(failed[0].get("feedback_note"))
        if note and not note.lower().startswith("inferred from"):
            avoidance_rules.append(f"Feedback note to correct: {note}.")

    successful = best_response_matches(query, context=context, limit=1) if _compact_text(query) else []
    if successful:
        preview = _preview(successful[0].get("assistant_reply_preview", ""), 140)
        strategies = ", ".join(successful[0].get("strategies", [])[:4])
        if strategies:
            instructions.append(f"A similar successful reply used: {strategies}.")
        if preview:
            instructions.append(f"Reuse the shape of this kind of successful answer, but adapt it freshly: {preview}")

    summary = " ".join(instructions + avoidance_rules) or "Adaptive prompt optimization is active."
    return {
        "effective_instructions": instructions,
        "avoidance_rules": avoidance_rules,
        "summary": summary,
    }


def build_learning_prompt_boost(query: str = "", context: str = "casual", emotion: str = "neutral") -> str | None:
    data = load_section("learning", {})
    payload = _prompt_optimization_payload(data, query=query, context=context, emotion=emotion)
    hints = list(payload.get("effective_instructions") or [])
    if not hints and not payload.get("avoidance_rules"):
        scores = data.get("strategy_scores", {}) if isinstance(data, dict) else {}
        if not isinstance(scores, dict):
            scores = {}
        top_tags = [tag for tag, score in sorted(scores.items(), key=lambda item: item[1], reverse=True) if float(score or 0.0) > 0][:5]
        if "empathetic" in top_tags and _compact_text(emotion).lower() in {"sad", "angry"}:
            hints.append("A warmer, emotionally aware tone has worked well in similar moments.")
        if "professional" in top_tags and _compact_text(context).lower() == "work":
            hints.append("A practical, professional tone tends to land well for work-focused requests.")
        if "calm" in top_tags and _compact_text(emotion).lower() == "angry":
            hints.append("Keep the wording calm and steady.")
    lines = list(hints) + list(payload.get("avoidance_rules") or [])
    if not lines:
        return None
    return "Self-improvement guidance: " + " ".join(lines)


def learning_status_payload(snapshot: dict | None = None) -> dict:
    data = _ensure_learning_defaults(snapshot if isinstance(snapshot, dict) else load_section("learning", {}))
    interactions = list(data.get("interactions") or [])
    scores = data.get("strategy_scores", {}) if isinstance(data.get("strategy_scores"), dict) else {}
    top_strategies = [
        {"tag": tag, "score": round(float(score or 0.0), 3)}
        for tag, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:6]
    ]
    feedback_count = int(data.get("feedback_count", 0) or 0)
    positive = int(data.get("positive_feedback", 0) or 0)
    success_rate = round((positive / feedback_count) * 100, 1) if feedback_count else 0.0
    preferences = {
        "response_length": _preferred_response_length(data),
        "tone": _preferred_tone(data),
        "proactive_support": _proactive_preference(data),
    }
    behavior = _behavior_learning_payload(data)
    automation_suggestions = _automation_suggestions(data)
    prompt_optimization = _prompt_optimization_payload(data)
    best_responses = list(data.get("best_responses") or [])
    failed_responses = list(data.get("failed_responses") or [])
    return {
        "interaction_count": len(interactions),
        "feedback_count": feedback_count,
        "positive_feedback": positive,
        "negative_feedback": int(data.get("negative_feedback", 0) or 0),
        "success_rate": success_rate,
        "top_strategies": top_strategies,
        "user_preferences": preferences,
        "behavior_learning": behavior,
        "response_memory": {
            "best_response_count": len(best_responses),
            "failed_response_count": len(failed_responses),
            "best_examples": best_responses[-3:],
            "failed_examples": failed_responses[-3:],
        },
        "automation_suggestions": automation_suggestions,
        "prompt_optimization": prompt_optimization,
        "last_interaction": interactions[-1] if interactions else {},
        "summary": (
            f"Tracked {len(interactions)} learning interaction(s) with {feedback_count} feedback item(s). "
            f"Positive response rate: {success_rate}%. "
            f"Preferred style is {preferences['response_length']} and {preferences['tone']}."
        ),
    }
