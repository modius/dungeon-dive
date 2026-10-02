---
name: channel-insights
description: >
  Build and update the channel insights dashboard: evidence-backed
  recommendations on which content approaches grow The Dungeon Dive, from
  breakout ratios, evergreen earning, launch curves, series decay, and an
  opportunity map by lane.
  Triggers: "channel insights", "build insights", "update insights", "channel analytics"
---

Build the Channel Insights dashboard (`docs/insights.html`). It recommends what to make more of, what to rethink, and what to watch.

## Steps

1. Ensure stats are fresh (optional):
   ```bash
   python3 scripts/fetch_youtube_stats.py --config config.json --index video_index.json --output youtube_stats.json --max-age-hours 24
   ```

2. Build insights:
   ```bash
   python3 scripts/build_insights.py --index video_index.json --stats youtube_stats.json --analytics transcript_analytics.json --dashboard docs/insights.html
   ```
   It prints the recommendations it generated. Read them: they become public on the next push.

3. View the dashboard: open `docs/insights.html` in a browser.

## Public data only: how the metrics stay fair

There is **no YouTube Analytics access** (no impressions, CTR, retention or traffic sources). Everything is inferred from public counts, durations, titles, transcripts, the curated classification and the committed view history. The core metrics live in `scripts/dashboard_data.py`:

- **Breakout ratio**: views ÷ the median views of the ~20 uploads published around the video. Neighbours are the same age and from the same era of the channel, so this cancels the old-video head start and channel growth. Using a median keeps a single 200k hit from dragging the baseline. Only videos ≥ 60 days old get one. **Never compare raw or mean view counts across eras.** The old page did, and its format "averages" were really a handful of outliers.
- **Evergreen rate**: views/day over the last 90 days for videos over a year old, from `stats_history/`. It's the back catalogue's search and recommendation pull.
- **Launch curve**: views at day 1/2/3/7/14/30. The benchmark band comes from every launch with 30 days of history.

Comparisons use the last 3 years (`WINDOW_DAYS`). Group medians carry an 80% bootstrap interval with a fixed seed, so a rebuild from the same data is identical.

## What it produces

1. **Tiles**: typical video (median views, last 12 months), channel views/day, back-catalogue share, breakouts.
2. **Recommendations**: up to 10 cards, each with a kind (do more / refresh / trade-off / watch), evidence (n, lift, interval), a confidence grade, example videos and an experiment to try. Confidence is **high** when the interval clears 1.0×, the effect is ≥1.25× or ≤0.8× and n ≥ 20. It's **medium** when the interval clears 1.0× with n ≥ 8, and **low** otherwise. A lane trade-off ranks higher the bigger its share of recent uploads.
3. **What breaks out**: a log-scale ratio scatter, traits over-represented among breakouts, the biggest breakouts and the quietest uploads.
4. **Formats and lanes**: median plus middle-half dot plots, and an opportunity map (upload share vs evergreen earning per old video).
5. **Length, solo focus, title patterns.**
6. **Multi-part series**: later parts against part 1, from the curated `series`/`part`.
7. **Back catalogue**: weekly channel views/day and the top evergreen earners.
8. **Launch tracker**: the newest uploads and the most unusual recent one, against the typical band.
9. **Upload schedule**: descriptive only. Nearly every upload goes out on Wednesday or Sunday, so the data can't say whether day of week matters, and the page says so instead of recommending a day.
10. **Mentioned often, rarely covered**: transcript mentions against dedicated videos (curated subject/franchise or title).

## Data sources

- `video_index.json`: publishing dates, forum topic IDs
- `youtube_stats.json`: views, likes, comments, duration (gitignored, fetched)
- `video_classification.json`: curated subject / format / lane / solo / series (committed)
- `stats_history/`: committed view history (written by `/refresh`)
- `transcript_analytics.json`: cross-referenced game mentions (for coverage)

## Rules
- The build stops if `youtube_stats.json` is missing. The whole page is engagement data
- Run `analyze_content.py` first if new videos were imported, and make sure they're classified (`/refresh` step 2). Unclassified videos drop out of the format and lane comparisons
- Do NOT hand-edit the data blob in `docs/insights.html` (between `// @insights-data-begin` and `// @insights-data-end`). The markup around it is a template and can be edited deliberately
- Recommendations come from rules in `recommend()` in `build_insights.py`. To change what gets recommended, change the rule there, not the page
