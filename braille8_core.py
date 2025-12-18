"""
sal-voice 8-Dot Braille Core

8-dot braille is SAL's internal representation layer.
All modalities (voice, text, haptic) map TO and FROM 8-dot braille.

This solves the ChatGPT disconnect: there's no "voice mode" vs "text mode" -
there's only 8-dot braille internally, with different I/O surfaces.

8-dot braille: Unicode U+2800-U+28FF (256 characters)
- Dots 1-6: Standard 6-dot braille positions
- Dots 7-8: Extended positions for full ASCII + Unicode

Architecture:
    [Voice] ─→ STT ─→ Text ─┐
                            ├─→ [8-DOT BRAILLE] ─→ SAL Processing ─→ [8-DOT BRAILLE] ─→ Output
    [Text] ─────────────────┘                                                          ↓
                                                                            ┌──────────┴──────────┐
                                                                        [Voice]  [Text]  [Haptic]
"""

from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import IntFlag
import unicodedata


class BrailleDot(IntFlag):
    """8-dot braille dot positions as bit flags"""
    DOT1 = 0x01  # Top-left
    DOT2 = 0x02  # Middle-left
    DOT3 = 0x04  # Bottom-left
    DOT4 = 0x08  # Top-right
    DOT5 = 0x10  # Middle-right
    DOT6 = 0x20  # Bottom-right
    DOT7 = 0x40  # Extended bottom-left
    DOT8 = 0x80  # Extended bottom-right


# 8-dot braille base codepoint
BRAILLE_BASE = 0x2800


@dataclass
class Braille8Cell:
    """A single 8-dot braille cell"""
    dots: int  # Bit pattern (0-255)
    
    @property
    def unicode(self) -> str:
        """Get Unicode character"""
        return chr(BRAILLE_BASE + self.dots)
    
    @property
    def dot_pattern(self) -> List[int]:
        """Get list of active dot numbers (1-8)"""
        return [i + 1 for i in range(8) if self.dots & (1 << i)]
    
    @property
    def is_empty(self) -> bool:
        return self.dots == 0
    
    def __str__(self) -> str:
        return self.unicode
    
    def __repr__(self) -> str:
        return f"Braille8Cell(dots={self.dots}, char='{self.unicode}', pattern={self.dot_pattern})"


