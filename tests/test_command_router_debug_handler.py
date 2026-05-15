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
from core.commands.handlers.debug import handle_debug_command


class CommandRouterDebugHandlerTests(unittest.TestCase):
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

    def _handler(self, command: str, **kwargs):
        return handle_debug_command(
            command,
            current_debug_session_summary=kwargs.get("current_debug_session_summary", lambda: "Debug session summary."),
            debug_dashboard_summary=kwargs.get("debug_dashboard_summary", lambda: "Debug dashboard."),
            fix_approval_summary=kwargs.get("fix_approval_summary", lambda: "No pending fix approvals."),
            fix_audit_summary=kwargs.get("fix_audit_summary", lambda: "Fix audit log."),
            allow_session_dashboard=kwargs.get("allow_session_dashboard", True),
            allow_fix_read_only=kwargs.get("allow_fix_read_only", True),
        )

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

    def test_debug_session_summary_behavior_unchanged(self) -> None:
        self._run_router(
            "debug session summary",
            extra_patches=[patch.object(command_router, "summarize_current_debug_session", return_value="Debug session summary.")],
        )

        self.assertEqual("Debug session summary.", self.spoken[-1])

    def test_debug_dashboard_behavior_unchanged(self) -> None:
        self._run_router(
            "debug dashboard",
            extra_patches=[
                patch.object(command_router, "build_debug_health_dashboard", return_value={"ok": True}),
                patch.object(command_router, "summarize_debug_health_dashboard", return_value="Debug dashboard."),
            ],
        )

        self.assertEqual("Debug dashboard.", self.spoken[-1])

    def test_fix_approvals_summary_behavior_unchanged(self) -> None:
        self._run_router(
            "show fix approvals",
            extra_patches=[patch.object(command_router, "_fix_approval_summary", return_value="No pending fix approvals.")],
        )

        self.assertEqual("No pending fix approvals.", self.spoken[-1])

    def test_fix_audit_read_only_behavior_unchanged(self) -> None:
        self._run_router(
            "fix audit",
            extra_patches=[patch.object(command_router, "summarize_fix_audit_log", return_value="Fix audit log.")],
        )

        self.assertEqual("Fix audit log.", self.spoken[-1])

    def test_unknown_debug_like_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "debug banana status",
            extra_patches=[
                patch.object(command_router, "try_handle_intent", return_value={"handled": False, "reply": ""}),
                patch.object(command_router, "is_personal_question", return_value=False),
                patch.object(command_router, "ask_ollama", ask),
                patch.object(command_router, "_remember_terminal_learning_turn", lambda *args, **kwargs: None),
            ],
        )

        self.assertTrue(ask.called)
        self.assertEqual("Existing fallback reply.", self.spoken[-1])

    def test_dangerous_fix_commands_are_not_handled_by_debug_handler(self) -> None:
        for command in ["apply fix", "apply suggested fix", "dismiss fix abc123", "allow abc123", "rollback fix"]:
            with self.subTest(command=command):
                self.assertFalse(self._handler(command).handled)

    def test_handler_returns_not_handled_cleanly(self) -> None:
        result = self._handler("debug banana status")

        self.assertFalse(result.handled)
        self.assertEqual("", result.reply)
        self.assertEqual("", result.route)


if __name__ == "__main__":
    unittest.main()
