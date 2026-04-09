#!/usr/bin/env python3
"""
Incremental data repair tool for the Dungeon Dive archive.

Subcommands: report, schema, rename, cleanup, timestamps, posts, transcripts.
Run with --dry-run to preview changes. See --help for details.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    requests = None

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

from config_utils import load_config


def load_index(path: str) -> dict:
    with open(path) as f:
        return json.load(f)

def save_index(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved {path}")

def _imported_videos(data: dict) -> list:
    return [v for v in data["videos"] if v.get("status") == "imported"]

def _legacy_transcripts(transcripts_dir: str, video_ids: set) -> list:
    if not os.path.isdir(transcripts_dir):
        return []
    return [(f, f.replace(".txt", "")) for f in os.listdir(transcripts_dir)
            if f.endswith(".txt") and not f.endswith("_transcript.txt")
            and f.replace(".txt", "") in video_ids]

def _transcript_exists(transcripts_dir: str, vid: str) -> bool:
    return (os.path.isfile(os.path.join(transcripts_dir, f"{vid}_transcript.txt"))
            or os.path.isfile(os.path.join(transcripts_dir, f"{vid}.txt")))

def _stale_pending(pending_dir: str, data: dict) -> list:
    done = {v["video_id"] for v in data["videos"]
            if v.get("status") in ("imported", "no_transcript")}
    if not os.path.isdir(pending_dir):
        return []
    return [f.replace("_meta.json", "") for f in os.listdir(pending_dir)
            if f.endswith("_meta.json") and f.replace("_meta.json", "") in done]

# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_report(args):
    data = load_index(args.index)
    video_ids = {v["video_id"] for v in data["videos"]}
    imported = _imported_videos(data)
    transcripts_dir = os.path.join(args.archive_dir, "transcripts")
    posts_dir = os.path.join(args.archive_dir, "posts")

    counts = {
        "Missing imported_at timestamps": len([v for v in imported if not v.get("imported_at")]),
        "Legacy transcript filenames": len(_legacy_transcripts(transcripts_dir, video_ids)),
        "Stale pending_imports": len(_stale_pending(args.pending_dir, data)),
        "Missing post files": len([v for v in imported
            if not os.path.isfile(os.path.join(posts_dir, f"{v['video_id']}_post.json"))]),
        "Missing transcript files": len([v for v in imported
            if not _transcript_exists(transcripts_dir, v["video_id"])]),
    }
    print("=== Repair Report ===")
    for label, n in counts.items():
        print(f"  {label + ':':<35s} {n}")
    print(f"  {'TOTAL issues:':<35s} {sum(counts.values())}")

def cmd_schema(args):
    data = load_index(args.index)
    count = 0
    for v in data["videos"]:
        ts = v.get("imported_at")
        if ts and ts.endswith("Z"):
            v["imported_at"] = ts[:-1] + "+00:00"
            count += 1
    if count and not args.dry_run:
        save_index(args.index, data)
    print(f"Normalized {count} timestamp(s){' (dry run)' if args.dry_run else ''}.")

def cmd_rename(args):
    data = load_index(args.index)
    video_ids = {v["video_id"] for v in data["videos"]}
    transcripts_dir = os.path.join(args.archive_dir, "transcripts")
    legacy = _legacy_transcripts(transcripts_dir, video_ids)

    for old_name, vid in legacy:
        new_name = f"{vid}_transcript.txt"
        old_path = os.path.join(transcripts_dir, old_name)
        new_path = os.path.join(transcripts_dir, new_name)
        if args.dry_run:
            print(f"  Would rename: {old_name} -> {new_name}")
        else:
            os.rename(old_path, new_path)
            print(f"  Renamed: {old_name} -> {new_name}")
    print(f"Renamed {len(legacy)} file(s){' (dry run)' if args.dry_run else ''}.")

def cmd_cleanup(args):
    data = load_index(args.index)
    stale = _stale_pending(args.pending_dir, data)

    for vid in stale:
        meta = os.path.join(args.pending_dir, f"{vid}_meta.json")
        tx = os.path.join(args.pending_dir, f"{vid}_transcript.txt")
        if args.dry_run:
            print(f"  Would remove: {vid}_meta.json" +
                  (f" + {vid}_transcript.txt" if os.path.isfile(tx) else ""))
        else:
            os.remove(meta)
            if os.path.isfile(tx):
                os.remove(tx)
            print(f"  Removed: {vid}")
    print(f"Cleaned {len(stale)} stale file(s){' (dry run)' if args.dry_run else ''}.")

def cmd_timestamps(args):
    data = load_index(args.index)
    posts_dir = os.path.join(args.archive_dir, "posts")
    config = load_config(args.config) if args.config else None
    disc = config.get("discourse", {}) if config else {}

    missing = [v for v in data["videos"]
               if v.get("status") == "imported" and not v.get("imported_at")]
    fixed = 0

    for v in missing:
        vid = v["video_id"]
        ts = None

        # Strategy 1: post file mtime
        post_path = os.path.join(posts_dir, f"{vid}_post.json")
        if os.path.isfile(post_path):
            mtime = os.path.getmtime(post_path)
            ts = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

        # Strategy 2: Discourse API
        if not ts and disc and v.get("discourse_topic_id") and requests:
            base_url = disc.get("base_url", "").rstrip("/")
            headers = {"Api-Key": disc["api_key"], "Api-Username": disc["api_username"]}
            try:
                resp = requests.get(f"{base_url}/t/{v['discourse_topic_id']}.json",
                                    headers=headers, timeout=10)
                if resp.ok:
                    ts = resp.json().get("created_at")
                time.sleep(0.5)
            except requests.RequestException:
                pass

        if ts:
            if args.dry_run:
                print(f"  Would set imported_at for {vid}: {ts}")
            else:
                v["imported_at"] = ts
            fixed += 1

    if fixed and not args.dry_run:
        save_index(args.index, data)
    print(f"Fixed {fixed}/{len(missing)} timestamp(s){' (dry run)' if args.dry_run else ''}.")

def cmd_posts(args):
    if not args.config:
        print("Error: --config is required for the posts subcommand.", file=sys.stderr)
        sys.exit(1)
    if requests is None:
        print("Error: requests library required.", file=sys.stderr)
        sys.exit(1)

    config = load_config(args.config)
    disc = config.get("discourse", {})
    base_url = disc.get("base_url", "").rstrip("/")
    headers = {"Api-Key": disc["api_key"], "Api-Username": disc["api_username"]}

    data = load_index(args.index)
    posts_dir = os.path.join(args.archive_dir, "posts")
    os.makedirs(posts_dir, exist_ok=True)

    candidates = [v for v in _imported_videos(data)
                  if v.get("discourse_topic_id")
                  and not os.path.isfile(os.path.join(posts_dir, f"{v['video_id']}_post.json"))]

    to_process = candidates[:args.limit]
    recovered = 0

    for i, v in enumerate(to_process, 1):
        vid = v["video_id"]
        topic_id = v["discourse_topic_id"]
        print(f"  [{i}/{len(to_process)}] Fetching topic {topic_id} for {vid}...")

        if args.dry_run:
            recovered += 1
            continue

        try:
            resp = requests.get(f"{base_url}/t/{topic_id}.json", headers=headers, timeout=15)
            if resp.ok:
                topic = resp.json()
                body = topic["post_stream"]["posts"][0]["cooked"]
                post_data = {
                    "video_id": vid,
                    "title": v.get("title", ""),
                    "discourse_topic_id": topic_id,
                    "body": body,
                    "recovered_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                }
                out = os.path.join(posts_dir, f"{vid}_post.json")
                with open(out, "w") as f:
                    json.dump(post_data, f, indent=2, ensure_ascii=False)
                recovered += 1
            else:
                print(f"    HTTP {resp.status_code}")
        except requests.RequestException as e:
            print(f"    Error: {e}")

        if i < len(to_process):
            time.sleep(0.5)

    print(f"Recovered {recovered}/{len(to_process)} post(s){' (dry run)' if args.dry_run else ''}.")

def cmd_transcripts(args):
    if YouTubeTranscriptApi is None:
        print("Error: youtube-transcript-api required.", file=sys.stderr)
        sys.exit(1)

    # Rate limit check
    result = subprocess.run([sys.executable, "scripts/check_rate_limit.py"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print("Warning: Rate limited by YouTube. Try again later.", file=sys.stderr)
        sys.exit(1)

    data = load_index(args.index)
    transcripts_dir = os.path.join(args.archive_dir, "transcripts")
    os.makedirs(transcripts_dir, exist_ok=True)

    candidates = [v for v in _imported_videos(data)
                  if not _transcript_exists(transcripts_dir, v["video_id"])]
    to_process = candidates[:args.limit]
    recovered = 0

    for i, v in enumerate(to_process, 1):
        vid = v["video_id"]
        print(f"  [{i}/{len(to_process)}] Fetching transcript for {vid}...")

        if args.dry_run:
            recovered += 1
            continue

        try:
            ytt_api = YouTubeTranscriptApi()
            entries = ytt_api.fetch(vid)
            texts = [e.text if hasattr(e, "text") else e.get("text", "") for e in entries]
            transcript = " ".join(texts)

            out = os.path.join(transcripts_dir, f"{vid}_transcript.txt")
            with open(out, "w") as f:
                f.write(transcript)
            recovered += 1
            print(f"    Saved ({len(transcript)} chars)")
        except Exception as e:
            print(f"    Failed: {e}")

        if i < len(to_process):
            time.sleep(3.0)

    print(f"Recovered {recovered}/{len(to_process)} transcript(s)"
          f"{' (dry run)' if args.dry_run else ''}.")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Dungeon Dive data repair tool")
    p.add_argument("--index", default="video_index.json")
    p.add_argument("--archive-dir", default="archive")
    p.add_argument("--pending-dir", default="pending_imports")
    p.add_argument("--dry-run", action="store_true", help="Preview changes without applying")

    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("report", help="Show all issues without fixing")
    sub.add_parser("schema", help="Normalize timestamps (Z -> +00:00)")
    sub.add_parser("rename", help="Fix legacy transcript filenames")
    sub.add_parser("cleanup", help="Remove stale pending_imports files")

    ts = sub.add_parser("timestamps", help="Backfill missing imported_at")
    ts.add_argument("--config", default=None, help="config.json (enables Discourse API)")
    ps = sub.add_parser("posts", help="Recover missing post files from Discourse")
    ps.add_argument("--config", required=True, help="Path to config.json")
    ps.add_argument("--limit", type=int, default=10)
    tx = sub.add_parser("transcripts", help="Recover missing transcripts from YouTube")
    tx.add_argument("--limit", type=int, default=5)

    args = p.parse_args()
    cmds = {"report": cmd_report, "schema": cmd_schema, "rename": cmd_rename,
            "cleanup": cmd_cleanup, "timestamps": cmd_timestamps,
            "posts": cmd_posts, "transcripts": cmd_transcripts}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
