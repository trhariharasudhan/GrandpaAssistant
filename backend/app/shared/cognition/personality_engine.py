from __future__ import annotations


def _compact_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def resolve_personality_mode(context: str = "casual", emotion: str = "neutral", user_text: str = "") -> str:
    normalized_context = _compact_text(context).lower() or "casual"
    normalized_emotion = _compact_text(emotion).lower() or "neutral"
    lowered = _compact_text(user_text).lower()

    if normalized_emotion == "sad":
        return "empathetic"
    if normalized_emotion == "angry":
        return "calm"
    if normalized_context == "work" or any(token in lowered for token in ("deadline", "client", "meeting", "project", "code", "bug")):
        return "professional"
    if normalized_context == "emotional":
        return "empathetic"
    return "friendly"


def build_personality_instruction(context: str = "casual", emotion: str = "neutral", user_text: str = "") -> str:
    mode = resolve_personality_mode(context=context, emotion=emotion, user_text=user_text)
    mapping = {
        "friendly": "Use a warm, casual, natural tone. Keep it easygoing and human.",
        "professional": "Use a calm, clear, practical tone. Stay slightly professional without sounding stiff.",
        "empathetic": "Use a gentle, supportive tone. Be warm and emotionally aware without being dramatic.",
        "calm": "Stay calm, grounded, and de-escalating. Keep the wording measured and respectful.",
    }
    return f"Dynamic personality mode: {mode}. {mapping.get(mode, mapping['friendly'])}"


def personality_status_payload(context: str = "casual", emotion: str = "neutral", user_text: str = "") -> dict:
    mode = resolve_personality_mode(context=context, emotion=emotion, user_text=user_text)
    return {
        "mode": mode,
        "instruction": build_personality_instruction(context=context, emotion=emotion, user_text=user_text),
    }
