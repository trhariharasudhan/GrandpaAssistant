import os
import sys
import threading
import time
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


from core.personal_assistant import reminder_scheduler


class ReminderSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old_enabled = os.environ.pop(reminder_scheduler.REMINDER_SCHEDULER_ENABLED_ENV, None)
        self.old_interval = os.environ.pop(reminder_scheduler.REMINDER_CHECK_INTERVAL_ENV, None)

    def tearDown(self) -> None:
        reminder_scheduler.stop_global_reminder_scheduler(timeout=0.5)
        if self.old_enabled is None:
            os.environ.pop(reminder_scheduler.REMINDER_SCHEDULER_ENABLED_ENV, None)
        else:
            os.environ[reminder_scheduler.REMINDER_SCHEDULER_ENABLED_ENV] = self.old_enabled
        if self.old_interval is None:
            os.environ.pop(reminder_scheduler.REMINDER_CHECK_INTERVAL_ENV, None)
        else:
            os.environ[reminder_scheduler.REMINDER_CHECK_INTERVAL_ENV] = self.old_interval

    def test_scheduler_disabled_by_default(self) -> None:
        scheduler = reminder_scheduler.ReminderScheduler(check_due=lambda: {"ok": True}, interval_seconds=0.01)

        self.assertFalse(reminder_scheduler.is_reminder_scheduler_enabled())
        self.assertFalse(scheduler.start())
        self.assertFalse(scheduler.is_running())

    def test_scheduler_starts_only_when_enabled_and_duplicate_start_is_ignored(self) -> None:
        scheduler = reminder_scheduler.ReminderScheduler(check_due=lambda: {"ok": True}, interval_seconds=0.05)

        self.assertTrue(scheduler.start(enabled=True))
        self.assertTrue(scheduler.is_running())
        self.assertFalse(scheduler.start(enabled=True))
        self.assertTrue(scheduler.stop(timeout=1.0))
        self.assertFalse(scheduler.is_running())

    def test_check_loop_calls_reminder_engine_without_long_sleep(self) -> None:
        ticked = threading.Event()

        def check_due():
            ticked.set()
            return {"ok": True, "notification_count": 1, "due_reminders": [{"title": "drink water"}]}

        scheduler = reminder_scheduler.ReminderScheduler(check_due=check_due, interval_seconds=0.01)
        self.assertTrue(scheduler.start(enabled=True))
        self.assertTrue(ticked.wait(1.0))
        self.assertTrue(scheduler.stop(timeout=1.0))
        status = scheduler.status()
        self.assertGreaterEqual(status["ticks"], 1)
        self.assertEqual(1, status["last_notification_count"])
        self.assertEqual(1, status["last_due_count"])

    def test_interval_config_uses_env_with_default_fallback(self) -> None:
        os.environ[reminder_scheduler.REMINDER_CHECK_INTERVAL_ENV] = "7"
        self.assertEqual(7.0, reminder_scheduler.reminder_check_interval_seconds())

        os.environ[reminder_scheduler.REMINDER_CHECK_INTERVAL_ENV] = "not-a-number"
        self.assertEqual(float(reminder_scheduler.DEFAULT_REMINDER_CHECK_INTERVAL_SECONDS), reminder_scheduler.reminder_check_interval_seconds())

    def test_notification_or_check_failure_does_not_crash_scheduler(self) -> None:
        scheduler = reminder_scheduler.ReminderScheduler(check_due=lambda: (_ for _ in ()).throw(RuntimeError("toast failed")), interval_seconds=0.01)

        result = scheduler.run_once()

        self.assertFalse(result["ok"])
        self.assertIn("toast failed", result["message"])
        self.assertIn("toast failed", scheduler.status()["last_error"])

    def test_global_lifecycle_respects_env_flag_and_status_is_safe(self) -> None:
        self.assertFalse(reminder_scheduler.start_global_reminder_scheduler())
        os.environ[reminder_scheduler.REMINDER_SCHEDULER_ENABLED_ENV] = "1"
        with patch.object(reminder_scheduler._GLOBAL_SCHEDULER, "_check_due", return_value={"ok": True, "notification_count": 0, "due_reminders": []}):
            started = reminder_scheduler.start_global_reminder_scheduler()
            status = reminder_scheduler.get_reminder_scheduler_status()
            stopped = reminder_scheduler.stop_global_reminder_scheduler(timeout=1.0)

        self.assertTrue(started)
        self.assertTrue(status["enabled"])
        self.assertTrue(status["running"])
        self.assertTrue(stopped)


if __name__ == "__main__":
    unittest.main()
