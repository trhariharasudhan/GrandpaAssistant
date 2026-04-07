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
import mobile_companion  # noqa: E402
import productivity.event_module as event_module  # noqa: E402
import productivity.nextgen_module as nextgen_module  # noqa: E402
import productivity.task_module as task_module  # noqa: E402
import productivity_store  # noqa: E402
import utils.config as config_module  # noqa: E402


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
    combined = " | ".join(item for item in responses if item)
    return combined.strip()


def _contains(text, *parts):
    lowered = str(text or "").lower()
    return all(part.lower() in lowered for part in parts)


@contextmanager
def _temporary_data_files():
    original_brain_db_path = brain_database.DB_PATH
    original_store_db_path = productivity_store.DB_PATH
    original_app_db_path = app_data_store.DB_PATH
    original_task_path = task_module.DATA_FILE
    original_event_path = event_module.DATA_FILE
    original_nextgen_path = nextgen_module.DATA_FILE
    original_settings_path = config_module.SETTINGS_PATH
    original_mobile_state_path = mobile_companion.STATE_PATH

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = os.path.join(temp_dir, "assistant.db")
        temp_tasks_path = os.path.join(temp_dir, "tasks.json")
        temp_events_path = os.path.join(temp_dir, "events.json")
        temp_nextgen_path = os.path.join(temp_dir, "nextgen_features.json")
        temp_settings_path = os.path.join(temp_dir, "settings.json")
        temp_mobile_state_path = os.path.join(temp_dir, "mobile_companion.json")

        brain_database.DB_PATH = temp_db_path
        productivity_store.DB_PATH = temp_db_path
        app_data_store.DB_PATH = temp_db_path
        task_module.DATA_FILE = temp_tasks_path
        event_module.DATA_FILE = temp_events_path
        nextgen_module.DATA_FILE = temp_nextgen_path
        config_module.SETTINGS_PATH = temp_settings_path
        config_module._SETTINGS_CACHE = None
        config_module._SETTINGS_CACHE_MTIME = None
        mobile_companion.STATE_PATH = temp_mobile_state_path
        web_api.command_router_module.pending_confirmation = None

        try:
            with open(temp_tasks_path, "w", encoding="utf-8") as file:
                json.dump({"tasks": [], "reminders": []}, file, indent=2)
            with open(temp_events_path, "w", encoding="utf-8") as file:
                json.dump({"events": []}, file, indent=2)
            with open(temp_nextgen_path, "w", encoding="utf-8") as file:
                json.dump({}, file, indent=2)
            with open(temp_settings_path, "w", encoding="utf-8") as file:
                json.dump({}, file, indent=2)
            yield
        finally:
            brain_database.DB_PATH = original_brain_db_path
            productivity_store.DB_PATH = original_store_db_path
            app_data_store.DB_PATH = original_app_db_path
            task_module.DATA_FILE = original_task_path
            event_module.DATA_FILE = original_event_path
            nextgen_module.DATA_FILE = original_nextgen_path
            config_module.SETTINGS_PATH = original_settings_path
            config_module._SETTINGS_CACHE = None
            config_module._SETTINGS_CACHE_MTIME = None
            mobile_companion.STATE_PATH = original_mobile_state_path
            web_api.command_router_module.pending_confirmation = None


def _run_checked(command):
    for _ in range(4):
        reply = _run(command)
        lowered = reply.lower()
        if "please confirm this" in lowered:
            command = "yes"
            continue
        return reply
    return reply


