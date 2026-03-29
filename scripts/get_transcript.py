#!/usr/bin/env python3
"""
Fetch transcript/captions for a YouTube video.

Usage:
    python get_transcript.py VIDEO_ID
    python get_transcript.py VIDEO_ID --output transcript.txt
    python get_transcript.py VIDEO_ID --with-timestamps

Note: Uses youtube-transcript-api (no API key required).
Install: pip install youtube-transcript-api --break-system-packages
"""

import argparse
import sys

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("Error: youtube-transcript-api required.")
    print("Install with: pip install youtube-transcript-api")
    sys.exit(1)


def get_transcript(video_id: str, with_timestamps: bool = False) -> str:
    """
    Fetch transcript for a video.

    Args:
        video_id: YouTube video ID
        with_timestamps: Include timestamps in output

    Returns:
        Transcript text
    """
    try:
        # New API in youtube-transcript-api 1.x
        ytt_api = YouTubeTranscriptApi()
        entries = ytt_api.fetch(video_id)

        if with_timestamps:
            lines = []
            for entry in entries:
                start = entry.start if hasattr(entry, 'start') else entry.get('start', 0)
                text = entry.text if hasattr(entry, 'text') else entry.get('text', '')
                minutes = int(start // 60)
                seconds = int(start % 60)
                lines.append(f"[{minutes:02d}:{seconds:02d}] {text}")
            return "\n".join(lines)
        else:
            texts = []
            for entry in entries:
                text = entry.text if hasattr(entry, 'text') else entry.get('text', '')
                texts.append(text)
            return " ".join(texts)

    except Exception as e:
        print(f"Error fetching transcript: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube video transcript")
    parser.add_argument("video_id", help="YouTube video ID")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--with-timestamps", "-t", action="store_true",
                       help="Include timestamps")
    args = parser.parse_args()

    transcript = get_transcript(args.video_id, args.with_timestamps)

    if transcript is None:
        sys.exit(1)

    if args.output:
        with open(args.output, "w") as f:
            f.write(transcript)
        print(f"Transcript saved to: {args.output}")
    else:
        print(transcript)


if __name__ == "__main__":
    main()
