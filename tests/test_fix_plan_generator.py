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

import fix_plan_generator
from api import web_api
from core import command_router


class FixPlanGeneratorTests(unittest.TestCase):
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

    def _report(self, families, text):
        return {
            "ok": True,
            "language": "en",
            "summary": "Debug report",
            "error_text": text,
            "error_families": families,
            "safe_steps": ["Read the first error line."],
            "active_window": {"kind": "editor", "title": "main.py - VS Code"},
            "no_command_executed": True,
        }

    def test_module_not_found_suggests_venv_requirements_and_pip_install_as_suggestion_only(self) -> None:
        plan = fix_plan_generator.build_fix_plan_from_debug_report(
            self._report(["module_not_found", "import_error"], "ModuleNotFoundError: No module named 'yaml'"),
            language="en",
        )

        commands = " ".join(item["command"] for item in plan["suggested_commands"])
        checks = " ".join(plan["safe_checks"] + plan["suggested_file_checks"])
        self.assertIn("pip install", commands)
        self.assertIn("requirements", checks.lower())
        self.assertTrue(all(item["suggestion_only"] for item in plan["suggested_commands"]))
        self.assertTrue(plan["no_command_executed"])
        self.assertTrue(plan["no_file_edited"])

    def test_git_push_rejected_suggests_pull_rebase_not_force_push(self) -> None:
        plan = fix_plan_generator.build_fix_plan_from_debug_report(
            self._report(["git"], "fatal: failed to push some refs to origin main"),
            language="en",
        )

        combined = " ".join(item["command"] for item in plan["suggested_commands"] + plan["risky_commands"])
        self.assertIn("git pull --rebase", combined)
        self.assertNotIn("force", combined.lower())
        self.assertNotIn("reset --hard", combined.lower())

    def test_port_in_use_suggests_identify_process_not_killing_automatically(self) -> None:
        plan = fix_plan_generator.build_fix_plan_from_debug_report(
            self._report(["port_in_use"], "address already in use on port 8765"),
            language="en",
        )

        suggested = " ".join(item["command"] for item in plan["suggested_commands"])
        risky = " ".join(item["command"] for item in plan["risky_commands"])
        self.assertIn("netstat", suggested)
        self.assertIn("Stop-Process", risky)
        self.assertTrue(all(item["requires_confirmation"] for item in plan["risky_commands"]))

    def test_permission_denied_suggests_admin_or_permission_checks(self) -> None:
        plan = fix_plan_generator.build_fix_plan_from_debug_report(
            self._report(["permission_denied"], "Permission denied"),
            language="en",
        )

        combined = " ".join(plan["safe_checks"] + [item["command"] for item in plan["risky_commands"]])
        self.assertIn("permission", combined.lower())
        self.assertIn("Administrator", combined)

    def test_file_not_found_suggests_path_checks(self) -> None:
        plan = fix_plan_generator.build_fix_plan_from_debug_report(
            self._report(["file_not_found"], "FileNotFoundError: No such file or directory: config.json"),
            language="en",
        )

        checks = " ".join(plan["suggested_file_checks"])
        self.assertIn("path", checks.lower())

    def test_plan_has_no_command_executed_and_no_file_edited_true(self) -> None:
        plan = fix_plan_generator.build_fix_plan_from_debug_report(
            self._report(["python_traceback"], "Traceback (most recent call last):"),
            language="en",
        )

        self.assertTrue(plan["no_command_executed"])
        self.assertTrue(plan["no_file_edited"])
        self.assertTrue(plan["requires_confirmation"])

    def test_tamil_command_returns_tamil_friendly_plan(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=spoken.append), \
            patch.object(command_router, "build_fix_plan", return_value={"summary": "Idhu safe fix plan.", "safe_checks": ["Path check pannunga."], "suggested_commands": [], "risky_commands": [], "suggested_file_checks": [], "language": "ta"}) as plan:
            command_router.process_command("idha epdi fix panradhu", {}, input_mode="text")

        plan.assert_called_with(language="ta")
        self.assertIn("Naan command run pannala", spoken[-1])

    def test_api_route_allows_localhost(self) -> None:
        with patch.object(web_api, "build_fix_plan", return_value={"ok": True, "no_command_executed": True, "no_file_edited": True}):
            response = self.client.get("/api/debug/fix-plan")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["no_command_executed"])
        self.assertTrue(response.json()["no_file_edited"])

    def test_api_route_blocks_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.80", 50000))

        response = remote_client.get("/api/debug/fix-plan")

        self.assertEqual(response.status_code, 403)

    def test_api_route_allows_remote_admin(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.80", 50000))
        admin_context = {"user": {"id": 1, "username": "admin", "role": "admin"}}

        with patch.object(web_api, "authenticate_app_token", return_value=admin_context), \
            patch.object(web_api, "build_fix_plan", return_value={"ok": True, "no_command_executed": True, "no_file_edited": True}):
            response = remote_client.get("/api/debug/fix-plan", headers={"Authorization": "Bearer admin-token"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["no_file_edited"])


if __name__ == "__main__":
    unittest.main()
