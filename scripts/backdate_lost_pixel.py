#!/usr/bin/env python3
"""Backdate the Lost Pixel batch posts to their original YouTube publish dates."""

import json
import requests
import argparse
from datetime import datetime

# Lost Pixel batch: topic_id -> original publish date
LOST_PIXEL_POSTS = {
    1240: "2025-03-19T16:00:14Z",  # Play Through and Legacy Variant
    1241: "2022-09-01T07:00:10Z",  # Virtues of Randomness
    1242: "2022-08-19T07:00:21Z",  # Episode 23 Pete Jank
    1243: "2021-04-12T13:39:48Z",  # Expansions review
    1244: "2021-03-30T00:05:46Z",  # Take a Look (initial)
    1245: "2023-04-30T17:00:21Z",  # Masterclass
}

def backdate_topic(base_url, api_key, api_username, topic_id, timestamp):
    """Change a topic's timestamp using Discourse API."""
    url = f"{base_url}/t/{topic_id}/change-timestamp"
    headers = {
        "Api-Key": api_key,
        "Api-Username": api_username,
        "Content-Type": "application/json"
    }

    # Convert ISO timestamp to Unix timestamp
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    unix_ts = int(dt.timestamp())

    response = requests.put(url, headers=headers, json={"timestamp": unix_ts})
    return response.status_code == 200, response

def main():
    parser = argparse.ArgumentParser(description='Backdate Lost Pixel posts')
    parser.add_argument('--config', required=True, help='Path to config.json')
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    discourse = config['discourse']
    base_url = discourse['base_url'].rstrip('/')
    api_key = discourse['api_key']
    api_username = discourse['api_username']

    print(f"Backdating {len(LOST_PIXEL_POSTS)} Lost Pixel posts...")
    print("=" * 60)

    success = 0
    failed = 0

    for topic_id, timestamp in LOST_PIXEL_POSTS.items():
        date_str = timestamp[:10]
        ok, resp = backdate_topic(base_url, api_key, api_username, topic_id, timestamp)
        if ok:
            print(f"  ✓ Topic {topic_id} → {date_str}")
            success += 1
        else:
            print(f"  ✗ Topic {topic_id} failed: {resp.status_code}")
            failed += 1

    print("=" * 60)
    print(f"Complete: {success} success, {failed} failed")

if __name__ == "__main__":
    main()
