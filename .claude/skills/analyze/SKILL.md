---
name: analyze
description: >
  Run content analysis on imported videos to build taxonomy tags and update
  the content analytics dashboard. Extracts games, formats, mechanics,
  themes, player modes, and generates tag cloud data.
  Triggers: "analyze", "analyze content", "run analysis", "update taxonomy", "tag videos"
---

Analyze imported video content and update the content analytics dashboard.

## What it does

Reads post summaries and transcripts for all imported videos to extract:
- **Games**: Primary game subject + cross-referenced mentions
- **Format tags**: review, overview, lets-play, deep-dive, unboxing, comparison, top-list, crowdfund-preview, tutorial, discussion, digital-dive, buyers-guide
- **Mechanic tags**: dungeon-crawler, rpg, campaign, miniatures, deck-builder, hex-crawl, dice-game, sandbox, card-game, wargame, press-your-luck, tile-laying, tower-defense
- **Theme tags**: fantasy, horror, sci-fi, post-apocalyptic, pirate, western, mythology, steampunk
- **Player mode tags**: solo, cooperative, competitive, two-player
- **Platform tags**: tabletop, digital, print-and-play
- **Era tags**: classic, modern

Outputs `transcript_analytics.json` with per-video tags and aggregate stats.
Updates `docs/content.html` with tag cloud, game rankings, theme/mode charts.

## Steps

1. Run the analysis:
   ```
   python3 scripts/analyze_content.py --index video_index.json
   ```
   Use `--reanalyze` to re-process all videos (not just new ones).
   Use `--dry-run` to preview without writing.

2. Update dashboards:
   ```
   python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html
   ```
   This updates all three pages (index, health, content) including the new analytics.

3. Review and commit:
   ```
   git add transcript_analytics.json docs/content.html
   git commit -m "analytics: updated content taxonomy (N videos analyzed)"
   git push origin main
   ```

## When to run

- After each import cycle (the `/import` skill does NOT run this automatically)
- When taxonomy patterns in `scripts/analyze_content.py` are updated
- When you want to refresh the content dashboard with latest data

## Taxonomy design

Tags are organized into facets (format, mechanic, theme, mode, platform, era).
Each video can have multiple tags per facet. The tag cloud on content.html
shows all tags sized by frequency, colour-coded by facet:

- **Blue** (#818cf8): Content format
- **Green** (#34d399): Game mechanics
- **Gold** (#fbbf24): Settings/themes
- **Pink** (#f472b6): Player modes
- **Light blue** (#60a5fa): Platform
- **Warm gold** (#d4a853): Era

## Extending the taxonomy

To add new tags, edit the pattern dictionaries in `scripts/analyze_content.py`:
- `FORMAT_PATTERNS` — content format tags
- `MECHANIC_PATTERNS` — game mechanic tags
- `THEME_PATTERNS` — setting/theme tags
- `MODE_PATTERNS` — player mode tags
- `PLATFORM_PATTERNS` — platform tags
- `ERA_PATTERNS` — era tags

To add known games to the matcher, add to the `KNOWN_GAMES` list.

After editing patterns, run with `--reanalyze` to reprocess all videos.

## Rules
- Do NOT modify the dashboard HTML structure — only embedded data constants
- The analysis caches results; only new videos are analyzed by default
- Use `--reanalyze` after changing patterns to rebuild from scratch
- Tag cloud colours are defined in content.html's `tagColors` object
