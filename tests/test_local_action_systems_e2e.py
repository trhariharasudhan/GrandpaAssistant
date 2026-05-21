import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
for path in (ROOT, APP_DIR, APP_DIR / "shared"):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from autonomous_agent.manager import AutonomousAgentManager
from autonomous_agent.state import ContextManager
from browser_automation.planner import BrowserActionPlanner
from browser_automation.safety import BrowserSafetyLayer
from chat_integrations.manager import ChatIntegrationManager
from chat_integrations.storage import MessageMemory
from visual_desktop.service import VisualDesktopService


class FakeCapture:
    def capture(self, *, include_image=False):
        return {"ok": True, "active_window": {"app_name": "Browser", "title": "WhatsApp"}, "image_included": include_image}


class FakeOCR:
    def extract_text(self, capture=None):
        return {"ok": True, "summary": "WhatsApp chat with Riyaa and a Reply button", "lines": ["Riyaa", "Good morning", "Reply"]}


class LocalActionSystemsE2ETests(unittest.TestCase):
    def test_mock_e2e_flow_across_chat_agent_visual_and_browser_systems(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            chat = ChatIntegrationManager(memory=MessageMemory(os.path.join(temp_dir, "messages.enc")))
            agent = AutonomousAgentManager(context_manager=ContextManager(os.path.join(temp_dir, "tasks.json")))
            visual = VisualDesktopService(capture=FakeCapture(), ocr=FakeOCR())
            browser_planner = BrowserActionPlanner()
            browser_safety = BrowserSafetyLayer()

            notification = chat.ingest_notification("WhatsApp", "Riyaa: Can you call later?", platform="whatsapp")
            summary = chat.summarize_unread(platform="whatsapp")
            reply = chat.send_message(platform="whatsapp", contact="Riyaa", text="I will call later")
            task = agent.plan_goal("I am hungry")
            screen = visual.plan_action("click reply")
            browser_plan = browser_planner.build_plan("Order food from Swiggy")
            safety = browser_safety.assert_safe(browser_plan, confirmed=False)

        self.assertTrue(notification["ok"])
        self.assertGreaterEqual(summary["unread_count"], 1)
        self.assertTrue(reply["requires_approval"])
        self.assertTrue(any(node["tool_name"] == "browser_automation" for node in task["graph"]["nodes"]))
        self.assertIn(screen["result"]["message"], {"Confirmation required before clicking this UI element.", "Planned click on Reply. Real UI clicking is approval-gated and adapter-driven."})
        self.assertFalse(safety["ok"])
        self.assertTrue(safety["safety"]["requires_confirmation"])


if __name__ == "__main__":
    unittest.main()
