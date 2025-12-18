"""
SAL 8-Dot Braille IDE Code Completion Module

Intelligent braille autocompletion with language awareness.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_code import BrailleCodeEncoder, Language, get_language_keywords


class CompletionKind(str, Enum):
    """Types of completion items"""
    KEYWORD = "keyword"
    FUNCTION = "function"
    VARIABLE = "variable"
    CLASS = "class"
    MODULE = "module"
    PROPERTY = "property"
    METHOD = "method"
    CONSTANT = "constant"
    TYPE = "type"
    SNIPPET = "snippet"
    OPERATOR = "operator"


@dataclass
class CompletionItem:
    """A code completion suggestion"""
    label: str                      # Display text
    braille: str                    # Braille representation
    kind: CompletionKind
    detail: Optional[str] = None    # Additional detail
    documentation: Optional[str] = None
    insert_text: Optional[str] = None
    score: float = 0.0              # Relevance score
    
    @property
    def braille_icon(self) -> str:
        """Get braille icon for completion kind"""
        icons = {
            CompletionKind.KEYWORD: "⠅",
            CompletionKind.FUNCTION: "⠋",
            CompletionKind.VARIABLE: "⠧",
            CompletionKind.CLASS: "⠉",
            CompletionKind.MODULE: "⠍",
            CompletionKind.PROPERTY: "⠏",
            CompletionKind.METHOD: "⠍⠞",
            CompletionKind.CONSTANT: "⠉⠕",
            CompletionKind.TYPE: "⠞",
            CompletionKind.SNIPPET: "⠎⠝",
            CompletionKind.OPERATOR: "⠕",
        }
        return icons.get(self.kind, "⠶")
        
    @property
    def display(self) -> str:
        """Get display string with icon"""
        return f"{self.braille_icon} {self.braille}"


@dataclass
class CompletionContext:
    """Context for code completion"""
    line: str
    col: int
    prefix: str              # Text before cursor on current "word"
    language: Language
    line_num: int = 0
    file_content: str = ""   # Full file for context


class BrailleCodeCompletion:
    """
    Code completion engine that operates in braille space.
    
    Features:
    - Language-aware keyword completion
    - Symbol completion from current file
    - Snippet completion
    - Fuzzy matching
    """
    
    # Common snippets by language (as SAL specified)
    SNIPPETS: Dict[Language, List[Tuple[str, str, str]]] = {
        Language.PYTHON: [
            ("def", "def ${1:name}(${2:args}):\n    ${0:pass}", "Function definition"),
            ("class", "class ${1:Name}:\n    def __init__(self):\n        ${0:pass}", "Class definition"),
            ("if", "if ${1:condition}:\n    ${0:pass}", "If statement"),
            ("for", "for ${1:item} in ${2:iterable}:\n    ${0:pass}", "For loop"),
            ("while", "while ${1:condition}:\n    ${0:pass}", "While loop"),
            ("try", "try:\n    ${1:pass}\nexcept ${2:Exception} as e:\n    ${0:pass}", "Try/except"),
            ("with", "with ${1:expr} as ${2:var}:\n    ${0:pass}", "With statement"),
            ("async", "async def ${1:name}(${2:args}):\n    ${0:pass}", "Async function"),
            ("ifmain", 'if __name__ == "__main__":\n    ${0:pass}', "Main guard"),
            ("@prop", "@property\ndef ${1:name}(self):\n    return self._${1:name}", "Property decorator"),
        ],
        Language.RUST: [
            ("fn", "fn ${1:name}(${2:args}) ${3:-> Type }{\n    ${0:todo!()}\n}", "Function"),
            ("struct", "struct ${1:Name} {\n    ${0:field}: Type,\n}", "Struct"),
            ("impl", "impl ${1:Type} {\n    ${0}\n}", "Implementation"),
            ("match", "match ${1:expr} {\n    ${2:pattern} => ${0:todo!()},\n}", "Match expression"),
            ("if", "if ${1:condition} {\n    ${0:todo!()}\n}", "If statement"),
            ("for", "for ${1:item} in ${2:iter} {\n    ${0:todo!()}\n}", "For loop"),
            ("let", "let ${1:name}: ${2:Type} = ${0:value};", "Let binding"),
            ("letmut", "let mut ${1:name}: ${2:Type} = ${0:value};", "Mutable let binding"),
            ("test", "#[test]\nfn ${1:test_name}() {\n    ${0:todo!()}\n}", "Test function"),
        ],
        Language.JAVASCRIPT: [
            ("fn", "function ${1:name}(${2:args}) {\n    ${0}\n}", "Function"),
            ("arrow", "const ${1:name} = (${2:args}) => {\n    ${0}\n};", "Arrow function"),
            ("class", "class ${1:Name} {\n    constructor(${2:args}) {\n        ${0}\n    }\n}", "Class"),
            ("if", "if (${1:condition}) {\n    ${0}\n}", "If statement"),
            ("for", "for (let ${1:i} = 0; ${1:i} < ${2:length}; ${1:i}++) {\n    ${0}\n}", "For loop"),
            ("foreach", "${1:array}.forEach((${2:item}) => {\n    ${0}\n});", "ForEach"),
            ("map", "${1:array}.map((${2:item}) => ${0});", "Map"),
            ("async", "async function ${1:name}(${2:args}) {\n    ${0}\n}", "Async function"),
            ("try", "try {\n    ${1}\n} catch (${2:error}) {\n    ${0}\n}", "Try/catch"),
            ("promise", "new Promise((resolve, reject) => {\n    ${0}\n});", "Promise"),
        ],
        Language.GO: [
            ("fn", "func ${1:name}(${2:args}) ${3:returnType} {\n    ${0}\n}", "Function"),
            ("struct", "type ${1:Name} struct {\n    ${0:Field} Type\n}", "Struct"),
            ("interface", "type ${1:Name} interface {\n    ${0:Method}() Type\n}", "Interface"),
            ("if", "if ${1:condition} {\n    ${0}\n}", "If statement"),
            ("iferr", "if err != nil {\n    ${0:return err}\n}", "Error check"),
            ("for", "for ${1:i} := 0; ${1:i} < ${2:n}; ${1:i}++ {\n    ${0}\n}", "For loop"),
            ("forrange", "for ${1:i}, ${2:v} := range ${3:slice} {\n    ${0}\n}", "For range"),
            ("switch", "switch ${1:expr} {\ncase ${2:val}:\n    ${0}\ndefault:\n}", "Switch"),
            ("go", "go func() {\n    ${0}\n}()", "Goroutine"),
            ("defer", "defer ${0:func()}", "Defer"),
        ],
        Language.SQL: [
            ("select", "SELECT ${1:columns}\nFROM ${2:table}\nWHERE ${0:condition};", "Select query"),
            ("insert", "INSERT INTO ${1:table} (${2:columns})\nVALUES (${0:values});", "Insert"),
            ("update", "UPDATE ${1:table}\nSET ${2:column} = ${3:value}\nWHERE ${0:condition};", "Update"),
            ("delete", "DELETE FROM ${1:table}\nWHERE ${0:condition};", "Delete"),
            ("create", "CREATE TABLE ${1:name} (\n    ${2:id} SERIAL PRIMARY KEY,\n    ${0:column} TYPE\n);", "Create table"),
            ("join", "SELECT ${1:*}\nFROM ${2:table1}\nJOIN ${3:table2} ON ${0:condition};", "Join"),
            ("leftjoin", "LEFT JOIN ${1:table} ON ${0:condition}", "Left join"),
            ("group", "GROUP BY ${1:column}\nHAVING ${0:condition}", "Group by"),
            ("order", "ORDER BY ${1:column} ${0:ASC}", "Order by"),
            ("cte", "WITH ${1:name} AS (\n    ${2:SELECT * FROM table}\n)\nSELECT * FROM ${1:name}${0};", "CTE"),
        ],
    }
    
    def __init__(self):
        self.encoder = BrailleCodeEncoder()
        self.user_symbols: Dict[str, CompletionKind] = {}
        
    def get_completions(self, context: CompletionContext, max_results: int = 20) -> List[CompletionItem]:
        """Get completion suggestions for current context"""
        completions = []
        prefix = context.prefix.lower()
        
        # 1. Add keyword completions
        keywords = get_language_keywords(context.language.value)
        for kw in keywords:
            if self._matches(kw.text, prefix):
                kind = self._category_to_kind(kw.category)
                completions.append(CompletionItem(
                    label=kw.text,
                    braille=kw.braille,
                    kind=kind,
                    detail=f"{context.language.value} {kw.category}",
                    score=self._score(kw.text, prefix)
                ))
                
        # 2. Add snippet completions
        snippets = self.SNIPPETS.get(context.language, [])
        for trigger, body, description in snippets:
            if self._matches(trigger, prefix):
                completions.append(CompletionItem(
                    label=trigger,
                    braille=self.encoder.encode(trigger),
                    kind=CompletionKind.SNIPPET,
                    detail=description,
                    insert_text=body,
                    score=self._score(trigger, prefix) + 0.1  # Boost snippets
                ))
                
        # 3. Add symbol completions from file content
        if context.file_content:
            symbols = self._extract_symbols(context.file_content, context.language)
            for symbol, kind in symbols.items():
                if self._matches(symbol, prefix) and symbol != context.prefix:
                    completions.append(CompletionItem(
                        label=symbol,
                        braille=self.encoder.encode(symbol),
                        kind=kind,
                        detail="Local symbol",
                        score=self._score(symbol, prefix)
                    ))
                    
        # 4. Add user-defined symbols
        for symbol, kind in self.user_symbols.items():
            if self._matches(symbol, prefix):
                completions.append(CompletionItem(
                    label=symbol,
                    braille=self.encoder.encode(symbol),
                    kind=kind,
                    detail="User symbol",
                    score=self._score(symbol, prefix)
                ))
                
        # Sort by score and limit
        completions.sort(key=lambda x: -x.score)
        return completions[:max_results]
        
    def _matches(self, label: str, prefix: str) -> bool:
        """Check if label matches prefix (fuzzy)"""
        if not prefix:
            return True
        label_lower = label.lower()
        prefix_lower = prefix.lower()
        
        # Exact prefix match
        if label_lower.startswith(prefix_lower):
            return True
            
        # Fuzzy match (all chars in sequence)
        j = 0
        for char in label_lower:
            if j < len(prefix_lower) and char == prefix_lower[j]:
                j += 1
        return j == len(prefix_lower)
        
    def _score(self, label: str, prefix: str) -> float:
        """Calculate match score"""
        if not prefix:
            return 0.5
            
        label_lower = label.lower()
        prefix_lower = prefix.lower()
        
        # Exact match
        if label_lower == prefix_lower:
            return 1.0
            
        # Prefix match
        if label_lower.startswith(prefix_lower):
            return 0.9 + (len(prefix) / len(label)) * 0.1
            
        # Fuzzy match score
        j = 0
        for i, char in enumerate(label_lower):
            if j < len(prefix_lower) and char == prefix_lower[j]:
                j += 1
        if j == len(prefix_lower):
            return 0.5 + (len(prefix) / len(label)) * 0.3
            
        return 0.0
        
    def _category_to_kind(self, category: str) -> CompletionKind:
        """Convert keyword category to completion kind"""
        mapping = {
            "keyword": CompletionKind.KEYWORD,
            "builtin": CompletionKind.FUNCTION,
            "type": CompletionKind.TYPE,
            "constant": CompletionKind.CONSTANT,
            "special": CompletionKind.VARIABLE,
            "function": CompletionKind.FUNCTION,
        }
        return mapping.get(category, CompletionKind.KEYWORD)
        
    def _extract_symbols(self, content: str, language: Language) -> Dict[str, CompletionKind]:
        """Extract symbols from file content"""
        symbols = {}
        
        # Pattern for function/method definitions
        if language == Language.PYTHON:
            # Functions
            for match in re.finditer(r'def\s+(\w+)', content):
                symbols[match.group(1)] = CompletionKind.FUNCTION
            # Classes
            for match in re.finditer(r'class\s+(\w+)', content):
                symbols[match.group(1)] = CompletionKind.CLASS
            # Variables (simple assignment)
            for match in re.finditer(r'^(\w+)\s*=', content, re.MULTILINE):
                name = match.group(1)
                if name not in symbols and not name.startswith('_'):
                    symbols[name] = CompletionKind.VARIABLE
                    
        elif language == Language.RUST:
            for match in re.finditer(r'fn\s+(\w+)', content):
                symbols[match.group(1)] = CompletionKind.FUNCTION
            for match in re.finditer(r'struct\s+(\w+)', content):
                symbols[match.group(1)] = CompletionKind.CLASS
            for match in re.finditer(r'let\s+(?:mut\s+)?(\w+)', content):
                symbols[match.group(1)] = CompletionKind.VARIABLE
                
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            for match in re.finditer(r'function\s+(\w+)', content):
                symbols[match.group(1)] = CompletionKind.FUNCTION
            for match in re.finditer(r'class\s+(\w+)', content):
                symbols[match.group(1)] = CompletionKind.CLASS
            for match in re.finditer(r'(?:const|let|var)\s+(\w+)', content):
                symbols[match.group(1)] = CompletionKind.VARIABLE
                
        elif language == Language.GO:
            for match in re.finditer(r'func\s+(?:\([^)]+\)\s+)?(\w+)', content):
                symbols[match.group(1)] = CompletionKind.FUNCTION
            for match in re.finditer(r'type\s+(\w+)\s+struct', content):
                symbols[match.group(1)] = CompletionKind.CLASS
            for match in re.finditer(r'(?:var|const)\s+(\w+)', content):
                symbols[match.group(1)] = CompletionKind.VARIABLE
                
        return symbols
        
    def add_user_symbol(self, symbol: str, kind: CompletionKind):
        """Add a user-defined symbol for completion"""
        self.user_symbols[symbol] = kind
        
    def get_context_from_line(self, line: str, col: int, language: Language) -> CompletionContext:
        """Extract completion context from cursor position"""
        # Get prefix (word before cursor)
        prefix_match = re.search(r'(\w*)$', line[:col])
        prefix = prefix_match.group(1) if prefix_match else ""
        
        return CompletionContext(
            line=line,
            col=col,
            prefix=prefix,
            language=language
        )
        
    def render_completion_list(self, completions: List[CompletionItem], selected_index: int = 0) -> str:
        """Render completion list in braille"""
        if not completions:
            return self.encoder.encode("No completions")
            
        lines = []
        header = "⠿⠿ " + self.encoder.encode("Completions") + " ⠿⠿"
        lines.append(header)
        lines.append("⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒")
        
        for i, item in enumerate(completions[:10]):  # Show max 10
            selector = "⠕" if i == selected_index else "⠀"
            detail = f" ⠤ {self.encoder.encode(item.detail)}" if item.detail else ""
            lines.append(f"{selector} {item.display}{detail}")
            
        lines.append("⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒")
        
        return "\n".join(lines)
        
    def expand_snippet(self, snippet: str, placeholders: Dict[str, str] = None) -> str:
        """Expand a snippet template"""
        if placeholders is None:
            placeholders = {}
            
        result = snippet
        
        # Replace numbered placeholders ${N:default}
        def replace_placeholder(match):
            num = match.group(1)
            default = match.group(2) if match.group(2) else ""
            return placeholders.get(num, default)
            
        result = re.sub(r'\$\{(\d+)(?::([^}]*))?\}', replace_placeholder, result)
        
        # Replace $N placeholders
        result = re.sub(r'\$(\d+)', lambda m: placeholders.get(m.group(1), ""), result)
        
        return result
