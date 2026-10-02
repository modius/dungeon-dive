#!/usr/bin/env python3
"""
Committed view-count history for every channel video.

youtube_stats.json is a single overwritten snapshot, so on its own it can say how
many views a video has but never how fast it is gaining them. This module keeps
a thinned time series in stats_history/YYYY-MM.csv (committed) so the dashboards
can measure launch curves (views at day 7 / 30) and evergreen pull (views gained
per day by old videos), which are the age-fair performance signals.

Rows: date,video_id,views,likes,comments  (likes/comments empty for backfilled rows)

Thinning policy — keeps the history small enough to commit:
  * a video younger than DAILY_WINDOW_DAYS gets a row every snapshot (launch curve)
  * an older video gets a row when its last kept row is >= WEEKLY_GAP_DAYS old

Usage:
    python3 scripts/stats_history.py snapshot --stats youtube_stats.json --index video_index.json
    python3 scripts/stats_history.py backfill --index video_index.json --stats youtube_stats.json
    python3 scripts/stats_history.py summary
"""

import argparse
import csv
import glob
import itertools
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

HISTORY_DIR = "stats_history"
DAILY_WINDOW_DAYS = 90
WEEKLY_GAP_DAYS = 7
FIELDS = ["date", "video_id", "views", "likes", "comments"]


def _d(s):
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


# ── Reading ────────────────────────────────────────────────────────

def load_history(history_dir=HISTORY_DIR):
    """Return {video_id: [(date, views, likes, comments), ...]} sorted by date.

    likes/comments are None where the row did not record them (backfill).
    """
    series = defaultdict(list)
    for path in sorted(glob.glob(os.path.join(history_dir, "*.csv"))):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                try:
                    views = int(row["views"])
                except (TypeError, ValueError):
                    continue
                likes = int(row["likes"]) if row.get("likes") else None
                comments = int(row["comments"]) if row.get("comments") else None
                series[row["video_id"]].append((_d(row["date"]), views, likes, comments))
    for rows in series.values():
        rows.sort(key=lambda r: r[0])
    return dict(series)


def views_at(rows, when):
    """Views on `when`, linearly interpolated between the bracketing rows.

    Returns None when `when` falls outside the recorded span — extrapolating a
    view curve is exactly the guess this history exists to avoid.
    """
    if not rows or when < rows[0][0] or when > rows[-1][0]:
        return None
    prev = rows[0]
    for r in rows:
        if r[0] == when:
            return r[1]
        if r[0] > when:
            span = (r[0] - prev[0]).days
            if span <= 0:
                return r[1]
            frac = (when - prev[0]).days / span
            return round(prev[1] + (r[1] - prev[1]) * frac)
        prev = r
    return rows[-1][1]


def daily_gain(rows, end, window_days):
    """Average views gained per day over the `window_days` ending at `end`.

    Uses the nearest recorded rows inside the window rather than requiring exact
    dates; needs at least half the window covered to answer.
    """
    if not rows:
        return None
    start = end - timedelta(days=window_days)
    inside = [r for r in rows if start <= r[0] <= end]
    if len(inside) < 2:
        return None
    first, last = inside[0], inside[-1]
    span = (last[0] - first[0]).days
    if span < window_days / 2:
        return None
    return max(0.0, (last[1] - first[1]) / span)


# ── Writing ────────────────────────────────────────────────────────

def _month_path(history_dir, d):
    return os.path.join(history_dir, "{:%Y-%m}.csv".format(d))


def _write_month(path, rows):
    rows = sorted(rows, key=lambda r: (r["date"], r["video_id"]))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in FIELDS})


def _read_month(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def select_rows(snapshot_date, values, published, last_kept):
    """Apply the thinning policy to one snapshot.

    values: {video_id: (views, likes, comments)}
    published: {video_id: date}
    last_kept: {video_id: date of the last row kept before snapshot_date}
    """
    out = []
    for vid, (views, likes, comments) in sorted(values.items()):
        pub = published.get(vid)
        if pub is None or pub > snapshot_date:
            continue
        young = (snapshot_date - pub).days < DAILY_WINDOW_DAYS
        prev = last_kept.get(vid)
        if young or prev is None or (snapshot_date - prev).days >= WEEKLY_GAP_DAYS:
            out.append({"date": snapshot_date.isoformat(), "video_id": vid,
                        "views": views, "likes": likes, "comments": comments})
    return out


def _published_lookup(index_path):
    with open(index_path) as f:
        videos = json.load(f).get("videos", [])
    return {v["video_id"]: _d(v["published_at"]) for v in videos if v.get("published_at")}


def snapshot(stats_path, index_path, history_dir=HISTORY_DIR):
    """Record today's youtube_stats.json into the history (idempotent per date)."""
    with open(stats_path) as f:
        stats = json.load(f)
    fetched = stats.get("last_fetched")
    if not fetched:
        print("ERROR: {} has no last_fetched — run fetch_youtube_stats.py first".format(stats_path))
        return 1
    snap_date = _d(fetched)
    published = _published_lookup(index_path)
    values = {
        vid: (s.get("view_count", 0), s.get("like_count"), s.get("comment_count"))
        for vid, s in stats.get("stats", {}).items()
    }

    history = load_history(history_dir)
    last_kept = {}
    for vid, rows in history.items():
        before = [r[0] for r in rows if r[0] < snap_date]
        if before:
            last_kept[vid] = before[-1]

    new_rows = select_rows(snap_date, values, published, last_kept)
    path = _month_path(history_dir, snap_date)
    kept = [r for r in _read_month(path) if r["date"] != snap_date.isoformat()]
    _write_month(path, kept + new_rows)
    print("Snapshot {}: {} rows written to {} ({} videos in stats)".format(
        snap_date, len(new_rows), path, len(values)))
    return 0


# ── Backfill from git history ──────────────────────────────────────

TRENDS_RE = re.compile(r"const engagementTrends = (\[.*?\]);", re.S)


def _git(*args):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True,
                          check=True).stdout


