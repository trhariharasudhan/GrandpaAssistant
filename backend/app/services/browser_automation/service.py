from __future__ import annotations

import asyncio
import importlib.util
import json
import re
from dataclasses import asdict, is_dataclass
from typing import Any, Iterable

from .action_planner import ActionPlan, ActionStep, BrowserActionPlanner
from .safety_layer import BrowserSafetyLayer


def _compact_text(value: Any, limit: int = 1200) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _playwright_available() -> bool:
    return importlib.util.find_spec("playwright") is not None


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("Browser automation sync API cannot run inside an active event loop.")


def _step_to_dict(step: ActionStep | dict[str, Any]) -> dict[str, Any]:
    if is_dataclass(step):
        payload = asdict(step)
    else:
        payload = dict(step or {})
    return {
        "step_id": payload.get("step_id"),
        "action_type": _compact_text(payload.get("action_type")),
        "selector": _compact_text(payload.get("selector")),
        "value": _compact_text(payload.get("value")),
        "context": _compact_text(payload.get("context")),
        "retryable": bool(payload.get("retryable", True)),
        "confidence": float(payload.get("confidence") or 0.5),
        "fallback_selector": _compact_text(payload.get("fallback_selector")),
    }


def _plan_to_dict(plan: ActionPlan | None, command: str, browser: str, url: str) -> dict[str, Any]:
    if plan is None:
        return {
            "command": _compact_text(command),
            "goal": _compact_text(command),
            "intent": _infer_intent(command),
            "browser": _compact_text(browser) or "chrome",
            "url": _compact_text(url),
            "steps": [],
            "expected_outcome": "",
            "plan_confidence": 0.0,
            "planner": "browser_automation_service_compat",
        }
    return {
        "command": _compact_text(plan.command),
        "goal": _compact_text(plan.goal),
        "intent": _infer_intent(plan.command or command),
        "browser": _compact_text(browser) or "chrome",
        "url": _compact_text(url),
        "steps": [_step_to_dict(step) for step in plan.steps],
        "expected_outcome": _compact_text(plan.expected_outcome),
        "plan_confidence": float(plan.plan_confidence or 0.5),
        "planner": "browser_automation_service_compat",
    }


def _infer_intent(command: str) -> str:
    normalized = _compact_text(command).lower()
    if any(term in normalized for term in ("cab", "taxi", "uber", "ola")):
        return "book_cab"
    if any(term in normalized for term in ("order food", "swiggy", "zomato", "hungry")):
        return "order_food"
    if "youtube" in normalized or "music" in normalized:
        return "play_media"
    if "linkedin" in normalized or "job" in normalized:
        return "apply_job_filters" if "apply" in normalized or "filter" in normalized else "open_linkedin"
    if re.search(r"\b(search|google|find)\b", normalized):
        return "search_web"
    return "browser_task"


class _SessionManagerAdapter:
    def close_session(self, _session_id: str) -> bool:
        return True

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "playwright_available": _playwright_available(),
            "session_count": 0,
            "sessions": [],
            "last_error": "" if _playwright_available() else "Playwright is not installed.",
        }


class BrowserAutomationService:
    """Compatibility service for the API router.

    This wrapper exposes the stable synchronous API expected by
    `browser_automation_api.py` while delegating planning and safety to the
    copied browser automation package. Real Playwright execution is intentionally
    reported as unavailable unless Playwright is installed and a fuller async
    execution bridge is wired later.
    """

    def __init__(self, planner: BrowserActionPlanner | None = None, safety: BrowserSafetyLayer | None = None) -> None:
        self.planner = planner or BrowserActionPlanner()
        self.safety = safety or BrowserSafetyLayer()
        self.session_manager = _SessionManagerAdapter()

    def plan(self, request: str, *, url: str = "", browser: str = "chrome") -> dict[str, Any]:
        command = _compact_text(request, 2000)
        try:
            planned = _run_async(self.planner.plan_action_sequence(command, existing_url=url))
        except Exception:
            planned = None
        plan = _plan_to_dict(planned, command, browser, url)
        safety = self._classify_plan(plan)
        return {"ok": True, "plan": plan, "safety": safety}

    def execute(self, request: str, *, url: str = "", browser: str = "chrome", session_id: str | None = None, confirmed: bool = False) -> dict[str, Any]:
        planned = self.plan(request, url=url, browser=browser)
        safety = planned["safety"]
        if safety.get("requires_confirmation") and not confirmed:
            return {
                "ok": False,
                "executed": False,
                "plan": planned["plan"],
                "safety": safety,
                "message": "Confirmation required before running this browser automation.",
                "events": [],
            }
        if not _playwright_available():
            return {
                "ok": False,
                "executed": False,
                "plan": planned["plan"],
                "safety": safety,
                "message": "Browser automation is planned, but Playwright is not installed.",
                "missing_adapter": "playwright",
                "install_command": ".venv\\Scripts\\python.exe -m pip install playwright && .venv\\Scripts\\python.exe -m playwright install",
                "events": [],
                "session": {"session_id": session_id or "", "browser": browser},
            }
        return {
            "ok": False,
            "executed": False,
            "plan": planned["plan"],
            "safety": safety,
            "message": "Browser automation planning is available; real async Playwright execution bridge is not enabled in this compatibility wrapper.",
            "missing_adapter": "async_execution_bridge",
            "events": [],
            "session": {"session_id": session_id or "", "browser": browser},
        }

    def stream(self, request: str, *, url: str = "", browser: str = "chrome", session_id: str | None = None, confirmed: bool = False) -> Iterable[dict[str, Any]]:
        yield {"type": "plan_start", "request": _compact_text(request)}
        planned = self.plan(request, url=url, browser=browser)
        yield {"type": "plan", "plan": planned.get("plan"), "safety": planned.get("safety")}
        if planned.get("safety", {}).get("requires_confirmation") and not confirmed:
            yield {"type": "confirmation_required", "safety": planned["safety"]}
            return
        result = self.execute(request, url=url, browser=browser, session_id=session_id, confirmed=confirmed)
        yield {"type": "done", "ok": bool(result.get("ok")), "result": result}

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "package": "backend.app.services.browser_automation",
            "playwright_available": _playwright_available(),
            "service_exports": ["get_browser_automation_service", "sse_events"],
            "sessions": self.session_manager.status(),
        }

    def _classify_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        text = " ".join(
            [
                _compact_text(plan.get("command")),
                _compact_text(plan.get("goal")),
                _compact_text(plan.get("intent")),
                " ".join(_compact_text(step.get("context")) for step in plan.get("steps", []) if isinstance(step, dict)),
            ]
        )
        check = self.safety.classify_action(_compact_text(plan.get("intent")), context=text)
        return {
            "allowed": True,
            "blocked": False,
            "requires_confirmation": self.safety.should_require_confirmation(check),
            "risk_level": check.risk_level.value,
            "reason": check.description,
            "dangerous_keywords": list(check.dangerous_keywords),
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
