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
from core.commands.handlers.overlay_status import handle_overlay_status_command
from core.commands.summaries import overlay as overlay_summaries
from tests.test_command_router_contacts_handler import _context


class CommandRouterOverlayStatusHandlerTests(unittest.TestCase):
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

    def test_overlay_and_quick_overlay_status_behavior(self) -> None:
        self._run_router("overlay status", extra_patches=[patch.object(overlay_summaries, "overlay_status_summary", return_value="Overlay status.")])
        self._run_router("quick overlay status", extra_patches=[patch.object(overlay_summaries, "quick_overlay_status_summary", return_value="Quick overlay status.")])

        self.assertEqual("Overlay status.", self.spoken[-2])
        self.assertEqual("Quick overlay status.", self.spoken[-1])

    def test_pinned_commands_hotkey_and_help_behavior(self) -> None:
        self._run_router("list pinned commands", extra_patches=[patch.object(overlay_summaries, "pinned_commands_summary", return_value="Pinned commands.")])
        self._run_router("hotkey status", extra_patches=[patch.object(overlay_summaries, "hotkey_status_summary", return_value="Hotkey status.")])
        self._run_router("overlay help", extra_patches=[patch.object(overlay_summaries, "overlay_help_summary", return_value="Overlay help.")])

        self.assertEqual("Pinned commands.", self.spoken[-3])
        self.assertEqual("Hotkey status.", self.spoken[-2])
        self.assertEqual("Overlay help.", self.spoken[-1])

    def test_unknown_overlay_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "overlay banana mode",
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

    def test_overlay_actions_and_hotkey_mutations_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "pin command hello",
            "unpin command hello",
            "move pinned command hello up",
            "enable quick overlay",
            "disable quick overlay",
            "toggle quick overlay",
            "set overlay hotkey to ctrl alt space",
            "change ocr hotkey to ctrl shift o",
            "open quick overlay",
            "close quick overlay",
            "hide quick overlay",
            "show quick overlay",
            "click button",
            "type hello",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_overlay_status_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
