import importlib
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
APP_DIR = BACKEND_DIR / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in [BACKEND_DIR, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


SHIM_EXPECTATIONS = {
    "app_scan_module": ("system.app_scan_module", "get_all_apps"),
    "briefing_module": ("productivity.briefing_module", "build_due_reminder_alert"),
    "browser_automation_module": ("intelligence.browser_automation_module", "ask_selected_browser_text_ai"),
    "calendar_module": ("productivity.calendar_module", "get_time"),
    "dashboard_module": ("productivity.dashboard_module", "build_dashboard_report"),
    "desktop_launch_module": ("modules.desktop_launch_module", "open_desktop_ui"),
    "dictation_module": ("automation.dictation_module", "start_dictation"),
    "event_module": ("productivity.event_module", "add_event"),
    "export_module": ("productivity.export_module", "export_productivity_summary"),
    "file_intelligence_module": ("intelligence.file_intelligence_module", "find_file"),
    "google_calendar_module": ("integrations.google_calendar_module", "today_google_calendar_events"),
    "google_contacts_module": ("integrations.google_contacts_module", "list_favorite_contacts"),
    "health_module": ("system.health_module", "get_system_status"),
    "media_module": ("system.media_module", "media_control"),
    "messaging_automation_module": ("automation.messaging_automation_module", "quick_whatsapp_message"),
    "nextgen_module": ("productivity.nextgen_module", "nextgen_status_snapshot"),
    "notes_module": ("productivity.notes_module", "add_note"),
    "notification_module": ("automation.notification_module", "show_custom_popup"),
    "profile_module": ("productivity.profile_module", "build_profile_summary"),
    "routine_module": ("productivity.routine_module", "list_routines"),
    "startup_module": ("automation.startup_module", "startup_auto_launch_status"),
    "system_module": ("system.system_module", "take_screenshot"),
    "task_module": ("productivity.task_module", "add_task"),
    "weather_module": ("integrations.weather_module", "get_weather_report"),
    "web_module": ("integrations.web_module", "wikipedia_search"),
    "window_context_module": ("system.window_context_module", "get_active_window_info"),
    "windows_voice_control_module": ("system.windows_voice_control_module", "get_active_window_summary"),
}


class CompatibilityShimTests(unittest.TestCase):
    def test_each_compatibility_shim_imports_and_exposes_expected_symbol(self) -> None:
        for shim_name, (_target_module, expected_symbol) in SHIM_EXPECTATIONS.items():
            with self.subTest(shim=shim_name):
                module = importlib.import_module(f"modules.{shim_name}")
                self.assertTrue(hasattr(module, expected_symbol), expected_symbol)

    def test_direct_domain_imports_still_work(self) -> None:
        for shim_name, (target_module, expected_symbol) in SHIM_EXPECTATIONS.items():
            if target_module.startswith("modules."):
                continue
            with self.subTest(target=target_module, shim=shim_name):
                module = importlib.import_module(target_module)
                self.assertTrue(hasattr(module, expected_symbol), expected_symbol)

    def test_terminal_chatbot_sources_do_not_depend_on_compatibility_shims(self) -> None:
        chatbot_paths = [
            APP_DIR / "cli" / "chat.py",
            APP_DIR / "core" / "chatbot" / "__init__.py",
            APP_DIR / "core" / "chatbot" / "engine.py",
            APP_DIR / "core" / "chatbot" / "intent_router.py",
            APP_DIR / "core" / "chatbot" / "memory.py",
            APP_DIR / "core" / "chatbot" / "prompt_builder.py",
        ]
        forbidden = ("from modules", "import modules", "features.modules", "backend.app.features.modules")
        for path in chatbot_paths:
            with self.subTest(path=os.fspath(path.relative_to(ROOT))):
                source = path.read_text(encoding="utf-8")
                for marker in forbidden:
                    self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
