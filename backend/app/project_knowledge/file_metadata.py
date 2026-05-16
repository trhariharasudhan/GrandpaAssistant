from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DEFAULT_LIMITS
from .file_filters import normalize_project_path


def _modified_time(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _relative_path(path: Path, project_root: Path | None) -> str:
    if project_root is not None:
        try:
            return normalize_project_path(path.resolve().relative_to(project_root.resolve()))
        except (OSError, ValueError):
            pass
    return normalize_project_path(path.name)


def _line_count_estimate(path: Path, size_bytes: int) -> int | None:
    if size_bytes > DEFAULT_LIMITS.max_line_count_bytes:
        return None
    try:
        with path.open("rb") as handle:
            return sum(1 for _line in handle)
    except OSError:
        return None


def build_file_metadata(path: Any, project_root: Any | None = None) -> dict:
    try:
        candidate = Path(path)
        root = Path(project_root) if project_root is not None else None
        stat = candidate.stat()
        size_bytes = int(stat.st_size)
        return {
            "relative_path": _relative_path(candidate, root),
            "file_name": candidate.name,
            "extension": candidate.suffix.lower(),
            "size_bytes": size_bytes,
            "line_count_estimate": _line_count_estimate(candidate, size_bytes),
            "modified_time": _modified_time(stat.st_mtime),
        }
    except (OSError, TypeError, ValueError):
        return {
            "relative_path": "",
            "file_name": "",
            "extension": "",
            "size_bytes": 0,
            "line_count_estimate": None,
            "modified_time": None,
        }
