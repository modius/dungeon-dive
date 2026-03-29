#!/usr/bin/env python3
"""
Batch fetch transcripts for multiple YouTube videos.

Usage:
    python batch_fetch_transcripts.py VIDEO_ID1 VIDEO_ID2 VIDEO_ID3 ...
    python batch_fetch_transcripts.py --from-index pending --limit 10
    python batch_fetch_transcripts.py --from-index pending --year 2025 --limit 5

Creates a pending_imports/ folder with transcript files ready for processing.
"""

import argparse
import json
import os
import sys
import time

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("Error: youtube-transcript-api required.")
    print("Install with: pip3 install youtube-transcript-api")
    sys.exit(1)


def fetch_transcript(video_id: str) -> str:
    """Fetch transcript for a single video."""
    try:
        ytt_api = YouTubeTranscriptApi()
        entries = ytt_api.fetch(video_id)
        texts = []
        for entry in entries:
            text = entry.text if hasattr(entry, 'text') else entry.get('text', '')
            texts.append(text)
        return " ".join(texts)
    except Exception as e:
        return None


def load_video_index(index_path: str) -> dict:
    """Load video index file."""
    with open(index_path) as f:
        return json.load(f)


def get_videos_from_index(index_path: str, status: str = 'pending',
                          year: str = None, limit: int = None) -> list:
    """Get video IDs from index file with optional filters."""
    data = load_video_index(index_path)
    videos = []

    for v in data['videos']:
        if v['status'] != status:
            continue
        if year and not v['published_at'].startswith(year):
            continue
        videos.append({
            'video_id': v['video_id'],
            'title': v['title'],
            'published_at': v['published_at']
        })
        if limit and len(videos) >= limit:
            break

    return videos


def main():
    parser = argparse.ArgumentParser(description="Batch fetch YouTube transcripts")
    parser.add_argument("video_ids", nargs="*", help="Video IDs to fetch")
    parser.add_argument("--from-index", metavar="STATUS",
                        help="Fetch videos with this status from video_index.json (e.g., 'pending')")
    parser.add_argument("--index", default="video_index.json",
                        help="Path to video_index.json")
    parser.add_argument("--year", help="Filter by year (e.g., '2025')")
    parser.add_argument("--limit", type=int, help="Maximum number of videos to fetch")
    parser.add_argument("--output-dir", default="pending_imports",
                        help="Output directory for transcripts")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Delay between fetches in seconds (default: 3.0)")
    args = parser.parse_args()

    # Resolve paths - working directory is assumed to be the main project folder
    # (where config.json and video_index.json live)
    cwd = os.getcwd()

    if args.index.startswith("../"):
        index_path = os.path.join(cwd, args.index[3:])
    elif not os.path.isabs(args.index):
        index_path = os.path.join(cwd, args.index)
    else:
        index_path = args.index

    if args.output_dir.startswith("../"):
        output_dir = os.path.join(cwd, args.output_dir[3:])
    elif not os.path.isabs(args.output_dir):
        output_dir = os.path.join(cwd, args.output_dir)
    else:
        output_dir = args.output_dir

    # Get video list
    videos = []

    if args.from_index:
        if not os.path.exists(index_path):
            print(f"Error: Index file not found: {index_path}")
            sys.exit(1)
        videos = get_videos_from_index(index_path, args.from_index, args.year, args.limit)
        print(f"Found {len(videos)} {args.from_index} videos" +
              (f" from {args.year}" if args.year else ""))
    elif args.video_ids:
        # Load index for metadata if available
        if os.path.exists(index_path):
            data = load_video_index(index_path)
            video_map = {v['video_id']: v for v in data['videos']}
            for vid in args.video_ids:
                if vid in video_map:
                    v = video_map[vid]
                    videos.append({
                        'video_id': vid,
                        'title': v['title'],
                        'published_at': v['published_at']
                    })
                else:
                    videos.append({
                        'video_id': vid,
                        'title': 'Unknown',
                        'published_at': 'Unknown'
                    })
        else:
            videos = [{'video_id': vid, 'title': 'Unknown', 'published_at': 'Unknown'}
                      for vid in args.video_ids]
    else:
        parser.print_help()
        sys.exit(1)

    if not videos:
        print("No videos to fetch.")
        sys.exit(0)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Create manifest file
    manifest = {
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'videos': []
    }

    # Fetch transcripts
    success = 0
    failed = 0

    for i, video in enumerate(videos, 1):
        vid = video['video_id']
        title = video['title']
        published = video['published_at']

        print(f"[{i}/{len(videos)}] Fetching: {title[:50]}...")

        transcript = fetch_transcript(vid)

        if transcript:
            # Save transcript
            transcript_file = os.path.join(output_dir, f"{vid}_transcript.txt")
            with open(transcript_file, 'w') as f:
                f.write(transcript)

            # Save metadata
            meta_file = os.path.join(output_dir, f"{vid}_meta.json")
            meta = {
                'video_id': vid,
                'title': title,
                'published_at': published,
                'youtube_url': f"https://www.youtube.com/watch?v={vid}"
            }
            with open(meta_file, 'w') as f:
                json.dump(meta, f, indent=2)

            manifest['videos'].append(meta)
            success += 1
            print(f"    ✓ Saved transcript ({len(transcript)} chars)")
        else:
            failed += 1
            print(f"    ✗ Failed to fetch transcript")

        # Delay between fetches to avoid rate limiting
        if i < len(videos):
            time.sleep(args.delay)

    # Save manifest
    manifest_file = os.path.join(output_dir, "manifest.json")
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n{'='*50}")
    print(f"Fetched {success} transcripts, {failed} failed")
    print(f"Output directory: {output_dir}")
    print(f"\nNext step: Share the transcripts with Claude to generate summaries")
    print(f"Or run: cat {output_dir}/*_transcript.txt")


if __name__ == "__main__":
    main()
