import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
for path in [APP_DIR, SHARED_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


import llm_client
from core.chatbot.providers.fallback_provider import FallbackProvider
from core.chatbot.providers.ollama_provider import OllamaProvider
from core.chatbot.providers.openai_provider import OpenAIProvider


class LLMProviderAdapterTests(unittest.TestCase):
    def test_terminal_fallback_provider_uses_unified_result_shape(self) -> None:
        result = FallbackProvider().generate("hello")

        self.assertTrue(result.ok)
        self.assertEqual("fallback", result.provider)
        self.assertEqual("rules", result.model)
        self.assertTrue(result.text)

    def test_terminal_openai_adapter_preserves_missing_key_error(self) -> None:
        result = OpenAIProvider(api_key="", model="gpt-test", base_url="https://api.openai.com/v1", timeout_seconds=1).generate("hello")

        self.assertFalse(result.ok)
        self.assertEqual("openai", result.provider)
        self.assertEqual("gpt-test", result.model)
        self.assertIn("OPENAI_API_KEY", result.error)

    def test_terminal_ollama_adapter_uses_unified_provider_payload(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"response": "hello da"}

        with patch("core.llm.providers.ollama_provider.requests.post", return_value=response) as post:
            result = OllamaProvider(model="llama-test", base_url="http://localhost:11434", timeout_seconds=1).generate("hi")

        self.assertTrue(result.ok)
        self.assertEqual("hello da", result.text)
        self.assertEqual("ollama", result.provider)
        self.assertEqual("llama-test", post.call_args.kwargs["json"]["model"])

    def test_llm_client_delegates_ollama_generation_to_unified_manager(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"response": "hello"}

        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "OLLAMA_REQUEST_TIMEOUT_SECONDS": "1.5"}, clear=False), \
            patch.object(llm_client.requests, "post", return_value=response) as post:
            reply = llm_client.generate_chat_reply([], "hi")

        self.assertEqual(reply, "hello")
        self.assertEqual(post.call_args.kwargs["timeout"], 1.5)


if __name__ == "__main__":
    unittest.main()
