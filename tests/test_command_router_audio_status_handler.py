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
from core.commands.handlers.audio_status import handle_audio_status_command
from core.commands.summaries import audio as audio_summaries
from tests.test_command_router_contacts_handler import _context


class CommandRouterAudioStatusHandlerTests(unittest.TestCase):
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

    def test_sound_audio_and_chime_status_behavior(self) -> None:
        self._run_router("sound status", extra_patches=[patch.object(audio_summaries, "sound_status_summary", return_value="Sound status.")])
        self._run_router("audio status", extra_patches=[patch.object(audio_summaries, "audio_status_summary", return_value="Audio status.")])
        self._run_router("chime status", extra_patches=[patch.object(audio_summaries, "chime_status_summary", return_value="Chime status.")])

        self.assertEqual("Sound status.", self.spoken[-3])
        self.assertEqual("Audio status.", self.spoken[-2])
        self.assertEqual("Chime status.", self.spoken[-1])

    def test_notification_sound_and_voice_audio_readiness_behavior(self) -> None:
        self._run_router("notification sound status", extra_patches=[patch.object(audio_summaries, "notification_sound_summary", return_value="Notification sound status.")])
        self._run_router("voice audio readiness", extra_patches=[patch.object(audio_summaries, "voice_audio_readiness_summary", return_value="Voice audio readiness.")])

        self.assertEqual("Notification sound status.", self.spoken[-2])
        self.assertEqual("Voice audio readiness.", self.spoken[-1])

    def test_unknown_audio_command_falls_through(self) -> None:
        ask = Mock(return_value="Existing fallback reply.")
        self._run_router(
            "audio banana mode",
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

    def test_audio_mutations_and_playback_are_not_handled(self) -> None:
        context = _context()
        for command in [
            "play sound",
            "play chime",
            "test sound",
            "enable sounds",
            "disable sounds",
            "turn on voice chime",
            "turn off voice chime",
            "set voice mode to sensitive",
            "change tts backend to piper",
            "start listening",
            "stop listening",
            "record microphone",
            "listen now",
            "speak hello",
        ]:
            with self.subTest(command=command):
                self.assertFalse(handle_audio_status_command(command, context).handled)


if __name__ == "__main__":
    unittest.main()
