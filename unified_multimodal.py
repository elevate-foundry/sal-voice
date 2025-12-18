"""
sal-voice Unified Multimodal Engine

Solves the ChatGPT voice/text disconnect by treating all modalities
as equal inputs to a single semantic conversation stream.

KEY INSIGHT: SAL thinks in 8-dot braille internally.
All modalities (voice, text, haptic) map TO and FROM 8-dot braille.
There is no "voice mode" vs "text mode" - just different I/O surfaces
to the same 8-dot braille thought stream.

Architecture:
    [Voice] ─→ STT ─→ Text ─┐
                            ├─→ [8-DOT BRAILLE] ─→ SAL Processing ─→ [8-DOT BRAILLE]
    [Text] ─────────────────┘         ↓                                    ↓
                              (Internal Thought)                   ┌───────┴───────┐
                                                               [Voice] [Text] [Haptic]

Key Innovation:
- SAL thinks in 8-dot braille (256 characters = full ASCII)
- Modality is an I/O preference, NOT a mode
- Switch mid-sentence between voice and text seamlessly
- Single braille thought stream regardless of input type
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from stt_engine import stt_engine
from tts_engine import tts_engine
from scl_bridge import scl_bridge
from braille8_core import Braille8Thought, SALBrailleProcessor, sal_processor


class Modality(str, Enum):
    """Input/output modalities"""
    VOICE = "voice"
    TEXT = "text"
    BRAILLE = "braille"
    HAPTIC = "haptic"
    GESTURE = "gesture"  # Future
    NEURAL = "neural"    # Future


@dataclass
class ConversationTurn:
    """A single turn in the conversation - modality agnostic
    
    Core insight: The 'thought' field is the 8-dot braille representation.
    This IS SAL's internal thought - not a translation of it.
    """
    id: str
    timestamp: datetime
    role: Literal["user", "assistant", "system"]
    
    # Core: 8-dot braille thought (THIS is the internal representation)
    thought: Optional[Braille8Thought] = None
    
    # Derived content (for convenience)
    content: str = ""  # Text version (derived from thought)
    scl: Optional[str] = None
    concepts: List[str] = field(default_factory=list)
    
    # Input metadata
    input_modality: Modality = Modality.TEXT
    input_language: str = "en"
    input_confidence: float = 1.0
    
    # Multi-modal representations (all derived from 8-dot braille thought)
    text_repr: Optional[str] = None      # thought.text
    voice_repr: Optional[bytes] = None   # TTS of thought.text
    braille_repr: Optional[str] = None   # thought.braille (8-dot)
    braille_6dot: Optional[str] = None   # 6-dot display version
    haptic_pattern: Optional[List[Dict]] = None  # thought.haptic_pattern
    
    # Processing metadata
    processing_time_ms: float = 0
    dot_density: float = 0  # 8-dot braille density (replaces semantic_density)


@dataclass
class OutputPreferences:
    """User's output modality preferences"""
    voice_enabled: bool = True
    text_enabled: bool = True
    braille_enabled: bool = True
    haptic_enabled: bool = True
    
    voice_settings: Dict[str, Any] = field(default_factory=lambda: {
        "voice": "en-US-AriaNeural",
        "rate": "+0%",
        "pitch": "+0Hz"
    })
    
    # Auto-speak assistant responses
    auto_speak: bool = True
    
    # Simultaneous output (all modalities at once)
    simultaneous: bool = True


