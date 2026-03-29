# TODO

## Integrity & Reconciliation

- [x] **Build `check_integrity.py`** — verify index, YouTube, Discourse, and local archive all agree on counts and status. Read-only, report-only.
- [ ] **Reconcile legacy imports** — 60 Discourse topics (of 279) don't match video IDs in the index. Likely older posts imported under different parameters or non-standard formats. Need deep matching pass.
- [ ] **Normalise transcript naming** — 12 transcripts use legacy `{video_id}.txt` instead of `{video_id}_transcript.txt`. Standardise naming.
- [ ] **Problem video index** — build a visualization of YouTube-side issues (missing subtitles, fetch failures) shareable with the Dungeon Dive team.

## Scheduled Task

- [ ] **Full autonomous workflow** — the scheduled task should:
  1. Run integrity check
  2. Fetch new videos from YouTube
  3. Select which pending videos to process (thematic groupings, priority)
  4. Fetch transcripts
  5. Generate promotional summaries
  6. Post to Discourse with backdating
  7. Create a Keeper post summarising the run, posted to the dedicated Dungeon Dive video archive topic
- [ ] **Keeper post format** — define the format and target topic for automated Keeper posts. Target: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170 (post as reply)

## Dashboard

- [ ] **Problem videos section** — add a section to the dashboard showing videos with issues
- [ ] **Archive coverage stats** — show transcript/post coverage percentages
