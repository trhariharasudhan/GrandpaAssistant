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
        self.original_cancelled_streams = set(web_api._cancelled_streams)
        web_api._chat_sessions.clear()
        web_api._session_order.clear()
        web_api._pending_confirmations.clear()
        web_api._cancelled_streams.clear()

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
        web_api._cancelled_streams.clear()
        web_api._cancelled_streams.update(self.original_cancelled_streams)

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

    def test_chat_history_returns_current_session_payload(self) -> None:
        session = web_api._ensure_session(session_id="session-history", title="History")
        session["messages"].append({"role": "user", "content": "hello"})

        response = self.client.get("/chat/history", params={"session_id": "session-history"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["session"]["id"], "session-history")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "hello"}])
        self.assertEqual(payload["sessions"][0]["id"], "session-history")

    def test_chat_session_rename_preserves_response_shape(self) -> None:
        web_api._ensure_session(session_id="session-rename", title="Old title")

        response = self.client.post(
            "/chat/sessions/rename",
            json={"session_id": "session-rename", "title": "New title"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["session"]["id"], "session-rename")
        self.assertEqual(payload["session"]["title"], "New title")
        self.assertEqual(payload["sessions"][0]["title"], "New title")

    def test_chat_session_rename_missing_session_returns_404(self) -> None:
        response = self.client.post(
            "/chat/sessions/rename",
            json={"session_id": "missing", "title": "New title"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("Session not found", response.text)

    def test_chat_session_delete_removes_target_and_returns_current_session(self) -> None:
        web_api._ensure_session(session_id="keep-session", title="Keep")
        web_api._ensure_session(session_id="delete-session", title="Delete")

        response = self.client.post("/chat/sessions/delete", json={"session_id": "delete-session"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["current_session_id"], "keep-session")
        self.assertEqual([item["id"] for item in payload["sessions"]], ["keep-session"])
        self.assertNotIn("delete-session", web_api._chat_sessions)

    def test_chat_session_delete_missing_session_returns_404(self) -> None:
        response = self.client.post("/chat/sessions/delete", json={"session_id": "missing"})

        self.assertEqual(response.status_code, 404)
        self.assertIn("Session not found", response.text)

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

    def test_upload_remove_rejects_missing_document(self) -> None:
        session_id = "session-missing-doc"
        uploaded = self.client.post(
            "/chat/upload",
            data={"session_id": session_id},
            files={"file": ("alpha.txt", b"alpha content", "text/plain")},
        )
        self.assertEqual(uploaded.status_code, 200)

        removed = self.client.post(
            "/chat/upload/remove",
            json={"session_id": session_id, "filename": "missing.txt"},
        )

        self.assertEqual(removed.status_code, 404)
        self.assertIn("Document not found", removed.text)

    def test_export_chat_preserves_markdown_payload_shape(self) -> None:
        session = web_api._ensure_session(session_id="session-export", title="Export Me")
        session["messages"] = [
            {"role": "user", "content": "hello", "created_at": "2026-05-23T10:00:00"},
            {"role": "assistant", "content": "hi", "created_at": "2026-05-23T10:00:01"},
        ]

        response = self.client.get("/chat/export", params={"session_id": "session-export"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["session"], {"id": "session-export", "title": "Export Me"})
        self.assertEqual(payload["filename"], "export_me.md")
        self.assertIn("# Export Me", payload["content"])
        self.assertIn("[2026-05-23T10:00:00] You: hello", payload["content"])
        self.assertIn("[2026-05-23T10:00:01] Grandpa: hi", payload["content"])

    def test_export_chat_missing_session_returns_404(self) -> None:
        response = self.client.get("/chat/export", params={"session_id": "missing"})

        self.assertEqual(response.status_code, 404)
        self.assertIn("Session not found", response.text)

    def test_chat_reset_clears_messages_and_resets_clean_session(self) -> None:
        session = web_api._ensure_session(session_id="session-reset", title="Reset")
        session["messages"] = [{"role": "user", "content": "hello"}]

        with patch.object(web_api, "reset_clean_chat_session") as reset_clean:
            response = self.client.post("/chat/reset", params={"session_id": "session-reset"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        self.assertEqual(web_api._chat_sessions["session-reset"]["messages"], [])
        reset_clean.assert_called_once_with("session-reset")

    def test_chat_cancel_marks_session_stream_cancelled(self) -> None:
        response = self.client.post("/chat/cancel", json={"session_id": "session-stream"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        self.assertIn("session-stream", web_api._cancelled_streams)

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
