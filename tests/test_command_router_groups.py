import os
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


class CommandRouterGroupTests(unittest.TestCase):
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

    def _base_patches(self):
        return [
            patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: self.spoken.append(str(message))),
            patch.object(command_router, "play_sound"),
            patch.object(command_router, "log_command", lambda *args, **kwargs: None),
            patch.object(command_router, "remember_emotion_signal", lambda *args, **kwargs: None),
            patch.object(command_router, "set_last_user_input", lambda *args, **kwargs: None),
            patch.object(command_router, "set_last_result", lambda *args, **kwargs: None),
            patch.object(command_router, "validate_command", return_value={"allowed": True, "action": "allow", "message": ""}),
        ]

    def _run_command(self, command: str, installed_apps: dict | None = None, patches: list | None = None) -> None:
        active = self._base_patches()
        active.extend(patches or [])
        try:
            for item in active:
                item.start()
            command_router.process_command(command, installed_apps or {}, input_mode="voice")
        finally:
            for item in reversed(active):
                item.stop()

    def test_greeting_basic_chat_path(self) -> None:
        self._run_command("hello grandpa")

        self.assertTrue(self.spoken)
        self.assertIn("doing good", self.spoken[-1].lower())

    def test_simple_local_intent_path(self) -> None:
        self._run_command(
            "what is date",
            patches=[
                patch.object(
                    command_router,
                    "try_handle_intent",
                    return_value={"handled": True, "reply": "Today's date is test-day."},
                )
            ],
        )

        self.assertEqual("Today's date is test-day.", self.spoken[-1])

    def test_ai_fallback_path(self) -> None:
        self._run_command(
            "tell me a tiny story about debugging",
            patches=[
                patch.object(command_router, "try_handle_intent", return_value={"handled": False, "reply": ""}),
                patch.object(command_router, "is_personal_question", return_value=False),
                patch.object(command_router, "ask_ollama", return_value="Debugging is easier when tests speak first."),
                patch.object(command_router, "_remember_terminal_learning_turn", lambda *args, **kwargs: None),
            ],
        )

        self.assertEqual("Debugging is easier when tests speak first.", self.spoken[-1])

    def test_safe_app_system_command_sample(self) -> None:
        self._run_command(
            "open madeupapp",
            installed_apps={"madeupapp": {"name": "MadeUpApp"}},
            patches=[patch.object(command_router, "_open_scanned_or_known_app", return_value="Opened MadeUpApp.")],
        )

        self.assertEqual("Opened MadeUpApp.", self.spoken[-1])

    def test_dangerous_command_gets_safe_confirmation(self) -> None:
        self._run_command("shutdown")

        self.assertTrue(command_router.pending_confirmation)
        self.assertIn("shut down", self.spoken[-1].lower())

    def test_security_refusal_does_not_continue_to_system_action(self) -> None:
        self._run_command(
            "delete file important.txt",
            patches=[
                patch.object(
                    command_router,
                    "validate_command",
                    return_value={"allowed": False, "action": "block", "message": "Blocked for safety."},
                )
            ],
        )

        self.assertEqual("Blocked for safety.", self.spoken[-1])
        self.assertIsNone(command_router.pending_confirmation)

    def test_unknown_command_does_not_crash_when_ai_provider_fails(self) -> None:
        self._run_command(
            "unmapped command with no handler",
            patches=[
                patch.object(command_router, "try_handle_intent", return_value={"handled": False, "reply": ""}),
                patch.object(command_router, "is_personal_question", return_value=False),
                patch.object(command_router, "ask_ollama", side_effect=RuntimeError("provider down")),
                patch("builtins.print"),
            ],
        )

        self.assertEqual("Something went wrong", self.spoken[-1])

    def test_memory_context_command_path(self) -> None:
        set_memory_patch = patch.object(command_router, "set_memory", return_value=True)
        set_memory = set_memory_patch.start()
        try:
            self._run_command("my name is Priya")
        finally:
            set_memory_patch.stop()

        set_memory.assert_called_once_with("personal.identity.name", "priya")
        self.assertIn("priya", self.spoken[-1].lower())


if __name__ == "__main__":
    unittest.main()
