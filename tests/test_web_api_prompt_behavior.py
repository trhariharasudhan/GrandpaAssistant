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

from api import web_api


class WebApiPromptBehaviorTests(unittest.TestCase):
    def test_effective_system_prompt_includes_persona_language_and_code_guidance(self) -> None:
        with patch.object(web_api, "build_emotion_prompt_context", return_value="Emotion guidance."), \
            patch.object(web_api, "build_mood_memory_context", return_value="Mood guidance."), \
            patch.object(web_api, "build_intelligence_prompt_boost", return_value="Code answers should be complete."):
            prompt = web_api._effective_system_prompt("write code for enna da", mood_snapshot={"last_mood": "neutral"})

        self.assertIn(web_api._chat_settings["system_prompt"], prompt)
        self.assertIn("Tone:", prompt)
        self.assertIn("Understand Tanglish", prompt)
        self.assertIn("Code answers should be complete.", prompt)

    def test_build_chat_input_includes_memory_and_document_context(self) -> None:
        session = {"documents": [{"name": "notes.txt", "chunks": ["Python project notes mention FastAPI routes."]}]}
        with patch.object(web_api, "build_semantic_memory_context", return_value="Relevant saved memory."), \
            patch.object(web_api, "build_emotion_prompt_context", return_value="Emotion context."), \
            patch.object(web_api, "build_mood_memory_context", return_value="Mood context."), \
            patch.object(web_api, "build_intelligence_prompt_boost", return_value="Intelligence context."):
            prompt = web_api._build_chat_input(session, "summarize document routes")

        self.assertIn("Relevant saved memory.", prompt)
        self.assertIn("Use the attached document context", prompt)
        self.assertIn("User question: summarize document routes", prompt)
        self.assertIn("Answer clearly using the provided context", prompt)

    def test_build_chat_input_empty_context_does_not_crash(self) -> None:
        with patch.object(web_api, "build_semantic_memory_context", return_value=""), \
            patch.object(web_api, "_session_document_context", return_value=None), \
            patch.object(web_api, "build_emotion_prompt_context", return_value=""), \
            patch.object(web_api, "build_mood_memory_context", return_value=""), \
            patch.object(web_api, "build_intelligence_prompt_boost", return_value=""):
            prompt = web_api._build_chat_input({"documents": []}, "hello")

        self.assertIn("User question: hello", prompt)

    def test_chat_route_behavior_shape_is_preserved(self) -> None:
        patches = [
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
            patch.object(web_api, "_enforce_app_auth", lambda request: None),
            patch.object(web_api, "_save_chat_state", lambda: None),
            patch.object(web_api, "upsert_chat_session", lambda *args, **kwargs: None),
            patch.object(web_api, "append_chat_message", lambda *args, **kwargs: None),
            patch.object(web_api, "log_audit_event", lambda *args, **kwargs: None),
            patch.object(web_api.MOBILE_COMPANION, "record_chat_message", lambda *args, **kwargs: None),
            patch.object(web_api.ASSISTANT_RUNTIME, "observe_user_message", lambda *args, **kwargs: {"context": "casual"}),
            patch.object(web_api.ASSISTANT_RUNTIME, "observe_assistant_reply", lambda *args, **kwargs: None),
            patch.object(web_api, "observe_user_turn", lambda *args, **kwargs: None),
            patch.object(web_api, "record_assistant_turn", lambda *args, **kwargs: {"id": "interaction-1"}),
            patch.object(web_api, "record_mood_from_analysis", lambda *args, **kwargs: {"last_mood": "neutral"}),
            patch.object(web_api, "analyze_emotion", lambda *_args, **_kwargs: {"emotion": "neutral"}),
            patch.object(web_api, "validate_prompt_text", lambda *args, **kwargs: {"allowed": True}),
            patch.object(web_api, "answer_if_confident", lambda *args, **kwargs: None),
            patch.object(web_api, "_looks_like_direct_action_input", lambda *args, **kwargs: False),
            patch.object(web_api, "generate_chat_reply", return_value="Python is a programming language."),
        ]
        original_sessions = dict(web_api._chat_sessions)
        original_order = list(web_api._session_order)
        web_api._chat_sessions.clear()
        web_api._session_order.clear()
        try:
            for item in patches:
                item.start()
            response = TestClient(web_api.app).post("/chat", json={"message": "what is python?"})
        finally:
            for item in reversed(patches):
                item.stop()
            web_api._chat_sessions.clear()
            web_api._chat_sessions.update(original_sessions)
            web_api._session_order[:] = original_order

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["reply"], "Python is a programming language.")
        self.assertIn("session", payload)


if __name__ == "__main__":
    unittest.main()
