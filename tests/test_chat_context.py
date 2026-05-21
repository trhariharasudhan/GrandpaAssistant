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

from core import chat_context
from core import chat_service


class ChatContextTests(unittest.TestCase):
    def tearDown(self) -> None:
        for key in (
            chat_context.CHAT_ENHANCED_ENV,
            chat_context.CHAT_SEMANTIC_MEMORY_ENV,
            chat_context.CHAT_OLLAMA_ROUTING_ENV,
            "GRANDPA_USE_RUNTIME_PROMPTS",
            "GRANDPA_USE_PROJECT_CONTEXT",
            "LLM_PROVIDER",
        ):
            os.environ.pop(key, None)

    def test_chat_enhancements_default_on(self) -> None:
        os.environ.pop(chat_context.CHAT_ENHANCED_ENV, None)
        self.assertTrue(chat_context.chat_enhancements_enabled())
        self.assertTrue(chat_context.semantic_memory_enabled_for_chat())
        self.assertTrue(chat_context.runtime_prompts_enabled_for_chat())
        self.assertTrue(chat_context.ollama_routing_enabled_for_chat())

    def test_chat_enhancements_can_disable_all(self) -> None:
        os.environ[chat_context.CHAT_ENHANCED_ENV] = "0"
        self.assertFalse(chat_context.chat_enhancements_enabled())
        self.assertFalse(chat_context.semantic_memory_enabled_for_chat())
        self.assertFalse(chat_context.runtime_prompts_enabled_for_chat())

    def test_project_context_auto_for_coding_when_enhanced(self) -> None:
        os.environ.pop("GRANDPA_USE_PROJECT_CONTEXT", None)
        self.assertTrue(chat_context.project_context_enabled_for_chat("fix this python bug in my api"))

    def test_build_chat_memory_context_uses_semantic_layer(self) -> None:
        with patch.object(chat_context, "build_semantic_memory_context", return_value="Relevant saved memory\n- name: Da"):
            context = chat_context.build_chat_memory_context("what is my name")
        self.assertIn("Memory context hints", context)
        self.assertIn("name: Da", context)

    def test_planning_mode_default_on_with_chat_enhanced(self) -> None:
        os.environ.pop(chat_context.CHAT_PLANNING_MODE_ENV, None)
        self.assertTrue(chat_context.planning_mode_enabled_for_chat())
        self.assertEqual("planning", chat_context.resolve_chat_prompt_mode("plan my day"))

    def test_resolve_chat_llm_model_for_ollama_coding(self) -> None:
        os.environ["LLM_PROVIDER"] = "ollama"
        routing = {"mode": "auto", "route": "coding", "model": "deepseek-coder:6.7b"}
        with patch.object(chat_context, "select_route", return_value=routing):
            model = chat_context.resolve_chat_llm_model("debug this python function")
        self.assertEqual(model, "deepseek-coder:6.7b")

    def test_chat_service_passes_memory_context_to_provider(self) -> None:
        chat_service.clear_all_chat_sessions_for_tests()
        seen: dict[str, str] = {}

        def provider(_history, message, system_prompt=None):
            seen["message"] = message
            seen["system_prompt"] = system_prompt or ""
            return "hello"

        with patch.object(chat_service, "answer_if_confident", return_value=None), patch.object(
            chat_service,
            "build_chat_memory_context",
            return_value="Memory context hints:\n- favorite_app: notepad",
        ):
            result = chat_service.build_chat_reply("hi", session_id="ctx-test", provider=provider)

        self.assertEqual(result["reply"], "hello")
        self.assertIn("favorite_app", seen.get("system_prompt", ""))
        chat_service.clear_all_chat_sessions_for_tests()


if __name__ == "__main__":
    unittest.main()
