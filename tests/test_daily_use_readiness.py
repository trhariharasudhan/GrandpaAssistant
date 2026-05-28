import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in [ROOT, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


import daily_use_readiness
from api import web_api
from api.routes import health as health_routes


def _available_modules(name: str) -> bool:
    return name in {"speech_recognition", "pyttsx3", "pytesseract", "playwright"}


class DailyUseReadinessTests(unittest.TestCase):
    def test_all_dependencies_available_mocked(self) -> None:
        with patch.object(daily_use_readiness, "_module_available", side_effect=_available_modules), \
            patch.object(daily_use_readiness, "_tesseract_candidates", return_value=[{"source": "configured_path", "path": "C:\\Tesseract\\tesseract.exe"}]), \
            patch.object(daily_use_readiness.Path, "exists", return_value=True), \
            patch.object(daily_use_readiness, "_playwright_version", return_value="Version 1.40.0"), \
            patch.object(
                daily_use_readiness,
                "_playwright_executable_paths",
                return_value={
                    "chromium": "C:\\ms-playwright\\chromium\\chrome.exe",
                    "firefox": "C:\\ms-playwright\\firefox\\firefox.exe",
                    "webkit": "C:\\ms-playwright\\webkit\\Playwright.exe",
                },
            ), \
            patch.dict(os.environ, {daily_use_readiness.VOICE_RUNTIME_ENV: "1"}, clear=False):
            payload = daily_use_readiness.collect_daily_use_readiness()

        self.assertTrue(payload["ok"])
        self.assertEqual("ok", payload["status"])
        self.assertEqual(0, payload["warnings_count"])
        self.assertTrue(payload["voice"]["ready"])
        self.assertTrue(payload["ocr"]["ready"])
        self.assertTrue(payload["browser"]["ready"])

    def test_missing_pytesseract_is_warning_not_failure(self) -> None:
        def available(name: str) -> bool:
            return name != "pytesseract"

        with patch.object(daily_use_readiness, "_module_available", side_effect=available), \
            patch.object(daily_use_readiness, "_tesseract_candidates", return_value=[{"source": "path", "path": "C:\\Tesseract\\tesseract.exe"}]), \
            patch.object(daily_use_readiness.Path, "exists", return_value=True), \
            patch.object(daily_use_readiness, "_browser_readiness", return_value={"ready": True, "warnings": [], "status": "ok"}), \
            patch.dict(os.environ, {daily_use_readiness.VOICE_RUNTIME_ENV: "1"}, clear=False):
            payload = daily_use_readiness.collect_daily_use_readiness()

        self.assertTrue(payload["ok"])
        self.assertEqual("warning", payload["status"])
        self.assertFalse(payload["ocr"]["pytesseract_installed"])
        self.assertIn("ocr_pytesseract_missing", payload["warnings"])
        self.assertIn("pip install pytesseract", " ".join(payload["ocr"]["setup_hints"]))

    def test_missing_tesseract_executable_is_warning_not_failure(self) -> None:
        with patch.object(daily_use_readiness, "_module_available", return_value=True), \
            patch.object(daily_use_readiness, "_tesseract_candidates", return_value=[{"source": "configured_path", "path": "C:\\missing\\tesseract.exe"}]), \
            patch.object(daily_use_readiness.Path, "exists", return_value=False):
            payload = daily_use_readiness._ocr_readiness()

        self.assertEqual("warning", payload["status"])
        self.assertFalse(payload["ready"])
        self.assertFalse(payload["tesseract_executable_detected"])
        self.assertIn("tesseract_executable_missing", payload["warnings"])
        self.assertIn("TESSERACT_PATH", " ".join(payload["setup_hints"]))

    def test_playwright_package_installed_but_browser_runtimes_missing(self) -> None:
        with patch.object(daily_use_readiness, "_module_available", return_value=True), \
            patch.object(daily_use_readiness, "_playwright_version", return_value="Version 1.40.0"), \
            patch.object(
                daily_use_readiness,
                "_playwright_executable_paths",
                return_value={
                    "chromium": "C:\\ms-playwright\\chromium\\chrome.exe",
                    "firefox": "C:\\ms-playwright\\firefox\\firefox.exe",
                    "webkit": "C:\\ms-playwright\\webkit\\Playwright.exe",
                },
            ), \
            patch.object(daily_use_readiness.Path, "exists", return_value=False):
            payload = daily_use_readiness._browser_readiness()

        self.assertEqual("warning", payload["status"])
        self.assertTrue(payload["playwright_package_installed"])
        self.assertEqual(["chromium", "firefox", "webkit"], payload["missing_browser_runtimes"])
        self.assertFalse(payload["browser_launched"])
        self.assertIn("python -m playwright install chromium", " ".join(payload["setup_hints"]))

    def test_endpoint_returns_warning_not_failure_for_optional_missing_tools(self) -> None:
        readiness = {
            "ok": True,
            "status": "warning",
            "safe_to_expose": True,
            "read_only": True,
            "warnings_count": 2,
            "warnings": ["ocr_pytesseract_missing", "browser_playwright_browser_runtime_missing"],
            "actions_performed": {
                "browser_launched": False,
                "microphone_accessed": False,
                "camera_accessed": False,
                "ocr_ran": False,
            },
        }
        with patch.object(web_api, "collect_startup_diagnostics", return_value={"ok": True, "items": []}), \
            patch.object(health_routes, "_daily_use_readiness", return_value=readiness):
            response = TestClient(web_api.app).get("/api/doctor")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual("warning", payload["daily_use_readiness"]["status"])
        self.assertTrue(payload["daily_use_readiness"]["read_only"])

    def test_payload_declares_no_browser_mic_camera_or_ocr_actions(self) -> None:
        with patch.object(daily_use_readiness, "_voice_readiness", return_value={"ready": False, "warnings": ["voice_runtime_disabled"]}), \
            patch.object(daily_use_readiness, "_ocr_readiness", return_value={"ready": False, "warnings": ["pytesseract_missing"]}), \
            patch.object(daily_use_readiness, "_browser_readiness", return_value={"ready": False, "warnings": ["playwright_package_missing"]}):
            payload = daily_use_readiness.collect_daily_use_readiness()

        self.assertEqual(
            {
                "browser_launched": False,
                "microphone_accessed": False,
                "camera_accessed": False,
                "ocr_ran": False,
            },
            payload["actions_performed"],
        )


if __name__ == "__main__":
    unittest.main()
