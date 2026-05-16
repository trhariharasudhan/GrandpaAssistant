import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.config import DEFAULT_LIMITS
from project_knowledge.project_context_adapter import (
    PROJECT_CONTEXT_ENV,
    build_project_context_for_prompt,
    is_project_context_enabled,
)


class ProjectContextAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_env = os.environ.pop(PROJECT_CONTEXT_ENV, None)

    def tearDown(self) -> None:
        if self.previous_env is None:
            os.environ.pop(PROJECT_CONTEXT_ENV, None)
        else:
            os.environ[PROJECT_CONTEXT_ENV] = self.previous_env

    def test_env_off_returns_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = build_project_context_for_prompt(project_root=tmp, user_message="prompt builder")

        self.assertFalse(is_project_context_enabled())
        self.assertFalse(result["enabled"])
        self.assertEqual("", result["context_text"])
        self.assertIsNone(result["error"])

    def test_env_on_builds_context_safely(self) -> None:
        os.environ[PROJECT_CONTEXT_ENV] = "1"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "prompt_builder.py").write_text("def build_prompt():\n    return 'ok'\n", encoding="utf-8")
            result = build_project_context_for_prompt(project_root=root, user_message="build prompt")

        self.assertTrue(result["enabled"])
        self.assertIn("PROJECT KNOWLEDGE CONTEXT", result["context_text"])
        self.assertEqual(1, result["summary"]["result_count"])
        self.assertIsNone(result["error"])

    def test_malformed_project_root_handled_safely(self) -> None:
        os.environ[PROJECT_CONTEXT_ENV] = "yes"

        result = build_project_context_for_prompt(project_root="not-a-real-folder", user_message="prompt")

        self.assertTrue(result["enabled"])
        self.assertEqual(0, result["summary"]["result_count"])
        self.assertIsNone(result["error"])

    def test_context_text_capped(self) -> None:
        os.environ[PROJECT_CONTEXT_ENV] = "on"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("needle " + ("body " * 2000), encoding="utf-8")
            result = build_project_context_for_prompt(project_root=root, user_message="needle")

        self.assertLessEqual(len(result["context_text"]), DEFAULT_LIMITS.max_context_total_chars)

    def test_summary_excludes_snippet_text(self) -> None:
        os.environ[PROJECT_CONTEXT_ENV] = "true"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("needle private snippet", encoding="utf-8")
            result = build_project_context_for_prompt(project_root=root, user_message="needle")

        self.assertNotIn("private snippet", json.dumps(result["summary"]))

    def test_no_reference_dependency(self) -> None:
        source = (APP_DIR / "project_knowledge" / "project_context_adapter.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))

    def test_errors_do_not_raise(self) -> None:
        os.environ[PROJECT_CONTEXT_ENV] = "1"

        with patch("project_knowledge.project_context_adapter.build_retrieval_context", side_effect=RuntimeError("boom")):
            result = build_project_context_for_prompt(project_root=ROOT, user_message="prompt")

        self.assertTrue(result["enabled"])
        self.assertEqual("", result["context_text"])
        self.assertEqual("RuntimeError", result["error"])


if __name__ == "__main__":
    unittest.main()
