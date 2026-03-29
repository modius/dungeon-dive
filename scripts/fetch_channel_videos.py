#!/usr/bin/env python3
"""
Fetch all videos from a YouTube channel and update the local index.

Usage:
    python fetch_channel_videos.py --config config.json --index video_index.json
    python fetch_channel_videos.py --config config.json --index video_index.json --full-refresh
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests --break-system-packages")
    sys.exit(1)


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
    with open(config_path) as f:
        return json.load(f)


def load_index(index_path: str) -> dict:
    """Load existing index or create new one."""
    path = Path(index_path)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"channel_id": None, "last_fetched": None, "videos": []}


def save_index(index: dict, index_path: str):
    """Save index to JSON file."""
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)


def get_uploads_playlist_id(api_key: str, channel_id: str) -> str:
    """Get the uploads playlist ID for a channel."""
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "key": api_key,
        "id": channel_id,
        "part": "contentDetails"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if not data.get("items"):
        raise ValueError(f"Channel not found: {channel_id}")

    return data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def fetch_playlist_videos(api_key: str, playlist_id: str, existing_ids: set) -> list:
    """Fetch all videos from a playlist."""
    videos = []
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    page_token = None

    while True:
        params = {
            "key": api_key,
            "playlistId": playlist_id,
            "part": "snippet,contentDetails",
            "maxResults": 50
        }
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        for item in data.get("items", []):
            video_id = item["contentDetails"]["videoId"]

            # Skip if already in index
            if video_id in existing_ids:
                continue

            snippet = item["snippet"]
            videos.append({
                "video_id": video_id,
                "title": snippet["title"],
                "description": snippet.get("description", "")[:500],  # Truncate
                "published_at": snippet["publishedAt"],
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "status": "pending",
                "discourse_topic_id": None,
                "imported_at": None
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return videos


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube channel videos")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--index", required=True, help="Path to video_index.json")
    parser.add_argument("--full-refresh", action="store_true", help="Re-fetch all videos")
    args = parser.parse_args()

    config = load_config(args.config)
    index = load_index(args.index)

    api_key = config["youtube"]["api_key"]
    channel_id = config["youtube"]["channel_id"]

    # Get existing video IDs
    existing_ids = set()
    if not args.full_refresh:
        existing_ids = {v["video_id"] for v in index.get("videos", [])}

    print(f"Fetching videos from channel: {channel_id}")
    print(f"Existing videos in index: {len(existing_ids)}")

    # Get uploads playlist
    uploads_playlist = get_uploads_playlist_id(api_key, channel_id)

    # Fetch new videos
    new_videos = fetch_playlist_videos(api_key, uploads_playlist, existing_ids)

    print(f"New videos found: {len(new_videos)}")

    # Update index
    if args.full_refresh:
        index["videos"] = new_videos
    else:
        index["videos"].extend(new_videos)

    index["channel_id"] = channel_id
    index["last_fetched"] = datetime.now(timezone.utc).isoformat()

    # Sort by published date (newest first)
    index["videos"].sort(key=lambda v: v["published_at"], reverse=True)

    save_index(index, args.index)

    print(f"Index updated: {args.index}")
    print(f"Total videos: {len(index['videos'])}")

    # Summary by status
    statuses = {}
    for v in index["videos"]:
        status = v.get("status", "pending")
        statuses[status] = statuses.get(status, 0) + 1

    print("\nStatus breakdown:")
    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count}")


if __name__ == "__main__":
    main()
