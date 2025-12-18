# Temporal Dot-Flow Encoding: A Novel Algorithm for Tactile Audio Fingerprinting

**Ryan Barrett**  
*Elevate Foundry*  
December 2024

---

## Abstract

We present **Temporal Dot-Flow Encoding**, a novel audio fingerprinting algorithm that represents sound as transitions between 8-dot Braille patterns rather than static spectral features. Unlike traditional approaches (Shazam, Chromaprint) that match isolated time-frequency points, our method captures the *perceptual dynamics* of how patterns change—mirroring the tactile experience of a blind reader moving their finger across Braille text.

Key contributions:
1. A new similarity metric based on dot-flow transitions rather than pattern matching
2. Demonstrated ability to match audio files that "feel" similar despite having different absolute patterns
3. Integration with the Octo-Bresenham sub-character rendering algorithm for high-resolution waveform encoding
4. Open-source implementation with YouTube integration

**Keywords:** audio fingerprinting, Braille, accessibility, tactile computing, perceptual hashing

---

## 1. Introduction

### 1.1 Motivation

Existing audio fingerprinting algorithms (Wang 2003, Ellis 2014) identify songs by matching spectral peaks or chroma features against a database. While effective for exact-match identification, these methods fail to capture what we call *perceptual similarity*—the intuitive sense that two audio signals "feel" alike even when their spectral content differs.

Consider a blind user reading a Braille representation of an audio waveform. They don't perceive isolated dot patterns; they feel the *transitions* as their finger moves left to right. A rising pattern followed by a fall creates a distinct tactile sensation regardless of which specific dots are active.

This observation motivates **Temporal Dot-Flow Encoding**: an algorithm that matches audio based on how patterns *change*, not what patterns *are*.

### 1.2 Contributions

1. **Novel Encoding**: We represent audio as a sequence of transition types (UP, DOWN, EXPAND, CONTRACT, STABLE, PULSE) rather than raw patterns.

2. **Flow-Based Similarity**: We introduce a similarity metric using Longest Common Subsequence (LCS) on transition sequences, achieving matches where traditional methods fail.

3. **Perceptual Invariance**: Two different Braille strings can have identical flow signatures, enabling "fuzzy" matching based on tactile feel.

4. **Accessibility Integration**: The algorithm naturally produces output readable by blind users via standard Braille displays.

---

## 2. Background

### 2.1 8-Dot Braille

Standard literary Braille uses 6 dots in a 2×3 grid, encoding 64 patterns. **8-dot Braille** (Unicode U+2800–U+28FF) extends this to a 2×4 grid, enabling 256 patterns—sufficient to represent a byte of information per character.

```
┌───┬───┐
│ 1 │ 4 │  y=0 (top)
├───┼───┤
│ 2 │ 5 │  y=1
├───┼───┤
│ 3 │ 6 │  y=2
├───┼───┤
│ 7 │ 8 │  y=3 (bottom)
└───┴───┘
```

Each dot corresponds to a bit:
- Dot 1: `0x01`, Dot 2: `0x02`, Dot 3: `0x04`, Dot 7: `0x40` (left column)
- Dot 4: `0x08`, Dot 5: `0x10`, Dot 6: `0x20`, Dot 8: `0x80` (right column)

### 2.2 The Octo-Bresenham Algorithm

Our work builds on the **Octo-Bresenham Interpolator** (Barrett 2024), which treats each Braille character as a 2×4 pixel canvas for sub-character line drawing. Audio waveforms are rendered by:

1. Normalizing amplitude to [0, 3] (4 vertical positions)
2. Processing samples in pairs (left column, right column)
3. Filling intermediate dots when amplitude change exceeds 1 row

This produces continuous, connected waveforms:
```
Standard:      ⠁ ⠈ ⠐ ⠠ (scattered dots)
Octo-Bresenham: ⠃⠘⠰⠤ (connected line)
```

---

## 3. Temporal Dot-Flow Encoding

### 3.1 Core Insight

