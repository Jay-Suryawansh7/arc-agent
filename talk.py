#!/usr/bin/env python3
"""
ARC - Interactive Talking Assistant
Simple conversation mode without wake word (for testing)
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from arc.voice.stt import get_whisper_stt
from arc.voice.tts import get_piper_tts

async def talk():
    """Simple talk loop"""
    logger.info("🤖 ARC Assistant - Conversation Mode")
    logger.info("=" * 50)
    
    # Initialize
    tts = get_piper_tts()
    stt = get_whisper_stt()
    
    logger.info("Loading speech recognition model...")
    stt.load_model()
    
    logger.info("✅ Ready! Press Ctrl+C to exit\n")
    
    while True:
        try:
            # Listen
            logger.info("🎤 Listening... (speak for 5 seconds)")
            audio = stt.record_audio(duration=5.0)
            
            # Transcribe
            logger.info("🔄 Processing...")
            text = stt.transcribe_audio(audio)
            
            if not text.strip():
                logger.info("❌ No speech detected\n")
                continue
            
            logger.info(f"You said: {text}")
            
            # Simple echo response (replace with agent later)
            response = f"I heard you say: {text}"
            logger.info(f"🤖 ARC: {response}\n")
            
            # Speak via command line (faster than Python)
            import subprocess
            subprocess.run(
                f'echo "{response}" | piper --model models/piper/en_US-lessac-medium.onnx --output_file /tmp/arc_response.wav && afplay /tmp/arc_response.wav',
                shell=True,
                capture_output=True
            )
            
        except KeyboardInterrupt:
            logger.info("\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(talk())
