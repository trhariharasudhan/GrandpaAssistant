import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


import llm_client
import offline_multi_model
from core.llm.status import (
    get_active_provider_summary,
    get_all_provider_statuses,
    get_health_report,
    get_model_summary,
    get_provider_status,
)


class LLMStatusSurfaceTests(unittest.TestCase):
    def test_fallback_status_works_without_network(self) -> None:
        status = get_provider_status("fallback", force=True)

        self.assertTrue(status["ok"])
        self.assertEqual("fallback", status["provider"])
        self.assertEqual("rules", status["model"])
        self.assertEqual("ok", status["status"])

    def test_missing_cloud_keys_do_not_crash(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}, clear=False):
            openai = get_provider_status("openai", force=True)
            gemini = get_provider_status("gemini", force=True)

        self.assertFalse(openai["ok"])
        self.assertFalse(gemini["ok"])
        self.assertEqual("openai", openai["provider"])
        self.assertEqual("gemini", gemini["provider"])

    def test_ollama_unavailable_returns_status_not_exception(self) -> None:
        with patch("core.llm.providers.ollama_provider.requests.get", side_effect=RuntimeError("offline")):
            status = get_provider_status("ollama", force=True)

        self.assertFalse(status["ok"])
        self.assertEqual("ollama", status["provider"])
        self.assertEqual("unavailable", status["status"])
        self.assertIn("offline", status["error"])

    def test_unified_summary_functions_include_expected_sections(self) -> None:
        with patch("core.llm.providers.ollama_provider.requests.get", side_effect=RuntimeError("offline")):
            active = get_active_provider_summary("fallback", force=True)
            models = get_model_summary("fallback", force=True)
            providers = get_all_provider_statuses(force=True)
            report = get_health_report("fallback", force=True)

        self.assertEqual("fallback", active["provider"])
        self.assertIn("fallback", providers)
        self.assertIn("models", models)
        self.assertIn("providers", report)

    def test_old_llm_status_wrapper_preserves_expected_keys(self) -> None:
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "OPENAI_API_KEY": ""}, clear=False), \
            patch("core.llm.providers.ollama_provider.requests.get", side_effect=RuntimeError("offline")):
            status = llm_client.get_llm_status()

        for key in ["provider", "model", "base_url", "api_key_configured", "ready", "health"]:
            self.assertIn(key, status)
        self.assertEqual("ollama", status["provider"])
        self.assertIsInstance(status["ready"], bool)

    def test_old_ollama_status_wrapper_preserves_expected_keys(self) -> None:
        with patch("core.llm.providers.ollama_provider.requests.get", side_effect=RuntimeError("offline")):
            status = offline_multi_model.get_ollama_status()

        for key in ["ok", "provider", "model", "base_url", "installed_models"]:
            self.assertIn(key, status)
        self.assertFalse(status["ok"])
        self.assertEqual("ollama", status["provider"])


if __name__ == "__main__":
    unittest.main()
