from __future__ import annotations

from typing import Iterable


DEFAULT_PROMPT_MODE = "default"
SUPPORTED_PROMPT_MODES = frozenset(
    {
        "default",
        "coding",
        "voice",
        "vision",
        "research",
        "automation",
        "planning",
    }
)


def normalize_mode(mode: str | None) -> str:
    """Return a supported prompt mode, falling back to default for blank input."""
    normalized = (mode or DEFAULT_PROMPT_MODE).strip().lower()
    if not normalized:
        return DEFAULT_PROMPT_MODE
    return normalized


def is_supported_mode(mode: str | None) -> bool:
    return normalize_mode(mode) in SUPPORTED_PROMPT_MODES


def validate_mode(mode: str | None) -> str:
    normalized = normalize_mode(mode)
    if normalized not in SUPPORTED_PROMPT_MODES:
        supported = ", ".join(sorted(SUPPORTED_PROMPT_MODES))
        raise ValueError(f"Unsupported prompt mode '{mode}'. Supported modes: {supported}")
    return normalized


def list_supported_modes() -> list[str]:
    return sorted(SUPPORTED_PROMPT_MODES)


def filter_supported_modes(modes: Iterable[str]) -> list[str]:
    return [validate_mode(mode) for mode in modes]
