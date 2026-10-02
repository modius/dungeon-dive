#!/usr/bin/env python3
"""
Build docs/insights.html — what content approaches work, and what to try next.

Public data only (no YouTube Analytics): view/like/comment counts, durations,
titles, the curated classification (video_classification.json) and the
committed view history (stats_history/). See dashboard_data.py for the metrics:

* breakout ratio — views ÷ median views of the ~20 uploads around it (age-fair)
* evergreen rate — views/day still earned by videos over a year old
* launch curve   — views at day N after publish

Every recommendation is generated from these with its evidence attached: sample
size, median lift, an 80% bootstrap interval, a confidence grade, example
videos, and a concrete experiment.

Usage:
    python3 scripts/build_insights.py --index video_index.json --stats youtube_stats.json \\
        --analytics transcript_analytics.json --series series_queue.json \\
        --dashboard docs/insights.html [--dry-run]
"""

import argparse
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import timedelta

import dashboard_data as dd
import stats_history

WINDOW_DAYS = 3 * 365          # performance comparisons use the last three years
BREAKOUT_RATIO = 3.0           # "breakout": 3x the uploads around it
DATA_RE = re.compile(r"(// @insights-data-begin\n).*?(\n// @insights-data-end)", re.S)


# ── Coverage gaps (mentions vs dedicated videos) ───────────────────

LEADING_ARTICLE_RE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)


def normalize_game_name(name):
    """Canonical form for comparing game names ("The Restless" == "Restless")."""
    stripped = LEADING_ARTICLE_RE.sub("", (name or "").strip().lower())
    return re.sub(r"[^a-z0-9]+", " ", stripped).strip()


def compute_coverage_gaps(videos, min_mentions=5, max_dedicated=2):
    """Games cross-referenced in many transcripts but rarely the subject.

    Dedicated coverage counts every channel video whose curated subject or
    franchise is the game, or whose title names it — so a standalone family
    member (Silver Tower under Warhammer Quest) and a pending, not-yet-imported
    video both count as coverage.
    """
    spellings = defaultdict(Counter)
    mentions = defaultdict(set)
    for v in videos:
        for g in v["tags"].get("games", []):
            key = normalize_game_name(g)
            if key:
                spellings[key][g] += 1
                mentions[key].add(v["id"])

    dedicated_keys = []
    for v in videos:
        keys = {normalize_game_name(v["cls"].get("subject")),
                normalize_game_name(v["cls"].get("franchise"))}
        dedicated_keys.append((v["id"], keys - {""}, normalize_game_name(v["title"])))

    out = []
    for key, mentioned in mentions.items():
        if len(mentioned) < min_mentions:
            continue
        word_rx = re.compile(r"\b" + re.escape(key) + r"\b")
        dedicated = {vid for vid, keys, title in dedicated_keys
                     if key in keys or word_rx.search(title)}
        if len(dedicated) > max_dedicated:
            continue
        out.append({
            "game": spellings[key].most_common(1)[0][0],
            "mentions": len(mentioned),
            "dedicated": len(dedicated),
        })
    out.sort(key=lambda r: (-r["mentions"] / max(r["dedicated"], 1), -r["mentions"]))
    return out[:12]


# ── Section builders ───────────────────────────────────────────────

def _strip(group):
    """Drop the video lists from a group_ratios() entry for the page payload."""
    return {k: v for k, v in group.items() if k != "videos"}


def _examples(vs, n=3, best=True):
    ranked = sorted((v for v in vs if v.get("ratio") is not None),
                    key=lambda v: v["ratio"], reverse=best)
    return [dd.ref(v) for v in ranked[:n]]


