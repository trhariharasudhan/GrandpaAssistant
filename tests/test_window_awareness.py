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

import screen_awareness
import window_awareness
from api import web_api
from core import command_router


class WindowAwarenessTests(unittest.TestCase):
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

    def _window_info(self, title="main.py - GrandpaAssistant - Visual Studio Code", app_name="Visual Studio Code"):
        return {"title": title, "app_name": app_name, "app_key": app_name.lower()}

    def test_mocked_active_window_returns_summary(self) -> None:
        with patch.object(window_awareness.window_context_module, "get_active_window_info", return_value=self._window_info()):
            payload = window_awareness.summarize_active_window(language="en")

        self.assertTrue(payload["ok"])
        self.assertIn("Visual Studio Code", payload["summary"])
        self.assertEqual(payload["active_window"]["kind"], "editor")

    def test_browser_editor_terminal_detection_works(self) -> None:
        browser = {"ok": True, "title": "Example - Google Chrome", "app_name": "Google Chrome", "process_name": "chrome.exe", "kind": "browser"}
        editor = {"ok": True, "title": "app.py - Visual Studio Code", "app_name": "Visual Studio Code", "process_name": "Code.exe", "kind": "editor"}
        terminal = {"ok": True, "title": "PowerShell", "app_name": "Windows Terminal", "process_name": "pwsh.exe", "kind": "terminal"}

        self.assertTrue(window_awareness.detect_browser_context(browser)["matched"])
        self.assertTrue(window_awareness.detect_editor_context(editor)["matched"])
        self.assertTrue(window_awareness.detect_terminal_context(terminal)["matched"])

    def test_missing_dependency_returns_safe_warning(self) -> None:
        with patch.object(window_awareness, "window_context_module", None):
            payload = window_awareness.summarize_active_window(language="en")

        self.assertFalse(payload["ok"])
        self.assertTrue(payload["warning"])
        self.assertIn("cannot detect", payload["message"].lower())

    def test_command_router_handles_window_commands(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=spoken.append), \
            patch.object(command_router, "summarize_active_window", return_value={"summary": "You are using VS Code."}):
            command_router.process_command("what app am i using", {}, input_mode="text")

        self.assertEqual(spoken[-1], "You are using VS Code.")

    def test_tamil_window_command_requests_tamil(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=spoken.append), \
            patch.object(command_router, "summarize_active_window", return_value={"summary": "நீங்கள் VS Code பயன்படுத்துகிறீர்கள்."}) as summary:
            command_router.process_command("naan enna app use panren", {}, input_mode="text")

        summary.assert_called_with(language="ta")
        self.assertIn("நீங்கள்", spoken[-1])

    def test_window_context_api_allows_localhost(self) -> None:
        with patch.object(web_api, "summarize_active_window", return_value={"ok": True, "summary": "Window"}):
            response = self.client.get("/api/window/context")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_window_context_api_blocks_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.40", 50000))

        response = remote_client.get("/api/window/context")

        self.assertEqual(response.status_code, 403)

    def test_window_context_api_allows_remote_admin(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.40", 50000))
        admin_context = {"user": {"id": 1, "username": "admin", "role": "admin"}}

        with patch.object(web_api, "authenticate_app_token", return_value=admin_context), \
            patch.object(web_api, "summarize_active_window", return_value={"ok": True, "summary": "Window"}):
            response = remote_client.get("/api/window/context", headers={"Authorization": "Bearer admin-token"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_screen_summary_includes_active_window_when_available(self) -> None:
        window_payload = {"ok": True, "title": "main.py - VS Code", "app_name": "VS Code", "kind": "editor"}
        with patch.object(screen_awareness.screen_reader, "read_screen_text", return_value="Hello screen"), \
            patch.object(screen_awareness, "safe_window_context_payload", return_value=window_payload):
            payload = screen_awareness.summarize_screen_context(language="en")

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["active_window"]["kind"], "editor")


if __name__ == "__main__":
    unittest.main()
