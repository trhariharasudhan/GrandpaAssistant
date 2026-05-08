from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


def main() -> int:
    try:
        from windows_control_audit import build_windows_control_audit
    except Exception as error:
        print("[FAIL] Could not import Windows controls audit module.")
        print(str(error))
        return 1

    payload = build_windows_control_audit()
    print("GrandpaAssistant Windows controls audit")
    print(f"Implemented: {payload['implemented_count']}/{payload['total_count']}")
    print(f"Warnings: {len(payload.get('warnings') or [])}")
    print("No destructive actions were executed.")
    print()
    for category in payload.get("categories", []):
        print(category["name"])
        for item in category.get("items", []):
            status = item.get("test_status", "not_tested").upper()
            implemented = "YES" if item.get("implemented") else "NO"
            print(f"  [{status}] {item['capability_key']} implemented={implemented} safety={item['safety_level']}")
            examples = ", ".join(item.get("command_examples") or [])
            if examples:
                print(f"    examples: {examples}")
            if item.get("notes"):
                print(f"    notes: {item['notes']}")
        print()
    return 0 if not payload.get("critical_failures") else 1


if __name__ == "__main__":
    raise SystemExit(main())
