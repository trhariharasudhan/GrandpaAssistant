import os
import sys
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

import debug_health_dashboard
from api import web_api
from core import command_router


class DebugHealthDashboardTests(unittest.TestCase):
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

    def _session(self):
        return {
            "id": "sess1",
            "title": "Import issue",
            "status": "active",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:01:00Z",
            "debug_reports": [{"summary": "ModuleNotFoundError"}],
            "fix_plans": [{"summary": "Check venv"}],
            "fix_approvals": [],
            "audit_events": [],
        }

    def _preflight(self, ollama_status="warning"):
        warnings = []
        if ollama_status == "warning":
            warnings.append({
                "key": "ollama_optional",
                "title": "Ollama optional readiness",
                "status": "warning",
                "ok": True,
                "optional": True,
                "detail": "Ollama unavailable.",
            })
        return {
            "check_results": [
                {"key": "dependency_venv", "title": "Dependency", "status": "ok", "ok": True},
                *warnings,
            ],
            "warnings": warnings,
            "recommended_next_steps": ["Start Ollama only if local AI responses are needed."],
            "no_destructive_action": True,
        }

    def _patch_dashboard_inputs(self, **overrides):
        values = {
            "get_current_debug_session": self._session(),
            "get_current_debug_timeline": {"events": [{"timestamp": "2026-01-01T00:01:00Z", "type": "report"}]},
            "build_debug_learning_summary": {"total_sessions_analyzed": 1, "common_error_families": [{"family": "module_not_found", "count": 1}]},
            "run_preflight_checklist": self._preflight(),
            "list_pending_fix_approvals": [{"id": "abc123", "status": "pending"}],
            "list_fix_audit_events": [{"event_type": "created"}],
            "list_debug_exports": [{"filename": "debug.md"}],
            "build_reuse_suggestions": {"confidence": "low", "similar_sessions": [], "no_command_executed": True},
        }
        values.update(overrides)
        return [
            patch.object(debug_health_dashboard, name, return_value=value)
            for name, value in values.items()
        ]

    def test_dashboard_combines_all_major_sections(self) -> None:
        patches = self._patch_dashboard_inputs()
        for item in patches:
            item.start()
        try:
            payload = debug_health_dashboard.build_debug_health_dashboard()
        finally:
            for item in reversed(patches):
                item.stop()

        self.assertTrue(payload["overall_ok"])
        self.assertEqual(payload["active_session"]["id"], "sess1")
        self.assertEqual(payload["pending_approvals_count"], 1)
        self.assertEqual(payload["recent_audit_count"], 1)
        self.assertEqual(payload["timeline_count"], 1)
        self.assertIn("learning_summary", payload)
        self.assertIn("preflight_status", payload)
        self.assertEqual(payload["export_count"], 1)

    def test_pending_approvals_count_works(self) -> None:
        patches = self._patch_dashboard_inputs(list_pending_fix_approvals=[{"id": "a"}, {"id": "b"}])
        for item in patches:
            item.start()
        try:
            payload = debug_health_dashboard.build_debug_health_dashboard()
        finally:
            for item in reversed(patches):
                item.stop()

        self.assertEqual(payload["pending_approvals_count"], 2)

    def test_warnings_included(self) -> None:
        patches = self._patch_dashboard_inputs()
        for item in patches:
            item.start()
        try:
            payload = debug_health_dashboard.build_debug_health_dashboard()
        finally:
            for item in reversed(patches):
                item.stop()

        self.assertTrue(payload["warnings"])
        self.assertEqual(payload["preflight_status"]["warning_count"], 1)

    def test_optional_ollama_warning_does_not_fail_overall_ok(self) -> None:
        patches = self._patch_dashboard_inputs(run_preflight_checklist=self._preflight("warning"))
        for item in patches:
            item.start()
        try:
            payload = debug_health_dashboard.build_debug_health_dashboard()
        finally:
            for item in reversed(patches):
                item.stop()

        self.assertTrue(payload["overall_ok"])

    def test_command_router_dashboard_command_works(self) -> None:
        spoken = []
        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)), \
            patch.object(command_router, "build_debug_health_dashboard", return_value={
                "overall_ok": True,
                "pending_approvals_count": 0,
                "recent_audit_count": 0,
                "timeline_count": 0,
                "export_count": 0,
                "warnings": [],
                "recommended_next_steps": ["Run the debug checklist."],
                "no_destructive_action": True,
            }):
            command_router.process_command("debug dashboard", {}, input_mode="text")

        self.assertIn("Debug dashboard", spoken[-1])

    def test_api_protected(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.170", 50000))

        response = remote_client.get("/api/debug/dashboard")

        self.assertEqual(response.status_code, 403)

    def test_no_destructive_action_true(self) -> None:
        patches = self._patch_dashboard_inputs()
        for item in patches:
            item.start()
        try:
            payload = debug_health_dashboard.build_debug_health_dashboard()
        finally:
            for item in reversed(patches):
                item.stop()

        self.assertTrue(payload["no_destructive_action"])

    def test_redaction_works(self) -> None:
        patches = self._patch_dashboard_inputs(
            get_current_debug_session={
                **self._session(),
                "title": "password=supersecret token=abc123",
            },
            build_debug_learning_summary={"prevention_suggestions": ["Use token=abc123 carefully."]},
        )
        for item in patches:
            item.start()
        try:
            payload = debug_health_dashboard.build_debug_health_dashboard()
        finally:
            for item in reversed(patches):
                item.stop()

        rendered = str(payload)
        self.assertNotIn("supersecret", rendered)
        self.assertNotIn("abc123", rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_localhost_api_returns_dashboard(self) -> None:
        with patch.object(web_api, "build_debug_health_dashboard", return_value={"overall_ok": True, "checks": [], "no_destructive_action": True}):
            response = self.client.get("/api/debug/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["overall_ok"])


if __name__ == "__main__":
    unittest.main()
