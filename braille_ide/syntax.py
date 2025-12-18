"""
SAL 8-Dot Braille IDE Syntax Highlighting Module

Language-aware braille patterns for syntax highlighting.
Each token type gets a unique braille prefix/suffix pattern.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_code import BrailleCodeEncoder, Language


class TokenType(str, Enum):
    """Types of syntax tokens"""
    KEYWORD = "keyword"
    BUILTIN = "builtin"
    TYPE = "type"
    CONSTANT = "constant"
    STRING = "string"
    NUMBER = "number"
    COMMENT = "comment"
    OPERATOR = "operator"
    PUNCTUATION = "punctuation"
    IDENTIFIER = "identifier"
    FUNCTION = "function"
    CLASS = "class"
    DECORATOR = "decorator"
    SPECIAL = "special"
    ERROR = "error"
    WHITESPACE = "whitespace"


@dataclass
class BrailleToken:
    """A syntax token with braille representation"""
    text: str
    braille: str
    token_type: TokenType
    start: int
    end: int
    line: int
    
    @property
    def highlighted_braille(self) -> str:
        """Get braille with syntax highlighting markers"""
        highlighter = BrailleSyntaxHighlighter()
        prefix, suffix = highlighter.get_highlight_markers(self.token_type)
        return f"{prefix}{self.braille}{suffix}"


class BrailleSyntaxHighlighter:
    """
    Syntax highlighter that works in 8-dot braille space.
    
    Uses braille dot patterns as highlighting markers:
    - Keywords: ⠕⠓⠒⠁ prefix (as SAL specified)
    - Types: ⠑⠊⠍⠙ prefix
    - Comments: ⠕⠓⠒⠁# prefix
    - etc.
    """
    
    # Braille highlighting patterns (prefix, suffix)
    HIGHLIGHT_PATTERNS: Dict[TokenType, Tuple[str, str]] = {
        TokenType.KEYWORD: ("⠸⠅", "⠸"),       # Bold keyword indicator
        TokenType.BUILTIN: ("⠸⠃", "⠸"),       # Built-in function
        TokenType.TYPE: ("⠸⠞", "⠸"),          # Type indicator
        TokenType.CONSTANT: ("⠸⠉", "⠸"),      # Constant
        TokenType.STRING: ("⠸⠎", "⠸"),        # String
        TokenType.NUMBER: ("⠸⠝", "⠸"),        # Number
        TokenType.COMMENT: ("⠸⠒", "⠸"),       # Comment (dimmed)
        TokenType.OPERATOR: ("⠸⠕", "⠸"),      # Operator
        TokenType.PUNCTUATION: ("", ""),        # No highlight
        TokenType.IDENTIFIER: ("", ""),         # No highlight
        TokenType.FUNCTION: ("⠸⠋", "⠸"),      # Function definition
        TokenType.CLASS: ("⠸⠉⠇", "⠸"),       # Class definition
        TokenType.DECORATOR: ("⠸⠙", "⠸"),     # Decorator
        TokenType.SPECIAL: ("⠸⠎⠏", "⠸"),     # Special variable
        TokenType.ERROR: ("⠸⠑⠗", "⠸"),       # Error
        TokenType.WHITESPACE: ("", ""),         # No highlight
    }
    
    # Language keyword patterns
    LANGUAGE_PATTERNS: Dict[Language, Dict[str, TokenType]] = {
        Language.PYTHON: {
            # Keywords
            "def": TokenType.KEYWORD, "class": TokenType.KEYWORD,
            "if": TokenType.KEYWORD, "elif": TokenType.KEYWORD, "else": TokenType.KEYWORD,
            "for": TokenType.KEYWORD, "while": TokenType.KEYWORD,
            "try": TokenType.KEYWORD, "except": TokenType.KEYWORD, "finally": TokenType.KEYWORD,
            "with": TokenType.KEYWORD, "as": TokenType.KEYWORD,
            "return": TokenType.KEYWORD, "yield": TokenType.KEYWORD, "raise": TokenType.KEYWORD,
            "break": TokenType.KEYWORD, "continue": TokenType.KEYWORD, "pass": TokenType.KEYWORD,
            "import": TokenType.KEYWORD, "from": TokenType.KEYWORD,
            "async": TokenType.KEYWORD, "await": TokenType.KEYWORD,
            "lambda": TokenType.KEYWORD, "and": TokenType.KEYWORD, "or": TokenType.KEYWORD,
            "not": TokenType.KEYWORD, "in": TokenType.KEYWORD, "is": TokenType.KEYWORD,
            "global": TokenType.KEYWORD, "nonlocal": TokenType.KEYWORD,
            "assert": TokenType.KEYWORD, "del": TokenType.KEYWORD,
            # Built-ins
            "print": TokenType.BUILTIN, "len": TokenType.BUILTIN, "range": TokenType.BUILTIN,
            "input": TokenType.BUILTIN, "open": TokenType.BUILTIN, "type": TokenType.BUILTIN,
            "isinstance": TokenType.BUILTIN, "hasattr": TokenType.BUILTIN, "getattr": TokenType.BUILTIN,
            "setattr": TokenType.BUILTIN, "enumerate": TokenType.BUILTIN, "zip": TokenType.BUILTIN,
            "map": TokenType.BUILTIN, "filter": TokenType.BUILTIN, "sorted": TokenType.BUILTIN,
            "reversed": TokenType.BUILTIN, "sum": TokenType.BUILTIN, "min": TokenType.BUILTIN,
            "max": TokenType.BUILTIN, "abs": TokenType.BUILTIN, "round": TokenType.BUILTIN,
            "all": TokenType.BUILTIN, "any": TokenType.BUILTIN, "iter": TokenType.BUILTIN,
            "next": TokenType.BUILTIN, "super": TokenType.BUILTIN,
            # Types
            "str": TokenType.TYPE, "int": TokenType.TYPE, "float": TokenType.TYPE,
            "bool": TokenType.TYPE, "list": TokenType.TYPE, "dict": TokenType.TYPE,
            "set": TokenType.TYPE, "tuple": TokenType.TYPE, "bytes": TokenType.TYPE,
            "object": TokenType.TYPE, "Exception": TokenType.TYPE,
            # Constants
            "None": TokenType.CONSTANT, "True": TokenType.CONSTANT, "False": TokenType.CONSTANT,
            # Special
            "self": TokenType.SPECIAL, "cls": TokenType.SPECIAL, "__init__": TokenType.SPECIAL,
            "__name__": TokenType.SPECIAL, "__main__": TokenType.SPECIAL,
        },
        Language.RUST: {
            # Keywords
            "fn": TokenType.KEYWORD, "let": TokenType.KEYWORD, "mut": TokenType.KEYWORD,
            "const": TokenType.KEYWORD, "static": TokenType.KEYWORD,
            "struct": TokenType.KEYWORD, "enum": TokenType.KEYWORD, "impl": TokenType.KEYWORD,
            "trait": TokenType.KEYWORD, "type": TokenType.KEYWORD,
            "pub": TokenType.KEYWORD, "mod": TokenType.KEYWORD, "use": TokenType.KEYWORD,
            "crate": TokenType.KEYWORD, "super": TokenType.KEYWORD,
            "if": TokenType.KEYWORD, "else": TokenType.KEYWORD, "match": TokenType.KEYWORD,
            "loop": TokenType.KEYWORD, "while": TokenType.KEYWORD, "for": TokenType.KEYWORD,
            "in": TokenType.KEYWORD, "break": TokenType.KEYWORD, "continue": TokenType.KEYWORD,
            "return": TokenType.KEYWORD, "async": TokenType.KEYWORD, "await": TokenType.KEYWORD,
            "move": TokenType.KEYWORD, "ref": TokenType.KEYWORD, "where": TokenType.KEYWORD,
            "unsafe": TokenType.KEYWORD, "extern": TokenType.KEYWORD,
            # Types
            "i8": TokenType.TYPE, "i16": TokenType.TYPE, "i32": TokenType.TYPE, "i64": TokenType.TYPE,
            "i128": TokenType.TYPE, "isize": TokenType.TYPE,
            "u8": TokenType.TYPE, "u16": TokenType.TYPE, "u32": TokenType.TYPE, "u64": TokenType.TYPE,
            "u128": TokenType.TYPE, "usize": TokenType.TYPE,
            "f32": TokenType.TYPE, "f64": TokenType.TYPE,
            "bool": TokenType.TYPE, "char": TokenType.TYPE, "str": TokenType.TYPE,
            "String": TokenType.TYPE, "Vec": TokenType.TYPE, "Option": TokenType.TYPE,
            "Result": TokenType.TYPE, "Box": TokenType.TYPE, "Rc": TokenType.TYPE, "Arc": TokenType.TYPE,
            # Constants
            "true": TokenType.CONSTANT, "false": TokenType.CONSTANT,
            # Special
            "self": TokenType.SPECIAL, "Self": TokenType.SPECIAL,
        },
        Language.JAVASCRIPT: {
            # Keywords
            "function": TokenType.KEYWORD, "const": TokenType.KEYWORD, "let": TokenType.KEYWORD,
            "var": TokenType.KEYWORD, "class": TokenType.KEYWORD, "extends": TokenType.KEYWORD,
            "if": TokenType.KEYWORD, "else": TokenType.KEYWORD,
            "for": TokenType.KEYWORD, "while": TokenType.KEYWORD, "do": TokenType.KEYWORD,
            "switch": TokenType.KEYWORD, "case": TokenType.KEYWORD, "default": TokenType.KEYWORD,
            "break": TokenType.KEYWORD, "continue": TokenType.KEYWORD, "return": TokenType.KEYWORD,
            "try": TokenType.KEYWORD, "catch": TokenType.KEYWORD, "finally": TokenType.KEYWORD,
            "throw": TokenType.KEYWORD, "async": TokenType.KEYWORD, "await": TokenType.KEYWORD,
            "import": TokenType.KEYWORD, "export": TokenType.KEYWORD, "from": TokenType.KEYWORD,
            "new": TokenType.KEYWORD, "delete": TokenType.KEYWORD, "typeof": TokenType.KEYWORD,
            "instanceof": TokenType.KEYWORD, "in": TokenType.KEYWORD, "of": TokenType.KEYWORD,
            "yield": TokenType.KEYWORD, "static": TokenType.KEYWORD, "get": TokenType.KEYWORD,
            "set": TokenType.KEYWORD,
            # Built-ins
            "console": TokenType.BUILTIN, "Math": TokenType.BUILTIN, "JSON": TokenType.BUILTIN,
            "Object": TokenType.BUILTIN, "Array": TokenType.BUILTIN, "Promise": TokenType.BUILTIN,
            "fetch": TokenType.BUILTIN, "setTimeout": TokenType.BUILTIN, "setInterval": TokenType.BUILTIN,
            # Types
            "String": TokenType.TYPE, "Number": TokenType.TYPE, "Boolean": TokenType.TYPE,
            "Symbol": TokenType.TYPE, "BigInt": TokenType.TYPE,
            "Map": TokenType.TYPE, "Set": TokenType.TYPE, "WeakMap": TokenType.TYPE,
            "WeakSet": TokenType.TYPE, "Date": TokenType.TYPE, "RegExp": TokenType.TYPE,
            "Error": TokenType.TYPE, "TypeError": TokenType.TYPE, "SyntaxError": TokenType.TYPE,
            # Constants
            "null": TokenType.CONSTANT, "undefined": TokenType.CONSTANT,
            "true": TokenType.CONSTANT, "false": TokenType.CONSTANT,
            "NaN": TokenType.CONSTANT, "Infinity": TokenType.CONSTANT,
            # Special
            "this": TokenType.SPECIAL, "super": TokenType.SPECIAL,
        },
        Language.GO: {
            # Keywords
            "func": TokenType.KEYWORD, "var": TokenType.KEYWORD, "const": TokenType.KEYWORD,
            "type": TokenType.KEYWORD, "struct": TokenType.KEYWORD, "interface": TokenType.KEYWORD,
            "package": TokenType.KEYWORD, "import": TokenType.KEYWORD,
            "if": TokenType.KEYWORD, "else": TokenType.KEYWORD,
            "for": TokenType.KEYWORD, "range": TokenType.KEYWORD,
            "switch": TokenType.KEYWORD, "case": TokenType.KEYWORD, "default": TokenType.KEYWORD,
            "select": TokenType.KEYWORD, "fallthrough": TokenType.KEYWORD,
            "break": TokenType.KEYWORD, "continue": TokenType.KEYWORD, "return": TokenType.KEYWORD,
            "defer": TokenType.KEYWORD, "go": TokenType.KEYWORD,
            "chan": TokenType.KEYWORD, "map": TokenType.KEYWORD,
            # Built-ins
            "make": TokenType.BUILTIN, "new": TokenType.BUILTIN, "len": TokenType.BUILTIN,
            "cap": TokenType.BUILTIN, "append": TokenType.BUILTIN, "copy": TokenType.BUILTIN,
            "delete": TokenType.BUILTIN, "panic": TokenType.BUILTIN, "recover": TokenType.BUILTIN,
            "print": TokenType.BUILTIN, "println": TokenType.BUILTIN,
            # Types
            "int": TokenType.TYPE, "int8": TokenType.TYPE, "int16": TokenType.TYPE,
            "int32": TokenType.TYPE, "int64": TokenType.TYPE,
            "uint": TokenType.TYPE, "uint8": TokenType.TYPE, "uint16": TokenType.TYPE,
            "uint32": TokenType.TYPE, "uint64": TokenType.TYPE,
            "float32": TokenType.TYPE, "float64": TokenType.TYPE,
            "complex64": TokenType.TYPE, "complex128": TokenType.TYPE,
            "string": TokenType.TYPE, "bool": TokenType.TYPE, "byte": TokenType.TYPE,
            "rune": TokenType.TYPE, "error": TokenType.TYPE,
            # Constants
            "nil": TokenType.CONSTANT, "true": TokenType.CONSTANT, "false": TokenType.CONSTANT,
            "iota": TokenType.CONSTANT,
        },
        Language.SQL: {
            # Keywords (uppercase by convention)
            "SELECT": TokenType.KEYWORD, "FROM": TokenType.KEYWORD, "WHERE": TokenType.KEYWORD,
            "AND": TokenType.KEYWORD, "OR": TokenType.KEYWORD, "NOT": TokenType.KEYWORD,
            "IN": TokenType.KEYWORD, "LIKE": TokenType.KEYWORD, "BETWEEN": TokenType.KEYWORD,
            "JOIN": TokenType.KEYWORD, "LEFT": TokenType.KEYWORD, "RIGHT": TokenType.KEYWORD,
            "INNER": TokenType.KEYWORD, "OUTER": TokenType.KEYWORD, "FULL": TokenType.KEYWORD,
            "ON": TokenType.KEYWORD, "USING": TokenType.KEYWORD,
            "GROUP": TokenType.KEYWORD, "BY": TokenType.KEYWORD, "ORDER": TokenType.KEYWORD,
            "ASC": TokenType.KEYWORD, "DESC": TokenType.KEYWORD, "HAVING": TokenType.KEYWORD,
            "LIMIT": TokenType.KEYWORD, "OFFSET": TokenType.KEYWORD,
            "INSERT": TokenType.KEYWORD, "INTO": TokenType.KEYWORD, "VALUES": TokenType.KEYWORD,
            "UPDATE": TokenType.KEYWORD, "SET": TokenType.KEYWORD, "DELETE": TokenType.KEYWORD,
            "CREATE": TokenType.KEYWORD, "TABLE": TokenType.KEYWORD, "DROP": TokenType.KEYWORD,
            "ALTER": TokenType.KEYWORD, "ADD": TokenType.KEYWORD, "COLUMN": TokenType.KEYWORD,
            "INDEX": TokenType.KEYWORD, "PRIMARY": TokenType.KEYWORD, "KEY": TokenType.KEYWORD,
            "FOREIGN": TokenType.KEYWORD, "REFERENCES": TokenType.KEYWORD,
            "CONSTRAINT": TokenType.KEYWORD, "UNIQUE": TokenType.KEYWORD, "CHECK": TokenType.KEYWORD,
            "DEFAULT": TokenType.KEYWORD, "AS": TokenType.KEYWORD, "DISTINCT": TokenType.KEYWORD,
            "UNION": TokenType.KEYWORD, "ALL": TokenType.KEYWORD, "EXCEPT": TokenType.KEYWORD,
            "INTERSECT": TokenType.KEYWORD, "EXISTS": TokenType.KEYWORD,
            "CASE": TokenType.KEYWORD, "WHEN": TokenType.KEYWORD, "THEN": TokenType.KEYWORD,
            "ELSE": TokenType.KEYWORD, "END": TokenType.KEYWORD,
            # Types
            "INT": TokenType.TYPE, "INTEGER": TokenType.TYPE, "BIGINT": TokenType.TYPE,
            "SMALLINT": TokenType.TYPE, "TINYINT": TokenType.TYPE,
            "VARCHAR": TokenType.TYPE, "CHAR": TokenType.TYPE, "TEXT": TokenType.TYPE,
            "BOOLEAN": TokenType.TYPE, "BOOL": TokenType.TYPE,
            "DATE": TokenType.TYPE, "TIME": TokenType.TYPE, "TIMESTAMP": TokenType.TYPE,
            "DATETIME": TokenType.TYPE, "INTERVAL": TokenType.TYPE,
            "FLOAT": TokenType.TYPE, "DOUBLE": TokenType.TYPE, "DECIMAL": TokenType.TYPE,
            "NUMERIC": TokenType.TYPE, "REAL": TokenType.TYPE,
            "BLOB": TokenType.TYPE, "BYTEA": TokenType.TYPE,
            "JSON": TokenType.TYPE, "JSONB": TokenType.TYPE,
            "UUID": TokenType.TYPE, "SERIAL": TokenType.TYPE,
            # Functions
            "COUNT": TokenType.BUILTIN, "SUM": TokenType.BUILTIN, "AVG": TokenType.BUILTIN,
            "MAX": TokenType.BUILTIN, "MIN": TokenType.BUILTIN,
            "COALESCE": TokenType.BUILTIN, "NULLIF": TokenType.BUILTIN,
            "UPPER": TokenType.BUILTIN, "LOWER": TokenType.BUILTIN,
            "CONCAT": TokenType.BUILTIN, "LENGTH": TokenType.BUILTIN,
            "SUBSTRING": TokenType.BUILTIN, "TRIM": TokenType.BUILTIN,
            "NOW": TokenType.BUILTIN, "CURRENT_DATE": TokenType.BUILTIN,
            "CURRENT_TIMESTAMP": TokenType.BUILTIN,
            # Constants
            "NULL": TokenType.CONSTANT, "TRUE": TokenType.CONSTANT, "FALSE": TokenType.CONSTANT,
        },
    }
    
    def __init__(self):
        self.encoder = BrailleCodeEncoder()
        
    def get_highlight_markers(self, token_type: TokenType) -> Tuple[str, str]:
        """Get braille highlight markers for token type"""
        return self.HIGHLIGHT_PATTERNS.get(token_type, ("", ""))
        
    def tokenize(self, text: str, language: Language, line_num: int = 0) -> List[BrailleToken]:
        """Tokenize a line of code"""
        tokens = []
        patterns = self.LANGUAGE_PATTERNS.get(language, {})
        
        # Regex patterns for different token types
        token_patterns = [
            (r'#.*$', TokenType.COMMENT),           # Python/Shell comments
            (r'//.*$', TokenType.COMMENT),          # C-style line comments
            (r'--.*$', TokenType.COMMENT),          # SQL comments
            (r'"(?:[^"\\]|\\.)*"', TokenType.STRING),  # Double-quoted strings
            (r"'(?:[^'\\]|\\.)*'", TokenType.STRING),  # Single-quoted strings
            (r'`[^`]*`', TokenType.STRING),         # Backtick strings
            (r'\b\d+\.?\d*\b', TokenType.NUMBER),   # Numbers
            (r'@\w+', TokenType.DECORATOR),         # Decorators
            (r'[+\-*/%=<>!&|^~]+', TokenType.OPERATOR),  # Operators
            (r'[(){}\[\],;:.]', TokenType.PUNCTUATION),  # Punctuation
            (r'\b\w+\b', TokenType.IDENTIFIER),     # Identifiers
            (r'\s+', TokenType.WHITESPACE),         # Whitespace
        ]
        
        pos = 0
        while pos < len(text):
            best_match = None
            best_type = None
            
            for pattern, token_type in token_patterns:
                match = re.match(pattern, text[pos:])
                if match:
                    if best_match is None or len(match.group()) > len(best_match.group()):
                        best_match = match
                        best_type = token_type
                        
            if best_match:
                matched_text = best_match.group()
                
                # Check if it's a keyword
                if best_type == TokenType.IDENTIFIER:
                    if matched_text in patterns:
                        best_type = patterns[matched_text]
                    # Check for function definitions
                    elif pos > 0 and text[pos-1:pos] in (' ', '\t'):
                        prev_word_match = re.search(r'(\w+)\s*$', text[:pos])
                        if prev_word_match and prev_word_match.group(1) in ('def', 'fn', 'func', 'function'):
                            best_type = TokenType.FUNCTION
                        elif prev_word_match and prev_word_match.group(1) == 'class':
                            best_type = TokenType.CLASS
                            
                token = BrailleToken(
                    text=matched_text,
                    braille=self.encoder.encode(matched_text),
                    token_type=best_type,
                    start=pos,
                    end=pos + len(matched_text),
                    line=line_num
                )
                tokens.append(token)
                pos += len(matched_text)
            else:
                # Single character fallback
                char = text[pos]
                token = BrailleToken(
                    text=char,
                    braille=self.encoder.encode(char),
                    token_type=TokenType.IDENTIFIER,
                    start=pos,
                    end=pos + 1,
                    line=line_num
                )
                tokens.append(token)
                pos += 1
                
        return tokens
        
    def highlight_line(self, text: str, language: Language, line_num: int = 0) -> str:
        """Highlight a line of code and return as braille with markers"""
        tokens = self.tokenize(text, language, line_num)
        result = []
        
        for token in tokens:
            if token.token_type == TokenType.WHITESPACE:
                result.append(token.braille)
            else:
                prefix, suffix = self.get_highlight_markers(token.token_type)
                result.append(f"{prefix}{token.braille}{suffix}")
                
        return "".join(result)
        
    def highlight_code(self, code: str, language: Language) -> str:
        """Highlight full code block"""
        lines = code.split('\n')
        highlighted = []
        
        for i, line in enumerate(lines):
            highlighted.append(self.highlight_line(line, language, i))
            
        return "\n".join(highlighted)
        
    def get_token_at_position(self, text: str, language: Language, col: int) -> Optional[BrailleToken]:
        """Get token at a specific column position"""
        tokens = self.tokenize(text, language)
        
        for token in tokens:
            if token.start <= col < token.end:
                return token
                
        return None
        
    def get_color_scheme(self) -> Dict[TokenType, str]:
        """Get color scheme for visual display (maps to CSS colors)"""
        return {
            TokenType.KEYWORD: "#569CD6",      # Blue
            TokenType.BUILTIN: "#DCDCAA",      # Yellow
            TokenType.TYPE: "#4EC9B0",         # Teal
            TokenType.CONSTANT: "#569CD6",     # Blue
            TokenType.STRING: "#CE9178",       # Orange
            TokenType.NUMBER: "#B5CEA8",       # Light green
            TokenType.COMMENT: "#6A9955",      # Green
            TokenType.OPERATOR: "#D4D4D4",     # Light gray
            TokenType.PUNCTUATION: "#D4D4D4",  # Light gray
            TokenType.IDENTIFIER: "#9CDCFE",   # Light blue
            TokenType.FUNCTION: "#DCDCAA",     # Yellow
            TokenType.CLASS: "#4EC9B0",        # Teal
            TokenType.DECORATOR: "#C586C0",    # Purple
            TokenType.SPECIAL: "#C586C0",      # Purple
            TokenType.ERROR: "#F44747",        # Red
            TokenType.WHITESPACE: "transparent",
        }
