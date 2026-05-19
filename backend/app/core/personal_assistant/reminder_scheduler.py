from __future__ import annotations

import logging
import os
import threading
from typing import Any, Callable

from . import reminder_engine
from .context import compact_text


logger = logging.getLogger(__name__)

REMINDER_SCHEDULER_ENABLED_ENV = "GRANDPA_REMINDER_SCHEDULER_ENABLED"
REMINDER_CHECK_INTERVAL_ENV = "GRANDPA_REMINDER_CHECK_INTERVAL_SECONDS"
DEFAULT_REMINDER_CHECK_INTERVAL_SECONDS = 30
TRUE_VALUES = {"1", "true", "yes", "on"}

ReminderCheck = Callable[[], dict[str, Any]]


def is_reminder_scheduler_enabled() -> bool:
    return compact_text(os.getenv(REMINDER_SCHEDULER_ENABLED_ENV)).lower() in TRUE_VALUES


def reminder_check_interval_seconds() -> float:
    raw_value = compact_text(os.getenv(REMINDER_CHECK_INTERVAL_ENV))
    if not raw_value:
        return float(DEFAULT_REMINDER_CHECK_INTERVAL_SECONDS)
    try:
        return max(1.0, float(raw_value))
    except Exception:
        return float(DEFAULT_REMINDER_CHECK_INTERVAL_SECONDS)


class ReminderScheduler:
    """Small managed loop for checking due reminders while the app is running."""

    def __init__(self, *, check_due: ReminderCheck | None = None, interval_seconds: float | None = None) -> None:
        self._check_due = check_due or reminder_engine.check_due_reminders
        if interval_seconds is None:
            self._interval_seconds = reminder_check_interval_seconds()
        else:
            self._interval_seconds = max(0.01, float(interval_seconds))
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._last_result: dict[str, Any] | None = None
        self._last_error = ""
        self._ticks = 0

    @property
    def interval_seconds(self) -> float:
        return self._interval_seconds

    def start(self, *, enabled: bool | None = None) -> bool:
        should_start = is_reminder_scheduler_enabled() if enabled is None else bool(enabled)
        if not should_start:
            logger.info("Reminder scheduler disabled by configuration.")
            return False
        with self._lock:
            if self.is_running():
                logger.info("Reminder scheduler already running.")
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="GrandpaReminderScheduler", daemon=True)
            self._thread.start()
            logger.info("Reminder scheduler started interval_seconds=%s", self._interval_seconds)
            return True

    def stop(self, *, timeout: float = 5.0) -> bool:
        with self._lock:
            thread = self._thread
            if thread is None:
                return True
            self._stop_event.set()
        thread.join(timeout=max(0.1, timeout))
        stopped = not thread.is_alive()
        if stopped:
            with self._lock:
                if self._thread is thread:
                    self._thread = None
            logger.info("Reminder scheduler stopped.")
        else:
            logger.warning("Reminder scheduler did not stop before timeout.")
        return stopped

    def is_running(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())

    def run_once(self) -> dict[str, Any]:
        try:
            result = self._check_due()
            if not isinstance(result, dict):
                result = {"ok": False, "message": "Reminder check returned an invalid result.", "notification_count": 0, "due_reminders": []}
            self._last_error = ""
        except Exception as error:
            result = {
                "ok": False,
                "message": "Reminder scheduler check failed: " + compact_text(error),
                "notification_count": 0,
                "due_reminders": [],
            }
            self._last_error = compact_text(error)
            logger.warning("Reminder scheduler check failed: %s", self._last_error)
        with self._lock:
            self._ticks += 1
            self._last_result = result
        due_count = len(result.get("due_reminders") or []) if isinstance(result.get("due_reminders"), list) else 0
        logger.info("Reminder scheduler tick ok=%s due_count=%s notification_count=%s", bool(result.get("ok")), due_count, result.get("notification_count", 0))
        return result

    def status(self) -> dict[str, Any]:
        with self._lock:
            last_result = dict(self._last_result or {})
            return {
                "enabled": is_reminder_scheduler_enabled(),
                "running": self.is_running(),
                "interval_seconds": self._interval_seconds,
                "ticks": self._ticks,
                "last_ok": bool(last_result.get("ok")) if last_result else None,
                "last_notification_count": int(last_result.get("notification_count") or 0) if last_result else 0,
                "last_due_count": len(last_result.get("due_reminders") or []) if isinstance(last_result.get("due_reminders"), list) else 0,
                "last_error": self._last_error,
                "env_var": REMINDER_SCHEDULER_ENABLED_ENV,
                "interval_env_var": REMINDER_CHECK_INTERVAL_ENV,
            }

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self._interval_seconds):
            self.run_once()


_GLOBAL_SCHEDULER = ReminderScheduler()


def get_global_reminder_scheduler() -> ReminderScheduler:
    return _GLOBAL_SCHEDULER


def start_global_reminder_scheduler(*, enabled: bool | None = None) -> bool:
    return _GLOBAL_SCHEDULER.start(enabled=enabled)


def stop_global_reminder_scheduler(*, timeout: float = 5.0) -> bool:
    return _GLOBAL_SCHEDULER.stop(timeout=timeout)


def run_reminder_scheduler_once() -> dict[str, Any]:
    return _GLOBAL_SCHEDULER.run_once()


def get_reminder_scheduler_status() -> dict[str, Any]:
    return _GLOBAL_SCHEDULER.status()
