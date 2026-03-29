#!/usr/bin/env python3
"""
Create a Discourse topic for a YouTube video.

Usage:
    python post_to_discourse.py --config config.json --title "Video Title" --body "Post content" --video-date "2024-06-15T14:00:00Z"

The script will:
1. Create the topic in the configured category
2. Backdate the topic to the video's publish date (if admin API key)
"""

import argparse
import json
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests --break-system-packages")
    sys.exit(1)


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
    with open(config_path) as f:
        return json.load(f)


def create_topic(config: dict, title: str, body: str) -> dict:
    """
    Create a new topic in Discourse.

    Returns:
        API response with topic_id and post_id
    """
    discourse = config["discourse"]
    url = f"{discourse['base_url']}/posts.json"

    headers = {
        "Api-Key": discourse["api_key"],
        "Api-Username": discourse["api_username"],
        "Content-Type": "application/json"
    }

    payload = {
        "title": title,
        "raw": body,
        "category": discourse["category_id"]
    }

    # Post as specific user if configured (requires admin key)
    if discourse.get("post_as_username"):
        headers["Api-Username"] = discourse["post_as_username"]

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error creating topic: {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        return None


def backdate_topic(config: dict, topic_id: int, timestamp: str) -> bool:
    """
    Change the topic's created_at timestamp.

    Args:
        config: Configuration dict
        topic_id: Discourse topic ID
        timestamp: ISO format timestamp (e.g., "2024-06-15T14:00:00Z")

    Returns:
        True if successful
    """
    discourse = config["discourse"]
    url = f"{discourse['base_url']}/t/{topic_id}/change-timestamp"

    headers = {
        "Api-Key": discourse["api_key"],
        "Api-Username": discourse["api_username"],
        "Content-Type": "application/json"
    }

    # Convert ISO timestamp to Unix timestamp
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    unix_timestamp = int(dt.timestamp())

    payload = {
        "timestamp": unix_timestamp
    }

    response = requests.put(url, headers=headers, json=payload)

    if response.status_code == 200:
        return True
    else:
        print(f"\n{'='*60}", file=sys.stderr)
        print("WARNING: Failed to backdate topic", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        print(f"HTTP Status: {response.status_code}", file=sys.stderr)

        if response.status_code == 403:
            print("\nThe API key lacks admin privileges.", file=sys.stderr)
            print("To fix this:", file=sys.stderr)
            print("  1. Go to Admin > Users > [your bot account]", file=sys.stderr)
            print("  2. Click 'Grant Admin'", file=sys.stderr)
            print("  3. Regenerate the API key if needed", file=sys.stderr)
        elif response.status_code == 404:
            print("\nThe change-timestamp endpoint was not found.", file=sys.stderr)
            print("This may indicate an older Discourse version.", file=sys.stderr)
        else:
            print(f"\nResponse: {response.text}", file=sys.stderr)

        print(f"\nThe topic was created but has today's date instead of {timestamp}.", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Create Discourse topic for YouTube video")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--title", required=True, help="Topic title")
    parser.add_argument("--body", required=True, help="Topic body content (or @filename to read from file)")
    parser.add_argument("--video-date", help="Video publish date (ISO format) to backdate topic")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be posted without posting")
    args = parser.parse_args()

    config = load_config(args.config)

    # Handle body from file
    body = args.body
    if body.startswith("@"):
        with open(body[1:]) as f:
            body = f.read()

    if args.dry_run:
        print("=== DRY RUN ===")
        print(f"Title: {args.title}")
        print(f"Category: {config['discourse']['category_id']}")
        print(f"Post as: {config['discourse'].get('post_as_username', config['discourse']['api_username'])}")
        print(f"Backdate to: {args.video_date}")
        print(f"\nBody:\n{body}")
        return

    print(f"Creating topic: {args.title}")

    result = create_topic(config, args.title, body)

    if result:
        topic_id = result.get("topic_id")
        topic_slug = result.get("topic_slug", "")
        print(f"Topic created: {config['discourse']['base_url']}/t/{topic_slug}/{topic_id}")

        if args.video_date:
            print(f"Backdating to: {args.video_date}")
            if backdate_topic(config, topic_id, args.video_date):
                print("Topic backdated successfully")

        # Output JSON for scripting
        output = {
            "success": True,
            "topic_id": topic_id,
            "topic_slug": topic_slug,
            "url": f"{config['discourse']['base_url']}/t/{topic_slug}/{topic_id}"
        }
        print(f"\n{json.dumps(output)}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
