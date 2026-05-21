from __future__ import annotations

import json
from typing import Any, Iterable

from .config import BrowserAutomationConfig
from .executor import BrowserExecutor
from .memory import BrowserMemory
from .planner import BrowserActionPlanner
from .safety import BrowserSafetyLayer
from .session_manager import BrowserSessionManager


class BrowserAutomationService:
    def __init__(
        self,
        *,
        planner: BrowserActionPlanner | None = None,
        executor: BrowserExecutor | None = None,
        session_manager: BrowserSessionManager | None = None,
        memory: BrowserMemory | None = None,
        safety: BrowserSafetyLayer | None = None,
        config: BrowserAutomationConfig | None = None,
    ) -> None:
        self.config = config or BrowserAutomationConfig()
        self.memory = memory or BrowserMemory()
        self.safety = safety or BrowserSafetyLayer()
        self.session_manager = session_manager or BrowserSessionManager(self.config)
        self.planner = planner or BrowserActionPlanner()
        self.executor = executor or BrowserExecutor(self.session_manager, self.safety, self.memory, self.config)

    def plan(self, request: str, *, url: str = "", browser: str = "chrome") -> dict[str, Any]:
        plan = self.planner.build_plan(request, url=url, browser=browser)
        return {"ok": True, "plan": plan, "safety": self.safety.classify(plan)}

    def execute(self, request: str, *, url: str = "", browser: str = "chrome", session_id: str | None = None, confirmed: bool = False) -> dict[str, Any]:
        planned = self.plan(request, url=url, browser=browser)
        if not planned["ok"]:
            return planned
        result = self.executor.execute_plan(planned["plan"], session_id=session_id, confirmed=confirmed)
        return {"ok": bool(result.get("ok")), "plan": planned["plan"], **result}

    def stream(self, request: str, *, url: str = "", browser: str = "chrome", session_id: str | None = None, confirmed: bool = False) -> Iterable[dict[str, Any]]:
        yield {"type": "plan_start", "request": request}
        planned = self.plan(request, url=url, browser=browser)
        yield {"type": "plan", "plan": planned.get("plan"), "safety": planned.get("safety")}
        if planned.get("safety", {}).get("requires_confirmation") and not confirmed:
            yield {"type": "confirmation_required", "safety": planned["safety"]}
            return
        result = self.executor.execute_plan(planned["plan"], session_id=session_id, confirmed=confirmed)
        for event in result.get("events", []):
            yield {"type": "event", "event": event}
        yield {"type": "done", "ok": bool(result.get("ok")), "result": result}

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "config": {
                "default_browser": self.config.default_browser,
                "allowed_browsers": sorted(self.config.allowed_browsers),
                "safe_mode": self.config.safe_mode,
                "human_delay_ms": self.config.human_delay_ms,
                "retry_attempts": self.config.retry_attempts,
                "screenshot_debugging": self.config.screenshot_debugging,
            },
            "sessions": self.session_manager.status(),
            "memory": self.memory.status(),
        }


_GLOBAL_SERVICE: BrowserAutomationService | None = None


def get_browser_automation_service() -> BrowserAutomationService:
    global _GLOBAL_SERVICE
    if _GLOBAL_SERVICE is None:
        _GLOBAL_SERVICE = BrowserAutomationService()
    return _GLOBAL_SERVICE


def sse_events(events: Iterable[dict[str, Any]]) -> Iterable[str]:
    for event in events:
        yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
