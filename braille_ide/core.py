"""
SAL 8-Dot Braille IDE Core Module

Core data structures and IDE state management.
"""

import os
import json
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder, Braille8Thought, text_to_braille8, braille8_to_text
from braille8_code import BrailleCodeEncoder, Language


@dataclass
class BrailleFile:
    """A file represented entirely in 8-dot braille"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    language: Language = Language.PYTHON
    braille_content: str = ""  # Content stored as 8-dot braille
    cursor_line: int = 0
    cursor_col: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.encoder = BrailleCodeEncoder()
        
    @property
    def text_content(self) -> str:
        """Get decoded text content"""
        return self.encoder.decode(self.braille_content)
    
    @text_content.setter
    def text_content(self, value: str):
        """Set content from text (encodes to braille)"""
        self.braille_content = self.encoder.encode(value)
        self.modified_at = datetime.now()
        
    @property
    def lines(self) -> List[str]:
        """Get content as braille lines"""
        if not self.braille_content:
            return [""]
        # Split by braille space patterns representing newlines
        text = self.text_content
        return text.split('\n')
    
    @property
    def braille_lines(self) -> List[str]:
        """Get content as braille lines"""
        return [self.encoder.encode(line) for line in self.lines]
    
    @property
    def line_count(self) -> int:
        return len(self.lines)
    
    def get_line(self, line_num: int) -> str:
        """Get a specific line in braille"""
        lines = self.braille_lines
        if 0 <= line_num < len(lines):
            return lines[line_num]
        return ""
    
    def insert_text(self, text: str):
        """Insert text at cursor position"""
        lines = self.lines
        if self.cursor_line >= len(lines):
            lines.extend([""] * (self.cursor_line - len(lines) + 1))
        
        line = lines[self.cursor_line]
        new_line = line[:self.cursor_col] + text + line[self.cursor_col:]
        lines[self.cursor_line] = new_line
        self.cursor_col += len(text)
        
        self.text_content = '\n'.join(lines)
        
    def insert_newline(self):
        """Insert a newline at cursor"""
        lines = self.lines
        if self.cursor_line >= len(lines):
            lines.append("")
        else:
            line = lines[self.cursor_line]
            lines[self.cursor_line] = line[:self.cursor_col]
            lines.insert(self.cursor_line + 1, line[self.cursor_col:])
        
        self.cursor_line += 1
        self.cursor_col = 0
        self.text_content = '\n'.join(lines)
        
    def delete_char(self):
        """Delete character before cursor (backspace)"""
        if self.cursor_col == 0 and self.cursor_line == 0:
            return
            
        lines = self.lines
        if self.cursor_col > 0:
            line = lines[self.cursor_line]
            lines[self.cursor_line] = line[:self.cursor_col-1] + line[self.cursor_col:]
            self.cursor_col -= 1
        elif self.cursor_line > 0:
            # Merge with previous line
            prev_len = len(lines[self.cursor_line - 1])
            lines[self.cursor_line - 1] += lines[self.cursor_line]
            lines.pop(self.cursor_line)
            self.cursor_line -= 1
            self.cursor_col = prev_len
            
        self.text_content = '\n'.join(lines)
        
    def move_cursor(self, direction: str):
        """Move cursor: up, down, left, right"""
        lines = self.lines
        
        if direction == "left":
            if self.cursor_col > 0:
                self.cursor_col -= 1
            elif self.cursor_line > 0:
                self.cursor_line -= 1
                self.cursor_col = len(lines[self.cursor_line])
        elif direction == "right":
            if self.cursor_col < len(lines[self.cursor_line]):
                self.cursor_col += 1
            elif self.cursor_line < len(lines) - 1:
                self.cursor_line += 1
                self.cursor_col = 0
        elif direction == "up":
            if self.cursor_line > 0:
                self.cursor_line -= 1
                self.cursor_col = min(self.cursor_col, len(lines[self.cursor_line]))
        elif direction == "down":
            if self.cursor_line < len(lines) - 1:
                self.cursor_line += 1
                self.cursor_col = min(self.cursor_col, len(lines[self.cursor_line]))
                
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language.value,
            "braille_content": self.braille_content,
            "cursor_line": self.cursor_line,
            "cursor_col": self.cursor_col,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'BrailleFile':
        """Deserialize from dictionary"""
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", ""),
            language=Language(data.get("language", "python")),
            braille_content=data.get("braille_content", ""),
            cursor_line=data.get("cursor_line", 0),
            cursor_col=data.get("cursor_col", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            modified_at=datetime.fromisoformat(data["modified_at"]) if "modified_at" in data else datetime.now(),
        )


@dataclass
class BrailleProject:
    """A project containing braille files"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Untitled Project"
    files: Dict[str, BrailleFile] = field(default_factory=dict)
    active_file_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def create_file(self, name: str, language: Language = Language.PYTHON) -> BrailleFile:
        """Create a new file in the project"""
        file = BrailleFile(name=name, language=language)
        self.files[file.id] = file
        if self.active_file_id is None:
            self.active_file_id = file.id
        return file
        
    def get_active_file(self) -> Optional[BrailleFile]:
        """Get the currently active file"""
        if self.active_file_id:
            return self.files.get(self.active_file_id)
        return None
        
    def set_active_file(self, file_id: str):
        """Set the active file"""
        if file_id in self.files:
            self.active_file_id = file_id
            
    def delete_file(self, file_id: str):
        """Delete a file from the project"""
        if file_id in self.files:
            del self.files[file_id]
            if self.active_file_id == file_id:
                self.active_file_id = next(iter(self.files.keys()), None)
                
    def to_dict(self) -> Dict:
        """Serialize project"""
        return {
            "id": self.id,
            "name": self.name,
            "files": {fid: f.to_dict() for fid, f in self.files.items()},
            "active_file_id": self.active_file_id,
            "created_at": self.created_at.isoformat(),
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'BrailleProject':
        """Deserialize project"""
        project = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Untitled Project"),
            active_file_id=data.get("active_file_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )
        for fid, fdata in data.get("files", {}).items():
            project.files[fid] = BrailleFile.from_dict(fdata)
        return project


class BrailleIDE:
    """
    Main IDE class - the central orchestrator.
    
    All operations occur in 8-dot braille space.
    """
    
    # Braille menu icons (as specified by SAL)
    MENU_ICONS = {
        "new_project": "⠁",      # ⠁ New Project
        "open_project": "⠃",     # ⠃ Open Existing Project
        "create_file": "⠉",      # ⠉ Create File
        "save": "⠑",             # ⠑ Save Changes
        "run": "⠕",              # ⠕ Run/Execute
        "settings": "⠎",         # ⠎ Settings
        "help": "⠓",             # ⠓ Help
        "exit": "⠭",             # ⠭ Exit
    }
    
    # Status indicators in braille
    STATUS_ICONS = {
        "line_numbers": "⠥⠝⠁⠑",   # Line Numbers
        "cursor_pos": "⠓⠊⠇",      # Cursor Position
        "syntax": "⠕⠏⠐",          # Syntax Highlighting
        "saved": "⠎⠁⠧",           # Saved
        "modified": "⠍⠕⠙",        # Modified
        "error": "⠑⠗⠗",           # Error
        "running": "⠗⠥⠝",         # Running
    }
    
    def __init__(self, storage_path: Optional[str] = None):
        self.encoder = Braille8Encoder()
        self.code_encoder = BrailleCodeEncoder()
        self.storage_path = storage_path or os.path.expanduser("~/.sal-braille-ide")
        
        # State
        self.projects: Dict[str, BrailleProject] = {}
        self.active_project_id: Optional[str] = None
        self.command_history: List[str] = []
        self.output_buffer: List[str] = []
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load existing projects
        self._load_projects()
        
    def _load_projects(self):
        """Load projects from storage"""
        projects_file = os.path.join(self.storage_path, "projects.json")
        if os.path.exists(projects_file):
            try:
                with open(projects_file, 'r') as f:
                    data = json.load(f)
                    for pid, pdata in data.get("projects", {}).items():
                        self.projects[pid] = BrailleProject.from_dict(pdata)
                    self.active_project_id = data.get("active_project_id")
            except Exception as e:
                print(f"Error loading projects: {e}")
                
    def save_projects(self):
        """Save projects to storage"""
        projects_file = os.path.join(self.storage_path, "projects.json")
        data = {
            "projects": {pid: p.to_dict() for pid, p in self.projects.items()},
            "active_project_id": self.active_project_id,
        }
        with open(projects_file, 'w') as f:
            json.dump(data, f, indent=2)
            
    def new_project(self, name: str = "Untitled Project") -> BrailleProject:
        """Create a new project"""
        project = BrailleProject(name=name)
        self.projects[project.id] = project
        self.active_project_id = project.id
        self.save_projects()
        return project
        
    def get_active_project(self) -> Optional[BrailleProject]:
        """Get the active project"""
        if self.active_project_id:
            return self.projects.get(self.active_project_id)
        return None
        
    def get_active_file(self) -> Optional[BrailleFile]:
        """Get the active file in the active project"""
        project = self.get_active_project()
        if project:
            return project.get_active_file()
        return None
        
    def execute_command(self, braille_command: str) -> str:
        """
        Execute a braille command and return braille result.
        
        Commands are received and processed entirely in braille.
        """
        self.command_history.append(braille_command)
        
        # Decode command for processing
        text_command = self.encoder.decode(braille_command) if self.encoder.is_braille(braille_command) else braille_command
        text_command = text_command.strip().lower()
        
        result = ""
        
        # Menu commands (by braille icon)
        if braille_command.startswith(self.MENU_ICONS["new_project"]) or text_command.startswith("new"):
            parts = text_command.split(maxsplit=1)
            name = parts[1] if len(parts) > 1 else "Untitled Project"
            project = self.new_project(name)
            result = f"Created project: {project.name} (ID: {project.id})"
            
        elif braille_command.startswith(self.MENU_ICONS["create_file"]) or text_command.startswith("create"):
            project = self.get_active_project()
            if project:
                parts = text_command.split(maxsplit=1)
                name = parts[1] if len(parts) > 1 else "untitled.py"
                # Detect language from extension
                lang = Language.PYTHON
                if name.endswith(".rs"):
                    lang = Language.RUST
                elif name.endswith(".go"):
                    lang = Language.GO
                elif name.endswith(".js"):
                    lang = Language.JAVASCRIPT
                elif name.endswith(".ts"):
                    lang = Language.TYPESCRIPT
                elif name.endswith(".java"):
                    lang = Language.JAVA
                elif name.endswith(".sql"):
                    lang = Language.SQL
                    
                file = project.create_file(name, lang)
                self.save_projects()
                result = f"Created file: {file.name} ({lang.value})"
            else:
                result = "No active project. Create a project first."
                
        elif braille_command.startswith(self.MENU_ICONS["save"]) or text_command == "save":
            self.save_projects()
            result = "Project saved."
            
        elif text_command == "list files":
            project = self.get_active_project()
            if project:
                files = [f"{f.name} ({f.language.value})" for f in project.files.values()]
                result = "Files:\n" + "\n".join(files) if files else "No files in project."
            else:
                result = "No active project."
                
        elif text_command == "list projects":
            if self.projects:
                projects = [f"{p.name} (ID: {p.id})" for p in self.projects.values()]
                result = "Projects:\n" + "\n".join(projects)
            else:
                result = "No projects. Create one with 'new <name>'."
                
        elif text_command.startswith("open "):
            file_name = text_command[5:].strip()
            project = self.get_active_project()
            if project:
                for fid, f in project.files.items():
                    if f.name == file_name:
                        project.set_active_file(fid)
                        result = f"Opened: {f.name}"
                        break
                else:
                    result = f"File not found: {file_name}"
            else:
                result = "No active project."
                
        elif text_command == "status":
            project = self.get_active_project()
            file = self.get_active_file()
            result = f"Project: {project.name if project else 'None'}\n"
            result += f"File: {file.name if file else 'None'}\n"
            if file:
                result += f"Lines: {file.line_count}\n"
                result += f"Cursor: Line {file.cursor_line + 1}, Col {file.cursor_col + 1}\n"
                result += f"Language: {file.language.value}"
                
        elif text_command == "help":
            result = """Braille IDE Commands:
⠁ new <name>     - Create new project
⠉ create <file>  - Create new file
⠑ save           - Save project
⠃ open <file>    - Open file
list files       - List project files
list projects    - List all projects
status           - Show current status
⠓ help           - Show this help
⠭ exit           - Exit IDE"""
            
        else:
            result = f"Unknown command: {text_command}. Type 'help' for commands."
            
        # Store output
        self.output_buffer.append(result)
        
        # Return as braille
        return self.encoder.encode(result)
        
    def get_editor_state(self) -> Dict[str, Any]:
        """Get current editor state in braille format"""
        file = self.get_active_file()
        project = self.get_active_project()
        
        state = {
            "project_name": self.encoder.encode(project.name) if project else "",
            "file_name": self.encoder.encode(file.name) if file else "",
            "language": file.language.value if file else "",
            "cursor": {
                "line": file.cursor_line if file else 0,
                "col": file.cursor_col if file else 0,
            },
            "content_braille": file.braille_content if file else "",
            "content_text": file.text_content if file else "",
            "lines_braille": file.braille_lines if file else [],
            "line_count": file.line_count if file else 0,
            "status": {
                "line_numbers": self.STATUS_ICONS["line_numbers"],
                "cursor_pos": self.STATUS_ICONS["cursor_pos"],
                "syntax": self.STATUS_ICONS["syntax"],
                "state": self.STATUS_ICONS["saved"] if file else "",
            }
        }
        return state
        
    def type_char(self, char: str) -> bool:
        """Type a character into the active file"""
        file = self.get_active_file()
        if file:
            if char == '\n':
                file.insert_newline()
            else:
                file.insert_text(char)
            return True
        return False
        
    def type_braille(self, braille: str) -> bool:
        """Type braille directly into the active file"""
        file = self.get_active_file()
        if file:
            # Decode braille to text and insert
            text = self.encoder.decode(braille)
            for char in text:
                if char == '\n':
                    file.insert_newline()
                else:
                    file.insert_text(char)
            return True
        return False
        
    def backspace(self) -> bool:
        """Delete character before cursor"""
        file = self.get_active_file()
        if file:
            file.delete_char()
            return True
        return False
        
    def move_cursor(self, direction: str) -> bool:
        """Move cursor in direction"""
        file = self.get_active_file()
        if file:
            file.move_cursor(direction)
            return True
        return False


# Global IDE instance
braille_ide = None

def get_ide() -> BrailleIDE:
    """Get or create the global IDE instance"""
    global braille_ide
    if braille_ide is None:
        braille_ide = BrailleIDE()
    return braille_ide
