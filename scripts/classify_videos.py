#!/usr/bin/env python3
"""
Curated per-video classification: video_classification.json (committed).

The regex taxonomy in analyze_content.py tags from whole transcripts, so a
40-minute video that once says "review" or "solo" carries the tag: 672 of 1001
videos were "overview", 628 "solo". It also only finds a primary game when the
title matches a narrow pattern (507 videos had none). Neither is usable for
"which content approaches work". This file holds one judged record per video —
subject, format, lane, theme, solo focus, series — written by Claude from the
title and post summary, and validated here against closed vocabularies.

analyze_content.py reads it and lets it override the heuristic fields;
build_insights.py and build_showcase.py rely on it.

Usage:
    # what still needs classifying (JSON rows: id, date, minutes, title, summary)
    python3 scripts/classify_videos.py missing --index video_index.json [--out rows.json]

    # merge new records (an object mapping video id -> record), validating first
    python3 scripts/classify_videos.py apply records.json

    # check the committed file
    python3 scripts/classify_videos.py validate
"""

import argparse
import json
import os
import re
import sys

CLASSIFICATION_PATH = "video_classification.json"

VOCAB = {
    "subject_type": ["boardgame", "rpg", "gamebook", "videogame", "book", "screen",
                     "hobby", "multi"],
    "format": ["review", "first-look", "crowdfund", "playthrough", "top-list", "guide",
               "discussion", "interview", "channel"],
    "lane": ["dungeon-crawler", "adventure-game", "solo-rpg", "group-rpg", "gamebook",
             "wargame", "other-boardgame", "videogame", "books-screen", "hobby-meta"],
    "theme": ["fantasy", "horror", "sci-fi", "post-apocalyptic", "western", "historical",
              "modern", "mixed", "none"],
}

FIELDS = ["subject", "franchise", "subject_type", "format", "lane", "theme", "solo",
          "series", "part"]

# Human labels, shared by the dashboards.
FORMAT_LABELS = {
    "review": "Review", "first-look": "First look", "crowdfund": "Crowdfund preview",
    "playthrough": "Playthrough", "top-list": "Top list", "guide": "Guide",
    "discussion": "Discussion", "interview": "Interview", "channel": "Channel / live",
}
LANE_LABELS = {
    "dungeon-crawler": "Dungeon crawlers", "adventure-game": "Adventure games",
    "solo-rpg": "Solo RPGs", "group-rpg": "Group RPGs", "gamebook": "Gamebooks",
    "wargame": "Wargames & skirmish", "other-boardgame": "Other board games",
    "videogame": "Video games", "books-screen": "Books & screen",
    "hobby-meta": "Hobby & channel",
}

SPEC = """Classify each video from its title and summary. One record per video id:
- subject: the single game/book/product the video is about (parent game for
  expansions; standalone family members keep their own name); null for top lists,
  genre talk, multi-game comparisons, channel/hobby videos. Reuse the spelling
  already used in video_classification.json for the same subject.
- franchise: the broader product line, else the subject; null when subject is null.
- subject_type: {subject_type}
- format (exactly one): {format}
  review = verdict on one product; first-look = overview/unboxing/first impressions;
  crowdfund = preview of an upcoming crowdfunded game; playthrough = let's play /
  session report; top-list = ranked or curated list; guide = how-to / tutorial /
  "ultimate guide" / buyer's guide; discussion = essay / opinion / comparison;
  interview = guest conversation; channel = channel update / livestream / Q&A.
- lane (exactly one): {lane}
- theme: {theme}
- solo: true when solo play is central to the video.
- series: name of a recurring multi-part series or named show, same spelling for
  every episode; null for standalone videos.
- part: integer part/episode number when the title gives one, else null.
""".format(**{k: " | ".join(v) for k, v in VOCAB.items()})


def load_classification(path=CLASSIFICATION_PATH):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    return data.get("videos", {})


