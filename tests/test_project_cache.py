import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
SCRIPT = ROOT / "scripts" / "dev" / "project_cache.py"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.cache import (
    CACHE_SCHEMA_VERSION,
    build_cache_manifest,
    clear_project_cache,
    get_cache_paths,
    is_cache_valid,
    load_project_cache,
    save_project_cache,
)


class ProjectCacheTests(unittest.TestCase):
    def test_cache_paths_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = get_cache_paths(tmp)
            second = get_cache_paths(tmp)

        self.assertEqual(first["cache_dir"], second["cache_dir"])
        self.assertTrue(str(first["cache_dir"]).replace("\\", "/").endswith("runtime/cache/project_knowledge/" + first["cache_dir"].name))

    def test_cache_save_and_load_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("safe body", encoding="utf-8")
            manifest = build_cache_manifest(root, files=[{"relative_path": "README.md", "size_bytes": 9, "modified_time": 1, "extension": ".md"}], chunks=[])
            save_result = save_project_cache(root, {"manifest": manifest, "chunks": [], "lexical_index": {"documents": {}, "stats": {}}})
            loaded = load_project_cache(root)
            clear_project_cache(root)

        self.assertTrue(save_result["ok"])
        self.assertTrue(loaded["ok"])
        self.assertEqual(CACHE_SCHEMA_VERSION, loaded["manifest"]["schema_version"])

    def test_schema_mismatch_invalidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("safe", encoding="utf-8")
            manifest = build_cache_manifest(root)
            manifest["schema_version"] = -1

            valid = is_cache_valid(root, manifest)

        self.assertFalse(valid)

    def test_missing_or_newer_files_invalidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "README.md"
            path.write_text("safe", encoding="utf-8")
            manifest = build_cache_manifest(root)
            path.write_text("safe changed", encoding="utf-8")

            valid = is_cache_valid(root, manifest)

        self.assertFalse(valid)

    def test_clear_removes_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("safe", encoding="utf-8")
            save_project_cache(root, {"manifest": build_cache_manifest(root), "chunks": [], "lexical_index": {"documents": {}}})
            paths = get_cache_paths(root)
            self.assertTrue(paths["cache_dir"].exists())
            result = clear_project_cache(root)

        self.assertTrue(result["ok"])
        self.assertFalse(paths["cache_dir"].exists())

    def test_cache_redacts_unsafe_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "settings.ini").write_text("token=abc123", encoding="utf-8")
            manifest = build_cache_manifest(root)
            save_project_cache(
                root,
                {
                    "manifest": manifest,
                    "chunks": [{"chunk_id": "a", "text": "token=abc123"}],
                    "lexical_index": {"documents": {"a": {"text": "token=abc123"}}, "stats": {}},
                },
            )
            loaded = load_project_cache(root)
            encoded = json.dumps(loaded)
            clear_project_cache(root)

        self.assertIn("[REDACTED]", encoded)
        self.assertNotIn("abc123", encoded)

    def test_malformed_cache_handled_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = get_cache_paths(root)
            paths["cache_dir"].mkdir(parents=True, exist_ok=True)
            paths["manifest"].write_text("{not json", encoding="utf-8")
            loaded = load_project_cache(root)
            clear_project_cache(root)

        self.assertFalse(loaded["ok"])
        self.assertEqual("JSONDecodeError", loaded["error"])

    def test_cli_status_rebuild_clear_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("prompt cache", encoding="utf-8")
            rebuild = subprocess.run(
                [str(PYTHON), str(SCRIPT), "rebuild", "--root", str(root), "--compact"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )
            status = subprocess.run(
                [str(PYTHON), str(SCRIPT), "status", "--root", str(root), "--compact"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )
            clear = subprocess.run(
                [str(PYTHON), str(SCRIPT), "clear", "--root", str(root), "--compact"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, rebuild.returncode, rebuild.stderr)
        self.assertEqual(0, status.returncode, status.stderr)
        self.assertEqual(0, clear.returncode, clear.stderr)
        self.assertTrue(json.loads(status.stdout)["valid"])

    def test_no_reference_dependency(self) -> None:
        source = (APP_DIR / "project_knowledge" / "cache.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
