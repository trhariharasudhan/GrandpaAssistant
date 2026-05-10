import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
for path in [APP_DIR, SHARED_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from core import chat_service
from core import unified_command_router


class CleanChatServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        chat_service.clear_all_chat_sessions_for_tests()
        self.local_patch = patch.object(chat_service, "answer_if_confident", return_value=None)
        self.local_patch.start()

    def tearDown(self) -> None:
        self.local_patch.stop()
        chat_service.clear_all_chat_sessions_for_tests()

    def test_normal_chat_returns_provider_answer_not_old_response(self) -> None:
        old_summary = "Python is a programming language."
        chat_service.build_chat_reply("tell me about python", session_id="s1", provider=lambda *_args, **_kwargs: old_summary)

        result = chat_service.build_chat_reply(
            "who is chief minister of tamil nadu 2026",
            session_id="s1",
            provider=lambda *_args, **_kwargs: old_summary,
        )

        self.assertEqual(result["route"], "chat")
        self.assertEqual(result["reply"], chat_service.FALLBACK_REPLY)
        self.assertNotEqual(result["reply"], old_summary)

    def test_two_unrelated_questions_do_not_contaminate_each_other(self) -> None:
        replies = iter(["Python is a programming language.", "M. K. Stalin is the Chief Minister of Tamil Nadu."])

        first = chat_service.build_chat_reply("what is python", session_id="s2", provider=lambda *_args, **_kwargs: next(replies))
        second = chat_service.build_chat_reply(
            "who is chief minister of tamil nadu 2026",
            session_id="s2",
            provider=lambda *_args, **_kwargs: next(replies),
        )

        self.assertIn("Python", first["reply"])
        self.assertIn("Stalin", second["reply"])
        self.assertNotIn("programming language", second["reply"])

    def test_follow_up_can_use_previous_context(self) -> None:
        seen_history_lengths = []

        def provider(history, _message, **_kwargs):
            seen_history_lengths.append(len(history))
            return "It refers to the previous answer." if history else "Python is a programming language."

        chat_service.build_chat_reply("what is python", session_id="s3", provider=provider)
        follow_up = chat_service.build_chat_reply("why is it popular", session_id="s3", provider=provider)

        self.assertGreater(seen_history_lengths[-1], 0)
        self.assertIn("previous answer", follow_up["reply"])

    def test_reset_chat_clears_context(self) -> None:
        chat_service.build_chat_reply("what is python", session_id="s4", provider=lambda *_args, **_kwargs: "Python answer.")
        reset = chat_service.build_chat_reply("reset chat", session_id="s4")
        session = chat_service.get_chat_session("s4")

        self.assertEqual(reset["route"], "reset")
        self.assertEqual(session.messages, [])

    def test_explicit_automation_routes_to_n8n(self) -> None:
        with patch.object(chat_service, "send_n8n_message", return_value={"ok": True, "status_code": 200, "data": {}}) as send:
            result = chat_service.build_chat_reply("trigger n8n hello from voice", session_id="s5", channel="voice")

        self.assertEqual(result["route"], "automation")
        self.assertEqual(result["reply"], "Automation sent to n8n successfully.")
        self.assertEqual(send.call_args.args[0], "hello from voice")

    def test_ui_command_routes_to_command_executor(self) -> None:
        result = chat_service.build_chat_reply(
            "analyze my screen",
            session_id="s6",
            command_executor=lambda command: [f"UI summary for {command}"],
        )

        self.assertEqual(result["route"], "ui")
        self.assertIn("UI summary", result["reply"])

    def test_provider_failure_returns_safe_fallback(self) -> None:
        def failing_provider(*_args, **_kwargs):
            raise RuntimeError("provider offline")

        result = chat_service.build_chat_reply("who is chief minister of tamil nadu 2026", session_id="s7", provider=failing_provider)

        self.assertEqual(result["reply"], chat_service.FALLBACK_REPLY)
        self.assertIn("failed", result["provider"])

    def test_unified_router_sends_natural_question_to_chat_service(self) -> None:
        with patch.object(
            unified_command_router,
            "build_chat_reply",
            return_value={
                "ok": True,
                "reply": "M. K. Stalin is the Chief Minister of Tamil Nadu.",
                "route": "chat",
                "session_id": "test",
                "provider": "mock",
                "context_turns": 0,
            },
        ) as chat_reply:
            result = unified_command_router.execute_command(
                "who is chief minister of tamil nadu 2026",
                installed_apps={},
                input_mode="text",
                source="test",
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.module, "chat-service")
        self.assertIn("Stalin", result.messages[0])
        chat_reply.assert_called_once()


if __name__ == "__main__":
    unittest.main()
