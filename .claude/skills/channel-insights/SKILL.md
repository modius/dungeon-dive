---
name: channel-insights
description: >
  Build and update the channel insights dashboard with performance analytics,
  publishing patterns, coverage gaps, and actionable suggestions for Daniel.
  Triggers: "channel insights", "build insights", "update insights", "channel analytics"
---

Build the Channel Insights dashboard with actionable analytics for the Dungeon Dive.

## Steps

1. Ensure stats are fresh (optional):
   ```bash
   python3 scripts/fetch_youtube_stats.py --config config.json --index video_index.json --output youtube_stats.json --max-age-hours 24
   ```

2. Build insights:
   ```bash
   python3 scripts/build_insights.py --index video_index.json --stats youtube_stats.json --analytics transcript_analytics.json --series series_queue.json --dashboard docs/insights.html
   ```

3. View the dashboard:
   Open `docs/insights.html` in a browser.

## What it produces

The insights dashboard (`docs/insights.html`) contains:

1. **Key Metrics** — total views, avg views/video, top game, upload cadence
2. **Content Performance** — top 15 games by average views (3+ videos only)
3. **Format Performance** — which content formats get most views
4. **Publishing Patterns** — day-of-week and monthly upload frequency
5. **Coverage Analysis** — games mentioned often but rarely featured (untapped topics)
6. **Series Completion** — progress bars for active/completed series
7. **Content Web** — game co-occurrence pairs (what's discussed together)
8. **Engagement Trends** — view counts over time with moving average
9. **Actionable Suggestions** — auto-generated, prioritized recommendations

## Data sources

- `video_index.json` — publishing dates, video count
- `youtube_stats.json` — views, likes, comments, duration
- `transcript_analytics.json` — game/format/theme taxonomy
- `series_queue.json` — series progress

## Rules
- The page degrades gracefully if youtube_stats.json doesn't exist
- Always run analyze_content.py before this if new videos were imported
- Do NOT modify docs/insights.html manually — it's auto-generated
