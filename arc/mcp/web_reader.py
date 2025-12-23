"""
Web Reader MCP Server for ARC.
Provides safe, read-only text extraction from webpages.
Adheres to robots.txt and strictly blocks non-HTML content.
"""
import logging
import requests
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WebReaderMCP:
    """
    Web Reader Tool Provider.
    Fetches and extracts text from a single URL.
    """
    USER_AGENT = "ARC-WebReader/1.0"

    def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatcher for web reader tools.
        """
        try:
            if tool_name == "read_webpage":
                return self.read_webpage(args.get("url", ""))
            else:
                 return {"status": "error", "error": f"Unknown tool: {tool_name}", "data": None}
                 
        except Exception as e:
            logger.error(f"WebReader MCP Execute Error: {e}")
            return {"status": "error", "error": str(e), "data": None}

    def _can_fetch(self, url: str) -> bool:
        """
        Check robots.txt for permission.
        """
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = f"{base_url}/robots.txt"
            
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch(self.USER_AGENT, url)
        except Exception as e:
            # If robots.txt fails (e.g. 404), default to allow, or safe deny?
            # Standard is default allow if no robots.txt
            logger.warning(f"Robots.txt check failed for {url}: {e}. Allowing.")
            return True

    def read_webpage(self, url: str) -> Dict[str, Any]:
        if not url:
            return {"status": "error", "error": "No URL provided", "data": None}

        # Validate URL scheme
        if not url.startswith("http"):
             return {"status": "error", "error": "URL must start with http/https", "data": None}

        # 1. Check Robots.txt
        if not self._can_fetch(url):
             return {"status": "error", "error": "Access denied by robots.txt", "data": None}

        try:
            # 2. Fetch Headers first (Safety: Content-Type)
            # Use stream=True to peek headers before download
            with requests.get(url, headers={"User-Agent": self.USER_AGENT}, stream=True, timeout=5) as r:
                r.raise_for_status()
                
                content_type = r.headers.get("Content-Type", "").lower()
                if "text/html" not in content_type and "text/plain" not in content_type:
                    return {"status": "error", "error": f"Unsupported Content-Type: {content_type}", "data": None}
                
                # 3. Size Limit (500KB)
                MAX_SIZE = 500 * 1024
                content = ""
                for chunk in r.iter_content(chunk_size=8192, decode_unicode=True):
                    content += chunk
                    if len(content) > MAX_SIZE:
                        logger.warning(f"Truncated {url} at 500KB")
                        break
            
            # 4. Extract Text
            soup = BeautifulSoup(content, "html.parser")
            
            # Remove scripts, styles, metadata
            for script in soup(["script", "style", "meta", "noscript", "header", "footer", "nav"]):
                script.decompose()
                
            text = soup.get_text(separator="\n")
            
            # Clean whitespace
            lines = (line.strip() for line in text.splitlines())
            clean_text = "\n".join(line for line in lines if line)
            
            return {"status": "success", "data": clean_text[:10000], "error": None} # Cap return size too

        except requests.Timeout:
             return {"status": "error", "error": "Request timed out (5s)", "data": None}
        except Exception as e:
             return {"status": "error", "error": str(e), "data": None}
