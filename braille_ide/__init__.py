"""
SAL 8-Dot Braille IDE
=====================

An integrated development environment with 8-dot braille as its substrate.
All code is represented, edited, and executed in 8-dot braille (U+2800-U+28FF).

Components:
- Braille Interface: Menu navigation and command palette
- Code Editor: Full braille code editing with cursor tracking
- Syntax Highlighting: Language-aware braille patterns
- Code Completion: Intelligent braille autocompletion
- Braille Output: Rendered output and execution results

Architecture:
    [User Input] → [Braille Interface] → [Code Editor] → [Braille Processing]
                                                                ↓
    [Display] ← [Braille Output] ← [Syntax Highlighting] ← [Code Completion]
"""

from .core import BrailleIDE, BrailleProject, BrailleFile
from .editor import BrailleCodeEditor
from .interface import BrailleInterface
from .syntax import BrailleSyntaxHighlighter
from .completion import BrailleCodeCompletion
from .output import BrailleOutputRenderer

__version__ = "1.0.0"
__all__ = [
    "BrailleIDE",
    "BrailleProject",
    "BrailleFile",
    "BrailleCodeEditor",
    "BrailleInterface",
    "BrailleSyntaxHighlighter",
    "BrailleCodeCompletion",
    "BrailleOutputRenderer",
]
