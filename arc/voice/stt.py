"""
Speech-to-Text module using OpenAI Whisper.
"""
import logging
import io
import wave
import numpy as np
from typing import Optional
from pathlib import Path

try:
    import whisper
    import pyaudio
except ImportError:
    whisper = None
    pyaudio = None

from arc.config import get_config

logger = logging.getLogger(__name__)

class WhisperSTT:
    def __init__(self):
        self.config = get_config()
        self.model = None
        self.model_size = self.config.voice.stt_model_size
        self.audio_format = None
        self.pyaudio_instance = None
        
    def load_model(self, model_size: Optional[str] = None):
        """Load Whisper model with specified size."""
        if whisper is None:
            raise ImportError("openai-whisper not installed. Run: pip install openai-whisper")
            
        if model_size:
            self.model_size = model_size
            
        logger.info(f"Loading Whisper model: {self.model_size}")
        try:
            self.model = whisper.load_model(self.model_size)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe_file(self, file_path: str, language: str = "en") -> str:
        """Transcribe audio from file."""
        if not self.model:
            self.load_model()
            
        try:
            logger.info(f"Transcribing file: {file_path}")
            result = self.model.transcribe(file_path, language=language)
            return result["text"].strip()
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "en") -> str:
        """Transcribe audio from numpy array."""
        if not self.model:
            self.load_model()
            
        try:
            # Whisper expects float32 audio normalized to [-1, 1]
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32) / 32768.0
                
            result = self.model.transcribe(audio_data, language=language)
            return result["text"].strip()
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def record_audio(self, duration: float = 5.0, sample_rate: int = 16000) -> np.ndarray:
        """Record audio from microphone."""
        if pyaudio is None:
            raise ImportError("pyaudio not installed")
            
        try:
            p = pyaudio.PyAudio()
            
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                input=True,
                frames_per_buffer=1024
            )
            
            logger.info(f"Recording for {duration} seconds...")
            frames = []
            
            for _ in range(0, int(sample_rate / 1024 * duration)):
                data = stream.read(1024)
                frames.append(data)
                
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Convert to numpy array
            audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
            return audio_data
            
        except Exception as e:
            logger.error(f"Audio recording failed: {e}")
            raise

    def start_streaming(self):
        """Start continuous transcription mode (placeholder for future implementation)."""
        logger.warning("Streaming transcription not yet implemented")
        # Real implementation would use a callback-based approach with VAD
        pass

    def stop_streaming(self):
        """Stop continuous transcription."""
        pass

# Singleton
_whisper_stt: Optional[WhisperSTT] = None

def get_whisper_stt() -> WhisperSTT:
    global _whisper_stt
    if _whisper_stt is None:
        _whisper_stt = WhisperSTT()
    return _whisper_stt
