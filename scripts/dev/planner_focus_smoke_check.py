import json
import os
import sys
import tempfile
from contextlib import contextmanager


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for _path in (APP_DIR, SHARED_DIR, FEATURES_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import api.web_api as web_api  # noqa: E402
import app_data_store  # noqa: E402
import brain.database as brain_database  # noqa: E402
import productivity.task_module as task_module  # noqa: E402
import productivity_store  # noqa: E402
import utils.config as config_module  # noqa: E402
from utils.paths import config_path, data_path  # noqa: E402


TASKS_PATH = data_path("tasks.json")
SETTINGS_PATH = config_path("settings.json")


def _print_result(name, ok, details=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}")
    if details:
        print(f"  {details}")


@contextmanager
def _temporary_data_files():
    original_brain_db_path = brain_database.DB_PATH
    original_store_db_path = productivity_store.DB_PATH
    original_app_db_path = app_data_store.DB_PATH
    original_task_path = task_module.DATA_FILE
    original_settings_path = config_module.SETTINGS_PATH

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = os.path.join(temp_dir, "assistant.db")
        temp_tasks_path = os.path.join(temp_dir, "tasks.json")
        temp_settings_path = os.path.join(temp_dir, "settings.json")

        brain_database.DB_PATH = temp_db_path
        productivity_store.DB_PATH = temp_db_path
        app_data_store.DB_PATH = temp_db_path
        task_module.DATA_FILE = temp_tasks_path
        config_module.SETTINGS_PATH = temp_settings_path
        config_module._SETTINGS_CACHE = None
        config_module._SETTINGS_CACHE_MTIME = None

        with open(temp_tasks_path, "w", encoding="utf-8") as file:
            json.dump({"tasks": [], "reminders": []}, file, indent=2)

        try:
            yield
        finally:
            brain_database.DB_PATH = original_brain_db_path
            productivity_store.DB_PATH = original_store_db_path
            app_data_store.DB_PATH = original_app_db_path
            task_module.DATA_FILE = original_task_path
            config_module.SETTINGS_PATH = original_settings_path
            config_module._SETTINGS_CACHE = None
            config_module._SETTINGS_CACHE_MTIME = None


def _run(command):
    responses = web_api._capture_command_reply(command)
    if not responses:
        return ""
    return responses[0]


def run_planner_focus_flow():
    add_task_primary = _run("add task finish project report high priority")
    add_task_secondary = _run("add task clean desk")
    add_reminder_due_soon = _run("add reminder pay internet bill in 30 minutes")
    add_reminder_later = _run("add reminder call amma tomorrow at 7 pm")

    plan_reply = _run("plan my day")
    focus_reply = _run("what should i do now")

    status_off_reply = _run("focus mode status")

    checks = []
    checks.append(("Task add primary", "Task added" in add_task_primary))
    checks.append(("Task add secondary", "Task added" in add_task_secondary))
    checks.append(("Reminder add due soon", "Reminder added" in add_reminder_due_soon))
    checks.append(("Reminder add later", "Reminder added" in add_reminder_later))
    checks.append(("Plan format header", "today agenda for" in plan_reply.lower()))
    checks.append(("Plan step format", "step 1:" in plan_reply.lower() and "step 4:" in plan_reply.lower()))
    checks.append(("Plan includes queue", "task queue" in plan_reply.lower()))
    checks.append(("Focus prioritizes due soon", "pay internet bill" in focus_reply.lower()))
    checks.append(("Focus status off", "currently disabled" in status_off_reply.lower()))

    ok = all(flag for _, flag in checks)
    details = {
        "plan_reply": plan_reply,
        "focus_reply": focus_reply,
        "focus_status_reply": status_off_reply,
    }
    return ok, checks, details


def main():
    overall = True
    with _temporary_data_files():
        flow_ok, flow_checks, details = run_planner_focus_flow()
        _print_result("Planner and focus flow", flow_ok)
        for name, ok in flow_checks:
            _print_result(name, ok)
        _print_result("Planner snapshot", True, details["plan_reply"])
        _print_result("Focus snapshot", True, details["focus_reply"])
        _print_result("Focus status snapshot", True, details["focus_status_reply"])
        overall = overall and flow_ok

    print("\nSummary:")
    print(f"overall_ok={overall}")
    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    main()
