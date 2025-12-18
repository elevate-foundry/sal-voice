"""
Code Completion Accuracy Experiment

Hypothesis: 8-dot braille representation enables better code completion
because the 256-character space encodes richer structural patterns.

Method:
1. Take code samples, mask the last N tokens
2. Use n-gram model to predict completions in both ASCII and Braille
3. Compare accuracy (exact match, edit distance, semantic similarity)

⠉⠕⠍⠏⠇⠑⠞⠊⠕⠝_⠑⠭⠏⠑⠗⠊⠍⠑⠝⠞
"""

import os
import sys
import json
import time
import random
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder

# Import our tokenizers
from braille_tokenizer import BrailleBPETokenizer, ASCIIBPETokenizer


@dataclass
class CompletionResult:
    """Result of a single completion attempt"""
    context: str
    expected: str
    predicted: str
    exact_match: bool
    edit_distance: int
    context_length: int


class NGramPredictor:
    """
    N-gram language model for code completion.
    Simple but effective for pattern comparison.
    """
    
    def __init__(self, n: int = 5):
        self.n = n
        self.ngrams = defaultdict(Counter)
        self.vocab = set()
        
    def train(self, token_sequences: List[List[int]]):
        """Train on tokenized sequences"""
        for tokens in token_sequences:
            self.vocab.update(tokens)
            for i in range(len(tokens) - self.n):
                context = tuple(tokens[i:i + self.n])
                next_token = tokens[i + self.n]
                self.ngrams[context][next_token] += 1
                
    def predict(self, context: List[int], num_predictions: int = 5) -> List[Tuple[int, float]]:
        """Predict next tokens given context"""
        context_tuple = tuple(context[-self.n:]) if len(context) >= self.n else tuple(context)
        
        if context_tuple in self.ngrams:
            counts = self.ngrams[context_tuple]
            total = sum(counts.values())
            predictions = [(tok, count / total) for tok, count in counts.most_common(num_predictions)]
            return predictions
        
        # Backoff to shorter context
        for backoff in range(1, len(context_tuple)):
            shorter = context_tuple[backoff:]
            if shorter in self.ngrams:
                counts = self.ngrams[shorter]
                total = sum(counts.values())
                predictions = [(tok, count / total * 0.5) for tok, count in counts.most_common(num_predictions)]
                return predictions
                
        return []
        
    def complete_sequence(self, context: List[int], length: int = 10) -> List[int]:
        """Generate a completion of specified length"""
        result = list(context)
        for _ in range(length):
            predictions = self.predict(result)
            if predictions:
                # Sample from top predictions
                next_token = predictions[0][0]  # Take most likely
                result.append(next_token)
            else:
                break
        return result[len(context):]


