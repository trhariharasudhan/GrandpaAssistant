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

from core import command_router


class CommandRouterConfirmationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_pending = command_router.pending_confirmation
        self.original_pending_map = dict(command_router.pending_confirmations)
        command_router.pending_confirmation = None
        command_router.pending_confirmations.clear()
        self.spoken = []
        self.resumed = []

    def tearDown(self) -> None:
        command_router.pending_confirmation = self.original_pending
        command_router.pending_confirmations.clear()
        command_router.pending_confirmations.update(self.original_pending_map)

    def _security_decision(self, command, **_kwargs):
        if command.startswith("delete file"):
            return {
                "allowed": False,
                "action": "confirm",
                "message": f"Please confirm this medium risk command: {command}",
                "permission": {"requires_admin_mode": False},
            }
        return {"allowed": True, "action": "allow", "message": ""}

    def test_multiple_pending_actions_can_be_dismissed_independently(self) -> None:
        with patch.object(command_router, "speak", side_effect=self.spoken.append), \
            patch.object(command_router, "validate_command", side_effect=self._security_decision), \
            patch.object(command_router, "log_command", lambda *args, **kwargs: None), \
            patch.object(command_router, "remember_emotion_signal", lambda *args, **kwargs: None):
            command_router.process_command("delete file alpha", {}, input_mode="text")
            command_router.process_command("delete file beta", {}, input_mode="text")

            ids = list(command_router.pending_confirmations.keys())
            self.assertEqual(len(ids), 2)
            command_router.process_command(f"dismiss {ids[0]}", {}, input_mode="text")

        self.assertNotIn(ids[0], command_router.pending_confirmations)
        self.assertIn(ids[1], command_router.pending_confirmations)
        self.assertEqual(self.spoken[-1], "Cancelled.")

    def test_pending_action_can_be_allowed_by_id(self) -> None:
        with patch.object(command_router, "speak", side_effect=self.spoken.append), \
            patch.object(command_router, "validate_command", side_effect=self._security_decision), \
            patch.object(command_router, "log_command", lambda *args, **kwargs: None), \
            patch.object(command_router, "remember_emotion_signal", lambda *args, **kwargs: None), \
            patch.object(command_router, "_resume_secured_command", lambda state, *_args: self.resumed.append(state["command"])):
            command_router.process_command("delete file alpha", {}, input_mode="text")
            confirmation_id = next(iter(command_router.pending_confirmations.keys()))
            command_router.process_command(f"allow {confirmation_id}", {}, input_mode="text")

        self.assertEqual(self.resumed, ["delete file alpha"])
        self.assertNotIn(confirmation_id, command_router.pending_confirmations)

    def test_general_ai_response_is_not_allowed_to_echo_question(self) -> None:
        with patch.object(command_router, "speak", lambda text, *args, **kwargs: self.spoken.append(text)), \
            patch.object(command_router, "validate_command", return_value={"allowed": True}), \
            patch.object(command_router, "log_command", lambda *args, **kwargs: None), \
            patch.object(command_router, "remember_emotion_signal", lambda *args, **kwargs: None), \
            patch.object(command_router, "try_handle_intent", return_value={"handled": False, "reply": ""}), \
            patch.object(command_router, "is_personal_question", return_value=False), \
            patch.object(command_router, "ask_ollama", return_value="describe python briefly"):
            command_router.process_command("describe python briefly", {}, input_mode="voice")

        self.assertNotEqual(self.spoken[-1].lower(), "describe python briefly")


if __name__ == "__main__":
    unittest.main()
