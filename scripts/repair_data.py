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

def _post_is_html(body: str) -> bool:
    """Post bodies recovered before 2026-08-28 hold Discourse's rendered HTML."""
    return "<div" in body or "<p>" in body

def _nonuniform_posts(posts_dir: str, data: dict, topic_categories: dict = None,
                      verify_categories: bool = False) -> list:
    """Post files that deviate from the canonical schema.

    Returns (video_id, path, issues) where issues is a subset of
    {"html", "video_date", "category"}.
    """
    out = []
    for v in _imported_videos(data):
        path = os.path.join(posts_dir, f"{v['video_id']}_post.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path) as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        issues = set()
        if _post_is_html(d.get("body", "")):
            issues.add("html")
        if "video_date" not in d:
            issues.add("video_date")
        # `category` must hold the topic's real Discourse category_id. Records
        # predating that rule hold a category *name* ("Dungeon Diving"), a
        # nominal 8 that nothing ever read, or nothing at all.
        cat = d.get("category")
        tid = d.get("discourse_topic_id") or v.get("discourse_topic_id")
        if cat is None or not isinstance(cat, int):
            issues.add("category")
        elif topic_categories and tid in topic_categories and topic_categories[tid] != cat:
            # The map *disproves* the stored value. Absence from the map is not
            # evidence of wrongness — category listings don't cover the whole
            # forum, so treating a miss as a fault would re-fetch ~300 records
            # on every run and never converge. Use --verify-categories to
            # re-check stored values against Discourse per topic.
            issues.add("category")
        elif verify_categories and isinstance(cat, int) and tid not in (topic_categories or {}):
            issues.add("category")
        if issues:
            out.append((v["video_id"], path, issues))
    return out

def _topic_category_map(base_url: str, headers: dict) -> dict:
    """Build {topic_id: category_id} by paging every category listing.

    Far cheaper than one topic fetch per post: ~40 requests covers the whole
    forum instead of ~850. Subcategories are listed separately by id, so
    paging the flat category id list is sufficient.
    """
    resp = requests.get(f"{base_url}/categories.json?include_subcategories=true",
                        headers=headers, timeout=20)
    resp.raise_for_status()
    cat_ids = []
    for c in resp.json()["category_list"]["categories"]:
        cat_ids.append(c["id"])
        for sc in c.get("subcategory_list") or []:
            cat_ids.append(sc["id"])

    mapping = {}
    for cid in cat_ids:
        page = 0
        while True:
            r = requests.get(f"{base_url}/c/{cid}.json?page={page}",
                             headers=headers, timeout=20)
            if not r.ok:
                break
            topics = r.json().get("topic_list", {}).get("topics", [])
            if not topics:
                break
            for t in topics:
                mapping[t["id"]] = t.get("category_id", cid)
            page += 1
            time.sleep(0.15)
    return mapping

def _fetch_topic_category(base_url: str, headers: dict, topic_id: int):
    """Category id for one topic. Fallback for topics absent from the bulk map.

    Category listings do not cover the whole forum (older topics fall off the
    paginated listings), so ~a third of the archive needs this per-topic read.
    """
    r = requests.get(f"{base_url}/t/{topic_id}.json", headers=headers, timeout=15)
    if not r.ok:
        return None, f"topic HTTP {r.status_code}"
    return r.json().get("category_id"), None

def _fetch_topic_markdown(base_url: str, headers: dict, topic_id: int):
    """Return (raw_markdown, category_id) for a topic's first post.

    Discourse's topic endpoint exposes only "cooked" (rendered HTML); the
    original authored markdown lives on the per-post endpoint as "raw".
    Recovering from "raw" is lossless — no HTML-to-markdown translation is
    involved, so the archived body is exactly what was published.
    """
    resp = requests.get(f"{base_url}/t/{topic_id}.json", headers=headers, timeout=15)
    if not resp.ok:
        return None, None, f"topic HTTP {resp.status_code}"
    topic = resp.json()
    first = topic["post_stream"]["posts"][0]
    presp = requests.get(f"{base_url}/posts/{first['id']}.json", headers=headers, timeout=15)
    if not presp.ok:
        return None, None, f"post HTTP {presp.status_code}"
    return presp.json().get("raw", ""), topic.get("category_id"), None

def _write_post_file(path: str, vid: str, title: str, body: str, video_date,
                     category, topic_id=None, recovered_at=None, normalized_at=None):
    """Write a post file in canonical key order."""
    out = {"video_id": vid, "title": title, "body": body,
           "video_date": video_date, "category": category}
    if topic_id is not None:
        out["discourse_topic_id"] = topic_id
    if recovered_at:
        out["recovered_at"] = recovered_at
    if normalized_at:
        out["normalized_at"] = normalized_at
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)


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
        "Non-uniform post records": len(_nonuniform_posts(posts_dir, data)),  # offline check only
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
            raw, category_id, err = _fetch_topic_markdown(base_url, headers, topic_id)
            if err:
                print(f"    {err}")
            elif not raw:
                print("    empty raw body — skipped")
            else:
                _write_post_file(
                    os.path.join(posts_dir, f"{vid}_post.json"),
                    vid, v.get("title", ""), raw,
                    v.get("published_at"), category_id,
                    topic_id=topic_id,
                    recovered_at=time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
                )
                recovered += 1
        except requests.RequestException as e:
            print(f"    Error: {e}")

        if i < len(to_process):
            time.sleep(0.5)

    print(f"Recovered {recovered}/{len(to_process)} post(s){' (dry run)' if args.dry_run else ''}.")

