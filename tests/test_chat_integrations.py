import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
for path in (ROOT, APP_DIR, APP_DIR / "shared"):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from api import chat_integrations_api
from chat_integrations.manager import ChatIntegrationManager
from chat_integrations.storage import MessageMemory


class ChatIntegrationTests(unittest.TestCase):
    def test_notification_parsing_and_encrypted_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = os.path.join(temp_dir, "messages.enc")
            manager = ChatIntegrationManager(memory=MessageMemory(memory_path))

            result = manager.ingest_notification("WhatsApp", "Riyaa: hello da", platform="whatsapp")

            self.assertTrue(result["ok"])
            self.assertEqual("Riyaa", result["message"]["contact"])
            raw = Path(memory_path).read_text(encoding="utf-8")
            self.assertNotIn("hello da", raw)
            self.assertTrue(manager.status()["memory"]["encrypted_at_rest"])

    def test_send_message_requires_approval_and_reports_missing_adapter(self) -> None:
        manager = ChatIntegrationManager(memory=MessageMemory(path=os.path.join(tempfile.gettempdir(), "ga-chat-test.enc")), approval_mode=True)

        draft = manager.send_message(platform="whatsapp", contact="Riyaa", text="Good morning")
        approved = manager.send_message(platform="whatsapp", contact="Riyaa", text="Good morning", approved=True)

        self.assertTrue(draft["requires_approval"])
        self.assertFalse(approved["ok"])
        self.assertEqual("whatsapp_web_playwright_adapter", approved["missing_adapter"])

    def test_summarize_unread_and_smart_reply_are_generalized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ChatIntegrationManager(memory=MessageMemory(os.path.join(temp_dir, "messages.enc")))
            manager.ingest_notification("Slack", "Work group: urgent build failed?", platform="slack")

            summary = manager.summarize_unread(platform="slack")
            replies = manager.suggest_replies(platform="slack", contact="work")

            self.assertGreaterEqual(summary["unread_count"], 1)
            self.assertTrue(any("prioritize" in item.lower() or "checking" in item.lower() for item in replies["suggestions"]))

    def test_api_routes_are_safe_and_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_manager = ChatIntegrationManager(memory=MessageMemory(os.path.join(temp_dir, "messages.enc")))
            app = FastAPI()
            app.include_router(chat_integrations_api.router)
            with patch.object(chat_integrations_api, "_manager", return_value=fake_manager):
                client = TestClient(app)
                parsed = client.post("/api/chat-integrations/notifications/parse", json={"title": "Telegram", "body": "Family: good morning", "platform": "telegram"})
                send = client.post("/api/chat-integrations/messages/send", json={"platform": "telegram", "contact": "Family", "text": "Good morning"})

            self.assertEqual(200, parsed.status_code)
            self.assertEqual(200, send.status_code)
            self.assertTrue(send.json()["requires_approval"])
            json.dumps(parsed.json())


if __name__ == "__main__":
    unittest.main()
