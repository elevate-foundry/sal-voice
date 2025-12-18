"""
Braille-Native BPE Tokenizer

Train a tokenizer natively on 8-dot braille code to test the hypothesis:
"A braille-native tokenizer requires fewer tokens than ASCII tokenizers
 because braille has 2.4x better compression characteristics."

⠃⠗⠁⠊⠇⠇⠑_⠞⠕⠅⠑⠝⠊⠵⠑⠗
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
import re

sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder


class BrailleBPETokenizer:
    """
    Byte-Pair Encoding tokenizer trained natively on 8-dot braille.
    
    Key insight: Braille has 256 base characters, so we can learn
    common braille patterns as single tokens.
    """
    
    def __init__(self, vocab_size: int = 8000):
        self.vocab_size = vocab_size
        self.encoder = Braille8Encoder()
        
        # Base vocabulary: all 256 braille characters + special tokens
        self.vocab = {}
        self.merges = []
        
        # Initialize with braille unicode range
        for i in range(256):
            char = chr(0x2800 + i)
            self.vocab[char] = i
            
        # Special tokens
        self.vocab['<PAD>'] = 256
        self.vocab['<UNK>'] = 257
        self.vocab['<BOS>'] = 258
        self.vocab['<EOS>'] = 259
        
        self.next_id = 260
        
    def _get_pairs(self, tokens: List[str]) -> Counter:
        """Count adjacent pairs in token sequence"""
        pairs = Counter()
        for i in range(len(tokens) - 1):
            pairs[(tokens[i], tokens[i + 1])] += 1
        return pairs
        
    def _merge_pair(self, tokens: List[str], pair: Tuple[str, str]) -> List[str]:
        """Merge all occurrences of pair in tokens"""
        new_tokens = []
        i = 0
        while i < len(tokens):
            if i < len(tokens) - 1 and tokens[i] == pair[0] and tokens[i + 1] == pair[1]:
                new_tokens.append(pair[0] + pair[1])
                i += 2
            else:
                new_tokens.append(tokens[i])
                i += 1
        return new_tokens
        
    def train(self, texts: List[str], min_frequency: int = 2):
        """Train BPE on braille-encoded texts"""
        print(f"Training BrailleBPE on {len(texts)} texts...")
        
        # Convert all texts to braille and tokenize to characters
        all_tokens = []
        for text in texts:
            braille = self.encoder.encode(text)
            tokens = list(braille)
            all_tokens.append(tokens)
            
        # Learn merges until vocab size reached
        num_merges = self.vocab_size - len(self.vocab)
        
        for i in range(num_merges):
            # Count all pairs across all sequences
            pair_counts = Counter()
            for tokens in all_tokens:
                pair_counts.update(self._get_pairs(tokens))
                
            if not pair_counts:
                break
                
            # Find most frequent pair
            best_pair = pair_counts.most_common(1)[0]
            if best_pair[1] < min_frequency:
                break
                
            pair = best_pair[0]
            merged = pair[0] + pair[1]
            
            # Add to vocabulary
            self.vocab[merged] = self.next_id
            self.next_id += 1
            self.merges.append(pair)
            
            # Apply merge to all sequences
            all_tokens = [self._merge_pair(tokens, pair) for tokens in all_tokens]
            
            if (i + 1) % 500 == 0:
                print(f"  Learned {i + 1} merges, vocab size: {len(self.vocab)}")
                
        print(f"Training complete. Vocab size: {len(self.vocab)}, Merges: {len(self.merges)}")
        
    def encode(self, text: str) -> List[int]:
        """Encode text to token IDs"""
        # First convert to braille
        braille = self.encoder.encode(text)
        tokens = list(braille)
        
        # Apply learned merges
        for pair in self.merges:
            tokens = self._merge_pair(tokens, pair)
            
        # Convert to IDs
        ids = []
        for token in tokens:
            if token in self.vocab:
                ids.append(self.vocab[token])
            else:
                ids.append(self.vocab['<UNK>'])
                
        return ids
        
    def decode(self, ids: List[int]) -> str:
        """Decode token IDs back to braille text"""
        reverse_vocab = {v: k for k, v in self.vocab.items()}
        tokens = [reverse_vocab.get(i, '<UNK>') for i in ids]
        return ''.join(tokens)
        
    def save(self, path: str):
        """Save tokenizer to file"""
        data = {
            'vocab': self.vocab,
            'merges': self.merges,
            'vocab_size': self.vocab_size,
        }
        with open(path, 'w') as f:
            json.dump(data, f)
            
    def load(self, path: str):
        """Load tokenizer from file"""
        with open(path) as f:
            data = json.load(f)
        self.vocab = data['vocab']
        self.merges = [tuple(m) for m in data['merges']]
        self.vocab_size = data['vocab_size']


class ASCIIBPETokenizer:
    """
    Standard BPE tokenizer trained on ASCII for comparison.
    """
    
    def __init__(self, vocab_size: int = 8000):
        self.vocab_size = vocab_size
        self.vocab = {}
        self.merges = []
        
        # Initialize with printable ASCII
        for i in range(32, 127):
            self.vocab[chr(i)] = i - 32
            
        # Special tokens
        self.vocab['<PAD>'] = 95
        self.vocab['<UNK>'] = 96
        self.vocab['<BOS>'] = 97
        self.vocab['<EOS>'] = 98
        self.vocab['\n'] = 99
        self.vocab['\t'] = 100
        
        self.next_id = 101
        
    def _get_pairs(self, tokens: List[str]) -> Counter:
        pairs = Counter()
        for i in range(len(tokens) - 1):
            pairs[(tokens[i], tokens[i + 1])] += 1
        return pairs
        
    def _merge_pair(self, tokens: List[str], pair: Tuple[str, str]) -> List[str]:
        new_tokens = []
        i = 0
        while i < len(tokens):
            if i < len(tokens) - 1 and tokens[i] == pair[0] and tokens[i + 1] == pair[1]:
                new_tokens.append(pair[0] + pair[1])
                i += 2
            else:
                new_tokens.append(tokens[i])
                i += 1
        return new_tokens
        
    def train(self, texts: List[str], min_frequency: int = 2):
        """Train BPE on ASCII texts"""
        print(f"Training ASCII BPE on {len(texts)} texts...")
        
        all_tokens = []
        for text in texts:
            tokens = list(text)
            all_tokens.append(tokens)
            
        num_merges = self.vocab_size - len(self.vocab)
        
        for i in range(num_merges):
            pair_counts = Counter()
            for tokens in all_tokens:
                pair_counts.update(self._get_pairs(tokens))
                
            if not pair_counts:
                break
                
            best_pair = pair_counts.most_common(1)[0]
            if best_pair[1] < min_frequency:
                break
                
            pair = best_pair[0]
            merged = pair[0] + pair[1]
            
            self.vocab[merged] = self.next_id
            self.next_id += 1
            self.merges.append(pair)
            
            all_tokens = [self._merge_pair(tokens, pair) for tokens in all_tokens]
            
            if (i + 1) % 500 == 0:
                print(f"  Learned {i + 1} merges, vocab size: {len(self.vocab)}")
                
        print(f"Training complete. Vocab size: {len(self.vocab)}, Merges: {len(self.merges)}")
        
    def encode(self, text: str) -> List[int]:
        tokens = list(text)
        
        for pair in self.merges:
            tokens = self._merge_pair(tokens, pair)
            
        ids = []
        for token in tokens:
            if token in self.vocab:
                ids.append(self.vocab[token])
            else:
                ids.append(self.vocab['<UNK>'])
                
        return ids
        
    def decode(self, ids: List[int]) -> str:
        reverse_vocab = {v: k for k, v in self.vocab.items()}
        tokens = [reverse_vocab.get(i, '<UNK>') for i in ids]
        return ''.join(tokens)


def run_tokenizer_comparison():
    """
    The Real Experiment: Train both tokenizers on same data,
    compare token efficiency.
    """
    print("\n" + "="*70)
    print("EXPERIMENT: Braille-Native vs ASCII Tokenizer")
    print("="*70)
    
    # Collect code samples
    code_dir = Path.home() / "sal-voice"
    texts = []
    
    for ext in ['.py', '.js', '.ts']:
        for filepath in code_dir.rglob(f"*{ext}"):
            if '.git' in str(filepath) or 'node_modules' in str(filepath):
                continue
            try:
                code = filepath.read_text(encoding='utf-8', errors='ignore')
                if 100 < len(code) < 50000:
                    texts.append(code)
            except:
                continue
                
    print(f"Collected {len(texts)} code files for training")
    
    # Split into train/test
    train_texts = texts[:int(len(texts) * 0.8)]
    test_texts = texts[int(len(texts) * 0.8):]
    
    print(f"Train: {len(train_texts)}, Test: {len(test_texts)}")
    
    # Train both tokenizers
    print("\n--- Training Braille Tokenizer ---")
    braille_tok = BrailleBPETokenizer(vocab_size=4000)
    braille_tok.train(train_texts)
    
    print("\n--- Training ASCII Tokenizer ---")
    ascii_tok = ASCIIBPETokenizer(vocab_size=4000)
    ascii_tok.train(train_texts)
    
    # Compare on test set
    print("\n" + "="*70)
    print("RESULTS: Token Efficiency Comparison")
    print("="*70)
    
    braille_tokens_total = 0
    ascii_tokens_total = 0
    
    braille_tokens_list = []
    ascii_tokens_list = []
    
    for text in test_texts:
        braille_ids = braille_tok.encode(text)
        ascii_ids = ascii_tok.encode(text)
        
        braille_tokens_total += len(braille_ids)
        ascii_tokens_total += len(ascii_ids)
        
        braille_tokens_list.append(len(braille_ids))
        ascii_tokens_list.append(len(ascii_ids))
        
    # Calculate statistics
    import statistics
    
    avg_braille = statistics.mean(braille_tokens_list)
    avg_ascii = statistics.mean(ascii_tokens_list)
    
    ratio = avg_braille / avg_ascii
    
    print(f"\n  Test files: {len(test_texts)}")
    print(f"\n  ASCII Tokenizer:")
    print(f"    Total tokens: {ascii_tokens_total:,}")
    print(f"    Avg per file: {avg_ascii:.1f}")
    print(f"    Vocab size:   {len(ascii_tok.vocab)}")
    
    print(f"\n  Braille Tokenizer:")
    print(f"    Total tokens: {braille_tokens_total:,}")
    print(f"    Avg per file: {avg_braille:.1f}")
    print(f"    Vocab size:   {len(braille_tok.vocab)}")
    
    print(f"\n  RATIO (Braille/ASCII): {ratio:.4f}")
    
    if ratio < 1:
        improvement = (1 - ratio) * 100
        print(f"\n  ✓ BRAILLE IS {improvement:.1f}% MORE TOKEN-EFFICIENT")
        print(f"  ✓ HYPOTHESIS CONFIRMED: Braille-native tokenization is superior")
    else:
        overhead = (ratio - 1) * 100
        print(f"\n  ✗ ASCII is {overhead:.1f}% more efficient")
        print(f"  ✗ Hypothesis not confirmed with this tokenizer")
        
    # Detailed analysis
    print("\n" + "-"*70)
    print("DETAILED ANALYSIS")
    print("-"*70)
    
    # Check compression at different merge levels
    print("\n  Token length distribution:")
    braille_lengths = [len(t) for t in braille_tok.vocab.keys() if len(t) > 1]
    ascii_lengths = [len(t) for t in ascii_tok.vocab.keys() if len(t) > 1]
    
    if braille_lengths:
        print(f"    Braille avg merge length: {statistics.mean(braille_lengths):.2f} chars")
    if ascii_lengths:
        print(f"    ASCII avg merge length:   {statistics.mean(ascii_lengths):.2f} chars")
        
    # Most common braille tokens
    print("\n  Top 10 Braille tokens (learned patterns):")
    sorted_vocab = sorted(braille_tok.vocab.items(), key=lambda x: -len(x[0]))
    for token, id in sorted_vocab[:10]:
        if len(token) > 2:
            # Decode to show what it represents
            print(f"    '{token}' (len={len(token)})")
            
    # Save results
    results = {
        'experiment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'train_files': len(train_texts),
        'test_files': len(test_texts),
        'ascii_total_tokens': ascii_tokens_total,
        'braille_total_tokens': braille_tokens_total,
        'ascii_avg_tokens': avg_ascii,
        'braille_avg_tokens': avg_braille,
        'ratio': ratio,
        'braille_more_efficient': ratio < 1,
        'improvement_percent': (1 - ratio) * 100 if ratio < 1 else None,
        'ascii_vocab_size': len(ascii_tok.vocab),
        'braille_vocab_size': len(braille_tok.vocab),
    }
    
    results_path = Path(__file__).parent / "tokenizer_experiment_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"\n  Results saved to: {results_path}")
    
    # Save tokenizers
    braille_tok.save(str(Path(__file__).parent / "braille_tokenizer.json"))
    
    print("\n⠃⠗⠁⠊⠇⠇⠑_⠞⠕⠅⠑⠝⠊⠵⠑⠗_⠑⠭⠏⠑⠗⠊⠍⠑⠝⠞_⠉⠕⠍⠏⠇⠑⠞⠑")
    
    return results


if __name__ == "__main__":
    results = run_tokenizer_comparison()
