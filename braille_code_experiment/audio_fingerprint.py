"""
Audio Fingerprint Visualizer
============================

Generates unique Braille-based visual fingerprints of audio files using
the Octo-Bresenham Interpolator. Each audio file produces a distinctive
"wave signature" that can be used to:

1. Visually identify audio files at a glance
2. Spot differences between similar audio files
3. Store audio signatures in text-based logs
4. Create accessible audio representations

Author: Ryan Barrett
"""

import math
import struct
import wave
import hashlib
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from octo_bresenham import OctoBresenham, OctoHeatmap, OctoSparkline


@dataclass
class AudioFingerprint:
    """Represents a visual fingerprint of an audio file."""
    filename: str
    duration_seconds: float
    sample_rate: int
    channels: int
    waveform: str           # Single-line Braille waveform
    envelope: str           # Amplitude envelope
    spectrum_hash: str      # Short hash for quick comparison
    spectrogram: str        # Multi-line frequency analysis
    metadata: Dict[str, Any]


class AudioFingerprintGenerator:
    """
    Generates Braille-based visual fingerprints from audio data.
    """
    
    def __init__(self, width: int = 60, height: int = 4):
        """
        Args:
            width: Character width for fingerprint output
            height: Row height for spectrogram
        """
        self.width = width
        self.height = height
        self.bresenham = OctoBresenham()
        self.heatmap = OctoHeatmap()
        self.sparkline = OctoSparkline()
    
    def from_wav_file(self, filepath: str) -> AudioFingerprint:
        """
        Generate fingerprint from a WAV file.
        
        Args:
            filepath: Path to WAV file
            
        Returns:
            AudioFingerprint object
        """
        with wave.open(filepath, 'rb') as wav:
            n_channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            n_frames = wav.getnframes()
            
            # Read raw audio data
            raw_data = wav.readframes(n_frames)
            
        # Convert to samples
        samples = self._bytes_to_samples(raw_data, sample_width, n_channels)
        duration = len(samples) / sample_rate
        
        return self._generate_fingerprint(
            samples=samples,
            sample_rate=sample_rate,
            channels=n_channels,
            filename=Path(filepath).name,
            duration=duration
        )
    
    def from_samples(self, samples: List[float], sample_rate: int = 44100,
                     filename: str = "raw_audio") -> AudioFingerprint:
        """
        Generate fingerprint from raw sample data.
        
        Args:
            samples: List of audio samples (normalized -1.0 to 1.0)
            sample_rate: Sample rate in Hz
            filename: Name identifier
            
        Returns:
            AudioFingerprint object
        """
        duration = len(samples) / sample_rate
        return self._generate_fingerprint(
            samples=samples,
            sample_rate=sample_rate,
            channels=1,
            filename=filename,
            duration=duration
        )
    
    def _bytes_to_samples(self, raw_data: bytes, sample_width: int, 
                          n_channels: int) -> List[float]:
        """Convert raw audio bytes to normalized float samples."""
        if sample_width == 1:
            fmt = 'B'  # unsigned char
            max_val = 128.0
            offset = 128
        elif sample_width == 2:
            fmt = 'h'  # signed short
            max_val = 32768.0
            offset = 0
        elif sample_width == 4:
            fmt = 'i'  # signed int
            max_val = 2147483648.0
            offset = 0
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")
        
        n_samples = len(raw_data) // sample_width
        samples = struct.unpack(f'<{n_samples}{fmt}', raw_data)
        
        # Convert to mono if stereo (average channels)
        if n_channels == 2:
            mono_samples = []
            for i in range(0, len(samples), 2):
                if i + 1 < len(samples):
                    mono_samples.append((samples[i] + samples[i + 1]) / 2)
            samples = mono_samples
        
        # Normalize to -1.0 to 1.0
        normalized = [(s - offset) / max_val for s in samples]
        return normalized
    
    def _generate_fingerprint(self, samples: List[float], sample_rate: int,
                              channels: int, filename: str, 
                              duration: float) -> AudioFingerprint:
        """Generate all fingerprint components."""
        
        # 1. Downsample for visualization
        vis_samples = self._downsample(samples, self.width * 2)
        
        # 2. Generate waveform (map -1,1 to 0,3)
        waveform_data = [(s + 1) * 1.5 for s in vis_samples]
        waveform = self.bresenham.render(waveform_data)
        
        # 3. Generate amplitude envelope
        envelope_data = self._compute_envelope(samples, self.width * 2)
        envelope = self.bresenham.render(envelope_data)
        
        # 4. Generate spectrum hash
        spectrum_hash = self._compute_spectrum_hash(samples, sample_rate)
        
        # 5. Generate spectrogram (frequency bands over time)
        spectrogram = self._generate_spectrogram(samples, sample_rate)
        
        # 6. Compute metadata
        metadata = {
            'rms': self._compute_rms(samples),
            'peak': max(abs(s) for s in samples) if samples else 0,
            'zero_crossings': self._count_zero_crossings(samples),
            'dynamic_range_db': self._compute_dynamic_range(samples),
        }
        
        return AudioFingerprint(
            filename=filename,
            duration_seconds=duration,
            sample_rate=sample_rate,
            channels=channels,
            waveform=waveform,
            envelope=envelope,
            spectrum_hash=spectrum_hash,
            spectrogram=spectrogram,
            metadata=metadata
        )
    
    def _downsample(self, samples: List[float], target_length: int) -> List[float]:
        """Downsample by averaging windows."""
        if len(samples) <= target_length:
            # Pad if too short
            return samples + [0.0] * (target_length - len(samples))
        
        window_size = len(samples) // target_length
        result = []
        for i in range(target_length):
            start = i * window_size
            end = min(start + window_size, len(samples))
            window = samples[start:end]
            if window:
                result.append(sum(window) / len(window))
            else:
                result.append(0.0)
        return result
    
    def _compute_envelope(self, samples: List[float], 
                          target_length: int) -> List[float]:
        """Compute amplitude envelope (absolute values, smoothed)."""
        if not samples:
            return [1.5] * target_length
            
        window_size = max(1, len(samples) // target_length)
        envelope = []
        
        for i in range(target_length):
            start = i * window_size
            end = min(start + window_size, len(samples))
            window = samples[start:end]
            if window:
                # RMS of window, normalized to 0-3
                rms = math.sqrt(sum(s * s for s in window) / len(window))
                envelope.append(rms * 3)
            else:
                envelope.append(0.0)
        
        return envelope
    
    def _compute_spectrum_hash(self, samples: List[float], 
                               sample_rate: int) -> str:
        """Compute a short hash based on frequency characteristics."""
        # Simple DFT-based hash (not full FFT for simplicity)
        n_bands = 8
        band_energies = []
        
        chunk_size = min(1024, len(samples))
        if chunk_size < 16:
            return "⠀" * 8
        
        # Take a representative chunk from middle of audio
        mid = len(samples) // 2
        chunk = samples[max(0, mid - chunk_size // 2):mid + chunk_size // 2]
        
        # Compute energy in frequency bands using simple correlation
        for band in range(n_bands):
            freq = (band + 1) * sample_rate / (2 * n_bands)
            # Correlate with sine wave at this frequency
            energy = 0.0
            for i, s in enumerate(chunk):
                t = i / sample_rate
                energy += s * math.sin(2 * math.pi * freq * t)
            band_energies.append(abs(energy) / len(chunk))
        
        # Normalize and convert to braille intensity
        max_energy = max(band_energies) if max(band_energies) > 0 else 1
        normalized = [e / max_energy for e in band_energies]
        
        # Map to intensity patterns
        result = []
        for e in normalized:
            level = int(e * 8)
            level = max(0, min(8, level))
            result.append(chr(0x2800 + self.heatmap.intensity_patterns[level]))
        
        return "".join(result)
    
    def _generate_spectrogram(self, samples: List[float], 
                              sample_rate: int) -> str:
        """Generate a multi-row frequency-time spectrogram."""
        n_time_bins = self.width
        n_freq_bands = self.height
        
        if len(samples) < 64:
            return "⠀" * self.width
        
        # Build 2D array: rows = frequency bands, cols = time
        spectrogram_data = []
        
        chunk_size = len(samples) // n_time_bins
        
        for freq_band in range(n_freq_bands):
            row = []
            # Frequency for this band (low to high, top to bottom in display)
            freq = (n_freq_bands - freq_band) * sample_rate / (2 * n_freq_bands * 2)
            
            for time_bin in range(n_time_bins):
                start = time_bin * chunk_size
                end = min(start + chunk_size, len(samples))
                chunk = samples[start:end]
                
                if len(chunk) < 8:
                    row.append(0.0)
                    continue
                
                # Compute energy at this frequency using Goertzel-like approach
                energy = 0.0
                for i, s in enumerate(chunk):
                    t = i / sample_rate
                    energy += s * math.sin(2 * math.pi * freq * t)
                
                row.append(abs(energy) / len(chunk))
            
            spectrogram_data.append(row)
        
        return self.heatmap.render_heatmap(spectrogram_data)
    
    def _compute_rms(self, samples: List[float]) -> float:
        """Compute RMS (root mean square) amplitude."""
        if not samples:
            return 0.0
        return math.sqrt(sum(s * s for s in samples) / len(samples))
    
    def _count_zero_crossings(self, samples: List[float]) -> int:
        """Count zero crossings (rough measure of frequency content)."""
        crossings = 0
        for i in range(1, len(samples)):
            if (samples[i-1] >= 0) != (samples[i] >= 0):
                crossings += 1
        return crossings
    
    def _compute_dynamic_range(self, samples: List[float]) -> float:
        """Compute dynamic range in dB."""
        if not samples:
            return 0.0
        
        # RMS in small windows
        window_size = max(100, len(samples) // 100)
        window_rms = []
        
        for i in range(0, len(samples), window_size):
            window = samples[i:i + window_size]
            if window:
                rms = math.sqrt(sum(s * s for s in window) / len(window))
                if rms > 0.0001:  # Ignore silence
                    window_rms.append(rms)
        
        if len(window_rms) < 2:
            return 0.0
        
        max_rms = max(window_rms)
        min_rms = min(window_rms)
        
        if min_rms > 0:
            return 20 * math.log10(max_rms / min_rms)
        return 0.0
    
    def format_fingerprint(self, fp: AudioFingerprint, 
                           show_spectrogram: bool = True) -> str:
        """Format fingerprint for display."""
        lines = [
            f"╔{'═' * (self.width + 2)}╗",
            f"║ {fp.filename[:self.width]:<{self.width}} ║",
            f"╠{'═' * (self.width + 2)}╣",
            f"║ Duration: {fp.duration_seconds:.2f}s | {fp.sample_rate}Hz | {fp.channels}ch",
            f"║ RMS: {fp.metadata['rms']:.3f} | Peak: {fp.metadata['peak']:.3f} | DR: {fp.metadata['dynamic_range_db']:.1f}dB",
            f"╠{'═' * (self.width + 2)}╣",
            f"║ Waveform:",
            f"║ {fp.waveform}",
            f"║ Envelope:",
            f"║ {fp.envelope}",
            f"║ Spectrum: {fp.spectrum_hash}",
        ]
        
        if show_spectrogram:
            lines.append(f"╠{'═' * (self.width + 2)}╣")
            lines.append(f"║ Spectrogram (freq↓ time→):")
            for row in fp.spectrogram.split('\n'):
                lines.append(f"║ {row}")
        
        lines.append(f"╚{'═' * (self.width + 2)}╝")
        
        return '\n'.join(lines)


def generate_test_audio(audio_type: str, duration: float = 1.0, 
                        sample_rate: int = 44100) -> List[float]:
    """Generate synthetic test audio."""
    n_samples = int(duration * sample_rate)
    samples = []
    
    if audio_type == "sine":
        # Pure 440Hz sine wave
        for i in range(n_samples):
            t = i / sample_rate
            samples.append(math.sin(2 * math.pi * 440 * t))
            
    elif audio_type == "chord":
        # C major chord (C4, E4, G4)
        freqs = [261.63, 329.63, 392.00]
        for i in range(n_samples):
            t = i / sample_rate
            val = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
            samples.append(val)
            
    elif audio_type == "sweep":
        # Frequency sweep from 100Hz to 2000Hz
        for i in range(n_samples):
            t = i / sample_rate
            freq = 100 + (2000 - 100) * (t / duration)
            samples.append(math.sin(2 * math.pi * freq * t))
            
    elif audio_type == "noise":
        # White noise
        import random
        random.seed(42)
        samples = [random.uniform(-1, 1) for _ in range(n_samples)]
        
    elif audio_type == "drums":
        # Simulated drum pattern
        import random
        random.seed(42)
        beat_samples = sample_rate // 4  # 4 beats per second
        for i in range(n_samples):
            beat_pos = i % beat_samples
            if beat_pos < beat_samples // 8:
                # Kick-like burst
                decay = 1 - (beat_pos / (beat_samples // 8))
                samples.append(math.sin(2 * math.pi * 80 * i / sample_rate) * decay)
            elif beat_samples // 2 < beat_pos < beat_samples // 2 + beat_samples // 16:
                # Snare-like noise burst
                decay = 1 - ((beat_pos - beat_samples // 2) / (beat_samples // 16))
                samples.append(random.uniform(-1, 1) * decay * 0.7)
            else:
                samples.append(0.0)
                
    elif audio_type == "speech":
        # Speech-like formants
        formants = [500, 1500, 2500]  # Approximate vowel formants
        for i in range(n_samples):
            t = i / sample_rate
            # Modulate amplitude like speech rhythm
            amplitude = 0.5 + 0.5 * math.sin(2 * math.pi * 3 * t)
            # Mix formants
            val = sum(
                math.sin(2 * math.pi * f * t) * (1 / (j + 1))
                for j, f in enumerate(formants)
            ) / len(formants)
            samples.append(val * amplitude)
    
    else:
        # Default: silence
        samples = [0.0] * n_samples
    
    return samples


def demo():
    """Demonstrate audio fingerprinting."""
    print("\n" + "=" * 70)
    print("  AUDIO FINGERPRINT VISUALIZER")
    print("  Using Octo-Bresenham Interpolator")
    print("=" * 70)
    
    generator = AudioFingerprintGenerator(width=50, height=4)
    
    # Test with various audio types
    audio_types = ["sine", "chord", "sweep", "noise", "drums", "speech"]
    
    for audio_type in audio_types:
        print(f"\n{'─' * 70}")
        print(f"  Audio Type: {audio_type.upper()}")
        print(f"{'─' * 70}")
        
        samples = generate_test_audio(audio_type, duration=0.5)
        fp = generator.from_samples(samples, filename=f"{audio_type}_test.wav")
        print(generator.format_fingerprint(fp, show_spectrogram=True))


def demo_comparison():
    """Show how fingerprints can differentiate similar audio."""
    print("\n" + "=" * 70)
    print("  FINGERPRINT COMPARISON DEMO")
    print("  Spot the difference between similar audio files")
    print("=" * 70)
    
    generator = AudioFingerprintGenerator(width=50, height=3)
    
    # Two similar but different sine waves
    print("\n1. Two sine waves at different frequencies:")
    
    samples_440 = generate_test_audio("sine", duration=0.3)
    fp_440 = generator.from_samples(samples_440, filename="sine_440hz.wav")
    
    # 550Hz sine wave
    samples_550 = []
    for i in range(int(0.3 * 44100)):
        t = i / 44100
        samples_550.append(math.sin(2 * math.pi * 550 * t))
    fp_550 = generator.from_samples(samples_550, filename="sine_550hz.wav")
    
    print(f"\n   440 Hz: {fp_440.waveform}")
    print(f"   550 Hz: {fp_550.waveform}")
    print(f"\n   Spectrum 440Hz: {fp_440.spectrum_hash}")
    print(f"   Spectrum 550Hz: {fp_550.spectrum_hash}")
    
    # Same content, different volumes
    print("\n2. Same audio at different volumes:")
    
    samples_loud = generate_test_audio("chord", duration=0.3)
    samples_quiet = [s * 0.3 for s in samples_loud]
    
    fp_loud = generator.from_samples(samples_loud, filename="chord_loud.wav")
    fp_quiet = generator.from_samples(samples_quiet, filename="chord_quiet.wav")
    
    print(f"\n   Loud:  {fp_loud.envelope}")
    print(f"   Quiet: {fp_quiet.envelope}")


def create_wav_file(samples: List[float], filename: str, 
                    sample_rate: int = 44100):
    """Helper to create WAV files for testing."""
    with wave.open(filename, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        
        # Convert float samples to 16-bit PCM
        pcm_data = b''
        for s in samples:
            # Clamp to -1, 1
            s = max(-1.0, min(1.0, s))
            # Convert to 16-bit signed integer
            pcm_val = int(s * 32767)
            pcm_data += struct.pack('<h', pcm_val)
        
        wav.writeframes(pcm_data)
    
    print(f"Created: {filename}")


if __name__ == "__main__":
    demo()
    demo_comparison()
    
    print("\n" + "=" * 70)
    print("  To fingerprint your own audio files:")
    print("  ")
    print("    from audio_fingerprint import AudioFingerprintGenerator")
    print("    gen = AudioFingerprintGenerator()")
    print("    fp = gen.from_wav_file('your_audio.wav')")
    print("    print(gen.format_fingerprint(fp))")
    print("=" * 70)
