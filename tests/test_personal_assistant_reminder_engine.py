import datetime
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
for path in [APP_DIR, SHARED_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from core.personal_assistant import executor, reminder_engine
from core.personal_assistant.context import clear_personal_assistant_contexts_for_tests
from core.personal_assistant.service import handle_personal_assistant_message


class PersonalAssistantReminderEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_personal_assistant_contexts_for_tests()
        self.payload = {"tasks": [], "reminders": []}
        self.load_patch = patch.object(executor, "load_task_payload", side_effect=lambda default_factory=None: self.payload)
        self.save_patch = patch.object(executor, "save_task_payload", side_effect=self._save_payload)
        self.load_patch.start()
        self.save_patch.start()

    def tearDown(self) -> None:
        self.save_patch.stop()
        self.load_patch.stop()
        clear_personal_assistant_contexts_for_tests()

    def _save_payload(self, payload, default_factory=None):
        self.payload = payload

    def _load_payload(self, default_factory=None):
        return self.payload

    def test_structured_reminder_creation_has_scheduler_fields(self) -> None:
        now = datetime.datetime(2026, 5, 17, 8, 0)
        result = reminder_engine.create_reminder(
            {"reminder_text": "drink water", "time_text": "in 10 minutes", "source_conversation_summary": "User asked for hydration reminder."},
            now=now,
            load_payload=self._load_payload,
            save_payload=self._save_payload,
        )

        self.assertTrue(result["ok"])
        reminder = self.payload["reminders"][0]
        self.assertTrue(reminder["id"])
        self.assertEqual("drink water", reminder["title"])
        self.assertEqual("2026-05-17T08:10", reminder["due_at"])
        self.assertEqual(reminder["due_at"], reminder["due_datetime"])
        self.assertEqual("pending", reminder["status"])
        self.assertIn("updated_at", reminder)

    def test_due_detection_marks_due_and_avoids_duplicate_notifications(self) -> None:
        now = datetime.datetime(2026, 5, 17, 8, 0)
        reminder_engine.create_reminder(
            {"reminder_text": "project discussion", "time_text": "in 10 minutes"},
            now=now,
            load_payload=self._load_payload,
            save_payload=self._save_payload,
        )
        deliveries = []

        first = reminder_engine.check_due_reminders(
            now=now + datetime.timedelta(minutes=10),
            notifier=lambda reminder: deliveries.append(reminder) or {"ok": True, "channel": "mock", "message": "sent"},
            load_payload=self._load_payload,
            save_payload=self._save_payload,
        )
        second = reminder_engine.check_due_reminders(
            now=now + datetime.timedelta(minutes=11),
            notifier=lambda reminder: deliveries.append(reminder) or {"ok": True, "channel": "mock", "message": "sent"},
            load_payload=self._load_payload,
            save_payload=self._save_payload,
        )

        self.assertEqual(1, first["notification_count"])
        self.assertEqual(0, second["notification_count"])
        self.assertEqual(1, len(deliveries))
        self.assertEqual("due", self.payload["reminders"][0]["status"])
        self.assertTrue(self.payload["reminders"][0]["notified_at"])

    def test_list_complete_and_cancel_reminders(self) -> None:
        now = datetime.datetime(2026, 5, 17, 8, 0)
        reminder_engine.create_reminder({"reminder_text": "call amma", "time_text": "in 10 minutes"}, now=now, load_payload=self._load_payload, save_payload=self._save_payload)
        reminder_engine.create_reminder({"reminder_text": "drink water", "time_text": "in 20 minutes"}, now=now, load_payload=self._load_payload, save_payload=self._save_payload)

        listed = reminder_engine.list_reminders(load_payload=self._load_payload)
        done = reminder_engine.complete_reminder("call amma", load_payload=self._load_payload, save_payload=self._save_payload)
        cancelled = reminder_engine.cancel_reminder("drink water", load_payload=self._load_payload, save_payload=self._save_payload)

        self.assertIn("call amma", listed["message"])
        self.assertTrue(done["ok"])
        self.assertTrue(cancelled["ok"])
        statuses = {item["title"]: item["status"] for item in self.payload["reminders"]}
        self.assertEqual("done", statuses["call amma"])
        self.assertEqual("cancelled", statuses["drink water"])

    def test_this_reminder_completes_single_pending_item(self) -> None:
        reminder_engine.create_reminder({"reminder_text": "stand up", "time_text": "in 10 minutes"}, load_payload=self._load_payload, save_payload=self._save_payload)

        result = handle_personal_assistant_message("mark this reminder done", session_id="single-reminder")

        self.assertTrue(result["executed"])
        self.assertEqual("done", self.payload["reminders"][0]["status"])

    def test_ambiguous_reminder_match_asks_follow_up(self) -> None:
        for title in ["project discussion", "project review"]:
            reminder_engine.create_reminder({"reminder_text": title, "time_text": "tomorrow morning"}, load_payload=self._load_payload, save_payload=self._save_payload)

        result = reminder_engine.cancel_reminder("project", load_payload=self._load_payload, save_payload=self._save_payload)

        self.assertFalse(result["ok"])
        self.assertTrue(result["needs_disambiguation"])
        self.assertIn("multiple", result["message"].lower())

    def test_chat_path_handles_relative_reminder_listing_completion_and_cancellation(self) -> None:
        created = handle_personal_assistant_message("remind me in 10 minutes to drink water", session_id="reminder-chat")
        listed = handle_personal_assistant_message("what reminders do I have?", session_id="reminder-chat")
        completed = handle_personal_assistant_message("mark drink water reminder done", session_id="reminder-chat")
        handle_personal_assistant_message("remind me in 10 minutes to stretch", session_id="reminder-chat")
        cancelled = handle_personal_assistant_message("cancel stretch reminder", session_id="reminder-chat")

        self.assertTrue(created["executed"])
        self.assertEqual("list_reminders", listed["intent"])
        self.assertIn("drink water", listed["reply"])
        self.assertTrue(completed["executed"])
        self.assertTrue(cancelled["executed"])

    def test_chat_path_ambiguous_cancel_asks_which_reminder(self) -> None:
        reminder_engine.create_reminder({"reminder_text": "project discussion", "time_text": "tomorrow morning"}, load_payload=self._load_payload, save_payload=self._save_payload)
        reminder_engine.create_reminder({"reminder_text": "project review", "time_text": "tomorrow morning"}, load_payload=self._load_payload, save_payload=self._save_payload)

        result = handle_personal_assistant_message("cancel project reminder", session_id="ambiguous-reminder")

        self.assertTrue(result["handled"])
        self.assertFalse(result["ok"])
        self.assertIn("multiple matching reminders", result["reply"].lower())
        self.assertTrue(all(item["status"] == "pending" for item in self.payload["reminders"]))

    def test_notification_fallback_path_returns_log_channel(self) -> None:
        reminder = reminder_engine.normalize_reminder_record({"reminder_text": "drink water", "time_text": "in 10 minutes"})
        result = reminder_engine.deliver_reminder_notification(reminder, use_windows_toast=False)

        self.assertTrue(result["ok"])
        self.assertEqual("log", result["channel"])


if __name__ == "__main__":
    unittest.main()
