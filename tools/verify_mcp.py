import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arc.config import get_config
from arc.mcp.client import get_mcp_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_mcp():
    logger.info("Verifying MCP Client Manager...")
    
    # We might need to mock or ensure at least one server is available.
    # If the user doesn't have `npx` or the mcp servers installed, this will fail.
    # For verification purpose, let's create a dummy python script echoing tools if needed,
    # or just try to start what's configured and report status.
    
    manager = get_mcp_manager()
    
    # Temporarily disable servers that might not exist to allow at least one to pass if possible
    # Or just let it try and report errors
    
    try:
        await manager.start()
        
        tools = manager.get_all_tools()
        logger.info(f"Discovered {len(tools)} tools across {len(manager.sessions)} connected servers.")
        
        for name, session in manager.sessions.items():
            logger.info(f"Server '{name}' connected successfully.")
            
        if not manager.sessions:
            logger.warning("No servers connected successfully. Check your configuration and installed packages.")
            
    except Exception as e:
        logger.error(f"MCP Verification Failed: {e}")
    finally:
        await manager.stop()

if __name__ == "__main__":
    asyncio.run(verify_mcp())
