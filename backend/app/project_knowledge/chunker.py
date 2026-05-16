from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .config import DEFAULT_LIMITS
from .content_reader import read_text_file_safely
from .file_filters import normalize_project_path


def _line_number(text: str, char_offset: int) -> int:
    if char_offset <= 0:
        return 1
    return text.count("\n", 0, min(char_offset, len(text))) + 1


def _chunk_id(relative_path: str, index: int) -> str:
    digest = hashlib.sha256(f"{relative_path}:{index}".encode("utf-8")).hexdigest()[:12]
    return f"{relative_path}:{index}:{digest}"


def chunk_text(text: str, *, max_chars: int | None = None, overlap_chars: int | None = None) -> list[dict]:
    source = str(text or "")
    if not source:
        return []

    max_size = max(1, int(max_chars or DEFAULT_LIMITS.max_chunk_chars))
    overlap = max(0, int(overlap_chars if overlap_chars is not None else DEFAULT_LIMITS.chunk_overlap_chars))
    overlap = min(overlap, max_size - 1)
    step = max_size - overlap

    chunks: list[dict] = []
    start = 0
    while start < len(source) and len(chunks) < DEFAULT_LIMITS.max_chunks_per_file:
        end = min(start + max_size, len(source))
        index = len(chunks)
        chunks.append(
            {
                "chunk_id": _chunk_id("text", index),
                "chunk_index": index,
                "text": source[start:end],
                "char_start": start,
                "char_end": end,
                "line_start": _line_number(source, start),
                "line_end": _line_number(source, max(start, end - 1)),
                "metadata": {},
            }
        )
        if end >= len(source):
            break
        start += step
    return chunks


def chunk_file(path: Any, project_root: Any | None = None) -> dict:
    read_result = read_text_file_safely(path, project_root=project_root)
    if not read_result.get("ok"):
        return {
            "ok": False,
            "relative_path": read_result.get("relative_path", normalize_project_path(path)),
            "chunks": [],
            "total_chunks": 0,
            "redacted": bool(read_result.get("redacted")),
            "truncated": bool(read_result.get("truncated")),
            "encoding": read_result.get("encoding", ""),
            "error": read_result.get("error") or "read_failed",
        }

    relative_path = str(read_result.get("relative_path") or normalize_project_path(Path(path).name))
    extension = Path(relative_path).suffix.lower()
    chunks = chunk_text(str(read_result.get("text") or ""))
    for chunk in chunks:
        index = int(chunk["chunk_index"])
        chunk["chunk_id"] = _chunk_id(relative_path, index)
        chunk["metadata"] = {
            "relative_path": relative_path,
            "extension": extension,
        }

    return {
        "ok": True,
        "relative_path": relative_path,
        "chunks": chunks,
        "total_chunks": len(chunks),
        "redacted": bool(read_result.get("redacted")),
        "truncated": bool(read_result.get("truncated")),
        "encoding": read_result.get("encoding", ""),
        "error": None,
    }
