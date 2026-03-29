#!/usr/bin/env python3
"""
Batch post prepared topics to Discourse.

Usage:
    python batch_post.py --config config.json --input-dir ready_to_post
    python batch_post.py --config config.json --input-dir ready_to_post --dry-run
    python batch_post.py --config config.json --no-archive  # Skip auto-archive

Expects files in input-dir:
    VIDEO_ID_post.json - Contains: title, body, video_date

Or a manifest.json with list of posts to make.

After successful posting, files are automatically archived to archive/posts/
and archive/transcripts/ (use --no-archive to disable).
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: requests library required.")
    print("Install with: pip3 install requests")
    sys.exit(1)


from config_utils import load_config


def create_topic(config: dict, title: str, body: str) -> dict:
    """Create a new topic in Discourse."""
    discourse = config["discourse"]
    url = f"{discourse['base_url']}/posts.json"

    headers = {
        "Api-Key": discourse["api_key"],
        "Api-Username": discourse.get("post_as_username", discourse["api_username"]),
        "Content-Type": "application/json"
    }

    payload = {
        "title": title,
        "raw": body,
        "category": discourse["category_id"]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"  Error: {response.status_code} - {response.text[:200]}")
        return None


def backdate_topic(config: dict, topic_id: int, timestamp: str) -> bool:
    """Change the topic's created_at timestamp."""
    discourse = config["discourse"]
    url = f"{discourse['base_url']}/t/{topic_id}/change-timestamp"

    headers = {
        "Api-Key": discourse["api_key"],
        "Api-Username": discourse["api_username"],
        "Content-Type": "application/json"
    }

    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    unix_timestamp = int(dt.timestamp())

    response = requests.put(url, headers=headers, json={"timestamp": unix_timestamp})
    return response.status_code == 200


def update_video_index(index_path: str, video_id: str, topic_id: int):
    """Mark a video as imported in the index."""
    if not os.path.exists(index_path):
        return

    with open(index_path) as f:
        data = json.load(f)

    for v in data['videos']:
        if v['video_id'] == video_id:
            v['status'] = 'imported'
            v['discourse_topic_id'] = topic_id
            v['imported_at'] = datetime.utcnow().isoformat() + 'Z'
            break

    with open(index_path, 'w') as f:
        json.dump(data, f, indent=2)


def archive_files(input_dir: str, transcript_dir: str, results: list):
    """Archive posted files and their transcripts."""
    # Ensure archive directories exist
    archive_posts = "archive/posts"
    archive_transcripts = "archive/transcripts"
    os.makedirs(archive_posts, exist_ok=True)
    os.makedirs(archive_transcripts, exist_ok=True)

    archived_posts = 0
    archived_transcripts = 0

    # Get successfully posted video IDs
    success_ids = [r['video_id'] for r in results if r.get('status') == 'success']

    # Archive post files
    for video_id in success_ids:
        post_file = os.path.join(input_dir, f"{video_id}_post.json")
        if os.path.exists(post_file):
            shutil.move(post_file, os.path.join(archive_posts, f"{video_id}_post.json"))
            archived_posts += 1

        # Archive corresponding transcript if exists
        transcript_file = os.path.join(transcript_dir, f"{video_id}_transcript.txt")
        if os.path.exists(transcript_file):
            shutil.move(transcript_file, os.path.join(archive_transcripts, f"{video_id}_transcript.txt"))
            archived_transcripts += 1

    # Archive the results file with timestamp
    results_file = os.path.join(input_dir, "post_results.json")
    if os.path.exists(results_file):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        shutil.move(results_file, os.path.join(archive_posts, f"post_results_{timestamp}.json"))

    return archived_posts, archived_transcripts


def main():
    parser = argparse.ArgumentParser(description="Batch post to Discourse")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--input-dir", default="ready_to_post",
                        help="Directory with prepared post files")
    parser.add_argument("--index", default="video_index.json",
                        help="Path to video_index.json to update")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without posting")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Delay between posts in seconds")
    parser.add_argument("--no-archive", action="store_true",
                        help="Don't auto-archive files after posting")
    parser.add_argument("--transcript-dir", default="pending_imports",
                        help="Directory with transcripts to archive")
    args = parser.parse_args()

    config = load_config(args.config)

    # Find post files
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory not found: {args.input_dir}")
        sys.exit(1)

    # Look for manifest or individual post files
    manifest_path = os.path.join(args.input_dir, "manifest.json")
    posts = []

    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
            posts = manifest.get('posts', [])
    else:
        # Find all *_post.json files
        for filename in sorted(os.listdir(args.input_dir)):
            if filename.endswith('_post.json'):
                filepath = os.path.join(args.input_dir, filename)
                with open(filepath) as f:
                    post = json.load(f)
                    posts.append(post)

    if not posts:
        print("No posts found in input directory.")
        print("Expected: *_post.json files or manifest.json")
        sys.exit(0)

    print(f"Found {len(posts)} posts to {'preview' if args.dry_run else 'publish'}")
    print("=" * 60)

    results = []
    success = 0
    failed = 0

    for i, post in enumerate(posts, 1):
        video_id = post.get('video_id', 'unknown')
        title = post['title']
        body = post['body']
        video_date = post.get('video_date')

        print(f"\n[{i}/{len(posts)}] {title[:60]}...")

        if args.dry_run:
            print(f"  Video ID: {video_id}")
            print(f"  Backdate: {video_date}")
            print(f"  Body preview: {body[:100]}...")
            results.append({'video_id': video_id, 'status': 'dry-run'})
            success += 1
            continue

        # Create topic
        result = create_topic(config, title, body)

        if result:
            topic_id = result.get('topic_id')
            topic_slug = result.get('topic_slug', '')
            url = f"{config['discourse']['base_url']}/t/{topic_slug}/{topic_id}"
            print(f"  ✓ Created: {url}")

            # Backdate
            if video_date:
                if backdate_topic(config, topic_id, video_date):
                    print(f"  ✓ Backdated to {video_date}")
                else:
                    print(f"  ✗ Backdating failed")

            # Update index
            if args.index and os.path.exists(args.index):
                update_video_index(args.index, video_id, topic_id)
                print(f"  ✓ Index updated")

            results.append({
                'video_id': video_id,
                'topic_id': topic_id,
                'url': url,
                'status': 'success'
            })
            success += 1
        else:
            results.append({'video_id': video_id, 'status': 'failed'})
            failed += 1

        # Delay between posts
        if i < len(posts) and not args.dry_run:
            time.sleep(args.delay)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"{'DRY RUN ' if args.dry_run else ''}Complete: {success} success, {failed} failed")

    # Save results
    if not args.dry_run:
        results_file = os.path.join(args.input_dir, "post_results.json")
        with open(results_file, 'w') as f:
            json.dump({
                'posted_at': datetime.utcnow().isoformat() + 'Z',
                'results': results
            }, f, indent=2)
        print(f"Results saved to: {results_file}")

        # Auto-archive posted files
        if not args.no_archive and success > 0:
            archived_posts, archived_transcripts = archive_files(
                args.input_dir, args.transcript_dir, results
            )
            print(f"\n📁 Archived: {archived_posts} posts, {archived_transcripts} transcripts → archive/")


if __name__ == "__main__":
    main()