def save_classification(videos, path=CLASSIFICATION_PATH):
    data = {
        "about": "Curated per-video classification. Validated by "
                 "scripts/classify_videos.py; read by analyze_content.py, "
                 "build_insights.py and build_showcase.py.",
        "vocab": VOCAB,
        "videos": {vid: {k: videos[vid].get(k) for k in FIELDS}
                   for vid in sorted(videos)},
    }
    # One record per line: a reclassification diffs as one changed line.
    lines = ["{"]
    lines.append(' "about": {},'.format(json.dumps(data["about"], ensure_ascii=False)))
    lines.append(' "vocab": {},'.format(json.dumps(data["vocab"], ensure_ascii=False)))
    lines.append(' "videos": {')
    items = list(data["videos"].items())
    for i, (vid, rec) in enumerate(items):
        lines.append("  {}: {}{}".format(json.dumps(vid), json.dumps(rec, ensure_ascii=False),
                                         "," if i < len(items) - 1 else ""))
    lines.append(" }")
    lines.append("}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def validate_record(vid, rec):
    errors = []
    if not isinstance(rec, dict):
        return ["{}: record is not an object".format(vid)]
    missing = [k for k in FIELDS if k not in rec]
    if missing:
        errors.append("{}: missing {}".format(vid, ", ".join(missing)))
    for field, allowed in VOCAB.items():
        if rec.get(field) not in allowed:
            errors.append("{}: {}={!r} not in vocabulary".format(vid, field, rec.get(field)))
    if not isinstance(rec.get("solo"), bool):
        errors.append("{}: solo must be true/false".format(vid))
    part = rec.get("part")
    if part is not None and not (isinstance(part, int) and not isinstance(part, bool)):
        errors.append("{}: part must be an integer or null".format(vid))
    for field in ("subject", "franchise", "series"):
        val = rec.get(field)
        if val is not None and (not isinstance(val, str) or not val.strip()):
            errors.append("{}: {} must be a non-empty string or null".format(vid, field))
    return errors


def _summary_excerpt(vid, posts_dir, words=85):
    path = os.path.join(posts_dir, "{}_post.json".format(vid))
    if not os.path.exists(path):
        return ""
    try:
        with open(path) as f:
            body = json.load(f).get("body", "")
    except (json.JSONDecodeError, OSError):
        return ""
    body = re.sub(r"^https?://\S+\s*", "", body.strip()).split("----")[0]
    return " ".join(body.split()[:words])


def cmd_missing(args):
    with open(args.index) as f:
        videos = json.load(f).get("videos", [])
    stats = {}
    if os.path.exists(args.stats):
        with open(args.stats) as f:
            stats = json.load(f).get("stats", {})
    have = load_classification(args.classification)
    rows = []
    for v in sorted(videos, key=lambda x: x.get("published_at", "")):
        vid = v["video_id"]
        if vid in have:
            continue
        dur = stats.get(vid, {}).get("duration_seconds")
        rows.append({
            "id": vid,
            "date": v.get("published_at", "")[:10],
            "minutes": round(dur / 60) if dur else None,
            "title": v.get("title", ""),
            "summary": _summary_excerpt(vid, args.posts_dir),
        })
    if args.out:
        with open(args.out, "w") as f:
            json.dump(rows, f, indent=1, ensure_ascii=False)
        print("{} unclassified videos written to {}".format(len(rows), args.out))
    else:
        print(json.dumps(rows, indent=1, ensure_ascii=False))
    if rows and args.out:
        print("\nClassification spec:\n" + SPEC)
    return 0


def cmd_apply(args):
    with open(args.records) as f:
        records = json.load(f)
    if not isinstance(records, dict):
        print("ERROR: expected an object mapping video id -> record")
        return 1
    errors = []
    for vid, rec in records.items():
        errors.extend(validate_record(vid, rec))
    if errors:
        print("REFUSING TO APPLY — {} problem(s):".format(len(errors)))
        for e in errors[:50]:
            print("  -", e)
        return 1
    videos = load_classification(args.classification)
    added = sum(1 for vid in records if vid not in videos)
    videos.update(records)
    save_classification(videos, args.classification)
    print("Applied {} records ({} new, {} replaced) → {} ({} total)".format(
        len(records), added, len(records) - added, args.classification, len(videos)))
    return 0


def cmd_validate(args):
    videos = load_classification(args.classification)
    errors = []
    for vid, rec in videos.items():
        errors.extend(validate_record(vid, rec))
    if errors:
        print("{} problem(s):".format(len(errors)))
        for e in errors[:50]:
            print("  -", e)
        return 1
    print("{}: {} records, all valid".format(args.classification, len(videos)))
    return 0


def main():
    p = argparse.ArgumentParser(description="Curated video classification")
    p.add_argument("--classification", default=CLASSIFICATION_PATH)
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("missing", help="list videos without a classification")
    m.add_argument("--index", default="video_index.json")
    m.add_argument("--stats", default="youtube_stats.json")
    m.add_argument("--posts-dir", default="archive/posts")
    m.add_argument("--out", help="write rows to this file instead of stdout")
    a = sub.add_parser("apply", help="validate and merge records")
    a.add_argument("records")
    sub.add_parser("validate", help="validate the committed file")
    sub.add_parser("spec", help="print the classification rules")
    args = p.parse_args()
    if args.cmd == "missing":
        return cmd_missing(args)
    if args.cmd == "apply":
        return cmd_apply(args)
    if args.cmd == "spec":
        print(SPEC)
        return 0
    return cmd_validate(args)


if __name__ == "__main__":
    sys.exit(main())
