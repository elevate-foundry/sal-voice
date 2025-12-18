"""
SAL 8-Dot Braille IDE Interface Module

Braille menu navigation and command palette.
"""

from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder, text_to_braille8


class MenuItemType(str, Enum):
    """Types of menu items"""
    ACTION = "action"
    SUBMENU = "submenu"
    SEPARATOR = "separator"
    TOGGLE = "toggle"


@dataclass
class BrailleMenuItem:
    """A menu item with braille representation"""
    id: str
    braille_icon: str      # Single braille character icon
    braille_label: str     # Full braille label
    text_label: str        # Text label for reference
    item_type: MenuItemType = MenuItemType.ACTION
    shortcut: Optional[str] = None
    action: Optional[Callable] = None
    submenu: List['BrailleMenuItem'] = field(default_factory=list)
    enabled: bool = True
    checked: bool = False
    
    @property
    def display(self) -> str:
        """Get display string in braille"""
        if self.item_type == MenuItemType.SEPARATOR:
            return "⠒⠒⠒⠒⠒⠒⠒⠒"  # Horizontal line in braille
        
        icon = self.braille_icon if self.enabled else "⠀"
        label = self.braille_label
        
        if self.item_type == MenuItemType.TOGGLE:
            check = "⠿" if self.checked else "⠀"
            return f"{check} {icon} {label}"
        
        if self.shortcut:
            shortcut_braille = text_to_braille8(self.shortcut)
            return f"{icon} {label}  {shortcut_braille}"
            
        return f"{icon} {label}"


