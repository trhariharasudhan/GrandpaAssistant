import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
SCRIPT = ROOT / "scripts" / "dev" / "project_context.py"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.config import CONTEXT_HEADER, DEFAULT_LIMITS
from project_knowledge.retrieval_context import (
    build_retrieval_context,
    format_retrieval_context_for_prompt,
    summarize_retrieval_context,
)


class ProjectRetrievalContextTests(unittest.TestCase):
    def test_context_builds_successfully(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "prompt_builder.py").write_text("def build_prompt():\n    return 'ok'\n", encoding="utf-8")
            context = build_retrieval_context(root, "build prompt")

        self.assertTrue(context["safe"])
        self.assertEqual("build prompt", context["query"])
        self.assertEqual(1, context["result_count"])
        self.assertEqual("prompt_builder.py", context["context_blocks"][0]["relative_path"])

    def test_total_char_limit_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("needle " + ("body " * 1000), encoding="utf-8")
            context = build_retrieval_context(root, "needle", max_total_chars=120)

        self.assertLessEqual(context["total_chars"], 120)
        self.assertTrue(context["truncated"])

    def test_per_block_limit_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("needle " + ("body " * 1000), encoding="utf-8")
            context = build_retrieval_context(root, "needle")

        self.assertLessEqual(len(context["context_blocks"][0]["text"]), DEFAULT_LIMITS.max_context_block_chars)

    def test_deterministic_ordering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.md").write_text("same term", encoding="utf-8")
            (root / "a.md").write_text("same term", encoding="utf-8")
            first = build_retrieval_context(root, "same")
            second = build_retrieval_context(root, "same")

        self.assertEqual(first["context_blocks"], second["context_blocks"])
        self.assertEqual("a.md", first["context_blocks"][0]["relative_path"])

    def test_formatting_helper_works(self) -> None:
        context = {
            "context_blocks": [
                {
                    "relative_path": "README.md",
                    "line_range": "1-2",
                    "text": "short snippet",
                }
            ]
        }
        formatted = format_retrieval_context_for_prompt(context)

        self.assertIn(CONTEXT_HEADER, formatted)
        self.assertIn("File: README.md", formatted)
        self.assertIn("Lines: 1-2", formatted)
        self.assertIn("short snippet", formatted)

    def test_summary_excludes_snippet_text(self) -> None:
        context = {
            "query": "needle",
            "result_count": 1,
            "total_chars": 10,
            "truncated": False,
            "context_blocks": [{"relative_path": "README.md", "text": "private snippet"}],
        }
        summary = summarize_retrieval_context(context)

        encoded = json.dumps(summary)
        self.assertIn("README.md", encoded)
        self.assertNotIn("private snippet", encoded)

    def test_redacted_secrets_stay_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "settings.ini").write_text("token=abc123\nneedle value\n", encoding="utf-8")
            context = build_retrieval_context(root, "token needle")

        encoded = json.dumps(context)
        self.assertIn("[REDACTED]", encoded)
        self.assertNotIn("abc123", encoded)

    def test_no_huge_dumps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            huge = "needle " + ("private_body " * 2000)
            (root / "README.md").write_text(huge, encoding="utf-8")
            context = build_retrieval_context(root, "needle")
            formatted = format_retrieval_context_for_prompt(context)

        self.assertLess(len(formatted), len(huge))
        self.assertLessEqual(len(formatted), DEFAULT_LIMITS.max_context_total_chars)

    def test_empty_results_handled_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("safe text", encoding="utf-8")
            context = build_retrieval_context(root, "notfound")

        self.assertTrue(context["safe"])
        self.assertEqual(0, context["result_count"])
        self.assertEqual([], context["context_blocks"])

    def test_malformed_query_handled_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("safe text", encoding="utf-8")
            context = build_retrieval_context(root, None)

        self.assertEqual("", context["query"])
        self.assertEqual(0, context["result_count"])

    def test_no_reference_usage(self) -> None:
        source = (APP_DIR / "project_knowledge" / "retrieval_context.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))

    def test_cli_summary_only_excludes_snippets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("needle private snippet", encoding="utf-8")
            result = subprocess.run(
                [str(PYTHON), str(SCRIPT), "needle", "--root", str(root), "--summary-only", "--compact"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(1, payload["result_count"])
        self.assertNotIn("private snippet", result.stdout)


if __name__ == "__main__":
    unittest.main()
