import sys
import unittest
import os
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
for path in [APP_DIR, SHARED_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from core import chat_service
from core.personal_assistant import executor


class ChatServiceContextAwareAssistantTests(unittest.TestCase):
    def setUp(self) -> None:
        chat_service.clear_all_chat_sessions_for_tests()
        self.previous_debug = os.environ.pop(chat_service.PERSONAL_ASSISTANT_DEBUG_ENV, None)
        self.local_patch = patch.object(chat_service, "answer_if_confident", return_value=None)
        self.local_patch.start()
        self.task_payload = {"tasks": [], "reminders": []}
        self.load_patch = patch.object(executor, "load_task_payload", side_effect=lambda default_factory=None: self.task_payload)
        self.save_patch = patch.object(executor, "save_task_payload", side_effect=self._save_task_payload)
        self.load_patch.start()
        self.save_patch.start()

    def tearDown(self) -> None:
        self.save_patch.stop()
        self.load_patch.stop()
        self.local_patch.stop()
        chat_service.clear_all_chat_sessions_for_tests()
        if self.previous_debug is None:
            os.environ.pop(chat_service.PERSONAL_ASSISTANT_DEBUG_ENV, None)
        else:
            os.environ[chat_service.PERSONAL_ASSISTANT_DEBUG_ENV] = self.previous_debug

    def _save_task_payload(self, payload, default_factory=None):
        self.task_payload = payload

    def test_chat_service_executes_supported_action_after_confirmation(self) -> None:
        provider_calls = []

        def provider(_history, _message, **_kwargs):
            provider_calls.append(_message)
            return "provider fallback"

        with patch.object(executor.local_action_executor, "execute_local_action", return_value={"ok": True, "message": "Opened calculator.", "data": {"app": "calculator"}}):
            first = chat_service.build_chat_reply("open calculator", session_id="assistant-action", provider=provider)
            second = chat_service.build_chat_reply("do it", session_id="assistant-action", provider=provider)

        self.assertEqual([], provider_calls)
        self.assertTrue(first["requires_confirmation"])
        self.assertTrue(second["executed"])
        self.assertEqual("personal-assistant", second["provider"])
        self.assertIn("Opened calculator", second["reply"])

    def test_chat_service_remembered_context_completes_reminder(self) -> None:
        first = chat_service.build_chat_reply("remind me to check invoices", session_id="assistant-reminder", provider=lambda *_args, **_kwargs: "fallback")
        second = chat_service.build_chat_reply("tomorrow morning", session_id="assistant-reminder", provider=lambda *_args, **_kwargs: "fallback")

        self.assertIn("When should I remind you", first["reply"])
        self.assertTrue(second["executed"])
        self.assertEqual("check invoices", self.task_payload["reminders"][0]["title"])

    def test_chat_service_still_falls_back_to_provider_for_normal_chat(self) -> None:
        result = chat_service.build_chat_reply(
            "tell me a short story",
            session_id="normal-chat",
            provider=lambda _history, _message, **_kwargs: "Once upon a time.",
        )

        self.assertEqual("Once upon a time.", result["reply"])
        self.assertNotEqual("personal-assistant", result["provider"])

    def test_unsupported_follow_up_action_reports_missing_adapter(self) -> None:
        def fake_action(payload):
            if payload["action"] == "open_app":
                return {"ok": True, "message": "Opened notepad.", "data": {"app": "notepad", "pid": 456}}
            return {"ok": False, "message": "I did not find a running notepad process that I can safely close.", "data": {"app": "notepad"}}

        with patch.object(executor.local_action_executor, "execute_local_action", side_effect=fake_action):
            chat_service.build_chat_reply("open notepad", session_id="close-chat", provider=lambda *_args, **_kwargs: "fallback")
            chat_service.build_chat_reply("yes", session_id="close-chat", provider=lambda *_args, **_kwargs: "fallback")
            confirm = chat_service.build_chat_reply("close it", session_id="close-chat", provider=lambda *_args, **_kwargs: "fallback")
            result = chat_service.build_chat_reply("yes", session_id="close-chat", provider=lambda *_args, **_kwargs: "fallback")

        self.assertTrue(confirm["requires_confirmation"])
        self.assertFalse(result["ok"])
        self.assertIn("close_app adapter failed", result["reply"])

    def test_memory_fact_does_not_override_action_intent(self) -> None:
        with patch.object(chat_service, "answer_if_confident", return_value="Stored fact about music."), patch.object(
            executor.local_action_executor,
            "execute_local_action",
            return_value={"ok": True, "message": "Reduced the system volume.", "data": {"operation": "decrease"}},
        ):
            result = chat_service.build_chat_reply("sound kammi pannu", session_id="volume-chat", provider=lambda *_args, **_kwargs: "fallback")

        self.assertEqual("personal-assistant", result["provider"])
        self.assertTrue(result["executed"])
        self.assertIn("Reduced the system volume", result["reply"])

    def test_debug_metadata_is_opt_in_and_safe(self) -> None:
        with patch.object(
            executor.local_action_executor,
            "execute_local_action",
            return_value={"ok": True, "message": "Reduced the system volume.", "data": {"operation": "decrease"}},
        ):
            normal = chat_service.build_chat_reply("Laptop sound kammi pannu", session_id="debug-normal", provider=lambda *_args, **_kwargs: "fallback")

        self.assertNotIn("debug", normal)

        os.environ[chat_service.PERSONAL_ASSISTANT_DEBUG_ENV] = "1"
        with patch.object(
            executor.local_action_executor,
            "execute_local_action",
            return_value={"ok": True, "message": "Reduced the system volume.", "data": {"operation": "decrease"}},
        ):
            debug = chat_service.build_chat_reply("Laptop sound kammi pannu", session_id="debug-on", provider=lambda *_args, **_kwargs: "fallback")

        self.assertIn("debug", debug)
        metadata = debug["debug"]
        self.assertEqual("adjust_volume", metadata["detected_intent"])
        self.assertEqual("adjust_volume", metadata["planned_action"])
        self.assertEqual([], metadata["missing_fields"])
        self.assertTrue(metadata["executor_result"]["ok"])
        self.assertNotIn("Laptop sound kammi pannu", str(metadata))


if __name__ == "__main__":
    unittest.main()
