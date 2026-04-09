#!/usr/bin/env python3
"""
Build channel insights data and update docs/insights.html.

Merges data from video_index.json, youtube_stats.json, transcript_analytics.json,
and series_queue.json to compute performance metrics, publishing patterns,
coverage gaps, and actionable suggestions.

Usage:
    python3 scripts/build_insights.py --index video_index.json
    python3 scripts/build_insights.py --index video_index.json --dry-run
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta


def safe_re_sub(pattern, replacement, string, **kwargs):
    """re.sub that escapes backslashes in the replacement string."""
    return re.sub(pattern, lambda m: replacement, string, **kwargs)


def load_json(path):
    """Load a JSON file, return None if missing."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def compute_key_metrics(videos, stats, analytics):
    """Compute top-level channel metrics."""
    has_stats = stats is not None
    total_views = 0
    view_counts = []

    if has_stats:
        st = stats.get("stats", {})
        for vid, s in st.items():
            vc = s.get("view_count", 0)
            total_views += vc
            view_counts.append(vc)

    avg_views = int(total_views / len(view_counts)) if view_counts else None

    # Most viewed game (by total views)
    most_viewed_game = None
    if has_stats and analytics:
        st = stats.get("stats", {})
        game_views = defaultdict(int)
        for v in analytics.get("videos", []):
            vid = v.get("video_id")
            pg = v.get("primary_game")
            if pg and vid and vid in st:
                game_views[pg] += st[vid].get("view_count", 0)
        if game_views:
            most_viewed_game = max(game_views, key=game_views.get)

    # Average days between uploads
    dates = sorted(v.get("published_at", "")[:10] for v in videos if v.get("published_at"))
    dates = [d for d in dates if d]
    avg_days = None
    if len(dates) >= 2:
        dt_dates = [datetime.strptime(d, "%Y-%m-%d") for d in dates]
        total_span = (dt_dates[-1] - dt_dates[0]).days
        avg_days = round(total_span / (len(dt_dates) - 1), 1)

    return {
        "total_views": total_views if has_stats else None,
        "avg_views": avg_views,
        "most_viewed_game": most_viewed_game,
        "avg_days_between_uploads": avg_days,
    }


def compute_game_performance(analytics, stats):
    """Top 15 games by avg views, minimum 3 videos."""
    if not analytics or not stats:
        return []

    st = stats.get("stats", {})
    game_data = defaultdict(list)

    for v in analytics.get("videos", []):
        vid = v.get("video_id")
        pg = v.get("primary_game")
        if pg and vid and vid in st:
            game_data[pg].append(st[vid].get("view_count", 0))

    results = []
    for game, views in game_data.items():
        if len(views) >= 3:
            avg = int(sum(views) / len(views))
            results.append([game, avg, len(views)])

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:15]


def compute_format_performance(analytics, stats):
    """Formats by avg views."""
    if not analytics or not stats:
        return []

    st = stats.get("stats", {})
    format_data = defaultdict(list)

    for v in analytics.get("videos", []):
        vid = v.get("video_id")
        formats = v.get("format", [])
        if vid and vid in st:
            vc = st[vid].get("view_count", 0)
            for fmt in formats:
                format_data[fmt].append(vc)

    results = []
    for fmt, views in format_data.items():
        if len(views) >= 2:
            avg = int(sum(views) / len(views))
            results.append([fmt, avg, len(views)])

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def compute_publishing_patterns(videos):
    """Day-of-week and monthly publishing counts."""
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_counts = [0] * 7
    monthly = defaultdict(int)

    for v in videos:
        pa = v.get("published_at", "")[:10]
        if not pa:
            continue
        try:
            dt = datetime.strptime(pa, "%Y-%m-%d")
            day_counts[dt.weekday()] += 1
            month_key = dt.strftime("%Y-%m")
            monthly[month_key] += 1
        except ValueError:
            pass

    monthly_list = [[k, v] for k, v in sorted(monthly.items())]

    return {
        "day_of_week": day_counts,
        "monthly": monthly_list,
    }


def compute_coverage_gaps(analytics):
    """Games with mention_count > dedicated_count."""
    if not analytics:
        return []

    # Count dedicated (primary_game) and mentions (games list)
    dedicated = Counter()
    mentions = Counter()

    for v in analytics.get("videos", []):
        pg = v.get("primary_game")
        if pg:
            dedicated[pg] += 1
        for g in v.get("games", []):
            mentions[g] += 1

    results = []
    for game, mention_count in mentions.items():
        ded_count = dedicated.get(game, 0)
        gap = mention_count - ded_count
        if gap > 0 and mention_count > ded_count:
            results.append([game, mention_count, ded_count, gap])

    results.sort(key=lambda x: x[3], reverse=True)
    return results


