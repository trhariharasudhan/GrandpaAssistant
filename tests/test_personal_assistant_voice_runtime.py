import os
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
for path in [APP_DIR, SHARED_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from core.personal_assistant import executor, voice_runtime
from core.personal_assistant.context import clear_personal_assistant_contexts_for_tests
from core.personal_assistant.service import handle_personal_assistant_message
from core.personal_assistant.tool_registry import list_available_tools


class VoiceRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_personal_assistant_contexts_for_tests()
        self.old_enabled = os.environ.pop(voice_runtime.VOICE_RUNTIME_ENABLED_ENV, None)
        self.old_wake = os.environ.pop(voice_runtime.WAKE_WORD_ENV, None)
        self.action_calls = []

    def tearDown(self) -> None:
        voice_runtime.stop_global_voice_runtime(timeout=0.5)
        clear_personal_assistant_contexts_for_tests()
        if self.old_enabled is None:
            os.environ.pop(voice_runtime.VOICE_RUNTIME_ENABLED_ENV, None)
        else:
            os.environ[voice_runtime.VOICE_RUNTIME_ENABLED_ENV] = self.old_enabled
        if self.old_wake is None:
            os.environ.pop(voice_runtime.WAKE_WORD_ENV, None)
        else:
            os.environ[voice_runtime.WAKE_WORD_ENV] = self.old_wake

    def _fake_action(self, payload):
        self.action_calls.append(payload)
        return {"ok": True, "message": "Reduced the system volume.", "data": {"operation": (payload.get("params") or {}).get("operation")}}

    def test_runtime_disabled_by_default(self) -> None:
        manager = voice_runtime.VoiceRuntimeManager(adapters=voice_runtime.VoiceRuntimeAdapters(), idle_sleep_seconds=0.01)

        self.assertFalse(voice_runtime.is_voice_runtime_enabled())
        self.assertFalse(manager.start())
        self.assertFalse(manager.is_running())

    def test_runtime_starts_stops_and_prevents_duplicate_instances(self) -> None:
        started = threading.Event()

        def listen_for_wake():
            started.set()
            return None

        manager = voice_runtime.VoiceRuntimeManager(
            adapters=voice_runtime.VoiceRuntimeAdapters(listen_for_wake=listen_for_wake),
            idle_sleep_seconds=0.01,
        )

        self.assertTrue(manager.start(enabled=True))
        self.assertTrue(started.wait(1.0))
        self.assertTrue(manager.is_running())
        self.assertFalse(manager.start(enabled=True))
        self.assertTrue(manager.stop(timeout=1.0))
        self.assertFalse(manager.is_running())

    def test_wake_word_detection_routes_command_through_assistant_pipeline(self) -> None:
        spoken = []
        with patch.object(executor.local_action_executor, "execute_local_action", side_effect=self._fake_action):
            manager = voice_runtime.VoiceRuntimeManager(
                adapters=voice_runtime.VoiceRuntimeAdapters(
                    listen_for_wake=lambda: "Hey Grandpa reduce volume",
                    listen_for_command=lambda: "",
                    speak=lambda text: spoken.append(text),
                    handle_command=lambda command: handle_personal_assistant_message(command, session_id="voice-command"),
                    stt_status=lambda: {"available": True, "resolved_backend": "mock"},
                )
            )
            result = manager.run_once()

        self.assertTrue(result["handled"])
        self.assertEqual("reduce volume", result["command"])
        self.assertTrue(any(call["action"] == "adjust_volume" for call in self.action_calls))
        self.assertTrue(spoken)
        self.assertEqual("command_handled", manager.status()["last_event"])

    def test_wake_word_without_inline_command_uses_command_listener(self) -> None:
        with patch.object(executor.local_action_executor, "execute_local_action", side_effect=self._fake_action):
            manager = voice_runtime.VoiceRuntimeManager(
                adapters=voice_runtime.VoiceRuntimeAdapters(
                    listen_for_wake=lambda: "Grandpa",
                    listen_for_command=lambda: "lower sound",
                    speak=lambda _text: None,
                    handle_command=lambda command: handle_personal_assistant_message(command, session_id="voice-followup"),
                    stt_status=lambda: {"available": True, "resolved_backend": "mock"},
                )
            )
            result = manager.run_once()

        self.assertTrue(result["handled"])
        self.assertEqual("lower sound", result["command"])

    def test_missing_stt_provider_is_safe(self) -> None:
        manager = voice_runtime.VoiceRuntimeManager(
            adapters=voice_runtime.VoiceRuntimeAdapters(
                listen_for_wake=lambda: "Grandpa",
                listen_for_command=lambda: None,
                speak=lambda _text: None,
                handle_command=lambda _command: {"ok": True, "reply": "unused"},
                stt_status=lambda: {"available": False, "resolved_backend": "unavailable", "last_error": "SpeechRecognition missing"},
            )
        )

        result = manager.run_once()
        status = manager.status()

        self.assertFalse(result["ok"])
        self.assertEqual("speech_to_text", result["missing_adapter"])
        self.assertFalse(status["stt_provider"]["available"])

    def test_status_tool_and_enable_disable_chat_flow(self) -> None:
        state = {"enabled": False}

        def fake_status():
            return {"enabled": state["enabled"], "running": state["enabled"], "wake_word": "Grandpa", "stt_provider": {"resolved_backend": "mock"}}

        def fake_enable():
            state["enabled"] = True
            return {"ok": True, "enabled": True, "running": True, "message": "Voice runtime enabled and listening for the wake word."}

        def fake_disable():
            state["enabled"] = False
            return {"ok": True, "enabled": False, "running": False, "message": "Voice runtime disabled."}

        with patch.object(voice_runtime, "get_voice_runtime_status", side_effect=fake_status), patch.object(
            voice_runtime, "enable_voice_runtime", side_effect=fake_enable
        ), patch.object(voice_runtime, "disable_voice_runtime", side_effect=fake_disable):
            status = handle_personal_assistant_message("is voice mode running?", session_id="voice-tools")
            confirm = handle_personal_assistant_message("enable voice mode", session_id="voice-tools")
            enabled = handle_personal_assistant_message("yes", session_id="voice-tools")
            disabled = handle_personal_assistant_message("disable voice mode", session_id="voice-tools")

        self.assertEqual("voice_runtime_status", status["intent"])
        self.assertTrue(confirm["requires_confirmation"])
        self.assertTrue(enabled["executed"])
        self.assertTrue(disabled["executed"])

    def test_registry_lists_voice_runtime_tools(self) -> None:
        tools = {item["tool_name"] for item in list_available_tools()}

        self.assertIn("voice_runtime_status", tools)
        self.assertIn("enable_voice_runtime", tools)
        self.assertIn("disable_voice_runtime", tools)

    def test_custom_wake_word_from_env(self) -> None:
        os.environ[voice_runtime.WAKE_WORD_ENV] = "Jarvis"

        self.assertTrue(voice_runtime.detect_wake_word("Hey Jarvis check reminders"))
        self.assertEqual("check reminders", voice_runtime.strip_wake_word("Hey Jarvis check reminders"))


if __name__ == "__main__":
    unittest.main()
