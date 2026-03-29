#!/usr/bin/env python3
"""
Post a reply to an existing Discourse topic.

Usage:
    python3 scripts/post_reply.py --config config.json --topic-id 1170 --body "Reply text"
    python3 scripts/post_reply.py --config config.json --topic-id 1170 --body @keeper-posts/keeper-theme.md
    python3 scripts/post_reply.py --config config.json --topic-id 1170 --body @file.md --dry-run
"""

import argparse
import sys

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip3 install requests")
    sys.exit(1)

from config_utils import load_config


def post_reply(config: dict, topic_id: int, body: str) -> dict:
    """Post a reply to an existing Discourse topic."""
    discourse = config["discourse"]
    url = f"{discourse['base_url']}/posts.json"

    headers = {
        "Api-Key": discourse["api_key"],
        "Api-Username": discourse.get("post_as_username", discourse["api_username"]),
        "Content-Type": "application/json",
    }

    payload = {
        "topic_id": topic_id,
        "raw": body,
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error posting reply: {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Post a reply to a Discourse topic")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--topic-id", type=int, required=True, help="Discourse topic ID to reply to")
    parser.add_argument("--body", required=True, help="Reply body text, or @filename to read from file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    args = parser.parse_args()

    # Load body from file if @filename syntax
    body = args.body
    if body.startswith("@"):
        filepath = body[1:]
        with open(filepath) as f:
            body = f.read()

    config = load_config(args.config)

    if args.dry_run:
        print(f"DRY RUN — would post reply to topic {args.topic_id}")
        print(f"Body preview ({len(body)} chars):")
        print(body[:500])
        if len(body) > 500:
            print(f"... ({len(body) - 500} more chars)")
        return

    result = post_reply(config, args.topic_id, body)
    if result:
        post_id = result.get("id")
        post_num = result.get("post_number")
        topic_slug = result.get("topic_slug", "")
        base_url = config["discourse"]["base_url"]
        print(f"  Posted: {base_url}/t/{topic_slug}/{args.topic_id}/{post_num}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
