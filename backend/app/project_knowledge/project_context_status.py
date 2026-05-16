from __future__ import annotations

from pathlib import Path
from typing import Any

from core.runtime_prompt_adapter import RUNTIME_PROMPT_ENV

from .config import DEFAULT_LIMITS
from .project_context_adapter import PROJECT_CONTEXT_ENV, is_project_context_enabled


def _available(project_root: Any | None) -> bool:
    if project_root is None:
        return True
    try:
        root = Path(project_root)
        return root.exists() and root.is_dir()
    except (OSError, TypeError, ValueError):
        return False


def summarize_project_context_adapter_result(result: dict) -> dict:
    summary = result.get("summary") if isinstance(result, dict) and isinstance(result.get("summary"), dict) else {}
    error = result.get("error") if isinstance(result, dict) else None
    context_text = result.get("context_text") if isinstance(result, dict) else ""
    return {
        "enabled": bool(result.get("enabled")) if isinstance(result, dict) else False,
        "result_count": int(summary.get("result_count") or 0),
        "has_error": bool(error),
        "error_type": str(error or "")[:80] if error else None,
        "context_included": bool(context_text and int(summary.get("result_count") or 0)),
        "total_chars": int(summary.get("total_chars") or 0),
    }


def get_project_context_status(project_root: Any | None = None) -> dict:
    try:
        available = _available(project_root)
    except Exception:
        available = False
    return {
        "project_context_enabled": is_project_context_enabled(),
        "env_var": PROJECT_CONTEXT_ENV,
        "requires_runtime_prompts": True,
        "runtime_prompt_env_var": RUNTIME_PROMPT_ENV,
        "available": bool(available),
        "safe_to_expose": True,
        "supported_search": "lexical",
        "embeddings_enabled": False,
        "vector_db_enabled": False,
        "active_consumer": "chat_service",
        "context_body_exposed": False,
        "snippet_body_exposed": False,
        "reference_folder_used": False,
        "limits": {
            "max_context_results": DEFAULT_LIMITS.max_context_results,
            "max_context_total_chars": DEFAULT_LIMITS.max_context_total_chars,
            "max_context_block_chars": DEFAULT_LIMITS.max_context_block_chars,
        },
        "last_retrieval": None,
    }
