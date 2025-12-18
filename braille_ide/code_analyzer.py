"""
Code Analyzer for SAL Braille IDE

Analyzes code to extract structure for the graph database:
- Functions, classes, methods
- Imports and dependencies
- Variable definitions
- Call relationships

This allows SAL-generated code to be automatically graphed.

⠉⠕⠙⠑_⠁⠝⠁⠇⠽⠵⠑⠗
"""

import ast
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder


class SymbolType(str, Enum):
    """Types of code symbols"""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    IMPORT = "import"
    DECORATOR = "decorator"


@dataclass
class CodeSymbol:
    """A symbol extracted from code"""
    name: str
    type: SymbolType
    line_start: int
    line_end: int
    signature: str = ""
    docstring: str = ""
    parent: str = ""  # Parent class/function name
    decorators: List[str] = field(default_factory=list)
    braille_name: str = ""
    
    def __post_init__(self):
        if not self.braille_name:
            encoder = Braille8Encoder()
            self.braille_name = encoder.encode(self.name)


@dataclass
class ImportInfo:
    """Information about an import"""
    module: str
    names: List[str]  # What's imported (empty for 'import x')
    alias: str = ""
    is_from: bool = False
    line: int = 0


@dataclass
class CallInfo:
    """Information about a function/method call"""
    caller: str  # Who makes the call
    callee: str  # What's being called
    line: int
    is_method: bool = False


@dataclass
class CodeAnalysis:
    """Complete analysis of a code file"""
    language: str
    symbols: List[CodeSymbol] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    calls: List[CallInfo] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    line_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "language": self.language,
            "symbols": [
                {
                    "name": s.name,
                    "type": s.type.value,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "signature": s.signature,
                    "parent": s.parent,
                    "braille_name": s.braille_name
                }
                for s in self.symbols
            ],
            "imports": [
                {
                    "module": i.module,
                    "names": i.names,
                    "is_from": i.is_from,
                    "line": i.line
                }
                for i in self.imports
            ],
            "calls": [
                {
                    "caller": c.caller,
                    "callee": c.callee,
                    "line": c.line
                }
                for c in self.calls
            ],
            "dependencies": list(self.dependencies),
            "line_count": self.line_count
        }


class PythonAnalyzer(ast.NodeVisitor):
    """Analyze Python code using AST"""
    
    def __init__(self):
        self.symbols: List[CodeSymbol] = []
        self.imports: List[ImportInfo] = []
        self.calls: List[CallInfo] = []
        self.current_scope: List[str] = []  # Stack of class/function names
        self.encoder = Braille8Encoder()
        
    def analyze(self, code: str) -> CodeAnalysis:
        """Analyze Python code"""
        try:
            tree = ast.parse(code)
            self.visit(tree)
            
            # Extract dependencies from imports
            dependencies = set()
            for imp in self.imports:
                dependencies.add(imp.module.split('.')[0])
                
            return CodeAnalysis(
                language="python",
                symbols=self.symbols,
                imports=self.imports,
                calls=self.calls,
                dependencies=dependencies,
                line_count=code.count('\n') + 1
            )
        except SyntaxError:
            # Return empty analysis for invalid code
            return CodeAnalysis(language="python", line_count=code.count('\n') + 1)
            
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition"""
        # Build signature
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {ast.unparse(arg.annotation)}"
            args.append(arg_str)
            
        signature = f"def {node.name}({', '.join(args)})"
        if node.returns:
            signature += f" -> {ast.unparse(node.returns)}"
            
        # Get docstring
        docstring = ast.get_docstring(node) or ""
        
        # Get decorators
        decorators = [ast.unparse(d) for d in node.decorator_list]
        
        parent = self.current_scope[-1] if self.current_scope else ""
        symbol_type = SymbolType.METHOD if parent else SymbolType.FUNCTION
        
        self.symbols.append(CodeSymbol(
            name=node.name,
            type=symbol_type,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            signature=signature,
            docstring=docstring[:200],
            parent=parent,
            decorators=decorators
        ))
        
        # Visit body with new scope
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition"""
        # Treat same as regular function
        self.visit_FunctionDef(node)
        
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition"""
        bases = [ast.unparse(b) for b in node.bases]
        signature = f"class {node.name}"
        if bases:
            signature += f"({', '.join(bases)})"
            
        docstring = ast.get_docstring(node) or ""
        decorators = [ast.unparse(d) for d in node.decorator_list]
        
        self.symbols.append(CodeSymbol(
            name=node.name,
            type=SymbolType.CLASS,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            signature=signature,
            docstring=docstring[:200],
            parent=self.current_scope[-1] if self.current_scope else "",
            decorators=decorators
        ))
        
        # Visit body with new scope
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()
        
    def visit_Import(self, node: ast.Import):
        """Visit import statement"""
        for alias in node.names:
            self.imports.append(ImportInfo(
                module=alias.name,
                names=[],
                alias=alias.asname or "",
                is_from=False,
                line=node.lineno
            ))
            
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from...import statement"""
        module = node.module or ""
        names = [alias.name for alias in node.names]
        
        self.imports.append(ImportInfo(
            module=module,
            names=names,
            is_from=True,
            line=node.lineno
        ))
        
    def visit_Call(self, node: ast.Call):
        """Visit function call"""
        caller = self.current_scope[-1] if self.current_scope else "<module>"
        
        # Get callee name
        if isinstance(node.func, ast.Name):
            callee = node.func.id
            is_method = False
        elif isinstance(node.func, ast.Attribute):
            callee = node.func.attr
            is_method = True
        else:
            callee = "<complex>"
            is_method = False
            
        self.calls.append(CallInfo(
            caller=caller,
            callee=callee,
            line=node.lineno,
            is_method=is_method
        ))
        
        self.generic_visit(node)
        
    def visit_Assign(self, node: ast.Assign):
        """Visit assignment (module-level variables)"""
        if not self.current_scope:  # Only module-level
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Check if it's a constant (ALL_CAPS)
                    is_const = target.id.isupper()
                    self.symbols.append(CodeSymbol(
                        name=target.id,
                        type=SymbolType.CONSTANT if is_const else SymbolType.VARIABLE,
                        line_start=node.lineno,
                        line_end=node.lineno,
                        signature=f"{target.id} = ..."
                    ))
                    
        self.generic_visit(node)


