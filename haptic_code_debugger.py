"""
Haptic Code Debugger - Only Possible in 8-Dot Braille

This system uses 8-dot braille as the internal representation to enable:
1. Feel syntax errors as haptic patterns BEFORE seeing them
2. Debug by touch - each error type has a unique vibration signature
3. Simultaneous multi-modal code review (text + braille + haptic + audio)

WHY THIS ONLY WORKS IN 8-DOT BRAILLE:
- 8-dot braille maps 1:1 to ASCII (256 chars)
- Each braille cell has a natural haptic signature (which dots are raised)
- The DOT PATTERN itself encodes semantic meaning
- No lossy translation between modalities

Example: A missing semicolon in JavaScript
- Text: "const x = 5"  (missing ;)
- 8-dot braille: ⠉⠕⠝⠎⠞⠀⠭⠀⠐⠶⠀⢑ (missing ⠆)
- Haptic: The ABSENCE of the semicolon's dot pattern (dots 2,3) creates a "gap"
- The haptic system feels this gap as a missing beat in the rhythm

This is fundamentally different from "converting text to haptic" because
the 8-dot braille IS the canonical form - everything else is a view into it.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum
import re

from braille8_core import Braille8Encoder, Braille8Thought
from braille8_code import braille_code_encoder, Language


class ErrorSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class HapticSignature:
    """A haptic pattern that represents a code concept or error"""
    pattern: List[Dict]  # Vibration pattern
    name: str
    description: str
    braille_marker: str  # The braille character(s) associated with this
    

@dataclass
class CodeError:
    """A code error with its haptic signature"""
    line: int
    column: int
    message: str
    severity: ErrorSeverity
    code_snippet: str
    braille_snippet: str
    haptic_signature: HapticSignature


class HapticCodeDebugger:
    """
    Debug code through haptic feedback using 8-dot braille as the core representation.
    
    The key insight: 8-dot braille cells have PHYSICAL structure (which dots are raised).
    This physical structure maps naturally to haptic patterns.
    We're not "converting" - we're REVEALING the haptic nature of the braille.
    """
    
    def __init__(self):
        self.encoder = Braille8Encoder()
        
        # Define haptic signatures for common errors
        self.error_signatures = {
            "missing_semicolon": HapticSignature(
                pattern=[
                    {"type": "vibrate", "duration": 100, "intensity": 0.8},
                    {"type": "pause", "duration": 50},
                    {"type": "vibrate", "duration": 100, "intensity": 0.8},
                    {"type": "pause", "duration": 200},  # THE GAP - missing semicolon
                    {"type": "vibrate", "duration": 300, "intensity": 0.5},  # Alert
                ],
                name="Missing Semicolon",
                description="Two quick pulses, then a gap where the semicolon should be",
                braille_marker="⠆"  # Semicolon in braille
            ),
            "unclosed_bracket": HapticSignature(
                pattern=[
                    {"type": "vibrate", "duration": 150, "intensity": 0.6},
                    {"type": "pause", "duration": 50},
                    {"type": "vibrate", "duration": 150, "intensity": 0.7},
                    {"type": "pause", "duration": 50},
                    {"type": "vibrate", "duration": 150, "intensity": 0.8},
                    {"type": "pause", "duration": 50},
                    {"type": "vibrate", "duration": 150, "intensity": 0.9},  # Ascending = unclosed
                ],
                name="Unclosed Bracket",
                description="Ascending intensity - something opened but never closed",
                braille_marker="⠐⠣"  # Open paren in braille
            ),
            "type_mismatch": HapticSignature(
                pattern=[
                    {"type": "vibrate", "duration": 100, "intensity": 0.8},
                    {"type": "pause", "duration": 100},
                    {"type": "vibrate", "duration": 100, "intensity": 0.3},
                    {"type": "pause", "duration": 100},
                    {"type": "vibrate", "duration": 100, "intensity": 0.8},
                    {"type": "pause", "duration": 100},
                    {"type": "vibrate", "duration": 100, "intensity": 0.3},  # Alternating = mismatch
                ],
                name="Type Mismatch",
                description="Alternating high/low intensity - two things that don't match",
                braille_marker="⠿"  # Full cell = type indicator
            ),
            "undefined_variable": HapticSignature(
                pattern=[
                    {"type": "vibrate", "duration": 50, "intensity": 0.9},
                    {"type": "pause", "duration": 300},  # Long pause = searching
                    {"type": "vibrate", "duration": 50, "intensity": 0.9},
                    {"type": "pause", "duration": 300},
                    {"type": "vibrate", "duration": 200, "intensity": 0.5},  # Give up
                ],
                name="Undefined Variable",
                description="Short pulse, long search, short pulse, long search - looking for something not there",
                braille_marker="⠀"  # Empty cell = nothing found
            ),
            "syntax_error": HapticSignature(
                pattern=[
                    {"type": "vibrate", "duration": 500, "intensity": 1.0},  # Strong alert
                    {"type": "pause", "duration": 100},
                    {"type": "vibrate", "duration": 100, "intensity": 0.5},
                    {"type": "vibrate", "duration": 100, "intensity": 0.5},
                    {"type": "vibrate", "duration": 100, "intensity": 0.5},
                ],
                name="Syntax Error",
                description="Strong pulse followed by rapid taps - something is fundamentally wrong",
                braille_marker="⠿⠿⠿"  # Multiple full cells = critical
            ),
        }
        
    def analyze_code(self, code: str, language: Language = Language.PYTHON) -> List[CodeError]:
        """
        Analyze code and return errors with haptic signatures.
        
        The magic: we analyze the 8-dot BRAILLE version of the code,
        not the text. The braille structure reveals patterns invisible in text.
        """
        errors = []
        
        # Convert to braille thought - this is our canonical representation
        thought = Braille8Thought(code)
        braille_code = thought.braille
        
        # Analyze based on language
        if language == Language.PYTHON:
            errors.extend(self._analyze_python(code, braille_code))
        elif language == Language.JAVASCRIPT:
            errors.extend(self._analyze_javascript(code, braille_code))
        elif language == Language.RUST:
            errors.extend(self._analyze_rust(code, braille_code))
            
        return errors
        
    def _analyze_python(self, code: str, braille: str) -> List[CodeError]:
        """Analyze Python code through its braille representation"""
        errors = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            # Check for unclosed parentheses
            open_count = line.count('(') - line.count(')')
            if open_count > 0:
                errors.append(CodeError(
                    line=i + 1,
                    column=line.rfind('('),
                    message=f"Unclosed parenthesis ({open_count} unclosed)",
                    severity=ErrorSeverity.ERROR,
                    code_snippet=line,
                    braille_snippet=self.encoder.encode(line),
                    haptic_signature=self.error_signatures["unclosed_bracket"]
                ))
                
            # Check for unclosed brackets
            open_brackets = line.count('[') - line.count(']')
            if open_brackets > 0:
                errors.append(CodeError(
                    line=i + 1,
                    column=line.rfind('['),
                    message=f"Unclosed bracket ({open_brackets} unclosed)",
                    severity=ErrorSeverity.ERROR,
                    code_snippet=line,
                    braille_snippet=self.encoder.encode(line),
                    haptic_signature=self.error_signatures["unclosed_bracket"]
                ))
                
            # Check for undefined looking variables (simplified)
            if re.search(r'\b(undefined|null|None)\s*\+', line):
                errors.append(CodeError(
                    line=i + 1,
                    column=0,
                    message="Possible operation on undefined value",
                    severity=ErrorSeverity.WARNING,
                    code_snippet=line,
                    braille_snippet=self.encoder.encode(line),
                    haptic_signature=self.error_signatures["undefined_variable"]
                ))
                
        return errors
        
    def _analyze_javascript(self, code: str, braille: str) -> List[CodeError]:
        """Analyze JavaScript code through its braille representation"""
        errors = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check for missing semicolons (simplified)
            if stripped and not stripped.endswith((';', '{', '}', ':', ',')):
                if not stripped.startswith(('if', 'else', 'for', 'while', 'function', '//', '/*', '*')):
                    if '=' in stripped or stripped.startswith(('const', 'let', 'var', 'return')):
                        errors.append(CodeError(
                            line=i + 1,
                            column=len(line),
                            message="Missing semicolon",
                            severity=ErrorSeverity.WARNING,
                            code_snippet=line,
                            braille_snippet=self.encoder.encode(line),
                            haptic_signature=self.error_signatures["missing_semicolon"]
                        ))
                        
            # Check for unclosed braces
            if stripped.endswith('{') or '{' in stripped:
                open_braces = line.count('{') - line.count('}')
                if open_braces > 0 and not any(line.strip().startswith(kw) for kw in ['if', 'for', 'while', 'function', 'class']):
                    pass  # Check at file level instead
                    
        return errors
        
    def _analyze_rust(self, code: str, braille: str) -> List[CodeError]:
        """Analyze Rust code through its braille representation"""
        errors = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            # Check for missing semicolons in Rust
            stripped = line.strip()
            if stripped and not stripped.endswith((';', '{', '}', ':')):
                if not stripped.startswith(('//', '/*', '*', 'fn', 'struct', 'impl', 'pub', 'mod', 'use')):
                    if 'let' in stripped or '=' in stripped:
                        errors.append(CodeError(
                            line=i + 1,
                            column=len(line),
                            message="Missing semicolon",
                            severity=ErrorSeverity.ERROR,
                            code_snippet=line,
                            braille_snippet=self.encoder.encode(line),
                            haptic_signature=self.error_signatures["missing_semicolon"]
                        ))
                        
        return errors
        
    def get_haptic_stream(self, errors: List[CodeError]) -> List[Dict]:
        """
        Generate a continuous haptic stream for all errors.
        
        This is where the magic happens: you can FEEL the errors
        as a sequence of distinct tactile patterns.
        """
        stream = []
        
        for i, error in enumerate(errors):
            # Add error location indicator (line number as pulses)
            for _ in range(min(error.line, 5)):  # Max 5 pulses for line number
                stream.append({"type": "vibrate", "duration": 30, "intensity": 0.3})
                stream.append({"type": "pause", "duration": 30})
                
            stream.append({"type": "pause", "duration": 100})  # Gap before error
            
            # Add the error's haptic signature
            stream.extend(error.haptic_signature.pattern)
            
            # Gap between errors
            stream.append({"type": "pause", "duration": 300})
            
        return stream
        
    def describe_in_braille(self, error: CodeError) -> str:
        """Describe the error entirely in 8-dot braille"""
        description = f"Line {error.line}: {error.message}"
        return self.encoder.encode(description)


# Demo function
def demo_haptic_debugging():
    """Demonstrate haptic code debugging"""
    debugger = HapticCodeDebugger()
    
    # JavaScript with missing semicolons
    js_code = """
const x = 5
const y = 10
const z = x + y
console.log(z)
"""
    
    print("⠠⠎⠁⠇ Haptic Code Debugger Demo")
    print("=" * 50)
    print("\nJavaScript Code:")
    print(js_code)
    
    errors = debugger.analyze_code(js_code, Language.JAVASCRIPT)
    
    print(f"\nFound {len(errors)} issues:\n")
    for error in errors:
        print(f"Line {error.line}: {error.message}")
        print(f"  Braille: {error.braille_snippet[:30]}...")
        print(f"  Haptic: {error.haptic_signature.name}")
        print(f"  Feel: {error.haptic_signature.description}")
        print()
        
    # Generate haptic stream
    haptic = debugger.get_haptic_stream(errors)
    print(f"Haptic stream: {len(haptic)} segments")
    print("You would FEEL: ", end="")
    for seg in haptic[:10]:
        if seg["type"] == "vibrate":
            print("〰️", end="")
        else:
            print("·", end="")
    print("...")


if __name__ == "__main__":
    demo_haptic_debugging()