def build_tiles(videos, today):
    cutoff12 = today - timedelta(days=365)
    mature12 = [v for v in videos if v["date"] >= cutoff12 and v.get("ratio") is not None]
    uploads12 = [v for v in videos if v["date"] >= cutoff12]

    gains, back = 0.0, 0.0
    for v in videos:
        g = stats_history.daily_gain(v["history"], today, 30)
        if g is None:
            continue
        gains += g
        if v["age"] >= dd.EVERGREEN_MIN_AGE:
            back += g
    dates = sorted(v["date"] for v in uploads12)
    cadence = None
    if len(dates) >= 2:
        cadence = round((dates[-1] - dates[0]).days / (len(dates) - 1), 1)
    return {
        "typical_views": int(dd.median([v["views"] for v in mature12])) if mature12 else None,
        "daily_views": int(gains) if gains else None,
        "back_catalogue_share": round(back / gains, 3) if gains else None,
        "breakouts_12m": sum(1 for v in mature12 if v["ratio"] >= BREAKOUT_RATIO),
        "mature_12m": len(mature12),
        "uploads_12m": len(uploads12),
        "cadence_days": cadence,
    }


def build_groups(window, keyfn, labelfn, order=None, min_n=5):
    groups = dd.group_ratios(window, keyfn, min_n=min_n)
    rows = []
    for key, g in groups.items():
        ever = [v["evergreen"] for v in g["videos"] if v["evergreen"] is not None]
        row = _strip(g)
        row.update({
            "key": key,
            "label": labelfn(key),
            "evergreen_median": round(dd.median(ever), 1) if ever else None,
            "best": _examples(g["videos"], 2),
        })
        rows.append(row)
    if order:
        rows.sort(key=lambda r: order.index(r["key"]) if r["key"] in order else 99)
    else:
        rows.sort(key=lambda r: -r["median"])
    return rows, groups


def build_opportunity(videos, today):
    """Per lane: share of the last 12 months' uploads vs evergreen earning power.

    Evergreen efficiency = the lane's share of back-catalogue daily views divided
    by its share of the back catalogue. Above 1, each old video in the lane
    earns more than the average old video.
    """
    cutoff12 = today - timedelta(days=365)
    recent = Counter(v["cls"].get("lane") for v in videos if v["date"] >= cutoff12)
    old = [v for v in videos if v["evergreen"] is not None and v["cls"].get("lane")]
    total_old = len(old)
    total_ever = sum(v["evergreen"] for v in old)
    total_recent = sum(recent.values())
    by_lane = defaultdict(list)
    for v in old:
        by_lane[v["cls"]["lane"]].append(v)
    rows = []
    for lane, vs in by_lane.items():
        if len(vs) < 5 or not total_ever:
            continue
        ever_share = sum(v["evergreen"] for v in vs) / total_ever
        cat_share = len(vs) / total_old
        rows.append({
            "key": lane,
            "label": dd.lane_label(lane),
            "upload_share": round(recent.get(lane, 0) / total_recent, 3) if total_recent else 0,
            "recent_uploads": recent.get(lane, 0),
            "catalogue": len(vs),
            "evergreen_share": round(ever_share, 3),
            "efficiency": round(ever_share / cat_share, 2) if cat_share else None,
        })
    rows.sort(key=lambda r: -(r["efficiency"] or 0))
    return rows


def build_breakouts(videos, window):
    points = [[v["date"].isoformat(), round(v["ratio"], 3), v["title"][:90], v["views"]]
              for v in videos if v.get("ratio") is not None]
    ranked = sorted(window, key=lambda v: v["ratio"], reverse=True)

    def describe(v):
        return dd.ref(v, format=dd.fmt_label(v["cls"].get("format")),
                      lane=dd.lane_label(v["cls"].get("lane")),
                      minutes=round(v["duration"] / 60))

    top = [describe(v) for v in ranked[:12]]
    # Livestreams/channel notes are not content bets; leave them out of the floor.
    floor = [v for v in reversed(ranked) if v["cls"].get("format") != "channel"][:8]
    bottom = [describe(v) for v in floor]

    # Traits over-represented among breakouts.
    hits = [v for v in window if v["ratio"] >= BREAKOUT_RATIO]
    traits = []
    if len(hits) >= 5:
        facets = [
            ("Format", lambda v: v["cls"].get("format"), dd.fmt_label),
            ("Lane", lambda v: v["cls"].get("lane"), dd.lane_label),
            ("Length", lambda v: dd.duration_bucket(v["duration"]), lambda k: k),
            ("Solo focus", lambda v: "solo" if v["cls"].get("solo") else None,
             lambda k: "Solo-focused"),
        ]
        for facet, fn, label in facets:
            all_c = Counter(fn(v) for v in window)
            hit_c = Counter(fn(v) for v in hits)
            for key, k in hit_c.items():
                if key is None or k < 3:
                    continue
                share_hits = k / len(hits)
                share_all = all_c[key] / len(window)
                traits.append({
                    "facet": facet, "label": label(key), "breakouts": k,
                    "share_breakouts": round(share_hits, 3),
                    "share_all": round(share_all, 3),
                    "lift": round(share_hits / share_all, 2) if share_all else None,
                })
        traits.sort(key=lambda t: -(t["lift"] or 0))
    return {"points": points, "top": top, "bottom": bottom,
            "traits": traits[:8], "count": len(hits), "window_n": len(window)}


