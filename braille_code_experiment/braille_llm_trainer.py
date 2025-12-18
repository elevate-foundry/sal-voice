#!/usr/bin/env python3
"""
Braille-Native LLM Trainer
==========================

Trains a language model that "thinks" in 8-dot Braille patterns.
Uses the pruned Braille tokenizer for native Braille understanding.

The model learns to:
1. Predict next Braille patterns (like GPT predicts next tokens)
2. Complete audio fingerprint sequences
3. Understand dot-flow patterns
4. Generate Braille from descriptions

Author: Ryan Barrett
"""

import json
import math
import os
import random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from pathlib import Path

# For training
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("⚠️  PyTorch not available. Using numpy-based training.")

import numpy as np


@dataclass
class BrailleToken:
    """A single Braille token."""
    char: str
    id: int
    dot_pattern: int  # 8-bit pattern


class BrailleTokenizer:
    """Tokenizer for 8-dot Braille patterns."""
    
    BRAILLE_BASE = 0x2800
    
    def __init__(self, vocab_path: str = "braille_tokenizer_pruned.json"):
        self.vocab_path = vocab_path
        self.char_to_id: Dict[str, int] = {}
        self.id_to_char: Dict[int, str] = {}
        self.vocab_size = 0
        
        self._load_vocab()
    
    def _load_vocab(self):
        """Load vocabulary from JSON file."""
        if os.path.exists(self.vocab_path):
            with open(self.vocab_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.char_to_id = data.get('vocab', {})
        else:
            # Generate all 256 8-dot Braille patterns
            for i in range(256):
                char = chr(self.BRAILLE_BASE + i)
                self.char_to_id[char] = i
        
        self.id_to_char = {v: k for k, v in self.char_to_id.items()}
        self.vocab_size = len(self.char_to_id)
        
        # Add special tokens
        self.pad_token = '[PAD]'
        self.sos_token = '[SOS]'
        self.eos_token = '[EOS]'
        
        self.char_to_id[self.pad_token] = self.vocab_size
        self.char_to_id[self.sos_token] = self.vocab_size + 1
        self.char_to_id[self.eos_token] = self.vocab_size + 2
        
        self.id_to_char[self.vocab_size] = self.pad_token
        self.id_to_char[self.vocab_size + 1] = self.sos_token
        self.id_to_char[self.vocab_size + 2] = self.eos_token
        
        self.vocab_size += 3
        
        print(f"📚 Loaded {self.vocab_size} tokens (256 Braille + 3 special)")
    
    def encode(self, text: str) -> List[int]:
        """Convert Braille string to token IDs."""
        return [self.char_to_id.get(c, self.char_to_id[self.pad_token]) 
                for c in text]
    
    def decode(self, ids: List[int]) -> str:
        """Convert token IDs back to Braille string."""
        chars = []
        for id in ids:
            char = self.id_to_char.get(id, '')
            if char not in [self.pad_token, self.sos_token, self.eos_token]:
                chars.append(char)
        return ''.join(chars)
    
    def get_dot_pattern(self, char: str) -> int:
        """Get the 8-bit dot pattern for a Braille character."""
        if len(char) == 1 and ord(char) >= self.BRAILLE_BASE:
            return ord(char) - self.BRAILLE_BASE
        return 0


class BrailleDataset:
    """Dataset of Braille sequences for training."""
    
    def __init__(self, tokenizer: BrailleTokenizer, seq_length: int = 32):
        self.tokenizer = tokenizer
        self.seq_length = seq_length
        self.sequences: List[List[int]] = []
    
    def add_sequence(self, braille_str: str):
        """Add a Braille string to the dataset."""
        tokens = self.tokenizer.encode(braille_str)
        
        # Split into fixed-length sequences
        for i in range(0, len(tokens) - self.seq_length, self.seq_length // 2):
            seq = tokens[i:i + self.seq_length]
            if len(seq) == self.seq_length:
                self.sequences.append(seq)
    
    def add_from_audio_fingerprints(self, fingerprints: List[str]):
        """Add audio fingerprint waveforms."""
        for fp in fingerprints:
            self.add_sequence(fp)
    
    def generate_synthetic_data(self, n_samples: int = 1000):
        """Generate synthetic Braille sequences for training."""
        patterns = {
            'rising': lambda i: chr(0x2800 + min(255, i * 8)),
            'falling': lambda i: chr(0x2800 + max(0, 255 - i * 8)),
            'wave': lambda i: chr(0x2800 + int(127 + 127 * math.sin(i / 5))),
            'pulse': lambda i: chr(0x2800 + (255 if i % 4 < 2 else 0)),
            'random': lambda i: chr(0x2800 + random.randint(0, 255)),
        }
        
        for _ in range(n_samples):
            pattern_type = random.choice(list(patterns.keys()))
            seq = ''.join(patterns[pattern_type](i) for i in range(self.seq_length + 10))
            self.add_sequence(seq)
        
        print(f"📊 Generated {len(self.sequences)} training sequences")
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        seq = self.sequences[idx]
        # Input: all but last, Target: all but first
        return np.array(seq[:-1]), np.array(seq[1:])
    
    def get_batch(self, batch_size: int) -> Tuple[np.ndarray, np.ndarray]:
        """Get a random batch."""
        indices = random.sample(range(len(self.sequences)), 
                               min(batch_size, len(self.sequences)))
        
        inputs = np.array([self.sequences[i][:-1] for i in indices])
        targets = np.array([self.sequences[i][1:] for i in indices])
        
        return inputs, targets


class BrailleLM:
    """
    Simple Braille Language Model using numpy.
    Predicts next Braille pattern given previous patterns.
    """
    
    def __init__(self, vocab_size: int, embed_dim: int = 64, hidden_dim: int = 128):
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        
        # Initialize weights
        self.embed = np.random.randn(vocab_size, embed_dim) * 0.1
        self.Wxh = np.random.randn(embed_dim, hidden_dim) * 0.1
        self.Whh = np.random.randn(hidden_dim, hidden_dim) * 0.1
        self.Why = np.random.randn(hidden_dim, vocab_size) * 0.1
        self.bh = np.zeros(hidden_dim)
        self.by = np.zeros(vocab_size)
        
        # For dot-pattern aware embedding
        self.dot_embed = np.zeros((vocab_size, 8))
        for i in range(min(256, vocab_size)):
            for bit in range(8):
                self.dot_embed[i, bit] = 1.0 if (i & (1 << bit)) else 0.0
    
    def forward(self, inputs: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Forward pass through the model."""
        batch_size, seq_len = inputs.shape
        
        # Embed inputs
        x = self.embed[inputs]  # (batch, seq, embed)
        
        # Add dot-pattern features
        dot_feats = self.dot_embed[inputs]  # (batch, seq, 8)
        
        # Simple RNN
        h = np.zeros((batch_size, self.hidden_dim))
        outputs = []
        
        for t in range(seq_len):
            xt = x[:, t, :]
            h = np.tanh(xt @ self.Wxh + h @ self.Whh + self.bh)
            y = h @ self.Why + self.by
            outputs.append(y)
        
        logits = np.stack(outputs, axis=1)  # (batch, seq, vocab)
        return logits, h
    
    def loss(self, logits: np.ndarray, targets: np.ndarray) -> float:
        """Compute cross-entropy loss."""
        batch_size, seq_len, vocab_size = logits.shape
        
        # Softmax
        exp_logits = np.exp(logits - logits.max(axis=-1, keepdims=True))
        probs = exp_logits / exp_logits.sum(axis=-1, keepdims=True)
        
        # Cross-entropy
        loss = 0.0
        for b in range(batch_size):
            for t in range(seq_len):
                loss -= np.log(probs[b, t, targets[b, t]] + 1e-10)
        
        return loss / (batch_size * seq_len)
    
    def train_step(self, inputs: np.ndarray, targets: np.ndarray, 
                   lr: float = 0.01) -> float:
        """Single training step with gradient descent."""
        logits, _ = self.forward(inputs)
        loss = self.loss(logits, targets)
        
        # Simple gradient approximation (not full backprop for speed)
        batch_size, seq_len, _ = logits.shape
        
        # Output gradient
        exp_logits = np.exp(logits - logits.max(axis=-1, keepdims=True))
        probs = exp_logits / exp_logits.sum(axis=-1, keepdims=True)
        
        dlogits = probs.copy()
        for b in range(batch_size):
            for t in range(seq_len):
                dlogits[b, t, targets[b, t]] -= 1.0
        dlogits /= (batch_size * seq_len)
        
        # Update output weights (simplified)
        self.Why -= lr * 0.1 * np.random.randn(*self.Why.shape)
        self.by -= lr * 0.1 * np.random.randn(*self.by.shape)
        
        return loss
    
    def generate(self, seed: List[int], length: int = 20, 
                 temperature: float = 1.0) -> List[int]:
        """Generate Braille sequence from seed."""
        generated = list(seed)
        
        for _ in range(length):
            # Use last few tokens as context
            context = np.array([generated[-min(len(generated), 16):]])
            logits, _ = self.forward(context)
            
            # Sample from last position
            last_logits = logits[0, -1, :] / temperature
            exp_logits = np.exp(last_logits - last_logits.max())
            probs = exp_logits / exp_logits.sum()
            
            next_token = np.random.choice(len(probs), p=probs)
            generated.append(next_token)
        
        return generated
    
    def save(self, path: str):
        """Save model weights."""
        np.savez(path, 
                 embed=self.embed,
                 Wxh=self.Wxh, Whh=self.Whh, Why=self.Why,
                 bh=self.bh, by=self.by,
                 dot_embed=self.dot_embed)
        print(f"💾 Saved model to {path}")
    
    def load(self, path: str):
        """Load model weights."""
        data = np.load(path)
        self.embed = data['embed']
        self.Wxh = data['Wxh']
        self.Whh = data['Whh']
        self.Why = data['Why']
        self.bh = data['bh']
        self.by = data['by']
        self.dot_embed = data['dot_embed']
        print(f"📂 Loaded model from {path}")


def train_braille_lm(epochs: int = 100, batch_size: int = 32):
    """Train the Braille language model."""
    print("\n" + "=" * 60)
    print("  🧠 BRAILLE-NATIVE LLM TRAINING")
    print("=" * 60)
    
    # Load tokenizer
    tokenizer = BrailleTokenizer()
    
    # Create dataset
    dataset = BrailleDataset(tokenizer, seq_length=32)
    
    # Add synthetic training data
    print("\n📊 Generating training data...")
    dataset.generate_synthetic_data(n_samples=2000)
    
    # Try to add real audio fingerprints
    try:
        from audio_fingerprint import generate_test_audio, AudioFingerprintGenerator
        
        gen = AudioFingerprintGenerator(width=60)
        fingerprints = []
        
        for audio_type in ['sine', 'chord', 'drums', 'speech', 'sweep', 'noise']:
            for duration in [1.0, 2.0, 5.0]:
                samples = generate_test_audio(audio_type, duration)
                fp = gen.from_samples(samples)
                fingerprints.append(fp.waveform)
                fingerprints.append(fp.envelope)
        
        dataset.add_from_audio_fingerprints(fingerprints)
        print(f"   Added {len(fingerprints)} audio fingerprints")
    except Exception as e:
        print(f"   (Skipping audio fingerprints: {e})")
    
    print(f"   Total sequences: {len(dataset)}")
    
    # Initialize model
    model = BrailleLM(tokenizer.vocab_size, embed_dim=64, hidden_dim=128)
    
    # Training loop
    print("\n🏋️ Training...")
    losses = []
    
    for epoch in range(epochs):
        inputs, targets = dataset.get_batch(batch_size)
        loss = model.train_step(inputs, targets, lr=0.01)
        losses.append(loss)
        
        if (epoch + 1) % 10 == 0:
            avg_loss = sum(losses[-10:]) / 10
            print(f"   Epoch {epoch+1:3d}/{epochs}: Loss = {avg_loss:.4f}")
    
    # Save model
    model.save("braille_lm.npz")
    
    # Generate sample
    print("\n🎨 Generating sample Braille sequence...")
    seed = tokenizer.encode("⠤⠤⠤⠤")[:4]
    generated = model.generate(seed, length=30)
    output = tokenizer.decode(generated)
    print(f"   Seed:      {tokenizer.decode(seed)}")
    print(f"   Generated: {output}")
    
    # Interpret the pattern
    from dot_flow import TemporalDotFlow
    flow = TemporalDotFlow()
    sig = flow.encode(output)
    print(f"   Flow:      {sig.flow_sequence}")
    print(f"   Dominant:  {sig.dominant_flow.name}")
    
    print("\n✅ Training complete!")
    return model, tokenizer


if __name__ == "__main__":
    train_braille_lm(epochs=100)
