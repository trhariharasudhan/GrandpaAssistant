import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "dev" / "runtime_backend_check.py"
spec = importlib.util.spec_from_file_location("runtime_backend_check", SCRIPT_PATH)
runtime_backend_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime_backend_check)


class RuntimeBackendCheckTests(unittest.TestCase):
    def test_port_list_includes_common_backend_ports(self) -> None:
        self.assertIn(8765, runtime_backend_check.PORTS_TO_CHECK)
        self.assertIn(8000, runtime_backend_check.PORTS_TO_CHECK)

    def test_endpoint_list_includes_required_routes(self) -> None:
        endpoints = set(runtime_backend_check.ENDPOINTS_TO_CHECK)
        self.assertIn("/api/health", endpoints)
        self.assertIn("/api/backend/stability", endpoints)
        self.assertIn("/api/debug/dashboard", endpoints)
        self.assertIn("/api/debug/docs-summary", endpoints)

    def test_response_preview_truncates_safely(self) -> None:
        preview = runtime_backend_check.response_preview("x" * 200, limit=40)

        self.assertLessEqual(len(preview), 40)
        self.assertTrue(preview.endswith("...[truncated]"))

    def test_response_preview_compacts_json(self) -> None:
        preview = runtime_backend_check.response_preview({"ok": True, "message": "hello\nworld"})

        self.assertIn('"ok": true', preview.lower())
        self.assertNotIn("\n", preview)

    def test_endpoint_preview_avoids_nested_health_runtime_context(self) -> None:
        preview = runtime_backend_check.endpoint_response_preview(
            "/api/health",
            {
                "ok": True,
                "service": "grandpa-assistant-api",
                "runtime": {"last_user_message": "private local text"},
            },
        )

        self.assertIn("grandpa-assistant-api", preview)
        self.assertNotIn("private local text", preview)

    def test_endpoint_preview_handles_raw_health_json_text(self) -> None:
        preview = runtime_backend_check.endpoint_response_preview(
            "/api/health",
            '{"ok":true,"service":"grandpa-assistant-api","runtime":{"last_user_message":"private"}}',
        )

        self.assertIn("grandpa-assistant-api", preview)
        self.assertNotIn("private", preview)

    def test_command_path_detection_prefers_venv_python(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "backend").mkdir()
            (root / "scripts").mkdir()
            (root / "backend" / "desktop_backend_entry.py").write_text("print('ok')", encoding="utf-8")
            venv_dir = root / ".venv" / "Scripts"
            venv_dir.mkdir(parents=True)
            python_path = venv_dir / "python.exe"
            python_path.write_text("", encoding="utf-8")

            self.assertEqual(runtime_backend_check.find_project_root(root), root)
            self.assertEqual(runtime_backend_check.resolve_python_exe(root), str(python_path))
            self.assertEqual(
                runtime_backend_check.backend_entry_path(root),
                str(root / "backend" / "desktop_backend_entry.py"),
            )

    def test_command_path_detection_falls_back_to_current_python(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "backend").mkdir()
            (root / "scripts").mkdir()
            (root / "backend" / "desktop_backend_entry.py").write_text("print('ok')", encoding="utf-8")

            with patch.object(runtime_backend_check.sys, "executable", "python-current"):
                self.assertEqual(runtime_backend_check.resolve_python_exe(root), "python-current")


if __name__ == "__main__":
    unittest.main()
