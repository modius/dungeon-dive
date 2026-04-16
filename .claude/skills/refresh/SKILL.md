---
name: refresh
description: >
  Refresh all Dungeon Dive analytics in one pass — content taxonomy, YouTube
  engagement stats, and channel insights dashboard. Chains analyze, fetch-stats,
  and channel-insights into a single run.
  Triggers: "refresh", "refresh analytics", "refresh dashboards", "update everything"
---

Refresh all Dungeon Dive analytics: content taxonomy, YouTube stats, and insights dashboard.

## Steps

### 1. Analyze content taxonomy

```bash
python3 scripts/analyze_content.py --index video_index.json
```

Tags all imported videos with game, format, mechanic, theme, player mode, platform, and era facets. Only processes new/untagged videos by default.

### 2. Fetch YouTube engagement stats

```bash
python3 scripts/fetch_youtube_stats.py --config config.json --index video_index.json --output youtube_stats.json --max-age-hours 24
```

Pulls views, likes, comments, and duration for all videos. Skips videos refreshed within 24 hours. Uses ~0.2% of daily API quota.

### 3. Rebuild all dashboards

```bash
python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html
python3 scripts/build_insights.py --index video_index.json --stats youtube_stats.json --analytics transcript_analytics.json --series series_queue.json --dashboard docs/insights.html
```

Updates the main dashboard (index, health, content pages) and the insights dashboard.

### 4. Commit and push

```bash
git add docs/index.html docs/content.html docs/health.html docs/insights.html
git commit -m "insights: refreshed engagement data (N videos, N total views)"
git push origin main
```

Note: `youtube_stats.json` is gitignored — do not commit it.

## When to run

- After `/import` to update analytics with newly imported videos
- Periodically to refresh YouTube engagement numbers
- Before presenting channel performance data to Daniel

## Rules
- Do NOT commit youtube_stats.json (volatile engagement data, gitignored)
- Steps must run in order — insights depends on fresh taxonomy and stats
- Safe to run multiple times per day
