from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path


logger = logging.getLogger(__name__)

PROMPT_ROOT = Path(__file__).resolve().parents[1] / "prompts"


def _resolve_prompt_path(relative_path: str) -> Path:
    candidate = (PROMPT_ROOT / relative_path).resolve()
    root = PROMPT_ROOT.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Prompt path escapes prompt root: {relative_path}") from exc
    return candidate


@lru_cache(maxsize=64)
def load_prompt(relative_path: str) -> str:
    """Load a prompt file relative to backend/app/prompts.

    Missing prompt files are safe: the function logs and returns an empty string.
    Path traversal attempts raise ValueError instead of reading outside the prompt root.
    """
    path = _resolve_prompt_path(relative_path)
    if not path.is_file():
        logger.warning("Prompt file not found: %s", relative_path)
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.error("Unable to load prompt file %s: %s", relative_path, exc)
        return ""


def prompt_exists(relative_path: str) -> bool:
    return _resolve_prompt_path(relative_path).is_file()


def list_available_prompts() -> list[str]:
    if not PROMPT_ROOT.exists():
        return []
    prompts: list[str] = []
    for path in PROMPT_ROOT.rglob("*.txt"):
        if path.is_file():
            prompts.append(path.relative_to(PROMPT_ROOT).as_posix())
    return sorted(prompts)
