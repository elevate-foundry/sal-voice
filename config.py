"""
sal-voice configuration
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8100
    debug: bool = True
    
    # Whisper STT
    whisper_model: Literal["tiny", "base", "small", "medium", "large"] = "base"
    whisper_device: str = "cpu"  # cpu, cuda, mps
    whisper_compute_type: str = "int8"  # float16, int8
    
    # TTS Provider
    tts_provider: Literal["edge", "openai", "local"] = "edge"
    tts_voice: str = "en-US-AriaNeural"  # Edge TTS voice
    tts_rate: str = "+0%"
    tts_pitch: str = "+0Hz"
    
    # OpenAI (optional)
    openai_api_key: str = ""
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "alloy"
    
    # SAL Integration
    sal_api_url: str = "http://localhost:8000"
    sal_auth_url: str = "http://localhost:8200"
    
    # Audio
    sample_rate: int = 16000
    audio_format: str = "wav"
    max_audio_duration: int = 300  # seconds
    
    # Paths
    cache_dir: Path = Path("cache")
    temp_dir: Path = Path("temp")
    
    # Braille output
    braille_enabled: bool = True
    haptic_feedback: bool = True
    
    class Config:
        env_file = ".env"
        env_prefix = "SAL_VOICE_"

settings = Settings()

# Ensure directories exist
settings.cache_dir.mkdir(exist_ok=True)
settings.temp_dir.mkdir(exist_ok=True)
