import os
import sys
import tempfile
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

import fix_audit_log
import fix_approval_flow
from api import web_api
from core import command_router


class FixAuditLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_path = os.path.join(self.temp_dir.name, "fix_audit.jsonl")
        self.patches = [
            patch.object(fix_audit_log, "FIX_AUDIT_LOG_PATH", self.audit_path),
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
        ]
        for item in self.patches:
            item.start()
        fix_approval_flow.clear_fix_approvals_for_tests()
        fix_audit_log.clear_fix_audit_log_for_tests()
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        fix_approval_flow.clear_fix_approvals_for_tests()
        fix_audit_log.clear_fix_audit_log_for_tests()
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_created_event_logged(self) -> None:
        approval = fix_approval_flow.create_fix_approval("command_suggestion", {"command": "git status"}, "Check status")

        events = fix_audit_log.list_fix_audit_events()

        self.assertEqual(events[0]["event_type"], "created")
        self.assertEqual(events[0]["approval"]["id"], approval["id"])

    def test_dismissed_event_logged(self) -> None:
        approval = fix_approval_flow.create_fix_approval("command_suggestion", {"command": "git status"}, "Check status")
        fix_approval_flow.dismiss_fix_approval(approval["id"])

        events = fix_audit_log.list_fix_audit_events()

        self.assertEqual(events[0]["event_type"], "dismissed")

    def test_executed_event_logged_with_mocked_subprocess(self) -> None:
        approval = fix_approval_flow.create_fix_approval("command_suggestion", {"command": "git status"}, "Check status")
        completed = Mock(returncode=0, stdout="clean", stderr="")

        with patch.object(fix_approval_flow.subprocess, "run", return_value=completed):
            fix_approval_flow.execute_fix_approval(approval["id"])

        events = fix_audit_log.list_fix_audit_events()
        self.assertEqual(events[0]["event_type"], "executed")
        self.assertEqual(events[0]["result"]["stdout"], "clean")

    def test_blocked_risky_action_logged(self) -> None:
        approval = fix_approval_flow.create_fix_approval("command_suggestion", {"command": "npm install"}, "Install")
        result = fix_approval_flow.execute_fix_approval(approval["id"])

        events = fix_audit_log.list_fix_audit_events()
        self.assertFalse(result["executed"])
        self.assertEqual(events[0]["event_type"], "blocked")

    def test_stdout_stderr_truncated_and_redacted(self) -> None:
        approval = fix_approval_flow.create_fix_approval("command_suggestion", {"command": "git status"}, "Check status")
        secret_text = "token=abc123 " + ("x" * 2000)
        completed = Mock(returncode=1, stdout=secret_text, stderr="password: swordfish")

        with patch.object(fix_approval_flow.subprocess, "run", return_value=completed):
            fix_approval_flow.execute_fix_approval(approval["id"])

        event = fix_audit_log.list_fix_audit_events()[0]
        self.assertIn("[REDACTED]", event["result"]["stdout"])
        self.assertIn("[REDACTED]", event["result"]["stderr"])
        self.assertLessEqual(len(event["result"]["stdout"]), fix_audit_log.MAX_TEXT_LENGTH + 20)

    def test_api_protected(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.100", 50000))

        response = remote_client.get("/api/debug/fix-audit")

        self.assertEqual(response.status_code, 403)

    def test_api_allows_localhost(self) -> None:
        fix_approval_flow.create_fix_approval("command_suggestion", {"command": "git status"}, "Check status")

        response = self.client.get("/api/debug/fix-audit")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["items"])

    def test_command_router_shows_audit_summary(self) -> None:
        fix_approval_flow.create_fix_approval("command_suggestion", {"command": "git status"}, "Check status")
        spoken = []

        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)):
            command_router.process_command("fix audit", {}, input_mode="text")

        self.assertIn("Recent fix audit events", spoken[-1])


if __name__ == "__main__":
    unittest.main()
