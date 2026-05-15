import os
import sys
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


from core.llm.base import LLMRequest
from core.llm.provider_manager import LLMProviderManager
from core.llm.providers.fallback_provider import FallbackLLMProvider


class LLMProviderRegistryTests(unittest.TestCase):
    def test_registry_exposes_default_providers(self) -> None:
        manager = LLMProviderManager.from_environment()
        self.assertEqual(["fallback", "gemini", "ollama", "openai"], manager.registry.names())

    def test_auto_provider_prefers_openai_when_key_exists(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "key", "LLM_PROVIDER": "auto"}, clear=False):
            manager = LLMProviderManager.from_environment()
            self.assertEqual("openai", manager.resolve_provider_name())

    def test_auto_provider_falls_back_to_ollama_without_cloud_keys(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "LLM_PROVIDER": "auto"}, clear=False):
            manager = LLMProviderManager.from_environment()
            self.assertEqual("ollama", manager.resolve_provider_name())

    def test_fallback_provider_supports_required_interfaces(self) -> None:
        provider = FallbackLLMProvider()
        request = LLMRequest(prompt="hello")

        result = provider.generate(request)
        stream = list(provider.stream_generate(request))
        health = provider.health_check()
        info = provider.model_info()

        self.assertTrue(result.ok)
        self.assertEqual([result.text], stream)
        self.assertTrue(health["ok"])
        self.assertEqual("fallback", info["provider"])


if __name__ == "__main__":
    unittest.main()
