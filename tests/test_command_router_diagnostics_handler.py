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
from core.commands.handlers.diagnostics import handle_diagnostics_command


class CommandRouterDiagnosticsHandlerTests(unittest.TestCase):
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
        return handle_diagnostics_command(
            command,
            assistant_doctor_summary=kwargs.get("assistant_doctor_summary", lambda include_ready=False: f"Doctor ready={include_ready}."),
            backend_stability_summary=kwargs.get("backend_stability_summary", lambda: "Backend stable."),
            security_status_summary=kwargs.get("security_status_summary", lambda: "Security ready."),
            voice_diagnostics_summary=kwargs.get("voice_diagnostics_summary", lambda: "Voice diagnostics ready."),
            allow_security_voice=kwargs.get("allow_security_voice", True),
            allow_health=kwargs.get("allow_health", True),
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

    def test_assistant_doctor_command_behavior_unchanged(self) -> None:
        self._run_router(
            "assistant doctor",
            extra_patches=[patch.object(command_router, "_assistant_doctor_summary", return_value="Doctor summary.")],
        )

        self.assertEqual("Doctor summary.", self.spoken[-1])

    def test_backend_stability_command_behavior_unchanged(self) -> None:
        self._run_router(
            "backend stability summary",
            extra_patches=[patch.object(command_router, "_backend_stability_summary", return_value="Backend stable.")],
        )

        self.assertEqual("Backend stable.", self.spoken[-1])

    def test_security_status_command_behavior_unchanged(self) -> None:
        self._run_router(
            "security status",
            extra_patches=[patch.object(command_router, "_security_status_summary", return_value="Security ready.")],
        )

        self.assertEqual("Security ready.", self.spoken[-1])

    def test_voice_diagnostics_command_behavior_unchanged(self) -> None:
        self._run_router(
            "voice diagnostics",
            extra_patches=[patch.object(command_router, "_voice_diagnostics_summary", return_value="Voice diagnostics ready.")],
        )

        self.assertEqual("Voice diagnostics ready.", self.spoken[-1])

    def test_unknown_diagnostic_like_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "diagnostic banana status",
            extra_patches=[
                patch.object(command_router, "try_handle_intent", return_value={"handled": False, "reply": ""}),
                patch.object(command_router, "is_personal_question", return_value=False),
                patch.object(command_router, "ask_ollama", ask),
                patch.object(command_router, "_remember_terminal_learning_turn", lambda *args, **kwargs: None),
            ],
        )

        self.assertTrue(ask.called)
        self.assertEqual("Existing fallback reply.", self.spoken[-1])

    def test_no_dangerous_system_command_handled_by_diagnostics_handler(self) -> None:
        for command in ["shutdown", "restart", "open calculator", "delete file test.txt", "lock system"]:
            with self.subTest(command=command):
                self.assertFalse(self._handler(command).handled)

    def test_handler_returns_not_handled_cleanly(self) -> None:
        result = self._handler("status of banana")

        self.assertFalse(result.handled)
        self.assertEqual("", result.reply)
        self.assertEqual("", result.route)


if __name__ == "__main__":
    unittest.main()
