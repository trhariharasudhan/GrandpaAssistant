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

import context_suggestions
from api import web_api
from core import command_router


class ContextSuggestionsTests(unittest.TestCase):
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

    def _screen(self, has_error=False):
        return {
            "ok": True,
            "warning": False,
            "summary": "Traceback error" if has_error else "Readable page text",
            "error_detection": {"has_error_like_text": has_error, "lines": ["Traceback error"] if has_error else []},
        }

    def _window(self, kind, app_name="App", title="Window"):
        return {
            "ok": True,
            "summary": title,
            "active_window": {
                "ok": True,
                "kind": kind,
                "app_name": app_name,
                "title": title,
            },
        }

    def test_editor_error_suggests_debug_or_explain_error(self) -> None:
        payload = context_suggestions.suggestion_from_screen_and_window(
            self._screen(has_error=True),
            self._window("editor", "Visual Studio Code", "main.py - VS Code"),
            language="en",
        )

        self.assertEqual(payload["action"], "debug_error")
        self.assertIn("debug", payload["suggestion"].lower())
        self.assertTrue(payload["no_action_executed"])

    def test_terminal_error_suggests_troubleshooting(self) -> None:
        payload = context_suggestions.suggestion_from_screen_and_window(
            self._screen(has_error=True),
            self._window("terminal", "Windows Terminal", "PowerShell"),
            language="en",
        )

        self.assertEqual(payload["action"], "troubleshoot_terminal")
        self.assertIn("troubleshoot", payload["suggestion"].lower())

    def test_browser_suggests_summarize(self) -> None:
        payload = context_suggestions.suggestion_from_screen_and_window(
            self._screen(),
            self._window("browser", "Google Chrome", "Example - Chrome"),
            language="en",
        )

        self.assertEqual(payload["action"], "summarize_page")
        self.assertIn("summarize", payload["suggestion"].lower())

    def test_file_explorer_suggests_file_help(self) -> None:
        payload = context_suggestions.suggestion_from_screen_and_window(
            self._screen(),
            self._window("file_explorer", "File Explorer", "Downloads"),
            language="en",
        )

        self.assertEqual(payload["action"], "file_help")
        self.assertIn("files", payload["suggestion"].lower())

    def test_no_useful_context_returns_safe_fallback(self) -> None:
        payload = context_suggestions.suggestion_from_screen_and_window(
            {"ok": False, "warning": True},
            {"ok": False, "warning": True},
            language="en",
        )

        self.assertEqual(payload["action"], "no_strong_suggestion")
        self.assertIn("No strong suggestion", payload["suggestion"])

    def test_tamil_command_returns_tamil_friendly_output(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=spoken.append), \
            patch.object(command_router, "summarize_context_suggestions", return_value="Ippo error explain pannalaam.") as summary:
            command_router.process_command("enna next pannalam", {}, input_mode="text")

        summary.assert_called_with(language="ta")
        self.assertIn("pannalaam", spoken[-1])

    def test_command_router_handles_suggestion_commands(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=spoken.append), \
            patch.object(command_router, "summarize_context_suggestions", return_value="I can summarize this page."):
            command_router.process_command("suggest next action", {}, input_mode="text")

        self.assertEqual(spoken[-1], "I can summarize this page.")

    def test_context_suggestions_api_allows_localhost(self) -> None:
        with patch.object(web_api, "build_context_suggestions", return_value={"ok": True, "suggestion": "Next action"}):
            response = self.client.get("/api/context/suggestions")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_context_suggestions_api_blocks_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.50", 50000))

        response = remote_client.get("/api/context/suggestions")

        self.assertEqual(response.status_code, 403)

    def test_context_suggestions_api_allows_remote_admin(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.50", 50000))
        admin_context = {"user": {"id": 1, "username": "admin", "role": "admin"}}

        with patch.object(web_api, "authenticate_app_token", return_value=admin_context), \
            patch.object(web_api, "build_context_suggestions", return_value={"ok": True, "suggestion": "Next action"}):
            response = remote_client.get("/api/context/suggestions", headers={"Authorization": "Bearer admin-token"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])


if __name__ == "__main__":
    unittest.main()
