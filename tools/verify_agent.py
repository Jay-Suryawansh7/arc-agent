import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arc.core.deep_agent import build_agent
from arc.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_agent():
    logger.info("Verifying DeepAgent...")
    
    # Ensure config is loaded
    config = get_config()
    
    try:
        agent = await build_agent()
        logger.info("Agent built successfully.")
        
        # Simple invocation - verify it runs without crashing
        # We don't expect a real intelligent response without a powerful local LLM fully hooked up,
        # but this tests the graph connectivity.
        logger.info("Sending test message...")
        response = await agent.ainvoke("Hello, who are you?")
        logger.info(f"Agent Response: {response}")
        
    except Exception as e:
        logger.error(f"Agent Verification Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_agent())
