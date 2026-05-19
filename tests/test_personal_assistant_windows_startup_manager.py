import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
for path in [APP_DIR, SHARED_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from core.personal_assistant.context import clear_personal_assistant_contexts_for_tests
from core.personal_assistant.service import handle_personal_assistant_message
from core.personal_assistant import windows_startup_manager
from core.personal_assistant.tool_registry import list_available_tools


class WindowsStartupManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_personal_assistant_contexts_for_tests()
        self.temp = tempfile.TemporaryDirectory()
        self.startup_dir = Path(self.temp.name) / "Startup"
        self.python_exe = Path(self.temp.name) / "python.exe"
        self.entrypoint = Path(self.temp.name) / "backend" / "main.py"
        self.python_exe.write_text("", encoding="utf-8")
        self.entrypoint.parent.mkdir(parents=True, exist_ok=True)
        self.entrypoint.write_text("print('boot')\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()
        clear_personal_assistant_contexts_for_tests()

    def test_status_when_disabled(self) -> None:
        status = windows_startup_manager.startup_status(startup_dir=self.startup_dir, python_executable=self.python_exe, entrypoint=self.entrypoint)

        self.assertTrue(status["ok"])
        self.assertFalse(status["enabled"])
        self.assertTrue(status["target_valid"])
        self.assertIn("disabled", status["message"])

    def test_enable_creates_startup_entry_and_duplicate_enable_does_not_duplicate(self) -> None:
        first = windows_startup_manager.enable_startup(startup_dir=self.startup_dir, python_executable=self.python_exe, entrypoint=self.entrypoint)
        second = windows_startup_manager.enable_startup(startup_dir=self.startup_dir, python_executable=self.python_exe, entrypoint=self.entrypoint)
        files = list(self.startup_dir.glob("GrandpaAssistantStartup*.cmd"))

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(1, len(files))
        script = files[0].read_text(encoding="utf-8")
        self.assertIn("GRANDPA_REMINDER_SCHEDULER_ENABLED=1", script)
        self.assertIn(str(self.entrypoint), script)

    def test_disable_removes_startup_entry(self) -> None:
        windows_startup_manager.enable_startup(startup_dir=self.startup_dir, python_executable=self.python_exe, entrypoint=self.entrypoint)

        result = windows_startup_manager.disable_startup(startup_dir=self.startup_dir)

        self.assertTrue(result["ok"])
        self.assertFalse((self.startup_dir / windows_startup_manager.STARTUP_FILE_NAME).exists())

    def test_missing_entrypoint_fails_safely(self) -> None:
        missing = self.entrypoint.parent / "missing.py"

        result = windows_startup_manager.enable_startup(startup_dir=self.startup_dir, python_executable=self.python_exe, entrypoint=missing)

        self.assertFalse(result["ok"])
        self.assertIn("missing", result["message"].lower())
        self.assertFalse((self.startup_dir / windows_startup_manager.STARTUP_FILE_NAME).exists())

    def test_enable_requires_confirmation_in_chat_path(self) -> None:
        with patch.object(windows_startup_manager, "startup_folder_path", return_value=self.startup_dir), patch.object(
            windows_startup_manager, "default_python_executable", return_value=self.python_exe
        ), patch.object(windows_startup_manager, "default_entrypoint_path", return_value=self.entrypoint):
            first = handle_personal_assistant_message("start GrandpaAssistant when Windows starts", session_id="startup-chat")
            second = handle_personal_assistant_message("yes", session_id="startup-chat")

        self.assertTrue(first["requires_confirmation"])
        self.assertEqual("enable_startup", first["intent"])
        self.assertTrue(second["executed"])
        self.assertTrue((self.startup_dir / windows_startup_manager.STARTUP_FILE_NAME).exists())

    def test_disable_and_status_chat_paths_use_startup_tools(self) -> None:
        with patch.object(windows_startup_manager, "startup_folder_path", return_value=self.startup_dir), patch.object(
            windows_startup_manager, "default_python_executable", return_value=self.python_exe
        ), patch.object(windows_startup_manager, "default_entrypoint_path", return_value=self.entrypoint):
            windows_startup_manager.enable_startup()
            status = handle_personal_assistant_message("check startup status", session_id="startup-status")
            disabled = handle_personal_assistant_message("stop opening on startup", session_id="startup-status")

        self.assertEqual("startup_status", status["intent"])
        self.assertTrue(status["executed"])
        self.assertEqual("disable_startup", disabled["intent"])
        self.assertTrue(disabled["executed"])

    def test_registry_lists_startup_tools(self) -> None:
        tools = {item["tool_name"] for item in list_available_tools()}

        self.assertIn("startup_status", tools)
        self.assertIn("enable_startup", tools)
        self.assertIn("disable_startup", tools)


if __name__ == "__main__":
    unittest.main()