PART_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
              "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def build_series(videos):
    """How later parts of a multi-part series perform relative to part 1."""
    series = defaultdict(list)
    for v in videos:
        name, part = v["cls"].get("series"), v["cls"].get("part")
        if name and isinstance(part, int) and v.get("ratio") is not None:
            series[name].append(v)
    rel_by_part = defaultdict(list)
    table = []
    for name, vs in series.items():
        parts = {}
        for v in vs:
            parts.setdefault(v["cls"]["part"], v)
        if 1 not in parts or len(parts) < 2:
            continue
        first = parts[1]["ratio"]
        for p, v in parts.items():
            if p >= 2 and first:
                rel_by_part[min(p, 8)].append(v["ratio"] / first)
        last_part = max(parts)
        table.append({
            "series": name,
            "parts": len(parts),
            "first": dd.ref(parts[1]),
            "last": dd.ref(parts[last_part], part=last_part),
            "retention": round(parts[last_part]["ratio"] / first, 2) if first else None,
            "median_ratio": round(dd.median([v["ratio"] for v in parts.values()]), 2),
        })
    curve = [{"part": 1, "median": 1.0, "n": len(table)}]
    for p in sorted(rel_by_part):
        vals = rel_by_part[p]
        if len(vals) >= 3:
            curve.append({"part": p, "median": round(dd.median(vals), 3), "n": len(vals),
                          "label": "{}+".format(p) if p == 8 else str(p)})
    table.sort(key=lambda r: (-r["parts"], r["series"]))

    in_series = [v for v in videos if v["cls"].get("series") and v.get("ratio") is not None]
    standalone = [v for v in videos if not v["cls"].get("series") and v.get("ratio") is not None
                  and v["cls"]]
    return {
        "curve": curve,
        "table": table[:8],
        "series_median": round(dd.median([v["ratio"] for v in in_series]), 3) if in_series else None,
        "standalone_median": round(dd.median([v["ratio"] for v in standalone]), 3) if standalone else None,
        "series_n": len(in_series),
    }


def build_evergreen(videos, today):
    old = sorted((v for v in videos if v["evergreen"] is not None),
                 key=lambda v: -v["evergreen"])
    total = sum(v["evergreen"] for v in old)
    top = []
    for v in old[:15]:
        top.append(dd.ref(v, per_day=round(v["evergreen"], 1),
                          format=dd.fmt_label(v["cls"].get("format")),
                          lane=dd.lane_label(v["cls"].get("lane"))))
    top10_share = sum(v["evergreen"] for v in old[:10]) / total if total else None

    # Weekly channel-wide views/day, walking back from the last full snapshot
    # so every week spans dates the whole channel was recorded on.
    weekly = []
    full = dd.full_snapshot_dates(videos)
    if full:
        start, end = full[0], full[-1]
        anchors = []
        a = end
        while a - timedelta(days=7) >= start:
            anchors.append(a)
            a -= timedelta(days=7)
        anchors.append(a)
        anchors.reverse()
        for anchor, nxt in zip(anchors, anchors[1:]):
            gained, n = 0, 0
            for v in videos:
                a = stats_history.views_at(v["history"], anchor)
                b = stats_history.views_at(v["history"], nxt)
                if a is not None and b is not None:
                    gained += max(0, b - a)
                    n += 1
            weekly.append([nxt.isoformat(), round(gained / (nxt - anchor).days)])
    return {"top": top, "catalogue_n": len(old),
            "daily_total": round(total), "top10_share": round(top10_share, 3) if top10_share else None,
            "weekly": weekly}


