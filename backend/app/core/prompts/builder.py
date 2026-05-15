from __future__ import annotations

from .base import PromptBuildRequest
from .context_blocks import render_bullets, render_history
from .language_style import detect_language_style, language_instruction
from .policies import DEFAULT_CODE_INSTRUCTIONS, DEFAULT_SAFETY_RULES


def _style_for(request: PromptBuildRequest) -> str:
    if request.language_style and request.language_style != "auto":
        return request.language_style
    return detect_language_style(request.user_message)


def build_prompt(request: PromptBuildRequest) -> str:
    style = _style_for(request)
    safety_rules = request.safety_rules or DEFAULT_SAFETY_RULES
    code_instructions = request.code_instructions or DEFAULT_CODE_INSTRUCTIONS
    lines = [
        f"Assistant name: {request.assistant_label}.",
        f"Personality: {request.personality}.",
        f"Channel: {request.channel}. Tone: {request.tone}. Response style: {request.response_style}.",
        language_instruction(style, english_only_for_mixed_input=request.channel in {"desktop", "api", "voice"}),
    ]
    lines.extend(code_instructions)
    lines.extend(safety_rules)
    lines.extend(request.channel_instructions)
    if request.compact:
        lines.append("Reply in 1 or 2 short sentences. Keep it easy to hear in voice mode.")
    if request.context_blocks:
        lines.extend(["", "Additional context:", "\n\n".join(block for block in request.context_blocks if block)])
    if request.local_knowledge:
        lines.extend(["", "Project or local knowledge context:", request.local_knowledge])
    lines.extend(["", "Saved user memory:", render_bullets(request.saved_memories, empty="- None saved.")])
    lines.extend(["", "Recent conversation context:", render_history(request.recent_history)])
    lines.extend(["", f"{request.user_label}: {request.user_message}", f"{request.assistant_label}:"])
    return "\n".join(str(line) for line in lines if line is not None)


def build_terminal_prompt(user_message: str, *, memories: list[dict], recent_messages: list[dict]) -> str:
    return build_prompt(
        PromptBuildRequest(
            user_message=user_message,
            channel="terminal",
            personality="friendly, casual, helpful, practical",
            saved_memories=[item.get("fact", "") for item in memories or [] if item.get("fact")],
            recent_history=recent_messages or [],
            assistant_label="Grandpa",
            user_label="User",
            channel_instructions=["Keep terminal chat concise and easy to read."],
        )
    )
