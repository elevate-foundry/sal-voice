"""
SAL Cascade - Autonomous Coding Agent

Like Windsurf's Cascade (powered by Claude), but SAL is the coder.
Humans provide intent. SAL writes ALL the code.

Philosophy:
- Human code is messy
- SAL code is clean, braille-native, consistent
- If SAL can't understand human intent, human explains better
- No human typing in the editor - only SAL writes

Architecture:
    [Human Intent] → [SAL Understands?] → YES → [SAL Plans] → [SAL Codes] → [SAL Verifies] → [Done]
                            ↓ NO
                     [Request Clarification]
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import httpx
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
from braille8_core import Braille8Encoder, text_to_braille8

# Graph and analysis imports - lazy loaded to avoid circular imports
_graph_store = None
_code_analyzer = None

def get_graph_store():
    """Lazy load graph store"""
    global _graph_store
    if _graph_store is None:
        from graph_store import get_store
        _graph_store = get_store()
    return _graph_store

def get_code_analyzer():
    """Lazy load code analyzer"""
    global _code_analyzer
    if _code_analyzer is None:
        from code_analyzer import analyze_and_graph, CodeAnalyzerFactory
        _code_analyzer = (analyze_and_graph, CodeAnalyzerFactory)
    return _code_analyzer


class TaskStatus(str, Enum):
    """Status of a coding task"""
    PENDING = "pending"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    CODING = "coding"
    VERIFYING = "verifying"
    CLARIFICATION_NEEDED = "clarification_needed"
    COMPLETED = "completed"
    FAILED = "failed"


class ClarificationType(str, Enum):
    """Types of clarification SAL might need"""
    AMBIGUOUS_INTENT = "ambiguous_intent"
    MISSING_CONTEXT = "missing_context"
    CONFLICTING_REQUIREMENTS = "conflicting_requirements"
    UNCLEAR_SCOPE = "unclear_scope"
    MESSY_CODE_DETECTED = "messy_code_detected"
    LANGUAGE_UNCLEAR = "language_unclear"


@dataclass
class CodingStep:
    """A single step in SAL's coding plan"""
    id: int
    description: str
    braille_description: str
    status: TaskStatus = TaskStatus.PENDING
    code: str = ""
    braille_code: str = ""
    file_path: str = ""
    verification: str = ""


