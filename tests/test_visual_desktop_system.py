import sys
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


from api import visual_desktop_api
from visual_desktop.service import VisualDesktopService


class FakeCapture:
    def capture(self, *, include_image=False):
        return {"ok": True, "monitor_count": 1, "active_window": {"app_name": "Browser", "title": "Login"}}


class FakeOCR:
    def extract_text(self, capture=None):
        return {"ok": True, "summary": "Login page with Login and Cancel buttons", "text": "Email\nPassword\nLogin\nCancel", "lines": ["Email", "Password", "Login", "Cancel"]}


class VisualDesktopSystemTests(unittest.TestCase):
    def test_analyze_screen_detects_buttons_without_image_dump(self) -> None:
        service = VisualDesktopService(capture=FakeCapture(), ocr=FakeOCR())

        result = service.analyze_screen()

        self.assertTrue(result["ok"])
        labels = [item["label"] for item in result["elements"]["elements"]]
        self.assertIn("Login", labels)
        self.assertNotIn("image_base64", result["capture"])

    def test_click_requires_confirmation_when_confidence_is_low(self) -> None:
        service = VisualDesktopService(capture=FakeCapture(), ocr=FakeOCR())

        result = service.plan_action("click the unknown button")

        self.assertFalse(result["ok"])
        self.assertTrue(result["result"].get("requires_confirmation") or "could not confidently" in result["result"]["message"].lower())

    def test_dangerous_visual_action_is_blocked(self) -> None:
        service = VisualDesktopService(capture=FakeCapture(), ocr=FakeOCR())

        result = service.plan_action("click submit and pay")

        self.assertTrue(result["result"].get("blocked"))

    def test_visual_api_returns_safe_status(self) -> None:
        service = VisualDesktopService(capture=FakeCapture(), ocr=FakeOCR())
        app = FastAPI()
        app.include_router(visual_desktop_api.router)
        with patch.object(visual_desktop_api, "_service", return_value=service):
            client = TestClient(app)
            response = client.post("/api/visual-desktop/analyze")

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["ok"])
        self.assertNotIn("image_base64", str(response.json()))


if __name__ == "__main__":
    unittest.main()
