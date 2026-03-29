#!/usr/bin/env python3
"""
Sync video index with Discourse to update import status.

Fetches all topics from the target category and extracts YouTube video IDs
from post content, then updates the local index to mark those as imported.

Usage:
    python sync_discourse_status.py --config config.json --index video_index.json
    python sync_discourse_status.py --config config.json --index video_index.json --dry-run
"""

import argparse
import json
import re
import sys
import time

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip3 install requests")
    sys.exit(1)


from config_utils import load_config


def load_index(index_path: str) -> dict:
    with open(index_path) as f:
        return json.load(f)


def save_index(index: dict, index_path: str):
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)


def extract_youtube_ids(text: str) -> list:
    """Extract YouTube video IDs from text content."""
    patterns = [
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    ]

    ids = set()
    for pattern in patterns:
        matches = re.findall(pattern, text)
        ids.update(matches)

    return list(ids)


def fetch_category_topics(config: dict) -> list:
    """Fetch all topics from the target category."""
    discourse = config["discourse"]
    base_url = discourse["base_url"]
    category_id = discourse["category_id"]

    headers = {
        "Api-Key": discourse["api_key"],
        "Api-Username": discourse["api_username"]
    }

    all_topics = []
    page = 0

    print(f"Fetching topics from category {category_id}...")

    while True:
        url = f"{base_url}/c/{category_id}.json?page={page}"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print(f"Error fetching page {page}: {response.status_code}")
            break

        data = response.json()
        topics = data.get("topic_list", {}).get("topics", [])

        if not topics:
            break

        all_topics.extend(topics)
        print(f"  Page {page}: {len(topics)} topics (total: {len(all_topics)})")

        page += 1
        time.sleep(0.3)  # Rate limiting

    return all_topics


def fetch_topic_content(config: dict, topic_id: int) -> str:
    """Fetch the first post content of a topic."""
    discourse = config["discourse"]
    base_url = discourse["base_url"]

    headers = {
        "Api-Key": discourse["api_key"],
        "Api-Username": discourse["api_username"]
    }

    url = f"{base_url}/t/{topic_id}.json"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return ""

    data = response.json()
    posts = data.get("post_stream", {}).get("posts", [])

    if posts:
        return posts[0].get("cooked", "") + " " + posts[0].get("raw", "")

    return ""


def main():
    parser = argparse.ArgumentParser(description="Sync video index with Discourse")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--index", required=True, help="Path to video_index.json")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without saving")
    parser.add_argument("--deep", action="store_true",
                       help="Fetch each topic's content (slower but more accurate)")
    args = parser.parse_args()

    config = load_config(args.config)
    index = load_index(args.index)

    # Build lookup of video_id -> video
    video_lookup = {v["video_id"]: v for v in index["videos"]}

    # Fetch topics from Discourse
    topics = fetch_category_topics(config)
    print(f"\nFound {len(topics)} topics in category")

    # Extract video IDs from topics
    imported_ids = set()
    topic_video_map = {}  # video_id -> topic_id

    print("\nExtracting YouTube video IDs...")

    for i, topic in enumerate(topics):
        topic_id = topic["id"]
        title = topic.get("title", "")
        slug = topic.get("slug", "")

        # Try to extract from title and slug first
        ids_found = extract_youtube_ids(title + " " + slug)

        # If --deep flag, also fetch the post content
        if args.deep and not ids_found:
            content = fetch_topic_content(config, topic_id)
            ids_found = extract_youtube_ids(content)
            time.sleep(0.2)  # Rate limiting

        # Also check if title matches a video title in our index
        if not ids_found:
            for vid, video in video_lookup.items():
                if video["title"].lower() == title.lower():
                    ids_found = [vid]
                    break

        for vid in ids_found:
            imported_ids.add(vid)
            topic_video_map[vid] = topic_id

        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(topics)} topics...")

    print(f"\nFound {len(imported_ids)} videos already in Discourse")

    # Update index
    changes = 0
    for video in index["videos"]:
        vid = video["video_id"]

        if vid in imported_ids and video["status"] != "imported":
            if args.dry_run:
                print(f"  Would mark as imported: {video['title'][:60]}...")
            else:
                video["status"] = "imported"
                video["discourse_topic_id"] = topic_video_map.get(vid)
            changes += 1

    # Summary
    imported_count = sum(1 for v in index["videos"] if v["status"] == "imported")
    pending_count = len(index["videos"]) - imported_count

    print(f"\n=== Summary ===")
    print(f"Total videos: {len(index['videos'])}")
    print(f"Imported: {imported_count}")
    print(f"Pending: {pending_count}")
    print(f"Changes: {changes}")

    if args.dry_run:
        print("\n(Dry run - no changes saved)")
    elif changes > 0:
        save_index(index, args.index)
        print(f"\nIndex updated: {args.index}")
    else:
        print("\nNo changes needed")


if __name__ == "__main__":
    main()
