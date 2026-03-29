# TODO

## Integrity & Reconciliation

- [x] **Build `check_integrity.py`** — verify index, YouTube, Discourse, and local archive all agree on counts and status. Read-only, report-only.
- [ ] **Reconcile legacy imports** — 60 Discourse topics (of 279) don't match video IDs in the index. Likely older posts imported under different parameters or non-standard formats. Need deep matching pass.
- [ ] **Normalise transcript naming** — 12 transcripts use legacy `{video_id}.txt` instead of `{video_id}_transcript.txt`. Standardise naming.
- [x] **Problem video index** — problem videos table added to health.html dashboard.

## Scheduled Task

- [x] **Full autonomous workflow** — prompt written, scripts built, tested end-to-end locally (HeroQuest batch).
- [x] **Keeper post format** — defined and working. Target: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170 (post as reply via `post_reply.py`).
- [ ] **Cloud environment network access** — Anthropic cloud proxy blocks `dungeondive.quest` and `googleapis.com`. Need to resolve domain allowlisting for remote scheduled execution.
- [ ] **Local schedule fallback** — if cloud can't be resolved, set up local `/schedule` as interim.

## Dashboard

- [x] **Three-page dashboard** — Archive, Health, Content with Chart.js and Keeper art hero banners.
- [x] **Problem videos section** — added to health.html.
- [x] **Archive coverage stats** — coverage donuts on health.html, archive coverage card on index.html.
- [ ] **Content analytics expansion** — only 34 of 1008 transcripts analyzed. Expand `transcript_analytics.json` as more transcripts are processed.

## Taxonomy & Classification

- [ ] **Analyse transcripts for Dungeon Dive taxonomy** — process all available transcripts to extract a consolidated set of terms, topics, game names, and content types. Build a tight taxonomy for classifying posts (e.g., review, let's play, unboxing, interview, top 10, digital dive, etc.).
- [ ] **Discourse category mapping** — verify videos are posted to the correct Discourse subcategories. Interviews should go under GabFest, digital games under Digital Dive, etc. Cross-reference the taxonomy against existing category assignments and flag mismatches.

## Archive Backfill

- [ ] **Backfill missing transcripts** — 71 imported videos have no transcript in the local archive (processed before archiving was automated). Run a background task to re-fetch these transcripts from YouTube and add them to `archive/transcripts/`. This also feeds the taxonomy analysis.

## GitHub Integration (Next Session)

- [ ] **GitHub Issues for problem videos** — when integrity check finds a video with no subtitles, auto-create a GitHub issue tagged `problem-video` with title, YouTube link, and the problem. The YouTube manager can see, fix, and close the issue. Next sync run detects the fix.
- [ ] **PR-based sync workflow** — instead of committing to main, each sync run:
  1. Creates a branch (`sync/YYYY-MM-DD-theme`)
  2. Does all work on the branch
  3. Opens a PR with the Keeper summary as the description
  4. Auto-merges with `gh pr merge --auto --squash`
  This creates a permanent, browsable record of each sync run with rich diffs and the Keeper narrative.
- [ ] **Retire file-based TODO/CHANGELOG** — once GitHub Issues and PRs are the audit trail, these files become redundant. Migrate remaining TODO items to GitHub Issues.
