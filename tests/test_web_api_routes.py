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


class WebApiRouteRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_sessions = dict(web_api._chat_sessions)
        self.original_order = list(web_api._session_order)
        self.original_confirmations = dict(web_api._pending_confirmations)
        web_api._chat_sessions.clear()
        web_api._session_order.clear()
        web_api._pending_confirmations.clear()

        self.patches = [
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
            patch.object(web_api, "_enforce_app_auth", lambda request: None),
            patch.object(web_api, "_save_chat_state", lambda: None),
            patch.object(web_api, "upsert_chat_session", lambda *args, **kwargs: None),
            patch.object(web_api, "append_chat_message", lambda *args, **kwargs: None),
            patch.object(web_api, "log_audit_event", lambda *args, **kwargs: None),
            patch.object(web_api.MOBILE_COMPANION, "record_chat_message", lambda *args, **kwargs: None),
            patch.object(web_api.MOBILE_COMPANION, "record_command_result", lambda *args, **kwargs: None),
            patch.object(web_api.ASSISTANT_RUNTIME, "start", lambda: None),
            patch.object(web_api.ASSISTANT_RUNTIME, "status_payload", lambda: {"running": True}),
            patch.object(web_api.ASSISTANT_RUNTIME, "observe_user_message", lambda *args, **kwargs: {"context": "casual"}),
            patch.object(web_api.ASSISTANT_RUNTIME, "observe_assistant_reply", lambda *args, **kwargs: None),
            patch.object(web_api, "observe_user_turn", lambda *args, **kwargs: None),
            patch.object(web_api, "record_assistant_turn", lambda *args, **kwargs: {"id": "interaction-1"}),
            patch.object(web_api, "record_mood_from_analysis", lambda *args, **kwargs: {"last_mood": "neutral"}),
            patch.object(web_api, "mood_status_payload", lambda: {"last_mood": "neutral"}),
            patch.object(web_api, "analyze_emotion", lambda *_args, **_kwargs: {"emotion": "neutral"}),
            patch.object(web_api, "validate_prompt_text", lambda *args, **kwargs: {"allowed": True}),
            patch.object(web_api, "answer_if_confident", lambda *args, **kwargs: None),
            patch.object(web_api, "_looks_like_direct_action_input", lambda *args, **kwargs: False),
            patch.object(web_api, "build_semantic_memory_context", lambda *_args, **_kwargs: ""),
            patch.object(web_api, "build_emotion_prompt_context", lambda *_args, **_kwargs: ""),
            patch.object(web_api, "build_mood_memory_context", lambda *_args, **_kwargs: ""),
            patch.object(web_api, "build_intelligence_prompt_boost", lambda *_args, **_kwargs: ""),
            patch.object(web_api, "semantic_memory_status", lambda **kwargs: {"ready": True}),
            patch.object(web_api, "collect_startup_diagnostics", lambda **kwargs: {"ok": True, "items": []}),
            patch.object(web_api, "_build_ui_state", lambda *args, **kwargs: {"test": True}),
        ]
        for item in self.patches:
            item.start()
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        web_api._chat_sessions.clear()
        web_api._chat_sessions.update(self.original_sessions)
        web_api._session_order[:] = self.original_order
        web_api._pending_confirmations.clear()
        web_api._pending_confirmations.update(self.original_confirmations)

    def test_health_route_reports_backend_service(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "grandpa-assistant-api")

    def test_cors_rejects_non_localhost_origin(self) -> None:
        response = self.client.options(
            "/api/health",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotEqual(response.headers.get("access-control-allow-origin"), "https://example.com")

    def test_chat_route_sanitizes_model_echo(self) -> None:
        with patch.object(web_api, "generate_chat_reply", return_value="User question: what is python?"):
            response = self.client.post("/chat", json={"message": "what is python?"})
        self.assertEqual(response.status_code, 200)
        reply = response.json()["reply"]
        self.assertNotEqual(reply.lower(), "user question: what is python?")
        self.assertIn("couldn't get an answer", reply.lower())

    def test_chat_route_rejects_empty_message(self) -> None:
        response = self.client.post("/chat", json={"message": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Message is required", response.text)

    def test_chat_stream_rejects_empty_message(self) -> None:
        response = self.client.post("/chat/stream", json={"message": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Message is required", response.text)

    def test_chat_stream_sanitizes_final_echo_message(self) -> None:
        with patch.object(web_api, "stream_chat_reply", return_value=iter(["what is python?"])):
            with self.client.stream("POST", "/chat/stream", json={"message": "what is python?"}) as response:
                body = response.read().decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("could not generate", body.lower())
        self.assertNotIn('"content": "what is python?"', body.lower())

    def test_upload_remove_targets_one_document_at_a_time(self) -> None:
        session_id = "session-docs"
        first = self.client.post(
            "/chat/upload",
            data={"session_id": session_id},
            files={"file": ("alpha.txt", b"alpha content", "text/plain")},
        )
        second = self.client.post(
            "/chat/upload",
            data={"session_id": session_id},
            files={"file": ("beta.txt", b"beta content", "text/plain")},
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        removed = self.client.post(
            "/chat/upload/remove",
            json={"session_id": session_id, "filename": "alpha.txt"},
        )
        self.assertEqual(removed.status_code, 200)
        names = [item["name"] for item in removed.json()["documents"]]
        self.assertEqual(names, ["beta.txt"])

    def test_command_confirmations_are_independent_by_id(self) -> None:
        first = self.client.post("/api/command", json={"command": "delete alpha file"})
        second = self.client.post("/api/command", json={"command": "delete beta file"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_id = first.json()["confirmation_id"]
        second_id = second.json()["confirmation_id"]
        self.assertNotEqual(first_id, second_id)
        self.assertIn(first_id, web_api._pending_confirmations)
        self.assertIn(second_id, web_api._pending_confirmations)

        with patch.object(web_api, "_capture_command_reply", return_value=["alpha deleted"]):
            confirmed = self.client.post(
                "/api/command",
                json={"command": "", "confirmation_id": first_id},
            )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["messages"], ["alpha deleted"])
        self.assertNotIn(first_id, web_api._pending_confirmations)
        self.assertIn(second_id, web_api._pending_confirmations)


if __name__ == "__main__":
    unittest.main()
