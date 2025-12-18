#!/usr/bin/env python3
"""
Braille Audio Search Engine
============================

Search for audio by matching 8-dot Braille fingerprints.
Like Shazam, but tactile and text-based.

Features:
- Index YouTube videos into a fingerprint database
- Search by audio sample or YouTube URL
- Find matching segments across videos
- Similarity scoring using Braille pattern distance

Author: Ryan Barrett
"""

import json
import math
import os
import sqlite3
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Generator
import struct

from octo_bresenham import OctoBresenham
from audio_fingerprint import AudioFingerprintGenerator, AudioFingerprint


@dataclass
class FingerprintChunk:
    """A searchable chunk of an audio fingerprint."""
    chunk_id: str
    video_id: str
    video_title: str
    start_time: float      # seconds
    duration: float        # seconds
    waveform: str          # Braille waveform for this chunk
    envelope: str          # Braille envelope
    spectrum: str          # 8-char spectrum hash
    energy: float          # RMS energy
    feature_hash: str      # Combined hash for fast lookup


@dataclass
class SearchResult:
    """A match found in the database."""
    video_id: str
    video_title: str
    match_time: float      # Where in the video the match occurs
    similarity: float      # 0.0 to 1.0
    query_segment: str     # Which part of query matched
    matched_waveform: str  # The matching waveform
    youtube_url: str


