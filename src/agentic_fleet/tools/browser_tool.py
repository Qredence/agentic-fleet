"""Browser automation tool using Playwright for real-time web browsing.

This tool allows agents to actually browse websites, extract content, and interact
with web pages to get the most up-to-date information.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlparse

from agent_framework import ToolProtocol

from agentic_fleet.tools.serialization import SerializationMixin

if TYPE_CHECKING:
    from playwright.async_api import (
        Browser,  # type: ignore[import]
        Page,
    )

async_playwright_factory: Callable[[], Any] | None = None
PlaywrightTimeoutError: type[Exception]
try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright as _async_playwright  # type: ignore[import]

    PLAYWRIGHT_AVAILABLE = True
    async_playwright_factory = _async_playwright
except ImportError:
    PlaywrightTimeoutError = TimeoutError
    PLAYWRIGHT_AVAILABLE = False


class BrowserTool(SerializationMixin, ToolProtocol):
    """
    Browser automation tool using Playwright for real-time web browsing.

    Allows agents to navigate to URLs, extract content, take screenshots,
    and interact with web pages to get current information.
    """

    # Class-level shared instances
    _shared_browser: Browser | None = None
    _shared_playwright: Any | None = None

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialize browser tool.

        Args:
            headless: Run browser in headless mode (default: True)
            timeout: Page navigation timeout in milliseconds (default: 30000)
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "playwright is not installed. Install it with: "
                "uv pip install playwright && playwright install chromium"
            )

        self.headless = headless
        self.timeout = timeout
        # Instance-level references are removed in favor of class-level shared ones
        self.name = "browser"
        self.description = (
            "Browse websites and extract real-time content. Navigate to URLs, "
            "extract text content, take screenshots, and interact with web pages. "
            "Provides access to the most current information directly from websites."
        )
        self.additional_properties: dict[str, Any] | None = None

    @classmethod
    async def _ensure_browser(cls, headless: bool = True) -> Browser:
        """Ensure browser is initialized (shared instance)."""
        if cls._shared_browser is None:
            if async_playwright_factory is None:  # pragma: no cover - import guard
                raise RuntimeError("Playwright is not available")

            factory = cast(Callable[[], Any], async_playwright_factory)
            playwright_manager = factory()
            cls._shared_playwright = await playwright_manager.start()
            playwright_obj = cast(Any, cls._shared_playwright)
            cls._shared_browser = await playwright_obj.chromium.launch(headless=headless)

        assert cls._shared_browser is not None
        return cls._shared_browser

    @classmethod
    async def cleanup(cls) -> None:
        """Clean up shared browser resources."""
        if cls._shared_browser:
            await cls._shared_browser.close()
            cls._shared_browser = None
        if cls._shared_playwright:
            await cls._shared_playwright.stop()
            cls._shared_playwright = None

    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to navigate to (must include http:// or https://)",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["navigate", "extract_text", "extract_links", "screenshot"],
                            "description": "Action to perform: 'navigate' (just load page), 'extract_text' (get page content), 'extract_links' (get all links), 'screenshot' (take screenshot)",
                            "default": "extract_text",
                        },
                        "wait_for": {
                            "type": "string",
                            "description": "Optional: CSS selector or text to wait for before extracting content",
                        },
                        "max_length": {
                            "type": "integer",
                            "description": "Maximum length of extracted text (default: 10000 characters)",
                            "default": 10000,
                        },
                    },
                    "required": ["url"],
                },
            },
        }

    async def run(
        self,
        url: str,
        action: str = "extract_text",
        wait_for: str | None = None,
        max_length: int = 10000,
    ) -> str:
        """
        Browse a website and perform the specified action.

        Args:
            url: URL to navigate to
            action: Action to perform (navigate, extract_text, extract_links, screenshot)
            wait_for: Optional CSS selector or text to wait for
            max_length: Maximum length of extracted text

        Returns:
            Result string based on the action performed
        """
        if not PLAYWRIGHT_AVAILABLE:
            return "Error: playwright is not installed. Install with: uv pip install playwright && playwright install chromium"

        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
        elif parsed.scheme not in ("http", "https"):
            return f"Error: Invalid URL scheme. Only http:// and https:// are supported. Got: {
                parsed.scheme
            }"

        page: Page | None = None
        try:
            browser = await self._ensure_browser(self.headless)
            page = await browser.new_page()

            # Set reasonable timeouts
            page.set_default_timeout(self.timeout)
            page.set_default_navigation_timeout(self.timeout)

            # Navigate to URL
            try:
                await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            except PlaywrightTimeoutError:
                # Try with domcontentloaded if networkidle times out
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)

            # Wait for specific element if requested
            if wait_for:
                try:
                    # Try as CSS selector first
                    await page.wait_for_selector(wait_for, timeout=5000)
                except PlaywrightTimeoutError:
                    # Try as text content
                    try:  # noqa: SIM105
                        await page.wait_for_function(
                            f"document.body.innerText.includes('{wait_for}')",
                            timeout=5000,
                        )
                    except PlaywrightTimeoutError:
                        pass  # Continue anyway

            # Perform requested action
            if action == "navigate":
                result = f"Successfully navigated to {url}"
            elif action == "extract_text":
                # Extract main content
                content = await page.evaluate(
                    """
                    () => {
                        // Remove script and style elements
                        const scripts = document.querySelectorAll('script, style, nav, header, footer, aside');
                        scripts.forEach(el => el.remove());

                        // Get main content
                        const main = document.querySelector('main, article, [role="main"]') || document.body;
                        return main.innerText || main.textContent || '';
                    }
                """
                )

                # Truncate if needed
                if len(content) > max_length:
                    content = (
                        content[:max_length] + f"\n\n[Content truncated at {max_length} characters]"
                    )

                result = f"Content from {url}:\n\n{content}"

            elif action == "extract_links":
                links = await page.evaluate(
                    """
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        return links.map(a => ({
                            text: a.innerText.trim(),
                            url: a.href
                        })).filter(link => link.url && link.url.startsWith('http'));
                    }
                """
                )

                if links:
                    link_list = "\n".join(
                        [f"- {link['text']}: {link['url']}" for link in links[:50]]
                    )
                    result = f"Links found on {url}:\n\n{link_list}"
                    if len(links) > 50:
                        result += f"\n\n[Showing first 50 of {len(links)} links]"
                else:
                    result = f"No links found on {url}"

            elif action == "screenshot":
                import tempfile
                import time

                screenshot_path = os.path.join(
                    tempfile.gettempdir(), f"browser_screenshot_{int(time.time())}.png"
                )
                await page.screenshot(path=screenshot_path, full_page=True)
                result = f"Screenshot saved to {screenshot_path} for {url}"
            else:
                result = f"Error: Unknown action '{action}'. Valid actions: navigate, extract_text, extract_links, screenshot"

            return result

        except Exception as e:
            return f"Error browsing {url}: {e!s}"
        finally:
            # Always close the page
            if page is not None:
                with contextlib.suppress(Exception):
                    await page.close()

    def __str__(self) -> str:
        return self.name

    def __del__(self):
        """
        Cleanup on deletion.

        Note: Explicit cleanup() call is preferred. This is a best-effort fallback
        that warns but doesn't act, as managing async lifecycle from __del__
        is unreliable with shared class-level resources.
        """
        pass

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """Convert tool to dictionary format for agent-framework.

        Returns the OpenAI function calling schema format.
        """
        return self.schema
