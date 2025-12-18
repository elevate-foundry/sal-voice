"""
LLM Code Completion Experiment

Test hypothesis with actual LLM (Ollama) - more realistic than n-grams.
Compare completion quality when prompting with ASCII vs Braille context.

⠇⠇⠍_⠉⠕⠍⠏⠇⠑⠞⠊⠕⠝
"""

import os
import sys
import json
import time
import random
import asyncio
import httpx
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder


@dataclass
class CompletionTest:
    """A single completion test case"""
    context: str
    expected: str
    ascii_prediction: str = ""
    braille_prediction: str = ""
    ascii_exact: bool = False
    braille_exact: bool = False
    ascii_similarity: float = 0.0
    braille_similarity: float = 0.0


def calculate_similarity(s1: str, s2: str) -> float:
    """Calculate string similarity (0-1)"""
    if not s1 or not s2:
        return 0.0
    
    # Normalize whitespace
    s1 = ' '.join(s1.split())
    s2 = ' '.join(s2.split())
    
    # Exact match
    if s1.strip() == s2.strip():
        return 1.0
    
    # Check if expected is contained in prediction
    if s2.strip() in s1:
        return 0.9
        
    # Token overlap
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    
    if not tokens1 or not tokens2:
        return 0.0
        
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    
    return len(intersection) / len(union)


class LLMCompletionExperiment:
    """
    Compare code completion with ASCII vs Braille prompts.
    
    The hypothesis: If we train/prompt an LLM with braille-encoded code,
    it might learn different (potentially better) patterns due to the
    256-character encoding space.
    """
    
    def __init__(self, model: str = "sal:latest"):
        self.model = model
        self.encoder = Braille8Encoder()
        self.ollama_url = "http://localhost:11434/api/generate"
        
    async def complete_async(self, prompt: str, max_tokens: int = 50) -> str:
        """Get completion from Ollama"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": 0.1,  # Low temp for deterministic completion
                        }
                    }
                )
                data = response.json()
                return data.get('response', '')
            except Exception as e:
                print(f"Error: {e}")
                return ""
                
    def complete(self, prompt: str, max_tokens: int = 50) -> str:
        """Sync wrapper for completion"""
        return asyncio.run(self.complete_async(prompt, max_tokens))
        
    def create_test_cases(self, code_dir: str = None, num_tests: int = 20) -> List[CompletionTest]:
        """Create test cases from real code"""
        code_dir = Path(code_dir) if code_dir else Path.home() / "sal-voice"
        tests = []
        
        # Collect code snippets
        snippets = []
        for ext in ['.py']:
            for filepath in code_dir.rglob(f"*{ext}"):
                if '.git' in str(filepath) or 'node_modules' in str(filepath):
                    continue
                try:
                    code = filepath.read_text(encoding='utf-8', errors='ignore')
                    # Extract function definitions
                    lines = code.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip().startswith('def ') and i + 5 < len(lines):
                            # Get function signature + first few lines
                            context = '\n'.join(lines[max(0, i-2):i+3])
                            expected = lines[i+3].strip() if i+3 < len(lines) else ""
                            if context and expected and len(expected) > 5:
                                snippets.append((context, expected))
                except:
                    continue
                    
        # Sample test cases
        random.shuffle(snippets)
        for context, expected in snippets[:num_tests]:
            tests.append(CompletionTest(context=context, expected=expected))
            
        print(f"Created {len(tests)} test cases")
        return tests
        
    def run_experiment(self, num_tests: int = 15) -> Dict:
        """Run the LLM completion experiment"""
        print("\n" + "="*70)
        print("LLM CODE COMPLETION EXPERIMENT")
        print("Model:", self.model)
        print("="*70)
        
        # Create test cases
        tests = self.create_test_cases(num_tests=num_tests)
        
        if not tests:
            print("No test cases found!")
            return {}
            
        print(f"\nRunning {len(tests)} completion tests...")
        
        ascii_similarities = []
        braille_similarities = []
        
        for i, test in enumerate(tests):
            print(f"\nTest {i+1}/{len(tests)}")
            
            # ASCII completion
            ascii_prompt = f"""Complete the next line of this Python code:

{test.context}

