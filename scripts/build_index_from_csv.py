#!/usr/bin/env python3
"""
Build video_index.json from existing CSV export and YouTube API.

Usage:
    python build_index_from_csv.py --config config.json --csv "exported.csv" --output video_index.json

The script will:
1. Parse the CSV to get video IDs and import status
2. Fetch additional metadata (publish dates) from YouTube API
3. Create video_index.json with correct statuses
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip3 install requests")
    sys.exit(1)


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
    with open(config_path) as f:
        return json.load(f)


def parse_csv(csv_path: str) -> dict:
    """
    Parse the CSV file and return a dict of video_id -> status.

    Status mapping:
    - "Summary Complete" -> "imported"
    - Empty/blank -> "pending"
    """
    videos = {}

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            video_id = row.get('Video ID', '').strip()
            status_raw = row.get('Status', '').strip()
            title = row.get('Title', '').strip()

            if not video_id:
                continue

            # Map status
            if status_raw == "Summary Complete":
                status = "imported"
            elif status_raw == "":
                status = "pending"
            else:
                # Unknown status, treat as pending
                status = "pending"

            videos[video_id] = {
                "title_from_csv": title,
                "status": status
            }

    return videos


def fetch_video_details_batch(api_key: str, video_ids: list) -> dict:
    """
    Fetch video details from YouTube API (batch of up to 50).

    Returns dict of video_id -> details
    """
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "key": api_key,
        "id": ",".join(video_ids),
        "part": "snippet,contentDetails"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    results = {}
    for item in data.get("items", []):
        video_id = item["id"]
        snippet = item["snippet"]

        results[video_id] = {
            "title": snippet.get("title", ""),
            "description": snippet.get("description", "")[:500],
            "published_at": snippet.get("publishedAt", ""),
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "channel_title": snippet.get("channelTitle", "")
        }

    return results


def build_index(config: dict, csv_videos: dict, output_path: str):
    """Build the video index by combining CSV data with YouTube metadata."""
    api_key = config["youtube"]["api_key"]
    channel_id = config["youtube"]["channel_id"]

    video_ids = list(csv_videos.keys())
    total = len(video_ids)

    print(f"Found {total} videos in CSV")

    # Count statuses
    imported_count = sum(1 for v in csv_videos.values() if v["status"] == "imported")
    pending_count = total - imported_count
    print(f"  Imported: {imported_count}")
    print(f"  Pending: {pending_count}")

    # Fetch metadata from YouTube in batches of 50
    print(f"\nFetching metadata from YouTube API...")
    all_metadata = {}

    for i in range(0, total, 50):
        batch = video_ids[i:i+50]
        print(f"  Fetching batch {i//50 + 1} ({len(batch)} videos)...")

        try:
            metadata = fetch_video_details_batch(api_key, batch)
            all_metadata.update(metadata)
        except Exception as e:
            print(f"  Warning: Failed to fetch batch: {e}")

        # Rate limiting
        if i + 50 < total:
            time.sleep(0.5)

    print(f"  Retrieved metadata for {len(all_metadata)} videos")

    # Build the index
    videos = []
    missing_metadata = 0

    for video_id, csv_data in csv_videos.items():
        yt_data = all_metadata.get(video_id, {})

        if not yt_data:
            missing_metadata += 1
            # Use CSV title as fallback
            yt_data = {
                "title": csv_data["title_from_csv"],
                "description": "",
                "published_at": "",
                "thumbnail_url": ""
            }

        video = {
            "video_id": video_id,
            "title": yt_data.get("title", csv_data["title_from_csv"]),
            "description": yt_data.get("description", ""),
            "published_at": yt_data.get("published_at", ""),
            "thumbnail_url": yt_data.get("thumbnail_url", ""),
            "status": csv_data["status"],
            "discourse_topic_id": None,
            "imported_at": None
        }

        videos.append(video)

    if missing_metadata:
        print(f"  Warning: {missing_metadata} videos missing YouTube metadata (may be private/deleted)")

    # Sort by publish date (newest first), with empty dates at end
    videos.sort(key=lambda v: v["published_at"] or "0000", reverse=True)

    # Build final index
    index = {
        "channel_id": channel_id,
        "last_fetched": datetime.now(timezone.utc).isoformat(),
        "videos": videos
    }

    # Save
    with open(output_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"\nIndex saved to: {output_path}")
    print(f"Total videos: {len(videos)}")


def main():
    parser = argparse.ArgumentParser(description="Build video index from CSV")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--csv", required=True, help="Path to CSV export")
    parser.add_argument("--output", default="video_index.json", help="Output path")
    args = parser.parse_args()

    config = load_config(args.config)
    csv_videos = parse_csv(args.csv)
    build_index(config, csv_videos, args.output)


if __name__ == "__main__":
    main()
