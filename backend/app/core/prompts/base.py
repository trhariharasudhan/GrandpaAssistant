from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PromptBuildRequest:
    user_message: str
    channel: str = "desktop"
    persona: str = "friendly"
    personality: str = "friendly, casual, helpful, practical"
    language_style: str = "auto"
    response_style: str = "natural"
    tone: str = "friendly"
    saved_memories: list[str] = field(default_factory=list)
    recent_history: list[dict] = field(default_factory=list)
    context_blocks: list[str] = field(default_factory=list)
    local_knowledge: str = ""
    safety_rules: list[str] = field(default_factory=list)
    code_instructions: list[str] = field(default_factory=list)
    channel_instructions: list[str] = field(default_factory=list)
    compact: bool = False
    assistant_label: str = "Grandpa"
    user_label: str = "User"
