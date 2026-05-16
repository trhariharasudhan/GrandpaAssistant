from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import DEFAULT_LIMITS
from .file_filters import is_safe_to_index, should_ignore_directory
from .file_metadata import build_file_metadata


def _depth(root: Path, path: Path) -> int:
    try:
        return len(path.relative_to(root).parts)
    except ValueError:
        return DEFAULT_LIMITS.max_directory_depth + 1


def discover_project_files(project_root: Any) -> list[dict]:
    try:
        root = Path(project_root).resolve()
    except (OSError, TypeError, ValueError):
        return []
    if not root.exists() or not root.is_dir():
        return []

    discovered: list[dict] = []
    stack = [root]
    while stack and len(discovered) < DEFAULT_LIMITS.max_scan_files:
        current = stack.pop()
        try:
            if current != root and (current.is_symlink() or should_ignore_directory(current)):
                continue
            if _depth(root, current) > DEFAULT_LIMITS.max_directory_depth:
                continue
            entries = sorted(current.iterdir(), key=lambda item: item.name.lower())
        except OSError:
            continue

        directories = []
        for entry in entries:
            try:
                if entry.is_dir():
                    if not entry.is_symlink() and not should_ignore_directory(entry):
                        directories.append(entry)
                    continue
                if len(discovered) >= DEFAULT_LIMITS.max_scan_files:
                    break
                if is_safe_to_index(entry):
                    metadata = build_file_metadata(entry, project_root=root)
                    discovered.append(
                        {
                            "relative_path": metadata["relative_path"],
                            "extension": metadata["extension"],
                            "size_bytes": metadata["size_bytes"],
                            "modified_time": metadata["modified_time"],
                            "file_name": metadata["file_name"],
                        }
                    )
            except OSError:
                continue
        stack.extend(reversed(directories))

    return sorted(discovered, key=lambda item: item["relative_path"].lower())