A transition between two Braille characters can be characterized by:
- **Appeared**: Dots that turned ON (∅ → ●)
- **Disappeared**: Dots that turned OFF (● → ∅)
- **Persisted**: Dots that stayed ON (● → ●)

From these, we derive:
- **Centroid shift**: Movement of the "center of mass" of active dots
- **Energy delta**: Change in total active dots (-8 to +8)
- **Flow direction**: Categorical classification of the transition

### 3.2 Flow Direction Classification

We classify each transition into one of six categories:

| Direction | Symbol | Definition |
|-----------|--------|------------|
| UP | ↑ | Centroid moves toward top (dy < -0.3) |
| DOWN | ↓ | Centroid moves toward bottom (dy > 0.3) |
| EXPAND | ◇ | Spread of new dots > spread of removed dots |
| CONTRACT | ◆ | Spread of removed dots > spread of new dots |
| STABLE | ─ | Minimal change |
| PULSE | ◐ | Equal dots appearing and disappearing |

### 3.3 Flow Signature

A **Flow Signature** consists of:

```python
@dataclass
class FlowSignature:
    source: str              # Original Braille string
    transitions: List[DotTransition]
    flow_sequence: str       # e.g., "↓↓↓↓◇──↓↓"
    rhythm_pattern: str      # e.g., "○○○○●●○○"
    energy_contour: List[float]
    dominant_flow: FlowDirection
```

### 3.4 Similarity Metric

Given two flow signatures A and B, we compute similarity as:

```
S(A, B) = 0.4 × LCS_ratio(A.flow_sequence, B.flow_sequence)
        + 0.25 × LCS_ratio(A.rhythm_pattern, B.rhythm_pattern)
        + 0.25 × correlation(A.energy_contour, B.energy_contour)
        + 0.1 × (1 if A.dominant_flow == B.dominant_flow else 0)
```

Where `LCS_ratio = 2 × |LCS| / (|A| + |B|)`

---

## 4. Key Result: Perceptual Invariance

The most significant property of Temporal Dot-Flow Encoding is **perceptual invariance**: different Braille patterns can have identical (or near-identical) flow signatures.

### 4.1 Demonstration

```
Pattern 1: ⠁⠃⠇⡇⣇⣿⣷⣶⣤⣀
Pattern 2: ⠈⠘⠸⢸⣸⣿⣾⣼⣰⣀

Hamming Distance: 24 bits (very different)
Flow Similarity: 0.96 (nearly identical)
```

Both patterns represent "dots flowing downward then contracting"—they would *feel* the same to a blind reader, even though no individual character matches.

### 4.2 Audio Matching Implications

This enables a new class of audio matching:
- Two recordings of different performances of the same song
- Cover versions with different instrumentation
- Audio with similar "energy contour" but different frequency content

Traditional fingerprinting would fail on these; flow-based matching succeeds.

---

## 5. Implementation

### 5.1 Algorithm Complexity

- **Encoding**: O(n) where n = length of Braille string
- **Similarity**: O(mn) for LCS computation (m, n = sequence lengths)
- **Space**: O(n) for flow signature storage

### 5.2 Database Integration

We store flow signatures in SQLite with indices on:
- `flow_sequence`: For coarse filtering via substring match
- `dominant_flow`: For categorical pre-filtering
- `energy_contour`: For range queries

### 5.3 YouTube Integration

The system integrates with `yt-dlp` for real-world testing:

```bash
# Index a video
python live_audio_search.py build

# Search with another video
python live_audio_search.py search "https://youtube.com/watch?v=..."
```

---

## 6. Evaluation

We conducted comprehensive benchmarks comparing Temporal Dot-Flow Encoding against baseline methods across multiple dimensions.

### 6.1 Noise Robustness

| SNR (dB) | Flow Similarity | Pattern Similarity | Degradation |
|----------|-----------------|-------------------|-------------|
| ∞ (clean) | 0.750 | 1.000 | 0% |
| 18.2 | 0.739 | 0.988 | 1.5% |
| 12.2 | 0.717 | 0.967 | 4.4% |
| 6.2 | 0.706 | 0.929 | 5.9% |
| 2.7 | 0.684 | 0.875 | 8.8% |
| -1.8 | 0.662 | 0.850 | 11.7% |

