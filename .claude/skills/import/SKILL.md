---
name: import
description: >
  Run a full Dungeon Dive video archive import cycle. Fetches new videos from YouTube,
  selects a thematic batch, downloads transcripts, generates summaries, posts to Discourse,
  writes a Keeper update, and updates the dashboard.
  Triggers: "import", "sync", "run import", "archive sync"
---

Run a full Dungeon Dive video archive import cycle. Read SKILL.md for post format guidelines and keeper-posts/ for The Keeper's voice.

## Pre-flight

1. `git pull origin main`
2. `python3 scripts/check_rate_limit.py` — if exit 1, STOP (daily limit reached).
3. `python3 scripts/test_config.py --config config.json` — if fails, STOP.
4. `python3 scripts/check_integrity.py --config config.json` — if exit 2, STOP and log error.

## Fetch & Select

5. `python3 scripts/fetch_channel_videos.py --config config.json --index video_index.json`
6. Select a batch:
   - **PRIORITY**: Any videos published in the last 14 days that are still pending.
   - **SERIES CONTINUATION**: Check `series_queue.json` for active series with `"status": "continuing"`. The next archive batch MUST continue the series at `rotation_index` (0-based into the `active_series` array). After importing, advance `rotation_index` to the next active series (wrapping around). This ensures multi-part series alternate rather than being abandoned.
   - **NEW THEME**: Only start a new series if no active series remain (all completed) or if a compelling theme presents itself AND no series is overdue (last_imported > 14 days ago). When starting a new series, add it to `active_series` in `series_queue.json`.
   - **ARCHIVE** (fallback): If the rotation series has no good sub-theme available, choose a thematic group from older pending videos. Scan titles for game names, series, or topics. Pick a theme that makes a compelling Keeper post. Aim for 5-10 videos. If a theme has more, save the rest for the next run.
   - Check `keeper-posts/` to avoid themes already covered.
   - Total batch must not exceed 12 videos.

## Transcribe & Post

7. `python3 scripts/batch_fetch_transcripts.py VIDEO_ID1 VIDEO_ID2 ...`
   - If some fail (no subtitles), mark them as `no_transcript` in video_index.json and continue.
8. Generate post files for each video:
   - Read transcript from `pending_imports/`
   - Write 150-250 word summary per SKILL.md guidelines
   - Every post MUST use "Daniel (@dungeondive)" on its first mention of Daniel
   - Save to `ready_to_post/{video_id}_post.json` with `video_date` for backdating, `category: 8`
   - Validate all JSON files
9. `python3 scripts/batch_post.py --config config.json --input-dir ready_to_post`

## Keeper Post

10. Compose a Keeper post in The Keeper's voice — Vancian wry humour, atmospheric, thematic:
    - Group videos by theme with narrative commentary
    - Include new videos naturally
    - List all imported videos with links: `[Title](https://dungeondive.quest/t/TOPIC_ID)`
    - Sign off with:
      ```
      *NNN transcripts • NNN posts archived*

      -- The Keeper
      *[Witty observation]*
      ```
    - Save to `keeper-posts/keeper-THEME.md`
    - `python3 scripts/post_reply.py --config config.json --topic-id 1170 --body @keeper-posts/keeper-THEME.md`

## Wrap Up

11. `python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html`
12. Update `series_queue.json`:
    - If this batch continued an active series: increment `last_part`, update `videos_remaining`, `last_imported`, and `keeper_post`. If no videos remain, set `"status": "completed"` and move the entry to `completed_series`.
    - Advance `rotation_index` to the next active series (wrap to 0 if past the end).
    - If a new series was started: add it to `active_series`.
13. Update CHANGELOG.md with run summary.
14. Commit and push:
    ```
    git add video_index.json docs/index.html archive/ keeper-posts/ CHANGELOG.md series_queue.json
    git commit -m "sync: imported N videos (theme description)"
    git push origin main
    ```

## Rules
- Do NOT modify Python scripts unless explicitly asked
- If rate limited on transcripts, import what you have and note it in CHANGELOG.md
- One Keeper post per run
- Quality over quantity: a themed batch of 5 is better than 12 random videos
- If no new videos and no good theme presents itself, skip and note why in CHANGELOG.md
