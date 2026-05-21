import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in (ROOT, APP_DIR, SHARED_DIR, FEATURES_DIR):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from core.jarvis_voice.conversation_state import ConversationStateManager
from core.jarvis_voice.manager import VoiceManager
from core.jarvis_voice.settings import JarvisVoiceSettings, load_voice_settings, save_voice_settings
from core.jarvis_voice.speech_pipeline import SpeechPipeline, SpeechPipelineAdapters
from core.jarvis_voice.streaming_router import StreamingVoiceRouter
from core.jarvis_voice.wake_word import WakeWordEngine


class JarvisVoiceSystemTests(unittest.TestCase):
    def test_wake_word_extracts_inline_command(self) -> None:
        engine = WakeWordEngine(["hey grandpa"])

        result = engine.extract_command("Hey Grandpa reduce volume")

        self.assertTrue(result["wake_detected"])
        self.assertEqual("hey grandpa", result["wake_word"])
        self.assertIn("reduce volume", result["command"].lower())

    def test_settings_persist_locally(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "jarvis_settings.json"
            with patch.dict(os.environ, {"GRANDPA_JARVIS_VOICE_SETTINGS_PATH": str(path)}, clear=False):
                save_voice_settings({"enabled": True, "wake_words": ["Hey Grandpa"], "voice_profile": "warm"})
                loaded = load_voice_settings()

        self.assertTrue(loaded.enabled)
        self.assertEqual(["hey grandpa"], loaded.wake_words)
        self.assertEqual("warm", loaded.voice_profile)

    def test_speech_pipeline_supports_vad_noise_suppression_and_fake_io(self) -> None:
        spoken: list[str] = []
        pipeline = SpeechPipeline(
            JarvisVoiceSettings(),
            SpeechPipelineAdapters(
                listen=lambda **_kwargs: "Hey Grandpa remind me",
                speak=lambda text: spoken.append(text),
                stop_speaking=lambda: spoken.append("STOP"),
            ),
        )

        self.assertEqual("Hey Grandpa remind me", pipeline.listen_for_wake())
        self.assertTrue(pipeline.voice_activity_detected((1000).to_bytes(2, "little", signed=True) * 20))
        self.assertEqual(b"abc", pipeline.suppress_noise(b"abc"))
        self.assertTrue(pipeline.speak("Hello")["ok"])
        self.assertEqual(["Hello"], spoken)
        self.assertTrue(pipeline.stop_speaking()["ok"])

    def test_streaming_router_uses_chat_handler_and_state_without_raw_history(self) -> None:
        state = ConversationStateManager()
        router = StreamingVoiceRouter(
            JarvisVoiceSettings(streaming_enabled=True),
            state,
            chat_handler=lambda message, **_kwargs: {
                "ok": True,
                "reply": "Reduced the system volume.",
                "intent": "adjust_volume",
                "route": "personal-assistant",
                "provider": "personal-assistant",
                "messages": [{"role": "user", "content": message}],
            },
        )

        events = list(router.stream_text("lower sound", session_id="voice-test"))
        final = events[-1]

        self.assertEqual("done", final["type"])
        self.assertEqual("adjust_volume", final["intent"])
        self.assertEqual(1, state.snapshot("voice-test")["turn_count"])
        route = router.route_text("lower sound", session_id="voice-test")
        self.assertNotIn("raw", route)
        self.assertNotIn("messages", json.dumps(route))

    def test_voice_manager_run_once_handles_wake_word_and_interruptible_reply(self) -> None:
        spoken: list[str] = []
        pipeline = SpeechPipeline(
            JarvisVoiceSettings(enabled=True, wake_words=["hey grandpa"]),
            SpeechPipelineAdapters(
                listen=lambda **kwargs: "Hey Grandpa reduce volume" if kwargs.get("for_wake_word") else "",
                speak=lambda text: spoken.append(text),
                stop_speaking=lambda: spoken.append("STOP"),
            ),
        )
        state = ConversationStateManager()
        router = StreamingVoiceRouter(
            pipeline.settings,
            state,
            chat_handler=lambda *_args, **_kwargs: {"ok": True, "reply": "Reduced the system volume.", "intent": "adjust_volume"},
        )
        manager = VoiceManager(settings=pipeline.settings, pipeline=pipeline, router=router, state_manager=state)

        result = manager.run_once(session_id="voice-test")

        self.assertTrue(result["handled"])
        self.assertEqual("command_processed", result["event"])
        self.assertEqual(["STOP", "Reduced the system volume."], spoken)
        self.assertEqual(1, manager.status()["command_count"])


class JarvisVoiceApiTests(unittest.TestCase):
    def setUp(self) -> None:
        from api import jarvis_voice_api

        self.jarvis_voice_api = jarvis_voice_api

    def tearDown(self) -> None:
        pass

    def test_jarvis_status_endpoint_reports_manager_status(self) -> None:
        from fastapi import FastAPI

        class FakeManager:
            def status(self):
                return {"ok": True, "running": False, "wake_words": ["hey grandpa"]}

        app = FastAPI()
        app.include_router(self.jarvis_voice_api.router)
        with patch.object(self.jarvis_voice_api, "_jarvis_manager", return_value=FakeManager()):
            client = TestClient(app)
            response = client.get("/api/jarvis/status")

        self.assertEqual(200, response.status_code)
        self.assertEqual(["hey grandpa"], response.json()["jarvis"]["wake_words"])

    def test_jarvis_websocket_streams_transcript_events(self) -> None:
        from fastapi import FastAPI

        class FakeManager:
            def status(self):
                return {"ok": True, "running": False}

            def stream_transcript(self, transcript, *, session_id, source):
                return [
                    {"type": "start", "session_id": session_id, "source": source},
                    {"type": "token", "text": "Hello "},
                    {"type": "done", "ok": True, "reply": f"Heard {transcript}", "intent": "chat"},
                ]

            def interrupt(self, *, session_id):
                return {"ok": True, "event": "interrupted"}

            def set_muted(self, muted, *, session_id):
                return {"ok": True, "muted": muted}

            def push_to_talk(self, transcript=None, *, session_id):
                return {"ok": True, "reply": transcript or "", "event": "command_processed"}

        app = FastAPI()
        app.include_router(self.jarvis_voice_api.router)
        with patch.object(self.jarvis_voice_api, "_jarvis_manager", return_value=FakeManager()):
            client = TestClient(app)
            with client.websocket_connect("/api/jarvis/ws") as websocket:
                self.assertEqual("status", websocket.receive_json()["type"])
                websocket.send_json({"type": "transcript", "transcript": "hello", "session_id": "ws-test"})
                self.assertEqual("start", websocket.receive_json()["type"])
                self.assertEqual("token", websocket.receive_json()["type"])
                done = websocket.receive_json()

        self.assertEqual("done", done["type"])
        self.assertIn("hello", done["reply"])


if __name__ == "__main__":
    unittest.main()
