import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
APP_DIR = BACKEND_DIR / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in [BACKEND_DIR, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from core import command_router
from core.commands.context import CommandContext
from core.commands.handlers.diagnostics import handle_diagnostics_command
from core.commands.handlers.knowledge import handle_knowledge_command
from core.commands.handlers.memory import handle_memory_command
from core.commands.handlers.security_status import handle_security_status_command
from core.commands.registry import CommandHandlerRegistry
from core.commands.result import CommandResult


def _context() -> CommandContext:
    return CommandContext(
        get_period=lambda: "It is morning.",
        tell_joke=lambda: "Test joke.",
        wikipedia_search=lambda value: f"Wiki {value}.",
        get_memory=lambda _key: "Priya",
        set_memory=lambda _key, _value: True,
        semantic_memory_summary=lambda: "Semantic ready.",
        semantic_memory_lookup=lambda query: f"Semantic {query}.",
        assistant_doctor_summary=lambda include_ready=False: f"Doctor {include_ready}.",
        backend_stability_summary=lambda: "Backend stable.",
        security_status_summary=lambda: "Security ready.",
        voice_diagnostics_summary=lambda: "Voice ready.",
        current_debug_session_summary=lambda: "Debug session.",
        debug_dashboard_summary=lambda: "Debug dashboard.",
        fix_approval_summary=lambda: "Fix approvals.",
        fix_audit_summary=lambda: "Fix audit.",
        debug_timeline_summary=lambda: "Debug timeline.",
        debug_search_summary=lambda query: f"Debug search {query}.",
        reuse_suggestions_summary=lambda language="auto": f"Reuse {language}.",
        debug_learning_summary=lambda: "Debug learning.",
        debug_checklist_summary=lambda language="auto": f"Checklist {language}.",
        offline_mode_status_summary=lambda: "Offline mode.",
        offline_help_summary=lambda: "Offline help.",
        offline_ai_status_summary=lambda: "Offline AI.",
        developer_mode_status_summary=lambda: "Developer mode.",
        focus_mode_status_summary=lambda: "Focus mode.",
        voice_trainer_status_summary=lambda: "Voice trainer.",
        piper_setup_summary=lambda: "Piper setup.",
        custom_voice_setup_summary=lambda: "Custom voice setup.",
        custom_voice_license_status_summary=lambda: "Custom voice license.",
        custom_voice_samples_summary=lambda: "Custom voice samples.",
        voice_status_summary=lambda: "Voice status.",
        developer_workspace_summary=lambda: "Developer workspace.",
        planner_focus_summary=lambda: "Planner focus.",
        reminder_timeline_summary=lambda: "Reminder timeline.",
        habit_dashboard_summary=lambda: "Habit dashboard.",
        goal_board_summary=lambda: "Goal board.",
        smart_reminder_priority_summary=lambda: "Smart reminders.",
        automation_history_summary=lambda: "Automation history.",
        mobile_companion_status_summary=lambda: "Mobile status.",
        language_mode_status_summary=lambda: "Language status.",
        meeting_mode_summary=lambda: "Meeting summary.",
        rag_library_summary=lambda: "RAG library.",
        proactive_suggestions_summary=lambda: "Proactive suggestions.",
        knowledge_review_queue_summary=lambda: "Knowledge review.",
        learning_status_summary=lambda: "Learning status.",
        phone_link_status_summary=lambda: "Phone link.",
        face_security_status_summary=lambda: "Face security.",
        startup_auto_launch_status_summary=lambda: "Startup auto launch.",
        smart_home_setup_summary=lambda: "Smart home setup.",
        active_window_summary=lambda language="auto": f"Active window {language}.",
        local_contacts_summary=lambda: "Local contacts.",
        local_contact_lookup_summary=lambda query: f"Local contact {query}.",
        google_contacts_summary=lambda: "Google contacts.",
        google_contact_changes_summary=lambda: "Google contact changes.",
        favorite_contacts_summary=lambda: "Favorite contacts.",
        contact_aliases_summary=lambda: "Contact aliases.",
        calendar_query_summary=lambda command: None,
        google_calendar_status_summary=lambda: "Google calendar status.",
        google_calendar_today_summary=lambda: "Today calendar.",
        google_calendar_upcoming_summary=lambda: "Upcoming calendar.",
        google_calendar_titles_summary=lambda: "Calendar titles.",
        storage_report_summary=lambda: "Storage report.",
        storage_cleanup_suggestion_summary=lambda: "Storage cleanup.",
        system_status_summary=lambda: "System status.",
        cpu_status_summary=lambda: "CPU status.",
        ram_status_summary=lambda: "RAM status.",
        disk_status_summary=lambda: "Disk status.",
        battery_status_summary=lambda: "Battery status.",
        hardware_status_summary=lambda: "Hardware status.",
        hardware_event_history_summary=lambda: "Hardware events.",
        smart_home_status_summary=lambda: "Smart Home status.",
        iot_awareness_summary=lambda: "IoT inventory.",
        iot_action_history_summary=lambda: "IoT history.",
        security_alerts_summary=lambda: "Security alerts.",
        security_logs_summary=lambda: "Security logs.",
        voice_auth_status_summary=lambda: "Voice auth status.",
        security_admin_status_summary=lambda: "Security admin status.",
        admin_permission_status_summary=lambda: "Admin permission status.",
        emergency_mode_status_summary=lambda: "Emergency mode status.",
        emergency_quick_response_summary=lambda: "Emergency quick response.",
        emergency_protocol_summary=lambda: "Emergency protocol.",
        profile_summary=lambda: "Profile summary.",
        personal_snapshot_summary=lambda: "Personal snapshot.",
        preferred_language_summary=lambda: "Preferred language.",
        preferred_tone_summary=lambda: "Preferred tone.",
        git_status_summary=lambda: "Git status.",
        git_branch_summary=lambda: "Git branch.",
        git_remotes_summary=lambda: "Git remotes.",
        git_recent_commits_summary=lambda: "Git recent commits.",
        git_repo_summary=lambda: "Git repo summary.",
    )


class CommandHandlerRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_pending = command_router.pending_confirmation
        self.original_pending_map = dict(command_router.pending_confirmations)
        command_router.pending_confirmation = None
        command_router.pending_confirmations.clear()
        self.spoken: list[str] = []

    def tearDown(self) -> None:
        command_router.pending_confirmation = self.original_pending
        command_router.pending_confirmations.clear()
        command_router.pending_confirmations.update(self.original_pending_map)

    def _run_router(self, command: str, extra_patches: list | None = None) -> None:
        patches = [
            patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: self.spoken.append(str(message))),
            patch.object(command_router, "play_sound"),
            patch.object(command_router, "log_command", lambda *args, **kwargs: None),
            patch.object(command_router, "remember_emotion_signal", lambda *args, **kwargs: None),
            patch.object(command_router, "set_last_user_input", lambda *args, **kwargs: None),
            patch.object(command_router, "set_last_result", lambda *args, **kwargs: None),
            patch.object(command_router, "validate_command", return_value={"allowed": True, "action": "allow", "message": ""}),
        ]
        patches.extend(extra_patches or [])
        try:
            for item in patches:
                item.start()
            command_router.process_command(command, {}, input_mode="voice")
        finally:
            for item in reversed(patches):
                item.stop()

    def test_handler_order_is_preserved(self) -> None:
        seen = []

        def first(command, context):
            seen.append("first")
            return CommandResult.not_handled()

        def second(command, context):
            seen.append("second")
            return CommandResult(True, "handled")

        registry = CommandHandlerRegistry([first, second])

        result = registry.handle("hello", _context())

        self.assertEqual(["first", "second"], seen)
        self.assertTrue(result.handled)
        self.assertEqual("handled", result.reply)

    def test_first_handled_result_stops_chain(self) -> None:
        seen = []

        def first(command, context):
            seen.append("first")
            return CommandResult(True, "first reply")

        def second(command, context):
            seen.append("second")
            return CommandResult(True, "second reply")

        result = CommandHandlerRegistry([first, second]).handle("hello", _context())

        self.assertEqual(["first"], seen)
        self.assertEqual("first reply", result.reply)

    def test_not_handled_falls_through(self) -> None:
        result = CommandHandlerRegistry([lambda command, context: CommandResult.not_handled()]).handle("unknown", _context())

        self.assertFalse(result.handled)
        self.assertEqual("", result.reply)

    def test_context_callbacks_are_available_to_handlers(self) -> None:
        context = _context()

        self.assertEqual("Test joke.", handle_knowledge_command("tell me a joke", context).reply)
        self.assertEqual("You are Priya", handle_memory_command("what is my name", context).reply)
        self.assertEqual("Security ready.", handle_security_status_command("security status", context).reply)

    def test_command_router_behavior_unchanged_for_extracted_commands(self) -> None:
        self._run_router("hello grandpa")
        self._run_router("what is my name", extra_patches=[patch.object(command_router, "get_memory", return_value="Priya")])
        self._run_router("security status", extra_patches=[patch.object(command_router, "_security_status_summary", return_value="Security ready.")])

        self.assertEqual("Hey! I am doing good. How are you?", self.spoken[0])
        self.assertEqual("You are Priya", self.spoken[1])
        self.assertEqual("Security ready.", self.spoken[2])

    def test_dangerous_command_is_not_swallowed_by_registry(self) -> None:
        context = _context()
        registry = CommandHandlerRegistry([handle_knowledge_command, handle_memory_command, handle_security_status_command, handle_diagnostics_command])

        result = registry.handle("shutdown", context)

        self.assertFalse(result.handled)


if __name__ == "__main__":
    unittest.main()
