#!/usr/bin/env python3
"""
Live Audio Search System
========================

Index real YouTube videos and search across them using
the novel Dot-Flow algorithm.

Usage:
    python live_audio_search.py build    # Build index from video list
    python live_audio_search.py search URL  # Search with YouTube audio
    python live_audio_search.py demo     # Full demonstration

Author: Ryan Barrett
"""

import argparse
import os
import sys
from typing import List

from dotflow_search import DotFlowSearch


# Curated list of diverse YouTube videos for indexing
SAMPLE_VIDEOS = [
    # Music - different genres
    ("dQw4w9WgXcQ", "Rick Astley - Never Gonna Give You Up"),
    ("9bZkp7q19f0", "PSY - Gangnam Style"),
    ("kJQP7kiw5Fk", "Luis Fonsi - Despacito"),
    
    # Classical / Instrumental
    ("rDiWlffqpak", "Beethoven - Für Elise"),
    ("4Tr0otuiQuU", "Bach - Cello Suite No. 1"),
    
    # Speech / Podcasts
    ("8S0FDjFBj8o", "TED Talk - How to speak"),
    
    # Sound Effects / Nature
    ("Qm846KdZN_c", "Rain Sounds"),
    ("V1bFr2SWP1I", "Ocean Waves"),
]


class LiveAudioSearchSystem:
    """
    Complete system for indexing and searching YouTube audio.
    """
    
    def __init__(self, db_path: str = "live_audio.db"):
        self.search = DotFlowSearch(db_path=db_path)
    
    def build_index(self, videos: List[tuple] = None, 
                    max_duration: int = 60) -> int:
        """
        Build index from a list of YouTube videos.
        
        Args:
            videos: List of (video_id, title) tuples
            max_duration: Max seconds to index per video
            
        Returns:
            Total chunks indexed
        """
        if videos is None:
            videos = SAMPLE_VIDEOS
        
        print("\n" + "=" * 60)
        print("  📥 BUILDING LIVE AUDIO INDEX")
        print("=" * 60)
        
        total_chunks = 0
        successful = 0
        
        for video_id, title in videos:
            url = f"https://youtube.com/watch?v={video_id}"
            print(f"\n📹 Indexing: {title}")
            print(f"   URL: {url}")
            
            try:
                # Index only first segment to save time/bandwidth
                from youtube_fingerprint import YouTubeFingerprint
                import wave
                import struct
                import tempfile
                
                yt = YouTubeFingerprint(keep_audio=True)
                
                # Download
                audio_path = yt.download_audio(url)
                
                # Trim to max_duration
                trimmed_path = f"{tempfile.gettempdir()}/trimmed_{video_id}.wav"
                
                with wave.open(audio_path, 'rb') as src:
                    params = src.getparams()
                    max_frames = min(src.getnframes(), 
                                    max_duration * src.getframerate())
                    data = src.readframes(max_frames)
                
                with wave.open(trimmed_path, 'wb') as dst:
                    dst.setparams(params)
                    dst.writeframes(data)
                
                # Index
                chunks = self.search.index_audio_file(
                    trimmed_path, video_id, title, url
                )
                total_chunks += chunks
                successful += 1
                
                # Cleanup
                os.remove(audio_path)
                os.remove(trimmed_path)
                
                print(f"   ✅ Indexed {chunks} chunks")
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
        
        print(f"\n{'=' * 60}")
        print(f"  📊 INDEX COMPLETE")
        print(f"     Videos: {successful}/{len(videos)}")
        print(f"     Chunks: {total_chunks}")
        print(f"{'=' * 60}")
        
        return total_chunks
    
    def search_youtube(self, url: str, segment_start: int = 0,
                       segment_duration: int = 10) -> None:
        """Search using audio from a YouTube video."""
        from youtube_fingerprint import YouTubeFingerprint
        import wave
        import struct
        
        print(f"\n🔍 Searching with: {url}")
        print(f"   Segment: {segment_start}s to {segment_start + segment_duration}s")
        
        yt = YouTubeFingerprint(keep_audio=True)
        audio_path = yt.download_audio(url)
        
        try:
            with wave.open(audio_path, 'rb') as wav:
                sample_rate = wav.getframerate()
                n_channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                
                # Seek to segment
                start_frame = segment_start * sample_rate
                wav.setpos(min(start_frame, wav.getnframes() - 1))
                
                # Read segment
                n_frames = min(segment_duration * sample_rate,
                              wav.getnframes() - start_frame)
                raw_data = wav.readframes(n_frames)
            
            # Convert to samples
            samples = self.search._bytes_to_samples(
                raw_data, sample_width, n_channels
            )
            
            # Search
            results = self.search.search(samples, sample_rate, 
                                         top_k=5, min_similarity=0.3)
            
            print(self.search.format_results(results))
            
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
    
    def interactive_demo(self):
        """Run interactive demonstration."""
        print("\n" + "=" * 60)
        print("  🎵 LIVE AUDIO SEARCH DEMONSTRATION")
        print("  Using Novel Dot-Flow Algorithm")
        print("=" * 60)
        
        # Check if index exists
        stats = self.search.get_stats()
        
        if stats['videos'] == 0:
            print("\n⚠️  No videos indexed. Building index first...")
            # Use fewer videos for demo
            demo_videos = SAMPLE_VIDEOS[:3]
            self.build_index(demo_videos, max_duration=30)
        
        stats = self.search.get_stats()
        print(f"\n📊 Index Statistics:")
        print(f"   Videos: {stats['videos']}")
        print(f"   Chunks: {stats['chunks']}")
        print(f"   Flow Distribution: {stats['flow_distribution']}")
        
        # Search demo
        print("\n" + "-" * 60)
        print("  🔍 SEARCH DEMO: Finding similar audio")
        print("-" * 60)
        
        # Search with first video (should find itself)
        if stats['videos'] > 0:
            test_url = f"https://youtube.com/watch?v={SAMPLE_VIDEOS[0][0]}"
            print(f"\n   Query: {SAMPLE_VIDEOS[0][1]}")
            self.search_youtube(test_url, segment_start=5, segment_duration=5)
        
        print("\n✨ Demo complete!")