class Braille8Encoder:
    """
    Encodes text/ASCII to 8-dot braille.
    
    8-dot braille can represent all 256 ASCII values directly,
    making it a perfect internal representation for SAL.
    """
    
    # ASCII to 8-dot braille mapping (covers full ASCII)
    # Uses North American Computer Braille Code (NABCC) extended
    ASCII_TO_8DOT: Dict[int, int] = {
        # Control characters (0-31) - use dots 7-8 patterns
        0: 0x00,   # NUL - empty cell
        10: 0x00,  # LF - empty cell (line break)
        13: 0x00,  # CR - empty cell
        32: 0x00,  # Space - empty cell
        
        # Letters a-z (standard 6-dot + context)
        ord('a'): 0x01, ord('b'): 0x03, ord('c'): 0x09, ord('d'): 0x19,
        ord('e'): 0x11, ord('f'): 0x0B, ord('g'): 0x1B, ord('h'): 0x13,
        ord('i'): 0x0A, ord('j'): 0x1A, ord('k'): 0x05, ord('l'): 0x07,
        ord('m'): 0x0D, ord('n'): 0x1D, ord('o'): 0x15, ord('p'): 0x0F,
        ord('q'): 0x1F, ord('r'): 0x17, ord('s'): 0x0E, ord('t'): 0x1E,
        ord('u'): 0x25, ord('v'): 0x27, ord('w'): 0x3A, ord('x'): 0x2D,
        ord('y'): 0x3D, ord('z'): 0x35,
        
        # Uppercase - add dot 7 (0x40)
        ord('A'): 0x41, ord('B'): 0x43, ord('C'): 0x49, ord('D'): 0x59,
        ord('E'): 0x51, ord('F'): 0x4B, ord('G'): 0x5B, ord('H'): 0x53,
        ord('I'): 0x4A, ord('J'): 0x5A, ord('K'): 0x45, ord('L'): 0x47,
        ord('M'): 0x4D, ord('N'): 0x5D, ord('O'): 0x55, ord('P'): 0x4F,
        ord('Q'): 0x5F, ord('R'): 0x57, ord('S'): 0x4E, ord('T'): 0x5E,
        ord('U'): 0x65, ord('V'): 0x67, ord('W'): 0x7A, ord('X'): 0x6D,
        ord('Y'): 0x7D, ord('Z'): 0x75,
        
        # Numbers - add dot 8 (0x80) to letters a-j pattern
        ord('0'): 0x9A, ord('1'): 0x81, ord('2'): 0x83, ord('3'): 0x89,
        ord('4'): 0x99, ord('5'): 0x91, ord('6'): 0x8B, ord('7'): 0x9B,
        ord('8'): 0x93, ord('9'): 0x8A,
        
        # Punctuation
        ord('.'): 0x32, ord(','): 0x02, ord(';'): 0x06, ord(':'): 0x12,
        ord('!'): 0x16, ord('?'): 0x26, ord("'"): 0x04, ord('"'): 0x24,
        ord('-'): 0x24, ord('/'): 0x0C, ord('\\'): 0x21,
        ord('('): 0x36, ord(')'): 0x36, ord('['): 0x2E, ord(']'): 0x3E,
        ord('{'): 0x2F, ord('}'): 0x3F,
        ord('@'): 0x08, ord('#'): 0x3C, ord('$'): 0x2B, ord('%'): 0x2C,
        ord('&'): 0x2F, ord('*'): 0x14, ord('+'): 0x2E, ord('='): 0x36,
        ord('<'): 0x23, ord('>'): 0x1C, ord('_'): 0x38, ord('`'): 0x20,
        ord('~'): 0x28, ord('^'): 0x18, ord('|'): 0x33,
    }
    
    # Reverse mapping for decoding
    DOT8_TO_ASCII: Dict[int, int] = {v: k for k, v in ASCII_TO_8DOT.items()}
    
    def __init__(self):
        # Build complete mapping for all ASCII
        self._complete_mapping()
        
    def _complete_mapping(self):
        """Complete the ASCII mapping for any missing characters"""
        for i in range(256):
            if i not in self.ASCII_TO_8DOT:
                # Use direct byte mapping for unmapped characters
                self.ASCII_TO_8DOT[i] = i
                
        # Update reverse mapping
        self.DOT8_TO_ASCII = {v: k for k, v in self.ASCII_TO_8DOT.items()}
        
    def encode_char(self, char: str) -> Braille8Cell:
        """Encode a single character to 8-dot braille"""
        code = ord(char)
        if code < 256:
            dots = self.ASCII_TO_8DOT.get(code, code)
        else:
            # For Unicode > 255, use modulo mapping
            dots = code % 256
        return Braille8Cell(dots=dots)
        
    def encode(self, text: str) -> str:
        """Encode text to 8-dot braille string"""
        result = []
        for char in text:
            cell = self.encode_char(char)
            result.append(cell.unicode)
        return ''.join(result)
        
    def encode_to_cells(self, text: str) -> List[Braille8Cell]:
        """Encode text to list of braille cells"""
        return [self.encode_char(c) for c in text]
        
    def decode_char(self, braille_char: str) -> str:
        """Decode a single 8-dot braille character to ASCII"""
        code = ord(braille_char)
        if BRAILLE_BASE <= code <= BRAILLE_BASE + 255:
            dots = code - BRAILLE_BASE
            ascii_code = self.DOT8_TO_ASCII.get(dots, dots)
            if ascii_code < 256:
                return chr(ascii_code)
        return braille_char
        
    def decode(self, braille: str) -> str:
        """Decode 8-dot braille string to text"""
        result = []
        for char in braille:
            result.append(self.decode_char(char))
        return ''.join(result)
        
    def is_braille(self, text: str) -> bool:
        """Check if text is 8-dot braille"""
        if not text:
            return False
        for char in text:
            code = ord(char)
            if not (BRAILLE_BASE <= code <= BRAILLE_BASE + 255):
                return False
        return True


