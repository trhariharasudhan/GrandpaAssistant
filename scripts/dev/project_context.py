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
    parser = argparse.ArgumentParser(description="Build safe project retrieval context JSON.")
    parser.add_argument("query", help="Search query to package as retrieval context.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON without indentation.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum context blocks, capped by project settings.")
    parser.add_argument("--root", default=str(ROOT), help="Project root to scan. Defaults to repository root.")
    parser.add_argument("--summary-only", action="store_true", help="Print metadata summary without snippets.")
    args = parser.parse_args(argv)

    try:
        from project_knowledge.retrieval_context import build_retrieval_context, summarize_retrieval_context

        context = build_retrieval_context(args.root, args.query, limit=args.limit)
        payload = summarize_retrieval_context(context) if args.summary_only else context
        if args.compact:
            print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
