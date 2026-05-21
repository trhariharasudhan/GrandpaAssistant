from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

from .config import BrowserAutomationConfig, browser_runtime_dir


def _compact_text(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


@dataclass
class BrowserSession:
    session_id: str
    browser: str
    context: Any = None
    page: Any = None
    profile_dir: str = ""


class BrowserSessionManager:
    def __init__(self, config: BrowserAutomationConfig | None = None) -> None:
        self.config = config or BrowserAutomationConfig()
        self._playwright = None
        self._sessions: dict[str, BrowserSession] = {}
        self._last_error = ""

    def playwright_available(self) -> bool:
        try:
            import playwright.sync_api  # noqa: F401

            return True
        except Exception:
            return False

    def get_or_create_session(self, *, session_id: str | None = None, browser: str | None = None) -> BrowserSession:
        key = _compact_text(session_id, 120) or "browser-" + uuid.uuid4().hex[:8]
        if key in self._sessions:
            return self._sessions[key]
        browser_name = self._normalize_browser(browser)
        profile_dir = os.path.join(browser_runtime_dir(), "profiles", key)
        os.makedirs(profile_dir, exist_ok=True)
        session = BrowserSession(session_id=key, browser=browser_name, profile_dir=profile_dir)
        try:
            self._attach_playwright(session)
            self._last_error = ""
        except Exception as error:
            self._last_error = _compact_text(error, 240)
        self._sessions[key] = session
        return session

    def close_session(self, session_id: str) -> bool:
        session = self._sessions.pop(_compact_text(session_id, 120), None)
        if not session:
            return True
        try:
            if session.context is not None:
                session.context.close()
        except Exception as error:
            self._last_error = _compact_text(error, 240)
            return False
        return True

    def close_all(self) -> None:
        for key in list(self._sessions):
            self.close_session(key)
        try:
            if self._playwright is not None:
                self._playwright.stop()
        except Exception:
            pass
        self._playwright = None

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "playwright_available": self.playwright_available(),
            "session_count": len(self._sessions),
            "sessions": [
                {"session_id": session.session_id, "browser": session.browser, "profile_dir": session.profile_dir, "has_page": session.page is not None}
                for session in self._sessions.values()
            ],
            "last_error": self._last_error,
        }

    def _normalize_browser(self, browser: str | None) -> str:
        value = _compact_text(browser or self.config.default_browser).lower()
        if value == "edge":
            return "edge"
        if value == "chrome":
            return "chrome"
        if value == "firefox":
            return "firefox"
        return "chromium"

    def _attach_playwright(self, session: BrowserSession) -> None:
        if not self.playwright_available():
            raise RuntimeError("Playwright is not installed. Install playwright and browser runtimes to enable real browser automation.")
        from playwright.sync_api import sync_playwright

        if self._playwright is None:
            self._playwright = sync_playwright().start()
        if session.browser == "firefox":
            browser_type = self._playwright.firefox
            session.context = browser_type.launch_persistent_context(
                session.profile_dir,
                headless=self.config.headless,
                accept_downloads=self.config.downloads_enabled,
            )
        else:
            browser_type = self._playwright.chromium
            channel = "msedge" if session.browser == "edge" else ("chrome" if session.browser == "chrome" else None)
            kwargs = {
                "headless": self.config.headless,
                "accept_downloads": self.config.downloads_enabled,
            }
            if channel:
                kwargs["channel"] = channel
            session.context = browser_type.launch_persistent_context(session.profile_dir, **kwargs)
        session.page = session.context.pages[0] if session.context.pages else session.context.new_page()
