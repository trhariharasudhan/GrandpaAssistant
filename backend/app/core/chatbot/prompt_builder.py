from __future__ import annotations

from core.prompts import build_terminal_prompt


def build_system_prompt(
    user_message: str,
    *,
    memories: list[dict],
    recent_messages: list[dict],
) -> str:
    return build_terminal_prompt(user_message, memories=memories, recent_messages=recent_messages)
