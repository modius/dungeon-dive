#!/usr/bin/env python3
"""
Update the archive dashboards (docs/index.html, docs/health.html).

Reads from video_index.json, the archive directory, integrity reports,
keeper-posts/ and series_queue.json to update embedded data in both pages.
docs/content.html (the channel showcase) is built by build_showcase.py and
docs/insights.html by build_insights.py.

Usage:
    python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html
    python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html --dry-run
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone


def safe_re_sub(pattern, replacement, string, **kwargs):
    """re.sub that escapes backslashes in the replacement string."""
    return re.sub(pattern, lambda m: replacement, string, **kwargs)


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

    # 4. Rebuild _archiveData from actual archive files
    transcripts_dir = os.path.join(archive_dir, "transcripts")
    posts_dir = os.path.join(archive_dir, "posts")
    tx_ids = set()
    post_ids = set()
    if os.path.isdir(transcripts_dir):
        tx_ids = {f.replace("_transcript.txt", "") for f in os.listdir(transcripts_dir)
                  if f.endswith("_transcript.txt")}
    if os.path.isdir(posts_dir):
        post_ids = {f.replace("_post.json", "") for f in os.listdir(posts_dir)
                    if f.endswith("_post.json")}
    all_ids = tx_ids | post_ids
    archive_data = {}
    for vid in sorted(all_ids):
        archive_data[vid] = {
            "hasTranscript": vid in tx_ids,
            "hasPost": vid in post_ids,
        }
    archive_json = json.dumps(archive_data, separators=(",", ":"))
    html = safe_re_sub(
        r"const _archiveData = \{.*?\};",
        "const _archiveData = {};".format(archive_json),
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


# ── health.html: archive operations (Keeper posts, import series) ──

def _git_added_dates(keeper_dir: str) -> dict:
    """{filename: YYYY-MM-DD the file was first committed}, from one git log call.

    File mtimes are useless here: the nightly runs from a fresh clone, so every
    Keeper post would carry the clone's date.
    """
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--name-only", "--format=@%cs", "--", keeper_dir],
            capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return {}
    dates, current = {}, None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("@"):
            current = line[1:]
        elif line and current:
            # log is newest first, so the last write is the first time it was added
            dates[os.path.basename(line)] = current
    return dates


def build_keeper_posts_data(keeper_dir: str) -> list:
    """Keeper posts in publication order: theme, date, linked video count."""
    posts = []
    if not os.path.isdir(keeper_dir):
        return posts
    added = _git_added_dates(keeper_dir)
    for fname in sorted(os.listdir(keeper_dir)):
        if not fname.startswith("keeper-") or not fname.endswith(".md"):
            continue
        fpath = os.path.join(keeper_dir, fname)
        with open(fpath) as f:
            content = f.read()
        theme_match = re.search(r"^#\s+(.+?)(?:\s*\(Part.*?\))?\s*(?:—.*)?$", content, re.MULTILINE)
        theme = theme_match.group(1).strip() if theme_match else fname.replace("keeper-", "").replace(".md", "").replace("-", " ").title()
        links = re.findall(r"https://dungeondive\.quest/t/\d+", content)
        date = added.get(fname) or datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d")
        posts.append({"theme": theme, "date": date, "count": len(set(links))})
    posts.sort(key=lambda p: p["date"])
    return posts


def build_import_series(videos: list, series_path: str) -> list:
    """Active and completed import series from series_queue.json."""
    if not os.path.exists(series_path):
        return []
    with open(series_path) as f:
        queue = json.load(f)
    status = {v["video_id"]: v.get("status") for v in videos}
    out = []
    for s in queue.get("active_series", []):
        ids = s.get("video_ids", [])
        out.append({
            "title": s.get("title", s.get("theme", "Unknown")),
            "status": "active",
            "total": len(ids),
            "imported": sum(1 for vid in ids if status.get(vid) == "imported"),
            "date": s.get("last_imported") or "",
        })
    for s in reversed(queue.get("completed_series", [])):
        total = s.get("total_videos", 0)
        out.append({
            "title": s.get("title", s.get("theme", "Unknown")),
            "status": "completed",
            "total": total,
            "imported": total,
            "date": s.get("completed_date", ""),
        })
    return out


def update_health_ops(html: str, videos: list, keeper_dir: str, series_path: str) -> str:
    keeper_js = json.dumps(build_keeper_posts_data(keeper_dir))
    html = safe_re_sub(r"const KEEPER_POSTS = \[.*?\];", "const KEEPER_POSTS = {};".format(keeper_js),
                       html, flags=re.DOTALL)
    series_js = json.dumps(build_import_series(videos, series_path))
    html = safe_re_sub(r"const IMPORT_SERIES = \[.*?\];", "const IMPORT_SERIES = {};".format(series_js),
                       html, flags=re.DOTALL)
    return html


def main():
    parser = argparse.ArgumentParser(description="Update dashboard stats and data")
    parser.add_argument("--index", default="video_index.json", help="Path to video_index.json")
    parser.add_argument("--dashboard", default="docs/index.html", help="Path to dashboard HTML")
    parser.add_argument("--archive-dir", default="archive", help="Path to archive directory")
    parser.add_argument("--keeper-dir", default="keeper-posts", help="Path to keeper posts directory")
    parser.add_argument("--series", default="series_queue.json", help="Path to series_queue.json")
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
        health_updated = update_health_ops(health_updated, videos, args.keeper_dir, args.series)

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

    if not changes:
        print("\nAll dashboards already up to date.")
    elif args.dry_run:
        print("\nDRY RUN — would update: {}".format(", ".join(changes)))
    else:
        print("\nDashboard updated: {}".format(args.dashboard))


if __name__ == "__main__":
    main()
