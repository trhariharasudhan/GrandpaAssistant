import os
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import debug_assistant
from api import web_api
from core import command_router


class DebugAssistantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.patches = [
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
        ]
        for item in self.patches:
            item.start()
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()

    def _screen_payload(self, text: str, ok=True):
        return {
            "ok": ok,
            "warning": not ok,
            "text": text,
            "lines": text.splitlines() if text else [],
            "error_detection": {"has_error_like_text": bool(text), "lines": text.splitlines() if text else []},
        }

    def test_python_module_not_found_produces_install_or_import_cause(self) -> None:
        text = "Traceback (most recent call last):\nModuleNotFoundError: No module named 'yaml'"

        causes = debug_assistant.infer_likely_causes(text, language="en")
        steps = debug_assistant.suggest_safe_debug_steps(text, language="en")

        self.assertTrue(any("package" in cause.lower() or "interpreter" in cause.lower() for cause in causes))
        self.assertTrue(any("virtual environment" in step.lower() for step in steps["safe_steps"]))

    def test_port_already_in_use_suggests_checking_running_process(self) -> None:
        text = "OSError: [WinError 10048] address already in use on port 8000"

        causes = debug_assistant.infer_likely_causes(text, language="en")
        steps = debug_assistant.suggest_safe_debug_steps(text, language="en")

        self.assertTrue(any("already using" in cause.lower() for cause in causes))
        self.assertTrue(any("already running" in step.lower() for step in steps["safe_steps"]))

    def test_permission_denied_suggests_admin_or_permission_cause(self) -> None:
        text = "Permission denied: access is denied"

        causes = debug_assistant.infer_likely_causes(text, language="en")

        self.assertTrue(any("permission" in cause.lower() for cause in causes))

    def test_file_not_found_suggests_path_check(self) -> None:
        text = "FileNotFoundError: No such file or directory: 'config.json'"

        steps = debug_assistant.suggest_safe_debug_steps(text, language="en")

        self.assertTrue(any("path" in step.lower() or "working directory" in step.lower() for step in steps["safe_steps"]))

    def test_no_visible_error_returns_friendly_fallback(self) -> None:
        with patch.object(debug_assistant, "summarize_screen_context", return_value=self._screen_payload("", ok=True)), \
            patch.object(debug_assistant, "summarize_active_window", return_value={"ok": True, "active_window": {"kind": "editor"}}):
            report = debug_assistant.build_debug_report(language="en")

        self.assertFalse(report["ok"])
        self.assertIn("do not see", report["summary"])
        self.assertTrue(report["no_command_executed"])

    def test_tamil_command_returns_tamil_friendly_report(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=spoken.append), \
            patch.object(command_router, "build_debug_report", return_value={"summary": "Visible error idhu.", "likely_causes": ["Path wrong-a irukkalaam."], "safe_steps": ["Path check pannunga."], "risky_steps": [], "language": "ta"}) as report:
            command_router.process_command("enna error idhu", {}, input_mode="text")

        report.assert_called_with(language="ta")
        self.assertIn("Naan command run pannala", spoken[-1])

    def test_api_route_allows_localhost(self) -> None:
        with patch.object(web_api, "build_debug_report", return_value={"ok": True, "summary": "Debug", "no_command_executed": True}):
            response = self.client.get("/api/debug/report")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["no_command_executed"])

    def test_api_route_blocks_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.70", 50000))

        response = remote_client.get("/api/debug/report")

        self.assertEqual(response.status_code, 403)

    def test_api_route_allows_remote_admin(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.70", 50000))
        admin_context = {"user": {"id": 1, "username": "admin", "role": "admin"}}

        with patch.object(web_api, "authenticate_app_token", return_value=admin_context), \
            patch.object(web_api, "build_debug_report", return_value={"ok": True, "summary": "Debug", "no_command_executed": True}):
            response = remote_client.get("/api/debug/report", headers={"Authorization": "Bearer admin-token"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["no_command_executed"])

    def test_no_command_executed_flag_is_true(self) -> None:
        text = "ImportError: cannot import name 'thing'"
        with patch.object(debug_assistant, "summarize_screen_context", return_value=self._screen_payload(text)), \
            patch.object(debug_assistant, "summarize_active_window", return_value={"ok": True, "active_window": {"kind": "editor"}}):
            report = debug_assistant.build_debug_report(language="en")

        self.assertTrue(report["no_command_executed"])
        self.assertTrue(report["safe_steps"])


if __name__ == "__main__":
    unittest.main()
