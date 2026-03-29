#!/usr/bin/env python3
"""
Integrity check for the Dungeon Dive video archive.

Read-only script that verifies consistency between the video index,
local archive files, dashboard stats, and optionally Discourse.

Usage:
    python3 scripts/check_integrity.py --config config.json
    python3 scripts/check_integrity.py --config config.json --check-discourse
    python3 scripts/check_integrity.py --config config.json --quiet
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


from config_utils import load_config


def load_index(index_path: str) -> dict:
    with open(index_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Check functions — each returns { "status": "pass"|"warn"|"error", ... }
# ---------------------------------------------------------------------------

def check_index_integrity(videos: list) -> dict:
    """Verify index structure: counts, required fields, duplicates."""
    result = {"status": "pass", "issues": []}

    # Counts by status
    status_counts = Counter(v.get("status", "MISSING") for v in videos)
    result["counts"] = {
        "total": len(videos),
        "imported": status_counts.get("imported", 0),
        "pending": status_counts.get("pending", 0),
        "no_transcript": status_counts.get("no_transcript", 0),
        "skipped": status_counts.get("skipped", 0),
    }

    # Unknown statuses
    known = {"pending", "imported", "no_transcript", "skipped"}
    unknown = {s for s in status_counts if s not in known}
    if unknown:
        result["issues"].append(f"Unknown status values: {unknown}")
        result["status"] = "error"

    # Duplicates
    ids = [v.get("video_id") for v in videos]
    dupes = [vid for vid, count in Counter(ids).items() if count > 1]
    result["duplicates"] = dupes
    if dupes:
        result["issues"].append(f"{len(dupes)} duplicate video_id(s)")
        result["status"] = "error"

    # Required fields
    required = ["video_id", "title", "status", "published_at"]
    missing_fields = []
    for v in videos:
        for field in required:
            if not v.get(field):
                missing_fields.append(f"{v.get('video_id', 'UNKNOWN')}: missing {field}")
    result["missing_fields"] = missing_fields
    if missing_fields:
        result["issues"].append(f"{len(missing_fields)} missing required field(s)")
        result["status"] = "error"

    # Imported without topic_id
    imported_no_topic = [
        v["video_id"] for v in videos
        if v.get("status") == "imported" and not v.get("discourse_topic_id")
    ]
    result["imported_without_topic_id"] = imported_no_topic
    if imported_no_topic:
        result["issues"].append(f"{len(imported_no_topic)} imported video(s) without discourse_topic_id")
        result["status"] = "error"

    # Imported without imported_at
    imported_no_date = [
        v["video_id"] for v in videos
        if v.get("status") == "imported" and not v.get("imported_at")
    ]
    result["imported_without_imported_at"] = imported_no_date
    if imported_no_date:
        result["issues"].append(f"{len(imported_no_date)} imported video(s) without imported_at timestamp")
        if result["status"] == "pass":
            result["status"] = "warn"

    return result


def check_archive_files(videos: list, archive_dir: str) -> dict:
    """Cross-reference imported videos vs archive files."""
    result = {"status": "pass", "issues": []}

    posts_dir = os.path.join(archive_dir, "posts")
    transcripts_dir = os.path.join(archive_dir, "transcripts")

    # Scan post files (exclude post_results_*.json and integrity_*.json)
    post_files = {}
    if os.path.isdir(posts_dir):
        for f in os.listdir(posts_dir):
            if f.endswith("_post.json"):
                vid = f.replace("_post.json", "")
                post_files[vid] = f

    # Scan transcript files (both naming conventions)
    transcript_files = {}
    legacy_transcripts = []
    if os.path.isdir(transcripts_dir):
        for f in os.listdir(transcripts_dir):
            if f.endswith("_transcript.txt"):
                vid = f.replace("_transcript.txt", "")
                transcript_files[vid] = f
            elif f.endswith(".txt") and not f.endswith("_transcript.txt"):
                vid = f.replace(".txt", "")
                transcript_files[vid] = f
                legacy_transcripts.append(f)

    result["post_files_count"] = len(post_files)
    result["transcript_files_count"] = len(transcript_files)
    result["transcript_files_legacy"] = len(legacy_transcripts)

    # Imported videos missing archive files
    imported = [v for v in videos if v.get("status") == "imported"]
    imported_count = len(imported)

    missing_posts = [v["video_id"] for v in imported if v["video_id"] not in post_files]
    missing_transcripts = [v["video_id"] for v in imported if v["video_id"] not in transcript_files]

    result["imported_count"] = imported_count
    result["missing_posts"] = missing_posts
    result["missing_transcripts"] = missing_transcripts

    # Orphan files (in archive but not in index as imported)
    imported_ids = {v["video_id"] for v in imported}
    all_ids = {v["video_id"] for v in videos}
    orphan_posts = [vid for vid in post_files if vid not in all_ids]
    orphan_transcripts = [vid for vid in transcript_files if vid not in all_ids]

    result["orphan_posts"] = orphan_posts
    result["orphan_transcripts"] = orphan_transcripts

    if missing_posts or missing_transcripts:
        result["issues"].append(
            f"{len(missing_posts)} imported videos missing post files, "
            f"{len(missing_transcripts)} missing transcripts"
        )
        result["status"] = "warn"

    if orphan_posts or orphan_transcripts:
        result["issues"].append(
            f"{len(orphan_posts)} orphan post files, "
            f"{len(orphan_transcripts)} orphan transcript files"
        )
        if result["status"] == "pass":
            result["status"] = "warn"

    return result


def check_file_validity(archive_dir: str) -> dict:
    """Verify post JSONs parse and transcripts are non-empty."""
    result = {"status": "pass", "issues": []}

    posts_dir = os.path.join(archive_dir, "posts")
    transcripts_dir = os.path.join(archive_dir, "transcripts")

    json_errors = []
    posts_checked = 0
    if os.path.isdir(posts_dir):
        for f in os.listdir(posts_dir):
            if f.endswith("_post.json"):
                posts_checked += 1
                try:
                    with open(os.path.join(posts_dir, f)) as fh:
                        json.load(fh)
                except (json.JSONDecodeError, Exception) as e:
                    json_errors.append(f"{f}: {e}")

    empty_transcripts = []
    transcripts_checked = 0
    if os.path.isdir(transcripts_dir):
        for f in os.listdir(transcripts_dir):
            if f.endswith(".txt"):
                transcripts_checked += 1
                fpath = os.path.join(transcripts_dir, f)
                if os.path.getsize(fpath) == 0:
                    empty_transcripts.append(f)

    result["posts_checked"] = posts_checked
    result["transcripts_checked"] = transcripts_checked
    result["json_errors"] = json_errors
    result["empty_transcripts"] = empty_transcripts

    if json_errors:
        result["issues"].append(f"{len(json_errors)} post JSON parse error(s)")
        result["status"] = "error"
    if empty_transcripts:
        result["issues"].append(f"{len(empty_transcripts)} empty transcript file(s)")
        result["status"] = "error"

    return result


def check_naming_anomalies(archive_dir: str) -> dict:
    """Flag legacy transcript files without _transcript suffix."""
    result = {"status": "pass", "issues": []}

    transcripts_dir = os.path.join(archive_dir, "transcripts")
    legacy = []
    if os.path.isdir(transcripts_dir):
        for f in os.listdir(transcripts_dir):
            if f.endswith(".txt") and not f.endswith("_transcript.txt"):
                legacy.append(f)

    result["legacy_files"] = legacy
    if legacy:
        result["issues"].append(f"{len(legacy)} transcript files using legacy naming (missing _transcript suffix)")
        result["status"] = "warn"

    return result


def check_dashboard_sync(dashboard_path: str, videos: list, archive_dir: str) -> dict:
    """Compare dashboard stats against actual index and archive counts."""
    result = {"status": "pass", "issues": [], "mismatches": {}}

    if not os.path.isfile(dashboard_path):
        result["status"] = "warn"
        result["issues"].append(f"Dashboard not found at {dashboard_path}")
        return result

    with open(dashboard_path) as f:
        html = f.read()

    # Parse stats from: const stats = { total: 1007, imported: 276, pending: 727, noTranscript: 4 };
    stats_match = re.search(
        r"total:\s*(\d+),\s*imported:\s*(\d+),\s*pending:\s*(\d+),\s*noTranscript:\s*(\d+)",
        html
    )
    if not stats_match:
        result["status"] = "warn"
        result["issues"].append("Could not parse stats from dashboard")
        return result

    dash_total = int(stats_match.group(1))
    dash_imported = int(stats_match.group(2))
    dash_pending = int(stats_match.group(3))
    dash_no_tx = int(stats_match.group(4))

    # Parse archive counts from: 205 transcripts &bull; 213 posts
    archive_match = re.search(r"(\d+)\s*transcripts\s*&bull;\s*(\d+)\s*posts", html)
    dash_transcripts = int(archive_match.group(1)) if archive_match else None
    dash_posts = int(archive_match.group(2)) if archive_match else None

    # Actual counts
    status_counts = Counter(v.get("status") for v in videos)
    actual_total = len(videos)
    actual_imported = status_counts.get("imported", 0)
    actual_pending = status_counts.get("pending", 0)
    actual_no_tx = status_counts.get("no_transcript", 0)

    # Actual archive file counts
    posts_dir = os.path.join(archive_dir, "posts")
    transcripts_dir = os.path.join(archive_dir, "transcripts")
    actual_post_files = len([f for f in os.listdir(posts_dir) if f.endswith("_post.json")]) if os.path.isdir(posts_dir) else 0
    actual_transcript_files = len([f for f in os.listdir(transcripts_dir) if f.endswith(".txt")]) if os.path.isdir(transcripts_dir) else 0

    # Compare
    comparisons = {
        "total": (actual_total, dash_total),
        "imported": (actual_imported, dash_imported),
        "pending": (actual_pending, dash_pending),
        "no_transcript": (actual_no_tx, dash_no_tx),
    }
    if dash_transcripts is not None:
        comparisons["transcripts"] = (actual_transcript_files, dash_transcripts)
    if dash_posts is not None:
        comparisons["posts"] = (actual_post_files, dash_posts)

    for key, (actual, dashboard) in comparisons.items():
        if actual != dashboard:
            result["mismatches"][key] = {"index": actual, "dashboard": dashboard}

    if result["mismatches"]:
        result["status"] = "warn"
        result["issues"].append(
            f"Dashboard out of date: {len(result['mismatches'])} stat(s) differ from index"
        )

    return result


def check_discourse_topics(videos: list, config: dict) -> dict:
    """Verify imported videos have valid Discourse topics (API calls)."""
    result = {"status": "pass", "issues": []}

    if requests is None:
        result["status"] = "warn"
        result["issues"].append("requests library not available — cannot check Discourse")
        return result

    base_url = config.get("discourse", {}).get("base_url", "").rstrip("/")
    api_key = config.get("discourse", {}).get("api_key", "")
    api_user = config.get("discourse", {}).get("api_username", "")

    if not base_url or not api_key:
        result["status"] = "warn"
        result["issues"].append("Discourse config incomplete — cannot verify topics")
        return result

    headers = {
        "Api-Key": api_key,
        "Api-Username": api_user,
    }

    imported = [v for v in videos if v.get("status") == "imported" and v.get("discourse_topic_id")]
    result["topics_to_check"] = len(imported)

    missing = []
    errors = []
    checked = 0

    for v in imported:
        topic_id = v["discourse_topic_id"]
        try:
            resp = requests.head(
                f"{base_url}/t/{topic_id}.json",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 404:
                missing.append({"video_id": v["video_id"], "topic_id": topic_id, "error": "404 Not Found"})
            elif resp.status_code >= 400:
                errors.append({"video_id": v["video_id"], "topic_id": topic_id, "error": f"HTTP {resp.status_code}"})
        except requests.RequestException as e:
            errors.append({"video_id": v["video_id"], "topic_id": topic_id, "error": str(e)})

        checked += 1
        if checked % 50 == 0:
            print(f"  Checked {checked}/{len(imported)} topics...")
        time.sleep(0.3)

    result["topics_checked"] = checked
    result["missing_topics"] = missing
    result["error_topics"] = errors

    if missing:
        result["issues"].append(f"{len(missing)} topic(s) return 404 — may have been deleted")
        result["status"] = "error"
    if errors:
        result["issues"].append(f"{len(errors)} topic(s) returned errors")
        if result["status"] == "pass":
            result["status"] = "warn"

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def print_section(title: str, result: dict, quiet: bool):
    if quiet:
        return
    status = result["status"].upper()
    print(f"\n--- {title} ---")
    # Print all keys that aren't meta
    for key, val in result.items():
        if key in ("status", "issues"):
            continue
        if isinstance(val, list) and len(val) > 10:
            print(f"  {key}: {len(val)} items")
        elif isinstance(val, list):
            if val:
                print(f"  {key}: {val}")
        elif isinstance(val, dict):
            for k, v in val.items():
                if isinstance(v, dict):
                    parts = [f"{sk}={sv}" for sk, sv in v.items()]
                    print(f"  {k}: {', '.join(parts)}")
                else:
                    print(f"  {k}: {v}")
        else:
            print(f"  {key}: {val}")
    if result["issues"]:
        for issue in result["issues"]:
            print(f"  ! {issue}")
    print(f"  STATUS: {status}")


def main():
    parser = argparse.ArgumentParser(description="Dungeon Dive archive integrity check")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--index", default="video_index.json", help="Path to video_index.json")
    parser.add_argument("--dashboard", default="docs/index.html", help="Path to dashboard HTML")
    parser.add_argument("--check-discourse", action="store_true", help="Verify Discourse topics via API (slow)")
    parser.add_argument("--output-dir", default="archive", help="Directory for results JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress console output")
    args = parser.parse_args()

    run_at = datetime.now(timezone.utc).isoformat()

    if not args.quiet:
        print("=== Dungeon Dive Integrity Check ===")
        print(f"Run: {run_at}")

    # Load data
    config = load_config(args.config)
    index_data = load_index(args.index)
    videos = index_data.get("videos", [])

    archive_dir = "archive"

    # Run checks
    checks = {}

    checks["index_integrity"] = check_index_integrity(videos)
    print_section("Index Integrity", checks["index_integrity"], args.quiet)

    checks["archive_files"] = check_archive_files(videos, archive_dir)
    print_section("Archive Files", checks["archive_files"], args.quiet)

    checks["file_validity"] = check_file_validity(archive_dir)
    print_section("File Validity", checks["file_validity"], args.quiet)

    checks["naming_anomalies"] = check_naming_anomalies(archive_dir)
    print_section("Naming Anomalies", checks["naming_anomalies"], args.quiet)

    checks["dashboard_sync"] = check_dashboard_sync(args.dashboard, videos, archive_dir)
    print_section("Dashboard Sync", checks["dashboard_sync"], args.quiet)

    if args.check_discourse:
        checks["discourse_verification"] = check_discourse_topics(videos, config)
        print_section("Discourse Verification", checks["discourse_verification"], args.quiet)
    else:
        checks["discourse_verification"] = {"status": "skipped", "issues": []}
        if not args.quiet:
            print("\n--- Discourse Verification ---")
            print("  SKIPPED (use --check-discourse to enable)")

    # Overall status
    statuses = [c["status"] for c in checks.values()]
    if "error" in statuses:
        overall = "error"
        exit_code = 2
    elif "warn" in statuses:
        overall = "warn"
        exit_code = 1
    else:
        overall = "pass"
        exit_code = 0

    # Build recommendations
    recommendations = []
    if checks["dashboard_sync"].get("mismatches"):
        mm = checks["dashboard_sync"]["mismatches"]
        parts = ["{} {}->{}".format(k, v["dashboard"], v["index"]) for k, v in mm.items()]
        recommendations.append("Update dashboard stats: " + ", ".join(parts))
    if checks["naming_anomalies"].get("legacy_files"):
        n = len(checks["naming_anomalies"]["legacy_files"])
        recommendations.append(f"Rename {n} legacy transcript files to *_transcript.txt format")
    if checks["archive_files"].get("missing_posts"):
        n = len(checks["archive_files"]["missing_posts"])
        recommendations.append(f"{n} imported videos missing local post archives")
    if checks["archive_files"].get("missing_transcripts"):
        n = len(checks["archive_files"]["missing_transcripts"])
        recommendations.append(f"{n} imported videos missing local transcripts")
    if checks["archive_files"].get("orphan_posts"):
        n = len(checks["archive_files"]["orphan_posts"])
        recommendations.append(f"{n} orphan post files in archive (no matching index entry)")
    if checks["archive_files"].get("orphan_transcripts"):
        n = len(checks["archive_files"]["orphan_transcripts"])
        recommendations.append(f"{n} orphan transcript files in archive (no matching index entry)")

    warn_count = statuses.count("warn")
    error_count = statuses.count("error")

    if not args.quiet:
        print(f"\n=== OVERALL: {overall.upper()} ({error_count} errors, {warn_count} warnings) ===")
        if recommendations:
            print("\nRecommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")

    # Write JSON results
    results = {
        "run_at": run_at,
        "overall_status": overall,
        "exit_code": exit_code,
        "error_count": error_count,
        "warning_count": warn_count,
        "checks": checks,
        "recommendations": recommendations,
    }

    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(args.output_dir, f"integrity_{timestamp}.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    if not args.quiet:
        print(f"\nResults written to: {output_path}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
