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
from modules.task_module import get_task_data  # noqa: E402
from modules.notes_module import _load_data as load_notes_data  # noqa: E402


TASKS_PATH = os.path.join(ROOT, "backend", "data", "tasks.json")
NOTES_PATH = os.path.join(ROOT, "backend", "data", "notes.json")


def _print_result(name, ok, details=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}")
    if details:
        print(f"  {details}")


@contextmanager
def _temporary_data_files():
    os.makedirs(os.path.dirname(TASKS_PATH), exist_ok=True)

    tasks_backup = TASKS_PATH + ".bak.codex"
    notes_backup = NOTES_PATH + ".bak.codex"

    if os.path.exists(TASKS_PATH):
        shutil.copy2(TASKS_PATH, tasks_backup)
    if os.path.exists(NOTES_PATH):
        shutil.copy2(NOTES_PATH, notes_backup)

    try:
        with open(TASKS_PATH, "w", encoding="utf-8") as f:
            json.dump({"tasks": [], "reminders": []}, f, indent=2)
        with open(NOTES_PATH, "w", encoding="utf-8") as f:
            json.dump({"notes": []}, f, indent=2)
        yield
    finally:
        if os.path.exists(tasks_backup):
            shutil.move(tasks_backup, TASKS_PATH)
        elif os.path.exists(TASKS_PATH):
            os.remove(TASKS_PATH)

        if os.path.exists(notes_backup):
            shutil.move(notes_backup, NOTES_PATH)
        elif os.path.exists(NOTES_PATH):
            os.remove(NOTES_PATH)


def _run(command):
    responses = web_api._capture_command_reply(command)
    if not responses:
        return ""
    return responses[0]


def run_tasks_flow():
    add_reply = _run("add task buy milk")
    list_reply = _run("show tasks")
    complete_reply = _run("complete task 1")
    delete_reply = _run("delete task 1")
    latest_reply = _run("latest task")

    checks = []
    checks.append(("Task add response", "Task added" in add_reply))
    checks.append(("Task listed", "buy milk" in list_reply.lower()))
    checks.append(("Task completed", "Completed task 1" in complete_reply))
    checks.append(("Task deleted", "Deleted task" in delete_reply))
    checks.append(("Task empty state", "no pending tasks" in latest_reply.lower()))

    ok = all(flag for _, flag in checks)
    return ok, checks


def run_reminders_flow():
    add_reply = _run("add reminder pay electricity bill tomorrow at 8 pm")
    add_set_reply = _run("set reminder submit report in 2 hours")
    list_reply = _run("show reminders")
    latest_reply = _run("latest reminder")

    task_data = get_task_data()
    reminders = task_data.get("reminders", [])
    first_title = reminders[0].get("title", "") if reminders else ""
    second_title = reminders[1].get("title", "") if len(reminders) > 1 else ""

    delete_reply = _run("delete reminder 1")

    checks = []
    checks.append(("Reminder add response", "Reminder added" in add_reply or "Recurring reminder added" in add_reply))
    checks.append(("Reminder set response", "Reminder added" in add_set_reply or "Recurring reminder added" in add_set_reply))
    checks.append(("Reminder listed", "pay electricity bill" in list_reply.lower()))
    checks.append(("Reminder latest", "latest reminder" in latest_reply.lower()))
    checks.append(("Reminder deleted", "Deleted reminder" in delete_reply))
    checks.append(
        (
            "Reminder title clean",
            first_title
            and not first_title.lower().startswith(("add reminder", "set reminder", "remind me"))
            and second_title
            and not second_title.lower().startswith(("add reminder", "set reminder", "remind me")),
        )
    )

    ok = all(flag for _, flag in checks)
    return ok, checks, first_title, second_title


def run_notes_flow():
    add_reply = _run("add note buy fruits from market")
    list_reply = _run("list notes")
    search_reply = _run("search notes for fruits")
    delete_reply = _run("delete note 1")
    latest_reply = _run("latest note")

    notes_data = load_notes_data()
    note_count = len(notes_data.get("notes", []))

    checks = []
    checks.append(("Note add response", "Note saved" in add_reply))
    checks.append(("Note listed", "buy fruits from market" in list_reply.lower()))
    checks.append(("Note search", "matching notes" in search_reply.lower()))
    checks.append(("Note deleted", "Deleted note" in delete_reply))
    checks.append(("Note empty state", "do not have any saved notes" in latest_reply.lower() and note_count == 0))

    ok = all(flag for _, flag in checks)
    return ok, checks


def main():
    overall = True
    with _temporary_data_files():
        tasks_ok, task_checks = run_tasks_flow()
        _print_result("Tasks flow", tasks_ok)
        for name, ok in task_checks:
            _print_result(name, ok)
        overall = overall and tasks_ok

        reminders_ok, reminder_checks, first_title, second_title = run_reminders_flow()
        _print_result(
            "Reminders flow",
            reminders_ok,
            f"Saved titles: first={first_title!r}, second={second_title!r}",
        )
        for name, ok in reminder_checks:
            _print_result(name, ok)
        overall = overall and reminders_ok

        notes_ok, note_checks = run_notes_flow()
        _print_result("Notes flow", notes_ok)
        for name, ok in note_checks:
            _print_result(name, ok)
        overall = overall and notes_ok

    print("\nSummary:")
    print(f"overall_ok={overall}")
    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    main()
