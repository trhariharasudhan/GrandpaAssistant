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
from core.commands.handlers.interface_status import handle_interface_status_command
from core.commands.summaries import interface as interface_summaries
from tests.test_command_router_contacts_handler import _context


class CommandRouterInterfaceStatusHandlerTests(unittest.TestCase):
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

    def test_startup_and_auto_launch_status_behavior(self) -> None:
        self._run_router("startup status", extra_patches=[patch.object(interface_summaries, "startup_status_summary", return_value="Startup status.")])
        self._run_router("auto launch status", extra_patches=[patch.object(command_router, "startup_auto_launch_status", return_value="Auto launch status.")])

        self.assertEqual("Startup status.", self.spoken[-2])
        self.assertEqual("Auto launch status.", self.spoken[-1])

    def test_tray_interface_and_desktop_backend_status_behavior(self) -> None:
        self._run_router("tray mode status", extra_patches=[patch.object(interface_summaries, "tray_mode_status_summary", return_value="Tray mode status.")])
        self._run_router("interface mode status", extra_patches=[patch.object(interface_summaries, "interface_mode_status_summary", return_value="Interface mode status.")])
        self._run_router("desktop backend mode", extra_patches=[patch.object(interface_summaries, "desktop_backend_mode_summary", return_value="Desktop backend mode.")])

        self.assertEqual("Tray mode status.", self.spoken[-3])
        self.assertEqual("Interface mode status.", self.spoken[-2])
        self.assertEqual("Desktop backend mode.", self.spoken[-1])

    def test_launcher_readiness_status_behavior(self) -> None:
        self._run_router(
            "launcher readiness status",
            extra_patches=[patch.object(interface_summaries, "launcher_readiness_status_summary", return_value="Launcher readiness.")],
        )

        self.assertEqual("Launcher readiness.", self.spoken[-1])

    def test_unknown_interface_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "startup banana mode",
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

    def test_startup_interface_mutations_and_launches_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "enable assistant startup",
            "disable assistant startup",
            "enable tray startup",
            "disable tray startup",
            "enable terminal mode",
            "enable ui mode",
            "set terminal input mode to voice",
            "open web ui",
            "open desktop ui",
            "open desktop shell",
            "open assistant window",
            "launch notepad",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_interface_status_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
