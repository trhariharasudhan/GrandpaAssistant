import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev" / "project_context_status.py"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


class ProjectContextStatusCliTests(unittest.TestCase):
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

    def test_cli_outputs_valid_json(self) -> None:
        result = self._run_script()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIsInstance(json.loads(result.stdout), dict)

    def test_compact_output_valid_json(self) -> None:
        result = self._run_script("--compact")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIsInstance(json.loads(result.stdout), dict)
        self.assertNotIn("\n  ", result.stdout)

    def test_check_exits_zero_in_safe_state(self) -> None:
        result = self._run_script("--check")

        self.assertEqual(0, result.returncode, result.stderr)
        status = json.loads(result.stdout)
        self.assertTrue(status["safe_to_expose"])
        self.assertFalse(status["reference_folder_used"])
        self.assertFalse(status["context_body_exposed"])
        self.assertFalse(status["snippet_body_exposed"])

    def test_output_does_not_expose_bodies(self) -> None:
        result = self._run_script()
        output = result.stdout.lower()

        self.assertNotIn("project knowledge context\nfile:", output)
        self.assertNotIn("context_text", output)
        self.assertNotIn("snippet_text", output)
        self.assertNotIn("reference/system_prompts_leaks", output.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
