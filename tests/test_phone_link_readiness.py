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

import phone_link_readiness
from api import web_api
from core import command_router


class PhoneLinkReadinessTests(unittest.TestCase):
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

    def test_safe_tel_uri_preview_redacts_number(self) -> None:
        preview = phone_link_readiness.safe_tel_uri_preview("9876543210")

        self.assertEqual(preview, "tel:******3210")

    def test_phone_link_status_never_places_call(self) -> None:
        with patch.object(phone_link_readiness, "os") as os_mock:
            os_mock.name = "posix"
            payload = phone_link_readiness.check_tel_handler_readiness()

        self.assertEqual(payload["status"], "warning")
        self.assertIn("Set up Windows Phone Link", payload["message"])

    def test_command_router_phone_link_status_works(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)), \
            patch.object(command_router, "check_tel_handler_readiness", return_value={"tel_handler_configured": False, "message": "Set up Windows Phone Link or choose a default app for tel: links."}):
            command_router.process_command("phone link status", {}, input_mode="text")

        self.assertIn("Set up Windows Phone Link", spoken[-1])

    def test_api_protected(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.170", 50000))

        response = remote_client.get("/api/phone-link/status")

        self.assertEqual(response.status_code, 403)

    def test_localhost_api_returns_status(self) -> None:
        with patch.object(web_api, "check_tel_handler_readiness", return_value={"ok": True, "status": "ok", "tel_handler_configured": True}):
            response = self.client.get("/api/phone-link/status")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["tel_handler_configured"])


if __name__ == "__main__":
    unittest.main()
