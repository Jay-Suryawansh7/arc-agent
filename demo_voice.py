#!/usr/bin/env python3
"""
ARC Voice Demo - Test the voice interface (STT + TTS)
This script demonstrates the speech recognition and synthesis capabilities.
"""
import asyncio
import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from arc.voice.tts import get_piper_tts
from arc.voice.stt import get_whisper_stt

async def test_tts():
    """Test Text-to-Speech"""
    logger.info("=" * 50)
    logger.info("Testing Text-to-Speech (Piper)")
    logger.info("=" * 50)
    
    try:
        tts = get_piper_tts()
        
        test_phrases = [
            "Hello, I am ARC, your autonomous reasoning companion.",
            "Text to speech system is now online.",
            "How can I assist you today?"
        ]
        
        for phrase in test_phrases:
            logger.info(f"Speaking: {phrase}")
            tts.speak(phrase)
            await asyncio.sleep(1)  # Pause between phrases
            
        logger.info("✅ TTS test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ TTS test failed: {e}")
        logger.info("Make sure Piper TTS is installed:")
        logger.info("  Download from: https://github.com/rhasspy/piper")

async def test_stt():
    """Test Speech-to-Text"""
    logger.info("=" * 50)
    logger.info("Testing Speech-to-Text (Whisper)")
    logger.info("=" * 50)
    
    try:
        stt = get_whisper_stt()
        
        logger.info("Loading Whisper model... (this may take a moment)")
        stt.load_model()
        
        logger.info("🎤 Recording for 5 seconds - SPEAK NOW!")
        audio = stt.record_audio(duration=5.0)
        
        logger.info("🔄 Transcribing...")
        text = stt.transcribe_audio(audio)
        
        logger.info(f"📝 You said: '{text}'")
        logger.info("✅ STT test completed successfully!")
        
    except ImportError as e:
        logger.error(f"❌ Missing dependencies: {e}")
        logger.info("Install with: pip3 install openai-whisper pyaudio")
    except Exception as e:
        logger.error(f"❌ STT test failed: {e}")

async def interactive_demo():
    """Interactive voice demo"""
    logger.info("=" * 50)
    logger.info("ARC Voice Demo - Interactive Mode")
    logger.info("=" * 50)
    
    try:
        # Initialize both systems
        tts = get_piper_tts()
        stt = get_whisper_stt()
        
        # Welcome message
        welcome = "ARC voice interface initialized. Please speak after the beep."
        logger.info(f"🔊 {welcome}")
        tts.speak(welcome)
        
        # Load STT model
        logger.info("Loading speech recognition...")
        stt.load_model()
        
        while True:
            logger.info("\n" + "=" * 50)
            logger.info("🎤 Listening... (5 seconds)")
            logger.info("Say something or press Ctrl+C to exit")
            logger.info("=" * 50)
            
            try:
                # Record audio
                audio = stt.record_audio(duration=5.0)
                
                # Transcribe
                logger.info("🔄 Processing...")
                text = stt.transcribe_audio(audio)
                
                if text.strip():
                    logger.info(f"📝 You said: '{text}'")
                    
                    # Echo back
                    response = f"You said: {text}"
                    logger.info(f"🔊 ARC: {response}")
                    tts.speak(response)
                else:
                    logger.info("❌ No speech detected")
                    
            except KeyboardInterrupt:
                logger.info("\n👋 Exiting interactive mode...")
                tts.speak("Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in loop: {e}")
                continue
                
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")

async def main():
    """Main entry point"""
    print("\n" + "🎙️  ARC VOICE SYSTEM DEMO" + "\n")
    print("Choose an option:")
    print("1. Test TTS only (Text-to-Speech)")
    print("2. Test STT only (Speech-to-Text)")
    print("3. Interactive demo (STT + TTS)")
    print("4. Run all tests")
    print()
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == "1":
        await test_tts()
    elif choice == "2":
        await test_stt()
    elif choice == "3":
        await interactive_demo()
    elif choice == "4":
        await test_tts()
        await asyncio.sleep(2)
        await test_stt()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())