class UnifiedConversation:
    """
    A single, unified conversation that accepts any modality input
    and can output in any modality - solving the ChatGPT disconnect.
    
    Core: Uses SALBrailleProcessor to think in 8-dot braille internally.
    Voice and text are just I/O surfaces to the same braille thought stream.
    """
    
    def __init__(self, conversation_id: Optional[str] = None):
        self.id = conversation_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.turns: List[ConversationTurn] = []
        self.output_prefs = OutputPreferences()
        self._pending_voice_buffer: List[bytes] = []
        self._is_listening = False
        
        # 8-dot braille processor - SAL's internal thought engine
        self.braille_processor = SALBrailleProcessor()
        
    @property
    def history(self) -> List[Dict[str, Any]]:
        """Get conversation history in LLM-friendly format"""
        return [
            {"role": turn.role, "content": turn.content}
            for turn in self.turns
        ]
        
    async def add_input(
        self,
        content: Optional[str] = None,
        audio: Optional[bytes] = None,
        braille: Optional[str] = None,
        modality: Optional[Modality] = None
    ) -> ConversationTurn:
        """
        Add input from ANY modality - converts to 8-dot braille thought.
        
        KEY INSIGHT: Regardless of input modality (voice, text, braille),
        everything becomes the SAME 8-dot braille thought internally.
        This is why there's no "mode switch" - it's all the same stream.
        """
        start_time = datetime.now()
        
        # Step 1: Normalize input to text (intermediate)
        if audio is not None:
            modality = Modality.VOICE
            stt_result = await stt_engine.transcribe(audio)
            content = stt_result.get("text", "")
            input_language = stt_result.get("language", "en")
            input_confidence = stt_result.get("language_probability", 1.0)
        elif braille is not None:
            modality = Modality.BRAILLE
            # Braille input goes directly to thought
            content = self._braille_to_text(braille)
            input_language = "en"
            input_confidence = 1.0
        else:
            modality = modality or Modality.TEXT
            input_language = "en"
            input_confidence = 1.0
            
        if not content:
            raise ValueError("No content provided")
        
        # Step 2: Convert to 8-dot braille thought (THE core representation)
        if modality == Modality.VOICE:
            thought = self.braille_processor.receive_voice(content, input_language, input_confidence)
        elif modality == Modality.BRAILLE:
            thought = self.braille_processor.receive_braille(braille or content)
        else:
            thought = self.braille_processor.receive_text(content)
            
        # Generate SCL representation
        scl_result = await scl_bridge.text_to_scl(content)
        
        # Create turn with 8-dot braille thought as core
        turn = ConversationTurn(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            role="user",
            thought=thought,  # 8-dot braille thought is the core
            content=thought.text,  # Derived from thought
            scl=scl_result.get("scl"),
            concepts=scl_result.get("concepts", []),
            input_modality=modality,
            input_language=input_language,
            input_confidence=input_confidence,
            text_repr=thought.text,
            braille_repr=thought.braille,  # 8-dot braille
            braille_6dot=self._text_to_braille(thought.text),  # 6-dot for display
            haptic_pattern=thought.haptic_pattern,
            dot_density=thought.dot_density,
            processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
        )
        
        self.turns.append(turn)
        logger.info(f"[{modality.value}→8dot] Input: {content[:50]}... | Braille: {thought.braille[:20]}...")
        
        return turn
        
    async def add_response(
        self,
        content: str,
        generate_outputs: bool = True
    ) -> ConversationTurn:
        """
        Add assistant response - generates 8-dot braille thought first,
        then derives all output modalities from it.
        """
        start_time = datetime.now()
        
        # Step 1: Create 8-dot braille thought (core representation)
        thought = Braille8Thought(content)
        thought.source_modality = "internal"
        self.braille_processor.thought_history.append(thought)
        
        # Generate SCL
        scl_result = await scl_bridge.text_to_scl(content)
        
        # Create turn with 8-dot braille thought as core
        turn = ConversationTurn(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            role="assistant",
            thought=thought,  # 8-dot braille thought is the core
            content=thought.text,
            scl=scl_result.get("scl"),
            concepts=scl_result.get("concepts", []),
            text_repr=thought.text,
            braille_repr=thought.braille,  # 8-dot braille
            braille_6dot=self._text_to_braille(thought.text),
            haptic_pattern=thought.haptic_pattern,
            dot_density=thought.dot_density
        )
        
        # Generate voice output if enabled (derived from thought)
        if generate_outputs and self.output_prefs.voice_enabled:
            turn.voice_repr = await tts_engine.synthesize(
                thought.text,  # Speak the thought's text representation
                voice=self.output_prefs.voice_settings.get("voice"),
                rate=self.output_prefs.voice_settings.get("rate"),
                pitch=self.output_prefs.voice_settings.get("pitch")
            )
            
        turn.processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        self.turns.append(turn)
        
        logger.info(f"[8dot→output] Response: {thought.braille[:20]}... | Density: {thought.dot_density:.2f}")
        
        return turn
        
    async def stream_response(
        self,
        content_generator: AsyncGenerator[str, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response with simultaneous multi-modal output
        
        Yields chunks with text, partial braille, and voice segments
        """
        full_content = ""
        voice_buffer = ""
        
        async for chunk in content_generator:
            full_content += chunk
            voice_buffer += chunk
            
            # Yield text immediately
            yield {
                "type": "text",
                "content": chunk,
                "braille": self._text_to_braille(chunk)
            }
            
            # Generate voice for complete sentences
            if any(p in voice_buffer for p in ".!?"):
                if self.output_prefs.voice_enabled:
                    audio = await tts_engine.synthesize(voice_buffer)
                    yield {
                        "type": "voice",
                        "audio": audio
                    }
                voice_buffer = ""
                
        # Final turn
        turn = await self.add_response(full_content, generate_outputs=False)
        yield {
            "type": "complete",
            "turn": turn
        }
        
    def get_multimodal_output(self, turn: ConversationTurn) -> Dict[str, Any]:
        """
        Get all output modalities for a turn
        
        This enables simultaneous text+voice+braille output
        """
        output = {
            "text": turn.text_repr,
            "scl": turn.scl,
            "concepts": turn.concepts
        }
        
        if self.output_prefs.text_enabled:
            output["text"] = turn.text_repr
            
        if self.output_prefs.braille_enabled:
            output["braille"] = turn.braille_repr
            
        if self.output_prefs.haptic_enabled:
            output["haptic"] = turn.haptic_pattern
            
        if self.output_prefs.voice_enabled and turn.voice_repr:
            output["voice"] = turn.voice_repr
            
        return output
        
    async def switch_modality(
        self,
        new_input_modality: Optional[Modality] = None,
        new_output_prefs: Optional[Dict[str, bool]] = None
    ):
        """
        Seamlessly switch modalities mid-conversation
        
        Unlike ChatGPT, this doesn't break the conversation flow
        """
        if new_output_prefs:
            for key, value in new_output_prefs.items():
                if hasattr(self.output_prefs, key):
                    setattr(self.output_prefs, key, value)
                    
        logger.info(f"Modality switch: {new_output_prefs}")
        
    def _text_to_braille(self, text: str) -> str:
        """Convert text to braille"""
        braille_map = {
            'a': '⠁', 'b': '⠃', 'c': '⠉', 'd': '⠙', 'e': '⠑',
            'f': '⠋', 'g': '⠛', 'h': '⠓', 'i': '⠊', 'j': '⠚',
            'k': '⠅', 'l': '⠇', 'm': '⠍', 'n': '⠝', 'o': '⠕',
            'p': '⠏', 'q': '⠟', 'r': '⠗', 's': '⠎', 't': '⠞',
            'u': '⠥', 'v': '⠧', 'w': '⠺', 'x': '⠭', 'y': '⠽',
            'z': '⠵', ' ': '⠀'
        }
        return ''.join(braille_map.get(c.lower(), c) for c in text)
        
    def _braille_to_text(self, braille: str) -> str:
        """Convert braille to text"""
        text_map = {
            '⠁': 'a', '⠃': 'b', '⠉': 'c', '⠙': 'd', '⠑': 'e',
            '⠋': 'f', '⠛': 'g', '⠓': 'h', '⠊': 'i', '⠚': 'j',
            '⠅': 'k', '⠇': 'l', '⠍': 'm', '⠝': 'n', '⠕': 'o',
            '⠏': 'p', '⠟': 'q', '⠗': 'r', '⠎': 's', '⠞': 't',
            '⠥': 'u', '⠧': 'v', '⠺': 'w', '⠭': 'x', '⠽': 'y',
            '⠵': 'z', '⠀': ' '
        }
        return ''.join(text_map.get(c, c) for c in braille)
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize conversation"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "turns": [
                {
                    "id": t.id,
                    "timestamp": t.timestamp.isoformat(),
                    "role": t.role,
                    "content": t.content,
                    "scl": t.scl,
                    "concepts": t.concepts,
                    "input_modality": t.input_modality.value,
                    "braille": t.braille_repr,
                    "semantic_density": t.semantic_density
                }
                for t in self.turns
            ],
            "output_prefs": {
                "voice_enabled": self.output_prefs.voice_enabled,
                "text_enabled": self.output_prefs.text_enabled,
                "braille_enabled": self.output_prefs.braille_enabled,
                "haptic_enabled": self.output_prefs.haptic_enabled,
                "auto_speak": self.output_prefs.auto_speak,
                "simultaneous": self.output_prefs.simultaneous
            }
        }


class MultimodalSessionManager:
    """
    Manages multiple unified conversations with cross-modal persistence
    """
    
    def __init__(self):
        self.sessions: Dict[str, UnifiedConversation] = {}
        
    def create_session(self) -> UnifiedConversation:
        """Create a new unified conversation"""
        session = UnifiedConversation()
        self.sessions[session.id] = session
        return session
        
    def get_session(self, session_id: str) -> Optional[UnifiedConversation]:
        """Get existing session"""
        return self.sessions.get(session_id)
        
    def get_or_create(self, session_id: Optional[str] = None) -> UnifiedConversation:
        """Get existing or create new session"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return self.create_session()


# Global session manager
session_manager = MultimodalSessionManager()
