import json
import sys
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
for path in (ROOT, APP_DIR, APP_DIR / "shared"):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from api.local_action_orchestrator_api import router
from local_action_orchestrator.orchestrator import LocalActionOrchestrator


class LocalActionOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = LocalActionOrchestrator()

    def assertDomain(self, command: str, expected: str) -> dict:
        plan = self.orchestrator.plan(command)
        self.assertEqual(expected, plan["detected_domain"], plan)
        self.assertIn("command", plan)
        self.assertIn("confidence", plan)
        self.assertIn("plan_steps", plan)
        self.assertIn("next_action", plan)
        json.dumps(plan)
        return plan

    def test_browser_search_command_routes_to_browser(self) -> None:
        plan = self.assertDomain("open browser and search laptops", "browser")

        self.assertFalse(plan["requires_confirmation"])
        self.assertEqual("safe_local_action", plan["risk_level"])
        self.assertEqual("safe_to_execute_after_user_review", plan["next_action"])

    def test_chat_send_command_requires_confirmation(self) -> None:
        plan = self.assertDomain("send message to Riya that I will call later", "chat")

        self.assertTrue(plan["requires_confirmation"])
        self.assertEqual("medium_confirmation", plan["risk_level"])
        self.assertEqual("ask_approval_or_missing_contact_details", plan["next_action"])

    def test_tanglish_screen_command_routes_to_visual_desktop(self) -> None:
        plan = self.assertDomain("screen la enna iruku paaru", "visual_desktop")

        self.assertFalse(plan["requires_confirmation"])
        self.assertEqual("safe_local_action", plan["risk_level"])

    def test_ticket_booking_routes_to_agent_with_high_confirmation(self) -> None:
        plan = self.assertDomain("book train ticket tomorrow", "autonomous_agent")

        self.assertTrue(plan["requires_confirmation"])
        self.assertEqual("high_confirmation", plan["risk_level"])
        self.assertEqual("create_task_graph_and_wait_for_confirmation", plan["next_action"])

    def test_greeting_routes_to_general(self) -> None:
        plan = self.assertDomain("hi da", "general")

        self.assertFalse(plan["requires_confirmation"])
        self.assertEqual("safe_read", plan["risk_level"])
        self.assertEqual("normal_chat_response", plan["next_action"])

    def test_api_plan_endpoint(self) -> None:
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.post("/api/local-actions/plan", json={"command": "summarize unread messages"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertEqual("chat", payload["detected_domain"])
        self.assertTrue(payload["requires_confirmation"])


if __name__ == "__main__":
    unittest.main()
