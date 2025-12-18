#!/usr/bin/env python3
"""
Benchmark Suite for Temporal Dot-Flow Encoding
===============================================

Compares our algorithm against baseline methods and tests:
1. Noise robustness
2. Computational efficiency
3. Cover song / variation detection
4. Storage efficiency

Author: Ryan Barrett
"""

import json
import math
import os
import random
import struct
import time
import wave
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import tempfile

import numpy as np

from dot_flow import TemporalDotFlow, FlowSignature
from audio_fingerprint import AudioFingerprintGenerator, generate_test_audio
from octo_bresenham import OctoBresenham


@dataclass
class BenchmarkResult:
    """Result from a benchmark test."""
    name: str
    metric: str
    value: float
    unit: str
    details: Dict[str, Any]


class DotFlowBenchmark:
    """
    Comprehensive benchmark suite for Temporal Dot-Flow Encoding.
    """
    
    def __init__(self):
        self.flow = TemporalDotFlow()
        self.generator = AudioFingerprintGenerator(width=60, height=2)
        self.results: List[BenchmarkResult] = []
    
    def run_all(self) -> List[BenchmarkResult]:
        """Run all benchmarks."""
        print("\n" + "=" * 70)
        print("  🧪 TEMPORAL DOT-FLOW BENCHMARK SUITE")
        print("=" * 70)
        
        self.benchmark_noise_robustness()
        self.benchmark_computational_efficiency()
        self.benchmark_cover_song_detection()
        self.benchmark_storage_efficiency()
        self.benchmark_tempo_variation()
        self.benchmark_amplitude_variation()
        
        self.print_summary()
        return self.results
    
    def benchmark_noise_robustness(self):
        """Test how well matching works with added noise."""
        print("\n" + "-" * 70)
        print("  📊 NOISE ROBUSTNESS TEST")
        print("-" * 70)
        
        # Generate clean reference audio
        clean_samples = generate_test_audio('chord', duration=5.0)
        clean_fp = self.generator.from_samples(clean_samples)
        clean_flow = self.flow.encode(clean_fp.waveform)
        
        noise_levels = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5]
        results = []
        
        print(f"\n{'SNR (dB)':<12} {'Flow Sim':<12} {'Pattern Sim':<12} {'Degradation':<12}")
        print("-" * 48)
        
        for noise_level in noise_levels:
            # Add white noise
            noisy_samples = [
                s + random.gauss(0, noise_level) 
                for s in clean_samples
            ]
            
            # Clip to valid range
            noisy_samples = [max(-1, min(1, s)) for s in noisy_samples]
            
            noisy_fp = self.generator.from_samples(noisy_samples)
            noisy_flow = self.flow.encode(noisy_fp.waveform)
            
            # Compute similarities
            flow_sim = self.flow.flow_similarity(clean_flow, noisy_flow)
            pattern_sim = self._pattern_similarity(clean_fp.waveform, noisy_fp.waveform)
            
            # SNR calculation
            if noise_level > 0:
                signal_power = sum(s**2 for s in clean_samples) / len(clean_samples)
                noise_power = noise_level ** 2
                snr_db = 10 * math.log10(signal_power / noise_power)
            else:
                snr_db = float('inf')
            
            snr_str = f"{snr_db:.1f}" if snr_db < 100 else "∞"
            degradation = (1 - flow_sim) * 100
            
            print(f"{snr_str:<12} {flow_sim:<12.3f} {pattern_sim:<12.3f} {degradation:<12.1f}%")
            
            results.append({
                'noise_level': noise_level,
                'snr_db': snr_db if snr_db < 100 else 999,
                'flow_similarity': flow_sim,
                'pattern_similarity': pattern_sim
            })
        
        # Find noise level where flow_sim drops below 0.7
        threshold_noise = None
        for r in results:
            if r['flow_similarity'] < 0.7:
                threshold_noise = r['noise_level']
                break
        
        self.results.append(BenchmarkResult(
            name="Noise Robustness",
            metric="Threshold SNR",
            value=results[2]['snr_db'] if len(results) > 2 else 0,
            unit="dB",
            details={'all_results': results, 'threshold_noise': threshold_noise}
        ))
        
        # Key finding
        if results[2]['flow_similarity'] > 0.8:
            print(f"\n✅ Flow matching maintains >80% similarity at 10% noise")
        else:
            print(f"\n⚠️  Flow matching degrades significantly with noise")
    
    def benchmark_computational_efficiency(self):
        """Benchmark encoding and matching speed."""
        print("\n" + "-" * 70)
        print("  ⚡ COMPUTATIONAL EFFICIENCY TEST")
        print("-" * 70)
        
        # Test different input sizes
        sizes = [100, 500, 1000, 5000, 10000]
        results = []
        
        print(f"\n{'Samples':<12} {'Encode (ms)':<15} {'Match (ms)':<15} {'Total (ms)':<15}")
        print("-" * 57)
        
        for n_samples in sizes:
            samples = generate_test_audio('sine', duration=n_samples/44100)
            
            # Benchmark encoding
            start = time.perf_counter()
            for _ in range(100):
                fp = self.generator.from_samples(samples)
                sig = self.flow.encode(fp.waveform)
            encode_time = (time.perf_counter() - start) / 100 * 1000
            
            # Benchmark matching
            sig2 = self.flow.encode(fp.waveform)
            start = time.perf_counter()
            for _ in range(100):
                sim = self.flow.flow_similarity(sig, sig2)
            match_time = (time.perf_counter() - start) / 100 * 1000
            
            total = encode_time + match_time
            print(f"{n_samples:<12} {encode_time:<15.3f} {match_time:<15.3f} {total:<15.3f}")
            
            results.append({
                'samples': n_samples,
                'encode_ms': encode_time,
                'match_ms': match_time,
                'total_ms': total
            })
        
        # Calculate throughput
        samples_per_sec = sizes[-1] / (results[-1]['total_ms'] / 1000)
        
        self.results.append(BenchmarkResult(
            name="Computational Efficiency",
            metric="Throughput",
            value=samples_per_sec,
            unit="samples/sec",
            details={'all_results': results}
        ))
        
        print(f"\n✅ Throughput: {samples_per_sec:,.0f} samples/sec")
        print(f"   Real-time factor: {samples_per_sec/44100:.1f}x (at 44.1kHz)")
    
    def benchmark_cover_song_detection(self):
        """
        Simulate cover song detection using variations of the same melody.
        Since we don't have Covers80 locally, we simulate by:
        - Original: sine wave melody
        - Cover: same melody with different harmonics/timbre
        """
        print("\n" + "-" * 70)
        print("  🎵 COVER SONG DETECTION TEST (Simulated)")
        print("-" * 70)
        
        # Generate "original" - pure melody
        def generate_melody(freqs: List[float], duration: float = 0.5) -> List[float]:
            samples = []
            sample_rate = 44100
            for freq in freqs:
                for i in range(int(duration * sample_rate)):
                    t = i / sample_rate
                    samples.append(math.sin(2 * math.pi * freq * t))
            return samples
        
        # Simple melody: C-E-G-C (major chord arpeggio)
        melody_freqs = [261.63, 329.63, 392.00, 523.25]  # C4, E4, G4, C5
        
        # Original version (pure sine)
        original = generate_melody(melody_freqs)
        original_fp = self.generator.from_samples(original)
        original_flow = self.flow.encode(original_fp.waveform)
        
        # Create variations (simulated "covers")
        variations = {
            'Same (control)': original,
            'Octave Up': generate_melody([f * 2 for f in melody_freqs]),
            'Octave Down': generate_melody([f / 2 for f in melody_freqs]),
            'With Harmonics': self._add_harmonics(original),
            'Tempo 1.2x': self._change_tempo(original, 1.2),
            'Tempo 0.8x': self._change_tempo(original, 0.8),
            'Different Melody': generate_melody([293.66, 349.23, 440.00, 587.33]),  # D-F-A-D
            'Random Noise': [random.uniform(-1, 1) for _ in original],
        }
        
        print(f"\n{'Variation':<20} {'Flow Sim':<12} {'Pattern Sim':<12} {'Match?':<10}")
        print("-" * 54)
        
        cover_results = []
        for name, var_samples in variations.items():
            var_fp = self.generator.from_samples(var_samples)
            var_flow = self.flow.encode(var_fp.waveform)
            
            flow_sim = self.flow.flow_similarity(original_flow, var_flow)
            pattern_sim = self._pattern_similarity(original_fp.waveform, var_fp.waveform)
            
            is_match = "✅" if flow_sim > 0.5 else "❌"
            print(f"{name:<20} {flow_sim:<12.3f} {pattern_sim:<12.3f} {is_match:<10}")
            
            cover_results.append({
                'variation': name,
                'flow_similarity': flow_sim,
                'pattern_similarity': pattern_sim,
                'expected_match': name not in ['Different Melody', 'Random Noise']
            })
        
        # Calculate precision/recall
        true_positives = sum(1 for r in cover_results 
                           if r['expected_match'] and r['flow_similarity'] > 0.5)
        false_positives = sum(1 for r in cover_results 
                            if not r['expected_match'] and r['flow_similarity'] > 0.5)
        false_negatives = sum(1 for r in cover_results 
                            if r['expected_match'] and r['flow_similarity'] <= 0.5)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        self.results.append(BenchmarkResult(
            name="Cover Song Detection",
            metric="F1 Score",
            value=f1,
            unit="",
            details={'precision': precision, 'recall': recall, 'variations': cover_results}
        ))
        
        print(f"\n📊 Precision: {precision:.2f}, Recall: {recall:.2f}, F1: {f1:.2f}")
    
    def benchmark_storage_efficiency(self):
        """Compare storage requirements."""
        print("\n" + "-" * 70)
        print("  💾 STORAGE EFFICIENCY TEST")
        print("-" * 70)
        
        # Generate 1 minute of audio
        samples = generate_test_audio('chord', duration=60.0)
        fp = self.generator.from_samples(samples)
        flow_sig = self.flow.encode(fp.waveform)
        
        # Storage sizes
        raw_audio_size = len(samples) * 2  # 16-bit samples
        waveform_size = len(fp.waveform.encode('utf-8'))
        flow_seq_size = len(flow_sig.flow_sequence.encode('utf-8'))
        
        # Typical deep learning embedding size
        dl_embedding_size = 512 * 4  # 512 float32 values
        
        # Chromaprint size (typical)
        chromaprint_size = 120  # ~120 bytes for 1 minute
        
        print(f"\n{'Method':<25} {'Size':<15} {'Compression':<15}")
        print("-" * 55)
        print(f"{'Raw Audio (16-bit)':<25} {raw_audio_size:,} bytes {1.0:<15.1f}x")
        print(f"{'Braille Waveform':<25} {waveform_size:,} bytes {raw_audio_size/waveform_size:<15.1f}x")
        print(f"{'Flow Sequence':<25} {flow_seq_size:,} bytes {raw_audio_size/flow_seq_size:<15.1f}x")
        print(f"{'DL Embedding (est.)':<25} {dl_embedding_size:,} bytes {raw_audio_size/dl_embedding_size:<15.1f}x")
        print(f"{'Chromaprint (est.)':<25} {chromaprint_size:,} bytes {raw_audio_size/chromaprint_size:<15.1f}x")
        
        self.results.append(BenchmarkResult(
            name="Storage Efficiency",
            metric="Flow Sequence Size",
            value=flow_seq_size,
            unit="bytes/minute",
            details={
                'raw_audio': raw_audio_size,
                'braille_waveform': waveform_size,
                'flow_sequence': flow_seq_size,
                'dl_embedding': dl_embedding_size,
                'chromaprint': chromaprint_size
            }
        ))
        
        print(f"\n✅ Flow sequence is {raw_audio_size/flow_seq_size:.0f}x smaller than raw audio")
    
    def benchmark_tempo_variation(self):
        """Test robustness to tempo changes."""
        print("\n" + "-" * 70)
        print("  🎼 TEMPO VARIATION TEST")
        print("-" * 70)
        
        original = generate_test_audio('drums', duration=5.0)
        original_fp = self.generator.from_samples(original)
        original_flow = self.flow.encode(original_fp.waveform)
        
        tempo_factors = [0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0]
        results = []
        
        print(f"\n{'Tempo':<12} {'Flow Sim':<12} {'Pattern Sim':<12}")
        print("-" * 36)
        
        for factor in tempo_factors:
            stretched = self._change_tempo(original, factor)
            stretched_fp = self.generator.from_samples(stretched)
            stretched_flow = self.flow.encode(stretched_fp.waveform)
            
            flow_sim = self.flow.flow_similarity(original_flow, stretched_flow)
            pattern_sim = self._pattern_similarity(original_fp.waveform, stretched_fp.waveform)
            
            print(f"{factor:<12.2f}x {flow_sim:<12.3f} {pattern_sim:<12.3f}")
            results.append({'factor': factor, 'flow_sim': flow_sim, 'pattern_sim': pattern_sim})
        
        self.results.append(BenchmarkResult(
            name="Tempo Variation",
            metric="Avg Similarity (0.75x-1.25x)",
            value=np.mean([r['flow_sim'] for r in results if 0.75 <= r['factor'] <= 1.25]),
            unit="",
            details={'all_results': results}
        ))
    
    def benchmark_amplitude_variation(self):
        """Test robustness to volume changes."""
        print("\n" + "-" * 70)
        print("  🔊 AMPLITUDE VARIATION TEST")
        print("-" * 70)
        
        original = generate_test_audio('speech', duration=5.0)
        original_fp = self.generator.from_samples(original)
        original_flow = self.flow.encode(original_fp.waveform)
        
        amplitude_factors = [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
        results = []
        
        print(f"\n{'Amplitude':<12} {'Flow Sim':<12} {'Pattern Sim':<12}")
        print("-" * 36)
        
        for factor in amplitude_factors:
            scaled = [min(1, max(-1, s * factor)) for s in original]
            scaled_fp = self.generator.from_samples(scaled)
            scaled_flow = self.flow.encode(scaled_fp.waveform)
            
            flow_sim = self.flow.flow_similarity(original_flow, scaled_flow)
            pattern_sim = self._pattern_similarity(original_fp.waveform, scaled_fp.waveform)
            
            print(f"{factor:<12.2f}x {flow_sim:<12.3f} {pattern_sim:<12.3f}")
            results.append({'factor': factor, 'flow_sim': flow_sim, 'pattern_sim': pattern_sim})
        
        self.results.append(BenchmarkResult(
            name="Amplitude Variation",
            metric="Avg Similarity",
            value=np.mean([r['flow_sim'] for r in results]),
            unit="",
            details={'all_results': results}
        ))
    
    def _pattern_similarity(self, a: str, b: str) -> float:
        """Traditional Hamming distance similarity."""
        if not a or not b:
            return 0.0
        
        max_len = max(len(a), len(b))
        a = a.ljust(max_len, chr(0x2800))
        b = b.ljust(max_len, chr(0x2800))
        
        distance = 0
        for ca, cb in zip(a, b):
            bits_a = ord(ca) - 0x2800 if ord(ca) >= 0x2800 else 0
            bits_b = ord(cb) - 0x2800 if ord(cb) >= 0x2800 else 0
            distance += bin(bits_a ^ bits_b).count('1')
        
        return 1.0 - (distance / (max_len * 8))
    
    def _add_harmonics(self, samples: List[float]) -> List[float]:
        """Add harmonics to simulate different timbre."""
        result = []
        for i, s in enumerate(samples):
            # Add 2nd and 3rd harmonics
            harmonic2 = s * 0.3  # Simplified - would need proper phase
            harmonic3 = s * 0.15
            result.append(max(-1, min(1, s + harmonic2 + harmonic3)))
        return result
    
    def _change_tempo(self, samples: List[float], factor: float) -> List[float]:
        """Change tempo by resampling."""
        new_length = int(len(samples) / factor)
        result = []
        for i in range(new_length):
            src_idx = i * factor
            idx = int(src_idx)
            frac = src_idx - idx
            if idx + 1 < len(samples):
                result.append(samples[idx] * (1 - frac) + samples[idx + 1] * frac)
            elif idx < len(samples):
                result.append(samples[idx])
        return result
    
    def print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 70)
        print("  📋 BENCHMARK SUMMARY")
        print("=" * 70)
        
        for r in self.results:
            if r.unit:
                print(f"\n  {r.name}: {r.value:.2f} {r.unit}")
            else:
                print(f"\n  {r.name}: {r.value:.3f}")
        
        print("\n" + "=" * 70)
    
    def export_results(self, path: str = "benchmark_results.json"):
        """Export results to JSON."""
        data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'results': [
                {
                    'name': r.name,
                    'metric': r.metric,
                    'value': r.value,
                    'unit': r.unit,
                    'details': r.details
                }
                for r in self.results
            ]
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"\n💾 Results exported to {path}")
        return path


def main():
    benchmark = DotFlowBenchmark()
    benchmark.run_all()
    benchmark.export_results()


if __name__ == "__main__":
    main()
