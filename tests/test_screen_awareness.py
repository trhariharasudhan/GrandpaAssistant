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
from api import web_api
from core import command_router


class ScreenAwarenessTests(unittest.TestCase):
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

    def test_mocked_ocr_text_summarization_works(self) -> None:
        text = "Settings\nNetwork connected\nSave changes"
        with patch.object(screen_awareness.screen_reader, "read_screen_text", return_value=text):
            payload = screen_awareness.summarize_screen_context(language="en")

        self.assertTrue(payload["ok"])
        self.assertIn("Network connected", payload["summary"])
        self.assertFalse(payload["error_detection"]["has_error_like_text"])

    def test_error_like_text_detection_works(self) -> None:
        result = screen_awareness.detect_error_like_text("Traceback\nPermission denied error")

        self.assertTrue(result["has_error_like_text"])
        self.assertTrue(result["lines"])

    def test_missing_dependency_returns_safe_warning(self) -> None:
        with patch.object(screen_awareness.screen_reader, "read_screen_text", return_value=screen_awareness.OCR_UNAVAILABLE_MESSAGE):
            payload = screen_awareness.summarize_screen_context(language="en")

        self.assertFalse(payload["ok"])
        self.assertTrue(payload["warning"])
        self.assertIn("OCR", payload["detail"])

    def test_command_router_handles_screen_command(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=spoken.append), \
            patch.object(command_router, "explain_screen", return_value="I can read this on the screen: Hello"):
            command_router.process_command("explain my screen", {}, input_mode="text")

        self.assertEqual(spoken[-1], "I can read this on the screen: Hello")

    def test_tamil_command_requests_tamil_response(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=spoken.append), \
            patch.object(command_router, "explain_screen", return_value="திரையில் உரை தெரிகிறது.") as explain:
            command_router.process_command("screen la enna iruku", {}, input_mode="text")

        explain.assert_called_with(language="ta")
        self.assertIn("திரையில்", spoken[-1])

    def test_screen_summary_api_allows_localhost(self) -> None:
        with patch.object(web_api, "summarize_screen_context", return_value={"ok": True, "summary": "Screen text", "checks": []}):
            response = self.client.get("/api/screen/summary")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_screen_summary_api_blocks_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.30", 50000))

        response = remote_client.get("/api/screen/summary")

        self.assertEqual(response.status_code, 403)

    def test_screen_summary_api_allows_remote_admin(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.30", 50000))
        admin_context = {"user": {"id": 1, "username": "admin", "role": "admin"}}

        with patch.object(web_api, "authenticate_app_token", return_value=admin_context), \
            patch.object(web_api, "summarize_screen_context", return_value={"ok": True, "summary": "Screen text"}):
            response = remote_client.get("/api/screen/summary", headers={"Authorization": "Bearer admin-token"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])


if __name__ == "__main__":
    unittest.main()
