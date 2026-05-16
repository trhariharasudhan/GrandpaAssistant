from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .file_discovery import discover_project_files


def build_project_snapshot(project_root: Any) -> dict:
    try:
        root = Path(project_root).resolve()
        root_text = str(root)
    except (OSError, TypeError, ValueError):
        root_text = ""

    discovered = discover_project_files(project_root)
    extension_counts = Counter(item["extension"] for item in discovered)
    largest = sorted(discovered, key=lambda item: (-item["size_bytes"], item["relative_path"].lower()))[:10]
    recent = sorted(discovered, key=lambda item: (item["modified_time"] or "", item["relative_path"].lower()), reverse=True)[:10]
    return {
        "project_root": root_text,
        "total_files": len(discovered),
        "indexed_extensions": dict(sorted(extension_counts.items())),
        "largest_files": largest,
        "recent_files": recent,
        "discovered_files": discovered,
    }
