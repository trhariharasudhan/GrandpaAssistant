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

import fix_approval_flow
from api import web_api
from core import command_router


class FixApprovalFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.patches = [
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
        ]
        for item in self.patches:
            item.start()
        fix_approval_flow.clear_fix_approvals_for_tests()
        command_router._remember_fix_plan(None)
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        fix_approval_flow.clear_fix_approvals_for_tests()
        command_router._remember_fix_plan(None)
        for item in reversed(self.patches):
            item.stop()

    def test_approval_id_unique(self) -> None:
        first = fix_approval_flow.create_fix_approval("command_suggestion", {"command": "git status"}, "Check git")
        second = fix_approval_flow.create_fix_approval("command_suggestion", {"command": "whoami"}, "Check account")

        self.assertNotEqual(first["id"], second["id"])

    def test_list_and_dismiss_works(self) -> None:
        approval = fix_approval_flow.create_fix_approval("command_suggestion", {"command": "git status"}, "Check git")

        self.assertEqual(len(fix_approval_flow.list_pending_fix_approvals()), 1)
        self.assertTrue(fix_approval_flow.dismiss_fix_approval(approval["id"]))
        self.assertEqual(fix_approval_flow.list_pending_fix_approvals(), [])

    def test_placeholders_block_execution(self) -> None:
        approval = fix_approval_flow.create_fix_approval(
            "command_suggestion",
            {"command": "python -m py_compile <changed-file.py>"},
            "Compile check",
        )

        result = fix_approval_flow.execute_fix_approval(approval["id"])

        self.assertFalse(result["executed"])
        self.assertIn("placeholder", result["message"].lower())

    def test_risky_command_rejected(self) -> None:
        validation = fix_approval_flow.validate_fix_action({"action_type": "command_suggestion", "command": "npm install"})

        self.assertFalse(validation["ok"])
        self.assertFalse(validation["runnable"])

    def test_read_only_allowed_command_executes_mocked_subprocess(self) -> None:
        approval = fix_approval_flow.create_fix_approval("command_suggestion", {"command": "git status"}, "Check git")
        completed = Mock(returncode=0, stdout="clean", stderr="")

        with patch.object(fix_approval_flow.subprocess, "run", return_value=completed) as run:
            result = fix_approval_flow.execute_fix_approval(approval["id"])

        run.assert_called_once()
        self.assertTrue(result["executed"])
        self.assertEqual(result["stdout"], "clean")

    def test_allow_without_approval_fails_safely(self) -> None:
        result = fix_approval_flow.execute_fix_approval("fix-missing")

        self.assertFalse(result["executed"])
        self.assertIn("not found", result["message"])

    def test_apply_fix_without_latest_plan_asks_for_plan(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=spoken.append):
            command_router.process_command("apply fix", {}, input_mode="text")

        self.assertIn("Ask for a fix plan first", spoken[-1])

    def test_apply_fix_creates_pending_approval_from_latest_plan(self) -> None:
        plan = {
            "suggested_commands": [
                {"command": "git status", "reason": "Inspect branch state."},
                {"command": "python -m pip show <missing-package>", "reason": "Placeholder should be skipped."},
            ]
        }
        command_router._remember_fix_plan(plan)
        spoken = []

        with patch.object(command_router, "speak", side_effect=spoken.append):
            command_router.process_command("apply suggested fix", {}, input_mode="text")

        approvals = fix_approval_flow.list_pending_fix_approvals()
        self.assertEqual(len(approvals), 1)
        self.assertEqual(approvals[0]["payload"]["command"], "git status")
        self.assertIn("allow", spoken[-1])

    def test_command_router_allow_executes_fix_approval(self) -> None:
        approval = fix_approval_flow.create_fix_approval("command_suggestion", {"command": "whoami"}, "Check user")
        spoken = []

        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)), \
            patch.object(command_router, "execute_fix_approval", return_value={"executed": True, "stdout": "user"}):
            command_router.process_command(f"allow {approval['id']}", {}, input_mode="text")

        self.assertIn("Fix approval executed", spoken[-1])

    def test_api_protected_from_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.90", 50000))

        response = remote_client.get("/api/debug/fix-approvals")

        self.assertEqual(response.status_code, 403)

    def test_api_create_and_dismiss_localhost(self) -> None:
        create_response = self.client.post(
            "/api/debug/fix-approvals",
            json={"action_type": "command_suggestion", "payload": {"command": "git status"}, "reason": "Check git"},
        )

        self.assertEqual(create_response.status_code, 200)
        approval_id = create_response.json()["id"]
        dismiss_response = self.client.post(f"/api/debug/fix-approvals/{approval_id}/dismiss")
        self.assertEqual(dismiss_response.status_code, 200)
        self.assertTrue(dismiss_response.json()["ok"])

    def test_no_force_push_or_delete_commands_allowed(self) -> None:
        blocked = [
            "git push --force origin main",
            "git reset --hard",
            "delete file important.txt",
            "Remove-Item important.txt",
        ]

        for command in blocked:
            with self.subTest(command=command):
                validation = fix_approval_flow.validate_fix_action({"action_type": "command_suggestion", "command": command})
                self.assertFalse(validation["ok"])


if __name__ == "__main__":
    unittest.main()
