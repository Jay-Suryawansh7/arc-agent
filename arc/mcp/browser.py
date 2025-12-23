"""
Browser MCP Server for ARC.
Provides safe, execution-only browser interactions.
"""
import webbrowser
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BrowserMCP:
    """
    Browser Tool Provider.
    Opens URLs and searches in the default system browser.
    NO content reading. NO scraping.
    """
    
    WEB_APP_MAP = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://github.com",
        "chatgpt": "https://chatgpt.com",
        "whatsapp": "https://web.whatsapp.com",
        "spotify": "https://open.spotify.com",
        "gmail": "https://mail.google.com",
        "claude": "https://claude.ai"
    }

    def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatcher for browser tools.
        """
        try:
            if tool_name == "open_url":
                return self.open_url(args.get("url", ""))
            elif tool_name == "search_web":
                return self.search_web(args.get("query", ""))
            elif tool_name == "open_web_app":
                return self.open_web_app(args.get("name", ""))
            else:
                 return {"status": "error", "error": f"Unknown tool: {tool_name}", "data": None}
                 
        except Exception as e:
            logger.error(f"Browser MCP Execute Error: {e}")
            return {"status": "error", "error": str(e), "data": None}

    def open_url(self, url: str) -> Dict[str, Any]:
        if not url:
            return {"status": "error", "error": "No URL provided", "data": None}
            
        # Basic sanity check (add scheme if missing)
        if not url.startswith("http"):
            url = "https://" + url
            
        try:
            logger.info(f"🌐 Opening URL: {url}")
            webbrowser.open_new_tab(url)
            return {"status": "success", "data": f"Opened {url}", "error": None}
        except Exception as e:
             return {"status": "error", "error": str(e), "data": None}

    def search_web(self, query: str) -> Dict[str, Any]:
        if not query:
            return {"status": "error", "error": "No query provided", "data": None}
            
        try:
            # Default to DuckDuckGo
            url = f"https://duckduckgo.com/?q={query.replace(' ', '+')}"
            logger.info(f"🔍 Searching: {query}")
            webbrowser.open_new_tab(url)
            return {"status": "success", "data": f"Searched for '{query}'", "error": None}
        except Exception as e:
             return {"status": "error", "error": str(e), "data": None}

    def open_web_app(self, name: str) -> Dict[str, Any]:
        if not name:
             return {"status": "error", "error": "No app name provided", "data": None}
             
        url = self.WEB_APP_MAP.get(name.lower())
        if not url:
             # Fallback to search if not found? Or error?
             # "Constraint: Use static mapping". Error is safer.
             return {"status": "error", "error": f"Unknown web app '{name}'. try search_web instead.", "data": None}
             
        return self.open_url(url)
