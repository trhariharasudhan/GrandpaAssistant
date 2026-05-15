from __future__ import annotations

from typing import Any


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _recent_history_context(history: list[dict] | None, *, limit: int = 6) -> str:
    items = list(history or [])[-limit:]
    lines = []
    for item in items:
        role = _compact_text((item or {}).get("role", "")).lower() or "user"
        content = _compact_text((item or {}).get("content", ""))
        if content:
            lines.append(f"{role.title()}: {content}")
    return "Recent conversation:\n" + "\n".join(lines) if lines else ""


def build_web_api_system_prompt(
    *,
    system_prompt: str,
    tone: str,
    response_style: str,
    tool_mode: bool,
    tool_prompt: str,
    provider: str,
    emotion_context: str = "",
    mood_context: str = "",
    intelligence_context: str = "",
) -> str:
    language_guidance = (
        "Understand Tanglish or mixed Tamil-English input, but always reply only in natural English unless the user explicitly asks for translation. "
    )
    conversation_guidance = (
        "Talk like a smart, friendly real person. In normal chat, keep replies short, usually 1 or 2 sentences unless the user asks for more. "
        "Use natural language like hey, yeah, okay, or got it when it fits. Avoid robotic phrasing, bullet lists, and overly structured formatting in casual conversation. "
        "Match the user's mood and keep the flow natural. "
    )
    provider_guidance = ""
    if provider == "ollama":
        provider_guidance = (
            "When the user asks a normal question, answer directly in plain language. "
            "Do not rewrite the user's request into a task or instruction block. "
            "Use TOOL only for clear assistant actions like opening apps, creating reminders, checking notes, or device control. "
            "If the user asks for an exact sentence, return only that sentence."
        )
    return (
        f"{system_prompt} "
        f"Tone: {tone}. Response style: {response_style}. "
        f"{conversation_guidance}"
        f"{language_guidance}"
        f"{emotion_context} "
        f"{mood_context} "
        f"{intelligence_context} "
        f"{provider_guidance} "
        f"{tool_prompt if tool_mode else ''}"
    ).strip()


def build_web_api_chat_prompt(
    *,
    user_message: str,
    memory_context: str = "",
    document_context: str = "",
    emotion_context: str = "",
    mood_context: str = "",
    intelligence_context: str = "",
) -> str:
    if not memory_context and not document_context:
        return f"{emotion_context}\n{mood_context}\n{intelligence_context or ''}\nUser question: {user_message}"

    sections = []
    if memory_context:
        sections.append(memory_context)
    if document_context:
        sections.append(document_context)
    combined_context = "\n\n".join(sections)

    guidance = (
        "Answer clearly using the provided context when relevant. Keep it natural and easy to read. "
        "If the attached document does not contain the answer, say that briefly."
        if document_context
        else "Answer clearly, keep it natural, and use the saved memory only when it helps the user."
    )
    return (
        f"{combined_context}\n\n"
        f"{emotion_context}\n"
        f"{mood_context}\n"
        f"{intelligence_context or ''}\n"
        f"User question: {user_message}\n"
        f"{guidance}"
    )


def build_streaming_chat_prompt(**kwargs) -> str:
    return build_web_api_chat_prompt(**kwargs)


def build_chat_api_prompt(
    *,
    message: str,
    direct_memory_context: str = "",
    memory_context: str = "",
    emotion_context: str = "",
    mood_context: str = "",
    intelligence_context: str = "",
    history: list[dict] | None = None,
    hardware_context: str = "",
) -> tuple[str, str | None]:
    memory_sections = []
    if direct_memory_context and direct_memory_context.lower() not in (memory_context or "").lower():
        memory_sections.append(f"Relevant saved fact: {direct_memory_context}")
    if memory_context:
        memory_sections.append(memory_context)

    if not memory_sections:
        chat_prompt = (
            f"User question: {message}\n"
            f"{emotion_context}\n"
            f"{mood_context}\n"
            f"{intelligence_context or ''}\n"
            "Reply in natural English only. Talk like a smart, friendly real person. "
            "Keep casual chat short and natural, usually 1 or 2 sentences unless the user asks for more. "
            "Understand Tanglish input, but do not answer in Tanglish."
        )
    else:
        combined_memory_context = "\n\n".join(section for section in memory_sections if section)
        chat_prompt = (
            f"{combined_memory_context}\n\n"
            f"User question: {message}\n"
            f"{emotion_context}\n"
            f"{mood_context}\n"
            f"{intelligence_context or ''}\n"
            "Answer naturally in English only. Talk like a smart, friendly real person. "
            "Use the saved memory only when it helps with the user's question. "
            "Keep casual chat short and natural, usually 1 or 2 sentences unless the user asks for more. "
            "Understand Tanglish input, but do not answer in Tanglish."
        )

    prompt_sections = []
    if hardware_context:
        prompt_sections.append(hardware_context)
    recent_history = _recent_history_context(history)
    if recent_history:
        prompt_sections.append(recent_history)
    prompt_sections.append(chat_prompt)
    if hardware_context:
        prompt_sections.append("Use the hardware context only when it is relevant to the request.")
    return "\n\n".join(section for section in prompt_sections if section), hardware_context or None
