#!/usr/bin/env python3
"""
Shared loading and metrics for the channel dashboards (insights, showcase).

Everything here is inference from public data — view, like and comment counts,
durations, titles, transcripts, and the committed view history. There is no
YouTube Analytics access (no impressions, CTR or retention), so the metrics are
built to be fair without them:

* breakout ratio — a video's views divided by the median of the ~20 uploads
  published around it. Neighbours share its age and the channel's size at the
  time, so the ratio cancels both the old-video head start and channel growth,
  and a median baseline is not dragged around by the occasional 200k hit.
* evergreen rate — views gained per day over the last 90 days by videos more
  than a year old: what the back catalogue still earns from search and
  recommendations today.
* launch curve — views at day N after publish, from stats_history/.
"""

import json
import math
import os
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import stats_history
from classify_videos import FORMAT_LABELS, LANE_LABELS, load_classification

MATURE_DAYS = 60        # a video's views are compared only once it is this old
NEIGHBOURS = 20         # breakout baseline: median of this many nearby uploads
EVERGREEN_MIN_AGE = 365
EVERGREEN_WINDOW = 90
LAUNCH_DAYS = [1, 2, 3, 7, 14, 30, 60, 90]
LAUNCH_MAX_FIRST_GAP = 3

FORUM_URL = "https://dungeondive.quest/t/{}"
YOUTUBE_URL = "https://www.youtube.com/watch?v={}"


