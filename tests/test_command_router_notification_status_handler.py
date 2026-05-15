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
from core.commands.handlers.notification_status import handle_notification_status_command
from core.commands.summaries import notification as notification_summaries
from tests.test_command_router_contacts_handler import _context


class CommandRouterNotificationStatusHandlerTests(unittest.TestCase):
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

    def test_notification_status_behavior(self) -> None:
        self._run_router(
            "notification status",
            extra_patches=[patch.object(notification_summaries, "notification_status_summary", return_value="Notification status.")],
        )

        self.assertEqual("Notification status.", self.spoken[-1])

    def test_notification_help_behavior(self) -> None:
        self._run_router(
            "notification help",
            extra_patches=[patch.object(notification_summaries, "notification_help_summary", return_value="Notification help.")],
        )

        self.assertEqual("Notification help.", self.spoken[-1])

    def test_popup_reminder_and_history_summaries_behavior(self) -> None:
        self._run_router("popup status", extra_patches=[patch.object(notification_summaries, "popup_alert_status_summary", return_value="Popup alert status.")])
        self._run_router("reminder notification status", extra_patches=[patch.object(notification_summaries, "reminder_notification_summary", return_value="Reminder notification status.")])
        self._run_router("notification history", extra_patches=[patch.object(notification_summaries, "notification_history_summary", return_value="Notification history.")])

        self.assertEqual("Popup alert status.", self.spoken[-3])
        self.assertEqual("Reminder notification status.", self.spoken[-2])
        self.assertEqual("Notification history.", self.spoken[-1])

    def test_unknown_notification_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "notification banana mode",
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

    def test_notification_mutations_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "send notification",
            "show popup",
            "show popup hello",
            "create reminder call amma",
            "update reminder call amma",
            "delete reminder call amma",
            "enable notifications",
            "disable notifications",
            "enable notification monitor",
            "disable notification monitor",
            "turn on health popup",
            "turn off health popup",
            "set popup timeout to 10",
            "change reminder popup interval to 5",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_notification_status_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
