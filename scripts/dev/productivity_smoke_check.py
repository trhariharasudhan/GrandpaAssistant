import os
import sys
from contextlib import contextmanager
import tempfile
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for _path in (APP_DIR, SHARED_DIR, FEATURES_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from brain import database as brain_database  # noqa: E402
import app_data_store  # noqa: E402
import api.web_api as web_api  # noqa: E402
import productivity_store  # noqa: E402
from modules import notes_module, task_module  # noqa: E402


def _print_result(name, ok, details=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}")
    if details:
        print(f"  {details}")


@contextmanager
def _temporary_runtime_db():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "assistant.db")
        tasks_path = os.path.join(temp_dir, "tasks.json")
        notes_path = os.path.join(temp_dir, "notes.json")
        path_patches = [
            patch.object(brain_database, "DB_PATH", db_path),
            patch.object(productivity_store, "DB_PATH", db_path),
            patch.object(app_data_store, "DB_PATH", db_path),
            patch.object(task_module, "DATA_FILE", tasks_path),
            patch.object(notes_module, "DATA_FILE", notes_path),
        ]
        for path_patch in path_patches:
            path_patch.start()
        try:
            yield
        finally:
            for path_patch in reversed(path_patches):
                path_patch.stop()


def _run(command):
    responses = web_api._capture_command_reply(command)
    if not responses:
        return ""
    return responses[0]


def _run_confirmed(command):
    prompt = _run(command)
    if "confirm" not in prompt.lower():
        return prompt, ""
    confirmed = _run("yes")
    return prompt, confirmed


@contextmanager
def _temporary_runtime_state():
    original_pending = getattr(web_api.command_router_module, "pending_confirmation", None)
    try:
        yield
    finally:
        web_api.command_router_module.pending_confirmation = original_pending


def run_tasks_flow():
    add_reply = _run("add task buy milk")
    list_reply = _run("show tasks")
    complete_reply = _run("complete task 1")
    delete_prompt, delete_reply = _run_confirmed("delete task 1")
    latest_reply = _run("latest task")

    checks = []
    checks.append(("Task add response", "Task added" in add_reply))
    checks.append(("Task listed", "buy milk" in list_reply.lower()))
    checks.append(("Task completed", "Completed task 1" in complete_reply))
    checks.append(("Task delete confirmation", "confirm" in delete_prompt.lower()))
    checks.append(("Task deleted", "Deleted task" in delete_reply))
    checks.append(("Task empty state", "no pending tasks" in latest_reply.lower()))

    ok = all(flag for _, flag in checks)
    return ok, checks


def run_reminders_flow():
    add_reply = _run("add reminder pay electricity bill tomorrow at 8 pm")
    add_set_reply = _run("set reminder submit report in 2 hours")
    list_reply = _run("show reminders")
    latest_reply = _run("latest reminder")

    task_data = task_module.get_task_data()
    reminders = task_data.get("reminders", [])
    first_title = reminders[0].get("title", "") if reminders else ""
    second_title = reminders[1].get("title", "") if len(reminders) > 1 else ""

    delete_prompt, delete_reply = _run_confirmed("delete reminder 1")

    checks = []
    checks.append(("Reminder add response", "Reminder added" in add_reply or "Recurring reminder added" in add_reply))
    checks.append(("Reminder set response", "Reminder added" in add_set_reply or "Recurring reminder added" in add_set_reply))
    checks.append(("Reminder listed", "pay electricity bill" in list_reply.lower()))
    checks.append(("Reminder latest", "latest reminder" in latest_reply.lower()))
    checks.append(("Reminder delete confirmation", "confirm" in delete_prompt.lower()))
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
    delete_prompt, delete_reply = _run_confirmed("delete note 1")
    latest_reply = _run("latest note")

    notes_data = notes_module._load_data()
    note_count = len(notes_data.get("notes", []))

    checks = []
    checks.append(("Note add response", "Note saved" in add_reply))
    checks.append(("Note listed", "buy fruits from market" in list_reply.lower()))
    checks.append(("Note search", "matching notes" in search_reply.lower()))
    checks.append(("Note delete confirmation", "confirm" in delete_prompt.lower()))
    checks.append(("Note deleted", "Deleted note" in delete_reply))
    checks.append(("Note empty state", "do not have any saved notes" in latest_reply.lower() and note_count == 0))

    ok = all(flag for _, flag in checks)
    return ok, checks


def main():
    overall = True
    with _temporary_runtime_db():
        with _temporary_runtime_state():
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
