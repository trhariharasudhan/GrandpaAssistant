import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.file_discovery import discover_project_files


class ProjectFileDiscoveryTests(unittest.TestCase):
    def _sample_project(self) -> tempfile.TemporaryDirectory:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "b.py").write_text("print('b')\n", encoding="utf-8")
        (root / "a.md").write_text("# A\nsecret body should not appear in metadata\n", encoding="utf-8")
        (root / "image.png").write_text("not indexed", encoding="utf-8")
        (root / ".git").mkdir()
        (root / ".git" / "config").write_text("hidden", encoding="utf-8")
        (root / "node_modules").mkdir()
        (root / "node_modules" / "pkg.py").write_text("hidden", encoding="utf-8")
        (root / "reference").mkdir()
        (root / "reference" / "system_prompts_leaks").mkdir()
        (root / "reference" / "system_prompts_leaks" / "leak.md").write_text("hidden reference", encoding="utf-8")
        (root / "nested").mkdir()
        (root / "nested" / "config.json").write_text('{"ok": true}', encoding="utf-8")
        return tmp

    def test_discovery_returns_safe_metadata_only(self) -> None:
        with self._sample_project() as tmp:
            files = discover_project_files(tmp)

        encoded = json.dumps(files)
        self.assertIn("a.md", encoded)
        self.assertIn("b.py", encoded)
        self.assertNotIn("secret body should not appear", encoded)
        self.assertNotIn("hidden", encoded)

    def test_ignored_directories_skipped(self) -> None:
        with self._sample_project() as tmp:
            files = discover_project_files(tmp)

        paths = {item["relative_path"] for item in files}
        self.assertNotIn(".git/config", paths)
        self.assertNotIn("node_modules/pkg.py", paths)
        self.assertNotIn("reference/system_prompts_leaks/leak.md", paths)

    def test_deterministic_ordering(self) -> None:
        with self._sample_project() as tmp:
            first = discover_project_files(tmp)
            second = discover_project_files(tmp)

        self.assertEqual(first, second)
        self.assertEqual(sorted(item["relative_path"] for item in first), [item["relative_path"] for item in first])

    def test_malformed_root_returns_empty(self) -> None:
        self.assertEqual([], discover_project_files(None))
        self.assertEqual([], discover_project_files("not-a-real-folder"))

    def test_no_reference_dependency(self) -> None:
        source = (APP_DIR / "project_knowledge" / "file_discovery.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
