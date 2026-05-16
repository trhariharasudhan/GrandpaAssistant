from __future__ import annotations

from pathlib import Path
from typing import Any

from .cache import build_cache_manifest, is_cache_valid, load_project_cache, save_project_cache
from .chunker import chunk_file
from .config import DEFAULT_LIMITS
from .file_discovery import discover_project_files
from .lexical_index import index_chunks, search_lexical_index
from .project_search import _safe_query


def _safe_root(project_root: Any) -> Path | None:
    try:
        root = Path(project_root).resolve()
    except (OSError, TypeError, ValueError):
        return None
    if not root.exists() or not root.is_dir():
        return None
    return root


def _build_cache_data(project_root: Path) -> dict:
    discovered = discover_project_files(project_root)
    chunks: list[dict] = []
    for item in discovered:
        relative_path = item.get("relative_path", "")
        result = chunk_file(project_root / relative_path, project_root=project_root)
        if result.get("ok"):
            chunks.extend(result.get("chunks") or [])
    lexical_index = index_chunks(chunks)
    lexical_index.setdefault("stats", {})
    lexical_index["stats"]["project_root"] = str(project_root)
    lexical_index["stats"]["files_considered"] = len(discovered)
    manifest = build_cache_manifest(project_root, files=discovered, chunks=chunks)
    return {"manifest": manifest, "chunks": chunks, "lexical_index": lexical_index}


def build_or_load_cached_index(project_root: Any) -> dict:
    root = _safe_root(project_root)
    if root is None:
        return {
            "ok": False,
            "source": "invalid",
            "lexical_index": index_chunks([]),
            "manifest": {},
            "cache_saved": False,
            "error": "invalid_project_root",
        }

    cached = load_project_cache(root)
    if cached.get("ok") and is_cache_valid(root, cached.get("manifest", {})):
        return {
            "ok": True,
            "source": "cache",
            "lexical_index": cached.get("lexical_index", {}),
            "manifest": cached.get("manifest", {}),
            "cache_saved": True,
            "error": None,
        }

    data = _build_cache_data(root)
    save_result = save_project_cache(root, data)
    return {
        "ok": True,
        "source": "rebuilt",
        "lexical_index": data["lexical_index"],
        "manifest": data["manifest"],
        "cache_saved": bool(save_result.get("ok")),
        "error": save_result.get("error"),
    }


def cached_search_project(project_root: Any, query: Any, limit: int = 10) -> dict:
    safe_query = _safe_query(query)
    try:
        result_limit = max(1, min(int(limit or DEFAULT_LIMITS.max_search_results), DEFAULT_LIMITS.max_search_results))
    except (TypeError, ValueError):
        result_limit = DEFAULT_LIMITS.max_search_results

    cached = build_or_load_cached_index(project_root)
    index = cached.get("lexical_index", {}) if isinstance(cached, dict) else {}
    results = search_lexical_index(index, safe_query, limit=result_limit)
    return {
        "query": safe_query,
        "result_count": len(results),
        "results": results,
        "stats": index.get("stats", {}) if isinstance(index, dict) else {},
        "cache": {
            "source": cached.get("source", "unknown") if isinstance(cached, dict) else "unknown",
            "cache_saved": bool(cached.get("cache_saved")) if isinstance(cached, dict) else False,
            "error": cached.get("error") if isinstance(cached, dict) else "cache_failed",
        },
        "safe": True,
    }
