"""
Browser Operations - Reusable, composable browser automation operations.

Provides high-level operations built on top of the Executor for common patterns.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from playwright.async_api import Page

logger = logging.getLogger(__name__)


class BrowserOperations:
    """
    High-level browser operations for common automation patterns.
    """

    def __init__(self, executor):
        self.executor = executor

    async def login(
        self,
        page: Page,
        service: str,
        username: str,
        password: str,
        login_url: str,
        username_selector: str,
        password_selector: str,
        submit_selector: str,
    ) -> Dict[str, Any]:
        """
        Perform login flow for a service.
        
        Args:
            page: Playwright page
            service: Service name for logging
            username: Username/email
            password: Password
            login_url: URL of login page
            username_selector: CSS selector for username field
            password_selector: CSS selector for password field
            submit_selector: CSS selector for submit button
            
        Returns:
            Dict with login result and status
        """
        logger.info(f"Starting login for {service}")

        # Navigate to login page
        nav_result = await self.executor.navigate(page, login_url)
        if not nav_result.success:
            return {"success": False, "error": "Failed to navigate to login page"}

        # Fill username
        user_result = await self.executor.fill(page, username_selector, username)
        if not user_result.success:
            return {"success": False, "error": "Failed to fill username"}

        # Fill password
        pass_result = await self.executor.fill(page, password_selector, password)
        if not pass_result.success:
            return {"success": False, "error": "Failed to fill password"}

        # Submit
        submit_result = await self.executor.click(page, submit_selector)
        if not submit_result.success:
            return {"success": False, "error": "Failed to submit login form"}

        # Wait for navigation
        await asyncio.sleep(3)

        return {
            "success": True,
            "service": service,
            "message": f"Successfully logged in to {service}",
        }

    async def fill_form(
        self,
        page: Page,
        form_fields: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Fill multiple form fields.
        
        Args:
            page: Playwright page
            form_fields: Dict of selector -> value
            
        Returns:
            Result dict with filled fields count
        """
        logger.info(f"Filling form with {len(form_fields)} fields")

        filled = []
        failed = []

        for selector, value in form_fields.items():
            result = await self.executor.fill(page, selector, value)
            if result.success:
                filled.append(selector)
            else:
                failed.append((selector, result.error))

        return {
            "total_fields": len(form_fields),
            "filled": len(filled),
            "failed": len(failed),
            "filled_selectors": filled,
            "failed_selectors": failed,
        }

    async def click_and_wait(
        self,
        page: Page,
        selector: str,
        wait_selector: str = None,
        timeout: int = 30000,
    ) -> Dict[str, Any]:
        """
        Click element and wait for page change or specific selector.
        
        Args:
            page: Playwright page
            selector: Selector of element to click
            wait_selector: Optional selector to wait for after click
            timeout: Timeout in ms
            
        Returns:
            Result dict with click status
        """
        logger.info(f"Click and wait: {selector}")

        # Click
        click_result = await self.executor.click(page, selector)
        if not click_result.success:
            return {"success": False, "error": "Click failed"}

        if wait_selector:
            try:
                await page.wait_for_selector(wait_selector, timeout=timeout)
                return {
                    "success": True,
                    "message": f"Clicked and waited for {wait_selector}",
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Wait for selector failed: {str(e)}",
                }

        return {"success": True, "message": "Click successful"}

    async def extract_table_data(
        self,
        page: Page,
        table_selector: str = "table",
    ) -> List[Dict[str, str]]:
        """
        Extract data from HTML table.
        
        Args:
            page: Playwright page
            table_selector: CSS selector for table
            
        Returns:
            List of dicts representing table rows
        """
        try:
            logger.info(f"Extracting table from {table_selector}")

            # Get headers
            headers = await page.locator(f"{table_selector} th").all_text_contents()
            if not headers:
                headers = await page.locator(f"{table_selector} td:first-child").all_text_contents()

            # Get rows
            rows = []
            row_elements = await page.locator(f"{table_selector} tbody tr").count()

            for i in range(row_elements):
                row_selector = f"{table_selector} tbody tr:nth-child({i + 1}) td"
                cells = await page.locator(row_selector).all_text_contents()
                
                if cells:
                    row_dict = {}
                    for j, header in enumerate(headers):
                        if j < len(cells):
                            row_dict[header.strip()] = cells[j].strip()
                    rows.append(row_dict)

            logger.info(f"Extracted {len(rows)} rows from table")
            return rows

        except Exception as e:
            logger.error(f"Failed to extract table: {e}")
            return []

    async def download_file(
        self,
        page: Page,
        download_selector: str,
        download_path: str,
    ) -> Dict[str, Any]:
        """
        Click download link and save file.
        
        Args:
            page: Playwright page
            download_selector: Selector for download link/button
            download_path: Path to save file
            
        Returns:
            Result dict with download status
        """
        try:
            logger.info(f"Downloading file: {download_selector}")

            async with page.expect_download() as download_info:
                await page.click(download_selector)

            download = await download_info.value
            await download.save_as(download_path)

            logger.info(f"File downloaded to {download_path}")
            return {
                "success": True,
                "path": download_path,
                "filename": download.suggested_filename,
            }

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return {"success": False, "error": str(e)}

    async def upload_file(
        self,
        page: Page,
        file_input_selector: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        Upload file via file input.
        
        Args:
            page: Playwright page
            file_input_selector: Selector for file input
            file_path: Path to file to upload
            
        Returns:
            Result dict with upload status
        """
        try:
            logger.info(f"Uploading file: {file_path}")

            await page.locator(file_input_selector).set_input_files(file_path)

            logger.info("File uploaded successfully")
            return {"success": True, "path": file_path}

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_page_title_and_url(self, page: Page) -> Dict[str, str]:
        """Get current page title and URL."""
        return {
            "title": page.title(),
            "url": page.url,
        }

    async def get_all_links(self, page: Page) -> List[Dict[str, str]]:
        """Extract all links from page."""
        try:
            links = []
            link_elements = await page.locator("a").count()

            for i in range(link_elements):
                href = await page.locator(f"a").nth(i).get_attribute("href")
                text = await page.locator(f"a").nth(i).text_content()
                if href:
                    links.append({"text": text or "", "href": href})

            return links

        except Exception as e:
            logger.error(f"Failed to extract links: {e}")
            return []
