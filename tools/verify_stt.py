import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arc.voice.stt import get_whisper_stt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_stt():
    logger.info("Verifying Speech-to-Text...")
    
    try:
        stt = get_whisper_stt()
        
        # Test model loading
        logger.info("Loading Whisper model (this may take a while on first run)...")
        stt.load_model()
        logger.info("Model loaded successfully!")
        
        # For actual transcription testing, you would need:
        # 1. A sample audio file, or
        # 2. Record from microphone
        
        # Example (commented out as it requires audio input):
        # audio = stt.record_audio(duration=3.0)
        # text = stt.transcribe_audio(audio)
        # logger.info(f"Transcribed: {text}")
        
        logger.info("STT verification passed (model loading successful)")
        
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        logger.info("Install with: pip install openai-whisper pyaudio")
    except Exception as e:
        logger.error(f"STT Verification Failed: {e}")

if __name__ == "__main__":
    verify_stt()
