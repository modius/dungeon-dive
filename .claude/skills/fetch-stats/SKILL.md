---
name: fetch-stats
description: >
  Fetch YouTube engagement data (views, likes, comments, duration) for all
  channel videos using the YouTube Data API. Safe to run frequently — uses
  0.2% of daily API quota. Completely isolated from transcript fetching.
  Triggers: "fetch stats", "get youtube stats", "update views", "fetch views"
---

Fetch YouTube engagement statistics for all indexed videos.

## Steps

1. Run the stats fetcher:
   ```bash
   python3 scripts/fetch_youtube_stats.py --config config.json --index video_index.json --output youtube_stats.json
   ```

   Use `--only-missing` to skip videos already fetched.
   Use `--max-age-hours 24` to refresh stats older than 24 hours.

2. Rebuild insights dashboard:
   ```bash
   python3 scripts/build_insights.py --index video_index.json --stats youtube_stats.json --analytics transcript_analytics.json --dashboard docs/insights.html
   ```

## Safety

This script uses the YouTube Data API v3 with an API key. It batches 50 video IDs per request, requiring ~21 API calls for all 1,012 videos. YouTube's daily quota is 10,000 units — this uses ~21 units (0.2%).

This is completely separate from transcript fetching (youtube-transcript-api) and will NOT trigger rate limits or bans.

## Output

`youtube_stats.json` — per-video engagement data (view_count, like_count, comment_count, duration_seconds, duration_display). This file is gitignored as engagement data is volatile.

## View history

`youtube_stats.json` is overwritten on every fetch. The durable record is `stats_history/` (committed), and **only `/refresh` writes it** (`stats_history.py snapshot`), committing and pushing in the same run. Don't take a snapshot from this skill. An uncommitted snapshot left in the tree would block the next `/refresh`'s `git pull` against the nightly's.

## Rules
- Safe to run multiple times per day
- Do NOT commit youtube_stats.json to git (it changes constantly)
- After fetching, always rebuild the insights dashboard
