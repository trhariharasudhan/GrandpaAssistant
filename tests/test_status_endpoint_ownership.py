import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in [ROOT, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


import llm_client
import offline_multi_model
from api import chat_api, web_api


def _route_keys(app) -> set[tuple[str, str]]:
    keys = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or []:
            if method in {"HEAD", "OPTIONS"}:
                continue
            keys.add((method, route.path))
    return keys


class StatusEndpointOwnershipTests(unittest.TestCase):
    def test_web_api_status_routes_import_and_expose_expected_keys(self) -> None:
        keys = _route_keys(web_api.app)
        expected = {
            ("GET", "/api/health"),
            ("GET", "/api/doctor"),
            ("GET", "/api/backend/stability"),
            ("GET", "/api/memory/status"),
            ("GET", "/api/voice/status"),
            ("GET", "/chat/settings"),
            ("POST", "/chat/settings"),
        }
        self.assertTrue(expected.issubset(keys))

        with patch.object(web_api, "_enforce_app_auth", lambda request: None), \
            patch("core.llm.providers.ollama_provider.requests.get", side_effect=RuntimeError("offline")):
            response = TestClient(web_api.app).get("/chat/settings")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn("ok", payload)
        self.assertIn("settings", payload)
        self.assertIn("llm_status", payload["settings"])
        self.assertIn("provider", payload["settings"]["llm_status"])

    def test_chat_api_status_routes_import_and_expose_expected_keys(self) -> None:
        keys = _route_keys(chat_api.app)
        expected = {
            ("GET", "/health"),
            ("GET", "/doctor"),
            ("GET", "/models"),
            ("GET", "/status"),
            ("GET", "/settings/validation"),
            ("GET", "/memory/status"),
            ("GET", "/security/status"),
        }
        self.assertTrue(expected.issubset(keys))

        with patch.object(chat_api, "_ensure_runtime_ready", lambda: None), \
            patch.object(chat_api, "collect_startup_diagnostics", lambda *args, **kwargs: {"ok": True}), \
            patch.object(chat_api.DEVICE_MANAGER, "get_status", return_value={"ok": True}), \
            patch.object(chat_api.DEVICE_MANAGER, "get_iot_status", return_value={"ok": True}), \
            patch.object(chat_api.ASSISTANT_RUNTIME, "status_payload", return_value={"running": True}), \
            patch.object(chat_api, "semantic_memory_status", return_value={"ok": True}), \
            patch("core.llm.providers.ollama_provider.requests.get", side_effect=RuntimeError("offline")):
            response = TestClient(chat_api.app).get("/health")

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertIn("ok", payload)
        self.assertIn("service", payload)
        self.assertIn("offline_assistant", payload)
        self.assertEqual("ollama", payload["offline_assistant"]["provider"])

    def test_provider_status_wrappers_read_from_core_llm_status(self) -> None:
        active_status = {
            "provider": "ollama",
            "model": "llama-test",
            "base_url": "http://localhost:11434",
            "ready": False,
            "status": "unavailable",
            "health": {"ok": False, "provider": "ollama"},
        }
        with patch.object(llm_client, "get_active_provider_summary", return_value=active_status) as active, \
            patch.object(llm_client, "get_model_summary", return_value={"models": {}}), \
            patch.object(llm_client, "get_health_report", return_value={"providers": {}}), \
            patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "OPENAI_API_KEY": ""}, clear=False):
            llm_status = llm_client.get_llm_status()

        self.assertTrue(active.called)
        self.assertEqual("ollama", llm_status["provider"])
        self.assertEqual("llama-test", llm_status["model"])

        provider_status = {
            "ok": False,
            "provider": "ollama",
            "model": "llama-test",
            "base_url": "http://localhost:11434",
            "installed_models": [],
            "status": "unavailable",
            "error": "offline",
            "health": {"ok": False, "provider": "ollama"},
        }
        with patch.object(offline_multi_model, "get_provider_status", return_value=provider_status) as provider:
            ollama_status = offline_multi_model.get_ollama_status()

        self.assertTrue(provider.called)
        self.assertFalse(ollama_status["ok"])
        self.assertEqual("ollama", ollama_status["provider"])

    def test_no_duplicate_active_desktop_status_routes(self) -> None:
        seen: set[tuple[str, str]] = set()
        duplicates: list[tuple[str, str]] = []
        for route in web_api.app.routes:
            if not isinstance(route, APIRoute):
                continue
            for method in route.methods or []:
                if method in {"HEAD", "OPTIONS"}:
                    continue
                key = (method, route.path)
                if key in seen:
                    duplicates.append(key)
                seen.add(key)

        self.assertEqual([], duplicates)


if __name__ == "__main__":
    unittest.main()
