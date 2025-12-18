#!/usr/bin/env python3
"""
Dot-Flow Audio Search Engine
============================

Search engine that uses the NOVEL Temporal Dot-Flow algorithm
instead of standard pattern matching.

This integrates dot_flow.py into the search pipeline for
genuinely novel audio fingerprint matching.

Author: Ryan Barrett
"""

import os
import sqlite3
import struct
import wave
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

from dot_flow import TemporalDotFlow, FlowSignature, FlowDirection
from audio_fingerprint import AudioFingerprintGenerator
from octo_bresenham import OctoBresenham


@dataclass
class FlowSearchResult:
    """A match found using dot-flow similarity."""
    video_id: str
    video_title: str
    match_time: float
    flow_similarity: float      # Novel: based on transitions
    pattern_similarity: float   # Traditional: based on dots
    combined_score: float
    query_flow: str            # Flow sequence of query
    matched_flow: str          # Flow sequence of match
    dominant_flow: str         # UP, DOWN, PULSE, etc.
    youtube_url: str


class DotFlowSearch:
    """
    Audio search using Temporal Dot-Flow Encoding.
    
    Key difference from traditional search:
    - Compares HOW patterns change, not the patterns themselves
    - Two different audio files can match if they "feel" the same
    """
    
    def __init__(self, db_path: str = "dotflow_audio.db",
                 chunk_duration: float = 3.0):
        self.db_path = db_path
        self.chunk_duration = chunk_duration
        self.flow = TemporalDotFlow()
        self.generator = AudioFingerprintGenerator(width=40, height=2)
        self._init_database()
    
    def _init_database(self):
        """Initialize database with flow-specific columns."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flow_chunks (
                chunk_id TEXT PRIMARY KEY,
                video_id TEXT NOT NULL,
                video_title TEXT,
                start_time REAL,
                duration REAL,
                waveform TEXT,
                flow_sequence TEXT,
                rhythm_pattern TEXT,
                dominant_flow TEXT,
                energy_contour TEXT,
                created_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_flow_seq 
            ON flow_chunks(flow_sequence)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_dominant 
            ON flow_chunks(dominant_flow)
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                duration REAL,
                url TEXT,
                indexed_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def index_audio_file(self, audio_path: str, video_id: str,
                         video_title: str, video_url: str = "") -> int:
        """Index an audio file using dot-flow encoding."""
        with wave.open(audio_path, 'rb') as wav:
            sample_rate = wav.getframerate()
            n_frames = wav.getnframes()
            n_channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            raw_data = wav.readframes(n_frames)
        
        samples = self._bytes_to_samples(raw_data, sample_width, n_channels)
        duration = len(samples) / sample_rate
        
        chunk_samples = int(self.chunk_duration * sample_rate)
        chunks_indexed = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO videos 
            (video_id, title, duration, url, indexed_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (video_id, video_title, duration, video_url, 
              datetime.now().isoformat()))
        
        for i in range(0, len(samples) - chunk_samples, chunk_samples // 2):
            chunk = samples[i:i + chunk_samples]
            start_time = i / sample_rate
            
            # Generate fingerprint
            chunk_fp = self.generator.from_samples(chunk, sample_rate)
            
            # Encode as flow signature (THE NOVEL PART)
            flow_sig = self.flow.encode(chunk_fp.waveform)
            
            chunk_id = f"{video_id}_{i}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO flow_chunks
                (chunk_id, video_id, video_title, start_time, duration,
                 waveform, flow_sequence, rhythm_pattern, dominant_flow,
                 energy_contour, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chunk_id, video_id, video_title, start_time, self.chunk_duration,
                chunk_fp.waveform, flow_sig.flow_sequence, flow_sig.rhythm_pattern,
                flow_sig.dominant_flow.name,
                ','.join(f"{e:.3f}" for e in flow_sig.energy_contour[:20]),
                datetime.now().isoformat()
            ))
            
            chunks_indexed += 1
        
        conn.commit()
        conn.close()
        
        print(f"✅ Indexed {chunks_indexed} flow chunks from '{video_title}'")
        return chunks_indexed
    
    def index_youtube(self, url: str) -> int:
        """Index a YouTube video."""
        from youtube_fingerprint import YouTubeFingerprint
        
        yt = YouTubeFingerprint(keep_audio=True)
        info = yt._get_video_info(yt._normalize_url(url))
        video_id = info.get('id', url)
        title = info.get('title', 'Unknown')
        
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
               top_k: int = 5, min_similarity: float = 0.4) -> List[FlowSearchResult]:
        """
        Search using dot-flow similarity.
        
        This is NOVEL because we match based on:
        1. Flow sequence (how dots transition)
        2. Rhythm pattern (where energy changes occur)
        3. Dominant flow direction
        """
        query_fp = self.generator.from_samples(query_samples, sample_rate)
        query_flow = self.flow.encode(query_fp.waveform)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First: filter by dominant flow (coarse)
        cursor.execute('''
            SELECT * FROM flow_chunks WHERE dominant_flow = ?
        ''', (query_flow.dominant_flow.name,))
        
        candidates = cursor.fetchall()
        
        # Fallback to all if no matches
        if not candidates:
            cursor.execute('SELECT * FROM flow_chunks')
            candidates = cursor.fetchall()
        
        results = []
        for row in candidates:
            # Reconstruct flow signature from stored data
            stored_flow = FlowSignature(
                source=row[5],
                transitions=[],
                flow_sequence=row[6],
                rhythm_pattern=row[7],
                energy_contour=[float(x) for x in row[9].split(',') if x],
                dominant_flow=FlowDirection[row[8]]
            )
            
            # Compute NOVEL flow-based similarity
            flow_sim = self.flow.flow_similarity(query_flow, stored_flow)
            
            # Also compute traditional pattern similarity for comparison
            pattern_sim = self._pattern_similarity(query_fp.waveform, row[5])
            
            # Combined score (flow-weighted)
            combined = flow_sim * 0.7 + pattern_sim * 0.3
            
            if combined >= min_similarity:
                results.append(FlowSearchResult(
                    video_id=row[1],
                    video_title=row[2],
                    match_time=row[3],
                    flow_similarity=flow_sim,
                    pattern_similarity=pattern_sim,
                    combined_score=combined,
                    query_flow=query_flow.flow_sequence[:30],
                    matched_flow=stored_flow.flow_sequence[:30],
                    dominant_flow=stored_flow.dominant_flow.name,
                    youtube_url=f"https://youtube.com/watch?v={row[1]}&t={int(row[3])}"
                ))
        
        conn.close()
        
        results.sort(key=lambda x: x.combined_score, reverse=True)
        return results[:top_k]
    
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
        
        max_distance = max_len * 8
        return 1.0 - (distance / max_distance)
    
    def _bytes_to_samples(self, raw_data: bytes, sample_width: int,
                          n_channels: int) -> List[float]:
        """Convert raw audio to normalized samples."""
        if sample_width == 1:
            fmt, max_val, offset = 'B', 128.0, 128
        elif sample_width == 2:
            fmt, max_val, offset = 'h', 32768.0, 0
        else:
            fmt, max_val, offset = 'i', 2147483648.0, 0
        
        n_samples = len(raw_data) // sample_width
        samples = struct.unpack(f'<{n_samples}{fmt}', raw_data)
        
        if n_channels == 2:
            mono = [(samples[i] + samples[i+1]) / 2 
                    for i in range(0, len(samples) - 1, 2)]
            samples = mono
        
        return [(s - offset) / max_val for s in samples]
    
    def format_results(self, results: List[FlowSearchResult]) -> str:
        """Format results with flow information."""
        if not results:
            return "❌ No matches found"
        
        lines = [
            "╔══════════════════════════════════════════════════════════════════╗",
            "║  🔍 DOT-FLOW SEARCH RESULTS (Novel Algorithm)                    ║",
            "╠══════════════════════════════════════════════════════════════════╣",
        ]
        
        for i, r in enumerate(results):
            flow_bar = "█" * int(r.flow_similarity * 10) + "░" * (10 - int(r.flow_similarity * 10))
            lines.extend([
                f"║ [{i+1}] {r.video_title[:50]:<50} ║",
                f"║     Flow Sim:    {flow_bar} {r.flow_similarity:.1%}                    ║",
                f"║     Pattern Sim: {r.pattern_similarity:.1%} | Combined: {r.combined_score:.1%}            ║",
                f"║     Dominant:    {r.dominant_flow:<20} @ {r.match_time:.1f}s        ║",
                f"║     Query Flow:  {r.query_flow:<40} ║",
                f"║     Match Flow:  {r.matched_flow:<40} ║",
            ])
            if i < len(results) - 1:
                lines.append("╠──────────────────────────────────────────────────────────────────╣")
        
        lines.append("╚══════════════════════════════════════════════════════════════════╝")
        return '\n'.join(lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM videos')
        n_videos = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM flow_chunks')
        n_chunks = cursor.fetchone()[0]
        
        cursor.execute('SELECT dominant_flow, COUNT(*) FROM flow_chunks GROUP BY dominant_flow')
        flow_dist = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'videos': n_videos,
            'chunks': n_chunks,
            'flow_distribution': flow_dist
        }


def demo():
    """Demonstrate dot-flow search."""
    print("\n" + "=" * 70)
    print("  DOT-FLOW AUDIO SEARCH ENGINE")
    print("  Using Novel Temporal Dot-Flow Encoding")
    print("=" * 70)
    
    from audio_fingerprint import generate_test_audio
    import tempfile
    
    search = DotFlowSearch(db_path="dotflow_demo.db")
    
    # Index test audio
    print("\n📥 Indexing test audio with flow encoding...")
    
    for audio_type in ["sine", "chord", "drums", "speech"]:
        samples = generate_test_audio(audio_type, duration=10.0)
        
        # Save to temp WAV
        temp_path = f"{tempfile.gettempdir()}/test_{audio_type}.wav"
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
            temp_path, f"test_{audio_type}",
            f"Test {audio_type.title()} Audio"
        )
        os.remove(temp_path)
    
    stats = search.get_stats()
    print(f"\n📊 Database: {stats['videos']} videos, {stats['chunks']} chunks")
    print(f"   Flow distribution: {stats['flow_distribution']}")
    
    # Search
    print("\n🔍 Searching for chord-like audio using DOT-FLOW...")
    query = generate_test_audio("chord", duration=3.0)
    results = search.search(query, min_similarity=0.3)
    print(search.format_results(results))
    
    # Cleanup
    os.remove("dotflow_demo.db")
    print("\n✨ Demo complete!")


if __name__ == "__main__":
    demo()
