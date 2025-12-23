"""
WhatsApp integration module.
Provides tools for WhatsApp Web automation via BrowserClient.
"""
import logging
from typing import Optional
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func): return func

from arc.mcp.browser import get_browser_client

logger = logging.getLogger(__name__)

@tool
async def open_whatsapp():
    """
    Open WhatsApp Web in the connected browser.
    """
    client = get_browser_client()
    return await client.open_whatsapp_web()

@tool
async def send_whatsapp_message(contact_name: str, message: str):
    """
    Send a WhatsApp message to a specific contact.
    WARNING: Relies on experimental browser automation.
    """
    client = get_browser_client()
    try:
        await client.select_whatsapp_contact(contact_name)
        # Assuming select_whatsapp_contact puts focus in chat box (simplified)
        # Note: Proper implementation needs Robust Selector logic in Browser Client for the chat input
        chat_box = "div[contenteditable='true'][data-tab='10']" # hypothetical selector
        await client.type_text(chat_box, message)
        await client.type_text(chat_box, "\n") # Send with Enter
        return f"Message sent to {contact_name}"
    except Exception as e:
        return f"Failed to send WhatsApp message: {e}"
