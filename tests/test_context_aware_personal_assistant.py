import sys
import tempfile
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


from core.personal_assistant.context import clear_personal_assistant_contexts_for_tests
from core.personal_assistant import executor
from core.personal_assistant.service import handle_personal_assistant_message


class ContextAwarePersonalAssistantTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_personal_assistant_contexts_for_tests()
        self.task_payload = {"tasks": [], "reminders": []}
        self.load_patch = patch.object(executor, "load_task_payload", side_effect=lambda default_factory=None: self.task_payload)
        self.save_patch = patch.object(executor, "save_task_payload", side_effect=self._save_task_payload)
        self.load_patch.start()
        self.save_patch.start()

    def tearDown(self) -> None:
        self.save_patch.stop()
        self.load_patch.stop()
        clear_personal_assistant_contexts_for_tests()

    def _save_task_payload(self, payload, default_factory=None):
        self.task_payload = payload

    def test_open_app_uses_confirmation_and_follow_up_for_multiple_phrasings(self) -> None:
        with patch.object(executor.local_action_executor, "execute_local_action", return_value={"ok": True, "message": "Opened calculator.", "data": {"app": "calculator"}}) as action:
            for index, message in enumerate(["open calculator", "launch calc", "calculator open pannu"], start=1):
                session_id = f"open-{index}"
                first = handle_personal_assistant_message(message, session_id=session_id)
                self.assertTrue(first["handled"])
                self.assertTrue(first["requires_confirmation"])
                self.assertIn("go ahead", first["reply"].lower())

                second = handle_personal_assistant_message("yes", session_id=session_id)
                self.assertTrue(second["executed"])
                self.assertIn("Opened calculator", second["reply"])

        self.assertEqual(3, action.call_count)
        for call in action.call_args_list:
            self.assertEqual({"action": "open_app", "params": {"app": "calculator"}}, call.args[0])

    def test_missing_open_target_asks_useful_follow_up(self) -> None:
        result = handle_personal_assistant_message("open it", session_id="missing-open")

        self.assertTrue(result["handled"])
        self.assertIn("Which app", result["reply"])
        self.assertIn("target_app", result["missing_details"])

    def test_reminder_collects_missing_time_from_follow_up(self) -> None:
        first = handle_personal_assistant_message("remind me to call amma", session_id="reminder")

        self.assertTrue(first["handled"])
        self.assertIn("When should I remind you", first["reply"])

        second = handle_personal_assistant_message("tomorrow morning", session_id="reminder")

        self.assertTrue(second["executed"])
        self.assertIn("Reminder added", second["reply"])
        self.assertEqual("call amma", self.task_payload["reminders"][0]["title"])
        self.assertIsNotNone(self.task_payload["reminders"][0]["due_at"])

    def test_reminder_handles_tanglish_time_and_task_in_one_message(self) -> None:
        result = handle_personal_assistant_message("remind me naalai morning to call amma", session_id="tanglish-reminder")

        self.assertTrue(result["executed"])
        self.assertIn("Reminder added", result["reply"])
        self.assertEqual("call amma", self.task_payload["reminders"][0]["title"])

    def test_create_folder_executes_when_details_are_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "receipts"
            with patch.object(executor.local_action_executor, "execute_local_action", return_value={"ok": True, "message": "Folder is ready.", "data": {"path": str(target)}}) as action:
                result = handle_personal_assistant_message(f"create folder receipts in {temp_dir}", session_id="folder")

        self.assertTrue(result["executed"])
        self.assertIn("Folder is ready", result["reply"])
        payload = action.call_args.args[0]
        self.assertEqual("create_folder", payload["action"])
        self.assertTrue(payload["params"]["path"].endswith("receipts"))

    def test_close_it_uses_context_but_reports_missing_adapter(self) -> None:
        def fake_action(payload):
            if payload["action"] == "open_app":
                return {"ok": True, "message": "Opened calculator.", "data": {"app": "calculator", "pid": 123}}
            return {"ok": True, "message": "Closed calculator.", "data": {"app": "calculator"}}

        with patch.object(executor.local_action_executor, "execute_local_action", side_effect=fake_action):
            handle_personal_assistant_message("open calculator", session_id="close")
            handle_personal_assistant_message("yes", session_id="close")

            result = handle_personal_assistant_message("close it", session_id="close")

        self.assertTrue(result["handled"])
        self.assertTrue(result["ok"])
        self.assertTrue(result["executed"])
        self.assertIn("Closed calculator", result["reply"])

    def test_system_diagnostics_runs_read_only_adapter_for_generalized_requests(self) -> None:
        with patch.object(executor, "build_backend_stability_payload", return_value={"overall_ok": True}), patch.object(
            executor, "format_backend_stability_text", return_value="Backend stability: release lock is clear."
        ):
            for message in ["run diagnostics", "check everything", "backend health check"]:
                result = handle_personal_assistant_message(message, session_id=message)
                self.assertTrue(result["executed"])
                self.assertIn("Backend health", result["reply"])
                self.assertIn("CPU usage", result["reply"])

    def test_volume_phrasings_map_to_same_safe_action(self) -> None:
        with patch.object(
            executor.local_action_executor,
            "execute_local_action",
            return_value={"ok": True, "message": "Reduced the system volume.", "data": {"operation": "decrease"}},
        ) as action:
            for message in ["reduce volume", "lower sound", "sound kammi pannu", "volume konjam kammi pannu"]:
                result = handle_personal_assistant_message(message, session_id=message)
                self.assertTrue(result["executed"])
                self.assertIn("Reduced the system volume", result["reply"])

        self.assertEqual(4, action.call_count)
        self.assertTrue(all(call.args[0]["action"] == "adjust_volume" for call in action.call_args_list))

    def test_volume_adapter_failure_is_specific(self) -> None:
        with patch.object(
            executor.local_action_executor,
            "execute_local_action",
            return_value={"ok": False, "message": "Windows volume control failed: unavailable.", "data": {"operation": "decrease"}},
        ):
            result = handle_personal_assistant_message("lower sound", session_id="volume-fail")

        self.assertFalse(result["ok"])
        self.assertIn("adjust_volume adapter failed", result["reply"])

    def test_meeting_reminder_collects_missing_details_then_stores_structure(self) -> None:
        first = handle_personal_assistant_message("I have a meeting tomorrow morning", session_id="meeting")

        self.assertTrue(first["handled"])
        self.assertIn("What time", first["reply"])

        second = handle_personal_assistant_message("10 AM project discussion", session_id="meeting")

        self.assertTrue(second["executed"])
        reminder = self.task_payload["reminders"][0]
        self.assertEqual("project discussion", reminder["title"])
        self.assertEqual("project discussion", reminder["topic"])
        self.assertIn("source_conversation_summary", reminder)

    def test_safe_close_refuses_unknown_untracked_process(self) -> None:
        result = handle_personal_assistant_message("close explorer", session_id="unsafe-close")

        self.assertTrue(result["handled"])
        self.assertFalse(result["ok"])
        self.assertIn("close_app adapter failed", result["reply"])

    def test_unknown_message_falls_through(self) -> None:
        result = handle_personal_assistant_message("tell me a story about old computers", session_id="unknown")

        self.assertFalse(result["handled"])


if __name__ == "__main__":
    unittest.main()
