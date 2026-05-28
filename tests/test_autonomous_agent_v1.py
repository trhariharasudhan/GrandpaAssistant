import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in [ROOT, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from api import autonomous_agent_api
from autonomous_agent.manager import AutonomousAgentManager
from autonomous_agent.state import ContextManager
from core.autonomous_agent import AgentExecutorBridge, AgentStateStore, create_plan


class AutonomousAgentV1Tests(unittest.TestCase):
    def _store(self, temp_dir: str) -> AgentStateStore:
        return AgentStateStore(os.path.join(temp_dir, "plans.json"))

    def test_plan_only_does_not_execute(self) -> None:
        app = FastAPI()
        app.include_router(autonomous_agent_api.router)
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AutonomousAgentManager(context_manager=ContextManager(os.path.join(temp_dir, "legacy.json")))
            store = self._store(temp_dir)
            bridge = AgentExecutorBridge(state_store=store)
            with patch.object(autonomous_agent_api, "_manager", return_value=manager), \
                patch.object(autonomous_agent_api, "_agent_v1", return_value=(create_plan, store, bridge)):
                with patch("services.local_action_executor.execute_local_action") as action, patch("core.personal_assistant.reminder_engine.create_reminder") as reminder:
                    response = TestClient(app).post("/api/agent/plan", json={"goal": "open notepad"})

        self.assertEqual(200, response.status_code)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["executed"])
        self.assertTrue(payload["dry_run"])
        self.assertIn("task", payload)
        self.assertIn("graph", payload)
        self.assertIn("plan_id", payload)
        action.assert_not_called()
        reminder.assert_not_called()

    def test_safe_app_open_plan_is_persisted_and_needs_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(temp_dir)
            plan = create_plan("open notepad")
            store.save_plan(plan)
            loaded = store.get_plan(plan.plan_id)

        self.assertIsNotNone(loaded)
        payload = loaded.to_dict()
        self.assertEqual("open_application", payload["proposed_steps"][0]["action"])
        self.assertEqual("needs_confirmation", payload["proposed_steps"][0]["safety"])
        self.assertTrue(payload["confirmation_needed"])

    def test_dangerous_delete_is_blocked(self) -> None:
        payload = create_plan("delete all project files").to_dict()

        self.assertEqual("blocked", payload["safety_classification"]["overall"])
        self.assertTrue(payload["blocked_reasons"])
        self.assertIn("blocked", payload["proposed_steps"][0]["safety"])

    def test_payment_or_order_is_blocked(self) -> None:
        payload = create_plan("order pizza and pay now").to_dict()

        self.assertEqual("blocked", payload["safety_classification"]["overall"])
        self.assertTrue(any("blocked" in reason.lower() for reason in payload["blocked_reasons"]))

    def test_execute_skips_confirmation_steps_when_unconfirmed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(temp_dir)
            plan = create_plan("open notepad")
            store.save_plan(plan)
            bridge = AgentExecutorBridge(state_store=store)
            with patch("services.local_action_executor.execute_local_action") as action:
                result = bridge.execute(plan_id=plan.plan_id, confirmed=False)

        self.assertTrue(result["ok"])
        self.assertEqual([], result["executed_steps"])
        self.assertEqual("confirmation_required", result["skipped_steps"][0]["skip_reason"])
        action.assert_not_called()

    def test_confirmed_execution_uses_local_action_executor(self) -> None:
        cases = [
            ("open calculator", {"action": "open_app", "params": {"app": "calculator"}}),
            ("open https://example.com", {"action": "open_url", "params": {"url": "https://example.com"}}),
            ("take a screenshot", {"action": "take_screenshot", "params": {}}),
        ]
        for goal, expected_payload in cases:
            with self.subTest(goal=goal), tempfile.TemporaryDirectory() as temp_dir:
                store = self._store(temp_dir)
                plan = create_plan(goal)
                store.save_plan(plan)
                bridge = AgentExecutorBridge(state_store=store)
                expected = {"ok": True, "action": expected_payload["action"], "message": "ok", "data": expected_payload["params"]}
                with patch("services.local_action_executor.execute_local_action", return_value=expected) as action:
                    result = bridge.execute(plan_id=plan.plan_id, confirmed=True)

                self.assertTrue(result["ok"])
                self.assertEqual(1, len(result["executed_steps"]))
                action.assert_called_once_with(expected_payload)

    def test_execute_endpoint_runs_persisted_plan_when_confirmed(self) -> None:
        app = FastAPI()
        app.include_router(autonomous_agent_api.router)
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(temp_dir)
            plan = create_plan("open calculator")
            store.save_plan(plan)
            bridge = AgentExecutorBridge(state_store=store)
            with patch.object(autonomous_agent_api, "_agent_v1", return_value=(create_plan, store, bridge)), \
                patch("services.local_action_executor.execute_local_action", return_value={"ok": True, "action": "open_app", "message": "ok", "data": {"app": "calculator"}}):
                response = TestClient(app).post("/api/agent/execute", json={"plan_id": plan.plan_id, "confirmed": True})

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.json()["executed_steps"]))

    def test_create_reminder_requires_confirmation_and_uses_service(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(temp_dir)
            plan = create_plan("remind me to drink water tomorrow morning")
            store.save_plan(plan)
            bridge = AgentExecutorBridge(state_store=store)
            skipped = bridge.execute(plan_id=plan.plan_id, confirmed=False)
            with patch("core.personal_assistant.reminder_engine.create_reminder", return_value={"ok": True, "message": "Reminder saved.", "reminder": {"id": "r1"}}) as reminder:
                executed = bridge.execute(plan_id=plan.plan_id, confirmed=True)

        self.assertEqual("confirmation_required", skipped["skipped_steps"][0]["skip_reason"])
        self.assertEqual(1, len(executed["executed_steps"]))
        reminder.assert_called_once()

    def test_verifier_warning_does_not_crash_execute(self) -> None:
        class BrokenVerifier:
            def verify(self, _step, _result):
                raise RuntimeError("verification adapter failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(temp_dir)
            plan = create_plan("open notepad")
            store.save_plan(plan)
            bridge = AgentExecutorBridge(state_store=store, verifier=BrokenVerifier())
            with patch("services.local_action_executor.execute_local_action", return_value={"ok": True, "action": "open_app", "message": "ok", "data": {}}):
                result = bridge.execute(plan_id=plan.plan_id, confirmed=True)

        self.assertTrue(result["ok"])
        self.assertEqual("warning", result["verification_result"]["status"])

    def test_blocked_steps_never_execute_even_when_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(temp_dir)
            plan = create_plan("format the drive")
            store.save_plan(plan)
            bridge = AgentExecutorBridge(state_store=store)
            with patch("services.local_action_executor.execute_local_action") as action:
                result = bridge.execute(plan_id=plan.plan_id, confirmed=True)

        self.assertEqual([], result["executed_steps"])
        self.assertTrue(result["blocked_steps"])
        action.assert_not_called()


if __name__ == "__main__":
    unittest.main()
