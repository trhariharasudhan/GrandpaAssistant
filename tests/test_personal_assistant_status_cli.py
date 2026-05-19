import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev" / "personal_assistant_status.py"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
SCRIPT_DIR = ROOT / "scripts" / "dev"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import personal_assistant_status


class PersonalAssistantStatusCliTests(unittest.TestCase):
    def _run_script(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            [str(PYTHON), str(SCRIPT), *args],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
            env=merged_env,
        )

    def test_script_exists(self) -> None:
        self.assertTrue(SCRIPT.is_file())

    def test_status_script_runs_in_safe_text_mode(self) -> None:
        result = self._run_script()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("GrandpaAssistant Personal Assistant Status", result.stdout)
        self.assertIn("Registered tools:", result.stdout)

    def test_json_output_is_valid_and_contains_expected_fields(self) -> None:
        result = self._run_script("--json")

        self.assertEqual(0, result.returncode, result.stderr)
        status = json.loads(result.stdout)
        self.assertTrue(status["read_only"])
        self.assertTrue(status["safe_to_expose"])
        self.assertIn("tools", status)
        self.assertIn("scheduler", status)
        self.assertIn("voice_runtime", status)
        self.assertIn("memory_manager", status)
        self.assertIn("screen_ocr", status)
        self.assertGreater(status["tools"]["tool_count"], 0)

    def test_no_private_memory_values_are_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "memory.json"
            memory_path.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "memories": [
                            {
                                "memory_id": "mem_private",
                                "category": "user_preferences",
                                "key": "favorite_place",
                                "value": "private beach house",
                                "source": "test",
                                "confidence": 0.9,
                                "created_at": "2026-01-01T00:00:00Z",
                                "updated_at": "2026-01-01T00:00:00Z",
                                "last_used_at": "",
                                "status": "active",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self._run_script(
                "--json",
                env={"GRANDPA_PERSONAL_ASSISTANT_MEMORY_PATH": str(memory_path)},
            )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("private beach house", result.stdout)
        status = json.loads(result.stdout)
        self.assertEqual(1, status["memory_manager"]["memory_count"])
        self.assertEqual(1, status["memory_manager"]["count_by_category"]["user_preferences"])
        self.assertFalse(status["memory_manager"]["private_values_exposed"])

    def test_check_mode_returns_success_for_healthy_core(self) -> None:
        result = self._run_script("--check")

        self.assertEqual(0, result.returncode, result.stderr)
        status = json.loads(result.stdout)
        self.assertTrue(status["ok"])
        self.assertEqual([], status["critical_failures"])

    def test_missing_optional_adapters_are_warnings_not_hard_failures(self) -> None:
        with patch.object(personal_assistant_status, "_tool_status", return_value={"ok": True, "tool_count": 1, "tool_names": ["volume_control"]}), patch.object(
            personal_assistant_status,
            "_voice_status",
            return_value={"ok": False, "available": False, "stt_provider": {"available": False}},
        ), patch.object(
            personal_assistant_status,
            "_screen_status",
            return_value={"ok": True, "window_awareness_importable": True, "screen_awareness_importable": False},
        ):
            status = personal_assistant_status.build_personal_assistant_status()

        self.assertTrue(status["ok"])
        self.assertEqual([], status["critical_failures"])
        self.assertIn("voice_runtime_warning", status["warnings"])
        self.assertIn("screen_ocr_optional_adapter_missing", status["warnings"])

    def test_verbose_safe_includes_extra_metadata_without_bodies(self) -> None:
        result = self._run_script("--json", "--verbose-safe")

        self.assertEqual(0, result.returncode, result.stderr)
        status = json.loads(result.stdout)
        self.assertIn("environment_flags", status)
        self.assertNotIn("last_transcript", result.stdout)
        self.assertNotIn("last_command", result.stdout)
        self.assertFalse(status["screenshots_captured"])
        self.assertFalse(status["llm_provider_called"])


if __name__ == "__main__":
    unittest.main()
