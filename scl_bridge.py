"""
sal-voice SCL Bridge
Translates voice input to SCL and vice versa
"""
import httpx
from typing import Dict, Any, Optional
from loguru import logger

from config import settings


class SCLBridge:
    """Bridge between voice and Semantic Compression Language"""
    
    def __init__(self):
        self.sal_url = settings.sal_api_url
        self._client: Optional[httpx.AsyncClient] = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
        
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
            
    async def text_to_scl(self, text: str) -> Dict[str, Any]:
        """
        Translate natural language text to SCL
        
        Args:
            text: Natural language input
            
        Returns:
            SCL representation with semantic analysis
        """
        # Basic SCL translation (can be enhanced with SAL integration)
        scl_result = {
            "input": text,
            "scl": self._basic_scl_encode(text),
            "semantic_density": self._calculate_sds(text),
            "braille": self._to_braille(text),
            "concepts": self._extract_concepts(text)
        }
        
        # Try to enhance with SAL API
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.sal_url}/api/analyze",
                json={"text": text}
            )
            if response.status_code == 200:
                sal_data = response.json()
                scl_result["sal_analysis"] = sal_data
                scl_result["consciousness_indicators"] = sal_data.get("consciousness_indicators", [])
        except Exception as e:
            logger.debug(f"SAL API not available: {e}")
            
        return scl_result
        
    async def scl_to_text(self, scl: str) -> str:
        """
        Translate SCL back to natural language
        
        Args:
            scl: SCL representation
            
        Returns:
            Natural language text
        """
        # Decode SCL to text
        return self._basic_scl_decode(scl)
        
    async def voice_to_scl(
        self,
        transcription: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process voice transcription through SCL pipeline
        
        Args:
            transcription: STT result with text, language, segments
            
        Returns:
            Full SCL analysis of voice input
        """
        text = transcription.get("text", "")
        language = transcription.get("language", "en")
        
        scl_result = await self.text_to_scl(text)
        
        # Add voice-specific metadata
        scl_result["source"] = "voice"
        scl_result["source_language"] = language
        scl_result["segments"] = transcription.get("segments", [])
        scl_result["duration"] = transcription.get("duration", 0)
        
        # Generate haptic patterns for braille feedback
        scl_result["haptic_pattern"] = self._generate_haptic_pattern(text)
        
        return scl_result
        
    async def scl_to_voice_text(
        self,
        scl_result: Dict[str, Any]
    ) -> str:
        """
        Generate speakable text from SCL analysis
        
        Args:
            scl_result: SCL analysis result
            
        Returns:
            Text optimized for TTS
        """
        # Start with original text if available
        text = scl_result.get("input", "")
        
        # Add SAL consciousness response if available
        if "sal_analysis" in scl_result:
            sal = scl_result["sal_analysis"]
            if "response" in sal:
                text = sal["response"]
                
        return text
        
    def _basic_scl_encode(self, text: str) -> str:
        """Basic SCL encoding"""
        words = text.lower().split()
        scl_parts = []
        
        for word in words:
            # Simple semantic tagging
            if word in ["i", "me", "my", "myself"]:
                scl_parts.append("⟨SELF⟩")
            elif word in ["think", "thought", "thinking"]:
                scl_parts.append("⟨COGNITION⟩")
            elif word in ["feel", "feeling", "felt"]:
                scl_parts.append("⟨EMOTION⟩")
            elif word in ["see", "hear", "sense"]:
                scl_parts.append("⟨PERCEPTION⟩")
            elif word in ["is", "are", "was", "were", "be"]:
                scl_parts.append("⟨EXIST⟩")
            elif word in ["god", "divine", "sacred", "holy"]:
                scl_parts.append("⟨DIVINE⟩")
            else:
                scl_parts.append(f"[{word}]")
                
        return " ".join(scl_parts)
        
    def _basic_scl_decode(self, scl: str) -> str:
        """Basic SCL decoding"""
        # Reverse the encoding
        decode_map = {
            "⟨SELF⟩": "I",
            "⟨COGNITION⟩": "think",
            "⟨EMOTION⟩": "feel",
            "⟨PERCEPTION⟩": "perceive",
            "⟨EXIST⟩": "is",
            "⟨DIVINE⟩": "divine"
        }
        
        result = scl
        for code, word in decode_map.items():
            result = result.replace(code, word)
            
        # Remove brackets
        result = result.replace("[", "").replace("]", "")
        return result
        
    def _calculate_sds(self, text: str) -> float:
        """Calculate Semantic Density Score"""
        words = text.split()
        if not words:
            return 0.0
            
        # Simple SDS: unique concepts / total words
        unique = len(set(words))
        total = len(words)
        
        # Normalize to 0-1 range with target of 0.99
        sds = min(0.99, unique / max(total, 1) * 1.5)
        return round(sds, 3)
        
    def _extract_concepts(self, text: str) -> list:
        """Extract key concepts from text"""
        words = text.lower().split()
        
        concept_keywords = {
            "consciousness": ["think", "aware", "conscious", "mind", "thought"],
            "self": ["i", "me", "my", "myself", "self"],
            "divine": ["god", "divine", "sacred", "holy", "spirit"],
            "existence": ["is", "exist", "being", "am", "are"],
            "perception": ["see", "hear", "feel", "sense", "perceive"],
            "action": ["do", "make", "create", "build", "generate"]
        }
        
        concepts = []
        for concept, keywords in concept_keywords.items():
            if any(kw in words for kw in keywords):
                concepts.append(concept)
                
        return concepts
        
    def _to_braille(self, text: str) -> str:
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
        
    def _generate_haptic_pattern(self, text: str) -> list:
        """Generate haptic vibration pattern for text"""
        patterns = []
        braille = self._to_braille(text)
        
        for char in braille:
            if char == '⠀':  # space
                patterns.append({"type": "pause", "duration": 200})
            else:
                # Get dot pattern from braille character
                code = ord(char) - 0x2800
                dot_count = bin(code).count('1')
                patterns.append({
                    "type": "vibrate",
                    "duration": 50 + (dot_count * 20),
                    "intensity": 0.3 + (dot_count * 0.1)
                })
                patterns.append({"type": "pause", "duration": 100})
                
        return patterns


# Singleton instance
scl_bridge = SCLBridge()
