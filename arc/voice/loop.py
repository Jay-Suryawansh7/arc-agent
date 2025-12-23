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
            
        # Ensure TTS model exists
        await self._ensure_model_exists()
        
        logger.info("✅ Voice loop initialized")

    async def _ensure_model_exists(self):
        """Check for TTS model and download if missing."""
        import urllib.request
        from pathlib import Path
        
        model_path = Path(self.config.voice.tts_voice).resolve()
        
        # We need both .onnx and .onnx.json (implicit dependency for Piper)
        json_path = model_path.with_suffix('.onnx.json')
        
        if model_path.exists() and json_path.exists():
            logger.info(f"✅ Voice model found: {model_path.name}")
            return

        logger.info(f"📥 Downloading voice model to {model_path}...")
        
        # Create parent directories
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Default fallback URL for en_US-lessac-medium
        base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium"
        model_url = f"{base_url}/en_US-lessac-medium.onnx"
        json_url = f"{base_url}/en_US-lessac-medium.onnx.json"
        
        try:
            # Download via a thread to strictly avoid blocking the loop, 
            # though usually initialization is synchronous-ish.
            def download():
                logger.info(f"   Downloading .onnx ({model_url})...")
                urllib.request.urlretrieve(model_url, model_path)
                logger.info(f"   Downloading .json ({json_url})...")
                urllib.request.urlretrieve(json_url, json_path)
            
            await asyncio.to_thread(download)
            logger.info("✅ Voice model downloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to download voice model: {e}")
            logger.warning("TTS may fail if model is missing.")
    
    def _play_sound(self, sound_type: str):
        """
        Play confirmation/error sounds.
        Non-blocking and non-fatal.
        """
        try:
            import platform
            system = platform.system()
            
            if system == 'Windows':
                import winsound
                # Simple beeps for Windows
                if sound_type == "wake":
                    winsound.Beep(1000, 200)  # High pitch
                elif sound_type == "error":
                    winsound.Beep(500, 500)   # Low pitch long
            elif system == 'Darwin':
                # macOS sounds
                sound_file = "/System/Library/Sounds/Tink.aiff" if sound_type == "wake" else "/System/Library/Sounds/Basso.aiff"
                subprocess.run(["afplay", sound_file], check=False, capture_output=True)
                
        except Exception as e:
            # Swallow audio errors to keep loop running
            logger.debug(f"Audio feedback failed: {e}")

    def _is_follow_up_allowed(self) -> bool:
        """Check if we're within follow-up timeout."""
        if not self.last_interaction_time:
            return False
        
        elapsed = (datetime.now() - self.last_interaction_time).total_seconds()
        return elapsed < self.conversation_timeout
    
    async def _speak_async(self, text: str, tone: str = "friendly"):
        """
        Speak text via TTS asynchronously.
        Returns the subprocess.Popen object of the player.
        """
        try:
            import platform
            import os
            import tempfile
            
            system = platform.system()
            temp_dir = tempfile.gettempdir()
            
            # Paths
            text_file_path = os.path.join(temp_dir, "arc_speak.txt")
            audio_file_path = os.path.join(temp_dir, "arc_response.wav")
            
            # 1. Write text (used for debugging/logging mainly, Piper input)
            with open(text_file_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            # 2. Run Piper (Generation is still blocking, usually fast for sentences)
            # We assume generation is fast enough. If long generation, we'd chunk it.
            # For now, we generate strictly before playing.
            from pathlib import Path
            model_abs_path = str(Path(self.config.voice.tts_voice).resolve())
            
            piper_cmd = [
                "piper",
                "--model", model_abs_path,
                "--input_file", text_file_path,
                "--output_file", audio_file_path
            ]
            
            # Log tone (Phase UX: Tone signal used for logging/future modulation)
            logger.info(f"🗣️ Speaking ({tone}): {text[:50]}...")
            
            subprocess.run(piper_cmd, check=True, capture_output=True)
            
            # 3. Play Audio Asynchronously
            player_process = None
            
            if system == 'Windows':
                # Use PowerShell to confirm blocking-in-process behavior so we can kill it
                # PlaySync() blocks the PowerShell process, which is what we want for Popen
                ps_cmd = [
                    "powershell", 
                    "-c", 
                    f"(New-Object Media.SoundPlayer '{audio_file_path}').PlaySync()"
                ]
                player_process = subprocess.Popen(ps_cmd)
                
            elif system == 'Darwin':
                player_process = subprocess.Popen(["afplay", audio_file_path])
                
            else:
                player_process = subprocess.Popen(["aplay", audio_file_path])
                
            return player_process
                
        except Exception as e:
            logger.error(f"TTS Async failed: {e}")
            return None

    async def _monitor_playback(self, player_process, check_interval=0.1):
        """
        Monitor playback for wake word interruption.
        Blocks until playback finishes or wake word is detected.
        """
        if not player_process:
            return
            
        if not self.wake_detector:
             # Just wait for process to finish if no means to interrupt
            player_process.wait()
            return

        try:
            import pyaudio
            import struct
            
            pa = pyaudio.PyAudio()
            # Assuming Porcupine default sample rate (16000) and frame length (512 usually)
            # We need to access these from wake detector if possible, or hardcode standard
            # Porcupine is usually 16kHz, 512 frame size.
            
            # We need to open a stream specifically for this monitoring
            stream = pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=512
            )
            
            logger.info("👂 Monitoring for interruption...")
            
            while player_process.poll() is None:
                # Read audio
                pcm = stream.read(512, exception_on_overflow=False)
                
                # Unpack for Porcupine (needs list/tuple of shorts usually, or bytes depending on wrapper)
                # wake_detector.process usually takes a list of integers
                pcm_unpacked = struct.unpack_from("h" * 512, pcm)
                
                keyword_index = self.wake_detector.process(pcm_unpacked)
                
                if keyword_index >= 0:
                    logger.info("🛑 Interruption Detected!")
                    
                    # Stop Audio
                    player_process.terminate()
                    
                    # Play Ding
                    self._play_sound("wake")
                    
                    self.interrupt() # Set flag
                    break
                    
                # Small yield not strictly needed as read is blocking, but good practice
                await asyncio.sleep(0.01)
                
            stream.close()
            pa.terminate()
            
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            if player_process:
                player_process.wait() # Fallback

    async def _speak(self, text: str):
        # Deprecated by _speak_async but kept for interface compatibility if needed
        proc = await self._speak_async(text)
        if proc:
            proc.wait()

    async def process_command(self, skip_wake_word: bool = False):
        """
        Process one voice command.
        """
        try:
            # Wait for wake word (unless skipping)
            if not skip_wake_word and self.wake_detector:
                logger.debug("Waiting for wake word...")
                # In a real loop, we might block here or use a specific wait method
                # For now, assuming external trigger or continuous loop structure
                # Check how start() calls this. It calls process_command repeatedly.
                # We need a blocking wait for wake word here if we want true wake word mode.
                # But typically `process_command` assumes it's time to listen.
                # Ref: Previous implementation just passed.
                pass
            
            # Play confirmation
            self._play_sound("wake")
            logger.info("🎤 Listening...")
            
            # Record speech
            try:
                # Flush basic instructions
                audio = self.stt.record_audio(duration=5.0)
            except Exception as e:
                logger.error(f"Recording failed: {e}")
                proc = await self._speak_async("Sorry, I couldn't hear you", "apologetic")
                await self._monitor_playback(proc)
                return
            
            # Transcribe
            logger.info("🔄 Processing...")
            try:
                user_input = self.stt.transcribe_audio(audio)
            except Exception as e:
                logger.error(f"Transcription failed: {e}")
                proc = await self._speak_async("Sorry, I didn't catch that", "apologetic")
                await self._monitor_playback(proc)
                return
            
            if not user_input.strip():
                return
            
            logger.info(f"You: {user_input}")
            
            # Check for interrupt commands (Text-based pre-processing)
            if any(word in user_input.lower() for word in ['stop', 'cancel', 'nevermind']):
                proc = await self._speak_async("Okay", "neutral")
                await self._monitor_playback(proc)
                self.in_conversation = False
                return
            
            # Send to agent (Updated: expects dict or tuple)
            logger.info("🧠 Processing request...")
            try:
                # Result is now dict {"text": str, "tone": str}
                result = await self.agent_callback(user_input)
                
                # Handle legacy string return if something missed updates
                if isinstance(result, str):
                    response_text = result
                    tone = "friendly"
                else:
                    response_text = result.get("text", "")
                    tone = result.get("tone", "friendly")
                    
            except Exception as e:
                logger.error(f"Agent error: {e}")
                response_text = "I encountered an error."
                tone = "apologetic"
            
            # Speak response (Async + Monitor)
            logger.info(f"ARC ({tone}): {response_text}")
            
            player_proc = await self._speak_async(response_text, tone)
            
            # Critical: Monitor for interruption while speaking
            await self._monitor_playback(player_proc)
            
            # Update state
            self.last_interaction_time = datetime.now()
            self.in_conversation = True
            
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            self._play_sound("error")
    
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
