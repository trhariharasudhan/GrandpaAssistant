from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print safe project context status JSON.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON without indentation.")
    parser.add_argument("--check", action="store_true", help="Exit 0 only when status is safe to expose.")
    parser.add_argument("--root", default=str(ROOT), help="Optional project root readiness check.")
    args = parser.parse_args(argv)

    try:
        from project_knowledge.project_context_status import get_project_context_status

        status = get_project_context_status(args.root)
        if args.compact:
            print(json.dumps(status, sort_keys=True, separators=(",", ":")))
        else:
            print(json.dumps(status, indent=2, sort_keys=True))
        if args.check:
            ok = (
                status.get("safe_to_expose") is True
                and status.get("reference_folder_used") is False
                and status.get("context_body_exposed") is False
                and status.get("snippet_body_exposed") is False
            )
            return 0 if ok else 1
        return 0
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
