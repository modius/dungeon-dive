#!/usr/bin/env python3
"""Backdate Valpiedra post to original YouTube publish date."""

import json
import argparse
import requests
from datetime import datetime

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    discourse = config['discourse']
    base_url = discourse['base_url'].rstrip('/')
    api_key = discourse['api_key']
    api_username = discourse['api_username']

    headers = {
        'Api-Key': api_key,
        'Api-Username': api_username,
    }

    # Get the topic ID from the post results
    try:
        with open('ready_to_post/post_results.json') as f:
            results = json.load(f)
        topic_id = results.get('svTgRSTyypU', {}).get('topic_id')
    except:
        topic_id = None

    if not topic_id:
        print("Could not find topic ID in post_results.json")
        print("Please enter the topic ID manually:")
        topic_id = int(input().strip())

    # Valpiedra publish date
    publish_date = "2026-02-04"

    print(f"Backdating Valpiedra post...")
    print("=" * 60)

    timestamp = datetime.fromisoformat(publish_date).strftime('%Y-%m-%d %H:%M:%S')
    url = f"{base_url}/t/{topic_id}/change-timestamp"

    response = requests.put(url, headers=headers, data={'timestamp': timestamp})

    if response.status_code == 200:
        print(f"  ✓ Topic {topic_id} → {publish_date}")
    else:
        print(f"  ✗ Topic {topic_id} failed: {response.status_code}")
        print(f"    {response.text[:200]}")

    print("=" * 60)
    print("Complete")

if __name__ == '__main__':
    main()
