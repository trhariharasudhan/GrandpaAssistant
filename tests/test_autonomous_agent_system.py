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


from api import autonomous_agent_api
from autonomous_agent.manager import AutonomousAgentManager
from autonomous_agent.state import ContextManager


class AutonomousAgentSystemTests(unittest.TestCase):
    def test_goal_planner_decomposes_food_and_cab_with_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AutonomousAgentManager(context_manager=ContextManager(os.path.join(temp_dir, "tasks.json")))
            food = manager.plan_goal("I am hungry")
            cab = manager.plan_goal("Book a cab home")

        self.assertEqual("ask_food_preference", food["graph"]["nodes"][0]["node_id"])
        self.assertTrue(any(node["requires_confirmation"] for node in food["graph"]["nodes"]))
        self.assertTrue(any(node["tool_name"] == "browser_automation" for node in cab["graph"]["nodes"]))

    def test_run_next_step_pauses_for_user_or_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AutonomousAgentManager(context_manager=ContextManager(os.path.join(temp_dir, "tasks.json")))
            planned = manager.plan_goal("Send today's report to manager")

            first = manager.run_next_step(planned["task"]["task_id"])
            second = manager.run_next_step(planned["task"]["task_id"])

        self.assertIn(first["status"], {"running", "waiting_for_user", "waiting_for_approval"})
        self.assertIn(second["status"], {"waiting_for_approval", "running", "waiting_for_details"})

    def test_stream_goal_reports_progress_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AutonomousAgentManager(context_manager=ContextManager(os.path.join(temp_dir, "tasks.json")))
            events = list(manager.stream_goal("Prepare meeting notes"))

        self.assertEqual("planned", events[0]["type"])
        self.assertIn(events[-1]["type"], {"paused", "done"})

    def test_agent_api_uses_manager(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AutonomousAgentManager(context_manager=ContextManager(os.path.join(temp_dir, "tasks.json")))
            app = FastAPI()
            app.include_router(autonomous_agent_api.router)
            with patch.object(autonomous_agent_api, "_manager", return_value=manager):
                client = TestClient(app)
                response = client.post("/api/agent/plan", json={"goal": "Book a cab home"})

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["ok"])
        self.assertIn("graph", response.json())


if __name__ == "__main__":
    unittest.main()
