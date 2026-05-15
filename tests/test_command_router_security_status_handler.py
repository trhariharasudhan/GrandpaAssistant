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
from core.commands.handlers.security_status import handle_security_status_command
from tests.test_command_router_contacts_handler import _context


class CommandRouterSecurityStatusHandlerTests(unittest.TestCase):
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

    def test_security_status_behavior(self) -> None:
        self._run_router("security status", extra_patches=[patch.object(command_router, "_security_status_summary", return_value="Security ready.")])

        self.assertEqual("Security ready.", self.spoken[-1])

    def test_auth_status_behavior(self) -> None:
        self._run_router("voice auth status", extra_patches=[patch.object(command_router, "_voice_auth_status_summary", return_value="Voice auth ready.")])

        self.assertEqual("Voice auth ready.", self.spoken[-1])

    def test_permission_status_behavior(self) -> None:
        self._run_router("admin status", extra_patches=[patch.object(command_router, "_admin_permission_status_summary", return_value="Admin permission status.")])

        self.assertEqual("Admin permission status.", self.spoken[-1])

    def test_trust_security_readiness_summary_behavior(self) -> None:
        self._run_router("security admin status", extra_patches=[patch.object(command_router, "_security_admin_status_summary", return_value="Security admin status.")])

        self.assertEqual("Security admin status.", self.spoken[-1])

    def test_security_logs_and_alerts_behavior(self) -> None:
        self._run_router("security alerts", extra_patches=[patch.object(command_router, "_security_alerts_summary", return_value="Security alerts.")])
        self._run_router("security logs", extra_patches=[patch.object(command_router, "_security_logs_summary", return_value="Security logs.")])

        self.assertEqual("Security alerts.", self.spoken[-2])
        self.assertEqual("Security logs.", self.spoken[-1])

    def test_unknown_security_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "security banana mode",
            extra_patches=[
                patch.object(command_router, "try_handle_intent", return_value={"handled": False, "reply": ""}),
                patch.object(command_router, "handle_calendar_queries", return_value=False),
                patch.object(command_router, "is_personal_question", return_value=False),
                patch.object(command_router, "ask_ollama", ask),
                patch.object(command_router, "_remember_terminal_learning_turn", lambda *args, **kwargs: None),
            ],
        )

        self.assertTrue(ask.called)
        self.assertEqual("Existing fallback reply.", self.spoken[-1])

    def test_auth_lock_unlock_permission_mutation_commands_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "authenticate my voice",
            "verify my voice",
            "unlock assistant",
            "lock system",
            "enable security admin mode",
            "disable security admin mode",
            "trust device usb",
            "approve device usb",
            "set security pin to 1234",
            "change security settings",
            "clear security logs",
            "emergency lockdown",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_security_status_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
