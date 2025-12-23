"""
Browser automation module via MCP.
Provides high-level wrappers for browser interactions.
"""
import logging
import asyncio
from typing import Optional, Any
from arc.mcp.client import get_mcp_manager

logger = logging.getLogger(__name__)

class BrowserClient:
    def __init__(self):
        self.manager = get_mcp_manager()
        self.server_name = "browser"

    async def _call(self, tool_name: str, args: dict) -> Any:
        try:
            # Try specific server first, then fallback to search
            try:
                return await self.manager.call_tool(self.server_name, tool_name, args)
            except ValueError:
                 return await self.manager.find_and_call_tool(tool_name, args)
        except Exception as e:
            logger.error(f"Browser tool execution failed ({tool_name}): {e}")
            raise

    async def navigate_to(self, url: str):
        """Navigate to a URL."""
        logger.info(f"Navigating to: {url}")
        return await self._call("navigate", {"url": url})

    async def get_page_content(self) -> str:
        """Get the current page content (text/markdown)."""
        # Tool name depends on specific browser server implementation
        # Assuming common names like 'read_page' or 'get_content'
        # Adjust based on actual available tools from @browsermcp/server
        return await self._call("read_page", {}) 

    async def click_element(self, selector: str):
        """Click an element matching the selector."""
        return await self._call("click", {"selector": selector})

    async def type_text(self, selector: str, text: str):
        """Type text into an element."""
        return await self._call("type", {"selector": selector, "text": text})

    async def screenshot(self) -> Any:
        """Take a screenshot of the current page."""
        return await self._call("screenshot", {})

    async def open_whatsapp_web(self):
        """Open WhatsApp Web."""
        await self.navigate_to("https://web.whatsapp.com")
        logger.info("WhatsApp Web opened. Please scan QR code if not logged in.")

    async def select_whatsapp_contact(self, name: str):
        """
        Select a contact on WhatsApp Web.
        Note: This utilizes generic browser tools and specific selectors.
        Selectors might need maintenance updates.
        """
        search_box = "div[contenteditable='true'][data-tab='3']" # Common selector, might change
        await self.click_element(search_box)
        await self.type_text(search_box, name)
        await asyncio.sleep(1.0) # Wait for search
        # Click first result
        # This is brittle and would require visual grounding or better accessibility selectors in a real implementation
        logger.warning("Selecting WhatsApp contact via generic selectors is experimental.")
        # await self.click_element("span[title='" + name + "']")

# Singleton/Factory if needed
def get_browser_client() -> BrowserClient:
    return BrowserClient()
