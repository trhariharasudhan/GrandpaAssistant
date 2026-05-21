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
SHARED_DIR = APP_DIR / "shared"
for path in (ROOT, APP_DIR, SHARED_DIR):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from api import browser_automation_api
from browser_automation.config import BrowserAutomationConfig
from browser_automation.executor import BrowserExecutor
from browser_automation.memory import BrowserMemory
from browser_automation.planner import BrowserActionPlanner
from browser_automation.safety import BrowserSafetyLayer
from browser_automation.service import BrowserAutomationService
from browser_automation.session_manager import BrowserSession


class FakeLocator:
    def __init__(self, page, selector=""):
        self.page = page
        self.selector = selector

    @property
    def first(self):
        return self

    def click(self, **_kwargs):
        self.page.actions.append(("click",))

    def fill(self, value):
        self.page.actions.append(("fill", value))

    def set_input_files(self, file_path):
        self.page.actions.append(("upload", self.selector, file_path))

    def inner_text(self, **_kwargs):
        return "Example page content with product list and useful structured data."


class FakePage:
    def __init__(self):
        self.url = ""
        self.actions = []

    def goto(self, url, **_kwargs):
        self.url = url
        self.actions.append(("goto", url))

    def locator(self, selector):
        return FakeLocator(self, selector)

    def title(self):
        return "Example Title"

    def screenshot(self, path, **_kwargs):
        Path(path).write_bytes(b"PNG")


class FakeSessionManager:
    def __init__(self):
        self.page = FakePage()
        self.closed = []

    def get_or_create_session(self, *, session_id=None, browser=None):
        return BrowserSession(session_id=session_id or "fake-session", browser=browser or "chrome", page=self.page, profile_dir="fake")

    def close_session(self, session_id):
        self.closed.append(session_id)
        return True

    def status(self):
        return {"ok": True, "playwright_available": True, "session_count": 1, "sessions": [{"session_id": "fake-session"}]}


