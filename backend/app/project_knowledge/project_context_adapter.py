from __future__ import annotations

import os
from typing import Any

from .retrieval_context import build_retrieval_context, format_retrieval_context_for_prompt, summarize_retrieval_context


PROJECT_CONTEXT_ENV = "GRANDPA_USE_PROJECT_CONTEXT"
TRUE_VALUES = {"1", "true", "yes", "on"}


def is_project_context_enabled() -> bool:
    return os.getenv(PROJECT_CONTEXT_ENV, "").strip().lower() in TRUE_VALUES


def build_project_context_for_prompt(
    *,
    project_root: Any,
    user_message: Any,
    limit: int = 5,
) -> dict:
    if not is_project_context_enabled():
        return {
            "enabled": False,
            "context_text": "",
            "summary": {
                "query": "",
                "result_count": 0,
                "total_chars": 0,
                "files": [],
                "truncated": False,
                "safe": True,
            },
            "error": None,
        }

    try:
        context = build_retrieval_context(project_root, user_message, limit=limit)
        context_text = format_retrieval_context_for_prompt(context)
        summary = summarize_retrieval_context(context)
        return {
            "enabled": True,
            "context_text": context_text,
            "summary": summary,
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - defensive adapter boundary
        return {
            "enabled": True,
            "context_text": "",
            "summary": {
                "query": "",
                "result_count": 0,
                "total_chars": 0,
                "files": [],
                "truncated": False,
                "safe": True,
            },
            "error": exc.__class__.__name__,
        }
