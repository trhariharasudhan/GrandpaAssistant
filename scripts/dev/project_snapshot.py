from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "backend" / "app"
for path in (APP_DIR,):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print safe read-only project knowledge snapshot JSON.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON without indentation.")
    parser.add_argument("--root", default=str(ROOT), help="Project root to scan. Defaults to repository root.")
    args = parser.parse_args(argv)

    try:
        from project_knowledge.project_snapshot import build_project_snapshot

        snapshot = build_project_snapshot(args.root)
        if args.compact:
            print(json.dumps(snapshot, sort_keys=True, separators=(",", ":")))
        else:
            print(json.dumps(snapshot, indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
