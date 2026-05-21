from __future__ import annotations

from typing import Any

from .state import compact_text


class RecoveryEngine:
    def recover(self, node: dict[str, Any], error: str) -> dict[str, Any]:
        return {
            "ok": False,
            "recoverable": True,
            "message": f"Step {compact_text(node.get('node_id'))} failed safely: {compact_text(error)}",
            "next_action": "ask_user_or_retry",
        }


class ExecutorManager:
    def __init__(self, *, browser_service: Any | None = None, chat_manager: Any | None = None, recovery: RecoveryEngine | None = None) -> None:
        self.browser_service = browser_service
        self.chat_manager = chat_manager
        self.recovery = recovery or RecoveryEngine()

    def execute_node(self, node: dict[str, Any], *, approved: bool = False) -> dict[str, Any]:
        if node.get("requires_confirmation") and not approved:
            return {"ok": False, "status": "waiting_for_approval", "node_id": node.get("node_id"), "message": compact_text(node.get("prompt")) or "Approval required before continuing."}
        tool = compact_text(node.get("tool_name"))
        try:
            if tool == "ask_user":
                return {"ok": True, "status": "waiting_for_user", "node_id": node.get("node_id"), "message": compact_text(node.get("prompt"))}
            if tool == "approval_checkpoint":
                return {"ok": True, "status": "approved", "node_id": node.get("node_id"), "message": "Approval checkpoint satisfied."}
            if tool == "browser_automation":
                if self.browser_service is None:
                    from browser_automation.service import get_browser_automation_service

                    self.browser_service = get_browser_automation_service()
                result = self.browser_service.execute(compact_text(node.get("request")), confirmed=approved)
                return {"ok": bool(result.get("ok")), "status": "done" if result.get("ok") else "failed", "node_id": node.get("node_id"), "result": result}
            if tool == "chat_integrations":
                if self.chat_manager is None:
                    from chat_integrations.manager import get_chat_integration_manager

                    self.chat_manager = get_chat_integration_manager()
                return {"ok": False, "status": "waiting_for_details", "node_id": node.get("node_id"), "message": "Message recipient and text are required before sending."}
            if tool == "local_note_draft":
                return {"ok": True, "status": "done", "node_id": node.get("node_id"), "message": "Prepared a local draft outline for review.", "draft": {"title": "Draft", "sections": ["Summary", "Actions", "Next steps"]}}
            return {"ok": False, "status": "unsupported", "node_id": node.get("node_id"), "message": f"No executor is registered for {tool}."}
        except Exception as error:
            return self.recovery.recover(node, compact_text(error))
