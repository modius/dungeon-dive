#!/usr/bin/env python3
"""
Check if we've exceeded the daily transcript-fetch quota.

Sums the number of videos posted across all batch result files in the last 24
hours. Exits 0 if under limit, exits 1 if at or over limit.

The video count is the meaningful signal — a 1-video priority drop should not
burn the same quota as a 12-video archive drain. The underlying constraint is
YouTube's transcript-API IP throttle (~12-15 fetches before a ~1h backoff), so
the limit is expressed in videos per 24h rather than runs.

Usage:
    python3 scripts/check_rate_limit.py
    python3 scripts/check_rate_limit.py --max-videos 20
    python3 scripts/check_rate_limit.py --max-videos 24 --hours 24
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone, timedelta


def main():
    parser = argparse.ArgumentParser(description="Check daily transcript-fetch video quota")
    parser.add_argument("--max-videos", type=int, default=20, help="Max videos posted per period (default: 20)")
    parser.add_argument("--hours", type=int, default=24, help="Period in hours (default: 24)")
    parser.add_argument("--results-dir", default="archive/posts", help="Directory containing post_results_*.json")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    recent_runs = []

    for path in glob.glob(os.path.join(args.results_dir, "post_results_*.json")):
        try:
            with open(path) as f:
                data = json.load(f)
            posted_at = data.get("posted_at", "")
            if posted_at:
                ts = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
                if ts >= cutoff:
                    count = len(data.get("results", []))
                    recent_runs.append({"file": os.path.basename(path), "date": posted_at[:16], "videos": count})
        except (json.JSONDecodeError, ValueError, KeyError):
            continue

    recent_runs.sort(key=lambda r: r["date"])
    total_videos = sum(r["videos"] for r in recent_runs)

    print(f"Videos posted in last {args.hours}h: {total_videos} (limit: {args.max_videos}) across {len(recent_runs)} run(s)")
    for run in recent_runs:
        print(f"  {run['date']} — {run['videos']} videos ({run['file']})")

    if total_videos >= args.max_videos:
        print(f"\nRate limit reached. Skipping this run.")
        sys.exit(1)
    else:
        remaining = args.max_videos - total_videos
        print(f"\n{remaining} video(s) of headroom remaining in this period. Proceeding.")
        sys.exit(0)


if __name__ == "__main__":
    main()
