import json
import os
import shutil
import sys
from contextlib import contextmanager


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for _path in (APP_DIR, SHARED_DIR, FEATURES_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import api.web_api as web_api  # noqa: E402


TASKS_PATH = os.path.join(ROOT, "backend", "data", "tasks.json")
SETTINGS_PATH = os.path.join(ROOT, "backend", "data", "settings.json")


def _print_result(name, ok, details=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}")
    if details:
        print(f"  {details}")


@contextmanager
def _temporary_data_files():
    os.makedirs(os.path.dirname(TASKS_PATH), exist_ok=True)

    tasks_backup = TASKS_PATH + ".bak.codex"
    settings_backup = SETTINGS_PATH + ".bak.codex"

    if os.path.exists(TASKS_PATH):
        shutil.copy2(TASKS_PATH, tasks_backup)
    if os.path.exists(SETTINGS_PATH):
        shutil.copy2(SETTINGS_PATH, settings_backup)

    try:
        with open(TASKS_PATH, "w", encoding="utf-8") as f:
            json.dump({"tasks": [], "reminders": []}, f, indent=2)
        yield
    finally:
        if os.path.exists(tasks_backup):
            shutil.move(tasks_backup, TASKS_PATH)
        elif os.path.exists(TASKS_PATH):
            os.remove(TASKS_PATH)

        if os.path.exists(settings_backup):
            shutil.move(settings_backup, SETTINGS_PATH)
        elif os.path.exists(SETTINGS_PATH):
            os.remove(SETTINGS_PATH)


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

    enable_focus_reply = _run("enable focus mode")
    focus_reply_in_focus_mode = _run("what should i do now")
    status_on_reply = _run("focus mode status")
    disable_focus_reply = _run("disable focus mode")
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
    checks.append(("Focus enable response", "focus mode enabled" in enable_focus_reply.lower()))
    checks.append(("Focus suggestion reflects mode", "focus mode is on" in focus_reply_in_focus_mode.lower()))
    checks.append(("Focus status on", "currently enabled" in status_on_reply.lower()))
    checks.append(("Focus disable response", "focus mode disabled" in disable_focus_reply.lower()))
    checks.append(("Focus status off", "currently disabled" in status_off_reply.lower()))

    ok = all(flag for _, flag in checks)
    details = {
        "plan_reply": plan_reply,
        "focus_reply": focus_reply,
        "focus_reply_in_focus_mode": focus_reply_in_focus_mode,
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
        _print_result("Focus mode snapshot", True, details["focus_reply_in_focus_mode"])
        overall = overall and flow_ok

    print("\nSummary:")
    print(f"overall_ok={overall}")
    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    main()
