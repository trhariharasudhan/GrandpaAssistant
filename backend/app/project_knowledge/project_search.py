from __future__ import annotations

from typing import Any

from .config import DEFAULT_LIMITS
from .lexical_index import build_lexical_index, search_lexical_index


def _safe_query(query: Any) -> str:
    try:
        return str(query or "")[: DEFAULT_LIMITS.max_query_chars]
    except Exception:
        return ""


def search_project(project_root: Any, query: Any, limit: int = 10) -> dict:
    safe_query = _safe_query(query)
    try:
        result_limit = max(1, min(int(limit or DEFAULT_LIMITS.max_search_results), DEFAULT_LIMITS.max_search_results))
    except (TypeError, ValueError):
        result_limit = DEFAULT_LIMITS.max_search_results

    index = build_lexical_index(project_root)
    results = search_lexical_index(index, safe_query, limit=result_limit)
    return {
        "query": safe_query,
        "result_count": len(results),
        "results": results,
        "stats": index.get("stats", {}) if isinstance(index, dict) else {},
        "safe": True,
    }
