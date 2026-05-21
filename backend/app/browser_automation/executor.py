from __future__ import annotations

import os
import logging
import time
from typing import Any

from .config import BrowserAutomationConfig, browser_runtime_dir
from .memory import BrowserMemory
from .safety import BrowserSafetyLayer
from .session_manager import BrowserSessionManager


logger = logging.getLogger(__name__)


def _compact_text(value: Any, limit: int = 2000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


class BrowserExecutor:
    def __init__(
        self,
        session_manager: BrowserSessionManager | None = None,
        safety: BrowserSafetyLayer | None = None,
        memory: BrowserMemory | None = None,
        config: BrowserAutomationConfig | None = None,
    ) -> None:
        self.config = config or BrowserAutomationConfig()
        self.session_manager = session_manager or BrowserSessionManager(self.config)
        self.safety = safety or BrowserSafetyLayer()
        self.memory = memory or BrowserMemory()

    def execute_plan(self, plan: dict[str, Any], *, session_id: str | None = None, confirmed: bool = False) -> dict[str, Any]:
        safety = self.safety.assert_safe(plan, confirmed=confirmed)
        if not safety["ok"]:
            return {"ok": False, "executed": False, "message": safety["message"], "safety": safety["safety"], "events": []}
        session = self.session_manager.get_or_create_session(session_id=session_id, browser=plan.get("browser"))
        if session.page is None:
            return {
                "ok": False,
                "executed": False,
                "message": "Browser automation is planned, but Playwright is unavailable or no browser page could be opened.",
                "safety": safety["safety"],
                "events": [],
                "missing_adapter": "playwright",
                "session": {"session_id": session.session_id, "browser": session.browser},
            }

        events = []
        for step in plan.get("steps", []):
            if not isinstance(step, dict):
                continue
            event = self._execute_step_with_retry(session.page, step)
            events.append(event)
            if not event.get("ok") and not step.get("optional"):
                break
            self._human_delay()
        page_info = self._page_info(session.page)
        self.memory.remember_task(task=plan.get("goal", ""), session_id=session.session_id, browser=session.browser, url=page_info.get("url", ""))
        self.memory.remember_session(session.session_id, {"browser": session.browser, **page_info})
        return {
            "ok": all(event.get("ok") or event.get("optional") for event in events),
            "executed": True,
            "message": "Browser automation completed." if events else "Browser session opened.",
            "events": events,
            "page": page_info,
            "safety": safety["safety"],
            "session": {"session_id": session.session_id, "browser": session.browser},
        }

    def _execute_step_with_retry(self, page: Any, step: dict[str, Any]) -> dict[str, Any]:
        attempts = max(1, int(self.config.retry_attempts or 1))
        last_event: dict[str, Any] = {"ok": False, "action": _compact_text(step.get("action")).lower(), "error": "Step was not attempted."}
        for attempt in range(1, attempts + 1):
            last_event = self._execute_step(page, step)
            last_event["attempt"] = attempt
            if last_event.get("ok"):
                return last_event
            if attempt < attempts:
                logger.debug("Browser automation step failed; retrying", extra={"action": last_event.get("action"), "attempt": attempt})
                self._human_delay()
        logger.warning("Browser automation step failed", extra={"action": last_event.get("action"), "error": last_event.get("error")})
        return last_event

    def _execute_step(self, page: Any, step: dict[str, Any]) -> dict[str, Any]:
        action = _compact_text(step.get("action")).lower()
        try:
            if action == "goto":
                page.goto(_compact_text(step.get("url")), wait_until="domcontentloaded", timeout=self.config.navigation_timeout_ms)
                return {"ok": True, "action": action, "url": _compact_text(step.get("url"))}
            if action == "click":
                selector = _compact_text(step.get("selector"))
                page.locator(selector).first.click(timeout=5000)
                return {"ok": True, "action": action, "selector": selector, "description": _compact_text(step.get("description")), "optional": bool(step.get("optional"))}
            if action == "fill":
                selector = _compact_text(step.get("selector"))
                page.locator(selector).first.fill(_compact_text(step.get("value")))
                return {"ok": True, "action": action, "selector": selector}
            if action == "fill_form":
                fields = step.get("fields")
                if not isinstance(fields, dict) or not fields:
                    return {"ok": False, "action": action, "error": "No form fields were provided."}
                filled = []
                for selector, value in fields.items():
                    compact_selector = _compact_text(selector)
                    page.locator(compact_selector).first.fill(_compact_text(value))
                    filled.append(compact_selector)
                return {"ok": True, "action": action, "filled_fields": filled}
            if action == "upload":
                selector = _compact_text(step.get("selector"))
                file_path = _compact_text(step.get("file_path"))
                if not file_path or not os.path.exists(file_path):
                    return {"ok": False, "action": action, "selector": selector, "error": "Upload file does not exist."}
                page.locator(selector).first.set_input_files(file_path)
                return {"ok": True, "action": action, "selector": selector, "file_name": os.path.basename(file_path)}
            if action == "download":
                selector = _compact_text(step.get("selector"))
                download_dir = os.path.join(browser_runtime_dir(), "downloads")
                os.makedirs(download_dir, exist_ok=True)
                with page.expect_download(timeout=self.config.navigation_timeout_ms) as download_info:
                    page.locator(selector).first.click(timeout=5000)
                download = download_info.value
                suggested_name = _compact_text(getattr(download, "suggested_filename", "download.bin"), 180)
                safe_name = os.path.basename(suggested_name) or "download.bin"
                path = os.path.join(download_dir, safe_name)
                download.save_as(path)
                return {"ok": True, "action": action, "selector": selector, "file_name": safe_name, "path": path}
            if action == "read":
                content = self.extract_structured_data(page)
                return {"ok": True, "action": action, "data": content}
            if action == "screenshot":
                return {"ok": True, "action": action, "path": self.screenshot(page)}
            return {"ok": False, "action": action, "error": "Unsupported browser step."}
        except Exception as error:
            return {"ok": False, "action": action, "error": _compact_text(error, 300), "optional": bool(step.get("optional"))}

    def extract_structured_data(self, page: Any) -> dict[str, Any]:
        try:
            title = _compact_text(page.title(), 300)
        except Exception:
            title = ""
        try:
            url = _compact_text(page.url, 1000)
        except Exception:
            url = ""
        try:
            text = _compact_text(page.locator("body").inner_text(timeout=3000), 4000)
        except Exception:
            text = ""
        return {"title": title, "url": url, "text_preview": text, "text_chars": len(text)}

    def screenshot(self, page: Any) -> str:
        directory = os.path.join(browser_runtime_dir(), "screenshots")
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"browser-{int(time.time() * 1000)}.png")
        page.screenshot(path=path, full_page=True)
        return path

    def _page_info(self, page: Any) -> dict[str, str]:
        try:
            title = _compact_text(page.title(), 300)
        except Exception:
            title = ""
        return {"url": _compact_text(getattr(page, "url", ""), 1000), "last_title": title}

    def _human_delay(self) -> None:
        time.sleep(max(0, self.config.human_delay_ms) / 1000.0)
