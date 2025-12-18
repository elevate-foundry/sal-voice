"""
sal-voice Speech-to-Text Engine
Supports Whisper (local) and OpenAI Whisper API
"""
import io
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
import numpy as np

from config import settings


class STTEngine:
    """Speech-to-Text engine using Whisper"""
    
    def __init__(self):
        self.model = None
        self.model_name = settings.whisper_model
        self._initialized = False
        
    async def initialize(self):
        """Lazy-load Whisper model"""
        if self._initialized:
            return
            
        logger.info(f"Loading Whisper model: {self.model_name}")
        
        try:
            # Try faster-whisper first (more efficient)
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_name,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type
            )
            self._use_faster = True
            logger.info("Using faster-whisper backend")
        except ImportError:
            # Fallback to openai-whisper
            import whisper
            self.model = whisper.load_model(self.model_name)
            self._use_faster = False
            logger.info("Using openai-whisper backend")
            
        self._initialized = True
        logger.info("STT engine initialized")
        
    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text
        
        Args:
            audio_data: Raw audio bytes (WAV format)
            language: Optional language code (auto-detect if None)
            task: "transcribe" or "translate" (to English)
            
        Returns:
            Dict with text, language, segments, confidence
        """
        await self.initialize()
        
        # Save audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name
            
        try:
            if self._use_faster:
                result = await self._transcribe_faster(temp_path, language, task)
            else:
                result = await self._transcribe_whisper(temp_path, language, task)
                
            # Add braille representation
            if settings.braille_enabled:
                result["braille"] = self._text_to_braille(result["text"])
                
            return result
            
        finally:
            Path(temp_path).unlink(missing_ok=True)
            
    async def _transcribe_faster(
        self,
        audio_path: str,
        language: Optional[str],
        task: str
    ) -> Dict[str, Any]:
        """Transcribe using faster-whisper"""
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            task=task,
            beam_size=5,
            vad_filter=True
        )
        
        segments_list = []
        full_text = []
        
        for segment in segments:
            segments_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": segment.avg_logprob
            })
            full_text.append(segment.text.strip())
            
        return {
            "text": " ".join(full_text),
            "language": info.language,
            "language_probability": info.language_probability,
            "segments": segments_list,
            "duration": info.duration
        }
        
    async def _transcribe_whisper(
        self,
        audio_path: str,
        language: Optional[str],
        task: str
    ) -> Dict[str, Any]:
        """Transcribe using openai-whisper"""
        import whisper
        
        result = self.model.transcribe(
            audio_path,
            language=language,
            task=task
        )
        
        segments_list = []
        for segment in result.get("segments", []):
            segments_list.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip(),
                "confidence": segment.get("avg_logprob", 0)
            })
            
        return {
            "text": result["text"].strip(),
            "language": result.get("language", "en"),
            "language_probability": 1.0,
            "segments": segments_list,
            "duration": segments_list[-1]["end"] if segments_list else 0
        }
        
    def _text_to_braille(self, text: str) -> str:
        """Convert text to Grade 1 Braille"""
        braille_map = {
            'a': '⠁', 'b': '⠃', 'c': '⠉', 'd': '⠙', 'e': '⠑',
            'f': '⠋', 'g': '⠛', 'h': '⠓', 'i': '⠊', 'j': '⠚',
            'k': '⠅', 'l': '⠇', 'm': '⠍', 'n': '⠝', 'o': '⠕',
            'p': '⠏', 'q': '⠟', 'r': '⠗', 's': '⠎', 't': '⠞',
            'u': '⠥', 'v': '⠧', 'w': '⠺', 'x': '⠭', 'y': '⠽',
            'z': '⠵', ' ': '⠀', '.': '⠲', ',': '⠂', '!': '⠖',
            '?': '⠦', "'": '⠄', '-': '⠤', ':': '⠒', ';': '⠆',
            '0': '⠴', '1': '⠂', '2': '⠆', '3': '⠒', '4': '⠲',
            '5': '⠢', '6': '⠖', '7': '⠶', '8': '⠦', '9': '⠔'
        }
        return ''.join(braille_map.get(c.lower(), c) for c in text)


# Singleton instance
stt_engine = STTEngine()
