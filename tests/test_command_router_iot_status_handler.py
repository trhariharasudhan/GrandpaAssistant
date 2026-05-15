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
from core.commands.handlers.iot_status import handle_iot_status_command
from tests.test_command_router_contacts_handler import _context


class CommandRouterIotStatusHandlerTests(unittest.TestCase):
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

    def test_smart_home_status_behavior(self) -> None:
        self._run_router("smart home status", extra_patches=[patch.object(command_router, "_smart_home_status_summary", return_value="Smart Home status.")])

        self.assertEqual("Smart Home status.", self.spoken[-1])

    def test_iot_device_status_summary_behavior(self) -> None:
        self._run_router("iot inventory", extra_patches=[patch.object(command_router, "_iot_awareness_summary", return_value="IoT inventory.")])

        self.assertEqual("IoT inventory.", self.spoken[-1])

    def test_iot_history_summary_behavior(self) -> None:
        self._run_router("iot action history", extra_patches=[patch.object(command_router, "_iot_action_history_summary", return_value="IoT history.")])

        self.assertEqual("IoT history.", self.spoken[-1])

    def test_setup_readiness_help_behavior(self) -> None:
        self._run_router("smart home setup help", extra_patches=[patch.object(command_router, "_smart_home_setup_summary", return_value="Smart Home setup help.")])

        self.assertEqual("Smart Home setup help.", self.spoken[-1])

    def test_unknown_iot_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "iot banana mode",
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

    def test_control_config_and_live_validation_commands_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "turn on living room light",
            "turn off fan",
            "switch on bedroom lamp",
            "run iot command fan",
            "pair smart bulb",
            "connect iot device",
            "iot validate",
            "validate smart home config",
            "update iot config",
            "delete smart home device",
            "refresh smart home devices",
            "scan iot devices",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_iot_status_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
