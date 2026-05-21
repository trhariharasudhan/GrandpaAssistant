"""Remove pycache-only orphan directories that shadow real packages."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = PROJECT_ROOT / "backend" / "app"

def _is_pycache_only(root: Path) -> bool:
    if not root.exists():
        return False
    py_files = list(root.rglob("*.py"))
    if py_files:
        return False
    pyc_files = list(root.rglob("*.pyc"))
    return len(pyc_files) > 0


def _discover_orphan_roots() -> list[Path]:
    roots: list[Path] = []
    if not BACKEND_APP.exists():
        return roots
    seen: set[str] = set()
    for cache_dir in BACKEND_APP.rglob("__pycache__"):
        parent = cache_dir.parent
        key = str(parent)
        if key in seen:
            continue
        seen.add(key)
        if _is_pycache_only(parent):
            roots.append(parent)
    return sorted(roots, key=str)


def cleanup_orphans(*, dry_run: bool) -> list[str]:
    removed: list[str] = []
    for root in _discover_orphan_roots():
        if not _is_pycache_only(root):
            continue
        rel = str(root.relative_to(PROJECT_ROOT)).replace("\\", "/")
        if dry_run:
            removed.append(rel)
            continue
        shutil.rmtree(root)
        removed.append(rel)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove orphan pycache-only backend folders.")
    parser.add_argument("--dry-run", action="store_true", help="List targets without deleting.")
    args = parser.parse_args()
    targets = cleanup_orphans(dry_run=args.dry_run)
    if not targets:
        print("No orphan pycache-only directories found.")
        return 0
    action = "Would remove" if args.dry_run else "Removed"
    for path in targets:
        print(f"{action}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