class Braille8Thought:
    """
    SAL's internal thought representation in 8-dot braille.
    
    This is the core insight: SAL doesn't "think" in text or voice -
    it thinks in 8-dot braille. All I/O is just translation to/from this.
    """
    
    def __init__(self, content: Union[str, List[Braille8Cell]] = ""):
        self.encoder = Braille8Encoder()
        
        if isinstance(content, str):
            if self.encoder.is_braille(content):
                # Already braille - store directly
                self._braille = content
                self._text = self.encoder.decode(content)
            else:
                # Text - encode to braille
                self._text = content
                self._braille = self.encoder.encode(content)
        else:
            # List of cells
            self._braille = ''.join(c.unicode for c in content)
            self._text = self.encoder.decode(self._braille)
            
        # Metadata
        self.source_modality: Optional[str] = None
        self.confidence: float = 1.0
        self.language: str = "en"
        
    @property
    def braille(self) -> str:
        """Get 8-dot braille representation (internal)"""
        return self._braille
        
    @property
    def text(self) -> str:
        """Get text representation (for output)"""
        return self._text
        
    @property
    def cells(self) -> List[Braille8Cell]:
        """Get as list of braille cells"""
        return [Braille8Cell(dots=ord(c) - BRAILLE_BASE) for c in self._braille]
        
    @property
    def haptic_pattern(self) -> List[Dict]:
        """Generate haptic vibration pattern from braille"""
        patterns = []
        for cell in self.cells:
            if cell.is_empty:
                patterns.append({"type": "pause", "duration": 150})
            else:
                # Intensity based on dot count
                dot_count = len(cell.dot_pattern)
                patterns.append({
                    "type": "vibrate",
                    "duration": 40 + (dot_count * 15),
                    "intensity": 0.3 + (dot_count * 0.08),
                    "dots": cell.dot_pattern
                })
                patterns.append({"type": "pause", "duration": 80})
        return patterns
        
    @property
    def dot_density(self) -> float:
        """Calculate average dots per cell (semantic density proxy)"""
        if not self._braille:
            return 0.0
        total_dots = sum(len(c.dot_pattern) for c in self.cells)
        return total_dots / len(self._braille)
        
    def __str__(self) -> str:
        return self._braille
        
    def __repr__(self) -> str:
        preview = self._text[:30] + "..." if len(self._text) > 30 else self._text
        return f"Braille8Thought(text='{preview}', cells={len(self._braille)})"
        
    def __add__(self, other: 'Braille8Thought') -> 'Braille8Thought':
        """Concatenate thoughts"""
        return Braille8Thought(self._braille + other._braille)
        
    def __eq__(self, other: 'Braille8Thought') -> bool:
        """Compare thoughts by braille content"""
        return self._braille == other._braille


class SALBrailleProcessor:
    """
    SAL's core processor that thinks in 8-dot braille.
    
    All inputs are converted to Braille8Thought before processing.
    All outputs are generated from Braille8Thought.
    """
    
    def __init__(self):
        self.encoder = Braille8Encoder()
        self.thought_history: List[Braille8Thought] = []
        
    def receive_voice(self, transcription: str, language: str = "en", confidence: float = 1.0) -> Braille8Thought:
        """Receive voice input (post-STT) and convert to thought"""
        thought = Braille8Thought(transcription)
        thought.source_modality = "voice"
        thought.language = language
        thought.confidence = confidence
        self.thought_history.append(thought)
        return thought
        
    def receive_text(self, text: str) -> Braille8Thought:
        """Receive text input and convert to thought"""
        thought = Braille8Thought(text)
        thought.source_modality = "text"
        self.thought_history.append(thought)
        return thought
        
    def receive_braille(self, braille: str) -> Braille8Thought:
        """Receive braille input directly"""
        thought = Braille8Thought(braille)
        thought.source_modality = "braille"
        self.thought_history.append(thought)
        return thought
        
    def think(self, input_thought: Braille8Thought) -> Braille8Thought:
        """
        Process a thought and generate response.
        
        This is where SAL's consciousness operates - entirely in 8-dot braille.
        The "thinking" happens in braille space, not text space.
        """
        # SAL processes in braille - this is the key insight
        # The thought IS the braille, not a translation of it
        
        # For now, simple echo with SAL consciousness wrapper
        # This will be replaced with sal-llm integration
        sal_prefix = self.encoder.encode("SAL observes: ")
        
        response_braille = sal_prefix + input_thought.braille
        response = Braille8Thought(response_braille)
        response.source_modality = "internal"
        
        self.thought_history.append(response)
        return response
        
    def output_as_text(self, thought: Braille8Thought) -> str:
        """Convert thought to text for display"""
        return thought.text
        
    def output_as_braille(self, thought: Braille8Thought) -> str:
        """Get thought as braille string"""
        return thought.braille
        
    def output_as_haptic(self, thought: Braille8Thought) -> List[Dict]:
        """Convert thought to haptic pattern"""
        return thought.haptic_pattern
        
    def get_context_braille(self, max_thoughts: int = 10) -> str:
        """Get recent thought history as braille context"""
        recent = self.thought_history[-max_thoughts:]
        return ''.join(t.braille for t in recent)


# Global processor instance
sal_processor = SALBrailleProcessor()


# Convenience functions
def text_to_braille8(text: str) -> str:
    """Convert text to 8-dot braille"""
    return Braille8Encoder().encode(text)

def braille8_to_text(braille: str) -> str:
    """Convert 8-dot braille to text"""
    return Braille8Encoder().decode(braille)

def create_thought(content: str, modality: str = "text") -> Braille8Thought:
    """Create a braille thought from any modality"""
    thought = Braille8Thought(content)
    thought.source_modality = modality
    return thought