class BrowserAutomationEngineTests(unittest.TestCase):
    def test_planner_maps_real_world_browser_tasks(self) -> None:
        planner = BrowserActionPlanner()

        cab = planner.build_plan("Book a cab to airport")
        food = planner.build_plan("Order food from Swiggy")
        youtube = planner.build_plan("Open YouTube and play relaxing music")
        linkedin = planner.build_plan("Login to LinkedIn and apply job filters for python developer")

        self.assertEqual("book_cab", cab["intent"])
        self.assertTrue(cab["requires_confirmation"])
        self.assertEqual("order_food", food["intent"])
        self.assertEqual("play_media", youtube["intent"])
        self.assertIn("youtube.com", youtube["url"])
        self.assertEqual("apply_job_filters", linkedin["intent"])

    def test_safety_requires_confirmation_for_dangerous_browser_actions(self) -> None:
        plan = BrowserActionPlanner().build_plan("Order food from Zomato")
        safety = BrowserSafetyLayer()

        decision = safety.assert_safe(plan, confirmed=False)
        confirmed = safety.assert_safe(plan, confirmed=True)

        self.assertFalse(decision["ok"])
        self.assertTrue(decision["safety"]["requires_confirmation"])
        self.assertTrue(confirmed["ok"])

    def test_executor_runs_safe_plan_with_fake_page_and_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = BrowserMemory(path=os.path.join(temp_dir, "memory.json"))
            manager = FakeSessionManager()
            config = BrowserAutomationConfig(human_delay_ms=0, retry_attempts=1)
            executor = BrowserExecutor(session_manager=manager, memory=memory, config=config)
            plan = BrowserActionPlanner().build_plan("Open YouTube and play music")

            result = executor.execute_plan(plan, session_id="fake-session", confirmed=False)

            self.assertTrue(result["executed"])
            self.assertTrue(manager.page.actions)
            self.assertIn("youtube.com", result["page"]["url"])
            self.assertEqual(1, memory.status()["recent_task_count"])

    def test_executor_reports_missing_playwright_adapter_without_crashing(self) -> None:
        class MissingSessionManager:
            def get_or_create_session(self, **kwargs):
                return BrowserSession(session_id="missing", browser="chrome", page=None, profile_dir="fake")

        executor = BrowserExecutor(session_manager=MissingSessionManager())

        result = executor.execute_plan(BrowserActionPlanner().build_plan("search browser automation"), session_id="missing")

        self.assertFalse(result["ok"])
        self.assertEqual("playwright", result["missing_adapter"])

    def test_executor_supports_upload_step_with_safe_file_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_path = os.path.join(temp_dir, "resume.txt")
            Path(upload_path).write_text("safe test file", encoding="utf-8")
            manager = FakeSessionManager()
            config = BrowserAutomationConfig(human_delay_ms=0, retry_attempts=1)
            executor = BrowserExecutor(session_manager=manager, config=config)
            plan = {
                "goal": "Upload a resume",
                "intent": "upload_file",
                "browser": "chrome",
                "steps": [{"action": "upload", "selector": "input[type=file]", "file_path": upload_path}],
            }

            result = executor.execute_plan(plan, session_id="fake-session", confirmed=False)

            self.assertTrue(result["ok"])
            self.assertEqual("resume.txt", result["events"][0]["file_name"])
            self.assertIn(("upload", "input[type=file]", upload_path), manager.page.actions)

    def test_executor_supports_safe_form_fill_steps(self) -> None:
        manager = FakeSessionManager()
        config = BrowserAutomationConfig(human_delay_ms=0, retry_attempts=1)
        executor = BrowserExecutor(session_manager=manager, config=config)
        plan = {
            "goal": "Fill a search form",
            "intent": "fill_form",
            "browser": "chrome",
            "steps": [{"action": "fill_form", "fields": {"input[name=q]": "browser automation"}}],
        }

        result = executor.execute_plan(plan, session_id="fake-session", confirmed=False)

        self.assertTrue(result["ok"])
        self.assertEqual(["input[name=q]"], result["events"][0]["filled_fields"])
        self.assertIn(("fill", "browser automation"), manager.page.actions)

    def test_sensitive_form_fields_require_confirmation(self) -> None:
        plan = {
            "goal": "Log in to a website",
            "intent": "login",
            "steps": [{"action": "fill_form", "fields": {"input[name=password]": "secret"}}],
        }

        decision = BrowserSafetyLayer().assert_safe(plan, confirmed=False)

        self.assertFalse(decision["ok"])
        self.assertIn("password", decision["safety"]["sensitive_fields"])

    def test_service_stream_stops_for_confirmation(self) -> None:
        service = BrowserAutomationService(session_manager=FakeSessionManager())

        events = list(service.stream("Book a cab", session_id="safe", confirmed=False))

        self.assertEqual("confirmation_required", events[-1]["type"])


class BrowserAutomationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(browser_automation_api.router)
        self.client = TestClient(app)

    def test_plan_endpoint_uses_service(self) -> None:
        fake_service = BrowserAutomationService(session_manager=FakeSessionManager())
        with patch.object(browser_automation_api, "_service", return_value=fake_service):
            response = self.client.post("/api/browser/plan", json={"request": "Open YouTube and play music"})

        self.assertEqual(200, response.status_code)
        self.assertEqual("play_media", response.json()["plan"]["intent"])

    def test_execute_endpoint_respects_confirmation(self) -> None:
        fake_service = BrowserAutomationService(session_manager=FakeSessionManager())
        with patch.object(browser_automation_api, "_service", return_value=fake_service):
            response = self.client.post("/api/browser/execute", json={"request": "Order food", "confirmed": False})

        self.assertEqual(200, response.status_code)
        self.assertFalse(response.json()["ok"])
        self.assertTrue(response.json()["safety"]["requires_confirmation"])

    def test_stream_endpoint_returns_sse(self) -> None:
        fake_service = BrowserAutomationService(session_manager=FakeSessionManager())
        with patch.object(browser_automation_api, "_service", return_value=fake_service):
            with self.client.stream("POST", "/api/browser/stream", json={"request": "Open YouTube and play music"}) as response:
                body = response.read().decode("utf-8")

        self.assertEqual(200, response.status_code)
        self.assertIn("data:", body)
        self.assertIn("plan", body)


if __name__ == "__main__":
    unittest.main()
