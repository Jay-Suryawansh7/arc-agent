import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arc.voice.tts import get_piper_tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_tts():
    logger.info("Verifying Text-to-Speech...")
    
    try:
        tts = get_piper_tts()
        
        # Test synthesis (will require piper to be installed)
        test_text = "Hello, I am ARC, your autonomous reasoning companion."
        
        logger.info(f"Testing TTS with: '{test_text}'")
        
        # Uncomment to actually test (requires piper installation):
        # tts.speak(test_text)
        
        logger.info("TTS module loaded successfully")
        logger.info("Note: Actual synthesis requires Piper TTS to be installed")
        logger.info("Install from: https://github.com/rhasspy/piper")
        
    except Exception as e:
        logger.error(f"TTS Verification Failed: {e}")

if __name__ == "__main__":
    verify_tts()
