from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .action_schema import AgentPlan, AgentStep, compact_text, plan_from_dict
from .state import AgentStateStore
from .verifier import AgentVerifier


LOCAL_ACTION_MAP = {
    "open_application": "open_app",
    "open_url": "open_url",
    "take_screenshot": "take_screenshot",
}


class AgentExecutorBridge:
    def __init__(self, *, state_store: AgentStateStore | None = None, verifier: AgentVerifier | None = None) -> None:
        self.state_store = state_store or AgentStateStore()
        self.verifier = verifier or AgentVerifier()

    def execute(self, *, plan_id: str = "", plan_payload: dict[str, Any] | None = None, confirmed: bool = False, confirmation_token: str = "") -> dict[str, Any]:
        plan = plan_from_dict(plan_payload) if plan_payload else self.state_store.get_plan(plan_id)
        if plan is None:
            return {"ok": False, "message": "Plan not found.", "executed_steps": [], "skipped_steps": [], "blocked_steps": [], "verification_result": {"status": "warning", "message": "No plan was available to execute."}}

        executed_steps = []
        skipped_steps = []
        blocked_steps = []
        verification_items = []
        for step in plan.steps:
            if step.safety == "blocked":
                blocked_steps.append({**step.to_dict(), "status": "blocked"})
                continue
            if step.requires_confirmation and not (confirmed or confirmation_token):
                skipped_steps.append({**step.to_dict(), "status": "skipped", "skip_reason": "confirmation_required"})
                continue
            result = self._execute_step(step)
            try:
                verification = self.verifier.verify(step, result)
            except Exception as error:
                verification = {"status": "warning", "message": f"Verification warning: {compact_text(error)}"}
            item = {**step.to_dict(), "status": "executed" if result.get("ok") else "warning", "result": result, "verification": verification}
            executed_steps.append(item)
            verification_items.append(verification)

        summary_status = "warning" if any(item.get("status") == "warning" for item in verification_items) else "ok"
        if blocked_steps and not executed_steps:
            summary_status = "blocked"
        payload = {
            "ok": True,
            "agent_version": "autonomous_desktop_agent_v1",
            "plan_id": plan.plan_id,
            "executed_steps": executed_steps,
            "skipped_steps": skipped_steps,
            "blocked_steps": blocked_steps,
            "verification_result": {"status": summary_status, "items": verification_items},
            "executed": bool(executed_steps),
        }
        stored = plan.to_dict()
        stored["executed"] = bool(executed_steps)
        stored["last_execution"] = payload
        self.state_store.save_plan_payload(stored)
        return payload

    def _execute_step(self, step: AgentStep) -> dict[str, Any]:
        if step.action in LOCAL_ACTION_MAP:
            from services import local_action_executor

            return local_action_executor.execute_local_action({"action": LOCAL_ACTION_MAP[step.action], "params": self._local_action_params(step)})
        if step.action == "read_safe_system_status":
            return self._read_safe_system_status()
        if step.action == "list_safe_directory_metadata":
            return self._list_safe_directory_metadata(step.params.get("path"))
        if step.action == "create_reminder":
            from core.personal_assistant import reminder_engine

            return reminder_engine.create_reminder(step.params)
        return {"ok": False, "action": step.action, "message": "Unsupported autonomous step."}

    def _local_action_params(self, step: AgentStep) -> dict[str, Any]:
        if step.action == "open_application":
            return {"app": step.params.get("app")}
        if step.action == "open_url":
            return {"url": step.params.get("url")}
        return {}

    def _read_safe_system_status(self) -> dict[str, Any]:
        try:
            from daily_use_readiness import collect_daily_use_readiness

            readiness = collect_daily_use_readiness()
        except Exception as error:
            readiness = {"ok": True, "status": "warning", "message": compact_text(error)}
        return {"ok": True, "action": "read_safe_system_status", "message": "Safe system status read.", "data": {"daily_use_readiness": readiness}}

    def _list_safe_directory_metadata(self, raw_path: Any) -> dict[str, Any]:
        try:
            from services import local_action_executor

            roots = [os.path.abspath(path) for path in getattr(local_action_executor, "SAFE_ROOTS", []) if path]
            target = os.path.abspath(os.path.expanduser(compact_text(raw_path)))
            allowed = any(os.path.commonpath([target, root]) == root for root in roots)
            if not allowed:
                return {"ok": False, "action": "list_safe_directory_metadata", "message": "Directory is outside safe local action roots.", "data": {"path": target}}
            if not os.path.isdir(target):
                return {"ok": False, "action": "list_safe_directory_metadata", "message": "Directory does not exist.", "data": {"path": target}}
            entries = []
            for child in sorted(Path(target).iterdir(), key=lambda item: item.name.lower())[:50]:
                entries.append({"name": child.name, "type": "directory" if child.is_dir() else "file"})
            return {"ok": True, "action": "list_safe_directory_metadata", "message": "Directory metadata listed.", "data": {"path": target, "entry_count": len(entries), "entries": entries}}
        except Exception as error:
            return {"ok": False, "action": "list_safe_directory_metadata", "message": f"Directory metadata warning: {compact_text(error)}", "data": {}}