def build_launch(videos, today):
    """Typical launch curve (days 1–30) and how recent uploads compare."""
    days = [d for d in dd.LAUNCH_DAYS if d <= 30]
    cohort = [v for v in videos if 30 in v["launch"]]
    band = []
    for d in days:
        vals = [v["launch"][d] for v in cohort if d in v["launch"]]
        if len(vals) >= 5:
            band.append({"day": d, "p25": int(dd.percentile(vals, 25)),
                         "median": int(dd.median(vals)), "p75": int(dd.percentile(vals, 75))})
    recent = []
    for v in sorted((v for v in videos if v["launch"] and v["age"] <= 45),
                    key=lambda v: v["date"], reverse=True)[:8]:
        latest_day = max(v["launch"])
        bench = next((b for b in band if b["day"] == latest_day), None)
        recent.append(dd.ref(
            v,
            curve=[[d, v["launch"][d]] for d in sorted(v["launch"]) if d <= 30],
            vs_typical=round(v["launch"][latest_day] / bench["median"], 2) if bench else None,
            at_day=latest_day,
        ))
    return {"band": band, "cohort_n": len(cohort), "recent": recent}


def build_schedule(videos, today):
    cutoff = today - timedelta(days=WINDOW_DAYS)
    dow = [0] * 7
    for v in videos:
        if v["date"] >= cutoff:
            dow[v["date"].weekday()] += 1
    monthly = Counter(v["date"].strftime("%Y-%m") for v in videos)
    return {"dow": dow, "monthly": sorted(monthly.items())}


def build_titles(window):
    rows = []
    for key, label, rx in dd.TITLE_PATTERNS:
        hit = [v for v in window if rx.search(v["title"])]
        if len(hit) < 5:
            continue
        ratios = [v["ratio"] for v in hit]
        lo, hi = dd.median_ci(ratios)
        rows.append({"key": key, "label": label, "n": len(hit),
                     "median": round(dd.median(ratios), 3),
                     "ci": [round(lo, 3), round(hi, 3)] if lo is not None else None,
                     "best": _examples(hit, 1)})
    rows.sort(key=lambda r: -r["median"])
    return rows


# ── Recommendations ────────────────────────────────────────────────

def confidence(n, ci, lift):
    if not ci:
        return "low"
    lo, hi = ci
    clear = lo > 1 or hi < 1
    strong = lift >= 1.25 or lift <= 0.8
    if clear and strong and n >= 20:
        return "high"
    if clear and n >= 8:
        return "medium"
    return "low"


CONF_WEIGHT = {"high": 3, "medium": 2, "low": 1}


def _pct(x):
    return "{:.0f}%".format(x * 100)


def _x(x):
    return "{:.1f}×".format(x) if x < 10 else "{:.0f}×".format(x)


def _card(kind, source, title, claim, evidence, n, lift, ci, examples, experiment,
          conf=None, impact=None, key=None):
    """One recommendation. `impact` is the share of recent uploads it concerns:
    a weak lane that is a fifth of the schedule matters more than one that is a
    twentieth, so it ranks higher."""
    conf = conf or confidence(n, ci, lift)
    examples_label = {"do": "Best examples", "avoid": "Exceptions that worked",
                      "refresh": None, "watch": None}[kind]
    score = abs(math.log(max(lift, 0.01))) * CONF_WEIGHT[conf]
    if impact:
        score *= 1 + 3 * impact
    return {
        "kind": kind, "source": source, "title": title, "claim": claim,
        "evidence": evidence, "n": n, "lift": round(lift, 2),
        "ci": ci, "confidence": conf, "examples": examples, "examples_label": examples_label,
        "experiment": experiment, "score": score, "key": key,
    }


