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
import debug_session_search
from api import web_api
from core import command_router


class DebugSessionSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.session_path = os.path.join(self.temp_dir.name, "debug_sessions.jsonl")
        self.patches = [
            patch.object(debug_session, "DEBUG_SESSIONS_PATH", self.session_path),
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
        ]
        for item in self.patches:
            item.start()
        debug_session.clear_debug_sessions_for_tests()
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        debug_session.clear_debug_sessions_for_tests()
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def _add_session(self, title, updated_at, report=None, plan=None, approval=None, audit=None):
        debug_session.start_debug_session(title=title, source="test")
        raw = debug_session._CURRENT_DEBUG_SESSION
        raw["updated_at"] = updated_at
        if report:
            raw["debug_reports"].append(report)
        if plan:
            raw["fix_plans"].append(plan)
        if approval:
            raw["fix_approvals"].append(approval)
        if audit:
            raw["audit_events"].append(audit)
        debug_session._write_snapshot(raw)
        debug_session.close_debug_session(status="closed")
        return raw["id"]

    def test_search_by_error_family(self) -> None:
        session_id = self._add_session(
            "Python import issue",
            "2026-05-08T01:00:00Z",
            report={"summary": "Missing dependency", "error_families": ["module_not_found"], "error_text": "No module named yaml"},
        )

        results = debug_session_search.search_debug_sessions("module_not_found")

        self.assertEqual(results["results"][0]["session_id"], session_id)
        self.assertIn("error_families", results["results"][0]["matched_fields"])

    def test_search_by_fix_plan_summary(self) -> None:
        self._add_session(
            "Fix plan",
            "2026-05-08T01:00:00Z",
            plan={"summary": "Check virtual environment and requirements"},
        )

        results = debug_session_search.search_debug_sessions("requirements")

        self.assertTrue(results["results"])
        self.assertIn("fix_plan_summary", results["results"][0]["matched_fields"])

    def test_search_by_approval_command(self) -> None:
        self._add_session(
            "Approval",
            "2026-05-08T01:00:00Z",
            approval={"payload": {"command": "git status"}, "reason": "Inspect repo"},
        )

        results = debug_session_search.search_debug_sessions("git status")

        self.assertTrue(results["results"])
        self.assertIn("approval_command", results["results"][0]["matched_fields"])

    def test_no_match_returns_empty_safe_result(self) -> None:
        self._add_session("Port issue", "2026-05-08T01:00:00Z", report={"summary": "Port busy"})

        results = debug_session_search.search_debug_sessions("banana")

        self.assertEqual(results["results"], [])
        self.assertIn("No matching", debug_session_search.summarize_debug_search_results(results))

    def test_results_sorted_by_score_then_updated_at(self) -> None:
        low_id = self._add_session("Port", "2026-05-08T03:00:00Z", report={"summary": "port"})
        high_id = self._add_session("Port port", "2026-05-08T02:00:00Z", report={"summary": "port in use", "error_text": "port port"})

        results = debug_session_search.search_debug_sessions("port")

        self.assertEqual(results["results"][0]["session_id"], high_id)
        self.assertNotEqual(results["results"][0]["session_id"], low_id)

    def test_redaction_works(self) -> None:
        self._add_session(
            "Secret issue",
            "2026-05-08T01:00:00Z",
            report={"summary": "password: swordfish", "error_text": "token=abc123"},
        )

        results = debug_session_search.search_debug_sessions("password")
        snippet = results["results"][0]["snippet"]

        self.assertIn("[REDACTED]", snippet)
        self.assertNotIn("swordfish", snippet)

    def test_command_router_search_command_works(self) -> None:
        self._add_session("Python issue", "2026-05-08T01:00:00Z", report={"summary": "ModuleNotFoundError"})
        spoken = []

        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)):
            command_router.process_command("search debug sessions for ModuleNotFoundError", {}, input_mode="text")

        self.assertIn("Debug search results", spoken[-1])

    def test_api_protected_from_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.140", 50000))

        response = remote_client.get("/api/debug/sessions/search?q=port")

        self.assertEqual(response.status_code, 403)

    def test_api_search_allows_localhost(self) -> None:
        self._add_session("Port issue", "2026-05-08T01:00:00Z", report={"summary": "port in use"})

        response = self.client.get("/api/debug/sessions/search?q=port")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["results"])


if __name__ == "__main__":
    unittest.main()
