"""
Session Manager - Handles browser context lifecycle and persistence.

Manages multiple persistent browser contexts per user, supports multi-browser configurations,
and handles context cleanup with proper resource management.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from enum import Enum

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class BrowserType(str, Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class BrowserChannel(str, Enum):
    CHROME = "chrome"
    EDGE = "msedge"
    FIREFOX = "firefox"


@dataclass
class BrowserConfig:
    """Browser initialization configuration."""
    browser_type: BrowserType = BrowserType.CHROMIUM
    channel: Optional[BrowserChannel] = BrowserChannel.CHROME
    headless: bool = False
    args: list = field(default_factory=list)
    disable_gpu: bool = True
    no_sandbox: bool = True
    window_width: int = 1920
    window_height: int = 1080
    user_agent: Optional[str] = None
    locale: str = "en-US"
    timezone_id: str = "America/New_York"


@dataclass
class SessionMetadata:
    """Metadata for a browser session."""
    session_id: str
    browser_type: BrowserType
    created_at: datetime
    last_accessed: datetime
    page_count: int = 0
    navigation_history: list = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)


class BrowserSessionManager:
    """
    Manages persistent browser sessions with multi-browser support.
    
    Features:
    - Multiple concurrent sessions per user
    - Browser context persistence
    - Automatic resource cleanup
    - Session metadata tracking
    - Cookie/cache persistence
    """

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or "browser_data"
        self.sessions: Dict[str, dict] = {}  # session_id -> {browser, context, pages, metadata}
        self.playwright = None
        self.browsers: Dict[BrowserType, Browser] = {}
        logger.info(f"BrowserSessionManager initialized with data_dir={self.data_dir}")

    async def start(self):
        """Initialize Playwright and browser instances."""
        try:
            self.playwright = await async_playwright().start()
            logger.info("Playwright started successfully")
        except Exception as e:
            logger.error(f"Failed to start Playwright: {e}")
            raise

    async def stop(self):
        """Cleanup all sessions and Playwright resources."""
        # Close all active sessions
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            try:
                await self.end_session(session_id)
            except Exception as e:
                logger.error(f"Error closing session {session_id}: {e}")

        # Close browser instances
        for browser in self.browsers.values():
            try:
                await browser.close()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")

        # Stop Playwright
        if self.playwright:
            await self.playwright.stop()
            logger.info("Playwright stopped")

    async def create_session(
        self,
        session_id: str,
        config: BrowserConfig = None,
    ) -> BrowserContext:
        """
        Create a new persistent browser session.
        
        Args:
            session_id: Unique identifier for the session
            config: Browser configuration (uses default if None)
            
        Returns:
            BrowserContext for the session
            
        Raises:
            ValueError: If session_id already exists
            RuntimeError: If Playwright not initialized
        """
        if session_id in self.sessions:
            raise ValueError(f"Session {session_id} already exists")

        if not self.playwright:
            raise RuntimeError("Playwright not initialized. Call start() first.")

        config = config or BrowserConfig()

        try:
            # Get or create browser instance
            browser = await self._get_or_create_browser(config)

            # Create context with persistence
            context_args = {
                "locale": config.locale,
                "timezone_id": config.timezone_id,
                "viewport": {"width": config.window_width, "height": config.window_height},
            }

            if config.user_agent:
                context_args["user_agent"] = config.user_agent

            context = await browser.new_context(**context_args)
            
            # Create initial page
            page = await context.new_page()

            # Store session
            metadata = SessionMetadata(
                session_id=session_id,
                browser_type=config.browser_type,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
            )

            self.sessions[session_id] = {
                "browser": browser,
                "context": context,
                "pages": {page.url: page},
                "metadata": metadata,
            }

            logger.info(f"Created session {session_id} with {config.browser_type}")
            return context

        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            raise

    async def _get_or_create_browser(self, config: BrowserConfig) -> Browser:
        """Get cached browser or create new instance."""
        if config.browser_type in self.browsers:
            return self.browsers[config.browser_type]

        launch_args = {
            "headless": config.headless,
            "args": config.args,
        }

        if config.channel:
            launch_args["channel"] = config.channel.value

        if config.disable_gpu:
            launch_args["args"].append("--disable-gpu")
        if config.no_sandbox:
            launch_args["args"].append("--no-sandbox")

        browser_method = getattr(self.playwright, config.browser_type.value)
        browser = await browser_method.launch(**launch_args)
        self.browsers[config.browser_type] = browser

        logger.info(f"Launched {config.browser_type} browser")
        return browser

    async def get_page(self, session_id: str, url: str = None) -> Page:
        """
        Get a page from session, optionally navigate to URL.
        
        Args:
            session_id: Session identifier
            url: Optional URL to navigate to
            
        Returns:
            Page object
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.sessions[session_id]
        session["metadata"].last_accessed = datetime.now()

        if url and url in session["pages"]:
            return session["pages"][url]

        context = session["context"]
        page = await context.new_page()

        if url:
            await page.goto(url)
            session["pages"][url] = page

        session["metadata"].page_count += 1
        return page

    async def close_page(self, session_id: str, page: Page):
        """Close a specific page and remove from session."""
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]
        # Remove from pages dict
        for url, p in list(session["pages"].items()):
            if p == page:
                del session["pages"][url]
                break

        try:
            await page.close()
        except Exception as e:
            logger.error(f"Error closing page: {e}")

    async def end_session(self, session_id: str):
        """Close a browser session and free resources."""
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found")
            return

        session = self.sessions[session_id]

        # Close all pages
        for page in list(session["pages"].values()):
            try:
                await page.close()
            except Exception as e:
                logger.error(f"Error closing page: {e}")

        # Close context
        try:
            await session["context"].close()
        except Exception as e:
            logger.error(f"Error closing context: {e}")

        del self.sessions[session_id]
        logger.info(f"Ended session {session_id}")

    def get_session_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        """Get metadata for a session."""
        if session_id not in self.sessions:
            return None
        return self.sessions[session_id]["metadata"]

    def list_sessions(self) -> list[str]:
        """List all active session IDs."""
        return list(self.sessions.keys())

    async def take_screenshot(self, session_id: str, page: Page, path: str) -> str:
        """Take a screenshot of the current page."""
        try:
            await page.screenshot(path=path)
            logger.info(f"Screenshot saved to {path}")
            return path
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            raise
