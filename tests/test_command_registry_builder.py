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
from core.commands.registry import DEFAULT_READONLY_GROUPS, build_readonly_registry
from tests.test_command_router_contacts_handler import _context


class CommandRegistryBuilderTests(unittest.TestCase):
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

    def test_default_order_is_stable(self) -> None:
        self.assertEqual(
            (
                "knowledge",
                "memory",
                "diagnostics",
                "debug",
                "status",
                "productivity",
                "knowledge_services",
                "device_status",
                "awareness",
                "contacts",
                "planning",
                "project_knowledge",
                "system_health",
                "iot_status",
                "security_status",
                "emergency_status",
                "profile_status",
                "developer_status",
                "notification_status",
                "audio_status",
                "overlay_status",
                "interface_status",
                "config_status",
            ),
            DEFAULT_READONLY_GROUPS,
        )
        result = build_readonly_registry(_context()).handle("hello", _context())

        self.assertTrue(result.handled)
        self.assertEqual("knowledge.greeting", result.route)

    def test_named_subset_order_is_stable(self) -> None:
        context = _context()
        registry = build_readonly_registry(context, ["status", "knowledge"])

        self.assertEqual("status.offline_help", registry.handle("offline help", context).route)
        self.assertEqual("knowledge.greeting", registry.handle("hello", context).route)

    def test_unknown_group_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown read-only command handler group"):
            build_readonly_registry(_context(), ["not_a_group"])

    def test_command_router_extracted_behavior_unchanged(self) -> None:
        self._run_router("hello grandpa")
        self._run_router("offline help")
        self._run_router("active window", extra_patches=[patch.object(command_router, "_active_window_summary", return_value="Active window summary.")])
        self._run_router("list contacts", extra_patches=[patch.object(command_router, "list_contacts", return_value=[])])

        self.assertEqual("Hey! I am doing good. How are you?", self.spoken[-4])
        self.assertTrue(self.spoken[-3].startswith("Offline quick help:"))
        self.assertEqual("Active window summary.", self.spoken[-2])
        self.assertEqual("No contacts saved yet. Say add contact <name> <phone>.", self.spoken[-1])

    def test_dangerous_action_commands_still_fall_through(self) -> None:
        context = _context()
        registry = build_readonly_registry(context)

        for command in ["shutdown", "call Priya", "delete contact Priya", "read my screen", "run automations now"]:
            with self.subTest(command=command):
                self.assertFalse(registry.handle(command, context).handled)

    def test_command_router_action_command_still_reaches_fallback(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "registry banana mode",
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
