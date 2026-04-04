import json
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import iot_control
import iot_registry


class IoTControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.creds_path = os.path.join(self.temp_dir.name, "iot_credentials.json")
        self.history_path = os.path.join(self.temp_dir.name, "iot_action_history.json")
        with open(self.creds_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "enabled": True,
                    "webhooks": {
                        "turn on bedroom light": {
                            "url": "http://localhost/device/light/on",
                            "method": "POST",
                            "success_message": "Bedroom light turned on.",
                        },
                        "unlock front door": {
                            "url": "http://localhost/device/door/unlock",
                            "method": "POST",
                            "success_message": "Front door unlocked.",
                        },
                    },
                },
                file,
                indent=2,
            )

        self.path_patch = patch.object(iot_registry, "IOT_CREDENTIALS_PATH", self.creds_path)
        self.history_patch = patch.object(iot_control, "IOT_ACTION_HISTORY_PATH", self.history_path)
        self.setting_patch = patch.object(iot_control, "get_setting", side_effect=self._fake_setting)
        self.path_patch.start()
        self.history_patch.start()
        self.setting_patch.start()

    def tearDown(self) -> None:
        self.path_patch.stop()
        self.history_patch.stop()
        self.setting_patch.stop()
        self.temp_dir.cleanup()

    def _fake_setting(self, key, default=None):
        values = {
            "iot.confirmation_mode": "risky_only",
            "iot.allow_fuzzy_command_matching": True,
            "iot.action_history_limit": 20,
        }
        return values.get(key, default)

    def test_fuzzy_resolution_matches_configured_command(self) -> None:
        result = iot_control.resolve_iot_control_command("please switch on my bedroom light")
        self.assertTrue(result["handled"])
        self.assertTrue(result["matched"])
        self.assertEqual(result["matched_command"], "turn on bedroom light")
        self.assertEqual(result["match_type"], "fuzzy")

    def test_risky_action_requires_confirmation(self) -> None:
        result = iot_control.execute_iot_control("unlock front door", confirm=False)
        self.assertFalse(result["ok"])
        self.assertFalse(result["executed"])
        self.assertTrue(result["requires_confirmation"])
        self.assertIn("confirm", result["message"].lower())

    def test_successful_webhook_execution_is_logged(self) -> None:
        response = Mock(status_code=200)
        with patch.object(iot_control.requests, "request", return_value=response) as mock_request:
            result = iot_control.execute_iot_control("turn on bedroom light", confirm=False)

        self.assertTrue(result["ok"])
        self.assertTrue(result["executed"])
        self.assertEqual(result["message"], "Bedroom light turned on.")
        mock_request.assert_called_once()

        history = iot_control.get_iot_action_history(limit=5)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["matched_command"], "turn on bedroom light")
        self.assertTrue(history[0]["ok"])


if __name__ == "__main__":
    unittest.main()
