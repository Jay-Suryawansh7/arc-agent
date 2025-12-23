#!/usr/bin/env python3
"""
ARC - Full Assistant with DeepAgent
Voice Input → AI Reasoning → Actions → Voice Output
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from arc.voice.stt import get_whisper_stt
from arc.voice.tts import get_piper_tts
from arc.core.deep_agent import build_agent
from arc.config import get_config

async def run_arc():
    """
    Full ARC System:
    1. Listen via STT
    2. Think via DeepAgent (LangGraph + LLM + Tools)
    3. Act (system tools, browser, etc)
    4. Respond via TTS
    """
    logger.info("=" * 60)
    logger.info("🤖 ARC - Autonomous Reasoning Companion")
    logger.info("=" * 60)
    
    config = get_config()
    
    # Initialize components
    logger.info("Initializing voice systems...")
    stt = get_whisper_stt()
    tts = get_piper_tts()
    
    logger.info("Loading speech recognition model...")
    stt.load_model()
    
    logger.info("Building AI agent with reasoning capabilities...")
    try:
        agent = await build_agent()
        logger.info("✅ Agent ready with tools:")
        logger.info("   - System control (apps, keyboard, mouse)")
        logger.info("   - WhatsApp automation")
        logger.info("   - Browser (via MCP)")
        logger.info("   - Git operations")
    except Exception as e:
        logger.error(f"Failed to build agent: {e}")
        logger.info("Note: Agent requires LLM backend configured in .env")
        logger.info("Falling back to echo mode for voice testing...")
        agent = None
    
    logger.info("\n✅ ARC is ready! Press Ctrl+C to exit\n")
    
    while True:
        try:
            # Listen
            logger.info("🎤 Listening... (5 seconds)")
            audio = stt.record_audio(duration=5.0)
            
            # Transcribe
            logger.info("🔄 Processing speech...")
            user_input = stt.transcribe_audio(audio)
            
            if not user_input.strip():
                logger.info("❌ No speech detected\n")
                continue
            
            logger.info(f"You: {user_input}")
            
            # Think & Act
            if agent:
                logger.info("🧠 Agent thinking...")
                try:
                    response = await agent.ainvoke(user_input)
                    logger.info(f"ARC: {response}")
                except Exception as e:
                    response = f"I encountered an error: {str(e)}"
                    logger.error(f"Agent error: {e}")
            else:
                # Fallback without agent
                response = f"I heard: {user_input}. But I need an LLM backend to understand and act on this."
            
            # Speak
            logger.info("🔊 Speaking...")
            import subprocess
            subprocess.run(
                f'echo "{response}" | piper --model models/piper/en_US-lessac-medium.onnx --output_file /tmp/arc_response.wav && afplay /tmp/arc_response.wav',
                shell=True,
                capture_output=True
            )
            logger.info("")
            
        except KeyboardInterrupt:
            logger.info("\n👋 ARC shutting down. Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            continue

if __name__ == "__main__":
    asyncio.run(run_arc())