def run_nextgen_flow():
    checks = []

    _run_checked("add task finish proposal deck")
    _run_checked("add reminder pay internet bill in 2 hours")

    day_plan_reply = _run_checked("generate ai day plan")
    checks.append(
        (
            "1) AI day planner",
            _contains(day_plan_reply, "blocks")
            or _contains(day_plan_reply, "planned"),
            day_plan_reply,
        )
    )

    add_habit_reply = _run_checked("add habit gym")
    check_habit_reply = _run_checked("check in habit gym")
    habit_summary_reply = _run_checked("habit dashboard")
    checks.append(
        (
            "2) Habit tracker",
            _contains(add_habit_reply, "habit added")
            and _contains(check_habit_reply, "marked habit done")
            and _contains(habit_summary_reply, "habit score"),
            f"{add_habit_reply} | {check_habit_reply} | {habit_summary_reply}",
        )
    )

    add_goal_reply = _run_checked("add goal launch v2 app")
    add_milestone_reply = _run_checked("add milestone complete ui polish to goal launch v2 app")
    complete_milestone_reply = _run_checked("complete milestone complete ui polish in goal launch v2 app")
    goal_summary_reply = _run_checked("goal board")
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

    reminder_priority_reply = _run_checked("smart reminder priority")
    checks.append(
        (
            "4) Smart reminder priority",
            _contains(reminder_priority_reply, "smart reminder priority")
            or _contains(reminder_priority_reply, "no reminders to rank"),
            reminder_priority_reply,
        )
    )

    apply_voice_trainer_reply = _run_checked("voice trainer noisy")
    voice_trainer_status_reply = _run_checked("voice trainer status")
    checks.append(
        (
            "5) Voice trainer",
            _contains(apply_voice_trainer_reply, "voice trainer applied")
            and _contains(voice_trainer_status_reply, "voice trainer status"),
            f"{apply_voice_trainer_reply} | {voice_trainer_status_reply}",
        )
    )

    set_language_reply = nextgen_module.set_language_mode("tamil")
    preview_language_reply = nextgen_module.preview_language_response("vanakkam macha")
    language_status_reply = nextgen_module.language_mode_status()
    checks.append(
        (
            "6) Language mode",
            _contains(set_language_reply, "supported")
            and _contains(preview_language_reply, "tamil", "reply in english")
            and _contains(language_status_reply, "english"),
            f"{set_language_reply} | {preview_language_reply} | {language_status_reply}",
        )
    )

    capture_meeting_reply = _run_checked("capture meeting product sync: send invoice, review roadmap")
    meeting_summary_reply = _run_checked("meeting summary")
    checks.append(
        (
            "7) Meeting capture",
            _contains(capture_meeting_reply, "meeting saved")
            and _contains(meeting_summary_reply, "meeting summary"),
            f"{capture_meeting_reply} | {meeting_summary_reply}",
        )
    )

    tag_doc_reply = _run_checked("tag document roadmap.pdf as product,planning")
    move_doc_reply = _run_checked("move document roadmap.pdf to folder strategy")
    rag_summary_reply = _run_checked("rag library summary")
    checks.append(
        (
            "8) RAG library manager",
            _contains(tag_doc_reply, "tagged as")
            and _contains(move_doc_reply, "moved")
            and _contains(rag_summary_reply, "rag library"),
            f"{tag_doc_reply} | {move_doc_reply} | {rag_summary_reply}",
        )
    )

    create_automation_reply = _run_checked(
        "create automation morning brief when time is 8 am then send daily summary"
    )
    list_automation_reply = _run_checked("list automations")
    run_automation_reply = _run_checked("run automations now")
    automation_history_reply = _run_checked("automation history")
    disable_automation_reply = _run_checked("disable automation morning brief")
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

    setup_mobile_reply = _run_checked("setup mobile companion pixel 8")
    pairing = mobile_companion.MOBILE_COMPANION.current_pairing_payload(include_code=True)
    if pairing.get("active") and pairing.get("code"):
        mobile_companion.MOBILE_COMPANION.complete_pairing(
            pairing["code"],
            "pixel 8",
            platform="smoke-test",
            app_version="1.0",
        )
    send_mobile_reply = _run_checked("send mobile update standup in 10 minutes")
    mobile_status_reply = _run_checked("mobile companion status")
    checks.append(
        (
            "10) Mobile companion",
            _contains(setup_mobile_reply, "mobile pairing started")
            and _contains(send_mobile_reply, "sent mobile update")
            and (
                _contains(mobile_status_reply, "linked device")
                or _contains(mobile_status_reply, "active connection")
            ),
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
