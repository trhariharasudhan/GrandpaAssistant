import os
import sys
import tempfile
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

import debug_session
import fix_audit_log
import fix_approval_flow
from api import web_api
from core import command_router


class DebugSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.session_path = os.path.join(self.temp_dir.name, "debug_sessions.jsonl")
        self.audit_path = os.path.join(self.temp_dir.name, "fix_audit.jsonl")
        self.patches = [
            patch.object(debug_session, "DEBUG_SESSIONS_PATH", self.session_path),
            patch.object(fix_audit_log, "FIX_AUDIT_LOG_PATH", self.audit_path),
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
        ]
        for item in self.patches:
            item.start()
        debug_session.clear_debug_sessions_for_tests()
        fix_audit_log.clear_fix_audit_log_for_tests()
        fix_approval_flow.clear_fix_approvals_for_tests()
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        debug_session.clear_debug_sessions_for_tests()
        fix_audit_log.clear_fix_audit_log_for_tests()
        fix_approval_flow.clear_fix_approvals_for_tests()
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_start_get_close_session(self) -> None:
        started = debug_session.start_debug_session(title="Port issue", source="test")

        self.assertEqual(debug_session.get_current_debug_session()["id"], started["id"])
        closed = debug_session.close_debug_session(note="done")
        self.assertEqual(closed["status"], "closed")
        self.assertIsNone(debug_session.get_current_debug_session())

    def test_attach_debug_report(self) -> None:
        debug_session.start_debug_session()
        debug_session.attach_debug_report({"summary": "Traceback", "error_text": "Error"})

        session = debug_session.get_current_debug_session()
        self.assertEqual(len(session["debug_reports"]), 1)

    def test_attach_fix_plan(self) -> None:
        debug_session.start_debug_session()
        debug_session.attach_fix_plan({"summary": "Plan", "suggested_commands": [{"command": "git status"}]})

        self.assertEqual(len(debug_session.get_current_debug_session()["fix_plans"]), 1)

    def test_attach_approval(self) -> None:
        debug_session.start_debug_session()
        approval = fix_approval_flow.create_fix_approval("command_suggestion", {"command": "git status"}, "Check status")

        session = debug_session.get_current_debug_session()
        self.assertEqual(session["fix_approvals"][0]["id"], approval["id"])

    def test_audit_event_attaches(self) -> None:
        debug_session.start_debug_session()
        event = fix_audit_log.append_fix_audit_event("created", message="hello")

        session = debug_session.get_current_debug_session()
        self.assertEqual(session["audit_events"][0]["event_type"], event["event_type"])

    def test_redaction_and_truncation(self) -> None:
        debug_session.start_debug_session()
        debug_session.attach_debug_report({"error_text": "password: swordfish " + ("x" * 2000), "token": "abc"})

        report = debug_session.get_current_debug_session()["debug_reports"][0]
        self.assertEqual(report["token"], "[REDACTED]")
        self.assertIn("[REDACTED]", report["error_text"])
        self.assertLessEqual(len(report["error_text"]), debug_session.MAX_TEXT_LENGTH + 20)

    def test_command_router_summaries(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)):
            command_router.process_command("start debug session", {}, input_mode="text")
            command_router.process_command("debug session summary", {}, input_mode="text")
            command_router.process_command("close debug session", {}, input_mode="text")

        self.assertIn("Started debug session", spoken[0])
        self.assertIn("Debug session", spoken[1])
        self.assertIn("Closed debug session", spoken[2])

    def test_api_protected_from_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.110", 50000))

        response = remote_client.get("/api/debug/session/current")

        self.assertEqual(response.status_code, 403)

    def test_api_start_current_list_close_localhost(self) -> None:
        start = self.client.post("/api/debug/session/start", json={"title": "API session"})
        current = self.client.get("/api/debug/session/current")
        sessions = self.client.get("/api/debug/sessions")
        closed = self.client.post("/api/debug/session/close", json={"note": "done"})

        self.assertEqual(start.status_code, 200)
        self.assertEqual(current.status_code, 200)
        self.assertTrue(sessions.json()["items"])
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.json()["status"], "closed")


if __name__ == "__main__":
    unittest.main()
