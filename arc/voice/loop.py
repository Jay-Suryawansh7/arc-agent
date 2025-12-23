"""
Voice Interaction Loop - Orchestrates the complete voice interaction flow.
Wake Word → STT → Agent → TTS → Repeat
"""
import asyncio
import logging
import time
import subprocess
from typing import Optional, List, Callable
from datetime import datetime, timedelta

from arc.config import get_config
from arc.voice.wake import get_wake_detector
from arc.voice.stt import get_whisper_stt
from arc.voice.tts import get_piper_tts

logger = logging.getLogger(__name__)

class VoiceLoop:
    """
    Orchestrates the complete voice interaction flow.
    """
    
    def __init__(self, agent_callback: Callable):
        """
        Initialize voice loop.
        
        Args:
            agent_callback: Async function that takes text and returns response
        """
        self.config = get_config()
        self.agent_callback = agent_callback
        
        # Components
        self.wake_detector = None
        self.stt = None
        self.tts = None
        
        # State
        self.running = False
        self.paused = False
        self.in_conversation = False
        self.last_interaction_time = None
        self.conversation_timeout = 30  # seconds for follow-up without wake word
        
        # Context
        self.conversation_history: List[dict] = []
        
    async def initialize(self):
        """Initialize all voice components."""
        logger.info("Initializing voice components...")
        
        # STT
        self.stt = get_whisper_stt()
        logger.info("Loading speech recognition model...")
        self.stt.load_model()
        
        # TTS  
        self.tts = get_piper_tts()
        
        # Wake word (optional - requires Porcupine key)
        try:
            self.wake_detector = get_wake_detector()
            self.wake_detector.initialize()
            logger.info("Wake word detection ready")
        except Exception as e:
            logger.warning(f"Wake word disabled: {e}")
            logger.info("Running in continuous mode (no wake word)")
            self.wake_detector = None
        
        logger.info("✅ Voice loop initialized")
    
    def _play_sound(self, sound_type: str):
        """Play confirmation/error sounds."""
        # Simple beep for confirmation
        if sound_type == "wake":
            subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], 
                         capture_output=True)
        elif sound_type == "error":
            subprocess.run(["afplay", "/System/Library/Sounds/Basso.aiff"],
                         capture_output=True)
    
    def _is_follow_up_allowed(self) -> bool:
        """Check if we're within follow-up timeout."""
        if not self.last_interaction_time:
            return False
        
        elapsed = (datetime.now() - self.last_interaction_time).total_seconds()
        return elapsed < self.conversation_timeout
    
    async def process_command(self, skip_wake_word: bool = False):
        """
        Process one voice command.
        
        Args:
            skip_wake_word: If True, skip wake word detection (for follow-ups)
        """
        try:
            # Wait for wake word (unless skipping)
            if not skip_wake_word and self.wake_detector:
                logger.info("👂 Listening for wake word...")
                # Note: This is blocking - in real implementation would be async
                # For now, we skip wake word if not available
                pass
            
            # Play confirmation
            self._play_sound("wake")
            logger.info("🎤 Listening...")
            
            # Record speech (with timeout)
            try:
                audio = self.stt.record_audio(duration=5.0)
            except Exception as e:
                logger.error(f"Recording failed: {e}")
                await self._speak("Sorry, I couldn't hear you")
                return
            
            # Transcribe
            logger.info("🔄 Processing...")
            try:
                user_input = self.stt.transcribe_audio(audio)
            except Exception as e:
                logger.error(f"Transcription failed: {e}")
                await self._speak("Sorry, I didn't catch that")
                return
            
            if not user_input.strip():
                logger.info("No speech detected")
                return
            
            logger.info(f"You: {user_input}")
            
            # Check for interrupt commands
            if any(word in user_input.lower() for word in ['stop', 'cancel', 'nevermind']):
                await self._speak("Okay, cancelled")
                self.in_conversation = False
                return
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now()
            })
            
            # Send to agent
            logger.info("🧠 Processing request...")
            try:
                response = await self.agent_callback(user_input)
            except Exception as e:
                logger.error(f"Agent error: {e}")
                response = "I encountered an error processing that request. Please try again."
            
            # Add response to history
            self.conversation_history.append({
                "role": "assistant", 
                "content": response,
                "timestamp": datetime.now()
            })
            
            # Speak response
            logger.info(f"ARC: {response}")
            await self._speak(response)
            
            # Update state
            self.last_interaction_time = datetime.now()
            self.in_conversation = True
            
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            self._play_sound("error")
    
    async def _speak(self, text: str):
        """Speak text via TTS."""
        try:
            # Use command-line piper for reliability
            subprocess.run(
                f'echo "{text}" | piper --model {self.config.voice.tts_voice} --output_file /tmp/arc_response.wav && afplay /tmp/arc_response.wav',
                shell=True,
                capture_output=True
            )
        except Exception as e:
            logger.error(f"TTS failed: {e}")
    
    async def start(self):
        """Start the voice loop."""
        await self.initialize()
        
        self.running = True
        logger.info("\n✅ ARC Voice Loop Active")
        logger.info("=" * 50)
        
        if self.wake_detector:
            logger.info("Say 'ARC' or the wake word to activate")
        else:
            logger.info("Continuous listening mode (no wake word)")
        
        logger.info("Press Ctrl+C to exit\n")
        
        try:
            while self.running:
                if self.paused:
                    await asyncio.sleep(0.1)
                    continue
                
                # Check if we're in a conversation window
                skip_wake = self._is_follow_up_allowed()
                
                if skip_wake:
                    logger.info("💬 Follow-up question? (or say 'stop')")
                
                await self.process_command(skip_wake_word=skip_wake)
                
                # Small delay
                await asyncio.sleep(0.5)
                
        except KeyboardInterrupt:
            logger.info("\n👋 Shutting down ARC...")
            await self.stop()
    
    async def stop(self):
        """Stop the voice loop."""
        self.running = False
        
        if self.wake_detector:
            self.wake_detector.cleanup()
        
        logger.info("Voice loop stopped")
    
    def pause(self):
        """Pause listening."""
        self.paused = True
        logger.info("Voice loop paused")
    
    def resume(self):
        """Resume listening."""
        self.paused = False
        logger.info("Voice loop resumed")
    
    def interrupt(self):
        """Interrupt current operation."""
        self.in_conversation = False
        logger.info("Operation interrupted")


async def start_voice_loop(agent_callback: Callable):
    """
    Start the voice interaction loop.
    
    Args:
        agent_callback: Async function to process commands
    """
    loop = VoiceLoop(agent_callback)
    await loop.start()
