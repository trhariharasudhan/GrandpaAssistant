import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

GENERATOR_PATH = ROOT / "scripts" / "dev" / "generate_debug_docs.py"
spec = importlib.util.spec_from_file_location("generate_debug_docs", GENERATOR_PATH)
generate_debug_docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_debug_docs)

from api import web_api
from core import command_router


class DebugDocsGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.patches = [
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
        ]
        for item in self.patches:
            item.start()
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()

    def test_generator_creates_debug_assistant_guide(self) -> None:
        result = generate_debug_docs.generate_debug_docs()

        self.assertTrue(result["ok"])
        self.assertTrue(os.path.exists(result["path"]))
        self.assertTrue(str(result["path"]).endswith(os.path.join("docs", "DEBUG_ASSISTANT_GUIDE.md")))

    def test_guide_contains_key_route_names(self) -> None:
        result = generate_debug_docs.generate_debug_docs()
        guide = Path(result["path"]).read_text(encoding="utf-8")

        self.assertIn("GET /api/debug/report", guide)
        self.assertIn("GET /api/debug/dashboard", guide)
        self.assertIn("GET /api/debug/docs-summary", guide)

    def test_guide_contains_key_command_names(self) -> None:
        result = generate_debug_docs.generate_debug_docs()
        guide = Path(result["path"]).read_text(encoding="utf-8")

        self.assertIn("debug dashboard", guide)
        self.assertIn("debug docs summary", guide)
        self.assertIn("apply fix", guide)

    def test_guide_contains_safety_warnings(self) -> None:
        result = generate_debug_docs.generate_debug_docs()
        guide = Path(result["path"]).read_text(encoding="utf-8").lower()

        self.assertIn("never", guide)
        self.assertIn("not executed automatically", guide)
        self.assertIn("git push --force", guide)
        self.assertIn("no secrets", guide)

    def test_command_router_docs_summary_works(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)):
            command_router.process_command("debug docs summary", {}, input_mode="text")

        self.assertIn("docs/DEBUG_ASSISTANT_GUIDE.md", spoken[-1])
        self.assertIn("debug dashboard", spoken[-1])

    def test_api_protected(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.170", 50000))

        response = remote_client.get("/api/debug/docs-summary")

        self.assertEqual(response.status_code, 403)

    def test_localhost_api_returns_summary(self) -> None:
        response = self.client.get("/api/debug/docs-summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["guide"], "docs/DEBUG_ASSISTANT_GUIDE.md")
        self.assertIn("debug dashboard", payload["key_commands"])


if __name__ == "__main__":
    unittest.main()
