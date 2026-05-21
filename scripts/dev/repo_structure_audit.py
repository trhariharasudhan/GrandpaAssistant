"""Scan backend layout for orphan artifacts, duplicates, and structure issues."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_APP = PROJECT_ROOT / "backend" / "app"

ORPHAN_ROOTS = (
    BACKEND_APP / "brain",
    BACKEND_APP / "core" / "knowledge_engine",
    BACKEND_APP / "core" / "math_engine",
    BACKEND_APP / "core" / "security",
)

KNOWN_DUPLICATE_AREAS = (
    ("api", "web_api.py vs chat_api.py — desktop primary vs alternate runtime"),
    ("core/chatbot/providers", "shared/llm_client.py — terminal vs web LLM stacks"),
    ("features/modules", "compatibility shims only; real code in features/<domain>/"),
    ("shared/brain", "canonical; do not recreate backend/app/brain/"),
)


@dataclass(frozen=True)
class DirAudit:
    path: str
    py_files: int
    pyc_files: int
    orphan_pycache_only: bool


def _count_files(root: Path, suffix: str) -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.rglob(f"*{suffix}") if _.is_file())


def audit_directory(root: Path) -> DirAudit:
    py_count = _count_files(root, ".py")
    pyc_count = _count_files(root, ".pyc")
    return DirAudit(
        path=str(root.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        py_files=py_count,
        pyc_files=pyc_count,
        orphan_pycache_only=root.exists() and py_count == 0 and pyc_count > 0,
    )


def find_orphan_pycache_dirs() -> list[str]:
    orphans: list[str] = []
    if not BACKEND_APP.exists():
        return orphans
    for path in sorted(BACKEND_APP.rglob("__pycache__")):
        parent = path.parent
        if any(parent.rglob("*.py")):
            continue
        rel = str(parent.relative_to(PROJECT_ROOT)).replace("\\", "/")
        if rel not in orphans:
            orphans.append(rel)
    return orphans


def build_report() -> dict[str, object]:
    dir_audits = [audit_directory(root) for root in ORPHAN_ROOTS]
    return {
        "project_root": str(PROJECT_ROOT),
        "orphan_roots": [asdict(item) for item in dir_audits],
        "orphan_pycache_parents": find_orphan_pycache_dirs(),
        "known_duplicate_areas": [
            {"area": area, "note": note} for area, note in KNOWN_DUPLICATE_AREAS
        ],
        "canonical_brain_path": "backend/app/shared/brain/",
        "canonical_security_path": "backend/app/security/",
        "modules_shim_path": "backend/app/features/modules/",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit GrandpaAssistant repo structure.")
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    args = parser.parse_args()
    report = build_report()

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("GrandpaAssistant structure audit")
    print(f"Root: {report['project_root']}")
    print("\nOrphan root candidates:")
    for item in report["orphan_roots"]:
        flag = "ORPHAN" if item["orphan_pycache_only"] else "ok"
        print(f"  [{flag}] {item['path']}  py={item['py_files']}  pyc={item['pyc_files']}")

    extra = report["orphan_pycache_parents"]
    if extra:
        print("\nOther pycache-only parents:")
        for path in extra:
            print(f"  - {path}")

    print("\nKnown duplicate areas (intentional until migration):")
    for row in report["known_duplicate_areas"]:
        print(f"  - {row['area']}: {row['note']}")

    print(f"\nCanonical brain: {report['canonical_brain_path']}")
    print(f"Canonical security: {report['canonical_security_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
