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

import debug_knowledge_reuse
import debug_session
from api import web_api
from core import command_router


class DebugKnowledgeReuseTests(unittest.TestCase):
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

    def _add_session(self, title="Old module issue", current=False):
        session = debug_session.start_debug_session(title=title, source="test")
        raw = debug_session._CURRENT_DEBUG_SESSION
        raw["updated_at"] = "2026-05-08T01:00:00Z"
        raw["debug_reports"].append({
            "summary": "ModuleNotFoundError for yaml",
            "error_text": "ModuleNotFoundError: No module named yaml",
            "error_families": ["module_not_found"],
        })
        raw["fix_plans"].append({
            "summary": "Check venv and install yaml only after approval.",
            "suggested_commands": [{"command": "python -m pip show yaml", "reason": "Check package"}],
        })
        debug_session._write_snapshot(raw)
        if not current:
            debug_session.close_debug_session(status="closed")
        return session["id"]

    def test_similar_session_found_by_error_family(self) -> None:
        session_id = self._add_session()

        payload = debug_knowledge_reuse.find_similar_debug_sessions(
            report={"error_families": ["module_not_found"], "summary": "No module named yaml"}
        )

        self.assertEqual(payload["similar_sessions"][0]["session_id"], session_id)

    def test_previous_fix_plan_snippet_returned(self) -> None:
        self._add_session()

        payload = debug_knowledge_reuse.build_reuse_suggestions(
            report={"error_families": ["module_not_found"], "summary": "yaml missing"}
        )

        self.assertTrue(payload["previous_fix_plan_snippets"])
        self.assertIn("venv", payload["previous_fix_plan_snippets"][0])

    def test_previous_command_suggestions_returned_as_suggestion_only(self) -> None:
        self._add_session()

        payload = debug_knowledge_reuse.build_reuse_suggestions(
            report={"error_families": ["module_not_found"], "summary": "yaml missing"}
        )

        command = payload["previous_commands_suggested"][0]
        self.assertEqual(command["command"], "python -m pip show yaml")
        self.assertTrue(command["suggestion_only"])

    def test_current_session_excluded_if_possible(self) -> None:
        current_id = self._add_session(title="Current issue", current=True)

        payload = debug_knowledge_reuse.find_similar_debug_sessions(
            report={"error_families": ["module_not_found"], "summary": "yaml missing"}
        )

        self.assertNotIn(current_id, [item["session_id"] for item in payload["similar_sessions"]])

    def test_no_similar_session_returns_safe_fallback(self) -> None:
        payload = debug_knowledge_reuse.build_reuse_suggestions(report={"summary": "totally unique issue"})

        self.assertEqual(payload["similar_sessions"], [])
        self.assertIn("did not find", debug_knowledge_reuse.summarize_reuse_suggestions(payload))

    def test_command_router_works(self) -> None:
        self._add_session()
        spoken = []

        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)):
            command_router.process_command("seen this before", {}, input_mode="text")

        self.assertTrue(spoken)

    def test_api_protected(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.150", 50000))

        response = remote_client.get("/api/debug/reuse-suggestions")

        self.assertEqual(response.status_code, 403)

    def test_no_command_executed_flag_true(self) -> None:
        self._add_session()

        payload = debug_knowledge_reuse.build_reuse_suggestions(
            report={"error_families": ["module_not_found"], "summary": "yaml missing"}
        )

        self.assertTrue(payload["no_command_executed"])

    def test_redaction_works(self) -> None:
        debug_session.start_debug_session(title="Secret old issue", source="test")
        raw = debug_session._CURRENT_DEBUG_SESSION
        raw["debug_reports"].append({
            "summary": "password: swordfish",
            "error_text": "token=abc123 ModuleNotFoundError",
            "error_families": ["module_not_found"],
        })
        raw["fix_plans"].append({"summary": "password: swordfish"})
        debug_session._write_snapshot(raw)
        debug_session.close_debug_session(status="closed")

        payload = debug_knowledge_reuse.build_reuse_suggestions(report={"summary": "password module_not_found"})
        text = str(payload)

        self.assertIn("[REDACTED]", text)
        self.assertNotIn("swordfish", text)


if __name__ == "__main__":
    unittest.main()
