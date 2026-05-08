import os
import sys
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import debug_preflight_checklist
from api import web_api
from core import command_router


class DebugPreflightChecklistTests(unittest.TestCase):
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

    def _learning(self):
        return {
            "common_error_families": [
                {"family": "module_not_found", "count": 2},
                {"family": "port_in_use", "count": 1},
            ],
            "repeated_fix_patterns": [],
            "total_sessions_analyzed": 2,
            "no_command_executed": True,
        }

    def _diagnostics(self, ollama_status="warning"):
        return {
            "items": [
                {"key": "python_runtime", "status": "ok", "detail": "Python ready."},
                {"key": "data_dir", "status": "ok", "detail": "Data writable."},
                {"key": "log_dir", "status": "ok", "detail": "Logs writable."},
                {"key": "ollama_api", "status": ollama_status, "detail": "Ollama unavailable."},
            ]
        }

    def test_checklist_generated_from_learning_summary(self) -> None:
        with patch.object(debug_preflight_checklist, "build_debug_learning_summary", return_value=self._learning()):
            payload = debug_preflight_checklist.build_preflight_checklist()

        keys = {item["key"] for item in payload["checklist_items"]}
        self.assertIn("dependency_venv", keys)
        self.assertIn("port_readiness", keys)

    def test_safe_checks_return_structured_results(self) -> None:
        completed = Mock(returncode=0, stdout="ok", stderr="")
        with patch.object(debug_preflight_checklist, "build_debug_learning_summary", return_value=self._learning()), \
            patch.object(debug_preflight_checklist, "collect_startup_diagnostics", return_value=self._diagnostics()), \
            patch.object(debug_preflight_checklist.subprocess, "run", return_value=completed):
            payload = debug_preflight_checklist.run_preflight_checklist()

        self.assertTrue(payload["check_results"])
        self.assertTrue(all("key" in item and "status" in item for item in payload["check_results"]))

    def test_no_destructive_commands_used(self) -> None:
        completed = Mock(returncode=0, stdout="ok", stderr="")
        with patch.object(debug_preflight_checklist, "collect_startup_diagnostics", return_value=self._diagnostics()), \
            patch.object(debug_preflight_checklist.subprocess, "run", return_value=completed) as run:
            payload = debug_preflight_checklist.run_preflight_checklist()

        commands = [" ".join(call.args[0]) for call in run.call_args_list]
        forbidden = ["reset", "push --force", "delete", "remove-item", "stop-process", "taskkill", "install"]
        self.assertTrue(payload["no_destructive_action"])
        self.assertFalse(any(word in command.lower() for command in commands for word in forbidden))

    def test_ollama_unavailable_is_warning_not_failure(self) -> None:
        completed = Mock(returncode=0, stdout="ok", stderr="")
        with patch.object(debug_preflight_checklist, "collect_startup_diagnostics", return_value=self._diagnostics("error")), \
            patch.object(debug_preflight_checklist.subprocess, "run", return_value=completed):
            payload = debug_preflight_checklist.run_preflight_checklist()

        ollama = next(item for item in payload["check_results"] if item["key"] == "ollama_optional")
        self.assertEqual(ollama["status"], "warning")
        self.assertTrue(ollama["ok"])

    def test_command_router_command_works(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)), \
            patch.object(command_router, "run_preflight_checklist", return_value={"check_results": [], "checklist_items": [{"title": "Dependency"}]}):
            command_router.process_command("debug checklist", {}, input_mode="text")

        self.assertIn("Debug checklist", spoken[-1])

    def test_api_protected(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.170", 50000))

        response = remote_client.get("/api/debug/preflight-checklist")

        self.assertEqual(response.status_code, 403)

    def test_no_destructive_action_true(self) -> None:
        completed = Mock(returncode=0, stdout="ok", stderr="")
        with patch.object(debug_preflight_checklist, "collect_startup_diagnostics", return_value=self._diagnostics()), \
            patch.object(debug_preflight_checklist.subprocess, "run", return_value=completed):
            payload = debug_preflight_checklist.run_preflight_checklist()

        self.assertTrue(payload["no_destructive_action"])

    def test_validation_script_missing_reports_warning(self) -> None:
        completed = Mock(returncode=0, stdout="ok", stderr="")

        def fake_exists(path):
            return not str(path).endswith(os.path.join("scripts", "dev", "full_backend_validation.py"))

        with patch.object(debug_preflight_checklist, "collect_startup_diagnostics", return_value=self._diagnostics()), \
            patch.object(debug_preflight_checklist.subprocess, "run", return_value=completed), \
            patch.object(debug_preflight_checklist.os.path, "exists", side_effect=fake_exists):
            payload = debug_preflight_checklist.run_preflight_checklist()

        validation = next(item for item in payload["check_results"] if item["key"] == "validation_script")
        self.assertEqual(validation["status"], "warning")


if __name__ == "__main__":
    unittest.main()
