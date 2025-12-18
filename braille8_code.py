"""
SAL 8-Dot Braille Programming Language Module

SAL thinks and codes in 8-dot braille. This module provides complete
8-dot braille mappings for all major programming languages:
- Python, Rust, Go, JavaScript/TypeScript, Java, SQL, C/C++, Ruby, etc.

8-dot braille (U+2800-U+28FF) can represent all 256 ASCII characters,
making it perfect for code representation.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Base braille codepoint
BRAILLE_BASE = 0x2800


class Language(str, Enum):
    """Supported programming languages"""
    PYTHON = "python"
    RUST = "rust"
    GO = "go"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    SQL = "sql"
    C = "c"
    CPP = "cpp"
    RUBY = "ruby"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SHELL = "shell"


# Complete ASCII to 8-dot braille mapping (NABCC-based with extensions)
ASCII_TO_BRAILLE8: Dict[str, str] = {
    # Lowercase letters
    'a': '⠁', 'b': '⠃', 'c': '⠉', 'd': '⠙', 'e': '⠑', 'f': '⠋',
    'g': '⠛', 'h': '⠓', 'i': '⠊', 'j': '⠚', 'k': '⠅', 'l': '⠇',
    'm': '⠍', 'n': '⠝', 'o': '⠕', 'p': '⠏', 'q': '⠟', 'r': '⠗',
    's': '⠎', 't': '⠞', 'u': '⠥', 'v': '⠧', 'w': '⠺', 'x': '⠭',
    'y': '⠽', 'z': '⠵',
    
    # Uppercase letters (add dot 7 = 0x40)
    'A': '⡁', 'B': '⡃', 'C': '⡉', 'D': '⡙', 'E': '⡑', 'F': '⡋',
    'G': '⡛', 'H': '⡓', 'I': '⡊', 'J': '⡚', 'K': '⡅', 'L': '⡇',
    'M': '⡍', 'N': '⡝', 'O': '⡕', 'P': '⡏', 'Q': '⡟', 'R': '⡗',
    'S': '⡎', 'T': '⡞', 'U': '⡥', 'V': '⡧', 'W': '⡺', 'X': '⡭',
    'Y': '⡽', 'Z': '⡵',
    
    # Numbers (add dot 8 = 0x80)
    '0': '⢚', '1': '⢁', '2': '⢃', '3': '⢉', '4': '⢙', '5': '⢑',
    '6': '⢋', '7': '⢛', '8': '⢓', '9': '⢊',
    
    # Programming punctuation (critical for code!)
    ' ': '⠀',      # Space
    '.': '⠲',      # Dot/period
    ',': '⠂',      # Comma
    ':': '⠒',      # Colon
    ';': '⠆',      # Semicolon
    '!': '⠖',      # Exclamation
    '?': '⠦',      # Question
    "'": '⠄',      # Single quote
    '"': '⠐⠂',    # Double quote (2-cell)
    '`': '⠈',      # Backtick
    
    # Brackets and parentheses
    '(': '⠐⠣',    # Open paren
    ')': '⠐⠜',    # Close paren
    '[': '⠨⠣',    # Open bracket
    ']': '⠨⠜',    # Close bracket
    '{': '⠸⠣',    # Open brace
    '}': '⠸⠜',    # Close brace
    '<': '⠐⠪',    # Less than
    '>': '⠐⠕',    # Greater than
    
    # Operators
    '+': '⠐⠖',    # Plus
    '-': '⠤',      # Minus/hyphen
    '*': '⠐⠔',    # Asterisk/multiply
    '/': '⠸⠌',    # Forward slash
    '\\': '⠸⠡',   # Backslash
    '=': '⠐⠶',    # Equals
    '%': '⠨⠴',    # Percent
    '&': '⠈⠯',    # Ampersand
    '|': '⠸⠳',    # Pipe
    '^': '⠈⠢',    # Caret
    '~': '⠈⠔',    # Tilde
    
    # Special characters
    '@': '⠈⠁',    # At sign
    '#': '⠨⠼',    # Hash/pound
    '$': '⠈⠎',    # Dollar
    '_': '⠨⠤',    # Underscore
    '\n': '⠀',    # Newline (space in braille)
    '\t': '⠀⠀',  # Tab (double space)
}

# Reverse mapping
BRAILLE8_TO_ASCII: Dict[str, str] = {v: k for k, v in ASCII_TO_BRAILLE8.items()}


@dataclass
class BrailleKeyword:
    """A programming keyword with its braille representation"""
    text: str
    braille: str
    language: Language
    category: str  # keyword, builtin, type, operator, etc.


class BrailleCodeEncoder:
    """
    Encodes programming code to 8-dot braille.
    SAL uses this to think about code in braille.
    """
    
    def __init__(self):
        self.keywords = self._build_keyword_database()
        
    def _build_keyword_database(self) -> Dict[Language, List[BrailleKeyword]]:
        """Build database of programming keywords in braille"""
        keywords = {lang: [] for lang in Language}
        
        # Python keywords
        python_keywords = [
            # Control flow
            ("def", "keyword"), ("class", "keyword"), ("if", "keyword"),
            ("elif", "keyword"), ("else", "keyword"), ("for", "keyword"),
            ("while", "keyword"), ("try", "keyword"), ("except", "keyword"),
            ("finally", "keyword"), ("with", "keyword"), ("as", "keyword"),
            ("return", "keyword"), ("yield", "keyword"), ("raise", "keyword"),
            ("break", "keyword"), ("continue", "keyword"), ("pass", "keyword"),
            ("import", "keyword"), ("from", "keyword"), ("async", "keyword"),
            ("await", "keyword"), ("lambda", "keyword"),
            # Built-ins
            ("print", "builtin"), ("len", "builtin"), ("range", "builtin"),
            ("str", "type"), ("int", "type"), ("float", "type"),
            ("list", "type"), ("dict", "type"), ("set", "type"),
            ("tuple", "type"), ("bool", "type"), ("None", "constant"),
            ("True", "constant"), ("False", "constant"), ("self", "special"),
        ]
        for kw, cat in python_keywords:
            keywords[Language.PYTHON].append(BrailleKeyword(
                text=kw, braille=self.encode(kw), language=Language.PYTHON, category=cat
            ))
            
        # Rust keywords
        rust_keywords = [
            ("fn", "keyword"), ("let", "keyword"), ("mut", "keyword"),
            ("const", "keyword"), ("static", "keyword"), ("struct", "keyword"),
            ("enum", "keyword"), ("impl", "keyword"), ("trait", "keyword"),
            ("pub", "keyword"), ("mod", "keyword"), ("use", "keyword"),
            ("match", "keyword"), ("if", "keyword"), ("else", "keyword"),
            ("loop", "keyword"), ("while", "keyword"), ("for", "keyword"),
            ("in", "keyword"), ("return", "keyword"), ("async", "keyword"),
            ("await", "keyword"), ("move", "keyword"), ("ref", "keyword"),
            ("self", "special"), ("Self", "special"), ("where", "keyword"),
            # Types
            ("i32", "type"), ("i64", "type"), ("u32", "type"), ("u64", "type"),
            ("f32", "type"), ("f64", "type"), ("bool", "type"), ("char", "type"),
            ("String", "type"), ("Vec", "type"), ("Option", "type"),
            ("Result", "type"), ("Box", "type"), ("Rc", "type"), ("Arc", "type"),
        ]
        for kw, cat in rust_keywords:
            keywords[Language.RUST].append(BrailleKeyword(
                text=kw, braille=self.encode(kw), language=Language.RUST, category=cat
            ))
            
        # Go keywords
        go_keywords = [
            ("func", "keyword"), ("var", "keyword"), ("const", "keyword"),
            ("type", "keyword"), ("struct", "keyword"), ("interface", "keyword"),
            ("package", "keyword"), ("import", "keyword"), ("if", "keyword"),
            ("else", "keyword"), ("for", "keyword"), ("range", "keyword"),
            ("switch", "keyword"), ("case", "keyword"), ("default", "keyword"),
            ("return", "keyword"), ("defer", "keyword"), ("go", "keyword"),
            ("chan", "keyword"), ("select", "keyword"), ("make", "builtin"),
            ("new", "builtin"), ("len", "builtin"), ("cap", "builtin"),
            ("append", "builtin"), ("copy", "builtin"), ("delete", "builtin"),
            # Types
            ("int", "type"), ("int32", "type"), ("int64", "type"),
            ("uint", "type"), ("float32", "type"), ("float64", "type"),
            ("string", "type"), ("bool", "type"), ("byte", "type"),
            ("error", "type"), ("nil", "constant"),
        ]
        for kw, cat in go_keywords:
            keywords[Language.GO].append(BrailleKeyword(
                text=kw, braille=self.encode(kw), language=Language.GO, category=cat
            ))
            
        # JavaScript/TypeScript keywords
        js_keywords = [
            ("function", "keyword"), ("const", "keyword"), ("let", "keyword"),
            ("var", "keyword"), ("class", "keyword"), ("extends", "keyword"),
            ("if", "keyword"), ("else", "keyword"), ("for", "keyword"),
            ("while", "keyword"), ("do", "keyword"), ("switch", "keyword"),
            ("case", "keyword"), ("break", "keyword"), ("continue", "keyword"),
            ("return", "keyword"), ("try", "keyword"), ("catch", "keyword"),
            ("finally", "keyword"), ("throw", "keyword"), ("async", "keyword"),
            ("await", "keyword"), ("import", "keyword"), ("export", "keyword"),
            ("default", "keyword"), ("new", "keyword"), ("this", "special"),
            ("super", "special"), ("typeof", "operator"), ("instanceof", "operator"),
            # Built-ins
            ("console", "builtin"), ("Array", "type"), ("Object", "type"),
            ("String", "type"), ("Number", "type"), ("Boolean", "type"),
            ("Promise", "type"), ("Map", "type"), ("Set", "type"),
            ("null", "constant"), ("undefined", "constant"), ("true", "constant"),
            ("false", "constant"),
        ]
        for kw, cat in js_keywords:
            keywords[Language.JAVASCRIPT].append(BrailleKeyword(
                text=kw, braille=self.encode(kw), language=Language.JAVASCRIPT, category=cat
            ))
            keywords[Language.TYPESCRIPT].append(BrailleKeyword(
                text=kw, braille=self.encode(kw), language=Language.TYPESCRIPT, category=cat
            ))
            
        # TypeScript additions
        ts_additions = [
            ("interface", "keyword"), ("type", "keyword"), ("enum", "keyword"),
            ("implements", "keyword"), ("public", "keyword"), ("private", "keyword"),
            ("protected", "keyword"), ("readonly", "keyword"), ("abstract", "keyword"),
            ("as", "keyword"), ("any", "type"), ("unknown", "type"),
            ("never", "type"), ("void", "type"),
        ]
        for kw, cat in ts_additions:
            keywords[Language.TYPESCRIPT].append(BrailleKeyword(
                text=kw, braille=self.encode(kw), language=Language.TYPESCRIPT, category=cat
            ))
            
        # Java keywords
        java_keywords = [
            ("public", "keyword"), ("private", "keyword"), ("protected", "keyword"),
            ("class", "keyword"), ("interface", "keyword"), ("extends", "keyword"),
            ("implements", "keyword"), ("abstract", "keyword"), ("final", "keyword"),
            ("static", "keyword"), ("void", "keyword"), ("return", "keyword"),
            ("if", "keyword"), ("else", "keyword"), ("for", "keyword"),
            ("while", "keyword"), ("do", "keyword"), ("switch", "keyword"),
            ("case", "keyword"), ("break", "keyword"), ("continue", "keyword"),
            ("try", "keyword"), ("catch", "keyword"), ("finally", "keyword"),
            ("throw", "keyword"), ("throws", "keyword"), ("new", "keyword"),
            ("this", "special"), ("super", "special"), ("import", "keyword"),
            ("package", "keyword"), ("synchronized", "keyword"),
            # Types
            ("int", "type"), ("long", "type"), ("float", "type"),
            ("double", "type"), ("boolean", "type"), ("char", "type"),
            ("byte", "type"), ("short", "type"), ("String", "type"),
            ("Integer", "type"), ("List", "type"), ("Map", "type"),
            ("null", "constant"), ("true", "constant"), ("false", "constant"),
        ]
        for kw, cat in java_keywords:
            keywords[Language.JAVA].append(BrailleKeyword(
                text=kw, braille=self.encode(kw), language=Language.JAVA, category=cat
            ))
            
        # SQL keywords
        sql_keywords = [
            ("SELECT", "keyword"), ("FROM", "keyword"), ("WHERE", "keyword"),
            ("AND", "keyword"), ("OR", "keyword"), ("NOT", "keyword"),
            ("IN", "keyword"), ("LIKE", "keyword"), ("BETWEEN", "keyword"),
            ("JOIN", "keyword"), ("LEFT", "keyword"), ("RIGHT", "keyword"),
            ("INNER", "keyword"), ("OUTER", "keyword"), ("ON", "keyword"),
            ("GROUP", "keyword"), ("BY", "keyword"), ("ORDER", "keyword"),
            ("ASC", "keyword"), ("DESC", "keyword"), ("HAVING", "keyword"),
            ("LIMIT", "keyword"), ("OFFSET", "keyword"), ("INSERT", "keyword"),
            ("INTO", "keyword"), ("VALUES", "keyword"), ("UPDATE", "keyword"),
            ("SET", "keyword"), ("DELETE", "keyword"), ("CREATE", "keyword"),
            ("TABLE", "keyword"), ("DROP", "keyword"), ("ALTER", "keyword"),
            ("INDEX", "keyword"), ("PRIMARY", "keyword"), ("KEY", "keyword"),
            ("FOREIGN", "keyword"), ("REFERENCES", "keyword"), ("NULL", "constant"),
            ("DEFAULT", "keyword"), ("UNIQUE", "keyword"), ("CHECK", "keyword"),
            # Types
            ("INT", "type"), ("INTEGER", "type"), ("VARCHAR", "type"),
            ("TEXT", "type"), ("BOOLEAN", "type"), ("DATE", "type"),
            ("TIMESTAMP", "type"), ("FLOAT", "type"), ("DECIMAL", "type"),
            # Functions
            ("COUNT", "function"), ("SUM", "function"), ("AVG", "function"),
            ("MAX", "function"), ("MIN", "function"), ("COALESCE", "function"),
        ]
        for kw, cat in sql_keywords:
            keywords[Language.SQL].append(BrailleKeyword(
                text=kw, braille=self.encode(kw), language=Language.SQL, category=cat
            ))
            
        return keywords
        
    def encode_char(self, char: str) -> str:
        """Encode a single character to 8-dot braille"""
        if char in ASCII_TO_BRAILLE8:
            return ASCII_TO_BRAILLE8[char]
        # Fallback: direct byte mapping
        code = ord(char)
        if code < 256:
            return chr(BRAILLE_BASE + code)
        return char
        
    def encode(self, text: str) -> str:
        """Encode text to 8-dot braille"""
        result = []
        i = 0
        while i < len(text):
            char = text[i]
            if char in ASCII_TO_BRAILLE8:
                result.append(ASCII_TO_BRAILLE8[char])
            else:
                result.append(self.encode_char(char))
            i += 1
        return ''.join(result)
        
    def decode(self, braille: str) -> str:
        """Decode 8-dot braille to text"""
        result = []
        i = 0
        while i < len(braille):
            # Check for multi-cell sequences
            if i + 1 < len(braille):
                two_cell = braille[i:i+2]
                if two_cell in BRAILLE8_TO_ASCII:
                    result.append(BRAILLE8_TO_ASCII[two_cell])
                    i += 2
                    continue
            
            char = braille[i]
            if char in BRAILLE8_TO_ASCII:
                result.append(BRAILLE8_TO_ASCII[char])
            else:
                # Direct byte mapping
                code = ord(char) - BRAILLE_BASE
                if 0 <= code < 256:
                    result.append(chr(code))
                else:
                    result.append(char)
            i += 1
        return ''.join(result)
        
    def encode_code(self, code: str, language: Language = None) -> str:
        """Encode programming code to 8-dot braille with language awareness"""
        return self.encode(code)
        
    def get_keyword_braille(self, keyword: str, language: Language) -> Optional[str]:
        """Get braille for a specific keyword in a language"""
        for kw in self.keywords.get(language, []):
            if kw.text == keyword:
                return kw.braille
        return None
        
    def generate_code_examples(self, language: Language) -> List[Tuple[str, str]]:
        """Generate code examples in both text and braille"""
        examples = []
        
        if language == Language.PYTHON:
            examples = [
                ('def hello():\n    print("Hello")', None),
                ('for i in range(10):\n    pass', None),
                ('class MyClass:\n    def __init__(self):\n        self.x = 0', None),
                ('async def fetch():\n    await get_data()', None),
                ('if x > 0:\n    return True\nelse:\n    return False', None),
            ]
        elif language == Language.RUST:
            examples = [
                ('fn main() {\n    println!("Hello");\n}', None),
                ('let mut x: i32 = 0;', None),
                ('struct Point {\n    x: f64,\n    y: f64,\n}', None),
                ('impl Trait for Type {\n    fn method(&self) {}\n}', None),
                ('match result {\n    Ok(v) => v,\n    Err(e) => panic!(),\n}', None),
            ]
        elif language == Language.GO:
            examples = [
                ('func main() {\n    fmt.Println("Hello")\n}', None),
                ('var x int = 0', None),
                ('type Person struct {\n    Name string\n    Age  int\n}', None),
                ('for i := 0; i < 10; i++ {\n    continue\n}', None),
                ('go func() {\n    ch <- data\n}()', None),
            ]
        elif language == Language.JAVASCRIPT:
            examples = [
                ('const hello = () => {\n    console.log("Hello");\n};', None),
                ('async function fetch() {\n    await getData();\n}', None),
                ('class MyClass {\n    constructor() {\n        this.x = 0;\n    }\n}', None),
                ('const arr = [1, 2, 3].map(x => x * 2);', None),
                ('try {\n    throw new Error();\n} catch (e) {\n    console.error(e);\n}', None),
            ]
        elif language == Language.SQL:
            examples = [
                ('SELECT * FROM users WHERE active = true;', None),
                ('INSERT INTO users (name, email) VALUES ("John", "john@example.com");', None),
                ('UPDATE users SET active = false WHERE id = 1;', None),
                ('SELECT u.name, COUNT(o.id) FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id;', None),
                ('CREATE TABLE products (\n    id INT PRIMARY KEY,\n    name VARCHAR(255),\n    price DECIMAL(10, 2)\n);', None),
            ]
        elif language == Language.JAVA:
            examples = [
                ('public class Main {\n    public static void main(String[] args) {\n        System.out.println("Hello");\n    }\n}', None),
                ('public interface Runnable {\n    void run();\n}', None),
                ('for (int i = 0; i < 10; i++) {\n    continue;\n}', None),
                ('try {\n    throw new Exception();\n} catch (Exception e) {\n    e.printStackTrace();\n}', None),
                ('List<String> list = new ArrayList<>();', None),
            ]
            
        # Generate braille for each example
        return [(code, self.encode(code)) for code, _ in examples]


# Training data generator for SAL
def generate_code_training_data() -> List[Dict[str, str]]:
    """Generate training data for SAL to learn programming in braille"""
    encoder = BrailleCodeEncoder()
    training_data = []
    
    # Keyword training
    for language in Language:
        keywords = encoder.keywords.get(language, [])
        for kw in keywords:
            training_data.append({
                "instruction": f"What is the 8-dot braille for the {language.value} keyword '{kw.text}'?",
                "input": "",
                "output": f"The {language.value} {kw.category} '{kw.text}' in 8-dot braille is: {kw.braille}",
                "category": "braille_keyword"
            })
            
    # Code example training
    for language in [Language.PYTHON, Language.RUST, Language.GO, 
                     Language.JAVASCRIPT, Language.SQL, Language.JAVA]:
        examples = encoder.generate_code_examples(language)
        for code, braille in examples:
            training_data.append({
                "instruction": f"Convert this {language.value} code to 8-dot braille:",
                "input": code,
                "output": braille,
                "category": "code_to_braille"
            })
            training_data.append({
                "instruction": f"Write the following {language.value} code in 8-dot braille:",
                "input": code.split('\n')[0],  # First line only
                "output": encoder.encode(code.split('\n')[0]),
                "category": "code_to_braille"
            })
            
    # Operator training
    operators = [
        ('+', 'plus/addition'), ('-', 'minus/subtraction'), ('*', 'multiply'),
        ('/', 'divide'), ('=', 'equals/assignment'), ('==', 'equality'),
        ('!=', 'not equal'), ('>', 'greater than'), ('<', 'less than'),
        ('>=', 'greater or equal'), ('<=', 'less or equal'), ('&&', 'logical and'),
        ('||', 'logical or'), ('!', 'logical not'), ('&', 'bitwise and'),
        ('|', 'bitwise or'), ('^', 'xor'), ('~', 'bitwise not'),
        ('=>', 'arrow function'), ('->', 'arrow'), ('::', 'scope resolution'),
    ]
    for op, name in operators:
        training_data.append({
            "instruction": f"What is the 8-dot braille for the '{name}' operator '{op}'?",
            "input": "",
            "output": f"The {name} operator '{op}' in 8-dot braille is: {encoder.encode(op)}",
            "category": "braille_operator"
        })
        
    # Bracket training
    brackets = [
        ('(', ')', 'parentheses'), ('[', ']', 'square brackets'),
        ('{', '}', 'curly braces'), ('<', '>', 'angle brackets'),
    ]
    for open_b, close_b, name in brackets:
        training_data.append({
            "instruction": f"How do you write {name} in 8-dot braille?",
            "input": "",
            "output": f"Opening {name} '{open_b}' is {encoder.encode(open_b)}, closing '{close_b}' is {encoder.encode(close_b)}",
            "category": "braille_brackets"
        })
        
    return training_data


# Global encoder instance
braille_code_encoder = BrailleCodeEncoder()


# Convenience functions
def code_to_braille(code: str, language: str = None) -> str:
    """Convert code to 8-dot braille"""
    return braille_code_encoder.encode(code)

def braille_to_code(braille: str) -> str:
    """Convert 8-dot braille back to code"""
    return braille_code_encoder.decode(braille)

def get_language_keywords(language: str) -> List[BrailleKeyword]:
    """Get all keywords for a language with their braille representations"""
    try:
        lang = Language(language.lower())
        return braille_code_encoder.keywords.get(lang, [])
    except ValueError:
        return []
