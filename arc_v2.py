#!/usr/bin/env python3
"""
ARC - Improved version with intelligent tool routing
Prioritizes system tools over general AI chat
"""
import asyncio
import logging
import subprocess
import re

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from arc.voice.stt import get_whisper_stt
from arc.config import get_config
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from arc.tools.system_tools import (
    open_app, close_app, list_running_apps,
    type_text_keyboard, press_key, screenshot_screen,
    is_app_running
)

class CommandRouter:
    """Smart command routing - tools first, then AI"""
    
    @staticmethod
    def detect_tool_command(text: str):
        """Detect if user wants to use a tool"""
        text_lower = text.lower()
        
        # App listing
        if any(word in text_lower for word in ['list', 'show', 'what']) and \
           any(word in text_lower for word in ['app', 'program', 'process', 'running']):
            return ('list_apps', {})
        
        # App opening
        if 'open' in text_lower:
            # Extract app name after 'open'
            match = re.search(r'open\s+(\w+)', text_lower)
            if match:
                return ('open_app', {'app_name': match.group(1).capitalize()})
        
        # App closing
        if any(word in text_lower for word in ['close', 'quit', 'exit']) and \
           'app' in text_lower or 'application' in text_lower:
            match = re.search(r'(?:close|quit|exit)\s+(\w+)', text_lower)
            if match:
                return ('close_app', {'app_name': match.group(1)})
        
        # Screenshot
        if any(word in text_lower for word in ['screenshot', 'screen shot', 'capture screen']):
            return ('screenshot', {})
        
        # Typing
        if 'type' in text_lower:
            # Extract text to type
            match = re.search(r'type\s+(.+)', text, re.IGNORECASE)
            if match:
                return ('type_text', {'text': match.group(1)})
        
        # Check if app is running
        if 'is' in text_lower and 'running' in text_lower:
            match = re.search(r'is\s+(\w+)\s+running', text_lower)
            if match:
                return ('is_running', {'app_name': match.group(1)})
        
        return None

async def run_arc():
    """
    Improved ARC with tool-first routing
    """
    logger.info("=" * 60)
    logger.info("🤖 ARC - Autonomous Reasoning Companion v2")
    logger.info("=" * 60)
    
    config = get_config()
    router = CommandRouter()
    
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
        test_response = llm.invoke([HumanMessage(content="Hi")])
        logger.info("✅ LLM connected")
    except Exception as e:
        logger.error(f"Failed to connect to Ollama: {e}")
        logger.info("Make sure Ollama is running: ollama serve")
        return
    
    system_prompt = """You are ARC, a helpful voice assistant with system control.
Keep responses brief (1-2 sentences). Be helpful and friendly."""
    
    logger.info("\n✅ ARC ready!")
    logger.info("Try commands like:")
    logger.info("  - 'List my running apps'")
    logger.info("  - 'Open Calculator'")
    logger.info("  - 'Take a screenshot'")
    logger.info("  - 'Is Chrome running?'")
    logger.info("\nPress Ctrl+C to exit\n")
    
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
            
            # Route command
            tool_cmd = router.detect_tool_command(user_input)
            
            if tool_cmd:
                tool_name, params = tool_cmd
                logger.info(f"🔧 Executing: {tool_name}")
                
                # Execute tool
                try:
                    if tool_name == 'list_apps':
                        apps = list_running_apps.invoke({})
                        response = f"You have {len(apps)} apps running. Top 5: {', '.join(apps[:5])}"
                    
                    elif tool_name == 'open_app':
                        result = open_app.invoke(params)
                        response = result
                    
                    elif tool_name == 'close_app':
                        result = close_app.invoke(params)
                        response = result
                    
                    elif tool_name == 'screenshot':
                        result = screenshot_screen.invoke({'path': '/tmp/arc_screenshot.png'})
                        response = result
                    
                    elif tool_name == 'type_text':
                        result = type_text_keyboard.invoke(params)
                        response = result
                    
                    elif tool_name == 'is_running':
                        result = is_app_running.invoke(params)
                        app = params['app_name']
                        response = f"Yes, {app} is running" if result else f"No, {app} is not running"
                    
                    else:
                        response = "Tool not implemented yet"
                        
                except Exception as e:
                    response = f"Error executing tool: {str(e)}"
                    logger.error(f"Tool error: {e}")
            
            else:
                # Use AI for general queries
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
