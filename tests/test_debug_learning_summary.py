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

import debug_learning_summary
import debug_session
from api import web_api
from core import command_router


class DebugLearningSummaryTests(unittest.TestCase):
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

    def _add_session(self, families=None, summary="Check venv", command="python -m pip show yaml"):
        debug_session.start_debug_session(title="Learning", source="test")
        raw = debug_session._CURRENT_DEBUG_SESSION
        raw["debug_reports"].append({
            "summary": "ModuleNotFoundError password: swordfish",
            "error_families": families or ["module_not_found"],
            "error_text": "token=abc123",
        })
        raw["fix_plans"].append({
            "summary": summary,
            "safe_checks": ["Verify active virtual environment"],
            "suggested_commands": [{"command": command, "reason": "Check dependency"}],
        })
        debug_session._write_snapshot(raw)
        debug_session.close_debug_session(status="closed")

    def test_counts_repeated_error_families(self) -> None:
        self._add_session(["module_not_found"])
        self._add_session(["module_not_found", "import_error"])

        payload = debug_learning_summary.build_debug_learning_summary()

        counts = {item["family"]: item["count"] for item in payload["common_error_families"]}
        self.assertEqual(counts["module_not_found"], 2)
        self.assertEqual(counts["import_error"], 1)

    def test_extracts_repeated_fix_patterns(self) -> None:
        self._add_session(summary="Check venv")
        self._add_session(summary="Check venv")

        payload = debug_learning_summary.build_debug_learning_summary()

        self.assertTrue(any(item.get("type") == "fix_plan_summary" for item in payload["repeated_fix_patterns"]))
        self.assertTrue(any(item.get("type") == "suggested_command" and item.get("suggestion_only") for item in payload["repeated_fix_patterns"]))

    def test_prevention_suggestions_generated(self) -> None:
        self._add_session(["port_in_use"])
        self._add_session(["permission_denied"])

        payload = debug_learning_summary.build_debug_learning_summary()

        self.assertTrue(payload["prevention_suggestions"])

    def test_no_sessions_returns_safe_fallback(self) -> None:
        payload = debug_learning_summary.build_debug_learning_summary()
        text = debug_learning_summary.summarize_debug_learning(payload)

        self.assertEqual(payload["total_sessions_analyzed"], 0)
        self.assertIn("No debug sessions", text)

    def test_command_router_command_works(self) -> None:
        self._add_session()
        spoken = []

        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)):
            command_router.process_command("debug learning summary", {}, input_mode="text")

        self.assertIn("Analyzed", spoken[-1])

    def test_api_protected(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.160", 50000))

        response = remote_client.get("/api/debug/learning-summary")

        self.assertEqual(response.status_code, 403)

    def test_api_allows_localhost(self) -> None:
        self._add_session()

        response = self.client.get("/api/debug/learning-summary")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["no_command_executed"])

    def test_no_command_executed_true(self) -> None:
        self._add_session()

        payload = debug_learning_summary.build_debug_learning_summary()

        self.assertTrue(payload["no_command_executed"])

    def test_redaction_works(self) -> None:
        self._add_session(summary="password: swordfish", command="python -m pip show yaml")
        self._add_session(summary="password: swordfish", command="python -m pip show yaml")

        payload = debug_learning_summary.build_debug_learning_summary()
        text = str(payload)

        self.assertIn("[REDACTED]", text)
        self.assertNotIn("swordfish", text)


if __name__ == "__main__":
    unittest.main()
