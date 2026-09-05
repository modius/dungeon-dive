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

**Use `--reanalyze` on a local run too, whenever the local cache is more than a day or two old.** The nightly `/refresh` runs from a clean clone, and `transcript_analytics.json` is gitignored — so the nightly has no cache and re-derives all 877 videos from scratch every time. A local incremental run does not reproduce that: cached entries keep tags derived from transcripts that have since gone missing from `archive/transcripts/`, so the local dashboard carries tags the nightly cannot regenerate and silently reverts the next day. Verified 2026-09-05: incremental output held 11 extra tags across 11 videos (`review`, `crowdfund-preview`, `discussion`, `tutorial`, `rpg`, `miniatures`, `hex-crawl`, `wargame`), and **all 11 were among the 79 imported videos with no local transcript**. Reproducibility beats the richer-but-unregenerable cache — match the nightly, and fix the cause with `/repair transcripts`.

> **The 79 missing transcripts are the real defect here, not the tagging.** `check_integrity.py` has been reporting `warn` with the recommendation "79 imported videos missing local transcripts" — 42 of them from 2024. Those videos are tagged from title and description alone, every night, on the published dashboards. Treat a rising count as a data-loss signal, not noise.

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

**`N videos` means the analyzed count** — the figure `analyze_content.py` prints in step 2 ("Analyzed 877 videos"), i.e. imported videos carrying taxonomy. It is **not** the figure `fetch_youtube_stats.py` prints in step 3 ("Fetched stats for 1060 videos (6 new, 1054 updated)"), which counts the whole channel including pending. Past runs mixed the two, so the history reads 842 → 850 → 856 → **1057** → 870 → 875, and the jumps look like data loss when nothing was wrong. `N total views` is the `total_views` from step 4's insights output. Not committing `docs/index.html` is normal — it only changes when `video_index.json` does, i.e. after an `/import`, not after a `/refresh`.

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