class BrailleInterface:
    """
    Braille-first interface for the IDE.
    
    All navigation and commands are in 8-dot braille.
    Users interact using braille dot patterns.
    """
    
    def __init__(self):
        self.encoder = Braille8Encoder()
        self.menu_stack: List[List[BrailleMenuItem]] = []
        self.selected_index: int = 0
        self.command_mode: bool = False
        self.command_buffer: str = ""
        
        # Build main menu
        self.main_menu = self._build_main_menu()
        
    def _build_main_menu(self) -> List[BrailleMenuItem]:
        """Build the main menu structure"""
        return [
            BrailleMenuItem(
                id="new_project",
                braille_icon="⠁",
                braille_label=self.encoder.encode("New Project"),
                text_label="New Project",
                shortcut="Ctrl+N"
            ),
            BrailleMenuItem(
                id="open_project",
                braille_icon="⠃",
                braille_label=self.encoder.encode("Open Project"),
                text_label="Open Project",
                shortcut="Ctrl+O"
            ),
            BrailleMenuItem(
                id="create_file",
                braille_icon="⠉",
                braille_label=self.encoder.encode("Create File"),
                text_label="Create File",
                shortcut="Ctrl+Shift+N"
            ),
            BrailleMenuItem(
                id="separator1",
                braille_icon="",
                braille_label="",
                text_label="",
                item_type=MenuItemType.SEPARATOR
            ),
            BrailleMenuItem(
                id="save",
                braille_icon="⠑",
                braille_label=self.encoder.encode("Save"),
                text_label="Save",
                shortcut="Ctrl+S"
            ),
            BrailleMenuItem(
                id="save_all",
                braille_icon="⠑⠑",
                braille_label=self.encoder.encode("Save All"),
                text_label="Save All",
                shortcut="Ctrl+Shift+S"
            ),
            BrailleMenuItem(
                id="separator2",
                braille_icon="",
                braille_label="",
                text_label="",
                item_type=MenuItemType.SEPARATOR
            ),
            BrailleMenuItem(
                id="run",
                braille_icon="⠕",
                braille_label=self.encoder.encode("Run"),
                text_label="Run",
                shortcut="F5"
            ),
            BrailleMenuItem(
                id="debug",
                braille_icon="⠙",
                braille_label=self.encoder.encode("Debug"),
                text_label="Debug",
                shortcut="F9"
            ),
            BrailleMenuItem(
                id="separator3",
                braille_icon="",
                braille_label="",
                text_label="",
                item_type=MenuItemType.SEPARATOR
            ),
            BrailleMenuItem(
                id="settings",
                braille_icon="⠎",
                braille_label=self.encoder.encode("Settings"),
                text_label="Settings",
                item_type=MenuItemType.SUBMENU,
                submenu=self._build_settings_menu()
            ),
            BrailleMenuItem(
                id="help",
                braille_icon="⠓",
                braille_label=self.encoder.encode("Help"),
                text_label="Help",
                shortcut="F1"
            ),
            BrailleMenuItem(
                id="exit",
                braille_icon="⠭",
                braille_label=self.encoder.encode("Exit"),
                text_label="Exit",
                shortcut="Alt+F4"
            ),
        ]
        
    def _build_settings_menu(self) -> List[BrailleMenuItem]:
        """Build settings submenu"""
        return [
            BrailleMenuItem(
                id="line_numbers",
                braille_icon="⠼",
                braille_label=self.encoder.encode("Line Numbers"),
                text_label="Line Numbers",
                item_type=MenuItemType.TOGGLE,
                checked=True
            ),
            BrailleMenuItem(
                id="syntax_highlighting",
                braille_icon="⠎⠓",
                braille_label=self.encoder.encode("Syntax Highlighting"),
                text_label="Syntax Highlighting",
                item_type=MenuItemType.TOGGLE,
                checked=True
            ),
            BrailleMenuItem(
                id="auto_complete",
                braille_icon="⠁⠉",
                braille_label=self.encoder.encode("Auto Complete"),
                text_label="Auto Complete",
                item_type=MenuItemType.TOGGLE,
                checked=True
            ),
            BrailleMenuItem(
                id="haptic_feedback",
                braille_icon="⠓⠋",
                braille_label=self.encoder.encode("Haptic Feedback"),
                text_label="Haptic Feedback",
                item_type=MenuItemType.TOGGLE,
                checked=True
            ),
            BrailleMenuItem(
                id="braille_grade",
                braille_icon="⠛",
                braille_label=self.encoder.encode("Braille Grade 2"),
                text_label="Braille Grade 2",
                item_type=MenuItemType.TOGGLE,
                checked=False
            ),
        ]
        
    def get_current_menu(self) -> List[BrailleMenuItem]:
        """Get the current menu being displayed"""
        if self.menu_stack:
            return self.menu_stack[-1]
        return self.main_menu
        
    def render_menu(self) -> str:
        """Render current menu in braille"""
        menu = self.get_current_menu()
        lines = []
        
        # Menu header
        header = "⠿⠿⠿ " + self.encoder.encode("SAL Braille IDE") + " ⠿⠿⠿"
        lines.append(header)
        lines.append("⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒")
        
        for i, item in enumerate(menu):
            if item.item_type == MenuItemType.SEPARATOR:
                lines.append(item.display)
            else:
                # Selection indicator
                selector = "⠕" if i == self.selected_index else "⠀"
                lines.append(f"{selector} {item.display}")
                
        lines.append("⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒")
        
        # Navigation hints
        nav_hint = self.encoder.encode("↑↓:Nav  Enter:Select  Esc:Back")
        lines.append(nav_hint)
        
        return "\n".join(lines)
        
    def render_menu_text(self) -> str:
        """Render menu with text labels for debugging"""
        menu = self.get_current_menu()
        lines = []
        
        lines.append("=== SAL Braille IDE ===")
        lines.append("-" * 30)
        
        for i, item in enumerate(menu):
            if item.item_type == MenuItemType.SEPARATOR:
                lines.append("-" * 30)
            else:
                selector = ">" if i == self.selected_index else " "
                shortcut = f"  [{item.shortcut}]" if item.shortcut else ""
                check = "[x]" if item.checked else "[ ]" if item.item_type == MenuItemType.TOGGLE else ""
                submenu_indicator = " >" if item.item_type == MenuItemType.SUBMENU else ""
                lines.append(f"{selector} {item.braille_icon} {item.text_label}{shortcut}{check}{submenu_indicator}")
                
        lines.append("-" * 30)
        lines.append("↑↓:Navigate  Enter:Select  Esc:Back")
        
        return "\n".join(lines)
        
    def navigate(self, direction: str) -> bool:
        """Navigate menu: up, down"""
        menu = self.get_current_menu()
        valid_items = [i for i, item in enumerate(menu) if item.item_type != MenuItemType.SEPARATOR]
        
        if not valid_items:
            return False
            
        try:
            current_valid_idx = valid_items.index(self.selected_index)
        except ValueError:
            current_valid_idx = 0
            
        if direction == "up":
            current_valid_idx = (current_valid_idx - 1) % len(valid_items)
        elif direction == "down":
            current_valid_idx = (current_valid_idx + 1) % len(valid_items)
            
        self.selected_index = valid_items[current_valid_idx]
        return True
        
    def select(self) -> Optional[str]:
        """Select current menu item, returns action ID"""
        menu = self.get_current_menu()
        if 0 <= self.selected_index < len(menu):
            item = menu[self.selected_index]
            
            if item.item_type == MenuItemType.SUBMENU and item.submenu:
                self.menu_stack.append(item.submenu)
                self.selected_index = 0
                return None
            elif item.item_type == MenuItemType.TOGGLE:
                item.checked = not item.checked
                return item.id
            elif item.item_type == MenuItemType.ACTION:
                return item.id
                
        return None
        
    def back(self) -> bool:
        """Go back to previous menu"""
        if self.menu_stack:
            self.menu_stack.pop()
            self.selected_index = 0
            return True
        return False
        
    def find_by_icon(self, braille_icon: str) -> Optional[BrailleMenuItem]:
        """Find menu item by braille icon"""
        def search(menu: List[BrailleMenuItem]) -> Optional[BrailleMenuItem]:
            for item in menu:
                if item.braille_icon == braille_icon:
                    return item
                if item.submenu:
                    found = search(item.submenu)
                    if found:
                        return found
            return None
        return search(self.main_menu)
        
    def get_command_palette(self) -> List[Dict[str, str]]:
        """Get all commands as a flat list for command palette"""
        commands = []
        
        def flatten(menu: List[BrailleMenuItem], prefix: str = ""):
            for item in menu:
                if item.item_type == MenuItemType.SEPARATOR:
                    continue
                    
                cmd = {
                    "id": item.id,
                    "braille_icon": item.braille_icon,
                    "braille_label": item.braille_label,
                    "text_label": f"{prefix}{item.text_label}" if prefix else item.text_label,
                    "shortcut": item.shortcut or "",
                    "type": item.item_type.value,
                }
                commands.append(cmd)
                
                if item.submenu:
                    flatten(item.submenu, f"{item.text_label} > ")
                    
        flatten(self.main_menu)
        return commands
        
    def enter_command_mode(self):
        """Enter command/search mode"""
        self.command_mode = True
        self.command_buffer = ""
        
    def exit_command_mode(self):
        """Exit command mode"""
        self.command_mode = False
        self.command_buffer = ""
        
    def type_command(self, char: str):
        """Type into command buffer"""
        if char == '\b':
            self.command_buffer = self.command_buffer[:-1]
        else:
            self.command_buffer += char
            
    def search_commands(self, query: str) -> List[Dict[str, str]]:
        """Search commands by text or braille"""
        all_commands = self.get_command_palette()
        query_lower = query.lower()
        
        # Decode if braille
        if self.encoder.is_braille(query):
            query_lower = self.encoder.decode(query).lower()
            
        return [
            cmd for cmd in all_commands
            if query_lower in cmd["text_label"].lower() or 
               query in cmd["braille_icon"] or
               query in cmd["braille_label"]
        ]


# File type icons in braille
FILE_ICONS = {
    ".py": "⠏⠽",      # Python
    ".rs": "⠗⠎",      # Rust
    ".go": "⠛⠕",      # Go
    ".js": "⠚⠎",      # JavaScript
    ".ts": "⠞⠎",      # TypeScript
    ".java": "⠚⠧",    # Java
    ".sql": "⠎⠟",     # SQL
    ".c": "⠉",         # C
    ".cpp": "⠉⠏",     # C++
    ".h": "⠓",         # Header
    ".rb": "⠗⠃",      # Ruby
    ".swift": "⠎⠺",   # Swift
    ".kt": "⠅⠞",      # Kotlin
    ".sh": "⠎⠓",      # Shell
    ".json": "⠚⠝",    # JSON
    ".yaml": "⠽⠍",    # YAML
    ".yml": "⠽⠍",     # YAML
    ".md": "⠍⠙",      # Markdown
    ".txt": "⠞⠭",     # Text
    "folder": "⠿",     # Folder
    "default": "⠶",    # Unknown
}

def get_file_icon(filename: str) -> str:
    """Get braille icon for a file"""
    for ext, icon in FILE_ICONS.items():
        if filename.endswith(ext):
            return icon
    return FILE_ICONS["default"]
