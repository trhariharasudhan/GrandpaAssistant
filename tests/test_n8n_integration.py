import os
import sys
import unittest
import urllib.error
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from api import chat_api, web_api
from core import command_router
from backend.app.integrations import n8n_client


class FakeResponse:
    def __init__(self, status=200, body=b'{"received":true}'):
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._body


class N8nClientTests(unittest.TestCase):
    def test_send_n8n_message_posts_json_and_parses_response(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = request.data.decode("utf-8")
            captured["timeout"] = timeout
            return FakeResponse(body=b'{"ok":true}')

        with patch.object(n8n_client.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = n8n_client.send_n8n_message(
                "hello",
                channel="voice",
                raw_command="trigger n8n hello",
                webhook_url="http://n8n.local/webhook",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["data"], {"ok": True})
        self.assertEqual(captured["url"], "http://n8n.local/webhook")
        self.assertIn('"message": "hello"', captured["body"])
        self.assertIn('"source": "GrandpaAssistant"', captured["body"])
        self.assertIn('"channel": "voice"', captured["body"])
        self.assertIn('"raw_command": "trigger n8n hello"', captured["body"])
        self.assertEqual(captured["timeout"], 10)

    def test_send_n8n_message_returns_structured_failure_when_offline(self) -> None:
        with patch.object(n8n_client.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
            result = n8n_client.send_n8n_message("hello")

        self.assertFalse(result["ok"])
        self.assertIsNone(result["status_code"])
        self.assertIn("unavailable", result["data"]["message"])


class N8nApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.patches = [
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
        ]
        for item in self.patches:
            item.start()
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()

    def test_n8n_test_route_forwards_message(self) -> None:
        expected = {"ok": True, "status_code": 200, "data": {"received": True}}
        with patch.object(web_api, "send_n8n_message", return_value=expected) as mocked:
            response = self.client.post("/api/automation/n8n/test", json={"message": "hello"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        mocked.assert_called_once_with("hello")

    def test_n8n_test_route_rejects_empty_message(self) -> None:
        response = self.client.post("/api/automation/n8n/test", json={"message": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Message is required", response.text)

    def test_n8n_test_route_blocks_remote_unauthenticated_clients(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.20", 50000))

        response = remote_client.post("/api/automation/n8n/test", json={"message": "hello"})

        self.assertEqual(response.status_code, 403)


class N8nChatApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(chat_api.app)

    def test_n8n_test_route_available_on_chat_api_port_shape(self) -> None:
        expected = {"ok": True, "status_code": 200, "data": {"received": True}}
        with patch.object(chat_api, "send_n8n_message", return_value=expected) as mocked:
            response = self.client.post("/api/automation/n8n/test", json={"message": "hello"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        mocked.assert_called_once_with("hello")


class N8nCommandRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        command_router.pending_confirmation = None
        command_router.pending_confirmations.clear()
        self.spoken = []
        self.speak_patch = patch.object(
            command_router,
            "speak",
            side_effect=lambda message, *args, **kwargs: self.spoken.append(message),
        )
        self.speak_patch.start()

    def tearDown(self) -> None:
        self.speak_patch.stop()
        command_router.pending_confirmation = None
        command_router.pending_confirmations.clear()

    def test_trigger_phrase_detection(self) -> None:
        result = command_router.detect_n8n_automation_intent("trigger n8n hello from voice")

        self.assertTrue(result["matched"])
        self.assertEqual(result["message"], "hello from voice")

    def test_command_router_sends_successful_n8n_call(self) -> None:
        with patch.object(command_router, "send_n8n_message", return_value={"ok": True}) as mocked:
            command_router.process_command("trigger n8n hello from voice", {}, input_mode="voice")

        mocked.assert_called_once_with(
            "hello from voice",
            channel="voice",
            raw_command="trigger n8n hello from voice",
        )
        self.assertEqual(self.spoken[-1], "Automation sent to n8n successfully.")

    def test_command_router_reports_offline_n8n_failure(self) -> None:
        with patch.object(command_router, "send_n8n_message", return_value={"ok": False}) as mocked:
            command_router.process_command("send to n8n hello", {}, input_mode="text")

        mocked.assert_called_once()
        self.assertEqual(self.spoken[-1], "n8n automation is not available right now.")

    def test_normal_chat_is_not_sent_to_n8n(self) -> None:
        with patch.object(command_router, "send_n8n_message", return_value={"ok": True}) as mocked:
            command_router.process_command("what is your name", {}, input_mode="text")

        mocked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
