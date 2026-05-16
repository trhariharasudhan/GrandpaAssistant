from __future__ import annotations

import logging
import os

from .prompt_builder import build_system_prompt
from .prompt_runtime_observability import build_prompt_runtime_metadata


logger = logging.getLogger(__name__)

RUNTIME_PROMPT_ENV = "GRANDPA_USE_RUNTIME_PROMPTS"
TRUE_VALUES = {"1", "true", "yes", "on"}
SAFE_MINIMAL_SYSTEM_PROMPT = (
    "You are GrandpaAssistant, a practical and safe local-first assistant. "
    "Answer clearly and ask before risky actions."
)


def _env_enabled() -> bool:
    return os.getenv(RUNTIME_PROMPT_ENV, "").strip().lower() in TRUE_VALUES


def get_runtime_system_prompt(
    mode: str = "default",
    *,
    memory_context: str | None = None,
    extra_context: str | None = None,
    use_runtime_prompts: bool | None = None,
    fallback_prompt: str | None = None,
    project_context_included: bool = False,
    project_context_result_count: int = 0,
) -> str:
    """Return a system prompt using the optional runtime prompt foundation.

    Runtime prompts are used only when explicitly enabled by the
    ``use_runtime_prompts`` argument or by ``GRANDPA_USE_RUNTIME_PROMPTS``.
    When disabled, this function returns ``fallback_prompt`` or a safe minimal
    default. Any runtime prompt loading/building error also falls back safely.
    """
    prompt, _metadata = get_runtime_system_prompt_with_metadata(
        mode,
        memory_context=memory_context,
        extra_context=extra_context,
        use_runtime_prompts=use_runtime_prompts,
        fallback_prompt=fallback_prompt,
        project_context_included=project_context_included,
        project_context_result_count=project_context_result_count,
    )
    return prompt


def get_runtime_system_prompt_with_metadata(
    mode: str = "default",
    *,
    memory_context: str | None = None,
    extra_context: str | None = None,
    use_runtime_prompts: bool | None = None,
    fallback_prompt: str | None = None,
    project_context_included: bool = False,
    project_context_result_count: int = 0,
) -> tuple[str, dict]:
    """Return a system prompt plus safe selection metadata.

    Metadata never includes prompt text, memory content, or extra context.
    """
    enabled = _env_enabled() if use_runtime_prompts is None else bool(use_runtime_prompts)
    fallback = (fallback_prompt or "").strip() or SAFE_MINIMAL_SYSTEM_PROMPT
    has_memory_context = bool((memory_context or "").strip())
    if not enabled:
        return fallback, build_prompt_runtime_metadata(
            runtime_enabled=False,
            selected_mode=mode,
            source="legacy",
            fallback_used=True,
            prompt_length=len(fallback),
            reason="runtime_prompts_disabled",
            memory_context_included=False,
            project_context_included=False,
            project_context_result_count=0,
        )

    try:
        prompt = build_system_prompt(
            mode,
            memory_context=memory_context,
            extra_context=extra_context,
        ).strip()
    except Exception as exc:  # pragma: no cover - exact failures are tested with mocks
        logger.warning("Runtime prompt build failed for mode %r: %s", mode, exc)
        return fallback, build_prompt_runtime_metadata(
            runtime_enabled=True,
            selected_mode=mode,
            source="legacy",
            fallback_used=True,
            prompt_length=len(fallback),
            reason="runtime_prompt_build_failed",
            memory_context_included=False,
            project_context_included=False,
            project_context_result_count=0,
        )

    if not prompt:
        return fallback, build_prompt_runtime_metadata(
            runtime_enabled=True,
            selected_mode=mode,
            source="legacy",
            fallback_used=True,
            prompt_length=len(fallback),
            reason="runtime_prompt_empty",
            memory_context_included=False,
            project_context_included=False,
            project_context_result_count=0,
        )

    return prompt, build_prompt_runtime_metadata(
        runtime_enabled=True,
        selected_mode=mode,
        source="runtime",
        fallback_used=False,
        prompt_length=len(prompt),
        reason=None,
        memory_context_included=has_memory_context,
        project_context_included=project_context_included,
        project_context_result_count=project_context_result_count,
    )
