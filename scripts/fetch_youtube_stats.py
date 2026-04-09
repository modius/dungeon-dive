#!/usr/bin/env python3
"""
Fetch YouTube engagement stats (views, likes, comments, duration) for all indexed videos.

Usage:
    python fetch_youtube_stats.py --config config.json --index video_index.json
    python fetch_youtube_stats.py --config config.json --index video_index.json --only-missing
    python fetch_youtube_stats.py --config config.json --index video_index.json --max-age-hours 24
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests --break-system-packages")
    sys.exit(1)

from config_utils import load_config


def parse_duration(iso_duration):
    """Parse ISO 8601 duration (PT1H2M3S) into seconds and display string."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration or "")
    if not match:
        return 0, "0:00"

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    total = hours * 3600 + minutes * 60 + seconds

    if hours:
        display = f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        display = f"{minutes}:{seconds:02d}"

    return total, display


def load_stats(output_path: str) -> dict:
    """Load existing stats file or create empty structure."""
    path = Path(output_path)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"last_fetched": None, "stats": {}}


def save_stats(data: dict, output_path: str):
    """Save stats to JSON file."""
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)


def filter_video_ids(all_ids, existing_stats, only_missing, max_age_hours):
    """Filter video IDs based on --only-missing and --max-age-hours flags."""
    if only_missing:
        return [vid for vid in all_ids if vid not in existing_stats]

    if max_age_hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        result = []
        for vid in all_ids:
            if vid not in existing_stats:
                result.append(vid)
                continue
            fetched_at = existing_stats[vid].get("fetched_at", "")
            try:
                ts = datetime.fromisoformat(fetched_at)
                if ts < cutoff:
                    result.append(vid)
            except (ValueError, TypeError):
                result.append(vid)
        return result

    return list(all_ids)


def fetch_stats_batch(api_key, video_ids):
    """Fetch stats for a batch of video IDs (max 50)."""
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "key": api_key,
        "id": ",".join(video_ids),
        "part": "statistics,contentDetails",
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    now = datetime.now(timezone.utc).isoformat()
    results = {}

    for item in data.get("items", []):
        vid = item["id"]
        stats = item.get("statistics", {})
        content = item.get("contentDetails", {})
        duration_secs, duration_display = parse_duration(content.get("duration", ""))

        results[vid] = {
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
            "duration_seconds": duration_secs,
            "duration_display": duration_display,
            "fetched_at": now,
        }

    return results


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube video engagement stats")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--index", required=True, help="Path to video_index.json")
    parser.add_argument("--output", default="youtube_stats.json", help="Output stats file")
    parser.add_argument("--only-missing", action="store_true", help="Only fetch videos not in output")
    parser.add_argument("--max-age-hours", type=float, help="Re-fetch stats older than N hours")
    args = parser.parse_args()

    config = load_config(args.config)
    api_key = config["youtube"]["api_key"]

    # Load video index
    with open(args.index) as f:
        index = json.load(f)
    all_ids = [v["video_id"] for v in index.get("videos", [])]
    print(f"Videos in index: {len(all_ids)}")

    # Load existing stats and filter
    stats_data = load_stats(args.output)
    to_fetch = filter_video_ids(all_ids, stats_data["stats"], args.only_missing, args.max_age_hours)
    print(f"Videos to fetch: {len(to_fetch)}")

    if not to_fetch:
        print("Nothing to fetch.")
        return

    # Batch in groups of 50
    new_count = 0
    updated_count = 0
    batches = [to_fetch[i:i + 50] for i in range(0, len(to_fetch), 50)]

    for i, batch in enumerate(batches, 1):
        print(f"[batch {i}/{len(batches)}] Fetching stats for {len(batch)} videos...")
        results = fetch_stats_batch(api_key, batch)

        for vid, stat in results.items():
            if vid in stats_data["stats"]:
                updated_count += 1
            else:
                new_count += 1
            stats_data["stats"][vid] = stat

    stats_data["last_fetched"] = datetime.now(timezone.utc).isoformat()
    save_stats(stats_data, args.output)

    total = new_count + updated_count
    print(f"\nFetched stats for {total} videos ({new_count} new, {updated_count} updated)")
    print(f"Stats file: {args.output} ({len(stats_data['stats'])} total entries)")


if __name__ == "__main__":
    main()
