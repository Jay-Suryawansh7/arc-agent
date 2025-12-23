"""
Wake word detection module using Picovoice Porcupine.
"""
import logging
import struct
from typing import Optional, Callable
from threading import Thread

try:
    import pvporcupine
    import pyaudio
except ImportError:
    pvporcupine = None
    pyaudio = None

from arc.config import get_config

logger = logging.getLogger(__name__)

class WakeWordDetector:
    def __init__(self):
        self.config = get_config()
        self.porcupine = None
        self.audio_stream = None
        self.pyaudio_instance = None
        self.listening = False
        self.callback: Optional[Callable] = None
        self.listen_thread = None
        
    def initialize(self, access_key: Optional[str] = None, sensitivity: float = 0.5):
        """Initialize Porcupine with wake word."""
        if pvporcupine is None:
            raise ImportError("pvporcupine not installed. Run: pip install pvporcupine")
            
        if access_key is None:
            access_key_secret = self.config.voice.porcupine_access_key
            if access_key_secret:
                access_key = access_key_secret.get_secret_value()
            else:
                raise ValueError("Porcupine access key not configured")
                
        try:
            logger.info("Initializing Porcupine wake word detector...")
            
            # Using built-in keywords or custom model
            # For custom "ARC" wake word, you'd need to train it via Picovoice Console
            # Here we'll use a built-in keyword as fallback
            keywords = ["jarvis"]  # Built-in keyword, replace with custom "ARC" model
            
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=keywords,
                sensitivities=[sensitivity]
            )
            
            logger.info(f"Porcupine initialized with keywords: {keywords}")
            
        except Exception as e:
            logger.error(f"Porcupine initialization failed: {e}")
            raise

    def on_wake_detected(self, callback: Callable):
        """Register callback to execute when wake word is detected."""
        self.callback = callback

    def start_listening(self):
        """Start listening for wake word in background thread."""
        if self.listening:
            logger.warning("Already listening")
            return
            
        if not self.porcupine:
            self.initialize()
            
        self.listening = True
        self.listen_thread = Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        logger.info("Wake word detection started")

    def _listen_loop(self):
        """Main listening loop (runs in background thread)."""
        if pyaudio is None:
            logger.error("pyaudio not installed")
            return
            
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            self.audio_stream = self.pyaudio_instance.open(
                rate=self.porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            
            logger.info("Listening for wake word...")
            
            while self.listening:
                pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                
                keyword_index = self.porcupine.process(pcm)
                
                if keyword_index >= 0:
                    logger.info("Wake word detected!")
                    if self.callback:
                        self.callback()
                        
        except Exception as e:
            logger.error(f"Listen loop error: {e}")
        finally:
            if self.audio_stream:
                self.audio_stream.close()
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()

    def stop_listening(self):
        """Stop listening for wake word."""
        self.listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2.0)
        logger.info("Wake word detection stopped")

    def cleanup(self):
        """Clean up resources."""
        self.stop_listening()
        if self.porcupine:
            self.porcupine.delete()

    def adjust_sensitivity(self, level: float):
        """Adjust detection sensitivity (requires reinitialization)."""
        logger.info(f"Sensitivity adjustment requires reinitialization: {level}")
        # Would need to recreate porcupine instance
        pass

# Singleton
_wake_detector: Optional[WakeWordDetector] = None

def get_wake_detector() -> WakeWordDetector:
    global _wake_detector
    if _wake_detector is None:
        _wake_detector = WakeWordDetector()
    return _wake_detector
