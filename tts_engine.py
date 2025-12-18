"""
sal-voice Text-to-Speech Engine
Supports Edge TTS, OpenAI TTS, and local TTS
"""
import io
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, AsyncGenerator
from loguru import logger

from config import settings


class TTSEngine:
    """Text-to-Speech engine with multiple backends"""
    
    def __init__(self):
        self.provider = settings.tts_provider
        self._initialized = False
        
    async def initialize(self):
        """Initialize TTS engine"""
        if self._initialized:
            return
            
        logger.info(f"Initializing TTS engine with provider: {self.provider}")
        self._initialized = True
        
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None
    ) -> bytes:
        """
        Synthesize text to speech
        
        Args:
            text: Text to synthesize
            voice: Voice identifier
            rate: Speech rate (e.g., "+10%", "-20%")
            pitch: Voice pitch (e.g., "+5Hz", "-10Hz")
            
        Returns:
            Audio data as bytes (MP3 format)
        """
        await self.initialize()
        
        voice = voice or settings.tts_voice
        rate = rate or settings.tts_rate
        pitch = pitch or settings.tts_pitch
        
        if self.provider == "edge":
            return await self._synthesize_edge(text, voice, rate, pitch)
        elif self.provider == "openai":
            return await self._synthesize_openai(text, voice)
        else:
            return await self._synthesize_local(text, voice)
            
    async def _synthesize_edge(
        self,
        text: str,
        voice: str,
        rate: str,
        pitch: str
    ) -> bytes:
        """Synthesize using Edge TTS (free, high quality)"""
        import edge_tts
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch
        )
        
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
                
        return audio_data.getvalue()
        
    async def _synthesize_openai(
        self,
        text: str,
        voice: str
    ) -> bytes:
        """Synthesize using OpenAI TTS API"""
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        response = await client.audio.speech.create(
            model=settings.openai_tts_model,
            voice=settings.openai_tts_voice,
            input=text
        )
        
        return response.content
        
    async def _synthesize_local(
        self,
        text: str,
        voice: str
    ) -> bytes:
        """Synthesize using local TTS (pyttsx3 or similar)"""
        # Fallback to edge TTS for now
        logger.warning("Local TTS not implemented, falling back to Edge TTS")
        return await self._synthesize_edge(text, voice, "+0%", "+0Hz")
        
    async def stream_synthesis(
        self,
        text: str,
        voice: Optional[str] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream audio synthesis for real-time playback
        
        Yields:
            Audio chunks as bytes
        """
        await self.initialize()
        
        voice = voice or settings.tts_voice
        
        if self.provider == "edge":
            import edge_tts
            communicate = edge_tts.Communicate(text=text, voice=voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        else:
            # Non-streaming fallback
            audio = await self.synthesize(text, voice)
            yield audio
            
    async def list_voices(self, language: Optional[str] = None) -> list:
        """List available voices"""
        if self.provider == "edge":
            import edge_tts
            voices = await edge_tts.list_voices()
            if language:
                voices = [v for v in voices if v["Locale"].startswith(language)]
            return voices
        elif self.provider == "openai":
            return [
                {"name": "alloy", "gender": "neutral"},
                {"name": "echo", "gender": "male"},
                {"name": "fable", "gender": "neutral"},
                {"name": "onyx", "gender": "male"},
                {"name": "nova", "gender": "female"},
                {"name": "shimmer", "gender": "female"}
            ]
        return []


# Singleton instance
tts_engine = TTSEngine()
