#!/usr/bin/env python3
"""
ARC - Simplified version with Ollama + System Tools
Voice Input → AI Reasoning → System Actions → Voice Output
"""
import asyncio
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from arc.voice.stt import get_whisper_stt
from arc.config import get_config
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from arc.tools.system_tools import (
    open_app, close_app, list_running_apps,
    type_text_keyboard, press_key, screenshot_screen
)

async def run_arc():
    """
    Simplified ARC:
    1. Listen via STT
    2. Think via Ollama LLM
    3. Act with system tools
    4. Respond via TTS
    """
    logger.info("=" * 60)
    logger.info("🤖 ARC - Autonomous Reasoning Companion (Simplified)")
    logger.info("=" * 60)
    
    config = get_config()
    
    # Initialize voice
    logger.info("Initializing voice systems...")
    stt = get_whisper_stt()
    logger.info("Loading speech recognition...")
    stt.load_model()
    
    # Initialize LLM
    logger.info(f"Connecting to Ollama ({config.llm.model_name})...")
    try:
        llm = ChatOllama(
            model=config.llm.model_name,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature
        )
        # Test connection
        test_response = llm.invoke([HumanMessage(content="Hello")])
        logger.info("✅ LLM connected")
    except Exception as e:
        logger.error(f"Failed to connect to Ollama: {e}")
        logger.info("Make sure Ollama is running: ollama serve")
        return
    
    system_prompt = """You are ARC, a helpful voice assistant. 
You can control the user's computer.

Available tools:
- List running apps
- Open apps (e.g., "open Calculator")
- Close apps
- Type text
- Take screenshots

Be concise in responses (1-2 sentences). Focus on being helpful."""
    
    logger.info("\n✅ ARC ready! Press Ctrl+C to exit\n")
    
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
            
            # Simple command handling
            response = ""
            lower_input = user_input.lower()
            
            if "list" in lower_input and ("app" in lower_input or "process" in lower_input):
                apps = list_running_apps.invoke({})
                response = f"You have {len(apps)} apps running. Some examples: {', '.join(apps[:5])}"
            
            elif "open" in lower_input:
                # Extract app name
                words = user_input.split()
                if len(words) > 1:
                    app_name = words[words.index(next(w for w in words if "open" in w.lower())) + 1]
                    result = open_app.invoke({"app_name": app_name})
                    response = result
                else:
                    response = "Which app would you like me to open?"
            
            elif "screenshot" in lower_input:
                result = screenshot_screen.invoke({"path": "/tmp/arc_screenshot.png"})
                response = result
            
            else:
                # Ask LLM
                logger.info("🧠 Asking AI...")
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_input)
                ]
                ai_response = llm.invoke(messages)
                response = ai_response.content
            
            logger.info(f"ARC: {response}")
            
            # Speak
            logger.info("🔊 Speaking...")
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
