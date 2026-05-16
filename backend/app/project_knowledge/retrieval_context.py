from __future__ import annotations

import re
from typing import Any

from .config import CONTEXT_HEADER, CONTEXT_SNIPPET_SEPARATOR, DEFAULT_LIMITS
from .content_reader import redact_obvious_secrets
from .project_search import search_project


_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _clean_text(value: Any) -> str:
    try:
        text = str(value or "")
    except Exception:
        return ""
    text = _CONTROL_RE.sub("", text)
    redacted, _changed = redact_obvious_secrets(text)
    return redacted


def _line_range(result: dict) -> str:
    start = int(result.get("line_start") or 1)
    end = int(result.get("line_end") or start)
    if start == end:
        return str(start)
    return f"{start}-{end}"


def _block_title(result: dict) -> str:
    path = _clean_text(result.get("relative_path"))
    return f"{path}:{_line_range(result)}" if path else _line_range(result)


def build_retrieval_context(
    project_root: Any,
    query: Any,
    *,
    limit: int = 5,
    max_total_chars: int | None = None,
) -> dict:
    try:
        safe_limit = max(1, min(int(limit or DEFAULT_LIMITS.max_context_results), DEFAULT_LIMITS.max_context_results))
    except (TypeError, ValueError):
        safe_limit = DEFAULT_LIMITS.max_context_results
    total_limit = max(1, int(max_total_chars or DEFAULT_LIMITS.max_context_total_chars))

    search = search_project(project_root, query, limit=safe_limit)
    context_blocks: list[dict] = []
    total_chars = 0
    truncated = False

    for result in search.get("results", [])[:safe_limit]:
        snippet = _clean_text(result.get("snippet"))[: DEFAULT_LIMITS.max_context_block_chars]
        block_overhead = len(_block_title(result)) + 64
        remaining = total_limit - total_chars - block_overhead
        if remaining <= 0:
            truncated = True
            break
        if len(snippet) > remaining:
            snippet = snippet[:remaining]
            truncated = True
        if len(_clean_text(result.get("snippet"))) > DEFAULT_LIMITS.max_context_block_chars:
            truncated = True

        block = {
            "title": _block_title(result),
            "relative_path": _clean_text(result.get("relative_path")),
            "chunk_id": _clean_text(result.get("chunk_id")),
            "score": float(result.get("score") or 0.0),
            "line_range": _line_range(result),
            "text": snippet,
        }
        block_chars = len(format_retrieval_context_for_prompt({"context_blocks": [block]}, include_header=False))
        if total_chars + block_chars > total_limit:
            truncated = True
            break
        context_blocks.append(block)
        total_chars += block_chars

    return {
        "query": search.get("query", ""),
        "safe": True,
        "result_count": len(context_blocks),
        "truncated": truncated or len(search.get("results", [])) > len(context_blocks),
        "total_chars": total_chars,
        "context_blocks": context_blocks,
        "metadata": {
            "source": "project_knowledge.lexical_search",
            "search_result_count": search.get("result_count", 0),
            "max_context_results": DEFAULT_LIMITS.max_context_results,
            "max_context_total_chars": total_limit,
            "max_context_block_chars": DEFAULT_LIMITS.max_context_block_chars,
            "stats": search.get("stats", {}),
        },
    }


def format_retrieval_context_for_prompt(context: dict, *, include_header: bool = True) -> str:
    blocks = context.get("context_blocks") if isinstance(context, dict) else []
    if not isinstance(blocks, list) or not blocks:
        return CONTEXT_HEADER if include_header else ""

    parts: list[str] = [CONTEXT_HEADER] if include_header else []
    total_limit = DEFAULT_LIMITS.max_context_total_chars
    for block in blocks:
        if not isinstance(block, dict):
            continue
        path = _clean_text(block.get("relative_path"))
        line_range = _clean_text(block.get("line_range"))
        text = _clean_text(block.get("text"))[: DEFAULT_LIMITS.max_context_block_chars]
        rendered = f"File: {path}\nLines: {line_range}\nSnippet:\n{text}"
        candidate = CONTEXT_SNIPPET_SEPARATOR.join([*parts, rendered]) if parts else rendered
        if len(candidate) > total_limit:
            break
        parts.append(rendered)

    return CONTEXT_SNIPPET_SEPARATOR.join(parts)[:total_limit]


def summarize_retrieval_context(context: dict) -> dict:
    blocks = context.get("context_blocks") if isinstance(context, dict) else []
    files: list[str] = []
    seen: set[str] = set()
    if isinstance(blocks, list):
        for block in blocks:
            if not isinstance(block, dict):
                continue
            path = _clean_text(block.get("relative_path"))
            if path and path not in seen:
                seen.add(path)
                files.append(path)

    return {
        "query": context.get("query", "") if isinstance(context, dict) else "",
        "result_count": context.get("result_count", 0) if isinstance(context, dict) else 0,
        "total_chars": context.get("total_chars", 0) if isinstance(context, dict) else 0,
        "files": files,
        "truncated": bool(context.get("truncated")) if isinstance(context, dict) else False,
        "safe": True,
    }
