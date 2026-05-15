from __future__ import annotations

from collections.abc import Iterable

from .prompt_loader import load_prompt
from .prompt_modes import validate_mode


BASE_PROMPT = "base/core.txt"
SAFETY_PROMPT = "safety/automation_safety.txt"
TOOL_PROMPT = "tools/tool_rules.txt"
MODE_PROMPTS = {
    "default": "modes/default.txt",
    "coding": "modes/coding.txt",
    "voice": "modes/voice.txt",
    "vision": "modes/vision.txt",
    "research": "modes/research.txt",
    "automation": "safety/automation_safety.txt",
    "planning": "modes/planning.txt",
}


def normalize_prompt_sections(sections: Iterable[str | None]) -> list[str]:
    """Trim prompt sections and remove exact duplicates while preserving order."""
    normalized: list[str] = []
    seen: set[str] = set()
    for section in sections:
        text = (section or "").strip()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)
    return normalized


def build_mode_prompt(mode: str = "default") -> str:
    prompt_mode = validate_mode(mode)
    return load_prompt(MODE_PROMPTS[prompt_mode])


def _context_section(title: str, value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    return f"{title}:\n{text}"


def build_system_prompt(
    mode: str = "default",
    *,
    memory_context: str | None = None,
    extra_context: str | None = None,
    include_safety: bool = True,
    include_tools: bool = True,
) -> str:
    """Compose a runtime system prompt without calling any model provider."""
    sections: list[str | None] = [
        load_prompt(BASE_PROMPT),
        build_mode_prompt(mode),
    ]
    if include_safety:
        sections.append(load_prompt(SAFETY_PROMPT))
    if include_tools:
        sections.append(load_prompt(TOOL_PROMPT))
    sections.extend(
        [
            _context_section("Memory context", memory_context),
            _context_section("Additional context", extra_context),
        ]
    )
    return "\n\n".join(normalize_prompt_sections(sections))
