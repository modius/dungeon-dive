#!/usr/bin/env python3
"""
Build docs/content.html — a showcase of The Dungeon Dive over the years.

Anecdotes drawn from the archive rather than taxonomy counts: a card per year
(defining video, biggest breakout, most-covered subject, firsts), records,
long-running obsessions, hidden gems, how the channel's lanes shifted, Daniel's
on-camera rituals and vocabulary from the transcripts, multi-part sagas, and
games that travel together. Every video links to YouTube and its forum topic.

Inputs: video_index.json, youtube_stats.json, transcript_analytics.json,
video_classification.json, stats_history/, archive/transcripts/.

Usage:
    python3 scripts/build_showcase.py [--dashboard docs/content.html] [--dry-run]
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

import dashboard_data as dd
import stats_history

DATA_RE = re.compile(r"(// @showcase-data-begin\n).*?(\n// @showcase-data-end)", re.S)

# Lanes folded to eight groups for stacked charts (one categorical slot each).
LANE_GROUPS = [
    ("dungeon-crawler", "Dungeon crawlers", {"dungeon-crawler"}),
    ("adventure-game", "Adventure games", {"adventure-game"}),
    ("solo-rpg", "Solo RPGs & gamebooks", {"solo-rpg", "gamebook"}),
    ("group-rpg", "Group RPGs", {"group-rpg"}),
    ("wargame", "Wargames & skirmish", {"wargame"}),
    ("videogame", "Video games", {"videogame"}),
    ("books-screen", "Books & screen", {"books-screen"}),
    ("other", "Other board games & hobby", {"other-boardgame", "hobby-meta"}),
]
FORMAT_GROUPS = [
    ("review", "Reviews", {"review"}),
    ("first-look", "First looks", {"first-look"}),
    ("playthrough", "Playthroughs", {"playthrough"}),
    ("discussion", "Discussions", {"discussion"}),
    ("top-list", "Top lists", {"top-list"}),
    ("guide", "Guides", {"guide"}),
    ("crowdfund", "Crowdfund previews", {"crowdfund"}),
    ("other", "Interviews & channel", {"interview", "channel"}),
]

# Daniel's on-camera rituals and the vocabulary that tracks the channel's
# interests, matched against lower-cased transcripts reduced to plain words.
RITUALS = [
    ("hey-everybody", "“Hey everybody, welcome back…”", r"\bhey everybody\b"),
    ("hey-folks", "“Hey folks, welcome back…”", r"\bhey folks\b"),
    ("daniel-here", "“…Daniel here”", r"\bdaniel here\b"),
    ("hope-soon", "“…and if you're not, I hope you are soon”", r"if you're not i hope you are soon"),
    ("bye-bye", "“…talk to you later, bye bye”", r"talk to you later bye bye"),
]
VOCAB = [
    ("solo-rpg", "“solo RPG”", r"\bsolo rpgs?\b"),
    ("oracle", "“oracle”", r"\boracles?\b"),
    ("games-workshop", "“Games Workshop”", r"\bgames workshop\b"),
    ("kickstarter", "“Kickstarter”", r"\bkickstarter"),
]
FIRST_LANE_TEXT = {
    "solo-rpg": "First solo RPG video",
    "videogame": "First video game",
    "books-screen": "First book or screen video",
    "gamebook": "First gamebook",
    "group-rpg": "First group RPG video",
    "wargame": "First wargame",
}
FIRST_FORMAT_TEXT = {
    "interview": "First interview",
    "top-list": "First top list",
    "guide": "First guide",
    "crowdfund": "First crowdfund preview",
}
MILESTONE_COUNTS = [1, 100, 250, 500, 750, 1000, 1250, 1500]


def load_transcripts(transcripts_dir):
    out = {}
    if not os.path.isdir(transcripts_dir):
        return out
    for name in os.listdir(transcripts_dir):
        if not name.endswith("_transcript.txt"):
            continue
        with open(os.path.join(transcripts_dir, name), errors="ignore") as f:
            text = f.read().lower()
        out[name[:-len("_transcript.txt")]] = " ".join(re.findall(r"[a-z']+", text))
    return out


def subject_key(v):
    return v["cls"].get("franchise") or v["cls"].get("subject")


def build_totals(videos, transcripts):
    with_stats = [v for v in videos if v["has_stats"]]
    years = sorted({v["date"].year for v in videos})
    return {
        "videos": len(videos),
        "first_date": videos[0]["date"].isoformat() if videos else None,
        "years": (years[-1] - years[0] + 1) if years else 0,
        "hours": round(sum(v["duration"] for v in with_stats) / 3600),
        "views": sum(v["views"] for v in with_stats),
        "words": sum(len(transcripts[v["id"]].split()) for v in videos if v["id"] in transcripts),
        "transcripts": sum(1 for v in videos if v["id"] in transcripts),
        "forum_topics": sum(1 for v in videos if v["topic"]),
        "subjects": len({v["cls"].get("subject") for v in videos if v["cls"].get("subject")}),
    }


def build_years(videos, transcripts):
    by_year = defaultdict(list)
    for v in videos:
        by_year[v["date"].year].append(v)

    # Firsts: the first video in each lane / notable format.
    firsts = defaultdict(list)
    seen_lane, seen_fmt = set(), set()
    for v in videos:
        lane, fmt = v["cls"].get("lane"), v["cls"].get("format")
        if lane in FIRST_LANE_TEXT and lane not in seen_lane:
            seen_lane.add(lane)
            firsts[v["date"].year].append(dd.ref(v, what=FIRST_LANE_TEXT[lane]))
        if fmt in FIRST_FORMAT_TEXT and fmt not in seen_fmt:
            seen_fmt.add(fmt)
            firsts[v["date"].year].append(dd.ref(v, what=FIRST_FORMAT_TEXT[fmt]))

    seen_subjects = set()
    out = []
    for year in sorted(by_year):
        vs = by_year[year]
        stats = [v for v in vs if v["has_stats"]]
        top = max(stats, key=lambda v: v["views"]) if stats else None
        # The year's breakout is a second highlight, so never the most-watched again.
        rated = [v for v in vs if v.get("ratio") is not None and v is not top]
        breakout = max(rated, key=lambda v: v["ratio"]) if rated else None
        subjects = Counter(subject_key(v) for v in vs if subject_key(v))
        new_subjects = {k for k in subjects if k not in seen_subjects}
        seen_subjects.update(subjects)
        lanes = Counter()
        for v in vs:
            lane = v["cls"].get("lane")
            for key, _, members in LANE_GROUPS:
                if lane in members:
                    lanes[key] += 1
        top_subject = subjects.most_common(1)[0] if subjects else None
        out.append({
            "year": year,
            "videos": len(vs),
            "hours": round(sum(v["duration"] for v in stats) / 3600),
            "median_views": int(dd.median([v["views"] for v in stats])) if stats else None,
            "words": sum(len(transcripts[v["id"]].split()) for v in vs if v["id"] in transcripts),
            "top": dd.ref(top) if top else None,
            "breakout": dd.ref(breakout) if breakout and breakout["ratio"] >= 1.5 else None,
            "top_subject": {"name": top_subject[0], "count": top_subject[1]} if top_subject and top_subject[1] >= 3 else None,
            "new_subjects": len(new_subjects),
            "lanes": dict(lanes),
            "firsts": firsts.get(year, [])[:3],
        })
    return out


def build_milestones(videos, transcripts):
    out = []
    for i, v in enumerate(videos, start=1):
        if i in MILESTONE_COUNTS:
            out.append(dd.ref(v, what="Video #{:,}".format(i)))
    # When the rituals first appeared.
    for key, label, rx in RITUALS:
        if key in ("hey-folks", "hope-soon"):
            pat = re.compile(rx)
            first = next((v for v in videos if v["id"] in transcripts
                          and pat.search(transcripts[v["id"]])), None)
            if first:
                out.append(dd.ref(first, what="First " + label))
    # Busiest month and longest gap.
    months = Counter(v["date"].strftime("%Y-%m") for v in videos)
    if months:
        m, n = months.most_common(1)[0]
        out.append({"what": "Busiest month", "date": m + "-01", "text": "{} uploads in {}".format(n, m)})
    gaps = [(b["date"] - a["date"]).days for a, b in zip(videos, videos[1:])]
    if gaps:
        i = max(range(len(gaps)), key=gaps.__getitem__)
        out.append(dd.ref(videos[i + 1], what="Return after the longest break",
                          text="{} days after the previous upload".format(gaps[i])))
    out.sort(key=lambda m: m["date"])
    return out


def is_content(v):
    """Channel updates, giveaways and livestreams are loved by regulars, not content records."""
    return v["cls"].get("format") != "channel"


def build_records(videos):
    """One record per video: the channel's biggest hit would otherwise take four."""
    stats = [v for v in videos if v["has_stats"] and v["views"] > 0]
    if not stats:
        return []
    rec, used = [], set()

    def add(label, pool, key, value, best=max):
        pool = [v for v in pool if v["id"] not in used]
        if not pool:
            return
        v = best(pool, key=key)
        used.add(v["id"])
        rec.append(dd.ref(v, label=label, value=value(v)))

    add("Most viewed", stats, lambda v: v["views"], lambda v: "{:,} views".format(v["views"]))
    rated = [v for v in stats if v.get("ratio") is not None]
    add("Biggest breakout", rated, lambda v: v["ratio"],
        lambda v: "{:.0f}× the uploads around it".format(v["ratio"]))
    add("Most liked", stats, lambda v: v["likes"], lambda v: "{:,} likes".format(v["likes"]))
    add("Most commented", stats, lambda v: v["comments"],
        lambda v: "{:,} comments".format(v["comments"]))
    add("Best loved", [v for v in stats if v["views"] >= 1000 and v["like_rate"] and is_content(v)],
        lambda v: v["like_rate"], lambda v: "{:.1f}% of viewers liked it".format(v["like_rate"] * 100))
    add("Most talked about", [v for v in stats if v["views"] >= 1000 and v["comment_rate"] and is_content(v)],
        lambda v: v["comment_rate"], lambda v: "a comment for every {:.0f} views".format(1 / v["comment_rate"]))
    add("Longest", stats, lambda v: v["duration"],
        lambda v: "{}h {:02d}m".format(v["duration"] // 3600, v["duration"] % 3600 // 60))
    add("Oldest still working", [v for v in stats if v["evergreen"] and v["evergreen"] >= 10],
        lambda v: v["date"], lambda v: "{:.0f} views/day, {} years on".format(v["evergreen"], v["age"] // 365),
        best=min)
    return rec


def build_champions(videos):
    best = {}
    for v in videos:
        lane = v["cls"].get("lane")
        if not lane or not v["has_stats"]:
            continue
        if lane not in best or v["views"] > best[lane]["views"]:
            best[lane] = v
    out = [dd.ref(v, lane=dd.lane_label(lane)) for lane, v in best.items()]
    out.sort(key=lambda r: -r["views"])
    return out


def build_obsessions(videos, top_n=14):
    by = defaultdict(list)
    for v in videos:
        k = subject_key(v)
        if k:
            by[k].append(v)
    rows = []
    for name, vs in by.items():
        years = Counter(v["date"].year for v in vs)
        if len(years) < 3:
            continue
        rows.append({
            "name": name,
            "count": len(vs),
            "years": sorted(years.items()),
            "span": [min(years), max(years)],
            "first": dd.ref(vs[0]),
            "latest": dd.ref(vs[-1]),
            "views": sum(v["views"] for v in vs),
        })
    rows.sort(key=lambda r: (-len(r["years"]), -r["count"]))
    return rows[:top_n]


def build_mix(videos, groups, field):
    years = sorted({v["date"].year for v in videos})
    series = []
    for key, label, members in groups:
        counts = [sum(1 for v in videos if v["date"].year == y and v["cls"].get(field) in members)
                  for y in years]
        series.append({"key": key, "label": label, "counts": counts})
    unclassified = [sum(1 for v in videos if v["date"].year == y and not v["cls"]) for y in years]
    return {"years": years, "series": series, "unclassified": unclassified}


def build_gems(videos, n=10):
    pool = [v for v in videos if v["like_rate"] and v["age"] >= 90 and v["views"] >= 1000
            and v.get("ratio") is not None and v["ratio"] < 1 and is_content(v)]
    if not pool:
        return {"items": [], "channel_like_rate": None}
    channel = dd.median([v["like_rate"] for v in videos if v["like_rate"]])
    pool.sort(key=lambda v: -v["like_rate"])
    return {
        "channel_like_rate": round(channel, 4),
        "items": [dd.ref(v, like_rate=round(v["like_rate"], 4),
                         lane=dd.lane_label(v["cls"].get("lane"))) for v in pool[:n]],
    }


def build_phrases(videos, transcripts, defs):
    years = sorted({v["date"].year for v in videos if v["id"] in transcripts})
    n_by_year = Counter(v["date"].year for v in videos if v["id"] in transcripts)
    out = []
    for key, label, rx in defs:
        pat = re.compile(rx)
        hits = Counter()
        total = 0
        for v in videos:
            t = transcripts.get(v["id"])
            if t and pat.search(t):
                hits[v["date"].year] += 1
                total += 1
        out.append({"key": key, "label": label, "videos": total,
                    "share": [round(hits[y] / n_by_year[y], 3) if n_by_year[y] else None for y in years]})
    return {"years": years, "n": [n_by_year[y] for y in years], "terms": out}


def build_sagas(videos, n=10):
    by = defaultdict(list)
    for v in videos:
        s = v["cls"].get("series")
        if s:
            by[s].append(v)
    rows = []
    for name, vs in by.items():
        if len(vs) < 3:
            continue
        rows.append({
            "series": name,
            "parts": len(vs),
            "span": [vs[0]["date"].isoformat(), vs[-1]["date"].isoformat()],
            "views": sum(v["views"] for v in vs),
            "first": dd.ref(vs[0]),
        })
    rows.sort(key=lambda r: -r["parts"])
    return rows[:n]


def build_pairs(videos, n=14):
    pairs = Counter()
    for v in videos:
        games = sorted(set(v["tags"].get("games", [])))
        for i in range(len(games)):
            for j in range(i + 1, len(games)):
                pairs[(games[i], games[j])] += 1
    return [[a, b, c] for (a, b), c in pairs.most_common(n)]


def build(videos, today, transcripts):
    return {
        "generated": today.isoformat(),
        "totals": build_totals(videos, transcripts),
        "years": build_years(videos, transcripts),
        "milestones": build_milestones(videos, transcripts),
        "records": build_records(videos),
        "champions": build_champions(videos),
        "obsessions": build_obsessions(videos),
        "lane_mix": build_mix(videos, LANE_GROUPS, "lane"),
        "format_mix": build_mix(videos, FORMAT_GROUPS, "format"),
        "gems": build_gems(videos),
        "rituals": build_phrases(videos, transcripts, RITUALS),
        "vocab": build_phrases(videos, transcripts, VOCAB),
        "sagas": build_sagas(videos),
        "pairs": build_pairs(videos),
    }


def embed(html, data):
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    new, n = DATA_RE.subn(lambda m: m.group(1) + "const SHOWCASE = " + payload + ";" + m.group(2), html)
    if n != 1:
        raise SystemExit("ERROR: showcase data markers not found in dashboard template")
    return new


def main():
    p = argparse.ArgumentParser(description="Build docs/content.html (channel showcase)")
    p.add_argument("--index", default="video_index.json")
    p.add_argument("--stats", default="youtube_stats.json")
    p.add_argument("--analytics", default="transcript_analytics.json")
    p.add_argument("--classification", default="video_classification.json")
    p.add_argument("--history-dir", default=stats_history.HISTORY_DIR)
    p.add_argument("--transcripts-dir", default="archive/transcripts")
    p.add_argument("--dashboard", default="docs/content.html")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not os.path.exists(args.stats):
        print("WARNING: {} not found — views, records and gems will be empty".format(args.stats))
    videos, today = dd.load_videos(args.index, args.stats, args.analytics,
                                   args.classification, args.history_dir)
    transcripts = load_transcripts(args.transcripts_dir)
    data = build(videos, today, transcripts)

    t = data["totals"]
    print("Showcase: {} videos over {} years, {:,} hours, {:,} words, {:,} views".format(
        t["videos"], t["years"], t["hours"], t["words"], t["views"]))
    print("  {} year cards, {} milestones, {} records, {} obsessions, {} sagas".format(
        len(data["years"]), len(data["milestones"]), len(data["records"]),
        len(data["obsessions"]), len(data["sagas"])))

    with open(args.dashboard) as f:
        original = f.read()
    updated = embed(original, data)
    if updated == original:
        print("Showcase already up to date.")
        return
    if args.dry_run:
        print("DRY RUN — would update {}".format(args.dashboard))
        return
    with open(args.dashboard, "w") as f:
        f.write(updated)
    print("Showcase updated: {}".format(args.dashboard))


if __name__ == "__main__":
    sys.exit(main())
