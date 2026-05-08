import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import call_control
from core import command_router
from security.permission_engine import classify_command


class CallControlTests(unittest.TestCase):
    def setUp(self) -> None:
        command_router.pending_confirmation = None

    def test_call_number_detected_as_call_intent(self) -> None:
        result = call_control.detect_call_intent("call 9876543210")

        self.assertTrue(result["is_call"])
        self.assertEqual(result["target_text"], "9876543210")

    def test_tamil_style_call_detected_as_call_intent(self) -> None:
        result = call_control.detect_call_intent("riyaa ku call pannu")

        self.assertTrue(result["is_call"])
        self.assertEqual(result["target_text"], "riyaa")

    def test_clear_number_call_does_not_ask_extra_confirmation(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)), \
            patch.object(command_router, "initiate_call", return_value={"ok": True, "message": "Starting call flow for that number."}) as initiate:
            command_router.process_command("call 9876543210", {}, input_mode="text")

        initiate.assert_called_once()
        self.assertIn("Starting call flow", spoken[-1])
        self.assertIsNone(command_router.pending_confirmation)

    def test_missing_call_target_asks_clarification(self) -> None:
        result = call_control.initiate_call("")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "missing_target")
        self.assertIn("Who should I call", result["message"])

    def test_ambiguous_contact_asks_clarification(self) -> None:
        with patch("call_control._resolve_contact_phone", return_value={
            "ok": False,
            "status": "ambiguous",
            "message": "I found multiple Google contacts for riyaa: Riyaa A, Riyaa B. Say the exact name.",
        }):
            result = call_control.resolve_call_target("riyaa")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "ambiguous")
        self.assertIn("multiple", result["message"].lower())

    def test_emergency_numbers_are_blocked(self) -> None:
        result = call_control.initiate_call("112")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "emergency_blocked")
        self.assertIn("manually", result["message"].lower())

    def test_provider_unavailable_returns_setup_instruction(self) -> None:
        with patch.object(call_control.webbrowser, "open", return_value=False):
            result = call_control.initiate_call("9876543210")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "provider_unavailable")
        self.assertIn("Phone Link", result["message"])

    def test_risky_actions_still_require_confirmation(self) -> None:
        decision = classify_command("shutdown system")

        self.assertTrue(decision["requires_confirmation"])
        self.assertTrue(decision["requires_authentication"])


if __name__ == "__main__":
    unittest.main()
