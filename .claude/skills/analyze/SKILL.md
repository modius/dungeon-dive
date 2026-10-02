---
name: analyze
description: >
  Run content analysis on imported videos to build taxonomy tags (merging in the
  curated classification) and rebuild the channel showcase page. Extracts games,
  formats, mechanics, themes, player modes, and tag data.
  Triggers: "analyze", "analyze content", "run analysis", "update taxonomy", "tag videos"
---

Analyze imported video content and rebuild the channel showcase (`docs/content.html`).

## Two layers of taxonomy

1. **Curated classification**: `video_classification.json` (committed). Each video has one judged record: `subject`, `franchise`, `subject_type`, `format`, `lane`, `theme`, `solo`, `series`, `part`. It's written by Claude from the title and post summary, and validated against closed vocabularies by `scripts/classify_videos.py`. **This is the layer the dashboards and `/plan-batch` should trust.** `analyze_content.py` copies it into `transcript_analytics.json` as `subject`, `primary_format`, `lane`, `primary_theme`, `solo_focus`, `series` and `part`. It also lets it set `primary_game`, `content_category` and the `solo` player mode. New videos are classified by `/refresh` step 2. `/refresh` is the only writer of this file.
2. **Regex facets** (below): multi-valued and secondary. They're useful for clustering and search, but too blunt to rank content approaches. Formats are matched against the title and post body only. Mechanics, themes, modes and platforms also count transcript evidence, but only after 3+ hits (`MIN_TRANSCRIPT_HITS`). Matching a single passing mention anywhere in a 40-minute auto-caption used to put "overview" on 672 of 1001 videos and "solo" on 628.

## What it does

Reads post summaries and transcripts for all imported videos to extract:
- **Games**: Primary game subject + cross-referenced mentions
- **Format tags**: review, overview, lets-play, deep-dive, unboxing, comparison, top-list, crowdfund-preview, tutorial, discussion, digital-dive, buyers-guide
- **Mechanic tags**: dungeon-crawler, rpg, campaign, miniatures, deck-builder, hex-crawl, dice-game, sandbox, card-game, wargame, press-your-luck, tile-laying, tower-defense
- **Theme tags**: fantasy, horror, sci-fi, post-apocalyptic, pirate, western, mythology, steampunk
- **Player mode tags**: solo, cooperative, competitive, two-player
- **Platform tags**: tabletop, digital, print-and-play
- **Era tags**: classic, modern

Outputs `transcript_analytics.json` (gitignored) with per-video tags and aggregate stats. `build_showcase.py` then rebuilds `docs/content.html`, the year-by-year showcase.

## Steps

1. Run the analysis:
   ```
   python3 scripts/analyze_content.py --index video_index.json
   ```
   Use `--reanalyze` to re-process all videos (not just new ones).
   Use `--dry-run` to preview without writing.

   If it warns that videos have no curated classification, classify them first (`/refresh` step 2), then re-run.

2. Rebuild the showcase:
   ```
   python3 scripts/build_showcase.py --index video_index.json --stats youtube_stats.json --analytics transcript_analytics.json --dashboard docs/content.html
   ```
   It works without `youtube_stats.json`, but records, gems and view figures come out empty, so fetch stats first if they're missing.

3. Review and commit:
   ```
   git add docs/content.html
   git commit -m "analytics: updated content taxonomy (N videos analyzed)"
   git push origin main
   ```
   `transcript_analytics.json` is gitignored (the nightly re-derives it), so don't try to add it.

## When to run

- After each import cycle (the `/import` skill does NOT run this automatically; the nightly `/refresh` does)
- When taxonomy patterns in `scripts/analyze_content.py` are updated
- When you want to refresh the content dashboard with latest data

## Taxonomy design

Tags are organized into facets (format, mechanic, theme, mode, platform, era).
Each video can have multiple tags per facet. They feed `transcript_analytics.json`
(and so `/plan-batch`); the showcase page draws on the curated classification
instead.

## Extending the taxonomy

To change the curated vocabulary (formats, lanes, themes), edit `VOCAB` and the labels in `scripts/classify_videos.py`, then re-classify the affected videos. `apply` rejects values that aren't in `VOCAB`.

To add new regex tags, edit the pattern dictionaries in `scripts/analyze_content.py`:
- `FORMAT_PATTERNS` — content format tags
- `MECHANIC_PATTERNS` — game mechanic tags
- `THEME_PATTERNS` — setting/theme tags
- `MODE_PATTERNS` — player mode tags
- `PLATFORM_PATTERNS` — platform tags
- `ERA_PATTERNS` — era tags

To add known games to the matcher, add to the `KNOWN_GAMES` list.

After editing patterns, run with `--reanalyze` to reprocess all videos.

## Rules
- Do NOT hand-edit the data in `docs/content.html`. `build_showcase.py` rewrites everything between `// @showcase-data-begin` and `// @showcase-data-end`. The markup around it is a template and can be edited deliberately
- The analysis caches results; only new videos are analyzed by default
- Use `--reanalyze` after changing patterns to rebuild from scratch
- Series colours on the showcase are the validated dark categorical slots (`--s1`…`--s8` in content.html), fixed per lane
