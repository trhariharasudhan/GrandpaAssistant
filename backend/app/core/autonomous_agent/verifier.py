from __future__ import annotations

from typing import Any

from .action_schema import AgentStep, compact_text


class AgentVerifier:
    def verify(self, step: AgentStep, result: dict[str, Any]) -> dict[str, Any]:
        try:
            if not result.get("ok"):
                return {"status": "warning", "message": compact_text(result.get("message")) or "Step did not report success."}
            if step.action == "open_application":
                return {"status": "ok", "message": "Application open action reported success.", "evidence": {"app": result.get("data", {}).get("app")}}
            if step.action == "open_url":
                return {"status": "ok", "message": "URL open action reported success.", "evidence": {"url": result.get("data", {}).get("url")}}
            if step.action == "take_screenshot":
                return {"status": "ok", "message": "Screenshot action reported success.", "evidence": {"path": result.get("data", {}).get("path")}}
            if step.action == "create_reminder":
                return {"status": "ok", "message": "Reminder service reported success.", "evidence": {"reminder_id": result.get("reminder", {}).get("id")}}
            return {"status": "ok", "message": "Read-only step completed."}
        except Exception as error:
            return {"status": "warning", "message": f"Verification warning: {compact_text(error)}"}