def load_json(path):
    if not path or not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _date(s):
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def median(values):
    s = sorted(values)
    n = len(s)
    if not n:
        return None
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def percentile(values, p):
    s = sorted(values)
    if not s:
        return None
    k = (len(s) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return s[int(k)]
    return s[lo] * (hi - k) + s[hi] * (k - lo)


def median_ci(values, level=0.8, iters=1000, seed=7):
    """Bootstrap interval for the median. Seeded, so nightly output is stable."""
    if len(values) < 3:
        return None, None
    rng = random.Random(seed)
    n = len(values)
    meds = sorted(median([values[rng.randrange(n)] for _ in range(n)])
                  for _ in range(iters))
    tail = (1 - level) / 2
    return meds[int(tail * iters)], meds[min(iters - 1, int((1 - tail) * iters))]


def load_videos(index_path="video_index.json", stats_path="youtube_stats.json",
                analytics_path="transcript_analytics.json",
                classification_path="video_classification.json",
                history_dir=stats_history.HISTORY_DIR):
    """Merge every data source into one record per video, oldest first.

    `today` is the stats fetch date, not the wall clock, so a rebuild from the
    same data produces the same page.
    """
    index = load_json(index_path) or {}
    stats_doc = load_json(stats_path) or {}
    stats = stats_doc.get("stats", {})
    analytics = {v["video_id"]: v for v in (load_json(analytics_path) or {}).get("videos", [])}
    curated = load_classification(classification_path)
    history = stats_history.load_history(history_dir) if os.path.isdir(history_dir) else {}

    fetched = stats_doc.get("last_fetched")
    today = _date(fetched) if fetched else datetime.now(timezone.utc).date()

    videos = []
    for v in index.get("videos", []):
        vid = v["video_id"]
        if not v.get("published_at"):
            continue
        s = stats.get(vid, {})
        pub = _date(v["published_at"])
        videos.append({
            "id": vid,
            "title": v.get("title", ""),
            "date": pub,
            "status": v.get("status"),
            "topic": v.get("discourse_topic_id"),
            "has_stats": vid in stats,
            "views": s.get("view_count", 0) or 0,
            "likes": s.get("like_count", 0) or 0,
            "comments": s.get("comment_count", 0) or 0,
            "duration": s.get("duration_seconds", 0) or 0,
            "cls": curated.get(vid) or {},
            "tags": analytics.get(vid) or {},
            "history": history.get(vid, []),
            "age": (today - pub).days,
        })
    videos.sort(key=lambda x: (x["date"], x["id"]))
    annotate(videos, today)
    return videos, today


def annotate(videos, today):
    """Attach ratio, evergreen and launch metrics in place."""
    # Livestreams and premieres with no recorded views would sit in the baseline
    # as zeros; leave them out of it.
    pool = [v for v in videos if v["has_stats"] and v["views"] > 0
            and v["age"] >= MATURE_DAYS]
    half = NEIGHBOURS // 2
    for i, v in enumerate(pool):
        lo = max(0, i - half)
        hi = min(len(pool), lo + NEIGHBOURS + 1)
        lo = max(0, hi - NEIGHBOURS - 1)
        base = median([p["views"] for p in pool[lo:hi] if p is not v])
        v["baseline"] = base
        v["ratio"] = v["views"] / base if base else None
    for v in videos:
        v.setdefault("ratio", None)
        v.setdefault("baseline", None)
        v["like_rate"] = v["likes"] / v["views"] if v["views"] >= 300 else None
        v["comment_rate"] = v["comments"] / v["views"] if v["views"] >= 300 else None
        v["evergreen"] = None
        if v["age"] >= EVERGREEN_MIN_AGE and v["history"]:
            v["evergreen"] = stats_history.daily_gain(v["history"], today, EVERGREEN_WINDOW)
        v["launch"] = launch_points(v)


def launch_points(v):
    """{day: views} for the launch days the history covers, else {}."""
    rows = v["history"]
    # A video enters the history when it enters video_index.json (at the next
    # /import's channel fetch), so the first row can trail publishing by a day
    # or two. Days before the first row are simply absent, never extrapolated.
    if not rows or (rows[0][0] - v["date"]).days > LAUNCH_MAX_FIRST_GAP:
        return {}
    out = {}
    for day in LAUNCH_DAYS:
        when = v["date"] + timedelta(days=day)
        val = stats_history.views_at(rows, when)
        if val is not None:
            out[day] = val
    return out


# ── Small helpers for the page payloads ────────────────────────────

def ref(v, **extra):
    """Compact reference to a video for the page: links + headline numbers."""
    out = {
        "id": v["id"],
        "title": v["title"],
        "date": v["date"].isoformat(),
        "views": v["views"],
        "topic": v["topic"],
    }
    if v.get("ratio") is not None:
        out["ratio"] = round(v["ratio"], 2)
    out.update(extra)
    return out


def duration_bucket(seconds):
    m = seconds / 60
    if m < 15:
        return "under 15 min"
    if m < 30:
        return "15–30 min"
    if m < 60:
        return "30–60 min"
    return "60+ min"


DURATION_ORDER = ["under 15 min", "15–30 min", "30–60 min", "60+ min"]


def group_ratios(videos, keyfn, min_n=1):
    """Median breakout ratio (with IQR and an 80% bootstrap CI) per key."""
    groups = defaultdict(list)
    for v in videos:
        if v.get("ratio") is None:
            continue
        k = keyfn(v)
        if k is None:
            continue
        groups[k].append(v)
    out = {}
    for k, vs in groups.items():
        if len(vs) < min_n:
            continue
        ratios = [x["ratio"] for x in vs]
        lo, hi = median_ci(ratios)
        out[k] = {
            "n": len(vs),
            "median": round(median(ratios), 3),
            "p25": round(percentile(ratios, 25), 3),
            "p75": round(percentile(ratios, 75), 3),
            "ci": [round(lo, 3), round(hi, 3)] if lo is not None else None,
            "median_views": int(median([x["views"] for x in vs])),
            "videos": vs,
        }
    return out


TITLE_PATTERNS = [
    ("guide", "“Guide” in the title", re.compile(r"\bguide\b", re.I)),
    ("top-n", "“Top N” / “Best” list title", re.compile(r"\btop\s+\d+|\bbest\b", re.I)),
    ("edition", "Dated edition (“2024 edition”)", re.compile(r"\b(?:19|20)\d\d\b.*\bedition\b|\bedition\b.*\b(?:19|20)\d\d\b", re.I)),
    ("question", "Question in the title", re.compile(r"\?")),
    ("part", "Numbered part (“Part 2”, “Episode 3”)", re.compile(r"\b(?:part|episode|ep\.?|session)\s*(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b", re.I)),
    ("review-word", "“Review” in the title", re.compile(r"\breview\b", re.I)),
    ("first-person", "First person (“I”, “my”)", re.compile(r"\b(?:I|I'm|I've|my|me)\b")),
    ("solo-word", "“Solo” in the title", re.compile(r"\bsolo\b", re.I)),
]


LANE_NOUNS = {
    "dungeon-crawler": "dungeon crawler", "adventure-game": "adventure game",
    "solo-rpg": "solo RPG", "group-rpg": "group RPG", "gamebook": "gamebook",
    "wargame": "wargame", "other-boardgame": "board game", "videogame": "video game",
    "books-screen": "book or screen", "hobby-meta": "hobby",
}


def lane_noun(key):
    return LANE_NOUNS.get(key, key or "unclassified")


def full_snapshot_dates(videos, share=0.5):
    """Dates on which at least `share` of tracked videos got a history row.

    Old videos are recorded weekly, so only these dates have the whole channel;
    a span ending between them would silently count only the young videos.
    """
    from collections import Counter
    tracked = sum(1 for v in videos if v["history"])
    counts = Counter(r[0] for v in videos for r in v["history"])
    return sorted(d for d, n in counts.items() if tracked and n >= share * tracked)


def fmt_label(key):
    return FORMAT_LABELS.get(key, key or "Unclassified")


def lane_label(key):
    return LANE_LABELS.get(key, key or "Unclassified")
