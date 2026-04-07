import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from brain import database as brain_database
import app_data_store
import productivity_store
from productivity import event_module, notes_module, task_module


class ProductivityStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "assistant.db")
        self.path_patches = [
            patch.object(brain_database, "DB_PATH", self.db_path),
            patch.object(productivity_store, "DB_PATH", self.db_path),
            patch.object(app_data_store, "DB_PATH", self.db_path),
        ]
        for path_patch in self.path_patches:
            path_patch.start()

    def tearDown(self) -> None:
        for path_patch in reversed(self.path_patches):
            path_patch.stop()
        self.temp_dir.cleanup()

    def test_task_module_imports_legacy_payload_once_then_reads_from_sqlite(self) -> None:
        legacy_path = os.path.join(self.temp_dir.name, "tasks.json")
        with open(legacy_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "tasks": [
                        {
                            "title": "Prepare release deck",
                            "completed": False,
                            "priority": "high",
                            "category": "work",
                            "created_at": "2026-04-06T09:00:00",
                        }
                    ],
                    "reminders": [
                        {
                            "title": "Ping QA",
                            "due_date": "2026-04-06",
                            "due_at": None,
                            "created_at": "2026-04-06T09:10:00",
                        }
                    ],
                },
                file,
                indent=2,
            )

        with patch.object(task_module, "DATA_FILE", legacy_path):
            first_load = task_module.get_task_data()
            self.assertEqual(first_load["tasks"][0]["title"], "Prepare release deck")
            self.assertEqual(first_load["reminders"][0]["title"], "Ping QA")

            os.remove(legacy_path)
            second_load = task_module.get_task_data()
            self.assertEqual(second_load["tasks"][0]["title"], "Prepare release deck")
            self.assertEqual(second_load["reminders"][0]["title"], "Ping QA")

    def test_notes_and_events_use_sqlite_without_rewriting_legacy_files(self) -> None:
        notes_path = os.path.join(self.temp_dir.name, "notes.json")
        events_path = os.path.join(self.temp_dir.name, "events.json")

        with patch.object(notes_module, "DATA_FILE", notes_path), patch.object(event_module, "DATA_FILE", events_path):
            note_message = notes_module.add_note("add note finish sqlite migration")
            event_message = event_module.add_event("add event release sync tomorrow at 10 am")

            self.assertIn("Note saved", note_message)
            self.assertIn("Event added", event_message)
            self.assertFalse(os.path.exists(notes_path))
            self.assertFalse(os.path.exists(events_path))

            notes_payload = notes_module._load_data()
            events_payload = event_module.get_event_data()
            self.assertEqual(notes_payload["notes"][0]["content"], "finish sqlite migration")
            self.assertTrue(events_payload["events"])

    def test_user_preferences_and_chat_state_roundtrip(self) -> None:
        created = app_data_store.create_user(
            "captain",
            "Captain",
            "hash",
            "salt",
            role="admin",
        )
        updated = app_data_store.update_user_profile(int(created["id"]), display_name="Grand Captain")
        self.assertEqual(updated["display_name"], "Grand Captain")

        preferences = productivity_store.update_user_preferences(
            int(created["id"]),
            {
                "preferred_language": "en-IN",
                "response_style": "concise",
                "tone": "professional",
                "theme": "dark",
                "short_answers": True,
            },
        )
        self.assertEqual(preferences["response_style"], "concise")
        self.assertTrue(preferences["short_answers"])

        default_factory = lambda: {"settings": {}, "session_order": [], "sessions": {}}
        state_payload = {
            "settings": {"ollama_model": "mistral:7b"},
            "session_order": ["session-1"],
            "sessions": {
                "session-1": {
                    "id": "session-1",
                    "title": "Launch plan",
                    "messages": [{"role": "user", "content": "plan launch"}],
                    "documents": [],
                    "created_at": "2026-04-06T10:00:00Z",
                    "updated_at": "2026-04-06T10:05:00Z",
                }
            },
        }

        productivity_store.save_chat_state_payload(state_payload, default_factory=default_factory)
        loaded = productivity_store.load_chat_state_payload(
            default_factory=default_factory,
            legacy_loader=lambda: {"settings": {}, "session_order": [], "sessions": {}},
        )

        self.assertEqual(loaded["settings"]["ollama_model"], "mistral:7b")
        self.assertEqual(loaded["session_order"], ["session-1"])
        self.assertEqual(loaded["sessions"]["session-1"]["title"], "Launch plan")
        self.assertEqual(
            productivity_store.get_user_preferences(int(created["id"]))["preferred_language"],
            "en-IN",
        )


if __name__ == "__main__":
    unittest.main()
