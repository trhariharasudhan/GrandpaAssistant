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


class ChatApiRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        chat_api.CHAT_HISTORY.clear()
        self.patches = [
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
            patch.object(chat_api, "mood_status_payload", lambda: {"last_mood": "neutral"}),
            patch.object(chat_api, "analyze_emotion", lambda *_args, **_kwargs: {"emotion": "neutral"}),
            patch.object(chat_api, "validate_prompt_text", lambda *args, **kwargs: {"allowed": True}),
            patch.object(chat_api, "answer_if_confident", lambda *args, **kwargs: None),
            patch.object(chat_api, "route_request", lambda *args, **kwargs: {"mode": "auto", "reason": "test"}),
            patch.object(chat_api, "build_semantic_memory_context", lambda *_args, **_kwargs: ""),
            patch.object(chat_api, "build_emotion_prompt_context", lambda *_args, **_kwargs: ""),
            patch.object(chat_api, "build_mood_memory_context", lambda *_args, **_kwargs: ""),
            patch.object(chat_api, "build_intelligence_prompt_boost", lambda *_args, **_kwargs: ""),
        ]
        for item in self.patches:
            item.start()
        self.client = TestClient(chat_api.app)

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        chat_api.CHAT_HISTORY.clear()

    def test_chat_rejects_empty_message(self) -> None:
        response = self.client.post("/chat", json={"message": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Message is required", response.text)

    def test_chat_sanitizes_echo_from_legacy_provider(self) -> None:
        with patch.object(chat_api, "generate_chat_reply", return_value="User question: what is python?"):
            response = self.client.post("/chat", json={"message": "what is python?"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("could not generate", response.json()["reply"].lower())

    def test_chat_stream_does_not_emit_exact_echo_chunk(self) -> None:
        with patch.object(chat_api, "stream_chat_reply", return_value=iter(["what is python?"])):
            with self.client.stream("POST", "/chat/stream", json={"message": "what is python?"}) as response:
                body = response.read().decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("could not generate", body.lower())
        self.assertNotIn('"content": "what is python?"', body.lower())


if __name__ == "__main__":
    unittest.main()
