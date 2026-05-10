from __future__ import annotations

from .language import detect_language_style, language_instruction


def build_system_prompt(
    user_message: str,
    *,
    memories: list[dict],
    recent_messages: list[dict],
) -> str:
    style = detect_language_style(user_message)
    memory_lines = [f"- {item.get('fact')}" for item in memories if item.get("fact")]
    context_lines = []
    for item in recent_messages:
        role = item.get("role", "user")
        text = item.get("message", "")
        if text:
            context_lines.append(f"{role.title()}: {text}")
    return "\n".join(
        [
            "Assistant name: Grandpa.",
            "Personality: friendly, casual, helpful, practical.",
            language_instruction(style),
            "For technical questions, give clear step-by-step answers.",
            "If the user asks for code, provide complete working code, not partial snippets.",
            "Do not repeat the user's question as the answer.",
            "Do not reuse unrelated previous topics.",
            "If you do not know, say so honestly.",
            "Never expose secrets or ask for API keys in chat.",
            "Politely refuse harmful or illegal requests and redirect safely.",
            "",
            "Saved user memory:",
            "\n".join(memory_lines) if memory_lines else "- None saved.",
            "",
            "Recent conversation context:",
            "\n".join(context_lines) if context_lines else "- No recent context.",
            "",
            f"User: {user_message}",
            "Grandpa:",
        ]
    )
