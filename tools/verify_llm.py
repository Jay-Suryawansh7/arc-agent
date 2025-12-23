import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arc.core.llm import get_llm, test_llm
from arc.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_llm():
    logger.info("Verifying LLM Backend Configuration...")
    config = get_config()
    logger.info(f"Target Backend: {config.llm.backend}")
    
    try:
        if config.llm.backend == "llamacpp" and not config.llm.model_path:
             logger.warning("Backend is llamacpp but no model path set. Skipping actual connection test.")
             return

        llm = get_llm()
        success = test_llm(llm)
        if success:
            logger.info("LLM Verification Passed!")
        else:
            logger.error("LLM Verification Failed.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        # Don't exit 1 here if it's just missing model file, we want to allow user to configure later
        logger.info("Please ensure you have configured your .env file or environment variables correctly.")

if __name__ == "__main__":
    verify_llm()