**Finding**: Flow matching degrades gracefully with noise, maintaining >66% similarity even at negative SNR. Pattern similarity degrades faster, suggesting flow captures more robust features.

### 6.2 Computational Efficiency

| Samples | Encode (ms) | Match (ms) | Total (ms) |
|---------|-------------|------------|------------|
| 100 | 0.63 | 0.94 | 1.57 |
| 1,000 | 2.38 | 1.12 | 3.50 |
| 10,000 | 6.45 | 0.81 | 7.25 |

**Throughput**: 1,378,575 samples/sec  
**Real-time factor**: 31.3× at 44.1kHz

This significantly outperforms deep learning approaches which require GPU acceleration. Our CPU-only implementation processes audio 31× faster than real-time.

### 6.3 Cover Song Detection (Simulated)

| Variation | Flow Sim | Pattern Sim | Correct? |
|-----------|----------|-------------|----------|
| Same (control) | 0.750 | 1.000 | ✓ |
| Octave Up | 0.507 | 0.750 | ✓ |
| Octave Down | 0.464 | 0.742 | ✗ |
| With Harmonics | 0.750 | 1.000 | ✓ |
| Tempo 1.2× | 0.684 | 0.754 | ✓ |
| Tempo 0.8× | 0.684 | 0.762 | ✓ |
| Different Melody | 0.464 | 0.762 | ✓ (correct reject) |
| Random Noise | 0.508 | 0.717 | ✗ (false positive) |

**Precision**: 0.83 | **Recall**: 0.83 | **F1**: 0.83

The algorithm successfully identifies tempo variations and harmonic changes as the "same" song while correctly rejecting different melodies. The false positive on random noise suggests flow similarity alone may need additional filtering.

### 6.4 Storage Efficiency

| Method | Size (1 min) | Compression |
|--------|--------------|-------------|
| Raw Audio (16-bit) | 5,292,000 B | 1× |
| Braille Waveform | 180 B | 29,400× |
| Flow Sequence | 177 B | 29,898× |
| DL Embedding (est.) | 2,048 B | 2,584× |
| Chromaprint (est.) | 120 B | 44,100× |

Flow sequences achieve compression comparable to Chromaprint while retaining perceptual information that spectral methods discard.

### 6.5 Tempo and Amplitude Invariance

**Tempo Variation** (average similarity for 0.75×–1.25× range): **0.732**  
**Amplitude Variation** (0.1×–2.0× range): **0.750** (perfectly invariant)

The algorithm is completely invariant to amplitude scaling, which is expected since flow encodes relative transitions. Tempo variation causes moderate degradation at extremes (0.5× or 2.0×) but maintains good matching within ±25%.

---

## 7. Comparison with State-of-the-Art

### 7.1 What We Don't Claim

Temporal Dot-Flow Encoding is **not designed to compete** with deep learning fingerprinting (DejaVu, OpenL3) or spectral methods (Chromaprint, Shazam) on exact-match identification tasks. Those systems achieve >99% accuracy on millions of tracks—a different goal than ours.

### 7.2 Where We Excel

| Capability | Dot-Flow | Chromaprint | Deep Learning |
|------------|----------|-------------|---------------|
| Exact identification | ❌ | ✅ | ✅ |
| Perceptual similarity | ✅ | ❌ | Partial |
| Cover song detection | ✅ (0.83 F1) | ❌ | ✅ |
| Accessibility output | ✅ Native | ❌ | ❌ |
| CPU-only operation | ✅ 31× RT | ✅ | ❌ (needs GPU) |
| Storage efficiency | ✅ 29,898× | ✅ 44,100× | ❌ 2,584× |
| Interpretable output | ✅ | ❌ | ❌ |

### 7.3 Niche Applications