def recommend(formats, lanes, durations, solo, titles, series, evergreen, opportunity,
              launch, window):
    cards = []
    upload_share = {o["key"]: o["upload_share"] for o in opportunity}

    # Formats and lanes: lift vs the typical upload (1.0x by construction).
    for dim, rows, noun in (("format", formats, "format"), ("lane", lanes, "lane")):
        for r in rows:
            if r["n"] < 8 or not r["ci"]:
                continue
            lift = r["median"]
            if r["ci"][0] > 1.05 and lift >= 1.2:
                ever = (" Old videos in this {} still earn a median {:.0f} views/day.".format(
                    noun, r["evergreen_median"]) if r.get("evergreen_median") else "")
                cards.append(_card(
                    "do", dim, "{}: {} the views of a typical upload".format(r["label"], _x(lift)),
                    "The median {} video gets {} the views of the uploads around it.{}".format(
                        dd.lane_noun(r["key"]) if dim == "lane" else r["label"].lower(), _x(lift), ever),
                    "n={} videos, last 3 years · 80% interval {}–{}".format(
                        r["n"], _x(r["ci"][0]), _x(r["ci"][1])),
                    r["n"], lift, r["ci"], r["best"],
                    "Schedule {} more {} videos in the next quarter and check their breakout "
                    "ratio here after 60 days — the bar to beat is {}.".format(
                        "two" if r["n"] < 20 else "three",
                        dd.lane_noun(r["key"]) if dim == "lane" else r["label"].lower(),
                        _x(max(1.0, lift * 0.8))),
                    key=r["key"]))
            elif r["ci"][1] < 0.95 and lift <= 0.8:
                share = upload_share.get(r["key"]) if dim == "lane" else None
                share_txt = (" They were {} of uploads in the last 12 months.".format(_pct(share))
                             if share and share >= 0.08 else "")
                noun = dd.lane_noun(r["key"]) if dim == "lane" else r["label"].lower()
                cards.append(_card(
                    "avoid", dim, "{}: {} of a typical upload".format(r["label"], _pct(lift)),
                    "The median {} video reaches {} of the views of the uploads around it.{} "
                    "That may be fine for the core audience, but these videos are unlikely to grow the channel.".format(
                        noun, _pct(lift), share_txt),
                    "n={} videos, last 3 years · 80% interval {}–{}".format(
                        r["n"], _pct(r["ci"][0]), _pct(r["ci"][1])),
                    r["n"], lift, r["ci"], r["best"],
                    "Keep making them for the regulars, but when picking between ideas give the "
                    "slot to a stronger format. The best of these show what works: "
                    "{}.".format(" / ".join("“{}”".format(e["title"]) for e in r["best"][:2])),
                    impact=share))

    # Length.
    by_bucket = {r["key"]: r for r in durations}
    short = by_bucket.get("under 15 min")
    if short and short["ci"] and short["n"] >= 8 and short["ci"][1] < 0.95:
        longest = max(durations, key=lambda r: r["median"])
        cards.append(_card(
            "avoid", "length", "Short videos under-perform: {} of typical".format(_pct(short["median"])),
            "Videos under 15 minutes reach {} of the views of nearby uploads; {} videos reach {}.".format(
                _pct(short["median"]), longest["label"], _x(longest["median"])),
            "n={} short videos · 80% interval {}–{}".format(
                short["n"], _pct(short["ci"][0]), _pct(short["ci"][1])),
            short["n"], short["median"], short["ci"], short["best"],
            "Fold short updates and quick looks into a longer video or a Community post, "
            "and keep standalone uploads in the {} range.".format(longest["label"])))

    # Solo focus.
    solo_row = next((r for r in solo if r["key"] == "solo"), None)
    if solo_row and solo_row["ci"] and solo_row["ci"][0] > 1.05:
        cards.append(_card(
            "do", "solo", "Solo-focused videos: {} of typical".format(_x(solo_row["median"])),
            "Videos where solo play is central reach {} the views of the uploads around them.".format(
                _x(solo_row["median"])),
            "n={} videos · 80% interval {}–{}".format(
                solo_row["n"], _x(solo_row["ci"][0]), _x(solo_row["ci"][1])),
            solo_row["n"], solo_row["median"], solo_row["ci"], solo_row["best"],
            "Put the solo angle in the title and the first minute: say how it plays solo, "
            "not only that it does."))

    # Title patterns.
    for r in titles:
        if r["n"] < 8 or not r["ci"]:
            continue
        if r["ci"][0] > 1.1 and r["median"] >= 1.3:
            cards.append(_card(
                "do", "title", "Titles with {}: {}".format(
                    r["label"][0].lower() + r["label"][1:], _x(r["median"])),
                "Videos whose titles have this pattern have a median breakout ratio of {}. "
                "The format probably matters more than the wording, but the pattern shows what viewers search for.".format(
                    _x(r["median"])),
                "n={} titles · 80% interval {}–{}".format(r["n"], _x(r["ci"][0]), _x(r["ci"][1])),
                r["n"], r["median"], r["ci"], r["best"],
                "When a video works as a guide or a list, say so in the title."))

    # Series decay.
    later = [c for c in series["curve"] if c["part"] >= 2]
    if later:
        p2 = later[0]
        if p2["n"] >= 5 and p2["median"] < 0.85:
            ex = sorted(series["table"], key=lambda r: r["retention"] or 1)[:2]
            cards.append(_card(
                "watch", "series", "Later parts lose viewers: part 2 gets {} of part 1".format(
                    _pct(p2["median"])),
                "Across multi-part series, part 2 reaches a median {} of part 1's breakout ratio, "
                "and later parts tend to fall further.".format(_pct(p2["median"])),
                "{} series with a part 1 and later parts".format(series["curve"][0]["n"]),
                p2["n"], p2["median"], None,
                [e["last"] for e in ex],
                "Make part 1 able to stand alone, with a full verdict and a searchable title, and "
                "give later parts their own hook in the title instead of only “Part N”.",
                conf="medium" if p2["n"] >= 10 else "low"))

    # Evergreen refresh: dated editions and guides still earning.
    edition_rx = re.compile(r"\b(?:19|20)\d\d\b")
    refresh = [e for e in evergreen["top"]
               if edition_rx.search(e["title"]) and e["format"] in ("Top list", "Guide")]
    if refresh:
        e = refresh[0]
        cards.append(_card(
            "refresh", "evergreen", "Refresh a dated favourite: “{}”".format(e["title"]),
            "Published {} and still earning {:.0f} views/day, one of the channel's strongest "
            "back-catalogue earners. Its date stamp makes a new edition the obvious next video.".format(
                e["date"][:4], e["per_day"]),
            "Evergreen rate over the last 90 days",
            1, max(e["per_day"] / max(1, dd.median([t["per_day"] for t in evergreen["top"]])), 1.01),
            None, [e],
            "Publish a new edition, link it from the old video's description and pinned comment, "
            "and compare its launch curve to the typical band on this page.",
            conf="medium"))
    guides = [e for e in evergreen["top"] if e["format"] in ("Guide", "Top list")]
    if len(guides) >= 3:
        share = len(guides) / len(evergreen["top"])
        cards.append(_card(
            "do", "evergreen", "Guides and lists keep paying: {} of the top 15 earners".format(
                "{}/{}".format(len(guides), len(evergreen["top"]))),
            "Of the 15 old videos still earning the most views per day, {} are guides or top "
            "lists. The back catalogue makes {} views/day in total.".format(
                len(guides), "{:,}".format(evergreen["daily_total"])),
            "Videos over a year old, views gained per day over the last 90 days",
            len(evergreen["top"]), 1 + share, None, guides[:3],
            "Plan one evergreen guide or list per quarter for a lane that viewers search "
            "(see the opportunity map), with a plain, searchable title.",
            conf="high" if len(guides) >= 6 else "medium"))

    # Opportunity: earns well, under-made. When the lane already has a "do"
    # card, the evergreen evidence joins it rather than repeating the lane.
    for o in opportunity:
        if o["efficiency"] and o["efficiency"] >= 1.5 and o["upload_share"] < o["evergreen_share"]:
            twin = next((c for c in cards if c["source"] == "lane" and c["kind"] == "do"
                         and c.get("key") == o["key"]), None)
            if twin:
                twin["claim"] += (" Its videos over a year old also earn {} the back-catalogue "
                                  "average per video ({} of all back-catalogue views/day), yet the "
                                  "lane got {} of uploads in the last 12 months.").format(
                    _x(o["efficiency"]), _pct(o["evergreen_share"]), _pct(o["upload_share"]))
                twin["title"] = "{}: launches well and keeps earning".format(o["label"])
                twin["score"] *= 1.5
                break
            cards.append(_card(
                "do", "opportunity", "{}: an under-served lane".format(o["label"]),
                "Each {} video over a year old earns {} the back-catalogue average in daily views, but "
                "the lane got only {} of uploads in the last 12 months.".format(
                    dd.lane_noun(o["key"]), _x(o["efficiency"]), _pct(o["upload_share"])),
                "{} catalogue videos · {} of back-catalogue views/day".format(
                    o["catalogue"], _pct(o["evergreen_share"])),
                o["catalogue"], o["efficiency"], None,
                [e for e in evergreen["top"] if e["lane"] == o["label"]][:3],
                "Raise this lane's share of uploads toward {} for two quarters and watch the weekly "
                "views/day line.".format(_pct(o["evergreen_share"])),
                conf="medium" if o["catalogue"] >= 20 else "low"))
            break

    # Launch watch: the recent upload furthest from the typical curve.
    notable = [r for r in launch["recent"] if r.get("vs_typical")
               and (r["vs_typical"] >= 1.5 or r["vs_typical"] <= 0.6)]
    notable.sort(key=lambda r: -abs(math.log(r["vs_typical"])))
    for r in notable[:1]:
            up = r["vs_typical"] >= 1.5
            cards.append(_card(
                "watch", "launch", "“{}” is {} typical at day {}".format(
                    r["title"], _x(r["vs_typical"]) if up else _pct(r["vs_typical"]) + " of",
                    r["at_day"]),
                "{} views on day {}, against a typical launch of {}.".format(
                    "{:,}".format(r["curve"][-1][1]), r["at_day"],
                    "{:,}".format(next(b["median"] for b in launch["band"] if b["day"] == r["at_day"]))),
                "Compared with {} launches recorded since April 2026".format(launch["cohort_n"]),
                launch["cohort_n"], r["vs_typical"], None, [r],
                "Note what is different about this one (topic, title, thumbnail) while it is "
                "fresh; check again at day 30." if up else
                "Consider a title or thumbnail change in the first week, while YouTube is still testing it.",
                conf="medium" if launch["cohort_n"] >= 15 else "low"))

    # Keep the strongest, at most two of each kind from any one source.
    cards.sort(key=lambda c: -c["score"])
    picked, per_source = [], Counter()
    for c in cards:
        if per_source[(c["source"], c["kind"])] >= 2:
            continue
        per_source[(c["source"], c["kind"])] += 1
        picked.append(c)
        if len(picked) >= 10:
            break
    order = {"do": 0, "refresh": 1, "avoid": 2, "watch": 3}
    picked.sort(key=lambda c: (order[c["kind"]], -c["score"]))
    for c in picked:
        c.pop("score", None)
        c.pop("key", None)
    return picked


