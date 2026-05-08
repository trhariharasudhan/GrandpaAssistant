import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import debug_session
import debug_session_export
from api import web_api
from core import command_router


class DebugSessionExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.session_path = os.path.join(self.temp_dir.name, "debug_sessions.jsonl")
        self.exports_dir = os.path.join(self.temp_dir.name, "exports")
        self.patches = [
            patch.object(debug_session, "DEBUG_SESSIONS_PATH", self.session_path),
            patch.object(debug_session_export, "DEBUG_EXPORTS_DIR", self.exports_dir),
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
        ]
        for item in self.patches:
            item.start()
        debug_session.clear_debug_sessions_for_tests()
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        debug_session.clear_debug_sessions_for_tests()
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def _seed_session(self):
        session = debug_session.start_debug_session(title="Export Test", source="test")
        debug_session.attach_debug_report({"summary": "ModuleNotFoundError password: swordfish", "error_text": "token=abc123"})
        debug_session.attach_fix_plan({"summary": "Check venv", "suggested_commands": [{"command": "git status"}]})
        debug_session.attach_fix_approval({"id": "abc12345", "payload": {"command": "git status"}, "action_type": "command_suggestion"})
        debug_session.attach_audit_event({"event_type": "executed", "message": "git status"})
        return session

    def test_export_current_session_creates_markdown_file(self) -> None:
        session = self._seed_session()

        result = debug_session_export.export_current_debug_session()

        self.assertTrue(result["ok"])
        self.assertEqual(result["session_id"], session["id"])
        self.assertTrue(os.path.exists(result["path"]))
        with open(result["path"], "r", encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("# GrandpaAssistant Debug Session Report", content)
        self.assertIn("No commands were run unless shown in audit events.", content)

    def test_export_latest_session_if_no_active_session(self) -> None:
        session = self._seed_session()
        debug_session.close_debug_session()

        result = debug_session_export.export_current_debug_session()

        self.assertTrue(result["ok"])
        self.assertEqual(result["session_id"], session["id"])

    def test_redaction_works(self) -> None:
        self._seed_session()

        result = debug_session_export.export_current_debug_session()
        with open(result["path"], "r", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("[REDACTED]", content)
        self.assertNotIn("swordfish", content)
        self.assertNotIn("token=abc123", content)

    def test_export_list_works(self) -> None:
        self._seed_session()
        debug_session_export.export_current_debug_session()

        exports = debug_session_export.list_debug_exports()

        self.assertEqual(len(exports), 1)
        self.assertTrue(exports[0]["filename"].endswith(".md"))

    def test_command_router_export_command_works(self) -> None:
        self._seed_session()
        spoken = []

        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)):
            command_router.process_command("export debug session", {}, input_mode="text")

        self.assertIn("Debug session exported", spoken[-1])

    def test_api_protected_from_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.120", 50000))

        response = remote_client.post("/api/debug/session/export")

        self.assertEqual(response.status_code, 403)

    def test_api_export_and_list_localhost(self) -> None:
        self._seed_session()

        export_response = self.client.post("/api/debug/session/export")
        list_response = self.client.get("/api/debug/session/exports")

        self.assertEqual(export_response.status_code, 200)
        self.assertTrue(export_response.json()["ok"])
        self.assertTrue(list_response.json()["items"])

    def test_no_screenshot_or_raw_binary_export(self) -> None:
        debug_session.start_debug_session()
        debug_session.attach_debug_report({"summary": "Screen text", "screenshot": b"\x89PNG".hex(), "raw_binary": "010101"})

        result = debug_session_export.export_current_debug_session()
        with open(result["path"], "r", encoding="utf-8") as handle:
            content = handle.read().lower()

        self.assertIn("does not include raw screenshots", content)
        self.assertNotIn("png", content)
        self.assertNotIn("raw_binary", content)


if __name__ == "__main__":
    unittest.main()
