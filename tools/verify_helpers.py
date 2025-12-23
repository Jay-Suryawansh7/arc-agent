import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arc.config import get_config
from arc.mcp.client import get_mcp_manager
from arc.mcp.browser import get_browser_client
from arc.mcp.git import get_git_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_helpers():
    logger.info("Verifying MCP Helpers...")
    manager = get_mcp_manager()
    
    # We try to start servers just to ensure clients can be instantiated and _call structure is valid
    # actual calls might fail without running servers
    try:
        # Start manager (simulated or real)
        # In a real run without installed servers, this might log errors but shouldn't crash
        await manager.start() 
        
        browser = get_browser_client()
        logger.info(f"Browser Client initialized: {browser}")

        git = get_git_client()
        logger.info(f"Git Client initialized: {git}")
        
    except Exception as e:
        logger.error(f"Helper Verification Failed: {e}")
    finally:
        await manager.stop()

if __name__ == "__main__":
    asyncio.run(verify_helpers())
