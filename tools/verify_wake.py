import logging
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arc.voice.wake import get_wake_detector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def on_wake():
    logger.info("🎤 WAKE WORD DETECTED!")

def verify_wake():
    logger.info("Verifying Wake Word Detection...")
    
    try:
        detector = get_wake_detector()
        
        # Initialize (requires access key in config)
        detector.initialize()
        
        # Register callback
        detector.on_wake_detected(on_wake)
        
        # Start listening
        logger.info("Say the wake word (default: 'jarvis' - or custom 'ARC' if configured)")
        detector.start_listening()
        
        # Listen for 10 seconds
        logger.info("Listening for 10 seconds...")
        time.sleep(10)
        
        detector.stop_listening()
        detector.cleanup()
        
        logger.info("Wake word detection test completed")
        
    except Exception as e:
        logger.error(f"Wake Word Verification Failed: {e}")
        logger.info("Ensure VOICE__PORCUPINE_ACCESS_KEY is set in .env")
        logger.info("Get access key from: https://console.picovoice.ai/")

if __name__ == "__main__":
    verify_wake()
