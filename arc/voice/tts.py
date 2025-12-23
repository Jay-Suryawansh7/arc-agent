"""
Text-to-Speech module using Piper TTS.
"""
import logging
import subprocess
import wave
import io
from typing import Optional
from pathlib import Path
from queue import Queue
from threading import Thread

try:
    import pyaudio
except ImportError:
    pyaudio = None

from arc.config import get_config

logger = logging.getLogger(__name__)

class PiperTTS:
    def __init__(self):
        self.config = get_config()
        self.voice_name = self.config.voice.tts_voice
        self.speaking = False
        self.audio_queue = Queue()
        self.playback_thread = None
        
    def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to audio using Piper TTS.
        Returns WAV audio bytes.
        """
        try:
            # Piper TTS is typically called via command line
            # Assuming piper binary is in PATH
            # piper --model <model> --output_file -
            
            # For this implementation, we'll use a simplified approach
            # In production, you'd need to:
            # 1. Download/install piper models
            # 2. Configure model paths
            # 3. Handle voice selection
            
            logger.info(f"Synthesizing: {text[:50]}...")
            
            # Placeholder: In real implementation, call piper CLI or use piper_tts library
            # Example command: echo "text" | piper --model en_US-lessac-medium --output_file output.wav
            
            cmd = [
                "piper",
                "--model", self.voice_name,
                "--output-raw"
            ]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            audio_data, error = process.communicate(input=text.encode())
            
            if process.returncode != 0:
                logger.error(f"Piper TTS failed: {error.decode()}")
                raise RuntimeError(f"TTS synthesis failed: {error.decode()}")
                
            return audio_data
            
        except FileNotFoundError:
            logger.error("Piper TTS not found. Install from: https://github.com/rhasspy/piper")
            raise
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise

    def play_audio(self, audio_data: bytes, sample_rate: int = 22050):
        """Play audio bytes using pyaudio."""
        if pyaudio is None:
            logger.error("pyaudio not installed")
            return
            
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                output=True
            )
            
            stream.write(audio_data)
            stream.stop_stream()
            stream.close()
            p.terminate()
            
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")

    def speak(self, text: str):
        """Synthesize and play text immediately."""
        try:
            audio_data = self.synthesize(text)
            self.play_audio(audio_data)
        except Exception as e:
            logger.error(f"Speak failed: {e}")

    def save_audio(self, text: str, output_path: str):
        """Synthesize text and save to file."""
        try:
            audio_data = self.synthesize(text)
            with open(output_path, 'wb') as f:
                f.write(audio_data)
            logger.info(f"Audio saved to: {output_path}")
        except Exception as e:
            logger.error(f"Save audio failed: {e}")

    def stop_speaking(self):
        """Stop current speech (placeholder)."""
        self.speaking = False
        # In a real implementation, this would interrupt the audio stream

# Singleton
_piper_tts: Optional[PiperTTS] = None

def get_piper_tts() -> PiperTTS:
    global _piper_tts
    if _piper_tts is None:
        _piper_tts = PiperTTS()
    return _piper_tts
