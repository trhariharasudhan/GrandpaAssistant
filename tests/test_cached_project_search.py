import json
import tempfile
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.cache import clear_project_cache, load_project_cache
from project_knowledge.cached_search import build_or_load_cached_index, cached_search_project


class CachedProjectSearchTests(unittest.TestCase):
    def test_cached_search_returns_results_and_reuses_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "prompt_builder.py").write_text("def build_prompt():\n    return 'ok'\n", encoding="utf-8")
            first = cached_search_project(root, "build prompt", limit=5)
            second = cached_search_project(root, "build prompt", limit=5)
            clear_project_cache(root)

        self.assertEqual(1, first["result_count"])
        self.assertEqual("rebuilt", first["cache"]["source"])
        self.assertEqual("cache", second["cache"]["source"])
        self.assertEqual(1, second["result_count"])

    def test_invalid_cache_rebuilds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("cache rebuild needle", encoding="utf-8")
            built = build_or_load_cached_index(root)
            (root / "README.md").write_text("cache rebuild needle changed", encoding="utf-8")
            rebuilt = build_or_load_cached_index(root)
            clear_project_cache(root)

        self.assertEqual("rebuilt", built["source"])
        self.assertEqual("rebuilt", rebuilt["source"])

    def test_cached_index_contains_safe_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "settings.ini").write_text("token=abc123\nneedle", encoding="utf-8")
            cached_search_project(root, "needle token")
            loaded = load_project_cache(root)
            encoded = json.dumps(loaded)
            clear_project_cache(root)

        self.assertTrue(loaded["ok"])
        self.assertTrue(loaded["manifest"]["safe"])
        self.assertIn("[REDACTED]", encoded)
        self.assertNotIn("abc123", encoded)

    def test_reference_folder_is_not_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ignored = root / "reference" / "system_prompts_leaks"
            ignored.mkdir(parents=True)
            (ignored / "leak.md").write_text("forbidden cached phrase", encoding="utf-8")
            (root / "README.md").write_text("normal text", encoding="utf-8")
            result = cached_search_project(root, "forbidden cached phrase")
            clear_project_cache(root)

        self.assertEqual(0, result["result_count"])
        self.assertEqual([], result["results"])
        self.assertNotIn("leak.md", json.dumps(result))

    def test_malformed_root_is_safe(self) -> None:
        result = cached_search_project("\0bad", "query")

        self.assertTrue(result["safe"])
        self.assertEqual(0, result["result_count"])
        self.assertEqual("invalid", result["cache"]["source"])


if __name__ == "__main__":
    unittest.main()