class JavaScriptAnalyzer:
    """Analyze JavaScript/TypeScript code using regex patterns"""
    
    def __init__(self):
        self.encoder = Braille8Encoder()
        
    def analyze(self, code: str) -> CodeAnalysis:
        """Analyze JavaScript code"""
        symbols = []
        imports = []
        calls = []
        
        lines = code.split('\n')
        
        # Function patterns
        func_patterns = [
            r'function\s+(\w+)\s*\((.*?)\)',  # function name()
            r'const\s+(\w+)\s*=\s*(?:async\s*)?\((.*?)\)\s*=>',  # const name = () =>
            r'(\w+)\s*:\s*(?:async\s*)?\((.*?)\)\s*=>',  # name: () =>
            r'(?:async\s+)?(\w+)\s*\((.*?)\)\s*{',  # method() {
        ]
        
        # Class pattern
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
        
        # Import patterns
        import_patterns = [
            r'import\s+{([^}]+)}\s+from\s+[\'"]([^\'"]+)[\'"]',  # import { x } from 'y'
            r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',  # import x from 'y'
            r'const\s+{([^}]+)}\s*=\s*require\([\'"]([^\'"]+)[\'"]\)',  # const { x } = require('y')
        ]
        
        for i, line in enumerate(lines, 1):
            # Check for functions
            for pattern in func_patterns:
                match = re.search(pattern, line)
                if match:
                    name = match.group(1)
                    params = match.group(2) if len(match.groups()) > 1 else ""
                    symbols.append(CodeSymbol(
                        name=name,
                        type=SymbolType.FUNCTION,
                        line_start=i,
                        line_end=i,
                        signature=f"{name}({params})"
                    ))
                    break
                    
            # Check for classes
            match = re.search(class_pattern, line)
            if match:
                name = match.group(1)
                extends = match.group(2) if match.group(2) else ""
                sig = f"class {name}"
                if extends:
                    sig += f" extends {extends}"
                symbols.append(CodeSymbol(
                    name=name,
                    type=SymbolType.CLASS,
                    line_start=i,
                    line_end=i,
                    signature=sig
                ))
                
            # Check for imports
            for pattern in import_patterns:
                match = re.search(pattern, line)
                if match:
                    names = [n.strip() for n in match.group(1).split(',')]
                    module = match.group(2)
                    imports.append(ImportInfo(
                        module=module,
                        names=names,
                        is_from=True,
                        line=i
                    ))
                    break
                    
        # Extract dependencies
        dependencies = set()
        for imp in imports:
            # Get base module name
            mod = imp.module.split('/')[0].replace('@', '')
            if not mod.startswith('.'):
                dependencies.add(mod)
                
        return CodeAnalysis(
            language="javascript",
            symbols=symbols,
            imports=imports,
            calls=calls,
            dependencies=dependencies,
            line_count=len(lines)
        )


