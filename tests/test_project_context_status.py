import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.project_context_adapter import PROJECT_CONTEXT_ENV
from project_knowledge.project_context_status import (
    get_project_context_status,
    summarize_project_context_adapter_result,
)


class ProjectContextStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_env = os.environ.pop(PROJECT_CONTEXT_ENV, None)

    def tearDown(self) -> None:
        if self.previous_env is None:
            os.environ.pop(PROJECT_CONTEXT_ENV, None)
        else:
            os.environ[PROJECT_CONTEXT_ENV] = self.previous_env

    def test_status_json_safe(self) -> None:
        status = get_project_context_status()

        self.assertIsInstance(status, dict)
        self.assertIsInstance(json.dumps(status), str)

    def test_env_flag_state_reflected(self) -> None:
        self.assertFalse(get_project_context_status()["project_context_enabled"])

        os.environ[PROJECT_CONTEXT_ENV] = "on"

        self.assertTrue(get_project_context_status()["project_context_enabled"])

    def test_body_exposure_flags_false(self) -> None:
        status = get_project_context_status()

        self.assertFalse(status["context_body_exposed"])
        self.assertFalse(status["snippet_body_exposed"])
        self.assertFalse(status["reference_folder_used"])
        self.assertTrue(status["safe_to_expose"])

    def test_no_context_or_snippet_fields(self) -> None:
        encoded = json.dumps(get_project_context_status()).lower()

        self.assertNotIn("context_text", encoded)
        self.assertNotIn("snippet_text", encoded)
        self.assertNotIn("file_content", encoded)
        self.assertNotIn("user_message", encoded)

    def test_no_reference_folder_text(self) -> None:
        encoded = json.dumps(get_project_context_status()).replace("\\", "/")

        self.assertNotIn("reference/system_prompts_leaks", encoded)

    def test_limits_included(self) -> None:
        limits = get_project_context_status()["limits"]

        self.assertIn("max_context_results", limits)
        self.assertIn("max_context_total_chars", limits)
        self.assertIn("max_context_block_chars", limits)

    def test_errors_do_not_crash(self) -> None:
        status = get_project_context_status(object())

        self.assertFalse(status["available"])
        self.assertTrue(status["safe_to_expose"])

    def test_project_root_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            status = get_project_context_status(tmp)

        self.assertTrue(status["available"])

    def test_adapter_result_summary_excludes_context_text(self) -> None:
        summary = summarize_project_context_adapter_result(
            {
                "enabled": True,
                "context_text": "PROJECT KNOWLEDGE CONTEXT private body",
                "summary": {"result_count": 2, "total_chars": 100},
                "error": None,
            }
        )

        encoded = json.dumps(summary)
        self.assertTrue(summary["context_included"])
        self.assertEqual(2, summary["result_count"])
        self.assertNotIn("private body", encoded)


if __name__ == "__main__":
    unittest.main()