def levenshtein_distance(s1: List[int], s2: List[int]) -> int:
    """Calculate edit distance between two token sequences"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


class CodeCompletionExperiment:
    """
    Compare code completion accuracy between ASCII and Braille representations.
    """
    
    def __init__(self):
        self.encoder = Braille8Encoder()
        self.braille_tokenizer = None
        self.ascii_tokenizer = None
        self.braille_predictor = None
        self.ascii_predictor = None
        
    def prepare_data(self, code_dir: str = None) -> Tuple[List[str], List[str]]:
        """Collect and split code samples"""
        code_dir = Path(code_dir) if code_dir else Path.home() / "sal-voice"
        texts = []
        
        for ext in ['.py', '.js', '.ts']:
            for filepath in code_dir.rglob(f"*{ext}"):
                if '.git' in str(filepath) or 'node_modules' in str(filepath):
                    continue
                try:
                    code = filepath.read_text(encoding='utf-8', errors='ignore')
                    if 500 < len(code) < 50000:
                        texts.append(code)
                except:
                    continue
                    
        random.shuffle(texts)
        split = int(len(texts) * 0.8)
        return texts[:split], texts[split:]
        
    def train_models(self, train_texts: List[str]):
        """Train tokenizers and n-gram models"""
        print("Training tokenizers...")
        
        # Train tokenizers
        self.braille_tokenizer = BrailleBPETokenizer(vocab_size=4000)
        self.braille_tokenizer.train(train_texts)
        
        self.ascii_tokenizer = ASCIIBPETokenizer(vocab_size=4000)
        self.ascii_tokenizer.train(train_texts)
        
        print("Training n-gram predictors...")
        
        # Tokenize training data
        braille_sequences = [self.braille_tokenizer.encode(t) for t in train_texts]
        ascii_sequences = [self.ascii_tokenizer.encode(t) for t in train_texts]
        
        # Train n-gram models
        self.braille_predictor = NGramPredictor(n=5)
        self.braille_predictor.train(braille_sequences)
        
        self.ascii_predictor = NGramPredictor(n=5)
        self.ascii_predictor.train(ascii_sequences)
        
        print(f"Braille n-grams: {len(self.braille_predictor.ngrams)}")
        print(f"ASCII n-grams: {len(self.ascii_predictor.ngrams)}")
        
    def evaluate_completion(self, test_texts: List[str], mask_length: int = 10) -> Dict:
        """
        Evaluate completion accuracy on test set.
        
        For each test sample:
        1. Tokenize
        2. Mask last N tokens
        3. Predict completion
        4. Compare to ground truth
        """
        print(f"\nEvaluating completion (mask_length={mask_length})...")
        
        braille_results = []
        ascii_results = []
        
        for text in test_texts:
            # Tokenize both ways
            braille_tokens = self.braille_tokenizer.encode(text)
            ascii_tokens = self.ascii_tokenizer.encode(text)
            
            if len(braille_tokens) < mask_length + 10 or len(ascii_tokens) < mask_length + 10:
                continue
                
            # Braille completion
            braille_context = braille_tokens[:-mask_length]
            braille_expected = braille_tokens[-mask_length:]
            braille_predicted = self.braille_predictor.complete_sequence(braille_context, mask_length)
            
            braille_exact = braille_predicted == braille_expected
            braille_edit = levenshtein_distance(braille_predicted, braille_expected)
            
            braille_results.append(CompletionResult(
                context=str(len(braille_context)),
                expected=str(braille_expected),
                predicted=str(braille_predicted),
                exact_match=braille_exact,
                edit_distance=braille_edit,
                context_length=len(braille_context)
            ))
            
            # ASCII completion
            ascii_context = ascii_tokens[:-mask_length]
            ascii_expected = ascii_tokens[-mask_length:]
            ascii_predicted = self.ascii_predictor.complete_sequence(ascii_context, mask_length)
            
            ascii_exact = ascii_predicted == ascii_expected
            ascii_edit = levenshtein_distance(ascii_predicted, ascii_expected)
            
            ascii_results.append(CompletionResult(
                context=str(len(ascii_context)),
                expected=str(ascii_expected),
                predicted=str(ascii_predicted),
                exact_match=ascii_exact,
                edit_distance=ascii_edit,
                context_length=len(ascii_context)
            ))
            
        return {
            'braille': braille_results,
            'ascii': ascii_results,
        }
        
    def calculate_metrics(self, results: Dict) -> Dict:
        """Calculate accuracy metrics"""
        braille = results['braille']
        ascii_r = results['ascii']
        
        if not braille or not ascii_r:
            return {}
            
        # Exact match accuracy
        braille_exact_acc = sum(1 for r in braille if r.exact_match) / len(braille)
        ascii_exact_acc = sum(1 for r in ascii_r if r.exact_match) / len(ascii_r)
        
        # Average edit distance (normalized by sequence length)
        braille_avg_edit = statistics.mean(r.edit_distance for r in braille)
        ascii_avg_edit = statistics.mean(r.edit_distance for r in ascii_r)
        
        # Token accuracy (what % of tokens were correct)
        braille_token_acc = 1 - (braille_avg_edit / 10)  # Normalized
        ascii_token_acc = 1 - (ascii_avg_edit / 10)
        
        return {
            'braille_exact_accuracy': braille_exact_acc,
            'ascii_exact_accuracy': ascii_exact_acc,
            'braille_avg_edit_distance': braille_avg_edit,
            'ascii_avg_edit_distance': ascii_avg_edit,
            'braille_token_accuracy': max(0, braille_token_acc),
            'ascii_token_accuracy': max(0, ascii_token_acc),
            'num_samples': len(braille),
        }
        
    def run_experiment(self) -> Dict:
        """Run the full completion experiment"""
        print("\n" + "="*70)
        print("CODE COMPLETION ACCURACY EXPERIMENT")
        print("Hypothesis: Braille enables better code completion")
        print("="*70)
        
        # Prepare data
        train_texts, test_texts = self.prepare_data()
        print(f"\nTrain: {len(train_texts)} files, Test: {len(test_texts)} files")
        
        # Train models
        self.train_models(train_texts)
        
        # Evaluate at different mask lengths
        all_results = {}
        
        for mask_length in [5, 10, 20]:
            results = self.evaluate_completion(test_texts, mask_length)
            metrics = self.calculate_metrics(results)
            all_results[f'mask_{mask_length}'] = metrics
            
            print(f"\n--- Mask Length: {mask_length} tokens ---")
            print(f"  Samples tested: {metrics.get('num_samples', 0)}")
            print(f"\n  Exact Match Accuracy:")
            print(f"    Braille: {metrics.get('braille_exact_accuracy', 0):.2%}")
            print(f"    ASCII:   {metrics.get('ascii_exact_accuracy', 0):.2%}")
            print(f"\n  Average Edit Distance:")
            print(f"    Braille: {metrics.get('braille_avg_edit_distance', 0):.2f}")
            print(f"    ASCII:   {metrics.get('ascii_avg_edit_distance', 0):.2f}")
            print(f"\n  Token Accuracy:")
            print(f"    Braille: {metrics.get('braille_token_accuracy', 0):.2%}")
            print(f"    ASCII:   {metrics.get('ascii_token_accuracy', 0):.2%}")
            
            # Determine winner
            braille_edit = metrics.get('braille_avg_edit_distance', float('inf'))
            ascii_edit = metrics.get('ascii_avg_edit_distance', float('inf'))
            
            if braille_edit < ascii_edit:
                improvement = (ascii_edit - braille_edit) / ascii_edit * 100
                print(f"\n  ✓ BRAILLE WINS: {improvement:.1f}% lower edit distance")
            elif ascii_edit < braille_edit:
                improvement = (braille_edit - ascii_edit) / braille_edit * 100
                print(f"\n  ✗ ASCII WINS: {improvement:.1f}% lower edit distance")
            else:
                print(f"\n  = TIE")
                
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        braille_wins = 0
        ascii_wins = 0
        
        for mask_key, metrics in all_results.items():
            braille_edit = metrics.get('braille_avg_edit_distance', float('inf'))
            ascii_edit = metrics.get('ascii_avg_edit_distance', float('inf'))
            
            if braille_edit < ascii_edit:
                braille_wins += 1
            elif ascii_edit < braille_edit:
                ascii_wins += 1
                
        print(f"\n  Braille wins: {braille_wins}/3")
        print(f"  ASCII wins:   {ascii_wins}/3")
        
        if braille_wins > ascii_wins:
            print("\n  ✓ CONCLUSION: BRAILLE ENABLES BETTER CODE COMPLETION")
        elif ascii_wins > braille_wins:
            print("\n  ✗ CONCLUSION: ASCII ENABLES BETTER CODE COMPLETION")
        else:
            print("\n  = CONCLUSION: NO SIGNIFICANT DIFFERENCE")
            
        # Save results
        output = {
            'experiment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'hypothesis': 'Braille enables better code completion',
            'results': all_results,
            'braille_wins': braille_wins,
            'ascii_wins': ascii_wins,
            'conclusion': 'braille_better' if braille_wins > ascii_wins else 'ascii_better' if ascii_wins > braille_wins else 'no_difference'
        }
        
        results_path = Path(__file__).parent / "completion_experiment_results.json"
        with open(results_path, 'w') as f:
            json.dump(output, f, indent=2)
            
        print(f"\nResults saved to: {results_path}")
        print("\n⠉⠕⠍⠏⠇⠑⠞⠊⠕⠝_⠑⠭⠏⠑⠗⠊⠍⠑⠝⠞_⠙⠕⠝⠑")
        
        return output


if __name__ == "__main__":
    experiment = CodeCompletionExperiment()
    results = experiment.run_experiment()
