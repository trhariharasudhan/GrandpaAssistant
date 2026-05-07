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

import context_action_executor
from api import web_api
from core import command_router


class ContextActionExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.patches = [
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
        ]
        for item in self.patches:
            item.start()
        command_router._remember_context_suggestion(None)
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        command_router._remember_context_suggestion(None)
        for item in reversed(self.patches):
            item.stop()

    def _screen_payload(self, text="Traceback error: missing module", has_error=True):
        return {
            "ok": True,
            "warning": False,
            "text": text,
            "lines": text.splitlines(),
            "error_detection": {"has_error_like_text": has_error, "lines": [text] if has_error else []},
        }

    def test_debug_error_explains_mocked_screen_error(self) -> None:
        with patch.object(context_action_executor, "summarize_screen_context", return_value=self._screen_payload()):
            result = context_action_executor.execute_suggested_action({"action": "debug_error"}, user_confirmation=True)

        self.assertTrue(result["executed"])
        self.assertTrue(result["read_only"])
        self.assertIn("error", result["message"].lower())

    def test_terminal_troubleshooting_explains_mocked_terminal_text(self) -> None:
        with patch.object(context_action_executor, "summarize_screen_context", return_value=self._screen_payload("npm failed with error")):
            result = context_action_executor.execute_suggested_action({"action": "troubleshoot_terminal"}, user_confirmation=True)

        self.assertTrue(result["executed"])
        self.assertEqual(result["action"], "troubleshoot_terminal")
        self.assertIn("terminal", result["message"].lower())

    def test_summarize_page_summarizes_mocked_screen_text(self) -> None:
        payload = self._screen_payload("GrandpaAssistant docs\nBackend validation passed", has_error=False)
        with patch.object(context_action_executor, "summarize_screen_context", return_value=payload):
            result = context_action_executor.execute_suggested_action({"action": "summarize_page"}, user_confirmation=True)

        self.assertTrue(result["executed"])
        self.assertIn("GrandpaAssistant docs", result["message"])

    def test_file_help_does_not_modify_files_and_asks_clarifying_question(self) -> None:
        result = context_action_executor.execute_suggested_action({"action": "file_help"}, user_confirmation=True)

        self.assertTrue(result["executed"])
        self.assertTrue(result["read_only"])
        self.assertIn("Do you want", result["message"])

    def test_do_it_without_latest_suggestion_gives_safe_fallback(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=spoken.append):
            command_router.process_command("do it", {}, input_mode="text")

        self.assertIn("Ask me for a context suggestion first", spoken[-1])

    def test_do_it_after_suggestion_executes_safe_read_only_action(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=spoken.append), \
            patch.object(command_router, "build_context_suggestions", return_value={"action": "summarize_page", "suggestion": "Summarize screen."}), \
            patch.object(command_router, "execute_suggested_action", return_value={"message": "Here is a summary.", "executed": True}) as execute:
            command_router.process_command("suggest next action", {}, input_mode="text")
            command_router.process_command("do it", {}, input_mode="text")

        execute.assert_called_once()
        self.assertEqual(spoken[-1], "Here is a summary.")

    def test_execute_suggestion_api_allows_localhost(self) -> None:
        with patch.object(web_api, "execute_suggested_action", return_value={"ok": True, "executed": True, "message": "Done"}):
            response = self.client.post("/api/context/execute-suggestion", json={"action_payload": {"action": "file_help"}})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["executed"])

    def test_execute_suggestion_api_blocks_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.60", 50000))

        response = remote_client.post("/api/context/execute-suggestion", json={"action_payload": {"action": "file_help"}})

        self.assertEqual(response.status_code, 403)

    def test_execute_suggestion_api_allows_remote_admin(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.60", 50000))
        admin_context = {"user": {"id": 1, "username": "admin", "role": "admin"}}

        with patch.object(web_api, "authenticate_app_token", return_value=admin_context), \
            patch.object(web_api, "execute_suggested_action", return_value={"ok": True, "executed": True, "message": "Done"}):
            response = remote_client.post(
                "/api/context/execute-suggestion",
                headers={"Authorization": "Bearer admin-token"},
                json={"action_payload": {"action": "file_help"}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["executed"])

    def test_destructive_or_risky_action_is_rejected(self) -> None:
        result = context_action_executor.execute_suggested_action({"action": "delete_files"}, user_confirmation=True)

        self.assertFalse(result["executed"])
        self.assertTrue(result["requires_confirmation"])
        self.assertIn("not a safe read-only", result["message"])


if __name__ == "__main__":
    unittest.main()
