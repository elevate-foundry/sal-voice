"""
SAL IDE Accessibility Module

Makes SAL IDE the most accessible coding environment:
- Screen reader optimizations (ARIA, live regions)
- Keyboard-first navigation
- Voice input for coding
- Haptic braille output
- High contrast modes

⠁⠉⠉⠑⠎⠎⠊⠃⠊⠇⠊⠞⠽_⠋⠊⠗⠎⠞
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder


class AccessibilityMode(str, Enum):
    """Accessibility modes for different needs"""
    STANDARD = "standard"
    SCREEN_READER = "screen_reader"
    HIGH_CONTRAST = "high_contrast"
    LARGE_TEXT = "large_text"
    REDUCED_MOTION = "reduced_motion"
    VOICE_ONLY = "voice_only"
    BRAILLE_DISPLAY = "braille_display"


@dataclass
class HapticPattern:
    """Haptic feedback pattern for braille displays"""
    dots: List[int]  # Which dots to activate (1-8)
    duration_ms: int = 100
    intensity: float = 1.0  # 0.0 to 1.0
    
    def to_vibration_pattern(self) -> List[int]:
        """Convert to Android/iOS vibration pattern [wait, vibrate, wait, ...]"""
        pattern = []
        for dot in self.dots:
            pattern.extend([0, int(self.duration_ms * self.intensity)])
        return pattern


@dataclass
class AccessibilityAnnouncement:
    """Announcement for screen readers"""
    text: str
    braille: str = ""
    priority: str = "polite"  # polite, assertive
    
    def __post_init__(self):
        if not self.braille:
            encoder = Braille8Encoder()
            self.braille = encoder.encode(self.text)


class AccessibilityManager:
    """
    Manages accessibility features for SAL IDE.
    
    Goal: Make this the BEST accessible coding environment.
    """
    
    def __init__(self):
        self.encoder = Braille8Encoder()
        self.mode = AccessibilityMode.STANDARD
        self.announcements: List[AccessibilityAnnouncement] = []
        self.keyboard_shortcuts: Dict[str, Callable] = {}
        self.focus_order: List[str] = []
        self.current_focus_index = 0
        
        # Default keyboard shortcuts for accessibility
        self._setup_default_shortcuts()
        
    def _setup_default_shortcuts(self):
        """Setup default accessibility keyboard shortcuts"""
        self.keyboard_shortcuts = {
            # Navigation
            "Alt+1": ("Focus editor", "editor"),
            "Alt+2": ("Focus file browser", "fileBrowser"),
            "Alt+3": ("Focus SAL panel", "salPanel"),
            "Alt+4": ("Focus output", "output"),
            
            # Actions
            "Ctrl+Enter": ("Run code", "runCode"),
            "Ctrl+S": ("Save file", "saveFile"),
            "Ctrl+Shift+S": ("Save to disk", "saveToDisk"),
            "Ctrl+B": ("Toggle braille mode", "toggleBraille"),
            "Ctrl+Shift+B": ("Build with SAL", "buildWithSal"),
            
            # Accessibility
            "F6": ("Next panel", "nextPanel"),
            "Shift+F6": ("Previous panel", "prevPanel"),
            "Ctrl+/": ("Announce current line", "announceLine"),
            "Ctrl+Shift+/": ("Announce file summary", "announceFile"),
            
            # Voice
            "Ctrl+Shift+V": ("Start voice input", "startVoice"),
            "Escape": ("Stop voice input", "stopVoice"),
        }
        
    def set_mode(self, mode: AccessibilityMode):
        """Set accessibility mode"""
        self.mode = mode
        self.announce(f"Accessibility mode: {mode.value}")
        
    def announce(self, text: str, priority: str = "polite") -> AccessibilityAnnouncement:
        """Create an announcement for screen readers"""
        announcement = AccessibilityAnnouncement(
            text=text,
            priority=priority
        )
        self.announcements.append(announcement)
        return announcement
        
    def announce_code_change(self, line_number: int, content: str, change_type: str = "edit"):
        """Announce code changes for screen readers"""
        braille_content = self.encoder.encode(content[:50])
        
        if change_type == "insert":
            text = f"Line {line_number} inserted: {content[:100]}"
        elif change_type == "delete":
            text = f"Line {line_number} deleted"
        else:
            text = f"Line {line_number}: {content[:100]}"
            
        return self.announce(text, "polite")
        
    def announce_sal_status(self, status: str, tokens: int = 0):
        """Announce SAL Cascade status changes"""
        status_messages = {
            "understanding": "SAL is understanding your intent",
            "planning": f"SAL is planning, {tokens} tokens processed",
            "coding": f"SAL is writing code, {tokens} tokens",
            "completed": f"SAL completed task with {tokens} tokens",
            "error": "SAL encountered an error",
        }
        
        text = status_messages.get(status, f"SAL status: {status}")
        return self.announce(text, "assertive")
        
    def get_aria_attributes(self, element_type: str) -> Dict[str, str]:
        """Get ARIA attributes for an element type"""
        aria_configs = {
            "editor": {
                "role": "textbox",
                "aria-multiline": "true",
                "aria-label": "Code editor. Press Control slash to hear current line.",
                "aria-live": "off",
                "aria-describedby": "editor-help",
            },
            "file_browser": {
                "role": "tree",
                "aria-label": "File browser. Use arrow keys to navigate.",
            },
            "file_item": {
                "role": "treeitem",
                "aria-selected": "false",
            },
            "sal_panel": {
                "role": "log",
                "aria-label": "SAL Cascade autonomous coding panel",
                "aria-live": "polite",
            },
            "sal_input": {
                "role": "textbox",
                "aria-label": "Describe what you want SAL to build",
            },
            "output": {
                "role": "log",
                "aria-label": "Code output and messages",
                "aria-live": "polite",
            },
            "braille_display": {
                "role": "region",
                "aria-label": "Braille representation of code",
                "aria-live": "polite",
            },
            "token_counter": {
                "role": "status",
                "aria-label": "SAL token counter",
                "aria-live": "polite",
            },
        }
        
        return aria_configs.get(element_type, {})
        
    def generate_haptic_for_code(self, code: str) -> List[HapticPattern]:
        """Generate haptic patterns for code (for braille displays)"""
        patterns = []
        braille = self.encoder.encode(code)
        
        for char in braille:
            # Convert braille unicode to dot pattern
            if '\u2800' <= char <= '\u28FF':
                dots_value = ord(char) - 0x2800
                active_dots = []
                for i in range(8):
                    if dots_value & (1 << i):
                        active_dots.append(i + 1)
                        
                patterns.append(HapticPattern(
                    dots=active_dots,
                    duration_ms=80,
                    intensity=0.8
                ))
                
        return patterns
        
    def get_keyboard_help(self) -> str:
        """Get keyboard shortcuts help text"""
        lines = ["SAL IDE Keyboard Shortcuts:", ""]
        
        categories = {
            "Navigation": ["Alt+1", "Alt+2", "Alt+3", "Alt+4", "F6", "Shift+F6"],
            "Actions": ["Ctrl+Enter", "Ctrl+S", "Ctrl+Shift+S", "Ctrl+B", "Ctrl+Shift+B"],
            "Accessibility": ["Ctrl+/", "Ctrl+Shift+/"],
            "Voice": ["Ctrl+Shift+V", "Escape"],
        }
        
        for category, keys in categories.items():
            lines.append(f"{category}:")
            for key in keys:
                if key in self.keyboard_shortcuts:
                    desc, _ = self.keyboard_shortcuts[key]
                    lines.append(f"  {key}: {desc}")
            lines.append("")
            
        return "\n".join(lines)
        
    def get_focus_order(self) -> List[Dict[str, str]]:
        """Get focus order for tab navigation"""
        return [
            {"id": "fileTree", "label": "File browser"},
            {"id": "codeInput", "label": "Code editor"},
            {"id": "cascadeInput", "label": "SAL intent input"},
            {"id": "buildButton", "label": "Build with SAL"},
            {"id": "outputContent", "label": "Output panel"},
        ]


# Generate accessibility JavaScript for the web app
def generate_accessibility_js() -> str:
    """Generate JavaScript for accessibility features"""
    return '''
    // ============================================
    // SAL IDE Accessibility Features
    // ============================================
    
    const accessibility = {
        mode: 'standard',
        announcements: [],
        
        // Announce to screen readers
        announce: function(text, priority = 'polite') {
            const announcer = document.getElementById('screenReaderAnnouncer');
            if (announcer) {
                announcer.setAttribute('aria-live', priority);
                announcer.textContent = text;
                
                // Clear after announcement
                setTimeout(() => { announcer.textContent = ''; }, 1000);
            }
            console.log('[A11y]', text);
        },
        
        // Announce SAL status changes
        announceSalStatus: function(status, tokens) {
            const messages = {
                'understanding': 'SAL is understanding your intent',
                'planning': `SAL is planning. ${tokens} tokens processed.`,
                'coding': `SAL is writing code. ${tokens} tokens.`,
                'completed': `SAL completed. ${tokens} tokens used.`,
                'error': 'SAL encountered an error'
            };
            this.announce(messages[status] || `SAL: ${status}`, 'assertive');
        },
        
        // Announce current line for screen readers
        announceCurrentLine: function() {
            const editor = document.getElementById('codeInput');
            if (!editor) return;
            
            const lines = editor.value.split('\\n');
            const pos = editor.selectionStart;
            let lineNum = 1;
            let charCount = 0;
            
            for (let i = 0; i < lines.length; i++) {
                charCount += lines[i].length + 1;
                if (charCount > pos) {
                    lineNum = i + 1;
                    break;
                }
            }
            
            const currentLine = lines[lineNum - 1] || '';
            this.announce(`Line ${lineNum}: ${currentLine || 'empty'}`, 'assertive');
        },
        
        // Focus management
        focusOrder: ['fileTree', 'codeInput', 'cascadeInput', 'outputContent'],
        currentFocusIndex: 0,
        
        focusNext: function() {
            this.currentFocusIndex = (this.currentFocusIndex + 1) % this.focusOrder.length;
            const el = document.getElementById(this.focusOrder[this.currentFocusIndex]);
            if (el) {
                el.focus();
                this.announce(`Focused: ${this.focusOrder[this.currentFocusIndex]}`);
            }
        },
        
        focusPrev: function() {
            this.currentFocusIndex = (this.currentFocusIndex - 1 + this.focusOrder.length) % this.focusOrder.length;
            const el = document.getElementById(this.focusOrder[this.currentFocusIndex]);
            if (el) {
                el.focus();
                this.announce(`Focused: ${this.focusOrder[this.currentFocusIndex]}`);
            }
        },
        
        // Keyboard shortcut handling
        handleKeyboard: function(e) {
            const key = [];
            if (e.ctrlKey) key.push('Ctrl');
            if (e.shiftKey) key.push('Shift');
            if (e.altKey) key.push('Alt');
            key.push(e.key);
            const combo = key.join('+');
            
            // Accessibility shortcuts
            if (combo === 'Ctrl+/') {
                e.preventDefault();
                this.announceCurrentLine();
            }
            if (e.key === 'F6') {
                e.preventDefault();
                if (e.shiftKey) this.focusPrev();
                else this.focusNext();
            }
            if (combo === 'Alt+1') { e.preventDefault(); document.getElementById('codeInput')?.focus(); }
            if (combo === 'Alt+2') { e.preventDefault(); document.getElementById('fileTree')?.focus(); }
            if (combo === 'Alt+3') { e.preventDefault(); document.getElementById('cascadeInput')?.focus(); }
            if (combo === 'Alt+4') { e.preventDefault(); document.getElementById('outputContent')?.focus(); }
        },
        
        // Initialize accessibility
        init: function() {
            // Add screen reader announcer
            if (!document.getElementById('screenReaderAnnouncer')) {
                const announcer = document.createElement('div');
                announcer.id = 'screenReaderAnnouncer';
                announcer.setAttribute('role', 'status');
                announcer.setAttribute('aria-live', 'polite');
                announcer.setAttribute('aria-atomic', 'true');
                announcer.className = 'sr-only';
                announcer.style.cssText = 'position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden;';
                document.body.appendChild(announcer);
            }
            
            // Add keyboard listener
            document.addEventListener('keydown', (e) => this.handleKeyboard(e));
            
            // Add skip link
            const skipLink = document.createElement('a');
            skipLink.href = '#codeInput';
            skipLink.textContent = 'Skip to editor';
            skipLink.className = 'skip-link';
            skipLink.style.cssText = 'position:absolute;left:-9999px;z-index:9999;padding:8px;background:#1e1e1e;color:#fff;text-decoration:none;&:focus{left:8px;top:8px;}';
            document.body.insertBefore(skipLink, document.body.firstChild);
            
            this.announce('SAL IDE loaded. Press F6 to navigate panels, Alt+1 through 4 for quick focus.');
        }
    };
    
    // Initialize on load
    document.addEventListener('DOMContentLoaded', () => accessibility.init());
'''


def generate_accessibility_css() -> str:
    """Generate CSS for accessibility features"""
    return '''
    /* Screen reader only class */
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }
    
    /* Skip link */
    .skip-link {
        position: absolute;
        left: -9999px;
        z-index: 9999;
        padding: 8px 16px;
        background: var(--accent-blue);
        color: white;
        text-decoration: none;
        border-radius: 4px;
    }
    
    .skip-link:focus {
        left: 8px;
        top: 8px;
    }
    
    /* Focus indicators */
    :focus {
        outline: 2px solid var(--accent-blue);
        outline-offset: 2px;
    }
    
    :focus:not(:focus-visible) {
        outline: none;
    }
    
    :focus-visible {
        outline: 2px solid var(--accent-blue);
        outline-offset: 2px;
    }
    
    /* High contrast mode */
    @media (prefers-contrast: high) {
        :root {
            --bg-primary: #000000;
            --bg-secondary: #111111;
            --text-primary: #ffffff;
            --text-secondary: #eeeeee;
            --border-color: #ffffff;
            --accent-blue: #00ffff;
            --accent-green: #00ff00;
        }
    }
    
    /* Reduced motion */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation: none !important;
            transition: none !important;
        }
    }
    
    /* Large text support */
    @media (min-resolution: 1dppx) {
        .large-text-mode {
            font-size: 18px;
        }
        
        .large-text-mode .code-input {
            font-size: 16px;
        }
    }
'''


# Global accessibility manager instance
a11y = AccessibilityManager()