def main():
    parser = argparse.ArgumentParser(
        description='Live Audio Search using Dot-Flow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s build              # Build index from sample videos
  %(prog)s search URL         # Search with YouTube audio
  %(prog)s demo               # Run full demonstration
  %(prog)s stats              # Show index statistics
        """
    )
    
    parser.add_argument('command', 
                        choices=['build', 'search', 'demo', 'stats'],
                        help='Command to run')
    parser.add_argument('url', nargs='?', help='YouTube URL for search')
    parser.add_argument('--db', default='live_audio.db',
                        help='Database path')
    parser.add_argument('--start', type=int, default=0,
                        help='Start time for search segment')
    parser.add_argument('--duration', type=int, default=10,
                        help='Duration for search segment')
    parser.add_argument('--max-index-duration', type=int, default=60,
                        help='Max seconds to index per video')
    
    args = parser.parse_args()
    
    system = LiveAudioSearchSystem(db_path=args.db)
    
    if args.command == 'build':
        system.build_index(max_duration=args.max_index_duration)
        
    elif args.command == 'search':
        if not args.url:
            print("❌ URL required for search")
            sys.exit(1)
        system.search_youtube(args.url, args.start, args.duration)
        
    elif args.command == 'demo':
        system.interactive_demo()
        
    elif args.command == 'stats':
        stats = system.search.get_stats()
        print(f"\n📊 Index Statistics:")
        print(f"   Videos: {stats['videos']}")
        print(f"   Chunks: {stats['chunks']}")
        print(f"   Flow Distribution: {stats['flow_distribution']}")


if __name__ == "__main__":
    main()
