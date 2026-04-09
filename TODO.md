# TODO

## Integrity & Reconciliation

- [x] **Build `check_integrity.py`** — verify index, YouTube, Discourse, and local archive all agree on counts and status.
- [x] **Normalise transcript naming** — 12 legacy transcripts renamed via `repair_data.py rename`.
- [x] **Problem video index** — problem videos table added to health.html dashboard.
- [x] **Backfill missing timestamps** — 69 missing `imported_at` values recovered via `repair_data.py timestamps`.
- [x] **Recover missing post files** — 82 missing posts recovered from Discourse via `repair_data.py posts`.
- [ ] **Reconcile legacy imports** — 60 Discourse topics (of 279) don't match video IDs in the index. Need deep matching pass.
- [ ] **Recover missing transcripts** — 79 imported videos still missing transcripts. Run `repair_data.py transcripts --limit 5` in small batches (rate-limited by YouTube).

## Discourse Taxonomy & Tagging

- [ ] **Establish controlled taxonomy** — curated, limited tag set for Discourse posts (not free-form tag cloud). Determine facets: content category, format, primary game, theme.
- [ ] **Implement tag-pushing in `batch_post.py`** — apply taxonomy tags when posting to Discourse.
- [ ] **Back-tag existing posts** — bulk-apply controlled taxonomy to existing Discourse topics via API.
- [ ] **Flatten Discourse categories** — remove subcategories (Reviews, Gab Fests, All Fiction is Fantasy, Digital Spelunking), keep single "The Channel" category. Migrate posts first.

## All Fiction is Fantasy Channel Integration

- [ ] **Add AFIF channel** (UCZkRBpwZB7jtX_zz-gYUmTw, 51 videos) to video_index.json with `source_channel` field.
- [ ] **Cross-reference** 2 existing Discourse topics in category 9 to avoid duplicates.
- [ ] **Decide posting target** — category 5 (The Channel, flat) or category 9 (existing AFIF category).
- [ ] **Fetch transcripts and analyse** — run content analysis to understand natural groupings before committing to structure.

## Content Classification

- [ ] **LLM-based classification** — add Claude-powered content_category assignment during `/analyze` for higher accuracy than transcript heuristics.
- [ ] **Review borderline classifications** — some board game reviews with heavy fiction discussion (Elder Space, Wandering Galaxy) classified as "books" by transcript heuristics.
- [ ] **Upgrade keyword classifications** — as transcripts are recovered, re-run `/analyze` to upgrade keyword → transcript classifications (79 pending).

## Scheduled Task

- [x] **Full autonomous workflow** — prompt written, scripts built, tested end-to-end.
- [x] **Keeper post format** — defined and working.
- [ ] **Cloud environment network access** — Anthropic cloud proxy blocks `dungeondive.quest` and `googleapis.com`. Need domain allowlisting.
- [ ] **Local schedule fallback** — if cloud can't be resolved, set up local `/schedule` as interim.

## Dashboard

- [x] **Four-page dashboard** — Archive, Health, Content, Insights with Chart.js visualisations.
- [x] **Channel Insights page** — performance analytics, publishing patterns, coverage gaps, engagement depth, content category comparison with IQR box-plots, actionable suggestions.
- [x] **YouTube engagement data** — views, likes, comments, duration for all 1,012 videos via `fetch_youtube_stats.py`.
- [x] **Content taxonomy** — 338 videos analysed with game, format, mechanic, theme, mode, category tags.

## GitHub Integration

- [ ] **GitHub Issues for problem videos** — auto-create issues for videos with no subtitles.
- [ ] **PR-based sync workflow** — branch per sync run, PR with Keeper summary, auto-merge.
- [ ] **Retire file-based TODO/CHANGELOG** — once GitHub Issues and PRs are the audit trail.
