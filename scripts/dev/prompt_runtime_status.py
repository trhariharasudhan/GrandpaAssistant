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
    parser = argparse.ArgumentParser(description="Print safe GrandpaAssistant prompt runtime status as JSON.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON without indentation.")
    parser.add_argument("--check", action="store_true", help="Exit 0 only when status is safe to expose and reference prompts are unused.")
    args = parser.parse_args(argv)

    try:
        from core.prompt_runtime_status import get_prompt_runtime_status

        status = get_prompt_runtime_status()
        if args.compact:
            print(json.dumps(status, sort_keys=True, separators=(",", ":")))
        else:
            print(json.dumps(status, indent=2, sort_keys=True))
        if args.check and (not status.get("safe_to_expose") or status.get("reference_folder_used")):
            return 1
        return 0
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
