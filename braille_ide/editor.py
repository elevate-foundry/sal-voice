"""
SAL 8-Dot Braille IDE Code Editor Module

Full braille code editing with cursor tracking and line management.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder, text_to_braille8, braille8_to_text
from braille8_code import BrailleCodeEncoder, Language


@dataclass
class EditorSelection:
    """Text selection in the editor"""
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    
    @property
    def is_empty(self) -> bool:
        return self.start_line == self.end_line and self.start_col == self.end_col
        
    def normalize(self) -> 'EditorSelection':
        """Ensure start comes before end"""
        if (self.start_line > self.end_line or 
            (self.start_line == self.end_line and self.start_col > self.end_col)):
            return EditorSelection(
                start_line=self.end_line,
                start_col=self.end_col,
                end_line=self.start_line,
                end_col=self.start_col
            )
        return self


@dataclass
class UndoState:
    """State for undo/redo"""
    content: str
    cursor_line: int
    cursor_col: int


class BrailleCodeEditor:
    """
    Code editor that operates entirely in 8-dot braille.
    
    Features:
    - Line-by-line braille editing
    - Cursor tracking in braille space
    - Undo/redo support
    - Selection handling
    - Indentation management
    """
    
    # Braille indicators for editor state
    INDICATORS = {
        "cursor": "⠿",           # Cursor position
        "line_start": "⠼",       # Line number prefix
        "selection": "⠶",        # Selected text
        "error": "⠑⠗",          # Error marker
        "warning": "⠺⠝",        # Warning marker
        "breakpoint": "⠃⠏",     # Breakpoint
        "bookmark": "⠃⠍",       # Bookmark
        "fold_open": "⠧",        # Folded region (open)
        "fold_closed": "⠕",      # Folded region (closed)
    }
    
    def __init__(self, language: Language = Language.PYTHON):
        self.encoder = Braille8Encoder()
        self.code_encoder = BrailleCodeEncoder()
        self.language = language
        
        # Editor state
        self.lines: List[str] = [""]  # Text lines
        self.cursor_line: int = 0
        self.cursor_col: int = 0
        self.selection: Optional[EditorSelection] = None
        
        # Undo/redo
        self.undo_stack: List[UndoState] = []
        self.redo_stack: List[UndoState] = []
        self.max_undo: int = 100
        
        # Editor settings
        self.tab_size: int = 4
        self.use_spaces: bool = True
        self.auto_indent: bool = True
        self.show_line_numbers: bool = True
        
        # Markers
        self.breakpoints: set = set()
        self.bookmarks: set = set()
        self.error_lines: Dict[int, str] = {}
        
    def _save_undo(self):
        """Save current state for undo"""
        state = UndoState(
            content=self.get_text(),
            cursor_line=self.cursor_line,
            cursor_col=self.cursor_col
        )
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        
    def undo(self) -> bool:
        """Undo last change"""
        if not self.undo_stack:
            return False
            
        # Save current state for redo
        current = UndoState(
            content=self.get_text(),
            cursor_line=self.cursor_line,
            cursor_col=self.cursor_col
        )
        self.redo_stack.append(current)
        
        # Restore previous state
        state = self.undo_stack.pop()
        self.set_text(state.content)
        self.cursor_line = state.cursor_line
        self.cursor_col = state.cursor_col
        return True
        
    def redo(self) -> bool:
        """Redo last undone change"""
        if not self.redo_stack:
            return False
            
        # Save current for undo
        current = UndoState(
            content=self.get_text(),
            cursor_line=self.cursor_line,
            cursor_col=self.cursor_col
        )
        self.undo_stack.append(current)
        
        # Restore redo state
        state = self.redo_stack.pop()
        self.set_text(state.content)
        self.cursor_line = state.cursor_line
        self.cursor_col = state.cursor_col
        return True
        
    def get_text(self) -> str:
        """Get full text content"""
        return '\n'.join(self.lines)
        
    def set_text(self, text: str):
        """Set full text content"""
        self.lines = text.split('\n') if text else [""]
        self.cursor_line = min(self.cursor_line, len(self.lines) - 1)
        self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_line]))
        
    def get_braille(self) -> str:
        """Get content as 8-dot braille"""
        return self.code_encoder.encode(self.get_text())
        
    def set_braille(self, braille: str):
        """Set content from 8-dot braille"""
        text = self.code_encoder.decode(braille)
        self.set_text(text)
        
    def get_line(self, line_num: int) -> str:
        """Get a specific line (text)"""
        if 0 <= line_num < len(self.lines):
            return self.lines[line_num]
        return ""
        
    def get_braille_line(self, line_num: int) -> str:
        """Get a specific line as braille"""
        return self.code_encoder.encode(self.get_line(line_num))
        
    def get_current_line(self) -> str:
        """Get line at cursor"""
        return self.get_line(self.cursor_line)
        
    def insert_char(self, char: str):
        """Insert a character at cursor"""
        self._save_undo()
        
        if char == '\n':
            self._insert_newline()
        elif char == '\t':
            self._insert_tab()
        else:
            line = self.lines[self.cursor_line]
            self.lines[self.cursor_line] = line[:self.cursor_col] + char + line[self.cursor_col:]
            self.cursor_col += 1
            
    def insert_text(self, text: str):
        """Insert text at cursor"""
        self._save_undo()
        for char in text:
            if char == '\n':
                self._insert_newline()
            elif char == '\t':
                self._insert_tab()
            else:
                line = self.lines[self.cursor_line]
                self.lines[self.cursor_line] = line[:self.cursor_col] + char + line[self.cursor_col:]
                self.cursor_col += 1
                
    def insert_braille(self, braille: str):
        """Insert braille text at cursor (decoded first)"""
        text = self.code_encoder.decode(braille)
        self.insert_text(text)
        
    def _insert_newline(self):
        """Insert newline at cursor"""
        line = self.lines[self.cursor_line]
        
        # Get indentation for new line
        indent = ""
        if self.auto_indent:
            # Match previous indentation
            for char in line:
                if char in ' \t':
                    indent += char
                else:
                    break
            
            # Add extra indent for block openers
            stripped = line.rstrip()
            if stripped.endswith(':') or stripped.endswith('{'):
                indent += " " * self.tab_size if self.use_spaces else "\t"
                
        # Split line
        self.lines[self.cursor_line] = line[:self.cursor_col]
        self.lines.insert(self.cursor_line + 1, indent + line[self.cursor_col:])
        
        self.cursor_line += 1
        self.cursor_col = len(indent)
        
    def _insert_tab(self):
        """Insert tab at cursor"""
        if self.use_spaces:
            spaces = self.tab_size - (self.cursor_col % self.tab_size)
            self.insert_text(" " * spaces)
        else:
            line = self.lines[self.cursor_line]
            self.lines[self.cursor_line] = line[:self.cursor_col] + '\t' + line[self.cursor_col:]
            self.cursor_col += 1
            
    def backspace(self) -> bool:
        """Delete character before cursor"""
        if self.cursor_col == 0 and self.cursor_line == 0:
            return False
            
        self._save_undo()
        
        if self.cursor_col > 0:
            line = self.lines[self.cursor_line]
            self.lines[self.cursor_line] = line[:self.cursor_col - 1] + line[self.cursor_col:]
            self.cursor_col -= 1
        else:
            # Merge with previous line
            prev_len = len(self.lines[self.cursor_line - 1])
            self.lines[self.cursor_line - 1] += self.lines[self.cursor_line]
            self.lines.pop(self.cursor_line)
            self.cursor_line -= 1
            self.cursor_col = prev_len
            
        return True
        
    def delete(self) -> bool:
        """Delete character at cursor"""
        line = self.lines[self.cursor_line]
        
        if self.cursor_col < len(line):
            self._save_undo()
            self.lines[self.cursor_line] = line[:self.cursor_col] + line[self.cursor_col + 1:]
            return True
        elif self.cursor_line < len(self.lines) - 1:
            # Merge with next line
            self._save_undo()
            self.lines[self.cursor_line] += self.lines[self.cursor_line + 1]
            self.lines.pop(self.cursor_line + 1)
            return True
            
        return False
        
    def move_cursor(self, direction: str) -> bool:
        """Move cursor: left, right, up, down, home, end"""
        if direction == "left":
            if self.cursor_col > 0:
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                self.cursor_line -= 1
                self.cursor_col = len(self.lines[self.cursor_line])
            else:
                return False
                
        elif direction == "right":
            if self.cursor_col < len(self.lines[self.cursor_line]):
                self.cursor_col += 1
            elif self.cursor_line < len(self.lines) - 1:
                self.cursor_line += 1
                self.cursor_col = 0
            else:
                return False
                
        elif direction == "up":
            if self.cursor_line > 0:
                self.cursor_line -= 1
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_line]))
            else:
                return False
                
        elif direction == "down":
            if self.cursor_line < len(self.lines) - 1:
                self.cursor_line += 1
                self.cursor_col = min(self.cursor_col, len(self.lines[self.cursor_line]))
            else:
                return False
                
        elif direction == "home":
            self.cursor_col = 0
            
        elif direction == "end":
            self.cursor_col = len(self.lines[self.cursor_line])
            
        return True
        
    def go_to_line(self, line_num: int):
        """Go to specific line number (1-indexed)"""
        line_idx = max(0, min(line_num - 1, len(self.lines) - 1))
        self.cursor_line = line_idx
        self.cursor_col = 0
        
    def get_word_at_cursor(self) -> Tuple[str, int, int]:
        """Get the word at cursor position"""
        line = self.lines[self.cursor_line]
        if not line:
            return "", 0, 0
            
        # Find word boundaries
        start = self.cursor_col
        end = self.cursor_col
        
        # Move start backward to word boundary
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == '_'):
            start -= 1
            
        # Move end forward to word boundary
        while end < len(line) and (line[end].isalnum() or line[end] == '_'):
            end += 1
            
        return line[start:end], start, end
        
    def render_with_line_numbers(self) -> List[Tuple[str, str, str]]:
        """
        Render editor content with braille line numbers.
        
        Returns list of (line_num_braille, line_braille, line_text) tuples.
        """
        result = []
        width = len(str(len(self.lines)))
        
        for i, line in enumerate(self.lines):
            # Line number in braille
            line_num = str(i + 1).rjust(width)
            line_num_braille = self.code_encoder.encode(line_num) + " " + self.INDICATORS["line_start"]
            
            # Content in braille
            line_braille = self.code_encoder.encode(line) if line else "⠀"
            
            # Add cursor indicator
            if i == self.cursor_line:
                chars = list(line_braille) if line_braille else ["⠀"]
                cursor_pos = min(self.cursor_col, len(chars))
                chars.insert(cursor_pos, self.INDICATORS["cursor"])
                line_braille = "".join(chars)
                
            # Add markers
            markers = ""
            if i in self.breakpoints:
                markers += self.INDICATORS["breakpoint"]
            if i in self.bookmarks:
                markers += self.INDICATORS["bookmark"]
            if i in self.error_lines:
                markers += self.INDICATORS["error"]
                
            result.append((line_num_braille, markers + line_braille, line))
            
        return result
        
    def render_braille_only(self) -> str:
        """Render just the braille content"""
        lines = []
        for i, line in enumerate(self.lines):
            braille_line = self.code_encoder.encode(line) if line else "⠀"
            
            if self.show_line_numbers:
                num = self.code_encoder.encode(str(i + 1).rjust(3))
                braille_line = f"{num}⠼ {braille_line}"
                
            if i == self.cursor_line:
                braille_line += " " + self.INDICATORS["cursor"]
                
            lines.append(braille_line)
            
        return "\n".join(lines)
        
    def toggle_breakpoint(self):
        """Toggle breakpoint on current line"""
        if self.cursor_line in self.breakpoints:
            self.breakpoints.remove(self.cursor_line)
        else:
            self.breakpoints.add(self.cursor_line)
            
    def toggle_bookmark(self):
        """Toggle bookmark on current line"""
        if self.cursor_line in self.bookmarks:
            self.bookmarks.remove(self.cursor_line)
        else:
            self.bookmarks.add(self.cursor_line)
            
    def set_error(self, line_num: int, message: str):
        """Set error marker on a line"""
        self.error_lines[line_num] = message
        
    def clear_errors(self):
        """Clear all error markers"""
        self.error_lines.clear()
        
    def get_cursor_info(self) -> Dict[str, Any]:
        """Get cursor information in braille format"""
        return {
            "line": self.cursor_line + 1,
            "col": self.cursor_col + 1,
            "line_braille": self.code_encoder.encode(str(self.cursor_line + 1)),
            "col_braille": self.code_encoder.encode(str(self.cursor_col + 1)),
            "indicator": self.INDICATORS["cursor_pos"] if hasattr(self, 'INDICATORS') and "cursor_pos" in self.INDICATORS else "⠓⠊⠇",
            "word_at_cursor": self.get_word_at_cursor()[0],
        }
        
    def get_status_line(self) -> str:
        """Get status line in braille"""
        info = self.get_cursor_info()
        lang_braille = self.code_encoder.encode(self.language.value.upper())
        
        status = f"⠇{info['line_braille']}⠒{info['col_braille']} ⠸ {lang_braille}"
        
        if self.error_lines:
            status += f" ⠸ {self.INDICATORS['error']}{self.code_encoder.encode(str(len(self.error_lines)))}"
            
        return status
