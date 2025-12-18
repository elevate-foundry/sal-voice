#!/usr/bin/env python3
"""
Temporal Dot-Flow Encoding
==========================

A NOVEL audio fingerprinting algorithm that encodes sound as the
*movement* of Braille dots between adjacent characters.

Key Insight: A blind reader doesn't perceive isolated Braille patterns -
they feel the TRANSITIONS as their finger moves left to right. This
algorithm captures that temporal-tactile experience.

Instead of comparing static patterns, we compare:
- Which dots APPEAR (rising energy in that position)
- Which dots DISAPPEAR (falling energy)
- Which dots PERSIST (sustained energy)
- The DIRECTION of flow (upward/downward in the 2x4 grid)

This creates a fundamentally different similarity metric based on
perceptual dynamics rather than static snapshots.

Author: Ryan Barrett
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Set
from enum import Enum, auto

from octo_bresenham import OctoBresenham


class FlowDirection(Enum):
    """Direction of dot movement between characters."""
    UP = auto()      # Dots moving toward top of grid
    DOWN = auto()    # Dots moving toward bottom
    EXPAND = auto()  # Dots spreading outward
    CONTRACT = auto() # Dots contracting inward
    STABLE = auto()  # No significant movement
    PULSE = auto()   # Alternating on/off


@dataclass
class DotTransition:
    """A single transition between two Braille characters."""
    appeared: Set[Tuple[int, int]]   # Dots that turned ON (x, y)
    disappeared: Set[Tuple[int, int]] # Dots that turned OFF
    persisted: Set[Tuple[int, int]]  # Dots that stayed ON
    flow_direction: FlowDirection
    energy_delta: float              # Change in dot count (-8 to +8)
    centroid_shift: Tuple[float, float]  # Movement of dot centroid


@dataclass 
class FlowSignature:
    """A complete flow-based fingerprint."""
    source: str                      # Original Braille string
    transitions: List[DotTransition]
    flow_sequence: str               # Encoded as symbols: ↑↓○●◐◑
    rhythm_pattern: str              # Encoded pulse timing
    energy_contour: List[float]      # Dot density over time
    dominant_flow: FlowDirection


class TemporalDotFlow:
    """
    Encodes audio as dot-flow transitions for novel fingerprinting.
    """
    
    BRAILLE_BASE = 0x2800
    
    # Dot position mapping (x, y) -> bit
    DOT_POSITIONS = {
        (0, 0): 0, (1, 0): 3,  # Top row
        (0, 1): 1, (1, 1): 4,  # Second row
        (0, 2): 2, (1, 2): 5,  # Third row
        (0, 3): 6, (1, 3): 7,  # Bottom row
    }
    
    # Reverse mapping: bit -> (x, y)
    BIT_TO_POS = {v: k for k, v in DOT_POSITIONS.items()}
    
    # Flow symbols for encoding
    FLOW_SYMBOLS = {
        FlowDirection.UP: '↑',
        FlowDirection.DOWN: '↓',
        FlowDirection.EXPAND: '◇',
        FlowDirection.CONTRACT: '◆',
        FlowDirection.STABLE: '─',
        FlowDirection.PULSE: '◐',
    }
    
    def __init__(self):
        self.bresenham = OctoBresenham()
    
    def _char_to_dots(self, char: str) -> Set[Tuple[int, int]]:
        """Convert Braille character to set of active dot positions."""
        if not char or ord(char) < self.BRAILLE_BASE:
            return set()
        
        bits = ord(char) - self.BRAILLE_BASE
        dots = set()
        for bit, pos in self.BIT_TO_POS.items():
            if bits & (1 << bit):
                dots.add(pos)
        return dots
    
    def _dots_to_char(self, dots: Set[Tuple[int, int]]) -> str:
        """Convert set of dot positions back to Braille character."""
        bits = 0
        for pos in dots:
            if pos in self.DOT_POSITIONS:
                bits |= (1 << self.DOT_POSITIONS[pos])
        return chr(self.BRAILLE_BASE + bits)
    
    def _compute_centroid(self, dots: Set[Tuple[int, int]]) -> Tuple[float, float]:
        """Compute the centroid (center of mass) of active dots."""
        if not dots:
            return (0.5, 1.5)  # Center of grid
        
        x_sum = sum(d[0] for d in dots)
        y_sum = sum(d[1] for d in dots)
        n = len(dots)
        return (x_sum / n, y_sum / n)
    
    def _determine_flow_direction(self, 
                                   appeared: Set[Tuple[int, int]],
                                   disappeared: Set[Tuple[int, int]],
                                   centroid_shift: Tuple[float, float]) -> FlowDirection:
        """Determine the dominant flow direction from a transition."""
        dx, dy = centroid_shift
        
        # Check for pulse (alternating pattern)
        if len(appeared) > 0 and len(disappeared) > 0:
            if len(appeared) == len(disappeared):
                return FlowDirection.PULSE
        
        # Check for expansion/contraction
        appeared_spread = self._compute_spread(appeared) if appeared else 0
        disappeared_spread = self._compute_spread(disappeared) if disappeared else 0
        
        if appeared_spread > disappeared_spread + 0.5:
            return FlowDirection.EXPAND
        if disappeared_spread > appeared_spread + 0.5:
            return FlowDirection.CONTRACT
        
        # Check vertical movement
        if abs(dy) > 0.3:
            return FlowDirection.UP if dy < 0 else FlowDirection.DOWN
        
        return FlowDirection.STABLE
    
    def _compute_spread(self, dots: Set[Tuple[int, int]]) -> float:
        """Compute how spread out the dots are from their centroid."""
        if len(dots) < 2:
            return 0.0
        
        cx, cy = self._compute_centroid(dots)
        distances = [math.sqrt((d[0] - cx)**2 + (d[1] - cy)**2) for d in dots]
        return sum(distances) / len(distances)
    
    def compute_transition(self, char1: str, char2: str) -> DotTransition:
        """Compute the transition between two Braille characters."""
        dots1 = self._char_to_dots(char1)
        dots2 = self._char_to_dots(char2)
        
        appeared = dots2 - dots1
        disappeared = dots1 - dots2
        persisted = dots1 & dots2
        
        centroid1 = self._compute_centroid(dots1)
        centroid2 = self._compute_centroid(dots2)
        centroid_shift = (centroid2[0] - centroid1[0], centroid2[1] - centroid1[1])
        
        energy_delta = len(dots2) - len(dots1)
        
        flow_direction = self._determine_flow_direction(
            appeared, disappeared, centroid_shift
        )
        
        return DotTransition(
            appeared=appeared,
            disappeared=disappeared,
            persisted=persisted,
            flow_direction=flow_direction,
            energy_delta=energy_delta,
            centroid_shift=centroid_shift
        )
    
    def encode(self, braille_string: str) -> FlowSignature:
        """
        Encode a Braille string as a flow signature.
        
        This is the core novel algorithm: instead of storing the
        patterns themselves, we store how they CHANGE.
        """
        if len(braille_string) < 2:
            return FlowSignature(
                source=braille_string,
                transitions=[],
                flow_sequence="",
                rhythm_pattern="",
                energy_contour=[],
                dominant_flow=FlowDirection.STABLE
            )
        
        transitions = []
        flow_sequence = []
        energy_contour = []
        
        # Compute all transitions
        for i in range(len(braille_string) - 1):
            trans = self.compute_transition(braille_string[i], braille_string[i + 1])
            transitions.append(trans)
            flow_sequence.append(self.FLOW_SYMBOLS[trans.flow_direction])
            
            # Track energy
            dots = self._char_to_dots(braille_string[i])
            energy_contour.append(len(dots) / 8.0)  # Normalize to 0-1
        
        # Add final character's energy
        final_dots = self._char_to_dots(braille_string[-1])
        energy_contour.append(len(final_dots) / 8.0)
        
        # Compute rhythm pattern (where pulses occur)
        rhythm = []
        for trans in transitions:
            if trans.flow_direction == FlowDirection.PULSE:
                rhythm.append('●')
            elif abs(trans.energy_delta) > 2:
                rhythm.append('◐')
            else:
                rhythm.append('○')
        
        # Determine dominant flow
        flow_counts = {}
        for trans in transitions:
            flow_counts[trans.flow_direction] = flow_counts.get(trans.flow_direction, 0) + 1
        
        dominant_flow = max(flow_counts.keys(), key=lambda k: flow_counts[k]) if flow_counts else FlowDirection.STABLE
        
        return FlowSignature(
            source=braille_string,
            transitions=transitions,
            flow_sequence=''.join(flow_sequence),
            rhythm_pattern=''.join(rhythm),
            energy_contour=energy_contour,
            dominant_flow=dominant_flow
        )
    
    def flow_similarity(self, sig1: FlowSignature, sig2: FlowSignature) -> float:
        """
        Compute similarity between two flow signatures.
        
        This is NOVEL because we compare:
        1. The SEQUENCE of flow directions (not patterns)
        2. The RHYTHM of energy changes
        3. The SHAPE of energy contours
        
        Two completely different Braille strings can have identical
        flow signatures if they "feel" the same when read.
        """
        if not sig1.transitions or not sig2.transitions:
            return 0.0
        
        # 1. Flow sequence alignment (like DNA sequence alignment)
        flow_sim = self._sequence_similarity(sig1.flow_sequence, sig2.flow_sequence)
        
        # 2. Rhythm pattern matching
        rhythm_sim = self._sequence_similarity(sig1.rhythm_pattern, sig2.rhythm_pattern)
        
        # 3. Energy contour correlation
        energy_sim = self._contour_similarity(sig1.energy_contour, sig2.energy_contour)
        
        # 4. Dominant flow match bonus
        flow_bonus = 0.1 if sig1.dominant_flow == sig2.dominant_flow else 0.0
        
        # Weighted combination
        return min(1.0, (
            flow_sim * 0.4 +
            rhythm_sim * 0.25 +
            energy_sim * 0.25 +
            flow_bonus
        ))
    
    def _sequence_similarity(self, seq1: str, seq2: str) -> float:
        """Compute similarity between two symbol sequences using LCS."""
        if not seq1 or not seq2:
            return 0.0
        
        # Longest Common Subsequence ratio
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i-1] == seq2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        lcs_length = dp[m][n]
        return (2 * lcs_length) / (m + n)
    
    def _contour_similarity(self, c1: List[float], c2: List[float]) -> float:
        """Compute similarity between energy contours using correlation."""
        if not c1 or not c2:
            return 0.0
        
        # Resample to same length
        target_len = min(len(c1), len(c2), 20)
        
        def resample(contour, length):
            if len(contour) == length:
                return contour
            result = []
            for i in range(length):
                idx = int((i / length) * len(contour))
                result.append(contour[min(idx, len(contour) - 1)])
            return result
        
        c1_r = resample(c1, target_len)
        c2_r = resample(c2, target_len)
        
        # Pearson correlation
        mean1 = sum(c1_r) / len(c1_r)
        mean2 = sum(c2_r) / len(c2_r)
        
        numerator = sum((a - mean1) * (b - mean2) for a, b in zip(c1_r, c2_r))
        denom1 = math.sqrt(sum((a - mean1) ** 2 for a in c1_r))
        denom2 = math.sqrt(sum((b - mean2) ** 2 for b in c2_r))
        
        if denom1 == 0 or denom2 == 0:
            return 0.0
        
        correlation = numerator / (denom1 * denom2)
        return (correlation + 1) / 2  # Normalize to 0-1
    
    def visualize_flow(self, sig: FlowSignature) -> str:
        """Create a visual representation of the flow signature."""
        lines = [
            "┌─────────────────────────────────────────────────────┐",
            "│ TEMPORAL DOT-FLOW SIGNATURE                         │",
            "├─────────────────────────────────────────────────────┤",
            f"│ Source:   {sig.source[:40]:<40} │",
            f"│ Flow:     {sig.flow_sequence[:40]:<40} │",
            f"│ Rhythm:   {sig.rhythm_pattern[:40]:<40} │",
            f"│ Dominant: {sig.dominant_flow.name:<40} │",
            "├─────────────────────────────────────────────────────┤",
            "│ Energy Contour:                                     │",
        ]
        
        # ASCII energy graph
        max_width = 40
        contour = sig.energy_contour[:max_width]
        graph = ""
        for e in contour:
            level = int(e * 4)
            graph += ["▁", "▂", "▃", "▄", "▅"][min(level, 4)]
        lines.append(f"│ {graph:<51} │")
        
        lines.append("└─────────────────────────────────────────────────────┘")
        
        return '\n'.join(lines)


def demo():
    """Demonstrate the novel dot-flow encoding."""
    print("\n" + "=" * 60)
    print("  TEMPORAL DOT-FLOW ENCODING")
    print("  A novel Braille-based audio fingerprinting algorithm")
    print("=" * 60)
    
    from audio_fingerprint import generate_test_audio, AudioFingerprintGenerator
    
    flow = TemporalDotFlow()
    gen = AudioFingerprintGenerator(width=40, height=2)
    
    # Generate test audio and fingerprints
    print("\n📊 Generating audio fingerprints...")
    
    test_cases = {
        'sine': generate_test_audio('sine', 1.0),
        'chord': generate_test_audio('chord', 1.0),
        'drums': generate_test_audio('drums', 1.0),
        'speech': generate_test_audio('speech', 1.0),
    }
    
    signatures = {}
    for name, samples in test_cases.items():
        fp = gen.from_samples(samples)
        sig = flow.encode(fp.waveform)
        signatures[name] = sig
        
        print(f"\n{'─' * 60}")
        print(f"  {name.upper()}")
        print(f"{'─' * 60}")
        print(flow.visualize_flow(sig))
    
    # Compare using flow similarity
    print("\n" + "=" * 60)
    print("  FLOW-BASED SIMILARITY MATRIX")
    print("  (Comparing transitions, not patterns)")
    print("=" * 60)
    
    names = list(signatures.keys())
    print("\n         ", end="")
    for n in names:
        print(f"{n:>10}", end="")
    print()
    
    for n1 in names:
        print(f"{n1:<10}", end="")
        for n2 in names:
            sim = flow.flow_similarity(signatures[n1], signatures[n2])
            print(f"{sim:>10.2f}", end="")
        print()
    
    # Demonstrate novelty: different patterns, same flow
    print("\n" + "=" * 60)
    print("  NOVELTY DEMONSTRATION")
    print("  Different patterns can have similar FLOW")
    print("=" * 60)
    
    # Two different Braille strings with similar flow patterns
    pattern1 = "⠁⠃⠇⡇⣇⣿⣷⣶⣤⣀"  # Rising then falling
    pattern2 = "⠈⠘⠸⢸⣸⣿⣾⣼⣰⣀"  # Different dots, similar flow
    
    sig1 = flow.encode(pattern1)
    sig2 = flow.encode(pattern2)
    
    print(f"\nPattern 1: {pattern1}")
    print(f"Pattern 2: {pattern2}")
    print(f"\nThese look different, but...")
    print(f"Flow 1:    {sig1.flow_sequence}")
    print(f"Flow 2:    {sig2.flow_sequence}")
    print(f"\nFlow similarity: {flow.flow_similarity(sig1, sig2):.2f}")
    print("\n✨ Same 'feel' despite different dots!")


if __name__ == "__main__":
    demo()
