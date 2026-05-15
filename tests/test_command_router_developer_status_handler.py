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
from core.commands.handlers.developer_status import handle_developer_status_command
from tests.test_command_router_contacts_handler import _context


class CommandRouterDeveloperStatusHandlerTests(unittest.TestCase):
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

    def test_developer_mode_status_behavior(self) -> None:
        self._run_router("developer mode status", extra_patches=[patch.object(command_router, "_developer_mode_status_summary", return_value="Developer mode status.")])

        self.assertEqual("Developer mode status.", self.spoken[-1])

    def test_workspace_coding_status_behavior(self) -> None:
        self._run_router("workspace summary", extra_patches=[patch.object(command_router, "_developer_workspace_summary", return_value="Workspace summary.")])

        self.assertEqual("Workspace summary.", self.spoken[-1])

    def test_git_status_summaries_behavior(self) -> None:
        self._run_router("git status", extra_patches=[patch.object(command_router, "_local_git_status_summary", return_value="Git status.")])
        self._run_router("git branch", extra_patches=[patch.object(command_router, "_git_current_branch_summary", return_value="Git branch.")])
        self._run_router("git remotes", extra_patches=[patch.object(command_router, "_git_remote_summary", return_value="Git remotes.")])
        self._run_router("recent commits", extra_patches=[patch.object(command_router, "_git_recent_commits_summary", return_value="Git recent commits.")])
        self._run_router("git summary", extra_patches=[patch.object(command_router, "_git_repo_summary", return_value="Git repo summary.")])

        self.assertEqual("Git status.", self.spoken[-5])
        self.assertEqual("Git branch.", self.spoken[-4])
        self.assertEqual("Git remotes.", self.spoken[-3])
        self.assertEqual("Git recent commits.", self.spoken[-2])
        self.assertEqual("Git repo summary.", self.spoken[-1])

    def test_unknown_developer_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "developer banana mode",
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

    def test_git_file_terminal_and_setting_mutations_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "git add .",
            "git commit",
            "git push",
            "git pull",
            "git reset hard",
            "save and run current file",
            "developer save and run",
            "run current file",
            "open terminal",
            "start terminal",
            "enable developer mode",
            "disable developer mode",
            "set developer mode",
            "write file app.py",
            "edit file app.py",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_developer_status_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