class BrailleAudioSearch:
    """
    Search engine for audio using Braille fingerprints.
    """
    
    # Braille character to dot pattern mapping for distance calculation
    BRAILLE_BASE = 0x2800
    
    def __init__(self, db_path: str = "braille_audio.db", 
                 chunk_duration: float = 3.0,
                 fingerprint_width: int = 30):
        """
        Args:
            db_path: Path to SQLite database
            chunk_duration: Duration of each searchable chunk (seconds)
            fingerprint_width: Width of fingerprint per chunk
        """
        self.db_path = db_path
        self.chunk_duration = chunk_duration
        self.fingerprint_width = fingerprint_width
        self.generator = AudioFingerprintGenerator(
            width=fingerprint_width, 
            height=2
        )
        self.bresenham = OctoBresenham()
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main fingerprint chunks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fingerprint_chunks (
                chunk_id TEXT PRIMARY KEY,
                video_id TEXT NOT NULL,
                video_title TEXT,
                start_time REAL,
                duration REAL,
                waveform TEXT,
                envelope TEXT,
                spectrum TEXT,
                energy REAL,
                feature_hash TEXT,
                created_at TEXT
            )
        ''')
        
        # Index for fast spectrum lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_spectrum 
            ON fingerprint_chunks(spectrum)
        ''')
        
        # Index for feature hash (coarse matching)
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_feature_hash 
            ON fingerprint_chunks(feature_hash)
        ''')
        
        # Videos metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                duration REAL,
                url TEXT,
                full_waveform TEXT,
                full_envelope TEXT,
                indexed_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _braille_to_dots(self, char: str) -> int:
        """Convert Braille character to dot bitmask."""
        if len(char) != 1:
            return 0
        code = ord(char)
        if code < self.BRAILLE_BASE or code > self.BRAILLE_BASE + 255:
            return 0
        return code - self.BRAILLE_BASE
    
    def _dots_to_braille(self, dots: int) -> str:
        """Convert dot bitmask to Braille character."""
        return chr(self.BRAILLE_BASE + (dots & 0xFF))
    
    def _hamming_distance(self, a: str, b: str) -> int:
        """Calculate Hamming distance between two Braille strings."""
        distance = 0
        max_len = max(len(a), len(b))
        a = a.ljust(max_len, chr(self.BRAILLE_BASE))
        b = b.ljust(max_len, chr(self.BRAILLE_BASE))
        
        for ca, cb in zip(a, b):
            dots_a = self._braille_to_dots(ca)
            dots_b = self._braille_to_dots(cb)
            # Count differing bits
            xor = dots_a ^ dots_b
            distance += bin(xor).count('1')
        
        return distance
    
    def _similarity_score(self, a: str, b: str) -> float:
        """
        Calculate similarity between two Braille strings.
        Returns 0.0 (completely different) to 1.0 (identical).
        """
        if not a or not b:
            return 0.0
        
        # Normalize lengths
        max_len = max(len(a), len(b))
        if max_len == 0:
            return 1.0
        
        # Maximum possible distance (8 bits per character)
        max_distance = max_len * 8
        
        distance = self._hamming_distance(a, b)
        
        return 1.0 - (distance / max_distance)
    
    def _compute_feature_hash(self, waveform: str, spectrum: str) -> str:
        """Compute a coarse hash for fast filtering."""
        # Quantize waveform to 4 levels
        quantized = []
        for char in waveform[:16]:  # First 16 chars
            dots = self._braille_to_dots(char)
            # Count active dots (0-8) and bucket
            active = bin(dots).count('1')
            quantized.append(str(active // 3))  # 0, 1, or 2
        
        return hashlib.md5(
            (''.join(quantized) + spectrum).encode()
        ).hexdigest()[:8]
    
    def index_audio_file(self, audio_path: str, video_id: str, 
                         video_title: str, video_url: str = "") -> int:
        """
        Index an audio file into the database.
        
        Args:
            audio_path: Path to WAV file
            video_id: Unique identifier
            video_title: Display title
            video_url: YouTube URL (optional)
            
        Returns:
            Number of chunks indexed
        """
        import wave
        
        # Read audio file
        with wave.open(audio_path, 'rb') as wav:
            sample_rate = wav.getframerate()
            n_frames = wav.getnframes()
            n_channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            raw_data = wav.readframes(n_frames)
        
        # Convert to samples
        samples = self._bytes_to_samples(raw_data, sample_width, n_channels)
        duration = len(samples) / sample_rate
        
        # Generate full fingerprint for storage
        full_fp = self.generator.from_samples(samples, sample_rate, video_title)
        
        # Split into chunks and index
        chunk_samples = int(self.chunk_duration * sample_rate)
        chunks_indexed = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Store video metadata
        cursor.execute('''
            INSERT OR REPLACE INTO videos 
            (video_id, title, duration, url, full_waveform, full_envelope, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            video_id, video_title, duration, video_url,
            full_fp.waveform, full_fp.envelope,
            datetime.now().isoformat()
        ))
        
        # Index chunks
        for i in range(0, len(samples) - chunk_samples, chunk_samples // 2):
            # 50% overlap for better matching
            chunk = samples[i:i + chunk_samples]
            start_time = i / sample_rate
            
            # Generate fingerprint for chunk
            chunk_fp = self.generator.from_samples(
                chunk, sample_rate, f"{video_title}_{start_time:.1f}s"
            )
            
            # Compute feature hash
            feature_hash = self._compute_feature_hash(
                chunk_fp.waveform, chunk_fp.spectrum_hash
            )
            
            chunk_id = f"{video_id}_{i}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO fingerprint_chunks
                (chunk_id, video_id, video_title, start_time, duration,
                 waveform, envelope, spectrum, energy, feature_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chunk_id, video_id, video_title, start_time, self.chunk_duration,
                chunk_fp.waveform, chunk_fp.envelope, chunk_fp.spectrum_hash,
                chunk_fp.metadata['rms'], feature_hash,
                datetime.now().isoformat()
            ))
            
            chunks_indexed += 1
        
        conn.commit()
        conn.close()
        
        print(f"✅ Indexed {chunks_indexed} chunks from '{video_title}'")
        return chunks_indexed
    
    def index_youtube(self, url: str) -> int:
        """
        Index a YouTube video into the database.
        
        Args:
            url: YouTube URL or video ID
            
        Returns:
            Number of chunks indexed
        """
        from youtube_fingerprint import YouTubeFingerprint
        
        yt = YouTubeFingerprint(keep_audio=True)
        
        # Get video info
        info = yt._get_video_info(yt._normalize_url(url))
        video_id = info.get('id', url)
        title = info.get('title', 'Unknown')
        
        # Download audio
        audio_path = yt.download_audio(url)
        
        try:
            return self.index_audio_file(
                audio_path, video_id, title,
                f"https://youtube.com/watch?v={video_id}"
            )
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
    
    def search(self, query_samples: List[float], sample_rate: int = 44100,
               top_k: int = 5, min_similarity: float = 0.6) -> List[SearchResult]:
        """
        Search for matching audio in the database.
        
        Args:
            query_samples: Audio samples to search for
            sample_rate: Sample rate of query audio
            top_k: Maximum results to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of SearchResult objects
        """
        # Generate fingerprint for query
        query_fp = self.generator.from_samples(
            query_samples, sample_rate, "query"
        )
        
        # Compute feature hash for filtering
        query_hash = self._compute_feature_hash(
            query_fp.waveform, query_fp.spectrum_hash
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First pass: filter by feature hash (coarse)
        cursor.execute('''
            SELECT * FROM fingerprint_chunks 
            WHERE feature_hash = ?
        ''', (query_hash,))
        
        candidates = cursor.fetchall()
        
        # If no exact hash matches, do broader search
        if not candidates:
            cursor.execute('''
                SELECT * FROM fingerprint_chunks
            ''')
            candidates = cursor.fetchall()
        
        # Second pass: compute detailed similarity
        results = []
        for row in candidates:
            chunk = FingerprintChunk(
                chunk_id=row[0],
                video_id=row[1],
                video_title=row[2],
                start_time=row[3],
                duration=row[4],
                waveform=row[5],
                envelope=row[6],
                spectrum=row[7],
                energy=row[8],
                feature_hash=row[9]
            )
            
            # Multi-factor similarity
            waveform_sim = self._similarity_score(query_fp.waveform, chunk.waveform)
            envelope_sim = self._similarity_score(query_fp.envelope, chunk.envelope)
            spectrum_sim = self._similarity_score(query_fp.spectrum_hash, chunk.spectrum)
            
            # Weighted combination
            similarity = (
                waveform_sim * 0.5 +
                envelope_sim * 0.3 +
                spectrum_sim * 0.2
            )
            
            if similarity >= min_similarity:
                results.append(SearchResult(
                    video_id=chunk.video_id,
                    video_title=chunk.video_title,
                    match_time=chunk.start_time,
                    similarity=similarity,
                    query_segment=query_fp.waveform[:20],
                    matched_waveform=chunk.waveform,
                    youtube_url=f"https://youtube.com/watch?v={chunk.video_id}&t={int(chunk.start_time)}"
                ))
        
        conn.close()
        
        # Sort by similarity and return top-k
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]
    
    def search_youtube(self, url: str, segment_start: int = 0, 
                       segment_duration: int = 10,
                       top_k: int = 5) -> List[SearchResult]:
        """
        Search database using audio from a YouTube video.
        
        Args:
            url: YouTube URL to use as query
            segment_start: Start time in seconds
            segment_duration: Duration to sample
            top_k: Maximum results
            
        Returns:
            List of SearchResult objects
        """
        from youtube_fingerprint import YouTubeFingerprint
        import wave
        
        yt = YouTubeFingerprint(keep_audio=True)
        
        # Download segment
        audio_path = yt.download_audio(url)
        
        try:
            with wave.open(audio_path, 'rb') as wav:
                sample_rate = wav.getframerate()
                n_channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                
                # Seek to start position
                start_frame = segment_start * sample_rate
                wav.setpos(min(start_frame, wav.getnframes() - 1))
                
                # Read segment
                n_frames = min(segment_duration * sample_rate, 
                              wav.getnframes() - start_frame)
                raw_data = wav.readframes(n_frames)
            
            samples = self._bytes_to_samples(raw_data, sample_width, n_channels)
            return self.search(samples, sample_rate, top_k)
            
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
    
    def search_wav(self, wav_path: str, top_k: int = 5) -> List[SearchResult]:
        """Search using a WAV file as query."""
        import wave
        
        with wave.open(wav_path, 'rb') as wav:
            sample_rate = wav.getframerate()
            n_channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            raw_data = wav.readframes(wav.getnframes())
        
        samples = self._bytes_to_samples(raw_data, sample_width, n_channels)
        return self.search(samples, sample_rate, top_k)
    
    def _bytes_to_samples(self, raw_data: bytes, sample_width: int,
                          n_channels: int) -> List[float]:
        """Convert raw audio bytes to normalized float samples."""
        if sample_width == 1:
            fmt, max_val, offset = 'B', 128.0, 128
        elif sample_width == 2:
            fmt, max_val, offset = 'h', 32768.0, 0
        elif sample_width == 4:
            fmt, max_val, offset = 'i', 2147483648.0, 0
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")
        
        n_samples = len(raw_data) // sample_width
        samples = struct.unpack(f'<{n_samples}{fmt}', raw_data)
        
        if n_channels == 2:
            mono = []
            for i in range(0, len(samples), 2):
                if i + 1 < len(samples):
                    mono.append((samples[i] + samples[i + 1]) / 2)
            samples = mono
        
        return [(s - offset) / max_val for s in samples]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM videos')
        n_videos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM fingerprint_chunks')
        n_chunks = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(duration) FROM videos')
        total_duration = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'videos': n_videos,
            'chunks': n_chunks,
            'total_duration_seconds': total_duration,
            'total_duration_formatted': f"{total_duration // 60:.0f}m {total_duration % 60:.0f}s"
        }
    
    def list_videos(self) -> List[Dict[str, Any]]:
        """List all indexed videos."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT video_id, title, duration, url, full_waveform, indexed_at
            FROM videos ORDER BY indexed_at DESC
        ''')
        
        videos = []
        for row in cursor.fetchall():
            videos.append({
                'video_id': row[0],
                'title': row[1],
                'duration': row[2],
                'url': row[3],
                'waveform': row[4][:40] + '...' if row[4] and len(row[4]) > 40 else row[4],
                'indexed_at': row[5]
            })
        
        conn.close()
        return videos
    
    def format_results(self, results: List[SearchResult]) -> str:
        """Format search results for display."""
        if not results:
            return "❌ No matches found"
        
        lines = [
            "╔════════════════════════════════════════════════════════════════╗",
            "║  🔍 SEARCH RESULTS                                             ║",
            "╠════════════════════════════════════════════════════════════════╣",
        ]
        
        for i, r in enumerate(results):
            sim_bar = "█" * int(r.similarity * 10) + "░" * (10 - int(r.similarity * 10))
            lines.append(f"║ [{i+1}] {r.video_title[:45]:<45} ║")
            lines.append(f"║     Similarity: {sim_bar} {r.similarity:.1%}              ║")
            lines.append(f"║     Match at: {r.match_time:.1f}s                                     ║")
            lines.append(f"║     Waveform: {r.matched_waveform[:35]}... ║")
            lines.append(f"║     URL: {r.youtube_url[:50]:<50} ║")
            if i < len(results) - 1:
                lines.append("╠────────────────────────────────────────────────────────────────╣")
        
        lines.append("╚════════════════════════════════════════════════════════════════╝")
        
        return '\n'.join(lines)


def demo():
    """Demonstrate the search system."""
    print("\n" + "=" * 66)
    print("  🔍 BRAILLE AUDIO SEARCH ENGINE")
    print("  Find sounds using 8-dot Braille fingerprints")
    print("=" * 66)
    
    from audio_fingerprint import generate_test_audio
    
    search = BrailleAudioSearch(db_path="demo_audio.db")
    
    # Index some test audio
    print("\n📥 Indexing test audio...")
    
    test_types = ["sine", "chord", "drums", "speech"]
    for audio_type in test_types:
        samples = generate_test_audio(audio_type, duration=10.0)
        
        # Save to temp WAV
        import wave
        import struct
        temp_path = f"/tmp/test_{audio_type}.wav"
        with wave.open(temp_path, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(44100)
            pcm = b''.join(
                struct.pack('<h', int(max(-1, min(1, s)) * 32767))
                for s in samples
            )
            wav.writeframes(pcm)
        
        search.index_audio_file(
            temp_path, 
            f"test_{audio_type}", 
            f"Test {audio_type.title()} Audio",
            f"local://test_{audio_type}"
        )
        os.remove(temp_path)
    
    # Show stats
    stats = search.get_stats()
    print(f"\n📊 Database: {stats['videos']} videos, {stats['chunks']} chunks")
    print(f"   Total duration: {stats['total_duration_formatted']}")
    
    # Search for a chord
    print("\n🔍 Searching for chord-like audio...")
    query = generate_test_audio("chord", duration=3.0)
    results = search.search(query, min_similarity=0.3)
    print(search.format_results(results))
    
    # Search for drums
    print("\n🔍 Searching for drum-like audio...")
    query = generate_test_audio("drums", duration=3.0)
    results = search.search(query, min_similarity=0.3)
    print(search.format_results(results))
    
    # Clean up demo database
    os.remove("demo_audio.db")
    
    print("\n✨ Demo complete!")


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Search for audio using Braille fingerprints',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s index URL              # Index a YouTube video
  %(prog)s search URL             # Search using YouTube audio
  %(prog)s search --wav file.wav  # Search using WAV file
  %(prog)s list                   # List indexed videos
  %(prog)s stats                  # Show database stats
  %(prog)s demo                   # Run demonstration
        """
    )
    
    parser.add_argument('command', choices=['index', 'search', 'list', 'stats', 'demo'],
                        help='Command to run')
    parser.add_argument('url', nargs='?', help='YouTube URL or video ID')
    parser.add_argument('--wav', type=str, help='WAV file path for search')
    parser.add_argument('--db', type=str, default='braille_audio.db',
                        help='Database path')
    parser.add_argument('--top', type=int, default=5,
                        help='Number of results to return')
    parser.add_argument('--start', type=int, default=0,
                        help='Start time for search segment')
    parser.add_argument('--duration', type=int, default=10,
                        help='Duration for search segment')
    
    args = parser.parse_args()
    
    if args.command == 'demo':
        demo()
        return
    
    search = BrailleAudioSearch(db_path=args.db)
    
    if args.command == 'index':
        if not args.url:
            print("❌ URL required for indexing")
            return
        print(f"\n📥 Indexing: {args.url}")
        search.index_youtube(args.url)
        
    elif args.command == 'search':
        if args.wav:
            print(f"\n🔍 Searching with: {args.wav}")
            results = search.search_wav(args.wav, top_k=args.top)
        elif args.url:
            print(f"\n🔍 Searching with: {args.url}")
            results = search.search_youtube(
                args.url, 
                segment_start=args.start,
                segment_duration=args.duration,
                top_k=args.top
            )
        else:
            print("❌ URL or --wav required for search")
            return
        print(search.format_results(results))
        
    elif args.command == 'list':
        videos = search.list_videos()
        if not videos:
            print("📭 No videos indexed yet")
        else:
            print("\n📺 Indexed Videos:")
            for v in videos:
                print(f"  • {v['title'][:50]} ({v['duration']:.0f}s)")
                print(f"    {v['waveform']}")
                
    elif args.command == 'stats':
        stats = search.get_stats()
        print(f"\n📊 Database Statistics:")
        print(f"   Videos: {stats['videos']}")
        print(f"   Chunks: {stats['chunks']}")
        print(f"   Duration: {stats['total_duration_formatted']}")


if __name__ == "__main__":
    main()