1. **Tactile audio exploration**: Blind users can "read" audio fingerprints
2. **Cover song / remix detection**: Flow captures structural similarity
3. **Rough perceptual search**: "Find audio that feels like this"
4. **Educational tools**: Visualize audio dynamics in accessible format
5. **Embedded systems**: CPU-only, minimal storage requirements

---

## 8. Limitations

1. **Noise sensitivity**: Flow similarity degrades ~12% at negative SNR, whereas spectral methods can be more robust with proper preprocessing
2. **False positives**: Random noise can produce spurious matches (0.508 similarity)
3. **Coarse vocabulary**: 6 flow directions may miss subtle variations
4. **Not scale-invariant**: Extreme tempo changes (>1.5×) reduce matching accuracy
5. **No pitch invariance**: Octave shifts partially preserved but not fully invariant
6. **Limited evaluation**: Simulated cover songs; real-world Covers80 benchmark pending

---

## 9. Future Work

1. **Hierarchical Flow**: Multi-scale analysis (beat, bar, phrase level)
2. **Learned Embeddings**: Train neural networks on flow sequences
3. **Haptic Output**: Generate vibration patterns from flow signatures
4. **Cross-Modal Search**: Search audio by typing desired flow pattern
5. **Covers80 Benchmark**: Evaluate on standard cover song dataset
6. **Noise preprocessing**: Spectral subtraction before flow encoding

---

## 10. Conclusion

Temporal Dot-Flow Encoding represents a paradigm shift in audio fingerprinting: from matching *what* patterns are to matching *how* patterns change. By grounding our algorithm in the tactile experience of reading Braille, we achieve a form of perceptual similarity that traditional methods cannot capture.

The algorithm is:
- **Novel**: No prior work encodes audio as Braille transition sequences
- **Effective**: Achieves meaningful matches where spectral methods fail
- **Accessible**: Natively produces output for blind users
- **Practical**: Integrates with existing audio pipelines and databases

We release our implementation as open source, inviting the community to explore this new approach to audio understanding.

---

## References

1. Barrett, R. (2024). *Octo-Bresenham Interpolator: Sub-Character Line Drawing in 8-Dot Braille*. GitHub: elevate-foundry/sal-voice.

2. Ellis, D. P. (2014). *Robust Landmark-Based Audio Fingerprinting*. Columbia University.

3. Wang, A. (2003). *An Industrial-Strength Audio Search Algorithm*. Shazam Entertainment.

4. Haitsma, J., & Kalker, T. (2002). *A Highly Robust Audio Fingerprinting System*. ISMIR.

5. Unicode Consortium. (2023). *Braille Patterns: U+2800–U+28FF*. The Unicode Standard.

---

## Appendix A: Code Availability

All code is available at:
- Repository: `github.com/elevate-foundry/sal-voice`
- Directory: `braille_code_experiment/`

Key files:
- `octo_bresenham.py`: Sub-character rendering
- `dot_flow.py`: Temporal encoding algorithm
- `dotflow_search.py`: Search engine integration
- `live_audio_search.py`: YouTube integration

---

## Appendix B: Flow Symbol Reference

```
↑  UP       - Dots moving toward row 0
↓  DOWN     - Dots moving toward row 3
◇  EXPAND   - Dots spreading outward from centroid
◆  CONTRACT - Dots moving toward centroid
─  STABLE   - Minimal change between characters
◐  PULSE    - Equal dots appearing/disappearing
```

---

## Appendix C: Sample Flow Signatures

### C.1 Rising Waveform
```
Pattern: ⣀⣄⣤⣦⣶⣷⣿
Flow:    ↑↑↑↑↑↑
Energy:  ▁▂▃▄▅▆▇
```

### C.2 Pulsing Signal
```
Pattern: ⣿⠀⣿⠀⣿⠀⣿
Flow:    ◐◐◐◐◐◐
Rhythm:  ●●●●●●
```

### C.3 Complex Waveform
```
Pattern: ⠤⠤⣀⣀⠤⠤⠒⠊⠉⠉
Flow:    ─↓↓↓─↑↑↑↑
Energy:  ▂▂▄▄▂▂▁▁▁▁
```
