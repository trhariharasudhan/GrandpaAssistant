import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev" / "prompt_runtime_status.py"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


class PromptRuntimeStatusCliTests(unittest.TestCase):
    def _run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(PYTHON), str(SCRIPT), *args],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_script_exists(self) -> None:
        self.assertTrue(SCRIPT.is_file())

    def test_running_script_returns_valid_json(self) -> None:
        result = self._run_script()

        self.assertEqual(0, result.returncode, result.stderr)
        status = json.loads(result.stdout)
        self.assertIsInstance(status, dict)

    def test_json_contains_expected_safe_keys(self) -> None:
        result = self._run_script()
        status = json.loads(result.stdout)

        self.assertIn("runtime_enabled", status)
        self.assertIn("supported_modes", status)
        self.assertIn("available_prompt_files", status)
        self.assertIn("safe_to_expose", status)

    def test_output_does_not_contain_prompt_body_text(self) -> None:
        result = self._run_script()

        self.assertNotIn("You are GrandpaAssistant", result.stdout)
        self.assertNotIn("Automation safety rules:", result.stdout)

    def test_output_does_not_contain_reference_folder(self) -> None:
        result = self._run_script()

        self.assertNotIn("reference/system_prompts_leaks", result.stdout.replace("\\", "/"))

    def test_compact_returns_valid_compact_json(self) -> None:
        result = self._run_script("--compact")

        self.assertEqual(0, result.returncode, result.stderr)
        status = json.loads(result.stdout)
        self.assertIsInstance(status, dict)
        self.assertNotIn("\n  ", result.stdout)

    def test_check_exits_zero_under_safe_conditions(self) -> None:
        result = self._run_script("--check")

        self.assertEqual(0, result.returncode, result.stderr)
        status = json.loads(result.stdout)
        self.assertTrue(status["safe_to_expose"])
        self.assertFalse(status["reference_folder_used"])


if __name__ == "__main__":
    unittest.main()