def cmd_normalize(args):
    """Bring legacy post files up to the canonical schema.

    Three deviations exist in the archive, all created by older tooling:
      * body holds Discourse's rendered HTML instead of the authored markdown
        (every file written by `posts` before 2026-08-28)
      * `video_date` missing
      * `category` missing

    HTML bodies and missing categories need the Discourse API; a missing
    `video_date` is backfilled from the index offline. Without --config only
    the offline fixes run.
    """
    data = load_index(args.index)
    posts_dir = os.path.join(args.archive_dir, "posts")
    by_id = {v["video_id"]: v for v in data["videos"]}

    base_url = headers = None
    topic_categories = {}
    if args.config:
        if requests is None:
            print("Error: requests library required.", file=sys.stderr)
            sys.exit(1)
        disc = load_config(args.config).get("discourse", {})
        base_url = disc.get("base_url", "").rstrip("/")
        headers = {"Api-Key": disc["api_key"], "Api-Username": disc["api_username"]}
        print("Building topic -> category map from category listings...")
        topic_categories = _topic_category_map(base_url, headers)
        print(f"  mapped {len(topic_categories)} topics")

    targets = _nonuniform_posts(posts_dir, data, topic_categories if args.config else None,
                                verify_categories=getattr(args, "verify_categories", False))
    mapped_ids = {v["video_id"] for v in data["videos"]
                  if topic_categories.get(v.get("discourse_topic_id")) is not None}
    if not targets:
        print("All post files already match the canonical schema.")
        return

    needs_api = [t for t in targets if "html" in t[2]
                 or ("category" in t[2] and t[0] not in mapped_ids)]
    offline = [t for t in targets if t not in needs_api]
    if not args.config and needs_api:
        print(f"No --config: skipping {len(needs_api)} record(s) needing the Discourse API.")
    queue = (offline + needs_api) if args.config else offline
    queue = queue[:args.limit] if args.limit else queue

    fixed = skipped = 0
    for i, (vid, path, issues) in enumerate(queue, 1):
        with open(path) as f:
            d = json.load(f)
        idx_entry = by_id.get(vid, {})
        topic_id = d.get("discourse_topic_id") or idx_entry.get("discourse_topic_id")
        body, category = d.get("body", ""), d.get("category")
        api_needed = "html" in issues
        api_calls_made = False

        if "category" in issues:
            resolved = topic_categories.get(topic_id) if topic_id else None
            if resolved is None and args.config and topic_id and not args.dry_run:
                resolved, err = _fetch_topic_category(base_url, headers, topic_id)
                if err:
                    print(f"  [{i}/{len(queue)}] {vid}: {err} — skipped")
                    skipped += 1; continue
                api_calls_made = True
            if resolved is None and args.config and not args.dry_run:
                print(f"  [{i}/{len(queue)}] {vid}: category unresolvable — skipped")
                skipped += 1; continue
            if resolved is not None:
                category = resolved

        if api_needed:
            if not topic_id:
                print(f"  [{i}/{len(queue)}] {vid}: no topic id — skipped"); skipped += 1; continue
            print(f"  [{i}/{len(queue)}] {vid}: fetching raw for topic {topic_id} ({', '.join(sorted(issues))})")
            if not args.dry_run:
                raw, _cat, err = _fetch_topic_markdown(base_url, headers, topic_id)
                if err:
                    print(f"    {err} — skipped"); skipped += 1; continue
                # Guard: never overwrite the permanent record with a body that
                # isn't demonstrably this video's post. Requiring the watch URL
                # for *this* video id is stricter than a bare id match and, unlike
                # a "starts with the link" test, does not reject legitimate
                # owner-authored posts that introduce the video before linking it.
                if not raw or f"youtube.com/watch?v={vid}" not in raw:
                    print("    raw body does not link this video — skipped")
                    skipped += 1; continue
                body = raw
        else:
            print(f"  [{i}/{len(queue)}] {vid}: {', '.join(sorted(issues))} (offline)")

        video_date = d.get("video_date") or idx_entry.get("published_at")
        if not video_date:
            print("    no published_at in index — skipped"); skipped += 1; continue

        if not args.dry_run:
            _write_post_file(
                path, vid, d.get("title") or idx_entry.get("title", ""),
                body, video_date, category,
                topic_id=topic_id if "discourse_topic_id" in d else None,
                recovered_at=d.get("recovered_at"),
                normalized_at=time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
            )
        fixed += 1
        if (api_needed or api_calls_made) and i < len(queue):
            time.sleep(0.25)

    suffix = " (dry run)" if args.dry_run else ""
    print(f"Normalized {fixed} post file(s), skipped {skipped}{suffix}.")
    remaining = len(targets) - len(queue)
    if remaining:
        print(f"{remaining} record(s) not attempted this run — re-run to continue.")

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
    nm = sub.add_parser("normalize", help="Bring legacy post files up to the canonical schema")
    nm.add_argument("--config", default=None, help="config.json (needed for HTML bodies and categories)")
    nm.add_argument("--limit", type=int, default=0, help="0 = no limit")
    nm.add_argument("--verify-categories", action="store_true",
                    help="Re-check stored categories against Discourse per topic "
                         "(slow; the bulk map only covers part of the forum)")
    tx = sub.add_parser("transcripts", help="Recover missing transcripts from YouTube")
    tx.add_argument("--limit", type=int, default=5)

    args = p.parse_args()
    cmds = {"report": cmd_report, "schema": cmd_schema, "rename": cmd_rename,
            "cleanup": cmd_cleanup, "timestamps": cmd_timestamps,
            "posts": cmd_posts, "normalize": cmd_normalize,
            "transcripts": cmd_transcripts}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
