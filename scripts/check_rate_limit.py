#!/usr/bin/env python3
"""
Check if we've exceeded the daily sync run limit.

Counts batch result files from the last 24 hours.
Exits 0 if under limit, exits 1 if at or over limit.

Usage:
    python3 scripts/check_rate_limit.py
    python3 scripts/check_rate_limit.py --max-runs 2
    python3 scripts/check_rate_limit.py --max-runs 3 --hours 24
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone, timedelta


def main():
    parser = argparse.ArgumentParser(description="Check daily sync rate limit")
    parser.add_argument("--max-runs", type=int, default=2, help="Max sync runs per period (default: 2)")
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

    print(f"Sync runs in last {args.hours}h: {len(recent_runs)} (limit: {args.max_runs})")
    for run in recent_runs:
        print(f"  {run['date']} — {run['videos']} videos ({run['file']})")

    if len(recent_runs) >= args.max_runs:
        print(f"\nRate limit reached. Skipping this run.")
        sys.exit(1)
    else:
        remaining = args.max_runs - len(recent_runs)
        print(f"\n{remaining} run(s) remaining in this period. Proceeding.")
        sys.exit(0)


if __name__ == "__main__":
    main()
