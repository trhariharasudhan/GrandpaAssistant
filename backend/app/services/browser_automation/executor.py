"""
Browser Executor - Executes Playwright actions with retry logic and error handling.

Provides robust action execution with:
- Retry logic with exponential backoff
- Comprehensive error handling
- Timeout management
- Human-like delays
- Action result tracking
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

logger = logging.getLogger(__name__)


class ActionStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    RETRY = "retry"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ActionResult:
    """Result of executing an action."""
    action_type: str
    status: ActionStatus
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BrowserExecutor:
    """
    Executes Playwright actions with robust retry and error handling.
    
    Features:
    - Exponential backoff retry logic
    - Configurable timeouts
    - Human-like navigation delays
    - Screenshot capture on failure
    - Comprehensive action logging
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        page_load_timeout: int = 30000,
        action_timeout: int = 10000,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.page_load_timeout = page_load_timeout
        self.action_timeout = action_timeout
        self.action_history: list[ActionResult] = []

    def _get_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        delay = self.base_delay * (2 ** attempt)
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter

    def _add_human_delay(self, min_ms: int = 200, max_ms: int = 1000):
        """Add random delay to simulate human behavior."""
        delay = random.uniform(min_ms, max_ms) / 1000.0
        return delay

    async def navigate(
        self,
        page: Page,
        url: str,
        wait_until: str = "networkidle",
    ) -> ActionResult:
        """
        Navigate to a URL with retry logic.
        
        Args:
            page: Playwright page
            url: URL to navigate to
            wait_until: When to consider navigation complete
            
        Returns:
            ActionResult with navigation status
        """
        start_time = datetime.now()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Navigating to {url} (attempt {attempt + 1}/{self.max_retries})")
                
                await page.goto(url, wait_until=wait_until, timeout=self.page_load_timeout)
                
                # Add human-like delay
                await asyncio.sleep(self._add_human_delay())

                duration = (datetime.now() - start_time).total_seconds() * 1000
                result = ActionResult(
                    action_type="navigate",
                    status=ActionStatus.SUCCESS,
                    success=True,
                    result={"url": url, "title": page.title()},
                    duration_ms=duration,
                    retry_count=attempt,
                )
                self.action_history.append(result)
                logger.info(f"Navigation successful: {url}")
                return result

            except PlaywrightTimeoutError as e:
                last_error = f"Navigation timeout: {str(e)}"
                logger.warning(f"Navigation timeout (attempt {attempt + 1}): {url}")

            except PlaywrightError as e:
                last_error = f"Navigation error: {str(e)}"
                logger.warning(f"Navigation error (attempt {attempt + 1}): {str(e)}")

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error during navigation: {str(e)}")

            if attempt < self.max_retries - 1:
                delay = self._get_retry_delay(attempt)
                logger.info(f"Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)

        # All retries exhausted
        duration = (datetime.now() - start_time).total_seconds() * 1000
        result = ActionResult(
            action_type="navigate",
            status=ActionStatus.FAILED,
            success=False,
            error=last_error,
            duration_ms=duration,
            retry_count=self.max_retries,
        )
        self.action_history.append(result)
        return result

    async def click(
        self,
        page: Page,
        selector: str,
        button: str = "left",
        click_count: int = 1,
    ) -> ActionResult:
        """Click an element with retry logic."""
        start_time = datetime.now()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Clicking {selector} (attempt {attempt + 1})")
                
                # Wait for element to be visible
                await page.wait_for_selector(selector, timeout=self.action_timeout)
                
                # Scroll into view
                await page.locator(selector).scroll_into_view_if_needed()
                
                # Click
                await page.click(selector, button=button, click_count=click_count)
                
                # Add human-like delay
                await asyncio.sleep(self._add_human_delay())

                duration = (datetime.now() - start_time).total_seconds() * 1000
                result = ActionResult(
                    action_type="click",
                    status=ActionStatus.SUCCESS,
                    success=True,
                    result={"selector": selector},
                    duration_ms=duration,
                    retry_count=attempt,
                )
                self.action_history.append(result)
                logger.info(f"Click successful: {selector}")
                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Click failed (attempt {attempt + 1}): {selector} - {str(e)}")

            if attempt < self.max_retries - 1:
                delay = self._get_retry_delay(attempt)
                await asyncio.sleep(delay)

        duration = (datetime.now() - start_time).total_seconds() * 1000
        result = ActionResult(
            action_type="click",
            status=ActionStatus.FAILED,
            success=False,
            error=last_error,
            duration_ms=duration,
            retry_count=self.max_retries,
        )
        self.action_history.append(result)
        return result

    async def fill(
        self,
        page: Page,
        selector: str,
        text: str,
        clear: bool = True,
    ) -> ActionResult:
        """Fill a form field with retry logic."""
        start_time = datetime.now()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Filling {selector} (attempt {attempt + 1})")
                
                await page.wait_for_selector(selector, timeout=self.action_timeout)
                
                if clear:
                    await page.fill(selector, "")
                
                # Type character by character for human-like input
                await page.locator(selector).type(text, delay=random.uniform(10, 50))
                
                await asyncio.sleep(self._add_human_delay(100, 300))

                duration = (datetime.now() - start_time).total_seconds() * 1000
                result = ActionResult(
                    action_type="fill",
                    status=ActionStatus.SUCCESS,
                    success=True,
                    result={"selector": selector, "text_length": len(text)},
                    duration_ms=duration,
                    retry_count=attempt,
                )
                self.action_history.append(result)
                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Fill failed (attempt {attempt + 1}): {selector}")

            if attempt < self.max_retries - 1:
                delay = self._get_retry_delay(attempt)
                await asyncio.sleep(delay)

        duration = (datetime.now() - start_time).total_seconds() * 1000
        result = ActionResult(
            action_type="fill",
            status=ActionStatus.FAILED,
            success=False,
            error=last_error,
            duration_ms=duration,
            retry_count=self.max_retries,
        )
        self.action_history.append(result)
        return result

    async def extract_text(
        self,
        page: Page,
        selector: str,
    ) -> ActionResult:
        """Extract text from an element."""
        try:
            logger.info(f"Extracting text from {selector}")
            
            await page.wait_for_selector(selector, timeout=self.action_timeout)
            text = await page.locator(selector).text_content()

            result = ActionResult(
                action_type="extract_text",
                status=ActionStatus.SUCCESS,
                success=True,
                result={"selector": selector, "text": text},
                duration_ms=0,
            )
            self.action_history.append(result)
            return result

        except Exception as e:
            logger.error(f"Extract text failed: {str(e)}")
            result = ActionResult(
                action_type="extract_text",
                status=ActionStatus.FAILED,
                success=False,
                error=str(e),
            )
            self.action_history.append(result)
            return result

    async def take_screenshot(self, page: Page, path: str) -> ActionResult:
        """Take a screenshot of the current page."""
        try:
            logger.info(f"Taking screenshot: {path}")
            await page.screenshot(path=path)
            
            result = ActionResult(
                action_type="screenshot",
                status=ActionStatus.SUCCESS,
                success=True,
                result={"path": path},
            )
            self.action_history.append(result)
            return result

        except Exception as e:
            logger.error(f"Screenshot failed: {str(e)}")
            result = ActionResult(
                action_type="screenshot",
                status=ActionStatus.FAILED,
                success=False,
                error=str(e),
            )
            self.action_history.append(result)
            return result

    def get_action_history(self, limit: int = 50) -> list[ActionResult]:
        """Get recent action history."""
        return self.action_history[-limit:]

    def clear_history(self):
        """Clear action history."""
        self.action_history.clear()
