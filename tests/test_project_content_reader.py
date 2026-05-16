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


from project_knowledge.config import DEFAULT_LIMITS
from project_knowledge.content_reader import is_probably_binary, read_text_file_safely


class ProjectContentReaderTests(unittest.TestCase):
    def test_text_file_reads_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "app.py"
            path.write_text("print('hello')\n", encoding="utf-8")
            result = read_text_file_safely(path, project_root=root)

        self.assertTrue(result["ok"])
        self.assertEqual("app.py", result["relative_path"])
        self.assertEqual("utf-8", result["encoding"])
        self.assertIn("print('hello')", result["text"])
        self.assertIsNone(result["error"])

    def test_unsupported_file_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "image.png"
            path.write_text("body", encoding="utf-8")
            result = read_text_file_safely(path, project_root=root)

        self.assertFalse(result["ok"])
        self.assertEqual("", result["text"])
        self.assertEqual("unsupported_or_unsafe_file", result["error"])

    def test_ignored_directory_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ignored = root / "reference" / "system_prompts_leaks"
            ignored.mkdir(parents=True)
            path = ignored / "leak.md"
            path.write_text("hidden body", encoding="utf-8")
            result = read_text_file_safely(path, project_root=root)

        self.assertFalse(result["ok"])
        self.assertEqual("", result["text"])
        self.assertNotIn("hidden body", json.dumps(result))

    def test_binary_file_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "binary.py"
            path.write_bytes(b"abc\x00def")
            result = read_text_file_safely(path, project_root=root)

        self.assertTrue(is_probably_binary(path))
        self.assertFalse(result["ok"])
        self.assertEqual("binary_file", result["error"])

    def test_large_file_truncates_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "large.md"
            path.write_text("a" * (DEFAULT_LIMITS.max_read_bytes + 100), encoding="utf-8")
            result = read_text_file_safely(path, project_root=root)

        self.assertTrue(result["ok"])
        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(result["text"]), DEFAULT_LIMITS.max_read_bytes)

    def test_secret_like_lines_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "settings.ini"
            path.write_text(
                "password=hunter2\napi_key: abc123\nAuthorization: Bearer verysecret\n",
                encoding="utf-8",
            )
            result = read_text_file_safely(path, project_root=root)

        self.assertTrue(result["ok"])
        self.assertTrue(result["redacted"])
        self.assertIn("[REDACTED]", result["text"])
        self.assertNotIn("hunter2", result["text"])
        self.assertNotIn("abc123", result["text"])
        self.assertNotIn("verysecret", result["text"])

    def test_malformed_paths_do_not_crash(self) -> None:
        result = read_text_file_safely(None)

        self.assertFalse(result["ok"])
        self.assertEqual("", result["text"])

    def test_no_reference_dependency(self) -> None:
        source = (APP_DIR / "project_knowledge" / "content_reader.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
