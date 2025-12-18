#!/usr/bin/env python3
"""
YouTube Audio Fingerprint Generator
====================================

Downloads audio from YouTube videos and generates Braille-based
tactile fingerprints using the Octo-Bresenham Interpolator.

Requirements:
    pip install yt-dlp

Usage:
    python youtube_fingerprint.py https://www.youtube.com/watch?v=VIDEO_ID
    python youtube_fingerprint.py VIDEO_ID
    python youtube_fingerprint.py --compare URL1 URL2

Author: Ryan Barrett
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple

from audio_fingerprint import AudioFingerprintGenerator, AudioFingerprint


class YouTubeFingerprint:
    """
    Downloads YouTube audio and generates Braille fingerprints.
    """
    
    def __init__(self, width: int = 60, height: int = 4, 
                 keep_audio: bool = False, output_dir: Optional[str] = None):
        """
        Args:
            width: Character width for fingerprint
            height: Row height for spectrogram
            keep_audio: If True, keeps downloaded audio files
            output_dir: Directory for saved files (default: temp)
        """
        self.width = width
        self.height = height
        self.keep_audio = keep_audio
        self.output_dir = output_dir or tempfile.gettempdir()
        self.generator = AudioFingerprintGenerator(width=width, height=height)
        
        # Check for yt-dlp
        self._check_ytdlp()
    
    def _check_ytdlp(self):
        """Verify yt-dlp is installed."""
        try:
            result = subprocess.run(
                ['yt-dlp', '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise FileNotFoundError
        except FileNotFoundError:
            print("⚠️  yt-dlp not found. Install with: brew install yt-dlp")
            print("   Or: pip install yt-dlp")
            sys.exit(1)
    
    def _normalize_url(self, url_or_id: str) -> str:
        """Convert video ID to full URL if needed."""
        if url_or_id.startswith(('http://', 'https://')):
            return url_or_id
        # Assume it's a video ID
        return f"https://www.youtube.com/watch?v={url_or_id}"
    
    def _get_video_info(self, url: str) -> dict:
        """Get video metadata without downloading."""
        result = subprocess.run(
            ['yt-dlp', '--dump-json', '--no-download', url],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get video info: {result.stderr}")
        
        import json
        return json.loads(result.stdout)
    
    def download_audio(self, url: str, output_path: Optional[str] = None) -> str:
        """
        Download audio from YouTube video.
        
        Args:
            url: YouTube URL or video ID
            output_path: Optional output file path
            
        Returns:
            Path to downloaded WAV file
        """
        url = self._normalize_url(url)
        
        if output_path is None:
            # Create temp file
            output_path = os.path.join(self.output_dir, 'yt_audio_%(id)s.%(ext)s')
        
        print(f"⏳ Downloading audio from: {url}")
        
        # Download with yt-dlp
        cmd = [
            'yt-dlp',
            '-x',                      # Extract audio only
            '--audio-format', 'wav',   # Convert to WAV
            '--audio-quality', '0',    # Best quality
            '-o', output_path,         # Output template
            '--no-playlist',           # Single video only
            '--quiet',                 # Less verbose
            '--progress',              # But show progress
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Download failed: {result.stderr}")
        
        # Find the actual output file
        if '%(id)s' in output_path:
            # Get video ID from URL
            info = self._get_video_info(url)
            video_id = info.get('id', 'unknown')
            actual_path = output_path.replace('%(id)s', video_id).replace('%(ext)s', 'wav')
        else:
            actual_path = output_path.replace('%(ext)s', 'wav')
        
        if not os.path.exists(actual_path):
            # Search for the file
            for f in os.listdir(self.output_dir):
                if f.endswith('.wav') and 'yt_audio' in f:
                    actual_path = os.path.join(self.output_dir, f)
                    break
        
        print(f"✅ Downloaded: {actual_path}")
        return actual_path
    
    def fingerprint_url(self, url: str, 
                        show_spectrogram: bool = True) -> Tuple[AudioFingerprint, str]:
        """
        Generate fingerprint from YouTube URL.
        
        Args:
            url: YouTube URL or video ID
            show_spectrogram: Include spectrogram in output
            
        Returns:
            Tuple of (AudioFingerprint, formatted_string)
        """
        url = self._normalize_url(url)
        
        # Get video info for title
        try:
            info = self._get_video_info(url)
            title = info.get('title', 'Unknown')[:50]
            duration = info.get('duration', 0)
            print(f"📺 Video: {title}")
            print(f"⏱️  Duration: {duration}s")
        except Exception as e:
            print(f"⚠️  Could not get video info: {e}")
            title = "Unknown"
        
        # Download audio
        audio_path = self.download_audio(url)
        
        try:
            # Generate fingerprint
            print("🔍 Generating Braille fingerprint...")
            fp = self.generator.from_wav_file(audio_path)
            
            # Override filename with video title
            fp.filename = title
            
            formatted = self.generator.format_fingerprint(fp, show_spectrogram)
            
            return fp, formatted
            
        finally:
            # Cleanup if not keeping audio
            if not self.keep_audio and os.path.exists(audio_path):
                os.remove(audio_path)
                print("🗑️  Cleaned up temporary audio file")
    
    def compare_videos(self, urls: List[str]) -> str:
        """
        Compare fingerprints of multiple videos side by side.
        
        Args:
            urls: List of YouTube URLs or video IDs
            
        Returns:
            Formatted comparison string
        """
        fingerprints = []
        
        for url in urls:
            try:
                fp, _ = self.fingerprint_url(url, show_spectrogram=False)
                fingerprints.append(fp)
            except Exception as e:
                print(f"⚠️  Failed to process {url}: {e}")
        
        if len(fingerprints) < 2:
            return "Need at least 2 videos to compare"
        
        lines = [
            "╔" + "═" * 62 + "╗",
            "║  FINGERPRINT COMPARISON" + " " * 37 + "║",
            "╠" + "═" * 62 + "╣",
        ]
        
        for i, fp in enumerate(fingerprints):
            lines.append(f"║ [{i+1}] {fp.filename[:55]:<55} ║")
        
        lines.append("╠" + "═" * 62 + "╣")
        lines.append("║ Waveforms:" + " " * 51 + "║")
        
        for i, fp in enumerate(fingerprints):
            lines.append(f"║ [{i+1}] {fp.waveform[:55]} ║")
        
        lines.append("╠" + "═" * 62 + "╣")
        lines.append("║ Envelopes:" + " " * 51 + "║")
        
        for i, fp in enumerate(fingerprints):
            lines.append(f"║ [{i+1}] {fp.envelope[:55]} ║")
        
        lines.append("╠" + "═" * 62 + "╣")
        lines.append("║ Spectrums:" + " " * 51 + "║")
        
        for i, fp in enumerate(fingerprints):
            lines.append(f"║ [{i+1}] {fp.spectrum_hash} (RMS: {fp.metadata['rms']:.3f}, Peak: {fp.metadata['peak']:.3f}) ║")
        
        lines.append("╚" + "═" * 62 + "╝")
        
        return '\n'.join(lines)
    
    def fingerprint_segment(self, url: str, start_time: int = 0, 
                            duration: int = 30) -> Tuple[AudioFingerprint, str]:
        """
        Fingerprint a specific segment of a video.
        
        Args:
            url: YouTube URL or video ID
            start_time: Start time in seconds
            duration: Duration in seconds
            
        Returns:
            Tuple of (AudioFingerprint, formatted_string)
        """
        url = self._normalize_url(url)
        
        # Use yt-dlp with time range
        output_path = os.path.join(self.output_dir, f'yt_segment_{start_time}_{duration}.wav')
        
        print(f"⏳ Downloading segment: {start_time}s to {start_time + duration}s")
        
        cmd = [
            'yt-dlp',
            '-x',
            '--audio-format', 'wav',
            '--download-sections', f'*{start_time}-{start_time + duration}',
            '-o', output_path,
            '--no-playlist',
            '--quiet',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Download failed: {result.stderr}")
        
        try:
            fp = self.generator.from_wav_file(output_path)
            fp.filename = f"Segment {start_time}s-{start_time+duration}s"
            formatted = self.generator.format_fingerprint(fp)
            return fp, formatted
        finally:
            if not self.keep_audio and os.path.exists(output_path):
                os.remove(output_path)


def main():
    parser = argparse.ArgumentParser(
        description='Generate Braille fingerprints from YouTube audio',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://www.youtube.com/watch?v=dQw4w9WgXcQ
  %(prog)s dQw4w9WgXcQ
  %(prog)s --compare URL1 URL2 URL3
  %(prog)s --segment 30 60 URL  # Fingerprint 30s-90s
  %(prog)s --keep URL           # Keep downloaded audio
        """
    )
    
    parser.add_argument('urls', nargs='*', help='YouTube URL(s) or video ID(s)')
    parser.add_argument('--compare', action='store_true', 
                        help='Compare multiple videos')
    parser.add_argument('--segment', nargs=2, type=int, metavar=('START', 'DURATION'),
                        help='Fingerprint specific segment (start_seconds duration_seconds)')
    parser.add_argument('--width', type=int, default=60,
                        help='Output width in characters (default: 60)')
    parser.add_argument('--height', type=int, default=4,
                        help='Spectrogram height in rows (default: 4)')
    parser.add_argument('--keep', action='store_true',
                        help='Keep downloaded audio files')
    parser.add_argument('--no-spectrogram', action='store_true',
                        help='Skip spectrogram generation')
    parser.add_argument('--output', '-o', type=str,
                        help='Output directory for audio files')
    
    args = parser.parse_args()
    
    if not args.urls:
        parser.print_help()
        sys.exit(1)
    
    yt_fp = YouTubeFingerprint(
        width=args.width,
        height=args.height,
        keep_audio=args.keep,
        output_dir=args.output
    )
    
    print("\n" + "=" * 64)
    print("  🎵 YOUTUBE BRAILLE AUDIO FINGERPRINT GENERATOR")
    print("  Using Octo-Bresenham Interpolator")
    print("=" * 64 + "\n")
    
    try:
        if args.compare:
            result = yt_fp.compare_videos(args.urls)
            print(result)
        elif args.segment:
            start, duration = args.segment
            fp, formatted = yt_fp.fingerprint_segment(
                args.urls[0], start_time=start, duration=duration
            )
            print(formatted)
        else:
            for url in args.urls:
                fp, formatted = yt_fp.fingerprint_url(
                    url, show_spectrogram=not args.no_spectrogram
                )
                print(formatted)
                print()
                
    except KeyboardInterrupt:
        print("\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()
