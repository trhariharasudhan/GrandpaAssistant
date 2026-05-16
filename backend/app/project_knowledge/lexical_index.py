from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .chunker import chunk_file
from .config import DEFAULT_LIMITS
from .content_reader import redact_obvious_secrets
from .file_discovery import discover_project_files
from .tokenizer import tokenize_query, tokenize_text


def _safe_snippet(text: Any) -> str:
    redacted, _changed = redact_obvious_secrets(str(text or ""))
    return redacted[: DEFAULT_LIMITS.max_result_snippet_chars]


def _document_tokens(chunk: dict) -> list[str]:
    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    path_text = metadata.get("relative_path", "")
    return tokenize_text(f"{path_text} {chunk.get('text', '')}")


def index_chunks(chunks: list[dict]) -> dict:
    documents: dict[str, dict] = {}
    inverted: dict[str, dict[str, int]] = defaultdict(dict)

    for chunk in chunks or []:
        if not isinstance(chunk, dict):
            continue
        chunk_id = str(chunk.get("chunk_id") or "")
        if not chunk_id:
            continue
        metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        relative_path = str(metadata.get("relative_path") or "")
        tokens = _document_tokens(chunk)
        token_counts = Counter(tokens)
        documents[chunk_id] = {
            "chunk_id": chunk_id,
            "chunk_index": int(chunk.get("chunk_index") or 0),
            "relative_path": relative_path,
            "line_start": int(chunk.get("line_start") or 1),
            "line_end": int(chunk.get("line_end") or 1),
            "text": str(chunk.get("text") or ""),
            "metadata": dict(metadata),
            "token_counts": dict(sorted(token_counts.items())),
        }
        for token, count in token_counts.items():
            inverted[token][chunk_id] = int(count)

    return {
        "documents": documents,
        "inverted_index": {token: dict(sorted(postings.items())) for token, postings in sorted(inverted.items())},
        "stats": {
            "document_count": len(documents),
            "term_count": len(inverted),
        },
    }


def build_lexical_index(project_root: Any) -> dict:
    try:
        root = Path(project_root).resolve()
    except (OSError, TypeError, ValueError):
        return index_chunks([])

    chunks: list[dict] = []
    for item in discover_project_files(root):
        relative_path = item.get("relative_path", "")
        result = chunk_file(root / relative_path, project_root=root)
        if result.get("ok"):
            chunks.extend(result.get("chunks") or [])

    index = index_chunks(chunks)
    index["stats"]["project_root"] = str(root)
    index["stats"]["files_considered"] = len(discover_project_files(root))
    return index


def _score_document(document: dict, query_terms: list[str]) -> tuple[float, list[str]]:
    counts = document.get("token_counts") if isinstance(document.get("token_counts"), dict) else {}
    path_tokens = set(tokenize_text(document.get("relative_path", "")))
    matched: list[str] = []
    score = 0.0
    for term in query_terms:
        count = int(counts.get(term) or 0)
        if count <= 0:
            continue
        matched.append(term)
        score += 1.0 + min(count, 5) * 0.25
        if term in path_tokens:
            score += 1.5
    score += len(matched) * 0.5
    return score, matched


def search_lexical_index(index: dict, query: Any, limit: int = 10) -> list[dict]:
    query_terms = tokenize_query(query)
    if not query_terms or not isinstance(index, dict):
        return []

    documents = index.get("documents") if isinstance(index.get("documents"), dict) else {}
    result_limit = max(1, min(int(limit or DEFAULT_LIMITS.max_search_results), DEFAULT_LIMITS.max_search_results))
    scored: list[dict] = []
    for document in documents.values():
        if not isinstance(document, dict):
            continue
        score, matched = _score_document(document, query_terms)
        if score <= 0:
            continue
        scored.append(
            {
                "relative_path": document.get("relative_path", ""),
                "chunk_id": document.get("chunk_id", ""),
                "chunk_index": int(document.get("chunk_index") or 0),
                "score": round(score, 4),
                "matched_terms": matched,
                "snippet": _safe_snippet(document.get("text", "")),
                "line_start": int(document.get("line_start") or 1),
                "line_end": int(document.get("line_end") or 1),
                "metadata": document.get("metadata", {}),
            }
        )

    return sorted(
        scored,
        key=lambda item: (-float(item["score"]), str(item["relative_path"]).lower(), int(item["chunk_index"])),
    )[:result_limit]
