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
from core.commands.handlers.config_status import handle_config_status_command
from core.commands.summaries import config as config_summaries
from tests.test_command_router_contacts_handler import _context


class CommandRouterConfigStatusHandlerTests(unittest.TestCase):
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

    def test_config_settings_and_assistant_settings_behavior(self) -> None:
        self._run_router("config status", extra_patches=[patch.object(config_summaries, "config_status_summary", return_value="Config status.")])
        self._run_router("settings status", extra_patches=[patch.object(config_summaries, "settings_status_summary", return_value="Settings status.")])
        self._run_router("show settings", extra_patches=[patch.object(config_summaries, "assistant_settings_summary", return_value="Assistant settings.")])

        self.assertEqual("Config status.", self.spoken[-3])
        self.assertEqual("Settings status.", self.spoken[-2])
        self.assertEqual("Assistant settings.", self.spoken[-1])

    def test_environment_and_feature_toggle_status_behavior(self) -> None:
        self._run_router(
            "environment config readiness",
            extra_patches=[patch.object(config_summaries, "environment_config_readiness_summary", return_value="Environment readiness.")],
        )
        self._run_router("feature toggle summary", extra_patches=[patch.object(config_summaries, "feature_toggle_summary", return_value="Feature toggles.")])

        self.assertEqual("Environment readiness.", self.spoken[-2])
        self.assertEqual("Feature toggles.", self.spoken[-1])

    def test_unknown_config_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "config banana mode",
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

    def test_settings_mutations_and_admin_flows_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "change wake word to hey appa",
            "set active timeout to 30",
            "enable strict wake word",
            "disable strict wake word",
            "enable full settings access",
            "full control mode",
            "run as administrator",
            "start admin mode",
            "update api key",
            "save config",
            "reset settings",
            "change security settings",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_config_status_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
