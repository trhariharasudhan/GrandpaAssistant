from __future__ import annotations

from pathlib import Path
from typing import Any

from .chunker import chunk_file
from .file_discovery import discover_project_files


def build_project_chunk_summary(project_root: Any) -> dict:
    try:
        root = Path(project_root).resolve()
        root_text = str(root)
    except (OSError, TypeError, ValueError):
        root = None
        root_text = ""

    if root is None or not root.exists() or not root.is_dir():
        return {
            "project_root": root_text,
            "total_files_considered": 0,
            "files_chunked": 0,
            "total_chunks": 0,
            "redacted_files": 0,
            "truncated_files": 0,
            "errors": [{"relative_path": "", "error": "invalid_project_root"}],
        }

    discovered = discover_project_files(root)
    files_chunked = 0
    total_chunks = 0
    redacted_files = 0
    truncated_files = 0
    errors: list[dict] = []

    for item in discovered:
        relative_path = item.get("relative_path", "")
        result = chunk_file(root / relative_path, project_root=root)
        if not result.get("ok"):
            errors.append({"relative_path": relative_path, "error": result.get("error") or "chunk_failed"})
            continue
        files_chunked += 1
        total_chunks += int(result.get("total_chunks") or 0)
        if result.get("redacted"):
            redacted_files += 1
        if result.get("truncated"):
            truncated_files += 1

    return {
        "project_root": root_text,
        "total_files_considered": len(discovered),
        "files_chunked": files_chunked,
        "total_chunks": total_chunks,
        "redacted_files": redacted_files,
        "truncated_files": truncated_files,
        "errors": errors[:50],
    }
