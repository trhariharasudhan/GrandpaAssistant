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
from core.commands.handlers.planning import handle_planning_command
from tests.test_command_router_contacts_handler import _context


class CommandRouterPlanningHandlerTests(unittest.TestCase):
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

    def test_google_calendar_status_summary_behavior(self) -> None:
        self._run_router("google calendar status", extra_patches=[patch.object(command_router, "google_calendar_status", return_value="Google Calendar connected.")])

        self.assertEqual("Google Calendar connected.", self.spoken[-1])

    def test_google_calendar_today_agenda_behavior(self) -> None:
        self._run_router("today in google calendar", extra_patches=[patch.object(command_router, "today_google_calendar_events", return_value="Today events.")])

        self.assertEqual("Today events.", self.spoken[-1])

    def test_google_calendar_upcoming_and_titles_behavior(self) -> None:
        self._run_router("upcoming google calendar events", extra_patches=[patch.object(command_router, "upcoming_google_calendar_events", return_value="Upcoming events.")])
        self._run_router("google calendar titles", extra_patches=[patch.object(command_router, "list_google_calendar_event_titles", return_value="Calendar titles.")])

        self.assertEqual("Upcoming events.", self.spoken[-2])
        self.assertEqual("Calendar titles.", self.spoken[-1])

    def test_local_calendar_summary_behavior(self) -> None:
        def fake_calendar_query(command, speak):
            if command == "is 2024 a leap year":
                speak("2024 is a leap year.")
                return True
            return False

        self._run_router("is 2024 a leap year", extra_patches=[patch.object(command_router, "handle_calendar_queries", side_effect=fake_calendar_query)])

        self.assertEqual("2024 is a leap year.", self.spoken[-1])

    def test_today_agenda_still_intent_router_owned(self) -> None:
        self._run_router("today agenda", extra_patches=[patch.object(command_router, "try_handle_intent", return_value={"handled": True, "reply": "Agenda today."})])

        self.assertEqual("Agenda today.", self.spoken[-1])

    def test_unknown_planning_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "planning banana mode",
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

    def test_mutation_and_external_commands_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "sync google calendar",
            "refresh google calendar",
            "add google calendar event dentist",
            "create google calendar event dentist",
            "delete latest google calendar event",
            "reschedule google calendar event dentist",
            "set reminder to call amma",
            "delete reminder dentist",
            "send notification to phone",
            "weather",
            "show weather popup",
            "ai day plan",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_planning_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
