#!/usr/bin/env python3
"""
Update all dashboard pages (docs/index.html, docs/health.html, docs/content.html).

Reads from video_index.json, the archive directory, integrity reports, and
keeper-posts/ to update embedded data in all three dashboard pages.

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
from datetime import datetime, timezone


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


def get_all_videos_sorted(videos: list) -> list:
    """Get all videos sorted by published_at descending."""
    return sorted(videos, key=lambda v: v.get("published_at", ""), reverse=True)


def build_raw_entries(videos: list) -> str:
    """Build the _raw pipe-delimited data for all videos."""
    lines = []
    for v in videos:
        vid = v["video_id"]
        title = v["title"].replace("|", "-")  # escape pipe in titles
        date = v["published_at"][:10]  # YYYY-MM-DD
        status = v.get("status", "pending")
        topic_id = v.get("discourse_topic_id") or ""
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

    # 3. Update _raw data with all videos
    all_videos = get_all_videos_sorted(videos)
    new_raw = build_raw_entries(all_videos)

    html = re.sub(
        r"const _raw = `[^`]*`",
        "const _raw = `{}`".format(new_raw),
        html,
        flags=re.DOTALL,
    )

    return html


# ── health.html updater ────────────────────────────────────────────

def get_latest_integrity(archive_dir: str):
    """Find and load the most recent integrity JSON report."""
    candidates = sorted(
        [f for f in os.listdir(archive_dir)
         if f.startswith("integrity_") and f.endswith(".json")],
        reverse=True,
    )
    if not candidates:
        return None
    with open(os.path.join(archive_dir, candidates[0])) as f:
        return json.load(f)


def build_batch_data(videos: list) -> list:
    """Build batch import data from imported_at timestamps, grouped by date."""
    date_counts = Counter()
    for v in videos:
        ts = v.get("imported_at")
        if ts and v.get("status") == "imported":
            date_counts[ts[:10]] += 1
    return [{"date": d, "count": c} for d, c in sorted(date_counts.items())]


def build_problem_videos(videos: list) -> list:
    """Get videos with no_transcript status."""
    return [
        {
            "title": v["title"],
            "published_at": v["published_at"][:10],
            "video_id": v["video_id"],
        }
        for v in videos
        if v.get("status") == "no_transcript"
    ]


def update_health(html: str, videos: list, archive_dir: str) -> str:
    """Update embedded data in health.html."""
    status_counts = Counter(v.get("status") for v in videos)
    total = len(videos)
    imported = status_counts.get("imported", 0)
    pending = status_counts.get("pending", 0)
    no_tx = status_counts.get("no_transcript", 0)

    tx_count, post_count = count_archive_files(archive_dir)

    # Load latest integrity report
    integrity = get_latest_integrity(archive_dir)
    if integrity:
        # Update the INTEGRITY constant — replace everything between the braces
        integrity_js = json.dumps({
            "run_at": integrity.get("run_at", datetime.now(timezone.utc).isoformat()),
            "overall_status": integrity.get("overall_status", "warn"),
            "error_count": integrity.get("error_count", 0),
            "warning_count": integrity.get("warning_count", 0),
            "checks": {
                "index_integrity": {
                    "status": integrity.get("checks", {}).get("index_integrity", {}).get("status", "pass"),
                    "issues": integrity.get("checks", {}).get("index_integrity", {}).get("issues", []),
                    "counts": {
                        "total": total,
                        "imported": imported,
                        "pending": pending,
                        "no_transcript": no_tx,
                        "skipped": 0,
                    },
                },
                "archive_files": {
                    "status": integrity.get("checks", {}).get("archive_files", {}).get("status", "pass"),
                    "issues": integrity.get("checks", {}).get("archive_files", {}).get("issues", []),
                    "post_files_count": post_count,
                    "transcript_files_count": tx_count,
                    "transcript_files_legacy": integrity.get("checks", {}).get("archive_files", {}).get("transcript_files_legacy", 0),
                    "imported_count": imported,
                    "missing_posts_count": integrity.get("checks", {}).get("archive_files", {}).get("missing_posts", 0)
                        if isinstance(integrity.get("checks", {}).get("archive_files", {}).get("missing_posts"), int)
                        else len(integrity.get("checks", {}).get("archive_files", {}).get("missing_posts", [])),
                    "missing_transcripts_count": integrity.get("checks", {}).get("archive_files", {}).get("missing_transcripts", 0)
                        if isinstance(integrity.get("checks", {}).get("archive_files", {}).get("missing_transcripts"), int)
                        else len(integrity.get("checks", {}).get("archive_files", {}).get("missing_transcripts", [])),
                },
                "file_validity": {
                    "status": integrity.get("checks", {}).get("file_validity", {}).get("status", "pass"),
                    "issues": integrity.get("checks", {}).get("file_validity", {}).get("issues", []),
                    "posts_checked": post_count,
                    "transcripts_checked": tx_count,
                },
                "naming_anomalies": {
                    "status": integrity.get("checks", {}).get("naming_anomalies", {}).get("status", "pass"),
                    "issues": integrity.get("checks", {}).get("naming_anomalies", {}).get("issues", []),
                    "legacy_count": integrity.get("checks", {}).get("naming_anomalies", {}).get("legacy_files", 0)
                        if isinstance(integrity.get("checks", {}).get("naming_anomalies", {}).get("legacy_files"), int)
                        else len(integrity.get("checks", {}).get("naming_anomalies", {}).get("legacy_files", [])),
                },
                "dashboard_sync": {
                    "status": "pass",
                    "issues": [],
                    "mismatch_count": 0,
                },
            },
            "recommendations": integrity.get("recommendations", []),
        }, indent=2)

        html = re.sub(
            r"const INTEGRITY = \{.*?\};",
            "const INTEGRITY = {};".format(integrity_js),
            html,
            flags=re.DOTALL,
        )

    # Update BATCH_DATA
    batch_data = build_batch_data(videos)
    batch_js = json.dumps(batch_data)
    html = re.sub(
        r"const BATCH_DATA = \[.*?\];",
        "const BATCH_DATA = {};".format(batch_js),
        html,
        flags=re.DOTALL,
    )

    # Update PROBLEM_VIDEOS
    problem_videos = build_problem_videos(videos)
    problem_js = json.dumps(problem_videos, indent=2)
    html = re.sub(
        r"const PROBLEM_VIDEOS = \[.*?\];",
        "const PROBLEM_VIDEOS = {};".format(problem_js),
        html,
        flags=re.DOTALL,
    )

    return html


# ── content.html updater ───────────────────────────────────────────

def build_keeper_posts_data(keeper_dir: str) -> list:
    """Build keeper posts timeline from keeper-posts/ directory."""
    posts = []
    if not os.path.isdir(keeper_dir):
        return posts

    for fname in sorted(os.listdir(keeper_dir)):
        if not fname.startswith("keeper-") or not fname.endswith(".md"):
            continue
        fpath = os.path.join(keeper_dir, fname)
        with open(fpath) as f:
            content = f.read()

        # Extract theme from first heading
        theme_match = re.search(r"^#\s+(.+?)(?:\s*\(Part.*?\))?\s*(?:—.*)?$", content, re.MULTILINE)
        theme = theme_match.group(1).strip() if theme_match else fname.replace("keeper-", "").replace(".md", "").replace("-", " ").title()

        # Count linked videos (Discourse topic links)
        links = re.findall(r"https://dungeondive\.quest/t/\d+", content)
        count = len(set(links))

        # Get file mtime as approximate date
        mtime = os.path.getmtime(fpath)
        date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

        posts.append({"theme": theme, "date": date, "count": count})

    return posts


def build_weekly_imports(videos: list) -> list:
    """Build weekly import counts from imported_at timestamps."""
    from collections import defaultdict
    weeks = defaultdict(int)
    for v in videos:
        ts = v.get("imported_at")
        if ts and v.get("status") == "imported":
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                # ISO week start (Monday)
                week_start = dt - __import__("datetime").timedelta(days=dt.weekday())
                week_key = week_start.strftime("%Y-%m-%d")
                weeks[week_key] += 1
            except (ValueError, TypeError):
                pass
    return [[k, v] for k, v in sorted(weeks.items())]


def update_content(html: str, videos: list, keeper_dir: str) -> str:
    """Update embedded data in content.html that can be derived from project state."""

    # Update keeperPosts
    keeper_data = build_keeper_posts_data(keeper_dir)
    if keeper_data:
        keeper_js = json.dumps(keeper_data, indent=2)
        html = re.sub(
            r"const keeperPosts = \[.*?\];",
            "const keeperPosts = {};".format(keeper_js),
            html,
            flags=re.DOTALL,
        )

    # Update weeklyImports
    weekly = build_weekly_imports(videos)
    if weekly:
        weekly_js = json.dumps(weekly)
        html = re.sub(
            r"const weeklyImports = \[.*?\];",
            "const weeklyImports = {};".format(weekly_js),
            html,
            flags=re.DOTALL,
        )

    # Update "Based on N analyzed transcripts" notes
    tx_dir = os.path.join("archive", "transcripts")
    tx_count = 0
    if os.path.isdir(tx_dir):
        tx_count = len([f for f in os.listdir(tx_dir) if f.endswith(".txt")])
    if tx_count > 0:
        html = re.sub(
            r"Based on \d+ analyzed transcripts",
            "Based on {} analyzed transcripts".format(tx_count),
            html,
        )

    return html


def main():
    parser = argparse.ArgumentParser(description="Update dashboard stats and data")
    parser.add_argument("--index", default="video_index.json", help="Path to video_index.json")
    parser.add_argument("--dashboard", default="docs/index.html", help="Path to dashboard HTML")
    parser.add_argument("--archive-dir", default="archive", help="Path to archive directory")
    parser.add_argument("--keeper-dir", default="keeper-posts", help="Path to keeper posts directory")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = parser.parse_args()

    index_data = load_index(args.index)
    videos = index_data.get("videos", [])
    status_counts = Counter(v.get("status") for v in videos)
    tx_count, post_count = count_archive_files(args.archive_dir)

    changes = []

    # ── index.html ──
    with open(args.dashboard) as f:
        original = f.read()

    updated = update_dashboard(original, videos, args.archive_dir)

    if original != updated:
        changes.append("index.html")
        if not args.dry_run:
            with open(args.dashboard, "w") as f:
                f.write(updated)

    print("Dashboard updates:")
    print("  Stats: total={}, imported={}, pending={}, noTranscript={}".format(
        len(videos), status_counts.get("imported", 0),
        status_counts.get("pending", 0), status_counts.get("no_transcript", 0)
    ))
    print("  Archive: {} transcripts, {} posts".format(tx_count, post_count))
    print("  Video entries in _raw: {}".format(len(videos)))

    # ── health.html ──
    docs_dir = os.path.dirname(args.dashboard)
    health_path = os.path.join(docs_dir, "health.html")
    if os.path.exists(health_path):
        with open(health_path) as f:
            health_original = f.read()

        health_updated = update_health(health_original, videos, args.archive_dir)

        if health_original != health_updated:
            changes.append("health.html")
            if not args.dry_run:
                with open(health_path, "w") as f:
                    f.write(health_updated)
            print("\nHealth dashboard updated: {}".format(health_path))
        else:
            print("\nHealth dashboard already up to date.")
    else:
        print("\nHealth dashboard not found at {}".format(health_path))

    # ── content.html ──
    content_path = os.path.join(docs_dir, "content.html")
    if os.path.exists(content_path):
        with open(content_path) as f:
            content_original = f.read()

        content_updated = update_content(content_original, videos, args.keeper_dir)

        if content_original != content_updated:
            changes.append("content.html")
            if not args.dry_run:
                with open(content_path, "w") as f:
                    f.write(content_updated)
            print("Content dashboard updated: {}".format(content_path))
        else:
            print("Content dashboard already up to date.")
    else:
        print("Content dashboard not found at {}".format(content_path))

    if not changes:
        print("\nAll dashboards already up to date.")
    elif args.dry_run:
        print("\nDRY RUN — would update: {}".format(", ".join(changes)))
    else:
        print("\nDashboard updated: {}".format(args.dashboard))


if __name__ == "__main__":
    main()
