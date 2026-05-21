"""Unified chat context: memory, prompt flags, and Ollama model routing."""

from __future__ import annotations

import logging
import os
from typing import Any

from core.prompt_memory_context import build_safe_memory_context
from core.prompt_mode_resolver import resolve_prompt_mode
from core.runtime_prompt_adapter import RUNTIME_PROMPT_ENV, TRUE_VALUES

try:
    from brain.semantic_memory import build_semantic_memory_context
except ImportError:  # pragma: no cover
    build_semantic_memory_context = None

try:
    from llm_client import generate_chat_reply, _resolved_provider
except ImportError:  # pragma: no cover
    generate_chat_reply = None

    def _resolved_provider() -> str:
        return "ollama"

try:
    from offline_multi_model import select_route
except ImportError:  # pragma: no cover
    select_route = None

try:
    from project_knowledge.project_context_adapter import is_project_context_enabled
except ImportError:  # pragma: no cover

    def is_project_context_enabled() -> bool:
        return False


logger = logging.getLogger(__name__)

CHAT_ENHANCED_ENV = "GRANDPA_CHAT_ENHANCED"
CHAT_SEMANTIC_MEMORY_ENV = "GRANDPA_CHAT_SEMANTIC_MEMORY"
CHAT_OLLAMA_ROUTING_ENV = "GRANDPA_CHAT_OLLAMA_ROUTING"
CHAT_PLANNING_MODE_ENV = "GRANDPA_CHAT_PLANNING_MODE"
FALSE_VALUES = {"0", "false", "no", "off"}


def _env_flag(name: str, *, default_when_unset: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default_when_unset
    normalized = str(raw).strip().lower()
    if normalized in FALSE_VALUES:
        return False
    return normalized in TRUE_VALUES


def chat_enhancements_enabled() -> bool:
    """Desktop chat enhancements default on unless GRANDPA_CHAT_ENHANCED=0."""
    return _env_flag(CHAT_ENHANCED_ENV, default_when_unset=True)


def semantic_memory_enabled_for_chat() -> bool:
    if not chat_enhancements_enabled():
        return _env_flag(CHAT_SEMANTIC_MEMORY_ENV, default_when_unset=False)
    return not os.getenv(CHAT_SEMANTIC_MEMORY_ENV, "").strip().lower() in FALSE_VALUES


def runtime_prompts_enabled_for_chat() -> bool:
    explicit = os.getenv(RUNTIME_PROMPT_ENV, "").strip().lower()
    if explicit in TRUE_VALUES:
        return True
    if explicit in FALSE_VALUES:
        return False
    return chat_enhancements_enabled()


def project_context_enabled_for_chat(user_message: str | None) -> bool:
    if is_project_context_enabled():
        return True
    if not chat_enhancements_enabled():
        return False
    try:
        mode = resolve_prompt_mode(user_message, default="default")
    except Exception:
        mode = "default"
    return mode == "coding"


def ollama_routing_enabled_for_chat() -> bool:
    if not chat_enhancements_enabled():
        return _env_flag(CHAT_OLLAMA_ROUTING_ENV, default_when_unset=False)
    return not os.getenv(CHAT_OLLAMA_ROUTING_ENV, "").strip().lower() in FALSE_VALUES


def planning_mode_enabled_for_chat() -> bool:
    """Enable planning runtime prompt mode for explicit planner-style chat."""
    if not chat_enhancements_enabled():
        return _env_flag(CHAT_PLANNING_MODE_ENV, default_when_unset=False)
    return not os.getenv(CHAT_PLANNING_MODE_ENV, "").strip().lower() in FALSE_VALUES


def resolve_chat_prompt_mode(user_message: str | None) -> str:
    return resolve_prompt_mode(
        user_message,
        default="default",
        allow_planning=planning_mode_enabled_for_chat(),
    )


def build_chat_memory_context(user_message: str) -> str:
    """Merge semantic memory (and future sources) into one safe prompt block."""
    if not semantic_memory_enabled_for_chat():
        return ""
    parts: list[str] = []
    if build_semantic_memory_context is not None:
        try:
            semantic = build_semantic_memory_context(user_message)
            if semantic:
                parts.append(str(semantic).strip())
        except Exception as error:  # pragma: no cover
            logger.warning("Semantic memory context failed: %s", error)
    combined = "\n\n".join(part for part in parts if part)
    return build_safe_memory_context(combined) if combined else ""


def resolve_chat_llm_model(user_message: str) -> str | None:
    """Pick an Ollama model from offline_multi_model when provider is ollama."""
    if not ollama_routing_enabled_for_chat() or select_route is None:
        return None
    try:
        if _resolved_provider() != "ollama":
            return None
        routing = select_route(user_message, mode="auto")
        model = str(routing.get("model") or "").strip()
        return model or None
    except Exception as error:  # pragma: no cover
        logger.warning("Ollama route selection failed: %s", error)
        return None


def default_chat_provider(history: list[dict[str, str]], user_message: str, system_prompt: str | None = None) -> str:
    if generate_chat_reply is None:
        raise RuntimeError("LLM client is not available.")
    model = resolve_chat_llm_model(user_message)
    return generate_chat_reply(history, user_message, model=model, system_prompt=system_prompt)


def chat_enhancement_status() -> dict[str, Any]:
    return {
        "chat_enhanced": chat_enhancements_enabled(),
        "semantic_memory": semantic_memory_enabled_for_chat(),
        "runtime_prompts": runtime_prompts_enabled_for_chat(),
        "ollama_routing": ollama_routing_enabled_for_chat(),
        "planning_mode": planning_mode_enabled_for_chat(),
    }