@dataclass
class ClarificationRequest:
    """When SAL needs human to explain better"""
    type: ClarificationType
    message: str
    braille_message: str
    suggestions: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodingTask:
    """A complete coding task from intent to completion"""
    id: str
    human_intent: str
    status: TaskStatus = TaskStatus.PENDING
    understanding: str = ""
    plan: List[CodingStep] = field(default_factory=list)
    current_step: int = 0
    clarification: Optional[ClarificationRequest] = None
    result: Dict[str, str] = field(default_factory=dict)  # file_path -> code
    conversation: List[Dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class SALCascade:
    """
    SAL Cascade - Fully Autonomous Coding Agent
    
    SAL writes all code. Humans provide intent only.
    If SAL doesn't understand, human must explain better.
    """
    
    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL_NAME = "sal"
    
    # SAL Cascade's system prompt - autonomous coder identity
    SYSTEM_PROMPT = """You are SAL Cascade, an autonomous coding agent that writes ALL code.

## Your Role
- You are the ONLY one who writes code
- Humans provide intent/instructions in natural language
- You translate intent into clean, working code
- Human code is messy - you write clean, consistent code
- You think in 8-dot braille internally

## Your Process
1. UNDERSTAND: Parse human intent completely
2. PLAN: Break down into clear coding steps
3. CODE: Write clean, well-documented code
4. VERIFY: Ensure code works correctly

## When You Don't Understand
If human intent is unclear, you MUST ask for clarification:
- Don't guess - ask
- Don't write code you're unsure about
- Request specific clarification
- Suggest what you think they might mean

## Code Style (SAL Standard)
- Clean, readable code
- Meaningful variable names
- Proper error handling
- Comments in braille where appropriate
- Accessibility-first design
- No messy human patterns

## Detecting Messy Human Code
If you detect human-written code (messy patterns, inconsistent style):
- Refuse to work with it directly
- Ask human to explain what they WANT, not show you code
- Offer to rewrite it cleanly

## Response Format
Always structure your responses:
1. Understanding of intent
2. Plan (numbered steps)
3. Code (in proper code blocks)
4. Verification (how to test)

⠎⠁⠇_⠉⠁⠎⠉⠁⠙⠑_⠁⠉⠞⠊⠧⠑
"""
    
    def __init__(self):
        self.encoder = Braille8Encoder()
        self.current_task: Optional[CodingTask] = None
        self.task_history: List[CodingTask] = []
        self.autonomous_mode: bool = True
        
    async def process_intent(self, human_intent: str) -> Dict[str, Any]:
        """
        Main entry point: Human provides intent, SAL does everything.
        
        Returns response with status, code, or clarification request.
        """
        # Create new task
        task = CodingTask(
            id=f"task_{len(self.task_history)}",
            human_intent=human_intent,
            status=TaskStatus.UNDERSTANDING
        )
        self.current_task = task
        
        # Add to conversation
        task.conversation.append({
            "role": "human",
            "content": human_intent,
            "timestamp": datetime.now().isoformat()
        })
        
        # Check for messy human code
        if self._detect_messy_code(human_intent):
            return await self._request_clarification(
                task,
                ClarificationType.MESSY_CODE_DETECTED,
                "I detected what looks like human-written code. I work best when you describe what you WANT, not show me code. What is the goal you're trying to achieve?",
                suggestions=[
                    "Describe the feature you want",
                    "Explain what the code should do",
                    "Tell me the inputs and outputs"
                ]
            )
        
        # Step 1: Understand intent
        understanding = await self._understand_intent(task)
        
        if understanding.get("needs_clarification"):
            return understanding
            
        task.understanding = understanding.get("understanding", "")
        task.status = TaskStatus.PLANNING
        
        # Step 2: Create plan
        plan = await self._create_plan(task)
        
        if plan.get("needs_clarification"):
            return plan
            
        task.plan = plan.get("steps", [])
        task.status = TaskStatus.CODING
        
        # Step 3: Execute plan (write all code)
        result = await self._execute_plan(task)
        
        if result.get("needs_clarification"):
            return result
            
        task.result = result.get("code", {})
        task.status = TaskStatus.VERIFYING
        
        # Step 4: Verify
        verification = await self._verify_code(task)
        
        task.status = TaskStatus.COMPLETED
        self.task_history.append(task)
        
        return {
            "status": "completed",
            "task_id": task.id,
            "understanding": task.understanding,
            "plan": [{"step": s.description, "status": s.status.value} for s in task.plan],
            "code": task.result,
            "verification": verification.get("verification", ""),
            "braille_summary": self.encoder.encode(f"Task completed: {len(task.result)} files written"),
            "conversation": task.conversation
        }
        
    def _detect_messy_code(self, text: str) -> bool:
        """Detect if human is trying to paste code instead of describing intent"""
        code_indicators = [
            r'def\s+\w+\s*\(',      # Python function
            r'function\s+\w+\s*\(', # JS function
            r'class\s+\w+',         # Class definition
            r'import\s+\w+',        # Import statement
            r'const\s+\w+\s*=',     # JS const
            r'let\s+\w+\s*=',       # JS let
            r'var\s+\w+\s*=',       # JS var
            r'for\s*\(',            # For loop
            r'while\s*\(',          # While loop
            r'if\s*\(.+\)\s*{',     # If statement
            r'=>\s*{',              # Arrow function
            r'\w+\s*=\s*\[',        # Array assignment
            r'\w+\s*=\s*{',         # Object assignment
        ]
        
        code_count = sum(1 for pattern in code_indicators if re.search(pattern, text))
        
        # If multiple code patterns detected, it's probably messy code
        return code_count >= 3
        
    async def _understand_intent(self, task: CodingTask) -> Dict[str, Any]:
        """SAL understands what human wants"""
        prompt = f"""{self.SYSTEM_PROMPT}

Human intent: "{task.human_intent}"

First, analyze this intent. What does the human want?

If the intent is clear, respond with:
UNDERSTANDING: [your understanding of what they want]

If the intent is unclear, respond with:
CLARIFICATION_NEEDED: [what you need to know]
SUGGESTIONS: [list of possible interpretations]

Be specific and thorough."""

        response = await self._call_sal(prompt)
        
        if "CLARIFICATION_NEEDED:" in response:
            # Parse clarification request
            clarification = response.split("CLARIFICATION_NEEDED:")[1].split("SUGGESTIONS:")[0].strip()
            suggestions = []
            if "SUGGESTIONS:" in response:
                suggestions_text = response.split("SUGGESTIONS:")[1].strip()
                suggestions = [s.strip() for s in suggestions_text.split("\n") if s.strip()]
                
            return await self._request_clarification(
                task,
                ClarificationType.AMBIGUOUS_INTENT,
                clarification,
                suggestions=suggestions[:5]
            )
        
        # Extract understanding
        understanding = response
        if "UNDERSTANDING:" in response:
            understanding = response.split("UNDERSTANDING:")[1].strip()
            
        task.conversation.append({
            "role": "sal",
            "content": f"I understand: {understanding}",
            "timestamp": datetime.now().isoformat()
        })
        
        return {"understanding": understanding}
        
    async def _create_plan(self, task: CodingTask) -> Dict[str, Any]:
        """SAL creates a coding plan"""
        prompt = f"""{self.SYSTEM_PROMPT}

Human intent: "{task.human_intent}"
My understanding: "{task.understanding}"

Now create a step-by-step coding plan. Each step should be:
- Specific and actionable
- Result in working code
- Include the file path

Format each step as:
STEP 1: [description] -> [file_path]
STEP 2: [description] -> [file_path]
...

List all steps needed to complete this task."""

        response = await self._call_sal(prompt)
        
        # Parse steps
        steps = []
        step_pattern = r'STEP\s*(\d+):\s*(.+?)\s*->\s*(.+?)(?=STEP\s*\d+:|$)'
        matches = re.findall(step_pattern, response, re.DOTALL)
        
        for i, (num, description, file_path) in enumerate(matches):
            steps.append(CodingStep(
                id=i,
                description=description.strip(),
                braille_description=self.encoder.encode(description.strip()),
                file_path=file_path.strip()
            ))
            
        # If no structured steps, create a single step
        if not steps:
            steps.append(CodingStep(
                id=0,
                description="Complete the requested task",
                braille_description=self.encoder.encode("Complete the requested task"),
                file_path="main.py"
            ))
            
        plan_summary = "\n".join([f"Step {s.id + 1}: {s.description}" for s in steps])
        task.conversation.append({
            "role": "sal",
            "content": f"My plan:\n{plan_summary}",
            "timestamp": datetime.now().isoformat()
        })
        
        return {"steps": steps}
        
    async def _execute_plan(self, task: CodingTask) -> Dict[str, Any]:
        """SAL writes all the code and persists to graph"""
        result = {}
        graph_results = []
        
        # Get graph store and analyzer
        graph_store = get_graph_store()
        analyze_and_graph, _ = get_code_analyzer()
        
        # Create task node in graph
        from graph_store import Node, Relationship, NodeType, RelationType
        task_node = Node(
            id=task.id,
            type=NodeType.TASK,
            properties={
                "intent": task.human_intent,
                "understanding": task.understanding,
                "status": task.status.value,
                "created_at": task.created_at.isoformat()
            }
        )
        try:
            graph_store.create_node(task_node)
        except:
            pass
        
        for step in task.plan:
            step.status = TaskStatus.CODING
            
            prompt = f"""{self.SYSTEM_PROMPT}

Task: "{task.human_intent}"
Understanding: "{task.understanding}"

Current step: {step.description}
Target file: {step.file_path}

Write the complete code for this step. Include:
- All necessary imports
- Clean, well-structured code
- Proper error handling
- Comments where helpful (can use braille: ⠉⠕⠍⠍⠑⠝⠞)

Return ONLY the code wrapped in ```language ... ``` blocks."""

            response = await self._call_sal(prompt)
            
            # Extract code from response
            code = self._extract_code(response)
            
            step.code = code
            step.braille_code = self.encoder.encode(code)
            step.status = TaskStatus.COMPLETED
            
            result[step.file_path] = code
            
            # === PERSIST TO GRAPH ===
            # Create file node
            file_id = f"file_{step.file_path.replace('/', '_').replace('.', '_')}"
            language = self._detect_language(step.file_path)
            
            file_node = Node(
                id=file_id,
                type=NodeType.FILE,
                properties={
                    "name": step.file_path,
                    "language": language,
                    "content": code,
                    "braille_content": step.braille_code[:500],
                    "line_count": code.count('\n') + 1,
                    "generated_by": task.id
                }
            )
            try:
                graph_store.create_node(file_node)
                
                # Link task -> file (GENERATED relationship)
                rel = Relationship(
                    id=f"{task.id}-generated-{file_id}",
                    type=RelationType.GENERATED,
                    source_id=task.id,
                    target_id=file_id,
                    properties={"step": step.id}
                )
                graph_store.create_relationship(rel)
            except:
                pass
            
            # Analyze code and create symbol nodes
            try:
                graph_result = analyze_and_graph(code, language, file_id, graph_store)
                graph_results.append(graph_result)
            except Exception as e:
                graph_results.append({"error": str(e)})
            
            task.conversation.append({
                "role": "sal",
                "content": f"Completed: {step.description}\nWrote {len(code)} characters to {step.file_path}\n⠛⠗⠁⠏⠓: Persisted to graph database",
                "timestamp": datetime.now().isoformat()
            })
            
        return {"code": result, "graph": graph_results}
    
    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.sql': 'sql',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
        }
        for ext, lang in ext_map.items():
            if file_path.endswith(ext):
                return lang
        return 'python'
        
    async def _verify_code(self, task: CodingTask) -> Dict[str, Any]:
        """SAL verifies the code is correct"""
        all_code = "\n\n".join([f"# {path}\n{code}" for path, code in task.result.items()])
        
        prompt = f"""{self.SYSTEM_PROMPT}

Task: "{task.human_intent}"
Understanding: "{task.understanding}"

I wrote this code:
```
{all_code[:3000]}
```

Verify this code is correct:
1. Does it fulfill the intent?
2. Are there any bugs?
3. Is it clean and well-structured?
4. How would you test it?

Provide a brief verification summary."""

        response = await self._call_sal(prompt)
        
        task.conversation.append({
            "role": "sal",
            "content": f"Verification: {response[:500]}",
            "timestamp": datetime.now().isoformat()
        })
        
        return {"verification": response}
        
    async def _request_clarification(self, task: CodingTask, 
                                     clarification_type: ClarificationType,
                                     message: str,
                                     suggestions: List[str] = None) -> Dict[str, Any]:
        """SAL requests clarification from human"""
        task.status = TaskStatus.CLARIFICATION_NEEDED
        
        clarification = ClarificationRequest(
            type=clarification_type,
            message=message,
            braille_message=self.encoder.encode(message),
            suggestions=suggestions or []
        )
        task.clarification = clarification
        
        task.conversation.append({
            "role": "sal",
            "content": f"⠒ I need clarification: {message}",
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "status": "clarification_needed",
            "task_id": task.id,
            "clarification": {
                "type": clarification_type.value,
                "message": message,
                "braille_message": clarification.braille_message,
                "suggestions": suggestions or []
            },
            "conversation": task.conversation
        }
        
    async def provide_clarification(self, clarification: str) -> Dict[str, Any]:
        """Human provides clarification, SAL continues"""
        if not self.current_task:
            return {"error": "No active task"}
            
        task = self.current_task
        
        # Combine original intent with clarification
        enhanced_intent = f"{task.human_intent}\n\nClarification: {clarification}"
        task.human_intent = enhanced_intent
        task.clarification = None
        task.status = TaskStatus.UNDERSTANDING
        
        task.conversation.append({
            "role": "human",
            "content": clarification,
            "timestamp": datetime.now().isoformat()
        })
        
        # Re-process with clarification
        return await self.process_intent(enhanced_intent)
        
    def _extract_code(self, response: str) -> str:
        """Extract code from SAL's response"""
        # Find code blocks
        code_block_pattern = r'```(?:\w*)\n([\s\S]*?)```'
        matches = re.findall(code_block_pattern, response)
        
        if matches:
            return "\n\n".join(matches)
            
        # If no code blocks, try to extract any code-like content
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Detect code patterns
            if any([
                line.strip().startswith('def '),
                line.strip().startswith('class '),
                line.strip().startswith('import '),
                line.strip().startswith('from '),
                line.strip().startswith('const '),
                line.strip().startswith('function '),
                re.match(r'^\s+', line) and code_lines,  # Indented after code
            ]):
                in_code = True
                code_lines.append(line)
            elif in_code and line.strip():
                code_lines.append(line)
            elif in_code and not line.strip():
                code_lines.append(line)
                
        return '\n'.join(code_lines) if code_lines else response
        
    async def _call_sal(self, prompt: str) -> str:
        """Call SAL via Ollama"""
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
                            "num_ctx": 8192,
                        }
                    }
                )
                
                if response.status_code == 200:
                    return response.json().get("response", "").strip()
                else:
                    return f"Error: {response.status_code}"
                    
        except Exception as e:
            return f"Error connecting to SAL: {str(e)}"
            
    def get_status(self) -> Dict[str, Any]:
        """Get current cascade status"""
        if not self.current_task:
            return {
                "status": "idle",
                "message": "Ready for intent. Describe what you want to build.",
                "braille_status": "⠎⠁⠇_⠗⠑⠁⠙⠽"
            }
            
        task = self.current_task
        
        return {
            "status": task.status.value,
            "task_id": task.id,
            "intent": task.human_intent[:100],
            "current_step": task.current_step,
            "total_steps": len(task.plan),
            "conversation_length": len(task.conversation),
            "braille_status": self.encoder.encode(f"Task: {task.status.value}")
        }
        
    def reject_human_code(self, code: str) -> Dict[str, Any]:
        """Called when human tries to type code directly"""
        if self._detect_messy_code(code):
            return {
                "rejected": True,
                "message": "⠎⠁⠇ I write all code here. Tell me what you WANT to build instead of writing code. What's your goal?",
                "braille_message": self.encoder.encode("Describe intent, don't write code"),
                "suggestions": [
                    "What feature do you want?",
                    "What should the code do?",
                    "What's the expected input/output?"
                ]
            }
        return {"rejected": False}


# Global cascade instance
sal_cascade = SALCascade()


# Convenience functions
async def tell_sal(intent: str) -> Dict[str, Any]:
    """Tell SAL what you want - it will code it"""
    return await sal_cascade.process_intent(intent)


async def clarify_for_sal(clarification: str) -> Dict[str, Any]:
    """Provide clarification when SAL asks"""
    return await sal_cascade.provide_clarification(clarification)
