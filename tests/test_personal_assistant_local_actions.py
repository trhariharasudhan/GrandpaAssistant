import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
for path in [APP_DIR, SHARED_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from services import local_action_executor


class LocalPersonalAssistantActionAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.audit_patch = patch.object(local_action_executor, "append_local_action_audit")
        self.audit_patch.start()

    def tearDown(self) -> None:
        self.audit_patch.stop()

    def test_adjust_volume_success_with_windows_interface(self) -> None:
        volume = Mock()
        volume.GetMasterVolumeLevelScalar.return_value = 0.5

        with patch.object(local_action_executor, "_get_volume_interface", return_value=volume):
            result = local_action_executor.execute_local_action(
                {"action": "adjust_volume", "params": {"operation": "decrease", "step": 10}}
            )

        self.assertTrue(result["ok"])
        self.assertEqual("Reduced the system volume.", result["message"])
        volume.SetMasterVolumeLevelScalar.assert_called_once()

    def test_adjust_volume_failure_is_safe_and_specific(self) -> None:
        with patch.object(local_action_executor, "_get_volume_interface", return_value=None), patch.object(
            local_action_executor, "_fallback_media_key", return_value=False
        ):
            result = local_action_executor.execute_local_action(
                {"action": "adjust_volume", "params": {"operation": "decrease"}}
            )

        self.assertFalse(result["ok"])
        self.assertIn("Windows volume control failed", result["message"])

    def test_close_app_requires_assistant_tracked_context(self) -> None:
        result = local_action_executor.execute_local_action(
            {"action": "close_app", "params": {"app": "calculator", "assistant_tracked": False}}
        )

        self.assertFalse(result["ok"])
        self.assertIn("opened or tracked", result["message"])

    def test_close_app_terminates_only_allowlisted_process(self) -> None:
        process = Mock()
        process.name.return_value = "calc.exe"

        fake_psutil = Mock()
        fake_psutil.Process.return_value = process

        with patch.dict("sys.modules", {"psutil": fake_psutil}):
            result = local_action_executor.execute_local_action(
                {"action": "close_app", "params": {"app": "calculator", "assistant_tracked": True, "pid": 123}}
            )

        self.assertTrue(result["ok"])
        self.assertEqual("Closed calculator.", result["message"])
        fake_psutil.Process.assert_called_once_with(123)
        process.terminate.assert_called_once()

    def test_close_app_refuses_non_allowlisted_process(self) -> None:
        result = local_action_executor.execute_local_action(
            {"action": "close_app", "params": {"app": "explorer", "assistant_tracked": True}}
        )

        self.assertFalse(result["ok"])
        self.assertIn("safe close-app allowlist", result["message"])


if __name__ == "__main__":
    unittest.main()
