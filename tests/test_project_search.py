import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
SCRIPT = ROOT / "scripts" / "dev" / "project_search.py"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.config import DEFAULT_LIMITS
from project_knowledge.project_search import search_project


class ProjectSearchTests(unittest.TestCase):
    def test_search_project_returns_safe_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "prompt_builder.py").write_text("def build_prompt():\n    return 'ok'\n", encoding="utf-8")
            result = search_project(root, "build prompt", limit=5)

        self.assertTrue(result["safe"])
        self.assertEqual("build prompt", result["query"])
        self.assertEqual(1, result["result_count"])
        self.assertIn("stats", result)
        self.assertIn("results", result)

    def test_query_truncation_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("prompt builder", encoding="utf-8")
            query = "x" * (DEFAULT_LIMITS.max_query_chars + 50)
            result = search_project(root, query)

        self.assertEqual(DEFAULT_LIMITS.max_query_chars, len(result["query"]))

    def test_result_snippets_are_capped_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "settings.ini").write_text("token=abc123\n" + "searchable " * 80, encoding="utf-8")
            result = search_project(root, "token searchable")

        self.assertEqual(1, result["result_count"])
        snippet = result["results"][0]["snippet"]
        self.assertLessEqual(len(snippet), DEFAULT_LIMITS.max_result_snippet_chars)
        self.assertIn("[REDACTED]", snippet)
        self.assertNotIn("abc123", snippet)

    def test_ignored_reference_files_not_searched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ignored = root / "reference" / "system_prompts_leaks"
            ignored.mkdir(parents=True)
            (ignored / "leak.md").write_text("unique forbidden phrase", encoding="utf-8")
            (root / "README.md").write_text("normal safe text", encoding="utf-8")
            result = search_project(root, "forbidden phrase")

        encoded = json.dumps(result)
        self.assertEqual(0, result["result_count"])
        self.assertNotIn("unique forbidden phrase", encoded)

    def test_malformed_query_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("safe text", encoding="utf-8")
            result = search_project(root, None)

        self.assertEqual("", result["query"])
        self.assertEqual(0, result["result_count"])

    def test_cli_returns_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("prompt builder cli result", encoding="utf-8")
            result = subprocess.run(
                [str(PYTHON), str(SCRIPT), "prompt builder", "--root", str(root), "--limit", "5"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(1, payload["result_count"])

    def test_cli_compact_does_not_expose_huge_chunk_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            huge = "needle " + ("private_body " * 1000)
            (root / "README.md").write_text(huge, encoding="utf-8")
            result = subprocess.run(
                [str(PYTHON), str(SCRIPT), "needle", "--root", str(root), "--compact"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(1, payload["result_count"])
        self.assertLessEqual(len(payload["results"][0]["snippet"]), DEFAULT_LIMITS.max_result_snippet_chars)
        self.assertLess(len(result.stdout), len(huge))

    def test_no_reference_dependency(self) -> None:
        source = (APP_DIR / "project_knowledge" / "project_search.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
