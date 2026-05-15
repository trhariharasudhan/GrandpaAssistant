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
for path in [ROOT, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from api import chat_api, web_api
from backend.app.config.grandpa_config import GrandpaConfig
from backend.app.core.chatbot.engine import ChatbotEngine
from backend.app.cli import chat as terminal_chat


class ProviderStatusRouteBehaviorTests(unittest.TestCase):
    def test_web_api_chat_settings_status_shape_is_preserved(self) -> None:
        with patch.object(web_api, "_enforce_app_auth", lambda request: None), \
            patch("core.llm.providers.ollama_provider.requests.get", side_effect=RuntimeError("offline")):
            response = TestClient(web_api.app).get("/chat/settings")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        llm_status = payload["settings"]["llm_status"]
        for key in ["provider", "model", "base_url", "ready", "health"]:
            self.assertIn(key, llm_status)

    def test_chat_api_health_uses_ollama_status_wrapper_without_crashing(self) -> None:
        with patch.object(chat_api, "_ensure_runtime_ready", lambda: None), \
            patch.object(chat_api, "collect_startup_diagnostics", lambda *args, **kwargs: {"ok": True}), \
            patch.object(chat_api.DEVICE_MANAGER, "get_status", return_value={"ok": True}), \
            patch.object(chat_api.DEVICE_MANAGER, "get_iot_status", return_value={"ok": True}), \
            patch.object(chat_api.ASSISTANT_RUNTIME, "status_payload", return_value={"running": True}), \
            patch.object(chat_api, "semantic_memory_status", return_value={"ok": True}), \
            patch("core.llm.providers.ollama_provider.requests.get", side_effect=RuntimeError("offline")):
            response = TestClient(chat_api.app).get("/health")

        self.assertEqual(response.status_code, 200)
        offline = response.json()["offline_assistant"]
        self.assertEqual("ollama", offline["provider"])
        self.assertFalse(offline["ok"])
        self.assertIn("installed_models", offline)

    def test_terminal_provider_model_config_commands_still_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = GrandpaConfig(
                provider="fallback",
                model="rules",
                db_path=str(Path(temp_dir) / "chat.db"),
                log_path=str(Path(temp_dir) / "chat.log"),
            )
            engine = ChatbotEngine(config=config, session_id="test-session")
            try:
                with patch("builtins.print") as printed:
                    self.assertEqual((True, False), terminal_chat._handle_slash_command(engine, "/provider"))
                    self.assertEqual((True, False), terminal_chat._handle_slash_command(engine, "/model"))
                    self.assertEqual((True, False), terminal_chat._handle_slash_command(engine, "/config"))
            finally:
                engine.close()

        output = "\n".join(str(call.args[0]) for call in printed.call_args_list if call.args)
        self.assertIn("Current provider is fallback", output)
        self.assertIn("Current model is rules", output)
        self.assertIn("provider_status", output)


if __name__ == "__main__":
    unittest.main()
