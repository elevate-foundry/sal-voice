"""
SAL 8-Dot Braille IDE Output Module

Braille output rendering and code execution.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import subprocess
import tempfile
import os
import sys
from pathlib import Path
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder, text_to_braille8
from braille8_code import BrailleCodeEncoder, Language


class OutputType(str, Enum):
    """Types of output"""
    STDOUT = "stdout"
    STDERR = "stderr"
    SYSTEM = "system"
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"
    DEBUG = "debug"


@dataclass
class OutputLine:
    """A line of output with braille representation"""
    text: str
    braille: str
    output_type: OutputType
    timestamp: datetime = field(default_factory=datetime.now)
    line_num: int = 0
    
    @property
    def braille_prefix(self) -> str:
        """Get braille prefix for output type"""
        prefixes = {
            OutputType.STDOUT: "⠕",      # Output
            OutputType.STDERR: "⠑",      # Error
            OutputType.SYSTEM: "⠎",      # System
            OutputType.ERROR: "⠑⠗",     # Error (red)
            OutputType.SUCCESS: "⠎⠥",   # Success (green)
            OutputType.INFO: "⠊",        # Info (blue)
            OutputType.DEBUG: "⠙",       # Debug (gray)
        }
        return prefixes.get(self.output_type, "⠶")
        
    @property
    def display(self) -> str:
        """Get display string"""
        return f"{self.braille_prefix} {self.braille}"


class BrailleOutputRenderer:
    """
    Renders output in 8-dot braille format.
    
    Handles:
    - Code execution output
    - Error messages
    - System messages
    - Haptic pattern generation
    """
    
    # Braille output indicators (as SAL specified)
    INDICATORS = {
        "printed": "⠊⠉⠁",     # Printed Output
        "braille": "⠓⠊⠇",     # Braille Output
        "error": "⠑⠗⠗",       # Error
        "warning": "⠺⠁⠗",     # Warning
        "success": "⠎⠥⠉",     # Success
        "running": "⠗⠥⠝",     # Running
        "done": "⠙⠕⠝",       # Done
    }
    
    def __init__(self, max_history: int = 1000):
        self.encoder = Braille8Encoder()
        self.code_encoder = BrailleCodeEncoder()
        self.output_history: List[OutputLine] = []
        self.max_history = max_history
        
    def add_output(self, text: str, output_type: OutputType = OutputType.STDOUT) -> OutputLine:
        """Add output line to history"""
        line = OutputLine(
            text=text,
            braille=self.encoder.encode(text),
            output_type=output_type,
            line_num=len(self.output_history)
        )
        self.output_history.append(line)
        
        # Trim history if needed
        if len(self.output_history) > self.max_history:
            self.output_history = self.output_history[-self.max_history:]
            
        return line
        
    def add_text_output(self, text: str, output_type: OutputType = OutputType.STDOUT):
        """Add multi-line text output"""
        lines = text.split('\n')
        for line in lines:
            self.add_output(line, output_type)
            
    def clear(self):
        """Clear output history"""
        self.output_history.clear()
        
    def get_recent(self, count: int = 20) -> List[OutputLine]:
        """Get recent output lines"""
        return self.output_history[-count:]
        
    def render_output(self, lines: Optional[List[OutputLine]] = None, show_timestamp: bool = False) -> str:
        """Render output in braille format"""
        if lines is None:
            lines = self.output_history
            
        result = []
        
        # Header
        header = f"⠿⠿ {self.INDICATORS['printed']} ⠿⠿"
        result.append(header)
        result.append("⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒")
        
        for line in lines:
            if show_timestamp:
                time_str = line.timestamp.strftime("%H:%M:%S")
                time_braille = self.encoder.encode(time_str)
                result.append(f"{time_braille} {line.display}")
            else:
                result.append(line.display)
                
        result.append("⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒")
        
        return "\n".join(result)
        
    def render_text_output(self, lines: Optional[List[OutputLine]] = None) -> str:
        """Render output as plain text (for debugging)"""
        if lines is None:
            lines = self.output_history
            
        result = []
        result.append("=== Output ===")
        result.append("-" * 30)
        
        for line in lines:
            prefix = {
                OutputType.STDOUT: "[OUT]",
                OutputType.STDERR: "[ERR]",
                OutputType.SYSTEM: "[SYS]",
                OutputType.ERROR: "[ERROR]",
                OutputType.SUCCESS: "[OK]",
                OutputType.INFO: "[INFO]",
                OutputType.DEBUG: "[DBG]",
            }.get(line.output_type, "[???]")
            result.append(f"{prefix} {line.text}")
            
        result.append("-" * 30)
        
        return "\n".join(result)
        
    def execute_code(self, code: str, language: Language) -> Tuple[bool, str, str]:
        """
        Execute code and capture output.
        
        Returns: (success, stdout, stderr)
        """
        self.add_output(f"Running {language.value} code...", OutputType.SYSTEM)
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix=self._get_extension(language), delete=False) as f:
                f.write(code)
                temp_file = f.name
                
            cmd = self._get_run_command(language, temp_file)
            
            if cmd is None:
                error_msg = f"Execution not supported for {language.value}"
                self.add_output(error_msg, OutputType.ERROR)
                return False, "", error_msg
                
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.dirname(temp_file)
            )
            
            # Clean up temp file
            os.unlink(temp_file)
            
            # Add output to history
            if result.stdout:
                self.add_text_output(result.stdout, OutputType.STDOUT)
            if result.stderr:
                self.add_text_output(result.stderr, OutputType.STDERR)
                
            success = result.returncode == 0
            
            if success:
                self.add_output("Execution completed successfully", OutputType.SUCCESS)
            else:
                self.add_output(f"Execution failed with code {result.returncode}", OutputType.ERROR)
                
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            error_msg = "Execution timed out after 30 seconds"
            self.add_output(error_msg, OutputType.ERROR)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            self.add_output(error_msg, OutputType.ERROR)
            return False, "", error_msg
            
    def _get_extension(self, language: Language) -> str:
        """Get file extension for language"""
        extensions = {
            Language.PYTHON: ".py",
            Language.RUST: ".rs",
            Language.GO: ".go",
            Language.JAVASCRIPT: ".js",
            Language.TYPESCRIPT: ".ts",
            Language.JAVA: ".java",
            Language.SQL: ".sql",
            Language.C: ".c",
            Language.CPP: ".cpp",
            Language.RUBY: ".rb",
            Language.SWIFT: ".swift",
            Language.KOTLIN: ".kt",
            Language.SHELL: ".sh",
        }
        return extensions.get(language, ".txt")
        
    def _get_run_command(self, language: Language, file_path: str) -> Optional[List[str]]:
        """Get command to run a file in given language"""
        commands = {
            Language.PYTHON: ["python3", file_path],
            Language.JAVASCRIPT: ["node", file_path],
            Language.RUBY: ["ruby", file_path],
            Language.SHELL: ["bash", file_path],
            Language.GO: ["go", "run", file_path],
        }
        return commands.get(language)
        
    def generate_haptic_pattern(self, output_type: OutputType) -> List[Dict[str, Any]]:
        """Generate haptic pattern for output type"""
        patterns = {
            OutputType.STDOUT: [
                {"type": "vibrate", "duration": 50, "intensity": 0.5},
            ],
            OutputType.STDERR: [
                {"type": "vibrate", "duration": 100, "intensity": 0.8},
                {"type": "pause", "duration": 50},
                {"type": "vibrate", "duration": 100, "intensity": 0.8},
            ],
            OutputType.ERROR: [
                {"type": "vibrate", "duration": 200, "intensity": 1.0},
                {"type": "pause", "duration": 100},
                {"type": "vibrate", "duration": 200, "intensity": 1.0},
                {"type": "pause", "duration": 100},
                {"type": "vibrate", "duration": 200, "intensity": 1.0},
            ],
            OutputType.SUCCESS: [
                {"type": "vibrate", "duration": 100, "intensity": 0.6},
                {"type": "pause", "duration": 50},
                {"type": "vibrate", "duration": 150, "intensity": 0.8},
            ],
            OutputType.INFO: [
                {"type": "vibrate", "duration": 30, "intensity": 0.3},
            ],
            OutputType.SYSTEM: [
                {"type": "vibrate", "duration": 20, "intensity": 0.2},
            ],
        }
        return patterns.get(output_type, [])
        
    def format_error(self, error: str, language: Language) -> str:
        """Format error message with braille markers"""
        lines = error.split('\n')
        formatted = []
        
        formatted.append(f"{self.INDICATORS['error']} Error:")
        formatted.append("⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒")
        
        for line in lines:
            # Highlight line numbers
            braille_line = self.code_encoder.encode(line)
            formatted.append(f"⠀⠀{braille_line}")
            
        formatted.append("⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒⠒")
        
        return "\n".join(formatted)
        
    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of output status"""
        stdout_count = sum(1 for l in self.output_history if l.output_type == OutputType.STDOUT)
        stderr_count = sum(1 for l in self.output_history if l.output_type == OutputType.STDERR)
        error_count = sum(1 for l in self.output_history if l.output_type == OutputType.ERROR)
        
        return {
            "total_lines": len(self.output_history),
            "stdout_lines": stdout_count,
            "stderr_lines": stderr_count,
            "error_count": error_count,
            "has_errors": error_count > 0,
            "status_braille": self.INDICATORS["error"] if error_count > 0 else self.INDICATORS["success"],
        }
