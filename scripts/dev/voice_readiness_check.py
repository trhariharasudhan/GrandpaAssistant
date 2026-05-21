"""Print voice STT/TTS/runtime readiness for local setup."""

from __future__ import annotations

import json
import os
import sys


def _bootstrap_paths() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    shared_dir = os.path.join(repo_root, "backend", "app", "shared")
    if shared_dir not in sys.path:
        sys.path.insert(0, shared_dir)


def main() -> int:
    _bootstrap_paths()
    from voice_readiness import collect_voice_readiness

    report = collect_voice_readiness()
    print(json.dumps(report, indent=2))
    for item in report.get("components", []):
        status = item.get("status", "unknown")
        label = item.get("id", "component")
        detail = item.get("detail", "")
        print(f"[{status}] {label}: {detail}")
    print(report.get("summary", ""))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
