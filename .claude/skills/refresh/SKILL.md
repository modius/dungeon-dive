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

### 1. Sync with remote

```bash
git pull origin main
```

**Run this first, before generating anything.** A nightly scheduled `/refresh` also pushes `docs/*.html`, so this repo regularly has a refresh commit waiting that you do not have locally. Pull while the tree is still clean — once steps 2–4 have rewritten the dashboards, `git pull` refuses to run ("local changes would be overwritten") and you are stuck reconciling generated HTML by hand.

### 2. Analyze content taxonomy

```bash
python3 scripts/analyze_content.py --index video_index.json
```

Tags all imported videos with game, format, mechanic, theme, player mode, platform, and era facets. Only processes new/untagged videos by default.

**Add `--reanalyze` after any change to the tagging logic** (`KNOWN_GAMES`, `AMBIGUOUS_GAME_NAMES`, the extractors in `analyze_content.py`). Cached tags are never revisited otherwise, so a fix silently applies to new videos only and the dashboards keep serving the old numbers. Costs ~40s for the full archive and touches no APIs.

### 3. Fetch YouTube engagement stats

```bash
python3 scripts/fetch_youtube_stats.py --config config.json --index video_index.json --output youtube_stats.json --max-age-hours 24
```

Pulls views, likes, comments, and duration for all videos. Skips videos refreshed within 24 hours. Uses ~0.2% of daily API quota.

### 4. Rebuild all dashboards

```bash
python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html
python3 scripts/build_insights.py --index video_index.json --stats youtube_stats.json --analytics transcript_analytics.json --series series_queue.json --dashboard docs/insights.html
```

Updates the main dashboard (index, health, content pages) and the insights dashboard.

### 5. Commit and push

```bash
git add docs/index.html docs/content.html docs/health.html docs/insights.html
git commit -m "insights: refreshed engagement data (N videos, N total views)"
git push origin main
```

Note: `youtube_stats.json` is gitignored — do not commit it.

**If the push is rejected** (`! [rejected] main -> main (fetch first)`), a concurrent refresh landed while this run was working. Do NOT hand-merge or `--force` — `docs/*.html` are generated files and a conflict in them is meaningless to resolve by hand. Regenerate instead:

```bash
git reset --hard HEAD~1          # drop your commit; the dashboards are regenerable
git pull --ff-only origin main   # take the other run's commit
```

> This reset is safe **only because a `/refresh` commit contains nothing but generated dashboards.** Do not carry it over to `/import`, whose commit holds the archive, live Discourse topic IDs, and the Keeper post — that one recovers with `git pull --rebase`.

Then re-run step 4 and commit again. Your local `youtube_stats.json` survives the reset (it is gitignored), so the rebuilt dashboards carry whichever data is fresher — compare the total-views figure in the other run's commit message against yours to confirm which that is. History stays linear and no data is lost.

## When to run

- After `/import` to update analytics with newly imported videos
- Periodically to refresh YouTube engagement numbers
- Before presenting channel performance data to Daniel

## Rules
- Do NOT commit youtube_stats.json (volatile engagement data, gitignored)
- Steps must run in order — insights depends on fresh taxonomy and stats
- Safe to run multiple times per day
- Always pull before generating (step 1) — a nightly `/refresh` shares this branch and touches the same generated files
- Never resolve a conflict in `docs/*.html` by hand; discard and regenerate