Next line:"""
            
            test.ascii_prediction = self.complete(ascii_prompt, max_tokens=30)
            test.ascii_similarity = calculate_similarity(test.ascii_prediction, test.expected)
            test.ascii_exact = test.ascii_prediction.strip() == test.expected.strip()
            
            # Braille completion - encode context to braille
            braille_context = self.encoder.encode(test.context)
            braille_prompt = f"""Complete the next line of this code (written in 8-dot braille):

{braille_context}

Next line (in braille):"""
            
            braille_response = self.complete(braille_prompt, max_tokens=50)
            # Decode braille response back to ASCII for comparison
            try:
                test.braille_prediction = self.encoder.decode(braille_response) if braille_response else ""
            except:
                test.braille_prediction = braille_response
                
            test.braille_similarity = calculate_similarity(test.braille_prediction, test.expected)
            test.braille_exact = test.braille_prediction.strip() == test.expected.strip()
            
            ascii_similarities.append(test.ascii_similarity)
            braille_similarities.append(test.braille_similarity)
            
            print(f"  Expected: {test.expected[:50]}...")
            print(f"  ASCII sim: {test.ascii_similarity:.2f}, Braille sim: {test.braille_similarity:.2f}")
            
        # Calculate results
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        
        avg_ascii = statistics.mean(ascii_similarities)
        avg_braille = statistics.mean(braille_similarities)
        
        ascii_exact_count = sum(1 for t in tests if t.ascii_exact)
        braille_exact_count = sum(1 for t in tests if t.braille_exact)
        
        print(f"\n  Samples: {len(tests)}")
        print(f"\n  Average Similarity Score:")
        print(f"    ASCII:   {avg_ascii:.3f}")
        print(f"    Braille: {avg_braille:.3f}")
        print(f"\n  Exact Matches:")
        print(f"    ASCII:   {ascii_exact_count}/{len(tests)}")
        print(f"    Braille: {braille_exact_count}/{len(tests)}")
        
        # Determine winner
        if avg_braille > avg_ascii:
            improvement = (avg_braille - avg_ascii) / avg_ascii * 100 if avg_ascii > 0 else 0
            print(f"\n  ✓ BRAILLE WINS: {improvement:.1f}% higher similarity")
            conclusion = "braille_better"
        elif avg_ascii > avg_braille:
            improvement = (avg_ascii - avg_braille) / avg_braille * 100 if avg_braille > 0 else 0
            print(f"\n  ✗ ASCII WINS: {improvement:.1f}% higher similarity")
            conclusion = "ascii_better"
        else:
            print(f"\n  = TIE")
            conclusion = "tie"
            
        # Statistical test
        try:
            from scipy import stats
            t_stat, p_value = stats.ttest_rel(braille_similarities, ascii_similarities)
            print(f"\n  Statistical significance:")
            print(f"    t-statistic: {t_stat:.3f}")
            print(f"    p-value: {p_value:.4f}")
            print(f"    {'Significant (p < 0.05)' if p_value < 0.05 else 'Not significant'}")
        except:
            p_value = None
            
        # Save results
        results = {
            'experiment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'model': self.model,
            'num_tests': len(tests),
            'ascii_avg_similarity': avg_ascii,
            'braille_avg_similarity': avg_braille,
            'ascii_exact_matches': ascii_exact_count,
            'braille_exact_matches': braille_exact_count,
            'p_value': p_value,
            'conclusion': conclusion,
            'test_details': [
                {
                    'context_preview': t.context[:100],
                    'expected': t.expected,
                    'ascii_prediction': t.ascii_prediction[:100],
                    'braille_prediction': t.braille_prediction[:100],
                    'ascii_similarity': t.ascii_similarity,
                    'braille_similarity': t.braille_similarity,
                }
                for t in tests
            ]
        }
        
        results_path = Path(__file__).parent / "llm_completion_results.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
            
        print(f"\nResults saved to: {results_path}")
        print("\n⠇⠇⠍_⠉⠕⠍⠏⠇⠑⠞⠊⠕⠝_⠙⠕⠝⠑")
        
        return results


if __name__ == "__main__":
    experiment = LLMCompletionExperiment(model="sal:latest")
    results = experiment.run_experiment(num_tests=10)
