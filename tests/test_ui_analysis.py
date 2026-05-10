import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(ROOT, "backend")
APP_DIR = os.path.join(BACKEND_DIR, "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [BACKEND_DIR, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from app.api import web_api
from app.features.ui_analysis import action_planner, screen_capture, ui_action_executor, ui_element_detector
from core import command_router


class FakeScreenshot:
    size = (640, 480)

    def save(self, path):
        with open(path, "wb") as file:
            file.write(b"fake-png")

    def __array__(self, dtype=None):
        try:
            import numpy as np

            return np.zeros((480, 640, 3), dtype=dtype or "uint8")
        except Exception:
            return []


class UIAnalysisTests(unittest.TestCase):
    def test_screenshot_capture_saves_under_runtime_screenshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(screen_capture, "SCREENSHOT_DIR", temp_dir), \
                patch.object(screen_capture, "pyautogui") as mocked_pyautogui:
                mocked_pyautogui.screenshot.return_value = FakeScreenshot()

                result = screen_capture.capture_current_screen()

            self.assertTrue(result["ok"])
            self.assertTrue(result["image_path"].startswith(temp_dir))
            self.assertTrue(os.path.exists(result["image_path"]))
            self.assertIn("shape", result)

    def test_ocr_extraction_result_is_structured(self) -> None:
        fake_elements = [
            {"type": "button", "label": "Submit", "bbox": [10, 20, 80, 30], "confidence": 0.9, "source": "ocr"}
        ]
        with patch.object(ui_element_detector, "_ocr_elements_from_image", return_value=(fake_elements, "Submit")):
            result = ui_element_detector.detect_ui_elements(image_path="screen.png")

        self.assertTrue(result["ok"])
        self.assertEqual(result["elements"][0]["label"], "Submit")
        self.assertEqual(result["elements"][0]["type"], "button")

    def test_action_planning_selects_matching_button(self) -> None:
        result = action_planner.build_action_plan(
            "click submit",
            [{"type": "button", "label": "Submit", "bbox": [10, 20, 80, 30], "confidence": 0.9}],
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["plans"][0]["action"], "click")
        self.assertIn("Submit", result["plans"][0]["target"])
        self.assertFalse(result["plans"][0]["blocked"])

    def test_dangerous_action_is_blocked(self) -> None:
        result = action_planner.build_action_plan(
            "click delete",
            [{"type": "button", "label": "Delete", "bbox": [10, 20, 80, 30], "confidence": 0.9}],
        )

        self.assertTrue(result["plans"][0]["blocked"])
        self.assertTrue(result["plans"][0]["requires_confirmation"])
        self.assertIn("blocked", result["plans"][0]["reason"].lower())

    def test_low_confidence_action_is_rejected(self) -> None:
        result = action_planner.build_action_plan(
            "click submit",
            [{"type": "button", "label": "Unrelated", "bbox": [10, 20, 80, 30], "confidence": 0.9}],
        )

        self.assertEqual(result["plans"], [])

    def test_ui_executor_clicks_center_of_bbox(self) -> None:
        with patch.object(ui_action_executor, "pyautogui") as mocked_pyautogui:
            result = ui_action_executor.execute_ui_action(
                {
                    "action": "click",
                    "target": "Login button",
                    "bbox": [10, 20, 100, 40],
                    "confidence": 0.9,
                }
            )

        self.assertTrue(result["ok"])
        mocked_pyautogui.click.assert_called_once_with(60, 40)

    def test_ui_executor_blocks_dangerous_action(self) -> None:
        with patch.object(ui_action_executor, "pyautogui") as mocked_pyautogui:
            result = ui_action_executor.execute_ui_action(
                {
                    "action": "click",
                    "target": "Delete button",
                    "bbox": [10, 20, 100, 40],
                    "confidence": 0.95,
                }
            )

        self.assertFalse(result["ok"])
        mocked_pyautogui.click.assert_not_called()


class UIAnalysisApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(web_api.app)

    def test_ui_plan_route_returns_plan(self) -> None:
        response = self.client.post(
            "/api/ui/plan",
            json={
                "request": "click submit",
                "elements": [{"type": "button", "label": "Submit", "bbox": [0, 0, 80, 30]}],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["plans"])

    def test_ui_routes_are_remote_protected(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.40", 50000))

        response = remote_client.post("/api/ui/plan", json={"request": "click submit", "elements": []})

        self.assertEqual(response.status_code, 403)


class UIAnalysisCommandRouterTests(unittest.TestCase):
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
        self.capture_patch = patch.object(
            command_router,
            "capture_current_screen",
            return_value={"ok": True, "image_path": "screen.png", "image_array": object()},
        )
        self.capture_patch.start()

    def tearDown(self) -> None:
        self.capture_patch.stop()
        self.speak_patch.stop()
        command_router._clear_pending_ui_action()
        command_router.pending_confirmation = None
        command_router.pending_confirmations.clear()

    def _elements(self):
        return [
            {"type": "browser_region", "label": "https://example.com", "bbox": [0, 0, 900, 80], "confidence": 0.8},
            {"type": "text_field", "label": "Email", "bbox": [100, 200, 300, 40], "confidence": 0.8},
            {"type": "button", "label": "Submit", "bbox": [700, 620, 120, 40], "confidence": 0.9},
            {"type": "button", "label": "Login", "bbox": [600, 500, 120, 40], "confidence": 0.9},
        ]

    def test_screen_analysis_command_detected(self) -> None:
        with patch.object(command_router, "detect_ui_elements", return_value={"ok": True, "elements": self._elements()}):
            command_router.process_command("analyze my screen", {}, input_mode="text")

        self.assertIn("browser", self.spoken[-1].lower())
        self.assertIn("button", self.spoken[-1].lower())

    def test_find_on_screen_reports_matching_element(self) -> None:
        with patch.object(command_router, "detect_ui_elements", return_value={"ok": True, "elements": self._elements()}):
            command_router.process_command("where is the submit button", {}, input_mode="text")

        self.assertIn("Submit", self.spoken[-1])
        self.assertIn("bottom right", self.spoken[-1])

    def test_normal_chat_unaffected_by_ui_analysis_detection(self) -> None:
        self.assertFalse(command_router._handle_ui_analysis_command("where is my project folder"))
        self.assertFalse(command_router._handle_ui_analysis_command("what is python"))

    def test_dangerous_action_request_is_blocked(self) -> None:
        plan = {
            "plans": [
                {
                    "action": "click",
                    "target": "Delete button",
                    "confidence": 0.95,
                    "blocked": True,
                    "requires_confirmation": True,
                    "reason": "Dangerous UI action is blocked.",
                }
            ]
        }
        with patch.object(command_router, "detect_ui_elements", return_value={"ok": True, "elements": self._elements()}), \
            patch.object(command_router, "build_action_plan", return_value=plan):
            command_router.process_command("plan screen action click delete", {}, input_mode="text")

        self.assertIn("cannot safely", self.spoken[-1].lower())

    def test_low_confidence_action_is_not_executed(self) -> None:
        with patch.object(command_router, "detect_ui_elements", return_value={"ok": True, "elements": self._elements()}), \
            patch.object(command_router, "build_action_plan", return_value={"plans": []}):
            command_router.process_command("plan screen action click mystery thing", {}, input_mode="text")

        self.assertIn("could not create a safe", self.spoken[-1].lower())

    def test_pending_action_created(self) -> None:
        with patch.object(command_router, "detect_ui_elements", return_value={"ok": True, "elements": self._elements()}):
            command_router.process_command("click login button", {}, input_mode="text")

        self.assertIsNotNone(command_router._pending_ui_action)
        self.assertIn("Say confirm", self.spoken[-1])

    def test_confirm_executes_safe_click(self) -> None:
        with patch.object(command_router, "detect_ui_elements", return_value={"ok": True, "elements": self._elements()}), \
            patch.object(command_router, "execute_ui_action", return_value={"ok": True, "message": "Clicked Login button."}) as execute:
            command_router.process_command("click login button", {}, input_mode="text")
            command_router.process_command("confirm", {}, input_mode="text")

        execute.assert_called_once()
        self.assertIsNone(command_router._pending_ui_action)
        self.assertEqual(self.spoken[-1], "Clicked Login button.")

    def test_cancel_clears_pending_action(self) -> None:
        with patch.object(command_router, "detect_ui_elements", return_value={"ok": True, "elements": self._elements()}):
            command_router.process_command("click login button", {}, input_mode="text")
            command_router.process_command("cancel", {}, input_mode="text")

        self.assertIsNone(command_router._pending_ui_action)
        self.assertEqual(self.spoken[-1], "Screen action cancelled.")

    def test_expired_pending_action_rejected(self) -> None:
        with patch.object(command_router, "detect_ui_elements", return_value={"ok": True, "elements": self._elements()}):
            command_router.process_command("click login button", {}, input_mode="text")
        command_router._pending_ui_action["created_at"] -= 120

        command_router.process_command("confirm", {}, input_mode="text")

        self.assertIsNone(command_router._pending_ui_action)
        self.assertIn("expired", self.spoken[-1].lower())

    def test_confirm_without_pending_does_not_execute_ui_action(self) -> None:
        with patch.object(command_router, "execute_ui_action") as execute:
            handled = command_router._handle_pending_ui_action_response("confirm")

        self.assertFalse(handled)
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
