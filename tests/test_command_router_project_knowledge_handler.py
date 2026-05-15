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
from core.commands.handlers.project_knowledge import handle_project_knowledge_command
from tests.test_command_router_contacts_handler import _context


class CommandRouterProjectKnowledgeHandlerTests(unittest.TestCase):
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

    def test_project_knowledge_library_status_behavior(self) -> None:
        self._run_router("rag library", extra_patches=[patch.object(command_router, "rag_library_summary", return_value="RAG library.")])

        self.assertEqual("RAG library.", self.spoken[-1])

    def test_local_knowledge_review_summary_behavior(self) -> None:
        self._run_router("show knowledge review queue", extra_patches=[patch.object(command_router, "_knowledge_review_queue_summary", return_value="Knowledge review queue is empty.")])

        self.assertEqual("Knowledge review queue is empty.", self.spoken[-1])

    def test_local_file_storage_summary_behavior(self) -> None:
        self._run_router("storage report", extra_patches=[patch.object(command_router, "get_storage_report", return_value="Storage report.")])
        self._run_router("cleanup suggestion", extra_patches=[patch.object(command_router, "get_cleanup_suggestion", return_value="Storage cleanup.")])

        self.assertEqual("Storage report.", self.spoken[-2])
        self.assertEqual("Storage cleanup.", self.spoken[-1])

    def test_unknown_project_knowledge_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "project knowledge banana mode",
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

    def test_indexing_file_mutation_and_rag_action_commands_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "index project files",
            "reindex files",
            "add knowledge answer category=science",
            "clear knowledge review item abc",
            "delete knowledge science",
            "create file notes.txt",
            "edit file notes.txt",
            "delete file notes.txt",
            "move file notes.txt",
            "tag document report as work",
            "move document report to folder archive",
            "ask document report what changed",
            "search document report for invoice",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_project_knowledge_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
