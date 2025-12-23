import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arc.core.memory import get_memory_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_memory():
    logger.info("Verifying Persistent Memory...")
    
    manager = get_memory_manager()
    
    # Test Short Term
    manager.add_short_term({"role": "user", "content": "Hello"})
    st = manager.get_short_term()
    logger.info(f"Short term memory size: {len(st)}")
    
    # Test Long Term (Plain)
    key = "user_name"
    val = "Jay"
    manager.store_long_term(key, val)
    retrieved = manager.retrieve_long_term(key)
    logger.info(f"Retrieved plain memory: {key} = {retrieved}")
    
    if retrieved != val:
        logger.error("Plain memory mismatch!")

    # Test Long Term (Encrypted)
    key_enc = "api_secret"
    val_enc = "super_secret_123"
    manager.store_long_term(key_enc, val_enc, encrypt=True)
    retrieved_enc = manager.retrieve_long_term(key_enc)
    logger.info(f"Retrieved encrypted memory: {key_enc} = {retrieved_enc}")
    
    if retrieved_enc != val_enc:
        logger.error("Encrypted memory mismatch!")

    # Search
    results = manager.search_memory("user")
    logger.info(f"Search results for 'user': {results}")
    
    # Forget
    manager.forget(key)
    if manager.retrieve_long_term(key) is None:
        logger.info("Successfully forgot memory.")
    else:
        logger.error("Failed to forget memory.")

if __name__ == "__main__":
    verify_memory()
