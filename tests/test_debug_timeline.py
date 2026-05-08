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
import debug_timeline
from api import web_api
from core import command_router


class DebugTimelineTests(unittest.TestCase):
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

    def _session(self):
        return {
            "id": "s1",
            "status": "active",
            "created_at": "2026-05-08T00:00:00Z",
            "debug_reports": [{"timestamp": "2026-05-08T00:01:00Z", "summary": "Error password: swordfish", "no_command_executed": True}],
            "fix_plans": [{"timestamp": "2026-05-08T00:03:00Z", "summary": "Plan token=abc123", "no_command_executed": True, "no_file_edited": True}],
            "fix_approvals": [{"created_at": "2026-05-08T00:02:00Z", "id": "ap1", "payload": {"command": "git status"}}],
            "audit_events": [{"timestamp": "2026-05-08T00:04:00Z", "event_type": "executed", "approval": {"command": "git status"}}],
        }

    def test_timeline_combines_report_plan_approval_audit_events(self) -> None:
        timeline = debug_timeline.build_debug_timeline(session=self._session())

        self.assertTrue(timeline["ok"])
        self.assertEqual([item["type"] for item in timeline["items"]], ["debug_report", "fix_approval", "fix_plan", "audit_event"])

    def test_events_sorted_by_timestamp(self) -> None:
        timeline = debug_timeline.build_debug_timeline(session=self._session())
        timestamps = [item["timestamp"] for item in timeline["items"]]

        self.assertEqual(timestamps, sorted(timestamps))

    def test_formatting_works(self) -> None:
        text = debug_timeline.format_debug_timeline(debug_timeline.build_debug_timeline(session=self._session()))

        self.assertIn("Debug timeline", text)
        self.assertIn("Fix approval", text)

    def test_redaction_and_truncation_works(self) -> None:
        session = self._session()
        session["debug_reports"][0]["summary"] = "password: swordfish " + ("x" * 1200)

        timeline = debug_timeline.build_debug_timeline(session=session)
        summary = timeline["items"][0]["summary"]

        self.assertIn("[REDACTED]", summary)
        self.assertNotIn("swordfish", summary)
        self.assertLessEqual(len(summary), debug_timeline.MAX_TEXT_LENGTH + 20)

    def test_command_router_timeline_command_works(self) -> None:
        debug_session.start_debug_session(title="Timeline")
        debug_session.attach_debug_report({"timestamp": "2026-05-08T00:01:00Z", "summary": "Error"})
        spoken = []

        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)):
            command_router.process_command("debug timeline", {}, input_mode="text")

        self.assertIn("Debug timeline", spoken[-1])

    def test_api_protected_from_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.130", 50000))

        response = remote_client.get("/api/debug/timeline")

        self.assertEqual(response.status_code, 403)

    def test_api_allows_localhost(self) -> None:
        debug_session.start_debug_session(title="Timeline")
        debug_session.attach_debug_report({"timestamp": "2026-05-08T00:01:00Z", "summary": "Error"})

        response = self.client.get("/api/debug/timeline")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["items"])

    def test_export_includes_timeline_section(self) -> None:
        debug_session.start_debug_session(title="Timeline")
        debug_session.attach_debug_report({"timestamp": "2026-05-08T00:01:00Z", "summary": "Error"})

        result = debug_session_export.export_current_debug_session()
        with open(result["path"], "r", encoding="utf-8") as handle:
            content = handle.read()

        self.assertIn("## Timeline", content)
        self.assertIn("Debug report captured", content)


if __name__ == "__main__":
    unittest.main()
