import os
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from api import chat_api


class ChatApiPromptBehaviorTests(unittest.TestCase):
    def test_chat_prompt_includes_memory_language_and_style(self) -> None:
        with patch.object(chat_api, "search_memory", return_value="Your goal is Python."), \
            patch.object(chat_api, "build_semantic_memory_context", return_value="Semantic memory says FastAPI."), \
            patch.object(chat_api, "build_emotion_prompt_context", return_value="Emotion context."), \
            patch.object(chat_api, "build_mood_memory_context", return_value="Mood context."), \
            patch.object(chat_api, "build_intelligence_prompt_boost", return_value="Full code answers preferred."):
            prompt = chat_api._chat_prompt_with_memory("enna da code plan")

        self.assertIn("Semantic memory says FastAPI.", prompt)
        self.assertIn("User question: enna da code plan", prompt)
        self.assertIn("Answer naturally in English only", prompt)
        self.assertIn("Full code answers preferred.", prompt)

    def test_build_ai_prompt_includes_recent_history_and_hardware_context(self) -> None:
        with patch.object(chat_api.DEVICE_MANAGER, "build_prompt_context", return_value="Hardware context."), \
            patch.object(chat_api, "search_memory", return_value=""), \
            patch.object(chat_api, "build_semantic_memory_context", return_value=""), \
            patch.object(chat_api, "build_emotion_prompt_context", return_value="Emotion context."), \
            patch.object(chat_api, "build_mood_memory_context", return_value="Mood context."), \
            patch.object(chat_api, "build_intelligence_prompt_boost", return_value="Intelligence context."):
            prompt, hardware = chat_api._build_ai_prompt(
                "continue",
                history=[{"role": "user", "content": "I opened VS Code"}],
            )

        self.assertEqual(hardware, "Hardware context.")
        self.assertIn("Hardware context.", prompt)
        self.assertIn("Recent conversation:", prompt)
        self.assertIn("User: I opened VS Code", prompt)
        self.assertIn("User question: continue", prompt)
        self.assertIn("Intelligence context.", prompt)
        self.assertIn("Use the hardware context only when it is relevant", prompt)

    def test_empty_context_does_not_crash(self) -> None:
        with patch.object(chat_api, "search_memory", return_value=""), \
            patch.object(chat_api, "build_semantic_memory_context", return_value=""), \
            patch.object(chat_api, "build_emotion_prompt_context", return_value=""), \
            patch.object(chat_api, "build_mood_memory_context", return_value=""), \
            patch.object(chat_api, "build_intelligence_prompt_boost", return_value=""):
            prompt = chat_api._chat_prompt_with_memory("")

        self.assertIn("User question:", prompt)
        self.assertIn("Reply in natural English only", prompt)

    def test_chat_route_behavior_shape_is_preserved(self) -> None:
        chat_api.CHAT_HISTORY.clear()
        patches = [
            patch.object(chat_api, "_ensure_runtime_ready", lambda: None),
            patch.object(chat_api, "_enforce_api_auth", lambda request: None),
            patch.object(chat_api, "_authenticated_user_id", lambda request: None),
            patch.object(chat_api, "append_chat_message", lambda *args, **kwargs: None),
            patch.object(chat_api, "log_audit_event", lambda *args, **kwargs: None),
            patch.object(chat_api, "append_security_activity", lambda *args, **kwargs: None),
            patch.object(chat_api.ASSISTANT_RUNTIME, "observe_user_message", lambda *args, **kwargs: {"context": "casual"}),
            patch.object(chat_api.ASSISTANT_RUNTIME, "observe_assistant_reply", lambda *args, **kwargs: None),
            patch.object(chat_api, "observe_user_turn", lambda *args, **kwargs: None),
            patch.object(chat_api, "record_assistant_turn", lambda *args, **kwargs: {"id": "interaction-1"}),
            patch.object(chat_api, "record_mood_from_analysis", lambda *args, **kwargs: {"last_mood": "neutral"}),
            patch.object(chat_api, "analyze_emotion", lambda *_args, **_kwargs: {"emotion": "neutral"}),
            patch.object(chat_api, "validate_prompt_text", lambda *args, **kwargs: {"allowed": True}),
            patch.object(chat_api, "answer_if_confident", lambda *args, **kwargs: None),
            patch.object(chat_api, "route_request", lambda *args, **kwargs: {"mode": "auto", "reason": "test"}),
            patch.object(chat_api, "generate_chat_reply", return_value="Python is a programming language."),
        ]
        try:
            for item in patches:
                item.start()
            response = TestClient(chat_api.app).post("/chat", json={"message": "what is python?"})
        finally:
            for item in reversed(patches):
                item.stop()
            chat_api.CHAT_HISTORY.clear()

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["reply"], "Python is a programming language.")
        self.assertIn("messages", payload)


if __name__ == "__main__":
    unittest.main()
