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
from core.commands.handlers.system_health import handle_system_health_command
from tests.test_command_router_contacts_handler import _context


class CommandRouterSystemHealthHandlerTests(unittest.TestCase):
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

    def test_system_health_summary_behavior(self) -> None:
        self._run_router("system status", extra_patches=[patch.object(command_router, "get_system_status", return_value="System status.")])

        self.assertEqual("System status.", self.spoken[-1])

    def test_battery_status_behavior(self) -> None:
        self._run_router("battery status", extra_patches=[patch.object(command_router, "get_battery_status", return_value="Battery status.")])

        self.assertEqual("Battery status.", self.spoken[-1])

    def test_performance_report_behavior(self) -> None:
        self._run_router("cpu usage", extra_patches=[patch.object(command_router, "get_cpu_status", return_value="CPU status.")])
        self._run_router("ram status", extra_patches=[patch.object(command_router, "get_ram_status", return_value="RAM status.")])
        self._run_router("disk status", extra_patches=[patch.object(command_router, "get_disk_status", return_value="Disk status.")])

        self.assertEqual("CPU status.", self.spoken[-3])
        self.assertEqual("RAM status.", self.spoken[-2])
        self.assertEqual("Disk status.", self.spoken[-1])

    def test_device_hardware_summary_behavior(self) -> None:
        self._run_router("hardware status", extra_patches=[patch.object(command_router, "_hardware_status_summary", return_value="Hardware status.")])
        self._run_router("hardware events", extra_patches=[patch.object(command_router, "_hardware_event_history_summary", return_value="Hardware events.")])

        self.assertEqual("Hardware status.", self.spoken[-2])
        self.assertEqual("Hardware events.", self.spoken[-1])

    def test_unknown_system_health_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "system health banana mode",
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

    def test_mutation_system_action_and_hardware_action_commands_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "cleanup files",
            "delete temp files",
            "change startup settings",
            "shutdown",
            "restart",
            "sleep",
            "open notepad",
            "close chrome",
            "run diagnostics command",
            "scan hardware",
            "rescan devices",
            "refresh hardware",
            "take screenshot",
            "read screen",
            "turn on battery saver",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_system_health_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
