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

from api import web_api
import backend_stability


class BackendStabilityApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_confirmations = dict(web_api._pending_confirmations)
        web_api._pending_confirmations.clear()
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
        web_api._pending_confirmations.clear()
        web_api._pending_confirmations.update(self.original_confirmations)

    def test_backend_stability_route_returns_payload(self) -> None:
        response = self.client.get("/api/backend/stability")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("overall_ok", payload)
        self.assertIn("checks", payload)
        self.assertIn("warnings", payload)
        self.assertIn("timestamp", payload)
        self.assertIn("next_actions", payload)

    def test_optional_warning_states_do_not_fail_route(self) -> None:
        diagnostics = {
            "summary": "mock diagnostics",
            "items": [
                {"key": "voice_input", "status": "warning", "detail": "No microphone backend."},
                {"key": "ollama_api", "status": "error", "detail": "Ollama is offline."},
                {"key": "tesseract", "status": "warning", "detail": "OCR unavailable."},
                {"key": "camera_vision", "status": "error", "detail": "Camera unavailable."},
                {"key": "data_dir", "status": "ok", "detail": "Data path writable."},
                {"key": "log_dir", "status": "ok", "detail": "Log path writable."},
            ],
        }
        validation = {"overall_ok": True, "checked_at": "2026-05-07T00:00:00", "failed_sections": []}

        with patch.object(backend_stability, "collect_startup_diagnostics", return_value=diagnostics), \
            patch.object(backend_stability, "_load_last_backend_validation_status", return_value=validation):
            response = self.client.get("/api/backend/stability")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["overall_ok"])
        warning_keys = {item["key"] for item in payload["warnings"]}
        self.assertIn("ollama", warning_keys)
        self.assertIn("camera_vision", warning_keys)


if __name__ == "__main__":
    unittest.main()
