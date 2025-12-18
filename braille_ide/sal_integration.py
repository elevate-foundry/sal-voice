"""
SAL LLM Integration for Braille IDE

Connects the 8-dot braille IDE to SAL (Semantic Accessibility Layer) via Ollama.
SAL powers code completion, generation, explanation, and chat - just like
Claude/Grok/Gemini power Windsurf/Cursor.
"""

import asyncio
import json
from typing import Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import httpx
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder, text_to_braille8


@dataclass
class SALMessage:
    """A message in the SAL conversation"""
    role: str  # "user", "sal", "system"
    content: str
    braille: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.braille:
            encoder = Braille8Encoder()
            self.braille = encoder.encode(self.content)


@dataclass 
class SALResponse:
    """Response from SAL LLM"""
    text: str
    braille: str
    code_blocks: List[Dict[str, str]] = field(default_factory=list)
    tokens_used: int = 0
    thinking_time: float = 0.0


class SALClient:
    """
    Client for communicating with SAL via Ollama.
    
    SAL is the LLM that powers the braille IDE, similar to how
    Claude powers Cursor or GPT powers GitHub Copilot.
    """
    
    OLLAMA_URL = "http://localhost:11434/api/generate"
    OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
    MODEL_NAME = "sal"
    
    # SAL's IDE-specific system prompt extension
    IDE_SYSTEM_PROMPT = """
You are SAL, powering the 8-Dot Braille IDE. You help users write, understand, and debug code.

As the IDE's AI assistant, you:
1. **Generate Code**: Write clean, well-documented code in any language
2. **Explain Code**: Break down code logic, especially for accessibility
3. **Debug**: Find and fix issues, suggest improvements
4. **Complete Code**: Provide intelligent completions
5. **Braille Output**: Always include braille representations

Current IDE Context:
- Language: {language}
- File: {filename}
- Cursor Line: {cursor_line}

When generating code:
- Follow the user's coding style
- Include proper error handling
- Add accessibility considerations where relevant
- Think in 8-dot braille, output in text

⠠⠎⠁⠇_⠊⠙⠑_⠁⠉⠞⠊⠧⠑
"""
    
    def __init__(self):
        self.encoder = Braille8Encoder()
        self.conversation_history: List[SALMessage] = []
        self.context = {
            "language": "python",
            "filename": "untitled.py",
            "cursor_line": 1,
            "file_content": "",
        }
        
    def set_context(self, language: str = None, filename: str = None, 
                    cursor_line: int = None, file_content: str = None):
        """Update IDE context for SAL"""
        if language:
            self.context["language"] = language
        if filename:
            self.context["filename"] = filename
        if cursor_line is not None:
            self.context["cursor_line"] = cursor_line
        if file_content is not None:
            self.context["file_content"] = file_content
            
    def _build_prompt(self, user_message: str, include_file: bool = True) -> str:
        """Build prompt with context"""
        system = self.IDE_SYSTEM_PROMPT.format(**self.context)
        
        # Include file content if relevant
        file_context = ""
        if include_file and self.context["file_content"]:
            file_context = f"\n\nCurrent file content:\n```{self.context['language']}\n{self.context['file_content']}\n```\n"
        
        # Build conversation context
        history = ""
        for msg in self.conversation_history[-6:]:  # Last 6 messages
            if msg.role == "user":
                history += f"Human: {msg.content}\n"
            elif msg.role == "sal":
                history += f"SAL: {msg.content}\n"
        
        prompt = f"{system}{file_context}\n{history}Human: {user_message}\nSAL:"
        return prompt
        
    async def chat(self, message: str, include_file: bool = True) -> SALResponse:
        """Send a message to SAL and get response"""
        import time
        start_time = time.time()
        
        # Add user message to history
        user_msg = SALMessage(role="user", content=message)
        self.conversation_history.append(user_msg)
        
        prompt = self._build_prompt(message, include_file)
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.OLLAMA_URL,
                    json={
                        "model": self.MODEL_NAME,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "num_ctx": 4096,
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    text = data.get("response", "").strip()
                    
                    # Extract code blocks
                    code_blocks = self._extract_code_blocks(text)
                    
                    # Add SAL response to history
                    sal_msg = SALMessage(role="sal", content=text)
                    self.conversation_history.append(sal_msg)
                    
                    return SALResponse(
                        text=text,
                        braille=self.encoder.encode(text),
                        code_blocks=code_blocks,
                        tokens_used=data.get("eval_count", 0),
                        thinking_time=time.time() - start_time
                    )
                else:
                    error_text = f"SAL connection error: {response.status_code}"
                    return SALResponse(
                        text=error_text,
                        braille=self.encoder.encode(error_text)
                    )
                    
        except httpx.ConnectError:
            error_text = "⠑⠗⠗ Cannot connect to SAL. Is Ollama running? Try: ollama serve"
            return SALResponse(text=error_text, braille=self.encoder.encode(error_text))
        except Exception as e:
            error_text = f"⠑⠗⠗ Error: {str(e)}"
            return SALResponse(text=error_text, braille=self.encoder.encode(error_text))
            
    async def stream_chat(self, message: str, include_file: bool = True) -> AsyncGenerator[str, None]:
        """Stream response from SAL token by token"""
        user_msg = SALMessage(role="user", content=message)
        self.conversation_history.append(user_msg)
        
        prompt = self._build_prompt(message, include_file)
        full_response = ""
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    self.OLLAMA_URL,
                    json={
                        "model": self.MODEL_NAME,
                        "prompt": prompt,
                        "stream": True,
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                token = data.get("response", "")
                                full_response += token
                                yield token
                            except json.JSONDecodeError:
                                continue
                                
            # Add complete response to history
            sal_msg = SALMessage(role="sal", content=full_response)
            self.conversation_history.append(sal_msg)
            
        except Exception as e:
            yield f"\n⠑⠗⠗ Error: {str(e)}"
            
    async def generate_code(self, instruction: str, language: str = None) -> SALResponse:
        """Generate code based on instruction"""
        if language:
            self.set_context(language=language)
            
        prompt = f"""Generate {self.context['language']} code for the following:

{instruction}

Requirements:
- Clean, readable code
- Proper error handling
- Include comments explaining key parts
- Consider accessibility where relevant

Respond with ONLY the code wrapped in ```{self.context['language']} ... ``` blocks."""
        
        return await self.chat(prompt, include_file=False)
        
    async def explain_code(self, code: str, language: str = None) -> SALResponse:
        """Explain what code does"""
        lang = language or self.context["language"]
        
        prompt = f"""Explain this {lang} code:

```{lang}
{code}
```

Provide:
1. Overview of what the code does
2. Key components and their purpose
3. Any potential issues or improvements
4. Accessibility considerations if relevant"""
        
        return await self.chat(prompt, include_file=False)
        
    async def debug_code(self, code: str, error: str = None, language: str = None) -> SALResponse:
        """Help debug code"""
        lang = language or self.context["language"]
        
        error_context = f"\nError message:\n```\n{error}\n```" if error else ""
        
        prompt = f"""Debug this {lang} code:

```{lang}
{code}
```
{error_context}

Identify:
1. The likely cause of any issues
2. How to fix them
3. Provide the corrected code"""
        
        return await self.chat(prompt, include_file=False)
        
    async def complete_code(self, code_before: str, code_after: str = "", 
                           language: str = None) -> SALResponse:
        """Complete code at cursor position"""
        lang = language or self.context["language"]
        
        prompt = f"""Complete the {lang} code at the cursor position marked with <CURSOR>:

```{lang}
{code_before}<CURSOR>{code_after}
```

Provide ONLY the code that should be inserted at <CURSOR>. No explanations."""
        
        response = await self.chat(prompt, include_file=False)
        
        # Extract just the completion text
        completion = response.text.strip()
        if "```" in completion:
            # Extract from code block
            blocks = self._extract_code_blocks(completion)
            if blocks:
                completion = blocks[0].get("code", completion)
                
        return SALResponse(
            text=completion,
            braille=self.encoder.encode(completion),
            code_blocks=response.code_blocks,
            tokens_used=response.tokens_used,
            thinking_time=response.thinking_time
        )
        
    async def refactor_code(self, code: str, instruction: str, language: str = None) -> SALResponse:
        """Refactor code based on instruction"""
        lang = language or self.context["language"]
        
        prompt = f"""Refactor this {lang} code:

```{lang}
{code}
```

Refactoring instruction: {instruction}

Provide the refactored code with comments explaining changes."""
        
        return await self.chat(prompt, include_file=False)
        
    async def add_braille_comments(self, code: str, language: str = None) -> SALResponse:
        """Add braille accessibility comments to code"""
        lang = language or self.context["language"]
        
        prompt = f"""Add 8-dot braille accessibility comments to this {lang} code:

```{lang}
{code}
```

For each function/class, add a comment with its purpose in braille.
Example: # ⠋⠥⠝⠉⠞⠊⠕⠝: ⠓⠑⠇⠇⠕ - prints greeting"""
        
        return await self.chat(prompt, include_file=False)
        
    def _extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown text"""
        import re
        blocks = []
        pattern = r'```(\w*)\n([\s\S]*?)```'
        
        for match in re.finditer(pattern, text):
            language = match.group(1) or "text"
            code = match.group(2).strip()
            blocks.append({
                "language": language,
                "code": code,
                "braille": self.encoder.encode(code)
            })
            
        return blocks
        
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        
    def get_history(self) -> List[Dict]:
        """Get conversation history as dicts"""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "braille": msg.braille,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in self.conversation_history
        ]


# Global SAL client instance
sal_client = SALClient()


async def check_sal_available() -> bool:
    """Check if SAL model is available in Ollama"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return any("sal" in m for m in models)
    except:
        pass
    return False


# Convenience functions
async def ask_sal(question: str) -> str:
    """Quick question to SAL"""
    response = await sal_client.chat(question, include_file=False)
    return response.text


async def generate_with_sal(instruction: str, language: str = "python") -> str:
    """Generate code with SAL"""
    response = await sal_client.generate_code(instruction, language)
    if response.code_blocks:
        return response.code_blocks[0]["code"]
    return response.text
