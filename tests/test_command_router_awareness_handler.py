import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


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
from core.commands.handlers.awareness import handle_awareness_command


def _context() -> CommandContext:
    return CommandContext(
        get_period=lambda: "It is morning.",
        tell_joke=lambda: "joke",
        wikipedia_search=lambda value: value,
        get_memory=lambda key: None,
        set_memory=lambda key, value: True,
        semantic_memory_summary=lambda: "semantic",
        semantic_memory_lookup=lambda query: "semantic lookup",
        assistant_doctor_summary=lambda include_ready=False: "doctor",
        backend_stability_summary=lambda: "backend",
        security_status_summary=lambda: "security",
        voice_diagnostics_summary=lambda: "voice diagnostics",
        current_debug_session_summary=lambda: "debug",
        debug_dashboard_summary=lambda: "dashboard",
        fix_approval_summary=lambda: "approvals",
        fix_audit_summary=lambda: "audit",
        debug_timeline_summary=lambda: "timeline",
        debug_search_summary=lambda query: "search",
        reuse_suggestions_summary=lambda language="auto": "reuse",
        debug_learning_summary=lambda: "learning",
        debug_checklist_summary=lambda language="auto": "checklist",
        offline_mode_status_summary=lambda: "offline",
        offline_help_summary=lambda: "offline help",
        offline_ai_status_summary=lambda: "offline ai",
        developer_mode_status_summary=lambda: "developer",
        focus_mode_status_summary=lambda: "focus",
        voice_trainer_status_summary=lambda: "voice trainer",
        piper_setup_summary=lambda: "piper",
        custom_voice_setup_summary=lambda: "custom voice",
        custom_voice_license_status_summary=lambda: "license",
        custom_voice_samples_summary=lambda: "samples",
        voice_status_summary=lambda: "voice",
        developer_workspace_summary=lambda: "workspace",
        planner_focus_summary=lambda: "planner",
        reminder_timeline_summary=lambda: "timeline",
        habit_dashboard_summary=lambda: "habit",
        goal_board_summary=lambda: "goal",
        smart_reminder_priority_summary=lambda: "smart reminders",
        automation_history_summary=lambda: "automation",
        mobile_companion_status_summary=lambda: "mobile",
        language_mode_status_summary=lambda: "language",
        meeting_mode_summary=lambda: "meeting",
        rag_library_summary=lambda: "rag",
        proactive_suggestions_summary=lambda: "suggestions",
        knowledge_review_queue_summary=lambda: "knowledge",
        learning_status_summary=lambda: "learning status",
        phone_link_status_summary=lambda: "phone",
        face_security_status_summary=lambda: "face",
        startup_auto_launch_status_summary=lambda: "startup",
        smart_home_setup_summary=lambda: "smart home",
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


class CommandRouterAwarenessHandlerTests(unittest.TestCase):
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

    def test_active_window_summary_behavior(self) -> None:
        self._run_router("active window", extra_patches=[patch.object(command_router, "_active_window_summary", return_value="Active window summary.")])

        self.assertEqual("Active window summary.", self.spoken[-1])

    def test_active_window_tamil_language_behavior(self) -> None:
        seen = []

        def fake_summary(language="auto"):
            seen.append(language)
            return "Tamil active window summary."

        self._run_router("naan enna app use panren", extra_patches=[patch.object(command_router, "_active_window_summary", side_effect=fake_summary)])

        self.assertEqual(["ta"], seen)
        self.assertEqual("Tamil active window summary.", self.spoken[-1])

    def test_screen_and_visible_text_capture_commands_are_not_handled(self) -> None:
        context = _context()
        for command in ["what is on my screen", "explain my screen", "read my screen", "summarize this screen"]:
            with self.subTest(command=command):
                self.assertFalse(handle_awareness_command(command, context).handled)

    def test_object_detection_capture_commands_are_not_handled(self) -> None:
        context = _context()
        for command in ["object detection status", "detected objects", "what objects do you see", "what do you see on camera"]:
            with self.subTest(command=command):
                self.assertFalse(handle_awareness_command(command, context).handled)

    def test_capture_and_action_commands_are_not_handled(self) -> None:
        context = _context()
        for command in ["take screenshot", "scan screen", "ocr now", "detect object now", "click ok", "type hello"]:
            with self.subTest(command=command):
                self.assertFalse(handle_awareness_command(command, context).handled)

    def test_unknown_awareness_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "awareness banana mode",
            extra_patches=[
                patch.object(command_router, "try_handle_intent", return_value={"handled": False, "reply": ""}),
                patch.object(command_router, "is_personal_question", return_value=False),
                patch.object(command_router, "ask_ollama", ask),
                patch.object(command_router, "_remember_terminal_learning_turn", lambda *args, **kwargs: None),
            ],
        )

        self.assertTrue(ask.called)
        self.assertEqual("Existing fallback reply.", self.spoken[-1])


if __name__ == "__main__":
    unittest.main()
