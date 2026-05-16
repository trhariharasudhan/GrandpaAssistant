import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.file_filters import is_safe_to_index, is_supported_file, normalize_project_path, should_ignore_directory


class ProjectFileFiltersTests(unittest.TestCase):
    def test_supported_extensions_handled(self) -> None:
        self.assertTrue(is_supported_file("app.py"))
        self.assertTrue(is_supported_file("README.md"))
        self.assertFalse(is_supported_file("image.png"))

    def test_ignored_directories_skipped(self) -> None:
        self.assertTrue(should_ignore_directory(Path("repo") / ".git"))
        self.assertTrue(should_ignore_directory(Path("repo") / ".python311" / "Lib"))
        self.assertTrue(should_ignore_directory(Path("repo") / "reference" / "system_prompts_leaks"))
        self.assertTrue(should_ignore_directory(Path("repo") / "node_modules" / "pkg"))
        self.assertFalse(should_ignore_directory(Path("repo") / "backend"))

    def test_malformed_paths_handled_safely(self) -> None:
        self.assertFalse(is_supported_file(None))
        self.assertTrue(should_ignore_directory(None))
        self.assertFalse(is_safe_to_index(None))

    def test_relative_paths_normalized(self) -> None:
        self.assertEqual("backend/app.py", normalize_project_path(Path("backend") / "app.py"))

    def test_unsafe_files_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unsupported = root / "image.png"
            unsupported.write_text("not code", encoding="utf-8")
            supported = root / "app.py"
            supported.write_text("print('ok')", encoding="utf-8")

            self.assertFalse(is_safe_to_index(unsupported))
            self.assertTrue(is_safe_to_index(supported))

    def test_no_reference_dependency(self) -> None:
        source = (APP_DIR / "project_knowledge" / "file_filters.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