# ── Assemble ───────────────────────────────────────────────────────

def build(videos, today):
    cutoff = today - timedelta(days=WINDOW_DAYS)
    window = [v for v in videos if v.get("ratio") is not None and v["date"] >= cutoff]
    classified = [v for v in window if v["cls"]]

    formats, _ = build_groups(classified, lambda v: v["cls"].get("format"), dd.fmt_label)
    lanes, _ = build_groups(classified, lambda v: v["cls"].get("lane"), dd.lane_label)
    durations, _ = build_groups(window, lambda v: dd.duration_bucket(v["duration"]),
                                lambda k: k, order=dd.DURATION_ORDER)
    solo, _ = build_groups(classified, lambda v: "solo" if v["cls"].get("solo") else "not-solo",
                           lambda k: "Solo-focused" if k == "solo" else "Not solo-focused")
    titles = build_titles(window)
    series = build_series(videos)
    evergreen = build_evergreen(videos, today)
    opportunity = build_opportunity(videos, today)
    launch = build_launch(videos, today)
    history_dates = sorted({r[0] for v in videos for r in v["history"]})

    return {
        "generated": today.isoformat(),
        "window_start": cutoff.isoformat(),
        "window_n": len(window),
        "classified_n": sum(1 for v in videos if v["cls"]),
        "total_n": len(videos),
        "history_start": history_dates[0].isoformat() if history_dates else None,
        "breakout_threshold": BREAKOUT_RATIO,
        "tiles": build_tiles(videos, today),
        "recommendations": recommend(formats, lanes, durations, solo, titles, series,
                                     evergreen, opportunity, launch, window),
        "breakouts": build_breakouts(videos, window),
        "formats": formats,
        "lanes": lanes,
        "opportunity": opportunity,
        "durations": durations,
        "solo": solo,
        "titles": titles,
        "series": series,
        "evergreen": evergreen,
        "launch": launch,
        "schedule": build_schedule(videos, today),
        "coverage": compute_coverage_gaps(videos),
    }


