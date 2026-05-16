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


def _print(payload: dict, compact: bool) -> None:
    if compact:
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage the local project knowledge cache.")
    parser.add_argument("action", choices=["status", "rebuild", "clear"], help="Cache action to run.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON without indentation.")
    parser.add_argument("--root", default=str(ROOT), help="Project root. Defaults to repository root.")
    args = parser.parse_args(argv)

    try:
        from project_knowledge.cache import clear_project_cache, get_cache_paths, is_cache_valid, load_project_cache
        from project_knowledge.cached_search import build_or_load_cached_index

        if args.action == "clear":
            result = clear_project_cache(args.root)
            payload = {"ok": bool(result.get("ok")), "action": "clear", "cache_dir": result.get("cache_dir"), "error": result.get("error")}
        elif args.action == "rebuild":
            clear_project_cache(args.root)
            result = build_or_load_cached_index(args.root)
            manifest = result.get("manifest", {}) if isinstance(result.get("manifest"), dict) else {}
            payload = {
                "ok": bool(result.get("ok")),
                "action": "rebuild",
                "source": result.get("source"),
                "cache_saved": bool(result.get("cache_saved")),
                "cache_dir": str(get_cache_paths(args.root)["cache_dir"]),
                "manifest": {
                    "schema_version": manifest.get("schema_version"),
                    "file_count": manifest.get("file_count", 0),
                    "chunk_count": manifest.get("chunk_count", 0),
                    "index_type": manifest.get("index_type"),
                    "safe": bool(manifest.get("safe")),
                },
                "error": result.get("error"),
            }
        else:
            loaded = load_project_cache(args.root)
            manifest = loaded.get("manifest", {}) if isinstance(loaded.get("manifest"), dict) else {}
            payload = {
                "ok": bool(loaded.get("ok")),
                "action": "status",
                "cache_dir": loaded.get("cache_dir"),
                "valid": bool(loaded.get("ok") and is_cache_valid(args.root, manifest)),
                "manifest": {
                    "schema_version": manifest.get("schema_version"),
                    "file_count": manifest.get("file_count", 0),
                    "chunk_count": manifest.get("chunk_count", 0),
                    "index_type": manifest.get("index_type"),
                    "safe": bool(manifest.get("safe")),
                },
                "error": loaded.get("error"),
            }

        _print(payload, args.compact)
        return 0 if payload.get("ok") or args.action in {"status", "clear"} else 1
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
