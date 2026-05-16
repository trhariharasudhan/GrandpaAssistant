from __future__ import annotations

from typing import TypedDict


MAX_REASON_LENGTH = 120
VALID_SOURCES = {"legacy", "runtime"}


class PromptRuntimeMetadata(TypedDict):
    runtime_enabled: bool
    selected_mode: str
    source: str
    fallback_used: bool
    prompt_length: int | None
    reason: str | None
    memory_context_included: bool
    project_context_included: bool
    project_context_result_count: int


def _normalize_text(value: str | None, *, default: str, max_length: int | None = None) -> str:
    text = " ".join(str(value or "").split()).strip().lower()
    if not text:
        text = default
    if max_length is not None and len(text) > max_length:
        text = text[:max_length].rstrip()
    return text


def build_prompt_runtime_metadata(
    *,
    runtime_enabled: bool,
    selected_mode: str,
    source: str,
    fallback_used: bool,
    prompt_length: int | None = None,
    reason: str | None = None,
    memory_context_included: bool = False,
    project_context_included: bool = False,
    project_context_result_count: int = 0,
) -> PromptRuntimeMetadata:
    """Build JSON-safe prompt runtime metadata without prompt or context bodies."""
    normalized_source = _normalize_text(source, default="legacy")
    if normalized_source not in VALID_SOURCES:
        normalized_source = "legacy"
    normalized_mode = _normalize_text(selected_mode, default="default")
    normalized_reason = _normalize_text(reason, default="", max_length=MAX_REASON_LENGTH) if reason else None
    safe_length = prompt_length if isinstance(prompt_length, int) and prompt_length >= 0 else None
    safe_project_count = project_context_result_count if isinstance(project_context_result_count, int) and project_context_result_count >= 0 else 0
    return {
        "runtime_enabled": bool(runtime_enabled),
        "selected_mode": normalized_mode,
        "source": normalized_source,
        "fallback_used": bool(fallback_used),
        "prompt_length": safe_length,
        "reason": normalized_reason,
        "memory_context_included": bool(memory_context_included),
        "project_context_included": bool(project_context_included),
        "project_context_result_count": safe_project_count,
    }
