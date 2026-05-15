import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from brain import ai_engine
from core.llm.base import LLMResponse
from core.llm.provider_manager import LLMProviderManager
import offline_multi_model


class AIEngineProviderManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        ai_engine.clear_memory()

    def tearDown(self) -> None:
        ai_engine.clear_memory()

    def test_ai_engine_can_generate_using_provider_manager(self) -> None:
        manager = Mock()
        manager.generate.return_value = LLMResponse(True, "Provider reply.", "fallback", "rules")

        with patch.object(ai_engine, "get_default_provider_manager", return_value=manager), \
            patch.object(ai_engine, "answer_if_confident", return_value=""), \
            patch.object(ai_engine, "get_setting", side_effect=lambda _name, default=None: default), \
            patch.object(ai_engine, "_build_prompt", return_value="prompt"):
            reply = ai_engine.ask_ollama("tell me something useful")

        self.assertEqual(reply, "Provider reply.")
        self.assertEqual(manager.generate.call_args.kwargs["provider"], "ollama")

    def test_ai_engine_provider_failure_returns_local_fallback(self) -> None:
        manager = Mock()
        manager.generate.return_value = LLMResponse(False, "", "ollama", "phi3", "offline")

        with patch.object(ai_engine, "get_default_provider_manager", return_value=manager), \
            patch.object(ai_engine, "answer_if_confident", return_value=""), \
            patch.object(ai_engine, "get_setting", side_effect=lambda _name, default=None: default), \
            patch.object(ai_engine, "_build_prompt", return_value="prompt"), \
            patch.object(ai_engine, "_provider_fallback_reply", return_value=""):
            reply = ai_engine.ask_ollama("hello there")

        self.assertTrue(reply)
        self.assertNotIn("Traceback", reply)

    def test_provider_health_status_uses_unified_ollama_provider(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"models": [{"name": "llama3:8b"}]}

        with patch("core.llm.providers.ollama_provider.requests.get", return_value=response):
            status = offline_multi_model.get_ollama_status()

        self.assertTrue(status["ok"])
        self.assertEqual("ollama", status["provider"])
        self.assertEqual(["llama3:8b"], status["installed_models"])

    def test_provider_manager_health_cache_reports_unavailable_without_network_crash(self) -> None:
        manager = LLMProviderManager.from_environment()
        with patch("core.llm.providers.ollama_provider.requests.get", side_effect=RuntimeError("offline")):
            health = manager.health_check("ollama",)

        self.assertFalse(health["ok"])
        self.assertEqual("ollama", health["provider"])


if __name__ == "__main__":
    unittest.main()
