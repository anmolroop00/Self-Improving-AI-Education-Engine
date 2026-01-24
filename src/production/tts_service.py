"""Text-to-Speech Service.

Provides abstraction over multiple TTS providers:
- Google Cloud TTS (for testing)
- Eleven Labs (for production)

Supports switching based on configuration.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..config import settings, TTSProvider

logger = logging.getLogger(__name__)


class TTSService(ABC):
    """Abstract base class for TTS services."""
    
    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None,
    ) -> Path:
        """Synthesize speech from text.
        
        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file
            voice_id: Optional voice ID (provider-specific)
            
        Returns:
            Path to the generated audio file
        """
        pass
    
    @abstractmethod
    def get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of an audio file in seconds.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Duration in seconds
        """
        pass
    
    @classmethod
    def create(cls) -> "TTSService":
        """Factory method to create appropriate TTS service based on config.
        
        Returns:
            Configured TTSService instance
        """
        if settings.tts_provider == TTSProvider.ELEVENLABS:
            return ElevenLabsTTS()
        else:
            return GoogleTTS()


class GoogleTTS(TTSService):
    """Google Cloud Text-to-Speech implementation.
    
    Good for testing and development. Supports many languages and voices.
    """
    
    def __init__(self):
        """Initialize Google Cloud TTS client."""
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """Lazy initialization of the client."""
        try:
            from google.cloud import texttospeech
            self._client = texttospeech.TextToSpeechClient()
            logger.info("Google Cloud TTS client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google TTS: {e}")
            raise
    
    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None,
    ) -> Path:
        """Synthesize speech using Google Cloud TTS.
        
        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file
            voice_id: Voice name (e.g., "en-US-Neural2-D")
            
        Returns:
            Path to the generated audio file
        """
        from google.cloud import texttospeech
        
        # Set up the synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Set up the voice
        voice_name = voice_id or "en-US-Neural2-D"
        language_code = voice_name.split("-")[0] + "-" + voice_name.split("-")[1]
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )
        
        # Set up the audio config
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0,
        )
        
        # Perform the synthesis
        logger.info(f"Synthesizing {len(text)} characters with Google TTS...")
        response = self._client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the audio file
        with open(output_path, "wb") as f:
            f.write(response.audio_content)
        
        logger.info(f"Audio saved to {output_path}")
        return output_path
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of an audio file.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Duration in seconds
        """
        try:
            try:
                from moviepy import AudioFileClip
            except ImportError:
                from moviepy.editor import AudioFileClip
            with AudioFileClip(str(audio_path)) as clip:
                return clip.duration
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            # Estimate based on file size (rough: ~16KB per second for MP3)
            return audio_path.stat().st_size / 16000


class ElevenLabsTTS(TTSService):
    """Eleven Labs Text-to-Speech implementation.
    
    Higher quality, more natural-sounding voices for production.
    """
    
    def __init__(self):
        """Initialize Eleven Labs client."""
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize the Eleven Labs client."""
        try:
            from elevenlabs import ElevenLabs
            self._client = ElevenLabs(api_key=settings.elevenlabs_api_key)
            logger.info("Eleven Labs client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Eleven Labs: {e}")
            raise
    
    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice_id: Optional[str] = None,
    ) -> Path:
        """Synthesize speech using Eleven Labs.
        
        Args:
            text: Text to convert to speech
            output_path: Path to save the audio file
            voice_id: Eleven Labs voice ID
            
        Returns:
            Path to the generated audio file
        """
        voice = voice_id or settings.elevenlabs_voice_id
        
        if not voice:
            raise ValueError("No voice ID provided for Eleven Labs")
        
        logger.info(f"Synthesizing {len(text)} characters with Eleven Labs...")
        
        # Generate audio
        audio = self._client.text_to_speech.convert(
            voice_id=voice,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write audio file
        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        
        logger.info(f"Audio saved to {output_path}")
        return output_path
    
    def get_audio_duration(self, audio_path: Path) -> float:
        """Get duration of an audio file.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Duration in seconds
        """
        try:
            try:
                from moviepy import AudioFileClip
            except ImportError:
                from moviepy.editor import AudioFileClip
            with AudioFileClip(str(audio_path)) as clip:
                return clip.duration
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return audio_path.stat().st_size / 16000