class CodeAnalyzerFactory:
    """Factory for language-specific analyzers"""
    
    @staticmethod
    def get_analyzer(language: str):
        """Get analyzer for language"""
        language = language.lower()
        
        if language in ('python', 'py'):
            return PythonAnalyzer()
        elif language in ('javascript', 'js', 'typescript', 'ts'):
            return JavaScriptAnalyzer()
        else:
            # Return Python analyzer as default
            return PythonAnalyzer()
            
    @staticmethod
    def analyze_code(code: str, language: str) -> CodeAnalysis:
        """Analyze code for any supported language"""
        analyzer = CodeAnalyzerFactory.get_analyzer(language)
        return analyzer.analyze(code)


def analyze_and_graph(code: str, language: str, file_id: str, 
                      graph_store) -> Dict[str, Any]:
    """
    Analyze code and create graph nodes/relationships.
    
    This is the main integration point between SAL Cascade and the graph.
    When SAL writes code, this function:
    1. Analyzes the code to extract structure
    2. Creates nodes for functions, classes, imports
    3. Creates relationships between them
    
    Returns summary of what was added to the graph.
    """
    from graph_store import Node, Relationship, NodeType, RelationType
    
    # Analyze the code
    analysis = CodeAnalyzerFactory.analyze_code(code, language)
    
    nodes_created = []
    relationships_created = []
    
    encoder = Braille8Encoder()
    
    # Create nodes for each symbol
    for symbol in analysis.symbols:
        node_type = {
            SymbolType.FUNCTION: NodeType.FUNCTION,
            SymbolType.METHOD: NodeType.FUNCTION,
            SymbolType.CLASS: NodeType.CLASS,
            SymbolType.VARIABLE: NodeType.VARIABLE,
            SymbolType.CONSTANT: NodeType.VARIABLE,
        }.get(symbol.type, NodeType.VARIABLE)
        
        node_id = f"{file_id}::{symbol.name}"
        
        node = Node(
            id=node_id,
            type=node_type,
            properties={
                "name": symbol.name,
                "signature": symbol.signature,
                "line_start": symbol.line_start,
                "line_end": symbol.line_end,
                "docstring": symbol.docstring,
                "parent": symbol.parent,
                "decorators": symbol.decorators,
                "braille_signature": encoder.encode(symbol.signature)
            }
        )
        
        try:
            graph_store.create_node(node)
            nodes_created.append(node_id)
            
            # Create DEFINES relationship from file
            rel = Relationship(
                id=f"{file_id}-defines-{node_id}",
                type=RelationType.DEFINES,
                source_id=file_id,
                target_id=node_id
            )
            graph_store.create_relationship(rel)
            relationships_created.append(rel.id)
            
            # If method, create relationship to parent class
            if symbol.parent:
                parent_id = f"{file_id}::{symbol.parent}"
                rel = Relationship(
                    id=f"{parent_id}-contains-{node_id}",
                    type=RelationType.CONTAINS,
                    source_id=parent_id,
                    target_id=node_id
                )
                try:
                    graph_store.create_relationship(rel)
                    relationships_created.append(rel.id)
                except:
                    pass
                    
        except Exception as e:
            # Node might already exist
            pass
            
    # Create nodes for imports
    for imp in analysis.imports:
        import_id = f"{file_id}::import::{imp.module}"
        
        node = Node(
            id=import_id,
            type=NodeType.IMPORT,
            properties={
                "module": imp.module,
                "names": imp.names,
                "is_from": imp.is_from,
                "line": imp.line
            }
        )
        
        try:
            graph_store.create_node(node)
            nodes_created.append(import_id)
            
            # Create IMPORTS relationship
            rel = Relationship(
                id=f"{file_id}-imports-{import_id}",
                type=RelationType.IMPORTS,
                source_id=file_id,
                target_id=import_id,
                properties={"names": imp.names}
            )
            graph_store.create_relationship(rel)
            relationships_created.append(rel.id)
            
        except:
            pass
            
    # Create CALLS relationships
    for call in analysis.calls:
        caller_id = f"{file_id}::{call.caller}"
        callee_id = f"{file_id}::{call.callee}"
        
        # Only create if both exist (internal calls)
        caller_exists = graph_store.get_node(caller_id)
        callee_exists = graph_store.get_node(callee_id)
        
        if caller_exists and callee_exists:
            rel = Relationship(
                id=f"{caller_id}-calls-{callee_id}-{call.line}",
                type=RelationType.CALLS,
                source_id=caller_id,
                target_id=callee_id,
                properties={"line": call.line}
            )
            try:
                graph_store.create_relationship(rel)
                relationships_created.append(rel.id)
            except:
                pass
                
    return {
        "analysis": analysis.to_dict(),
        "nodes_created": nodes_created,
        "relationships_created": relationships_created,
        "braille_summary": encoder.encode(f"Graphed {len(nodes_created)} symbols")
    }