def compute_series_health(series_data, analytics):
    """Series completion status."""
    if not series_data:
        return []

    results = []

    # Count videos per game from analytics for active series
    game_counts = Counter()
    if analytics:
        for v in analytics.get("videos", []):
            pg = v.get("primary_game")
            if pg:
                game_counts[pg] += 1

    for s in series_data.get("active_series", []):
        remaining = s.get("videos_remaining", 0)
        title = s.get("title", s.get("theme", "Unknown"))
        # Estimate total from remaining + already imported parts
        # Use game_counts as completed estimate
        completed = game_counts.get(title, 0)
        total = completed + remaining
        results.append({
            "title": title,
            "total": total,
            "completed": completed,
            "remaining": remaining,
            "status": "active",
            "last_imported": s.get("last_imported", ""),
        })

    for s in series_data.get("completed_series", []):
        total = s.get("total_videos", 0)
        results.append({
            "title": s.get("title", s.get("theme", "Unknown")),
            "total": total,
            "completed": total,
            "remaining": 0,
            "status": "completed",
            "last_imported": s.get("completed_date", ""),
        })

    return results


def compute_content_web(analytics):
    """Top 20 game co-occurrence pairs."""
    if not analytics:
        return []

    pair_counts = Counter()
    for v in analytics.get("videos", []):
        games = sorted(set(v.get("games", [])))
        for i in range(len(games)):
            for j in range(i + 1, len(games)):
                pair_counts[(games[i], games[j])] += 1

    results = []
    for (a, b), count in pair_counts.most_common(20):
        results.append([a, b, count])

    return results


def compute_engagement_trends(videos, stats):
    """All videos sorted by date with view counts."""
    if not stats:
        return []

    st = stats.get("stats", {})
    results = []

    for v in videos:
        vid = v.get("video_id")
        pa = v.get("published_at", "")[:10]
        if vid and vid in st and pa:
            results.append([pa, st[vid].get("view_count", 0)])

    results.sort(key=lambda x: x[0])
    return results


def generate_suggestions(key_metrics, game_perf, format_perf, coverage_gaps,
                         series_health, publishing, stats, engagement):
    """Generate actionable suggestions based on data patterns."""
    suggestions = []

    if not stats:
        suggestions.append({
            "category": "Setup",
            "title": "Enable engagement analytics",
            "detail": "Run fetch_youtube_stats.py to enable engagement analytics",
            "priority": "high",
        })
        return suggestions

    channel_avg = key_metrics.get("avg_views")
    if not channel_avg:
        return suggestions

    # High performer games
    for game, avg, count in game_perf:
        if avg > 1.5 * channel_avg:
            suggestions.append({
                "category": "Performance",
                "title": "High performer: {}".format(game),
                "detail": "{} averages {:,} views vs channel average of {:,}".format(
                    game, avg, channel_avg),
                "priority": "high",
            })

    # Coverage gaps
    for game, mentions, dedicated, gap in coverage_gaps:
        if mentions >= 5 and dedicated <= 2:
            suggestions.append({
                "category": "Coverage",
                "title": "Coverage gap: {}".format(game),
                "detail": "{} mentioned in {} videos but only {} dedicated".format(
                    game, mentions, dedicated),
                "priority": "medium",
            })

    # Format insights
    for fmt, avg, count in format_perf:
        if avg > 1.3 * channel_avg:
            suggestions.append({
                "category": "Format",
                "title": "Format insight: {}".format(fmt),
                "detail": "{} content averages {:,} views".format(fmt, avg),
                "priority": "low",
            })

    # Series stalled
    today = datetime.now()
    for s in series_health:
        if s["status"] == "active" and s.get("last_imported"):
            try:
                last = datetime.strptime(s["last_imported"], "%Y-%m-%d")
                if (today - last).days > 14:
                    suggestions.append({
                        "category": "Series",
                        "title": "Series stalled: {}".format(s["title"]),
                        "detail": "{} last updated {}".format(
                            s["title"], s["last_imported"]),
                        "priority": "medium",
                    })
            except ValueError:
                pass

    # Best publish day
    if publishing.get("day_of_week") and engagement:
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        # Group engagement by day of week
        day_views = defaultdict(list)
        for date_str, views in engagement:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                day_views[dt.weekday()].append(views)
            except ValueError:
                pass

        day_avgs = {}
        for d, views in day_views.items():
            if len(views) >= 5:
                day_avgs[d] = int(sum(views) / len(views))

        if day_avgs:
            best_day = max(day_avgs, key=day_avgs.get)
            best_avg = day_avgs[best_day]
            overall_avg = int(sum(v for vs in day_views.values() for v in vs) /
                             sum(len(vs) for vs in day_views.values()))
            if best_avg > 1.2 * overall_avg:
                suggestions.append({
                    "category": "Publishing",
                    "title": "Best publish day: {}".format(day_names[best_day]),
                    "detail": "{} videos average {:,} views".format(
                        day_names[best_day], best_avg),
                    "priority": "low",
                })

    return suggestions


