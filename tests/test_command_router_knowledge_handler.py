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
from core.commands.handlers.knowledge import handle_knowledge_command


class CommandRouterKnowledgeHandlerTests(unittest.TestCase):
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

    def _handler(self, command: str):
        return handle_knowledge_command(
            command,
            get_period=lambda: "It is morning.",
            tell_joke=lambda: "Test joke.",
            wikipedia_search=lambda value: f"Wiki: {value}",
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

    def test_greeting_behavior_unchanged_through_router(self) -> None:
        self._run_router("hello grandpa")

        self.assertEqual("Hey! I am doing good. How are you?", self.spoken[-1])

    def test_handler_math_or_local_intent_not_claimed_when_unknown(self) -> None:
        result = self._handler("2 + 2")

        self.assertFalse(result.handled)
        self.assertEqual("", result.reply)

    def test_local_date_intent_behavior_still_stays_in_existing_router_path(self) -> None:
        self._run_router(
            "what is date",
            extra_patches=[
                patch.object(
                    command_router,
                    "try_handle_intent",
                    return_value={"handled": True, "reply": "Today's date is test-day."},
                )
            ],
        )

        self.assertEqual("Today's date is test-day.", self.spoken[-1])

    def test_unknown_command_falls_through_to_existing_ai_path(self) -> None:
        ask = Mock(return_value="Existing AI fallback reply.")
        self._run_router(
            "unhandled local knowledge phrase",
            extra_patches=[
                patch.object(command_router, "try_handle_intent", return_value={"handled": False, "reply": ""}),
                patch.object(command_router, "is_personal_question", return_value=False),
                patch.object(command_router, "ask_ollama", ask),
                patch.object(command_router, "_remember_terminal_learning_turn", lambda *args, **kwargs: None),
            ],
        )

        self.assertTrue(ask.called)
        self.assertEqual("Existing AI fallback reply.", self.spoken[-1])

    def test_dangerous_system_command_not_handled_by_knowledge_handler(self) -> None:
        for command in ["shutdown", "restart", "delete file test.txt", "open calculator", "close notepad"]:
            with self.subTest(command=command):
                result = self._handler(command)
                self.assertFalse(result.handled)

    def test_handler_returns_not_handled_cleanly(self) -> None:
        result = self._handler("please route this somewhere else")

        self.assertFalse(result.handled)
        self.assertEqual("", result.reply)
        self.assertEqual("", result.route)


if __name__ == "__main__":
    unittest.main()
