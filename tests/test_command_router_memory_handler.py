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
from core.commands.handlers.memory import handle_memory_command


class CommandRouterMemoryHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_pending = command_router.pending_confirmation
        self.original_pending_map = dict(command_router.pending_confirmations)
        command_router.pending_confirmation = None
        command_router.pending_confirmations.clear()
        self.spoken: list[str] = []
        self.last_results: list[str] = []

    def tearDown(self) -> None:
        command_router.pending_confirmation = self.original_pending
        command_router.pending_confirmations.clear()
        command_router.pending_confirmations.update(self.original_pending_map)

    def _handler(self, command: str, **kwargs):
        return handle_memory_command(
            command,
            get_memory=kwargs.get("get_memory", lambda _key: None),
            set_memory=kwargs.get("set_memory", lambda _key, _value: True),
            semantic_memory_summary=kwargs.get("semantic_memory_summary", lambda: "Semantic memory ready."),
            semantic_memory_lookup=kwargs.get("semantic_memory_lookup", lambda query: f"Semantic result for {query}."),
            allow_personal=kwargs.get("allow_personal", True),
            allow_semantic=kwargs.get("allow_semantic", True),
        )

    def _run_router(self, command: str, extra_patches: list | None = None) -> None:
        patches = [
            patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: self.spoken.append(str(message))),
            patch.object(command_router, "play_sound"),
            patch.object(command_router, "log_command", lambda *args, **kwargs: None),
            patch.object(command_router, "remember_emotion_signal", lambda *args, **kwargs: None),
            patch.object(command_router, "set_last_user_input", lambda *args, **kwargs: None),
            patch.object(command_router, "set_last_result", side_effect=lambda value: self.last_results.append(str(value))),
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

    def test_saving_user_name_behavior_unchanged(self) -> None:
        saved = {}

        def save_value(key, value):
            saved[key] = value
            return True

        self._run_router("my name is Priya", extra_patches=[patch.object(command_router, "set_memory", side_effect=save_value)])

        self.assertEqual({"personal.identity.name": "priya"}, saved)
        self.assertEqual("Okay, I will remember that your name is priya", self.spoken[-1])

    def test_asking_saved_name_behavior_unchanged(self) -> None:
        self._run_router("what is my name", extra_patches=[patch.object(command_router, "get_memory", return_value="priya")])

        self.assertEqual("You are priya", self.spoken[-1])

    def test_unknown_memory_query_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback handled it.")
        self._run_router(
            "memory banana query",
            extra_patches=[
                patch.object(command_router, "try_handle_intent", return_value={"handled": False, "reply": ""}),
                patch.object(command_router, "is_personal_question", return_value=False),
                patch.object(command_router, "ask_ollama", ask),
                patch.object(command_router, "_remember_terminal_learning_turn", lambda *args, **kwargs: None),
            ],
        )

        self.assertTrue(ask.called)
        self.assertEqual("Existing fallback handled it.", self.spoken[-1])

    def test_empty_invalid_memory_command_does_not_crash(self) -> None:
        result = self._handler("")

        self.assertFalse(result.handled)
        self.assertEqual("", result.reply)

    def test_semantic_memory_status_and_search_are_read_only(self) -> None:
        status = self._handler("semantic memory status", semantic_memory_summary=lambda: "Semantic status text.")
        search = self._handler("search my memory for FastAPI", semantic_memory_lookup=lambda query: f"Found {query}.")

        self.assertTrue(status.handled)
        self.assertEqual("Semantic status text.", status.reply)
        self.assertTrue(status.metadata["set_last_result"])
        self.assertTrue(search.handled)
        self.assertEqual("Found fastapi.", search.reply)
        self.assertTrue(search.metadata["set_last_result"])

    def test_semantic_memory_router_sets_last_result(self) -> None:
        self._run_router(
            "semantic memory status",
            extra_patches=[patch.object(command_router, "_semantic_memory_summary", return_value="Semantic status text.")],
        )

        self.assertEqual("Semantic status text.", self.spoken[-1])
        self.assertEqual(["Semantic status text."], self.last_results)

    def test_no_system_dangerous_commands_handled_by_memory_handler(self) -> None:
        for command in ["clear memory", "shutdown", "restart", "delete file test.txt", "open calculator"]:
            with self.subTest(command=command):
                self.assertFalse(self._handler(command).handled)


if __name__ == "__main__":
    unittest.main()