def backfill(index_path, stats_path, dashboard="docs/insights.html",
             history_dir=HISTORY_DIR):
    """Rebuild a view history from every committed version of insights.html.

    Each nightly /refresh committed `engagementTrends` — [publish_date, views]
    for every video — so the git log of insights.html is a near-daily record of
    the whole channel from 2026-04-09 on. The pairs carry no video id: a date
    with one video maps directly, and the few dates with several uploads are
    resolved by continuity, walking back from today's known values and choosing
    the assignment closest to the next-newer snapshot.
    """
    published = _published_lookup(index_path)
    by_date = defaultdict(list)
    for vid, d in published.items():
        by_date[d.isoformat()].append(vid)

    # Commit times in UTC: youtube_stats.json's last_fetched is UTC, and the
    # nightly and local refreshes commit from different timezones.
    log = _git("log", "--format=%H %ct", "--", dashboard).split("\n")
    commits = []
    for line in log:
        if line.strip():
            sha, ts = line.split(" ", 1)
            commits.append((sha, datetime.fromtimestamp(int(ts), timezone.utc).date()))
    commits.reverse()  # oldest first

    # Keep the last commit per day; parse its trends.
    per_day = {}
    for sha, d in commits:
        per_day[d] = sha
    snapshots = []
    prev_total = None
    prev_pairs = None
    for d in sorted(per_day):
        text = _git("show", "{}:{}".format(per_day[d], dashboard))
        m = TRENDS_RE.search(text)
        if not m:
            continue
        try:
            pairs = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if not pairs:
            continue
        total = sum(p[1] for p in pairs)
        # A rebuild from stale local stats either repeats the previous snapshot
        # or reports fewer views than it; neither is a new observation.
        if pairs == prev_pairs or (prev_total is not None and total < prev_total):
            continue
        prev_total, prev_pairs = total, pairs
        snapshots.append((d, pairs))

    # Current values anchor the continuity walk.
    with open(stats_path) as f:
        current = {vid: s.get("view_count", 0)
                   for vid, s in json.load(f).get("stats", {}).items()}

    resolved = {}  # date -> {vid: views}
    later = dict(current)
    ambiguous_groups = 0
    for d, pairs in reversed(snapshots):
        grouped = defaultdict(list)
        for pub, views in pairs:
            grouped[pub].append(views)
        values = {}
        for pub, views_list in grouped.items():
            vids = [v for v in by_date.get(pub, []) if v in later or v in current]
            if len(vids) != len(views_list):
                continue
            if len(vids) == 1:
                values[vids[0]] = views_list[0]
                continue
            ambiguous_groups += 1
            if len(vids) > 6:
                continue
            ref = [later.get(v, current.get(v, 0)) for v in vids]
            best = min(itertools.permutations(views_list),
                       key=lambda perm: sum(abs(a - b) for a, b in zip(perm, ref)))
            values.update(dict(zip(vids, best)))
        resolved[d] = values
        later.update(values)

    # Apply the thinning policy forward in time.
    out_by_month = defaultdict(list)
    last_kept = {}
    for d in sorted(resolved):
        rows = select_rows(d, {v: (n, None, None) for v, n in resolved[d].items()},
                           published, last_kept)
        for r in rows:
            last_kept[r["video_id"]] = d
            out_by_month[_month_path(history_dir, d)].append(r)

    for path, rows in out_by_month.items():
        existing = _read_month(path)
        have = {(r["date"], r["video_id"]) for r in rows}
        merged = [r for r in existing if (r["date"], r["video_id"]) not in have] + rows
        _write_month(path, merged)
    total_rows = sum(len(r) for r in out_by_month.values())
    print("Backfilled {} snapshots ({} → {}) into {} rows across {} files; "
          "{} same-day upload groups resolved by continuity".format(
              len(resolved), min(resolved) if resolved else "-",
              max(resolved) if resolved else "-", total_rows, len(out_by_month),
              ambiguous_groups))
    return 0


def summary(history_dir=HISTORY_DIR):
    history = load_history(history_dir)
    dates = sorted({r[0] for rows in history.values() for r in rows})
    rows = sum(len(r) for r in history.values())
    if not dates:
        print("No history in {}".format(history_dir))
        return 0
    print("{} videos, {} rows, {} snapshot dates ({} → {})".format(
        len(history), rows, len(dates), dates[0], dates[-1]))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot", help="record youtube_stats.json into the history")
    s.add_argument("--stats", default="youtube_stats.json")
    s.add_argument("--index", default="video_index.json")
    s.add_argument("--history-dir", default=HISTORY_DIR)
    b = sub.add_parser("backfill", help="rebuild history from git log of insights.html")
    b.add_argument("--stats", default="youtube_stats.json")
    b.add_argument("--index", default="video_index.json")
    b.add_argument("--dashboard", default="docs/insights.html")
    b.add_argument("--history-dir", default=HISTORY_DIR)
    m = sub.add_parser("summary", help="print history coverage")
    m.add_argument("--history-dir", default=HISTORY_DIR)
    args = p.parse_args()

    if args.cmd == "snapshot":
        return snapshot(args.stats, args.index, args.history_dir)
    if args.cmd == "backfill":
        return backfill(args.index, args.stats, args.dashboard, args.history_dir)
    return summary(args.history_dir)


if __name__ == "__main__":
    sys.exit(main())
