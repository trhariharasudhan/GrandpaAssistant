import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from backend.app.cli import chat
from backend.app.config.grandpa_config import GrandpaConfig
from backend.app.core.chatbot import ChatbotEngine
from backend.app.core.chatbot.intent_router import route_intent
from backend.app.core.chatbot.memory import ChatMemory
from backend.app.core.chatbot.providers.openai_provider import OpenAIProvider


class TerminalChatCliTests(unittest.TestCase):
    def _config(self, tmp):
        return GrandpaConfig(
            provider="fallback",
            model="rules",
            db_path=str(Path(tmp) / "grandpa_chat.db"),
            log_path=str(Path(tmp) / "grandpa.log"),
            log_level="INFO",
        )

    def test_memory_saves_messages_with_session_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = ChatMemory(Path(tmp) / "chat.db")
            memory.add_message("s1", "user", "hello", provider="test", model="rules")
            memory.add_message("s1", "assistant", "vanakkam", provider="test", model="rules")

            history = memory.recent_messages("s1", limit_turns=10)

        self.assertEqual([item["role"] for item in history], ["user", "assistant"])
        self.assertEqual(history[0]["message"], "hello")
        self.assertGreaterEqual(history[0]["token_estimate"], 1)

    def test_intent_router_handles_greeting_time_math(self):
        self.assertIn("Hi", route_intent("hi da").reply)
        self.assertIn("Vanakkam", route_intent("vanakkam").reply)
        self.assertTrue(route_intent("what is time now").handled)
        self.assertEqual(route_intent("10+25").reply, "35")
        self.assertEqual(route_intent("what is 10+25").reply, "35")

    def test_missing_openai_key_has_clear_error(self):
        provider = OpenAIProvider(api_key="", model="gpt-test", base_url="https://api.openai.com/v1", timeout_seconds=1)
        result = provider.generate("hello")
        self.assertFalse(result.ok)
        self.assertIn("OPENAI_API_KEY is missing", result.error)

    def test_engine_fallback_reply_and_memory_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = ChatbotEngine(config=self._config(tmp), session_id="s1")
            try:
                reply = engine.reply("hi da")
                saved = engine.save_memory("my name is Hari")
                memory = engine.memory_summary()
                forgotten = engine.forget_memory("Hari")
            finally:
                engine.close()

        self.assertIn("Hi da", reply)
        self.assertEqual(saved, "Saved da.")
        self.assertIn("my name is Hari", memory)
        self.assertIn("Forgot 1", forgotten)

    def test_fallback_provider_does_not_echo_user_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = ChatbotEngine(config=self._config(tmp), session_id="s2")
            try:
                reply = engine.reply("explain quantum banana briefly")
            finally:
                engine.close()

        self.assertNotIn("explain quantum banana briefly", reply.lower())
        self.assertIn("couldn't reach an ai model", reply.lower())

    def test_cli_smoke_mode_prints_one_reply_and_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(tmp)
            engine = ChatbotEngine(config=config, session_id="smoke")
            buffer = io.StringIO()
            try:
                with redirect_stdout(buffer):
                    with patch("backend.app.cli.chat.ChatbotEngine", return_value=engine):
                        exit_code = chat.run_chat(session_id="smoke", smoke_message="hello")
            finally:
                engine.close()

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("GrandpaAssistant Terminal Chat", output)
        self.assertIn("Grandpa:", output)


if __name__ == "__main__":
    unittest.main()
