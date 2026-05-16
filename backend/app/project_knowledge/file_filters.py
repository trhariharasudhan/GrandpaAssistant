from __future__ import annotations

from pathlib import Path, PurePath
from typing import Any

from .config import DEFAULT_LIMITS, IGNORED_DIRECTORIES, SUPPORTED_EXTENSIONS


def _path(value: Any) -> Path | None:
    try:
        return Path(value)
    except (TypeError, ValueError):
        return None


def normalize_project_path(path: Any) -> str:
    try:
        return PurePath(str(path or "")).as_posix().strip("/")
    except Exception:
        return ""


def is_supported_file(path: Any) -> bool:
    candidate = _path(path)
    if candidate is None:
        return False
    return candidate.suffix.lower() in SUPPORTED_EXTENSIONS


def should_ignore_directory(path: Any) -> bool:
    candidate = _path(path)
    if candidate is None:
        return True
    parts = {part.lower() for part in candidate.parts}
    return any(ignored.lower() in parts for ignored in IGNORED_DIRECTORIES)


def is_safe_to_index(path: Any) -> bool:
    candidate = _path(path)
    if candidate is None:
        return False
    try:
        if should_ignore_directory(candidate.parent):
            return False
        if not is_supported_file(candidate):
            return False
        if candidate.is_symlink() or not candidate.is_file():
            return False
        return candidate.stat().st_size <= DEFAULT_LIMITS.max_file_size_bytes
    except OSError:
        return False
