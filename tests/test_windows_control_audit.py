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

import windows_control_audit
from api import web_api
from core import command_router


class WindowsControlAuditTests(unittest.TestCase):
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

    def test_audit_returns_categories_and_key_controls(self) -> None:
        payload = windows_control_audit.build_windows_control_audit()

        self.assertTrue(payload["categories"])
        keys = {item["capability_key"] for item in payload["items"]}
        self.assertIn("open_app", keys)
        self.assertIn("call_contact_number", keys)
        self.assertIn("debug_dashboard", keys)

    def test_audit_does_not_execute_destructive_actions(self) -> None:
        payload = windows_control_audit.build_windows_control_audit()

        self.assertTrue(payload["no_destructive_action"])
        power = next(item for item in payload["items"] if item["capability_key"] == "power_lock_safety")
        self.assertEqual(power["safety_level"], "confirmation_required")

    def test_api_route_is_protected(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.170", 50000))

        response = remote_client.get("/api/windows/controls/audit")

        self.assertEqual(response.status_code, 403)

    def test_localhost_api_returns_audit(self) -> None:
        response = self.client.get("/api/windows/controls/audit")

        self.assertEqual(response.status_code, 200)
        self.assertIn("items", response.json())

    def test_command_router_audit_command_works(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)), \
            patch.object(command_router, "build_windows_control_audit", return_value={
                "implemented_count": 2,
                "total_count": 2,
                "warnings": [],
                "language": "auto",
            }):
            command_router.process_command("windows controls audit", {}, input_mode="text")

        self.assertIn("Windows controls audit", spoken[-1])


if __name__ == "__main__":
    unittest.main()
