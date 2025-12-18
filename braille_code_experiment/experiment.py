"""
Braille Code Representation Experiment

Research Question: Is 8-dot braille a more efficient representation for code than ASCII?

Hypotheses:
H1: Braille encoding requires fewer tokens per program than ASCII
H2: Braille-encoded context can hold more semantic information
H3: Pattern recognition is enhanced by braille's dot-matrix structure
H4: Code completion accuracy improves with braille representation

Methodology:
1. Token Efficiency: Compare tokens required for same code in ASCII vs Braille
2. Semantic Density: Measure information per token
3. Context Capacity: Compare effective context length
4. Completion Accuracy: Test code completion with both representations

⠃⠗⠁⠊⠇⠇⠑_⠉⠕⠙⠑_⠑⠭⠏⠑⠗⠊⠍⠑⠝⠞
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from collections import Counter
import statistics
import hashlib

# Add parent paths
sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder, text_to_braille8

# Transformers for tokenization comparison
try:
    from transformers import AutoTokenizer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False


@dataclass
class ExperimentResult:
    """Result from a single experiment"""
    experiment_name: str
    ascii_value: float
    braille_value: float
    improvement_ratio: float  # braille_value / ascii_value (< 1 means braille is better)
    p_value: Optional[float] = None
    sample_size: int = 0
    details: Dict = field(default_factory=dict)


@dataclass
class CodeSample:
    """A code sample for testing"""
    filename: str
    language: str
    ascii_code: str
    braille_code: str = ""
    ascii_tokens: int = 0
    braille_tokens: int = 0
    
    def __post_init__(self):
        if not self.braille_code:
            encoder = Braille8Encoder()
            self.braille_code = encoder.encode(self.ascii_code)


class BrailleCodeExperiment:
    """
    Comprehensive experiment to test if 8-dot braille is a better
    representation for code than ASCII.
    """
    
    def __init__(self, code_dir: str = None):
        self.encoder = Braille8Encoder()
        self.code_dir = Path(code_dir) if code_dir else Path.home() / "sal-voice"
        self.results: List[ExperimentResult] = []
        self.samples: List[CodeSample] = []
        
        # Load tokenizers for comparison
        self.tokenizers = {}
        if HAS_TRANSFORMERS:
            try:
                self.tokenizers['llama'] = AutoTokenizer.from_pretrained(
                    "meta-llama/Llama-2-7b-hf", 
                    token=os.environ.get('HF_TOKEN'),
                    trust_remote_code=True
                )
            except:
                pass
            try:
                self.tokenizers['gpt2'] = AutoTokenizer.from_pretrained("gpt2")
            except:
                pass
                
    def collect_code_samples(self, max_files: int = 100) -> List[CodeSample]:
        """Collect code samples from the codebase"""
        samples = []
        extensions = {'.py': 'python', '.js': 'javascript', '.ts': 'typescript', 
                      '.go': 'go', '.rs': 'rust', '.java': 'java'}
        
        for ext, lang in extensions.items():
            for filepath in self.code_dir.rglob(f"*{ext}"):
                if len(samples) >= max_files:
                    break
                if '.git' in str(filepath) or 'node_modules' in str(filepath):
                    continue
                    
                try:
                    code = filepath.read_text(encoding='utf-8', errors='ignore')
                    if len(code) > 100:  # Skip tiny files
                        samples.append(CodeSample(
                            filename=str(filepath),
                            language=lang,
                            ascii_code=code[:10000]  # Cap at 10K chars
                        ))
                except:
                    continue
                    
        self.samples = samples
        print(f"Collected {len(samples)} code samples")
        return samples
        
    def experiment_1_token_efficiency(self) -> ExperimentResult:
        """
        H1: Braille encoding requires fewer tokens per program than ASCII
        
        Measure: tokens_needed(braille) / tokens_needed(ascii)
        """
        print("\n" + "="*60)
        print("EXPERIMENT 1: Token Efficiency")
        print("="*60)
        
        if not self.tokenizers:
            print("No tokenizers available - using character-based estimation")
            # Fallback: estimate tokens as chars/4
            ascii_tokens = []
            braille_tokens = []
            
            for sample in self.samples:
                ascii_tok = len(sample.ascii_code) / 4
                braille_tok = len(sample.braille_code) / 4
                ascii_tokens.append(ascii_tok)
                braille_tokens.append(braille_tok)
                sample.ascii_tokens = int(ascii_tok)
                sample.braille_tokens = int(braille_tok)
        else:
            tokenizer = self.tokenizers.get('gpt2') or list(self.tokenizers.values())[0]
            ascii_tokens = []
            braille_tokens = []
            
            for sample in self.samples:
                ascii_tok = len(tokenizer.encode(sample.ascii_code))
                braille_tok = len(tokenizer.encode(sample.braille_code))
                ascii_tokens.append(ascii_tok)
                braille_tokens.append(braille_tok)
                sample.ascii_tokens = ascii_tok
                sample.braille_tokens = braille_tok
                
        avg_ascii = statistics.mean(ascii_tokens)
        avg_braille = statistics.mean(braille_tokens)
        ratio = avg_braille / avg_ascii
        
        # Statistical significance
        from scipy import stats
        try:
            t_stat, p_value = stats.ttest_rel(braille_tokens, ascii_tokens)
        except:
            p_value = None
            
        result = ExperimentResult(
            experiment_name="Token Efficiency",
            ascii_value=avg_ascii,
            braille_value=avg_braille,
            improvement_ratio=ratio,
            p_value=p_value,
            sample_size=len(self.samples),
            details={
                'ascii_tokens_total': sum(ascii_tokens),
                'braille_tokens_total': sum(braille_tokens),
                'ascii_tokens_std': statistics.stdev(ascii_tokens) if len(ascii_tokens) > 1 else 0,
                'braille_tokens_std': statistics.stdev(braille_tokens) if len(braille_tokens) > 1 else 0,
            }
        )
        
        print(f"  ASCII avg tokens:   {avg_ascii:.1f}")
        print(f"  Braille avg tokens: {avg_braille:.1f}")
        print(f"  Ratio (braille/ascii): {ratio:.3f}")
        print(f"  {'✓ Braille more efficient' if ratio < 1 else '✗ ASCII more efficient'}")
        if p_value:
            print(f"  p-value: {p_value:.4f} {'(significant)' if p_value < 0.05 else ''}")
            
        self.results.append(result)
        return result
        
    def experiment_2_semantic_density(self) -> ExperimentResult:
        """
        H2: Braille-encoded context can hold more semantic information
        
        Measure: unique_symbols / total_chars (information density)
        """
        print("\n" + "="*60)
        print("EXPERIMENT 2: Semantic Density")
        print("="*60)
        
        ascii_densities = []
        braille_densities = []
        
        for sample in self.samples:
            # ASCII: count unique characters / total
            ascii_unique = len(set(sample.ascii_code))
            ascii_total = len(sample.ascii_code)
            ascii_density = ascii_unique / ascii_total if ascii_total > 0 else 0
            
            # Braille: count unique braille chars / total
            braille_unique = len(set(sample.braille_code))
            braille_total = len(sample.braille_code)
            braille_density = braille_unique / braille_total if braille_total > 0 else 0
            
            ascii_densities.append(ascii_density)
            braille_densities.append(braille_density)
            
        avg_ascii = statistics.mean(ascii_densities)
        avg_braille = statistics.mean(braille_densities)
        ratio = avg_braille / avg_ascii if avg_ascii > 0 else 1
        
        result = ExperimentResult(
            experiment_name="Semantic Density",
            ascii_value=avg_ascii,
            braille_value=avg_braille,
            improvement_ratio=ratio,
            sample_size=len(self.samples),
            details={
                'ascii_charset_avg': statistics.mean([len(set(s.ascii_code)) for s in self.samples]),
                'braille_charset_avg': statistics.mean([len(set(s.braille_code)) for s in self.samples]),
            }
        )
        
        print(f"  ASCII density:   {avg_ascii:.4f}")
        print(f"  Braille density: {avg_braille:.4f}")
        print(f"  Ratio: {ratio:.3f}")
        print(f"  {'✓ Braille more dense' if ratio > 1 else '✗ ASCII more dense'}")
        
        self.results.append(result)
        return result
        
    def experiment_3_compression_ratio(self) -> ExperimentResult:
        """
        Measure actual compression ratios
        """
        print("\n" + "="*60)
        print("EXPERIMENT 3: Compression Ratio")
        print("="*60)
        
        import zlib
        
        ascii_ratios = []
        braille_ratios = []
        
        for sample in self.samples:
            # Compress ASCII
            ascii_bytes = sample.ascii_code.encode('utf-8')
            ascii_compressed = zlib.compress(ascii_bytes)
            ascii_ratio = len(ascii_compressed) / len(ascii_bytes)
            
            # Compress Braille
            braille_bytes = sample.braille_code.encode('utf-8')
            braille_compressed = zlib.compress(braille_bytes)
            braille_ratio = len(braille_compressed) / len(braille_bytes)
            
            ascii_ratios.append(ascii_ratio)
            braille_ratios.append(braille_ratio)
            
        avg_ascii = statistics.mean(ascii_ratios)
        avg_braille = statistics.mean(braille_ratios)
        ratio = avg_braille / avg_ascii
        
        result = ExperimentResult(
            experiment_name="Compression Ratio",
            ascii_value=avg_ascii,
            braille_value=avg_braille,
            improvement_ratio=ratio,
            sample_size=len(self.samples),
            details={
                'interpretation': 'Lower is better (more compressible = more redundancy)',
            }
        )
        
        print(f"  ASCII compression:   {avg_ascii:.4f}")
        print(f"  Braille compression: {avg_braille:.4f}")
        print(f"  Ratio: {ratio:.3f}")
        
        self.results.append(result)
        return result
        
    def experiment_4_pattern_frequency(self) -> ExperimentResult:
        """
        H3: Pattern recognition is enhanced by braille's dot-matrix structure
        
        Measure: frequency of repeated patterns (n-grams)
        """
        print("\n" + "="*60)
        print("EXPERIMENT 4: Pattern Frequency (N-grams)")
        print("="*60)
        
        def count_ngrams(text: str, n: int) -> Counter:
            return Counter(text[i:i+n] for i in range(len(text) - n + 1))
        
        ascii_pattern_counts = []
        braille_pattern_counts = []
        
        for sample in self.samples:
            # Count 3-grams (common pattern length)
            ascii_ngrams = count_ngrams(sample.ascii_code, 3)
            braille_ngrams = count_ngrams(sample.braille_code, 3)
            
            # Count patterns that appear 3+ times (meaningful patterns)
            ascii_patterns = sum(1 for c in ascii_ngrams.values() if c >= 3)
            braille_patterns = sum(1 for c in braille_ngrams.values() if c >= 3)
            
            ascii_pattern_counts.append(ascii_patterns)
            braille_pattern_counts.append(braille_patterns)
            
        avg_ascii = statistics.mean(ascii_pattern_counts)
        avg_braille = statistics.mean(braille_pattern_counts)
        ratio = avg_braille / avg_ascii if avg_ascii > 0 else 1
        
        result = ExperimentResult(
            experiment_name="Pattern Frequency",
            ascii_value=avg_ascii,
            braille_value=avg_braille,
            improvement_ratio=ratio,
            sample_size=len(self.samples),
            details={
                'interpretation': 'Higher = more learnable patterns',
            }
        )
        
        print(f"  ASCII repeated patterns:   {avg_ascii:.1f}")
        print(f"  Braille repeated patterns: {avg_braille:.1f}")
        print(f"  Ratio: {ratio:.3f}")
        print(f"  {'✓ Braille more patterns' if ratio > 1 else '✗ ASCII more patterns'}")
        
        self.results.append(result)
        return result
        
    def experiment_5_8bit_utilization(self) -> ExperimentResult:
        """
        Measure how well each encoding uses the available bit space
        
        ASCII: 7 bits used (128 chars), but code uses ~30-40 common chars
        Braille: 8 bits available (256 chars)
        """
        print("\n" + "="*60)
        print("EXPERIMENT 5: Bit Space Utilization")
        print("="*60)
        
        ascii_utilizations = []
        braille_utilizations = []
        
        for sample in self.samples:
            # ASCII: unique chars / 128 possible
            ascii_unique = len(set(sample.ascii_code))
            ascii_util = ascii_unique / 128
            
            # Braille: unique chars / 256 possible  
            braille_unique = len(set(sample.braille_code))
            braille_util = braille_unique / 256
            
            ascii_utilizations.append(ascii_util)
            braille_utilizations.append(braille_util)
            
        avg_ascii = statistics.mean(ascii_utilizations)
        avg_braille = statistics.mean(braille_utilizations)
        
        # For this metric, we want to measure effective use
        # ASCII wastes ~90 chars, braille uses the full 256
        ascii_effective = avg_ascii * 128  # chars actually used
        braille_effective = avg_braille * 256
        
        result = ExperimentResult(
            experiment_name="Bit Space Utilization",
            ascii_value=avg_ascii,
            braille_value=avg_braille,
            improvement_ratio=avg_braille / avg_ascii if avg_ascii > 0 else 1,
            sample_size=len(self.samples),
            details={
                'ascii_chars_used': ascii_effective,
                'braille_chars_used': braille_effective,
                'ascii_wasted_capacity': 128 - ascii_effective,
                'braille_wasted_capacity': 256 - braille_effective,
            }
        )
        
        print(f"  ASCII utilization:   {avg_ascii:.2%} of 128 chars")
        print(f"  Braille utilization: {avg_braille:.2%} of 256 chars")
        print(f"  ASCII chars used:    {ascii_effective:.1f}")
        print(f"  Braille chars used:  {braille_effective:.1f}")
        
        self.results.append(result)
        return result
        
    def experiment_6_structural_encoding(self) -> ExperimentResult:
        """
        Test if braille's dot-matrix structure encodes syntactic structure
        
        In 8-dot braille, dots 7-8 can encode metadata (uppercase, numbers)
        This could map to code structure (keywords, identifiers, literals)
        """
        print("\n" + "="*60)
        print("EXPERIMENT 6: Structural Encoding")
        print("="*60)
        
        # Analyze how dot 7 and dot 8 correlate with code structure
        dot7_keywords = 0  # Upper dots for keywords
        dot8_numbers = 0   # Lower dots for numbers
        total_braille = 0
        
        keywords = {'def', 'class', 'if', 'else', 'for', 'while', 'return', 
                    'import', 'from', 'try', 'except', 'with', 'as', 'in',
                    'and', 'or', 'not', 'True', 'False', 'None', 'async', 'await'}
        
        for sample in self.samples:
            words = sample.ascii_code.split()
            for i, word in enumerate(words):
                if word in keywords:
                    # Check if braille encoding uses dot 7
                    braille_word = self.encoder.encode(word)
                    for char in braille_word:
                        if ord(char) >= 0x2800:
                            dots = ord(char) - 0x2800
                            if dots & 0x40:  # Dot 7
                                dot7_keywords += 1
                            total_braille += 1
                            
                if word.isdigit():
                    braille_word = self.encoder.encode(word)
                    for char in braille_word:
                        if ord(char) >= 0x2800:
                            dots = ord(char) - 0x2800
                            if dots & 0x80:  # Dot 8
                                dot8_numbers += 1
                            total_braille += 1
                            
        keyword_ratio = dot7_keywords / total_braille if total_braille > 0 else 0
        number_ratio = dot8_numbers / total_braille if total_braille > 0 else 0
        
        result = ExperimentResult(
            experiment_name="Structural Encoding",
            ascii_value=0,  # ASCII has no structural encoding
            braille_value=keyword_ratio + number_ratio,
            improvement_ratio=float('inf') if keyword_ratio + number_ratio > 0 else 1,
            sample_size=len(self.samples),
            details={
                'dot7_keyword_correlation': keyword_ratio,
                'dot8_number_correlation': number_ratio,
                'total_braille_chars_analyzed': total_braille,
            }
        )
        
        print(f"  Dot 7 (keywords) correlation: {keyword_ratio:.4f}")
        print(f"  Dot 8 (numbers) correlation:  {number_ratio:.4f}")
        print(f"  Total structural encoding:    {keyword_ratio + number_ratio:.4f}")
        print(f"  {'✓ Braille encodes structure' if keyword_ratio + number_ratio > 0.1 else '⚠ Weak structural encoding'}")
        
        self.results.append(result)
        return result
        
    def run_all_experiments(self) -> Dict:
        """Run all experiments and generate summary"""
        print("\n" + "="*60)
        print("BRAILLE CODE REPRESENTATION EXPERIMENT")
        print("Research Question: Is 8-dot braille better for code?")
        print("="*60)
        
        # Collect samples
        if not self.samples:
            self.collect_code_samples()
            
        # Run experiments
        self.experiment_1_token_efficiency()
        self.experiment_2_semantic_density()
        self.experiment_3_compression_ratio()
        self.experiment_4_pattern_frequency()
        self.experiment_5_8bit_utilization()
        self.experiment_6_structural_encoding()
        
        # Generate summary
        summary = self.generate_summary()
        
        return summary
        
    def generate_summary(self) -> Dict:
        """Generate summary of all experiments"""
        print("\n" + "="*60)
        print("SUMMARY: Braille vs ASCII for Code Representation")
        print("="*60)
        
        braille_wins = 0
        ascii_wins = 0
        
        for result in self.results:
            if result.experiment_name in ["Token Efficiency", "Compression Ratio"]:
                # Lower is better
                if result.improvement_ratio < 1:
                    braille_wins += 1
                    print(f"  ✓ {result.experiment_name}: Braille wins ({result.improvement_ratio:.3f})")
                else:
                    ascii_wins += 1
                    print(f"  ✗ {result.experiment_name}: ASCII wins ({result.improvement_ratio:.3f})")
            else:
                # Higher is better
                if result.improvement_ratio > 1:
                    braille_wins += 1
                    print(f"  ✓ {result.experiment_name}: Braille wins ({result.improvement_ratio:.3f})")
                else:
                    ascii_wins += 1
                    print(f"  ✗ {result.experiment_name}: ASCII wins ({result.improvement_ratio:.3f})")
                    
        print("\n" + "-"*60)
        print(f"  BRAILLE WINS: {braille_wins}")
        print(f"  ASCII WINS:   {ascii_wins}")
        print("-"*60)
        
        conclusion = "BRAILLE SUPERIOR" if braille_wins > ascii_wins else "ASCII SUPERIOR" if ascii_wins > braille_wins else "INCONCLUSIVE"
        print(f"\n  CONCLUSION: {conclusion}")
        
        summary = {
            'total_samples': len(self.samples),
            'braille_wins': braille_wins,
            'ascii_wins': ascii_wins,
            'conclusion': conclusion,
            'results': [
                {
                    'experiment': r.experiment_name,
                    'ascii_value': r.ascii_value,
                    'braille_value': r.braille_value,
                    'ratio': r.improvement_ratio,
                    'p_value': r.p_value,
                    'details': r.details,
                }
                for r in self.results
            ]
        }
        
        return summary
        
    def save_results(self, output_path: str = None):
        """Save results to JSON for paper"""
        output_path = output_path or str(Path(__file__).parent / "experiment_results.json")
        
        summary = {
            'experiment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_samples': len(self.samples),
            'results': [
                {
                    'experiment': r.experiment_name,
                    'ascii_value': r.ascii_value,
                    'braille_value': r.braille_value,
                    'improvement_ratio': r.improvement_ratio,
                    'p_value': r.p_value,
                    'sample_size': r.sample_size,
                    'details': r.details,
                }
                for r in self.results
            ],
            'samples': [
                {
                    'filename': s.filename,
                    'language': s.language,
                    'ascii_tokens': s.ascii_tokens,
                    'braille_tokens': s.braille_tokens,
                    'ascii_len': len(s.ascii_code),
                    'braille_len': len(s.braille_code),
                }
                for s in self.samples[:50]  # Save subset
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
            
        print(f"\nResults saved to: {output_path}")
        return output_path


if __name__ == "__main__":
    experiment = BrailleCodeExperiment()
    experiment.collect_code_samples(max_files=50)
    summary = experiment.run_all_experiments()
    experiment.save_results()
    
    print("\n⠃⠗⠁⠊⠇⠇⠑_⠑⠭⠏⠑⠗⠊⠍⠑⠝⠞_⠉⠕⠍⠏⠇⠑⠞⠑")
