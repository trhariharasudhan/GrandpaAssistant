import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
APP_DIR = BACKEND_DIR / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in [BACKEND_DIR, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from core import command_router
from core.commands.handlers.emergency_status import handle_emergency_status_command
from tests.test_command_router_contacts_handler import _context


class CommandRouterEmergencyStatusHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_pending = command_router.pending_confirmation
        self.original_pending_map = dict(command_router.pending_confirmations)
        command_router.pending_confirmation = None
        command_router.pending_confirmations.clear()
        self.spoken: list[str] = []

    def tearDown(self) -> None:
        command_router.pending_confirmation = self.original_pending
        command_router.pending_confirmations.clear()
        command_router.pending_confirmations.update(self.original_pending_map)

    def _run_router(self, command: str, extra_patches: list | None = None) -> None:
        patches = [
            patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: self.spoken.append(str(message))),
            patch.object(command_router, "play_sound"),
            patch.object(command_router, "log_command", lambda *args, **kwargs: None),
            patch.object(command_router, "remember_emotion_signal", lambda *args, **kwargs: None),
            patch.object(command_router, "set_last_user_input", lambda *args, **kwargs: None),
            patch.object(command_router, "set_last_result", lambda *args, **kwargs: None),
            patch.object(command_router, "validate_command", return_value={"allowed": True, "action": "allow", "message": ""}),
        ]
        patches.extend(extra_patches or [])
        try:
            for item in patches:
                item.start()
            command_router.process_command(command, {}, input_mode="voice")
        finally:
            for item in reversed(patches):
                item.stop()

    def test_emergency_status_behavior(self) -> None:
        self._run_router("emergency mode status", extra_patches=[patch.object(command_router, "_emergency_mode_status_summary", return_value="Emergency mode status.")])

        self.assertEqual("Emergency mode status.", self.spoken[-1])

    def test_emergency_help_readiness_behavior(self) -> None:
        self._run_router("emergency quick response", extra_patches=[patch.object(command_router, "_emergency_quick_response_summary", return_value="Emergency quick response.")])

        self.assertEqual("Emergency quick response.", self.spoken[-1])

    def test_emergency_protocol_information_behavior(self) -> None:
        self._run_router("emergency protocol status", extra_patches=[patch.object(command_router, "_emergency_protocol_summary", return_value="Emergency protocol.")])

        self.assertEqual("Emergency protocol.", self.spoken[-1])

    def test_unknown_emergency_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "emergency banana mode",
            extra_patches=[
                patch.object(command_router, "try_handle_intent", return_value={"handled": False, "reply": ""}),
                patch.object(command_router, "handle_calendar_queries", return_value=False),
                patch.object(command_router, "is_personal_question", return_value=False),
                patch.object(command_router, "ask_ollama", ask),
                patch.object(command_router, "_remember_terminal_learning_turn", lambda *args, **kwargs: None),
            ],
        )

        self.assertTrue(ask.called)
        self.assertEqual("Existing fallback reply.", self.spoken[-1])

    def test_trigger_send_call_location_and_lockdown_commands_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "start emergency protocol",
            "trigger emergency protocol",
            "send emergency alert",
            "emergency alert",
            "send sos",
            "send i am safe alert",
            "share my location",
            "share saved location",
            "send my location to emergency contact",
            "call emergency contact",
            "emergency call",
            "assistant lockdown",
            "security lockdown",
            "lock system",
            "enable emergency mode",
            "disable emergency mode",
            "clear emergency logs",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_emergency_status_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