def embed(html, data):
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    new, n = DATA_RE.subn(lambda m: m.group(1) + "const INSIGHTS = " + payload + ";" + m.group(2), html)
    if n != 1:
        raise SystemExit("ERROR: insights data markers not found in dashboard template")
    return new


def main():
    p = argparse.ArgumentParser(description="Build docs/insights.html")
    p.add_argument("--index", default="video_index.json")
    p.add_argument("--stats", default="youtube_stats.json")
    p.add_argument("--analytics", default="transcript_analytics.json")
    p.add_argument("--series", default="series_queue.json",
                   help="accepted for CLI compatibility; import-queue progress now lives on health.html")
    p.add_argument("--classification", default="video_classification.json")
    p.add_argument("--history-dir", default=stats_history.HISTORY_DIR)
    p.add_argument("--dashboard", default="docs/insights.html")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not os.path.exists(args.index):
        print("ERROR: Cannot load video index from {}".format(args.index))
        sys.exit(1)
    if not os.path.exists(args.stats):
        print("ERROR: {} not found — run fetch_youtube_stats.py first; the insights "
              "page is built entirely from engagement data".format(args.stats))
        sys.exit(1)

    videos, today = dd.load_videos(args.index, args.stats, args.analytics,
                                   args.classification, args.history_dir)
    data = build(videos, today)

    t = data["tiles"]
    print("Data: {} videos ({} classified), stats as of {}, history from {}".format(
        data["total_n"], data["classified_n"], data["generated"], data["history_start"]))
    print("  typical views (12m): {}  views/day: {}  back catalogue: {}  breakouts (12m): {}".format(
        t["typical_views"], t["daily_views"], t["back_catalogue_share"], t["breakouts_12m"]))
    total_views = sum(v["views"] for v in videos)
    print("  total views: {:,}".format(total_views))
    print("\nRecommendations:")
    for c in data["recommendations"]:
        print("  [{}/{}] {} — {}".format(c["kind"], c["confidence"], c["title"], c["evidence"]))

    with open(args.dashboard) as f:
        original = f.read()
    updated = embed(original, data)
    if updated == original:
        print("\nInsights dashboard already up to date.")
        return
    if args.dry_run:
        print("\nDRY RUN — would update {}".format(args.dashboard))
        return
    with open(args.dashboard, "w") as f:
        f.write(updated)
    print("\nInsights dashboard updated: {}".format(args.dashboard))


if __name__ == "__main__":
    main()