def update_insights_html(html, data):
    """Replace JS constants in the HTML with computed data."""
    replacements = {
        "keyMetrics": data["keyMetrics"],
        "gamePerformance": data["gamePerformance"],
        "formatPerformance": data["formatPerformance"],
        "publishingPatterns": data["publishingPatterns"],
        "coverageGaps": data["coverageGaps"],
        "seriesHealth": data["seriesHealth"],
        "contentWeb": data["contentWeb"],
        "engagementTrends": data["engagementTrends"],
        "suggestions": data["suggestions"],
    }

    # Use compact JSON for large arrays, indented for objects/small data
    compact_keys = {"engagementTrends", "gamePerformance", "formatPerformance",
                    "coverageGaps", "contentWeb"}

    for name, value in replacements.items():
        if name in compact_keys:
            js_value = json.dumps(value, separators=(",", ":"))
        else:
            js_value = json.dumps(value, indent=2)
        pattern = r"const {} = [\[{{].*?[\]}}];".format(re.escape(name))
        replacement = "const {} = {};".format(name, js_value)
        html = safe_re_sub(pattern, replacement, html, flags=re.DOTALL)

    return html


def main():
    parser = argparse.ArgumentParser(
        description="Build channel insights and update docs/insights.html")
    parser.add_argument("--index", default="video_index.json",
                        help="Path to video_index.json")
    parser.add_argument("--stats", default="youtube_stats.json",
                        help="Path to youtube_stats.json")
    parser.add_argument("--analytics", default="transcript_analytics.json",
                        help="Path to transcript_analytics.json")
    parser.add_argument("--series", default="series_queue.json",
                        help="Path to series_queue.json")
    parser.add_argument("--dashboard", default="docs/insights.html",
                        help="Path to insights HTML file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show changes without writing")
    args = parser.parse_args()

    # Load data sources
    index_data = load_json(args.index)
    if not index_data:
        print("ERROR: Cannot load video index from {}".format(args.index))
        sys.exit(1)

    videos = index_data.get("videos", [])
    stats = load_json(args.stats)
    analytics = load_json(args.analytics)
    series_data = load_json(args.series)

    print("Data sources:")
    print("  video_index: {} videos".format(len(videos)))
    print("  youtube_stats: {}".format(
        "{} entries".format(len(stats.get("stats", {}))) if stats else "NOT FOUND"))
    print("  transcript_analytics: {}".format(
        "{} analyzed".format(analytics.get("total_analyzed", 0)) if analytics else "NOT FOUND"))
    print("  series_queue: {}".format(
        "{} active, {} completed".format(
            len(series_data.get("active_series", [])),
            len(series_data.get("completed_series", []))) if series_data else "NOT FOUND"))

    # Compute all data
    key_metrics = compute_key_metrics(videos, stats, analytics)
    game_perf = compute_game_performance(analytics, stats)
    format_perf = compute_format_performance(analytics, stats)
    publishing = compute_publishing_patterns(videos)
    gaps = compute_coverage_gaps(analytics)
    series = compute_series_health(series_data, analytics)
    web = compute_content_web(analytics)
    engagement = compute_engagement_trends(videos, stats)
    suggestions = generate_suggestions(
        key_metrics, game_perf, format_perf, gaps,
        series, publishing, stats, engagement)

    data = {
        "keyMetrics": key_metrics,
        "gamePerformance": game_perf,
        "formatPerformance": format_perf,
        "publishingPatterns": publishing,
        "coverageGaps": gaps,
        "seriesHealth": series,
        "contentWeb": web,
        "engagementTrends": engagement,
        "suggestions": suggestions,
    }

    print("\nComputed insights:")
    print("  Key metrics: total_views={}, avg_views={}, top_game={}, cadence={}d".format(
        key_metrics.get("total_views"),
        key_metrics.get("avg_views"),
        key_metrics.get("most_viewed_game"),
        key_metrics.get("avg_days_between_uploads")))
    print("  Game performance: {} games (3+ videos)".format(len(game_perf)))
    print("  Format performance: {} formats".format(len(format_perf)))
    print("  Coverage gaps: {} games".format(len(gaps)))
    print("  Series health: {} series".format(len(series)))
    print("  Content web: {} pairs".format(len(web)))
    print("  Engagement trends: {} data points".format(len(engagement)))
    print("  Suggestions: {}".format(len(suggestions)))

    # Update HTML
    if not os.path.exists(args.dashboard):
        print("\nERROR: Dashboard not found at {}".format(args.dashboard))
        sys.exit(1)

    with open(args.dashboard) as f:
        original = f.read()

    updated = update_insights_html(original, data)

    if original == updated:
        print("\nInsights dashboard already up to date.")
        return

    if args.dry_run:
        print("\nDRY RUN — would update {}".format(args.dashboard))
    else:
        with open(args.dashboard, "w") as f:
            f.write(updated)
        print("\nInsights dashboard updated: {}".format(args.dashboard))

    if suggestions:
        print("\nSuggestions:")
        for s in suggestions:
            print("  [{}/{}] {} — {}".format(
                s["priority"], s["category"], s["title"], s["detail"]))


if __name__ == "__main__":
    main()
