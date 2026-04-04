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


DATA_DIR = os.path.join(ROOT, "backend", "data")
TASKS_PATH = os.path.join(DATA_DIR, "tasks.json")
EVENTS_PATH = os.path.join(DATA_DIR, "events.json")
NEXTGEN_PATH = os.path.join(DATA_DIR, "nextgen_features.json")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")


def _print_result(name, ok, details=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}")
    if details:
        print(f"  {details}")


def _run(command):
    responses = web_api._capture_command_reply(command)
    if not responses:
        return ""
    return responses[0]


def _contains(text, *parts):
    lowered = str(text or "").lower()
    return all(part.lower() in lowered for part in parts)


@contextmanager
def _temporary_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    targets = [TASKS_PATH, EVENTS_PATH, NEXTGEN_PATH, SETTINGS_PATH]
    backups = {}

    for path in targets:
        backup = path + ".bak.codex"
        if os.path.exists(path):
            shutil.copy2(path, backup)
            backups[path] = backup

    try:
        with open(TASKS_PATH, "w", encoding="utf-8") as file:
            json.dump({"tasks": [], "reminders": []}, file, indent=2)
        with open(EVENTS_PATH, "w", encoding="utf-8") as file:
            json.dump({"events": []}, file, indent=2)
        with open(NEXTGEN_PATH, "w", encoding="utf-8") as file:
            json.dump({}, file, indent=2)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as file:
            json.dump({}, file, indent=2)
        yield
    finally:
        for path in targets:
            backup = backups.get(path)
            if backup and os.path.exists(backup):
                shutil.move(backup, path)
            elif os.path.exists(path):
                os.remove(path)


def run_nextgen_flow():
    checks = []

    _run("add task finish proposal deck")
    _run("add reminder pay internet bill in 2 hours")

    day_plan_reply = _run("generate ai day plan")
    checks.append(
        (
            "1) AI day planner",
            _contains(day_plan_reply, "blocks")
            or _contains(day_plan_reply, "planned"),
            day_plan_reply,
        )
    )

    add_habit_reply = _run("add habit gym")
    check_habit_reply = _run("check in habit gym")
    habit_summary_reply = _run("habit dashboard")
    checks.append(
        (
            "2) Habit tracker",
            _contains(add_habit_reply, "habit added")
            and _contains(check_habit_reply, "marked habit done")
            and _contains(habit_summary_reply, "habit score"),
            f"{add_habit_reply} | {check_habit_reply} | {habit_summary_reply}",
        )
    )

    add_goal_reply = _run("add goal launch v2 app")
    add_milestone_reply = _run("add milestone complete ui polish to goal launch v2 app")
    complete_milestone_reply = _run("complete milestone complete ui polish in goal launch v2 app")
    goal_summary_reply = _run("goal board")
    checks.append(
        (
            "3) Goals and milestones",
            _contains(add_goal_reply, "goal added")
            and _contains(add_milestone_reply, "milestone added")
            and _contains(complete_milestone_reply, "milestone completed")
            and _contains(goal_summary_reply, "goal board"),
            f"{add_goal_reply} | {add_milestone_reply} | {complete_milestone_reply} | {goal_summary_reply}",
        )
    )

    reminder_priority_reply = _run("smart reminder priority")
    checks.append(
        (
            "4) Smart reminder priority",
            _contains(reminder_priority_reply, "smart reminder priority")
            or _contains(reminder_priority_reply, "no reminders to rank"),
            reminder_priority_reply,
        )
    )

    apply_voice_trainer_reply = _run("voice trainer noisy")
    voice_trainer_status_reply = _run("voice trainer status")
    checks.append(
        (
            "5) Voice trainer",
            _contains(apply_voice_trainer_reply, "voice trainer applied")
            and _contains(voice_trainer_status_reply, "voice trainer status"),
            f"{apply_voice_trainer_reply} | {voice_trainer_status_reply}",
        )
    )

    set_language_reply = _run("set language mode tamil")
    preview_language_reply = _run("preview language switch vanakkam macha")
    language_status_reply = _run("language mode status")
    checks.append(
        (
            "6) Language mode",
            _contains(set_language_reply, "language mode updated")
            and _contains(preview_language_reply, "tamil response mode")
            and _contains(language_status_reply, "language mode is tamil"),
            f"{set_language_reply} | {preview_language_reply} | {language_status_reply}",
        )
    )

    capture_meeting_reply = _run("capture meeting product sync: send invoice, review roadmap")
    meeting_summary_reply = _run("meeting summary")
    checks.append(
        (
            "7) Meeting capture",
            _contains(capture_meeting_reply, "meeting saved")
            and _contains(meeting_summary_reply, "meeting summary"),
            f"{capture_meeting_reply} | {meeting_summary_reply}",
        )
    )

    tag_doc_reply = _run("tag document roadmap.pdf as product,planning")
    move_doc_reply = _run("move document roadmap.pdf to folder strategy")
    rag_summary_reply = _run("rag library summary")
    checks.append(
        (
            "8) RAG library manager",
            _contains(tag_doc_reply, "tagged as")
            and _contains(move_doc_reply, "moved")
            and _contains(rag_summary_reply, "rag library"),
            f"{tag_doc_reply} | {move_doc_reply} | {rag_summary_reply}",
        )
    )

    create_automation_reply = _run(
        "create automation morning brief when time is 8 am then send daily summary"
    )
    list_automation_reply = _run("list automations")
    run_automation_reply = _run("run automations now")
    automation_history_reply = _run("automation history")
    disable_automation_reply = _run("disable automation morning brief")
    checks.append(
        (
            "9) Automation rules",
            _contains(create_automation_reply, "automation created")
            and _contains(list_automation_reply, "automation rules")
            and _contains(run_automation_reply, "automation run complete")
            and _contains(automation_history_reply, "automation history")
            and _contains(disable_automation_reply, "disabled"),
            (
                f"{create_automation_reply} | {list_automation_reply} | "
                f"{run_automation_reply} | {automation_history_reply} | {disable_automation_reply}"
            ),
        )
    )

    setup_mobile_reply = _run("setup mobile companion pixel 8")
    send_mobile_reply = _run("send mobile update standup in 10 minutes")
    mobile_status_reply = _run("mobile companion status")
    checks.append(
        (
            "10) Mobile companion",
            _contains(setup_mobile_reply, "mobile companion connected")
            and _contains(send_mobile_reply, "mobile update queued")
            and _contains(mobile_status_reply, "mobile companion active"),
            f"{setup_mobile_reply} | {send_mobile_reply} | {mobile_status_reply}",
        )
    )

    overall_ok = all(item[1] for item in checks)
    return overall_ok, checks


def main():
    overall_ok = True
    with _temporary_data_files():
        flow_ok, checks = run_nextgen_flow()
        overall_ok = overall_ok and flow_ok
        for name, ok, details in checks:
            _print_result(name, ok, details)

    print("\nSummary:")
    print(f"overall_ok={overall_ok}")
    if not overall_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
