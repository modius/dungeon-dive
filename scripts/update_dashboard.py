#!/usr/bin/env python3
"""
Update the dashboard (docs/index.html) stats and video data.

Reads from video_index.json and the archive directory to update:
- Stats line: total, imported, pending, noTranscript counts
- Archive counts: transcripts and posts
- Video entries in the _raw template literal

Usage:
    python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html
    python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html --dry-run
"""

import argparse
import json
import os
import re
import sys
from collections import Counter


def load_index(index_path: str) -> dict:
    with open(index_path) as f:
        return json.load(f)


def count_archive_files(archive_dir: str) -> tuple:
    """Count transcript and post files in archive."""
    transcripts_dir = os.path.join(archive_dir, "transcripts")
    posts_dir = os.path.join(archive_dir, "posts")

    tx_count = 0
    if os.path.isdir(transcripts_dir):
        tx_count = len([f for f in os.listdir(transcripts_dir) if f.endswith(".txt")])

    post_count = 0
    if os.path.isdir(posts_dir):
        post_count = len([f for f in os.listdir(posts_dir) if f.endswith("_post.json")])

    return tx_count, post_count


def get_imported_videos(videos: list) -> list:
    """Get all imported videos sorted by published_at descending."""
    imported = [v for v in videos if v.get("status") == "imported" and v.get("discourse_topic_id")]
    return sorted(imported, key=lambda v: v.get("published_at", ""), reverse=True)


def build_raw_entries(imported_videos: list) -> str:
    """Build the _raw pipe-delimited data for imported videos."""
    lines = []
    for v in imported_videos:
        vid = v["video_id"]
        title = v["title"].replace("|", "-")  # escape pipe in titles
        date = v["published_at"][:10]  # YYYY-MM-DD
        status = "imported"
        topic_id = v["discourse_topic_id"]
        lines.append("{}|{}|{}|{}|{}".format(vid, title, date, status, topic_id))
    return "\\n".join(lines)


def update_dashboard(html: str, videos: list, archive_dir: str) -> str:
    """Update all dynamic parts of the dashboard HTML."""
    status_counts = Counter(v.get("status") for v in videos)
    total = len(videos)
    imported = status_counts.get("imported", 0)
    pending = status_counts.get("pending", 0)
    no_tx = status_counts.get("no_transcript", 0)

    tx_count, post_count = count_archive_files(archive_dir)

    # 1. Update stats line
    html = re.sub(
        r"const stats = \{ total: \d+, imported: \d+, pending: \d+, noTranscript: \d+ \}",
        "const stats = {{ total: {}, imported: {}, pending: {}, noTranscript: {} }}".format(
            total, imported, pending, no_tx
        ),
        html,
    )

    # 2. Update archive counts
    html = re.sub(
        r"\d+ transcripts &bull; \d+ posts",
        "{} transcripts &bull; {} posts".format(tx_count, post_count),
        html,
    )

    # 3. Update _raw data with all imported videos
    imported_videos = get_imported_videos(videos)
    new_raw = build_raw_entries(imported_videos)

    html = re.sub(
        r"const _raw = `[^`]*`",
        "const _raw = `{}`".format(new_raw),
        html,
        flags=re.DOTALL,
    )

    return html


def main():
    parser = argparse.ArgumentParser(description="Update dashboard stats and data")
    parser.add_argument("--index", default="video_index.json", help="Path to video_index.json")
    parser.add_argument("--dashboard", default="docs/index.html", help="Path to dashboard HTML")
    parser.add_argument("--archive-dir", default="archive", help="Path to archive directory")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = parser.parse_args()

    index_data = load_index(args.index)
    videos = index_data.get("videos", [])

    with open(args.dashboard) as f:
        original = f.read()

    updated = update_dashboard(original, videos, args.archive_dir)

    if original == updated:
        print("Dashboard already up to date.")
        return

    # Show what changed
    status_counts = Counter(v.get("status") for v in videos)
    tx_count, post_count = count_archive_files(args.archive_dir)
    imported_count = len(get_imported_videos(videos))

    print("Dashboard updates:")
    print("  Stats: total={}, imported={}, pending={}, noTranscript={}".format(
        len(videos), status_counts.get("imported", 0),
        status_counts.get("pending", 0), status_counts.get("no_transcript", 0)
    ))
    print("  Archive: {} transcripts, {} posts".format(tx_count, post_count))
    print("  Video entries in _raw: {}".format(imported_count))

    if args.dry_run:
        print("\nDRY RUN — no changes written.")
        return

    with open(args.dashboard, "w") as f:
        f.write(updated)

    print("\nDashboard updated: {}".format(args.dashboard))


if __name__ == "__main__":
    main()
