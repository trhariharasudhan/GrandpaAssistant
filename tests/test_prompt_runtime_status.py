import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from core.runtime_prompt_adapter import RUNTIME_PROMPT_ENV
from core.prompt_runtime_status import EXPECTED_PROMPT_FILES, get_prompt_runtime_status
from project_knowledge.project_context_adapter import PROJECT_CONTEXT_ENV


class PromptRuntimeStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_env = os.environ.pop(RUNTIME_PROMPT_ENV, None)
        self.previous_project_env = os.environ.pop(PROJECT_CONTEXT_ENV, None)

    def tearDown(self) -> None:
        if self.previous_env is None:
            os.environ.pop(RUNTIME_PROMPT_ENV, None)
        else:
            os.environ[RUNTIME_PROMPT_ENV] = self.previous_env
        if self.previous_project_env is None:
            os.environ.pop(PROJECT_CONTEXT_ENV, None)
        else:
            os.environ[PROJECT_CONTEXT_ENV] = self.previous_project_env

    def test_status_is_dict_and_json_safe(self) -> None:
        status = get_prompt_runtime_status()

        self.assertIsInstance(status, dict)
        self.assertIsInstance(json.dumps(status), str)

    def test_contains_expected_keys(self) -> None:
        status = get_prompt_runtime_status()

        self.assertEqual(
            {
                "runtime_enabled",
                "env_var",
                "supported_modes",
                "active_consumer",
                "available_prompt_files",
                "missing_expected_prompt_files",
                "metadata_fields",
                "project_context_enabled",
                "project_context_env_var",
                "project_context_requires_runtime_prompts",
                "reference_folder_used",
                "safe_to_expose",
            },
            set(status),
        )

    def test_does_not_include_prompt_body_text(self) -> None:
        status_text = json.dumps(get_prompt_runtime_status())

        self.assertNotIn("You are GrandpaAssistant", status_text)
        self.assertNotIn("Automation safety rules:", status_text)
        self.assertIn("base/core.txt", status_text)

    def test_does_not_include_reference_folder(self) -> None:
        status_text = json.dumps(get_prompt_runtime_status()).replace("\\", "/")

        self.assertNotIn("reference/system_prompts_leaks", status_text)
        self.assertFalse(get_prompt_runtime_status()["reference_folder_used"])

    def test_runtime_enabled_follows_env_flag(self) -> None:
        self.assertFalse(get_prompt_runtime_status()["runtime_enabled"])

        os.environ[RUNTIME_PROMPT_ENV] = "on"

        self.assertTrue(get_prompt_runtime_status()["runtime_enabled"])

    def test_project_context_flag_state_is_safe_metadata(self) -> None:
        status = get_prompt_runtime_status()

        self.assertFalse(status["project_context_enabled"])
        self.assertEqual(PROJECT_CONTEXT_ENV, status["project_context_env_var"])
        self.assertTrue(status["project_context_requires_runtime_prompts"])

        os.environ[PROJECT_CONTEXT_ENV] = "yes"

        self.assertTrue(get_prompt_runtime_status()["project_context_enabled"])

    def test_missing_expected_files_reported_safely(self) -> None:
        with patch("core.prompt_runtime_status.list_available_prompts", return_value=["base/core.txt"]):
            status = get_prompt_runtime_status()

        self.assertIn("modes/default.txt", status["missing_expected_prompt_files"])
        self.assertEqual(["base/core.txt"], status["available_prompt_files"])

    def test_supported_modes_included(self) -> None:
        modes = get_prompt_runtime_status()["supported_modes"]

        self.assertIn("default", modes)
        self.assertIn("coding", modes)
        self.assertIn("planning", modes)

    def test_metadata_fields_included(self) -> None:
        fields = get_prompt_runtime_status()["metadata_fields"]

        self.assertIn("runtime_enabled", fields)
        self.assertIn("selected_mode", fields)
        self.assertIn("prompt_length", fields)
        self.assertIn("memory_context_included", fields)
        self.assertIn("project_context_included", fields)
        self.assertIn("project_context_result_count", fields)

    def test_status_does_not_include_memory_content(self) -> None:
        status_text = json.dumps(get_prompt_runtime_status())

        self.assertNotIn("User likes private memory", status_text)
        self.assertNotIn("memory_context:", status_text.lower())

    def test_expected_prompt_files_constant(self) -> None:
        self.assertIn("modes/research.txt", EXPECTED_PROMPT_FILES)
        self.assertIn("modes/planning.txt", EXPECTED_PROMPT_FILES)

    def test_planning_prompt_file_is_reported_available(self) -> None:
        status = get_prompt_runtime_status()

        self.assertIn("modes/planning.txt", status["available_prompt_files"])
        self.assertNotIn("modes/planning.txt", status["missing_expected_prompt_files"])


if __name__ == "__main__":
    unittest.main()
