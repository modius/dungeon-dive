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
6. Select a batch. Batch selection is now queue-driven — `/plan-batch` populates `series_queue.json`; `/import` drains it.

   **Selection decision tree:**

   1. **Ad-hoc priority.** Check for pending videos published in the last 14 days. If any exist, import them as an ad-hoc batch (no series entry), cap at 12, and **exit this run after posting** — do not drain the queue this session. Priority videos always jump the queue; the queue waits one cycle.

   2. **Drain the queue.** Only if no priority videos exist. If `series_queue.active_series` is non-empty and `active_series[rotation_index].video_ids` is non-empty:
      - Take the first `videos_per_batch` IDs from `video_ids`.
      - **Drift check:** for each ID, look it up in `video_index.json`. Skip any where `status != "pending"` (already imported, or `no_transcript`) — log skipped IDs to CHANGELOG. If an ID isn't found in `video_index.json` at all, that's an error; stop and surface it.
      - If after drift-check the slate is empty, skip this series (remove its remaining `video_ids`, move to `completed_series` with a note), advance `rotation_index`, and re-evaluate from step 2.
      - Otherwise, proceed to import the surviving IDs. Cap at 12.

   3. **Skip.** If no priority videos and the queue is empty (or fully drift-checked to nothing): do nothing, log "queue empty — run /plan-batch" to CHANGELOG, exit cleanly.

   **Unattended mode:** when `/import` is invoked by a scheduler (not interactively), the decision tree above is authoritative. Never start a new theme, never fabricate a batch by scanning titles, never ask for clarification. Priority, drain, or skip — in that order.

   **Interactive mode:** the user may override the selection at any point ("actually import these 5 instead"). Respect the override and skip queue mutation in step 12.

## Transcribe & Post

7. `python3 scripts/batch_fetch_transcripts.py VIDEO_ID1 VIDEO_ID2 ...`
   - The script writes structured failure records to `pending_imports/manifest.json` under the `failures` key, each with `error_type` and `permanent: true|false`.
   - **Permanent failures** (`permanent: true` — i.e. `TranscriptsDisabled`, `NoTranscriptFound`, `VideoUnavailable`): the video genuinely has no captions. Mark it as `no_transcript` in `video_index.json` and continue.
   - **Transient failures** (`permanent: false` — typically `RequestBlocked`, `IpBlocked`, `TooManyRequests`, `YouTubeRequestFailed`, network errors): DO NOT mutate the index. The video remains `pending`. Note in CHANGELOG which IDs hit transient errors and continue with whatever transcripts succeeded.
   - **Exit code 2** means the script bailed: more than half the batch hit transient failures, so the runner is almost certainly IP-blocked from YouTube. In that case: do NOT mark anything as `no_transcript`, log "transcript fetch blocked — runner IP issue" to CHANGELOG, abort the run cleanly without proceeding to post generation. The queue is unchanged so the next run will retry.
8. Generate post files for each video:
   - Read transcript from `pending_imports/`
   - Write 150-250 word summary per SKILL.md guidelines
   - Every post MUST use "Daniel (@dungeondive)" on its first mention of Daniel
   - Save to `ready_to_post/{video_id}_post.json` with `video_date` for backdating, `category: 8`
   - Validate all JSON files
9. `python3 scripts/batch_post.py --config config.json --input-dir ready_to_post`

## Keeper Post

10. Compose a Keeper post in The Keeper's voice — Vancian wry humour, atmospheric, thematic. This is a **teaser**, not an index: the per-video post summaries already do the analytical work. The Keeper's job here is to set atmosphere, frame the batch, and hook readers into clicking through.

    The format depends on the run type. There are two registers:

    **A. Series / archive batch (queue drain):**
    - **Target 400 words, hard cap 600 words.** Under the cap is fine; over it means cut.
    - Open with a short atmospheric framing paragraph (an arrival, a delivery, a rumour reaching the archive).
    - Group videos by sub-theme with one or two sentences of narrative per video — never a paragraph per video, never a full recap. If a video needs more than two sentences of set-up, the Keeper is doing the post summary's job.
    - Links in the flowing prose use the video title; no need for a separate exhibit catalogue when the batch is small (≤6). For larger batches, a terse linked list at the end is fine — but don't re-describe entries already mentioned above.

    **B. Priority drop (ad-hoc priority run, fresh uploads):**
    - **Target 100-200 words, hard cap 250 words.** This is an alert, not an essay. The aim is to flag that fresh material has arrived, not to summarise it — the per-video posts already exist for that.
    - One short atmospheric framing sentence or paragraph (a courier, a parcel, a despatch).
    - A linked list of the new videos with **at most one short sentence of hook** per entry — title-as-link, then a single phrase that gives the reader just enough to decide whether to click. No plot recap, no exhibit-catalogue prose.
    - Close with a one-line note that planned excavations resume next cycle.
    - Sign-off as below.

    Both registers share:
    - Sign off with:
      ```
      *NNN transcripts • NNN posts archived*

      -- The Keeper
      *[Witty observation]*
      ```
    - Save to `keeper-posts/keeper-THEME.md`
    - `python3 scripts/post_reply.py --config config.json --topic-id 1170 --body @keeper-posts/keeper-THEME.md`

**Note on The Keeper's voices:** there are three registers. (1) The per-video post summaries from step 8 — analytical, 150-250 words, encourage viewing the video. (2) The series Keeper archive update — atmospheric, 400-600 words, encourage browsing the forum thematically. (3) The priority-drop Keeper update — terse alert, 100-200 words, signals fresh arrivals without re-summarising them. Match the register to the run type. Don't conflate them.

## Wrap Up

11. `python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html`
12. Update `series_queue.json` (skip entirely if this was an ad-hoc priority run — priority videos never touch the queue — or an interactive user override):
    - **Drain:** remove the imported IDs from `active_series[rotation_index].video_ids`.
    - **Record progress:** increment `last_part`, set `last_imported` to today's date (YYYY-MM-DD), set `keeper_post` to the URL of the keeper reply just posted.
    - **Complete if drained:** if `video_ids` is now empty, remove the entry from `active_series` and append to `completed_series` with:
      - `parts_completed`: final `last_part` value
      - `total_videos`: sum of all videos imported across parts (track via a running counter, or count post files)
      - `completed_date`: today (YYYY-MM-DD)
      Drop fields that don't apply to completed entries (`video_ids`, `videos_per_batch`, `one_shot`, `status`, `last_imported`, `keeper_post`).
    - **Advance rotation:** if the entry was completed, advance `rotation_index`. If it now points past the end of `active_series`, wrap to 0. If `active_series` is empty, set to 0.
13. Update CHANGELOG.md with run summary.
14. Commit and push:
    ```
    git add video_index.json docs/index.html archive/ keeper-posts/ CHANGELOG.md series_queue.json
    git commit -m "sync: imported N videos (theme description)"
    git push origin main
    ```

## Rules
- Do NOT modify Python scripts unless explicitly asked
- If transcript fetch returns transient failures (IP block, rate limit, network), do NOT mark videos as `no_transcript` — they remain `pending` for the next run. Only `permanent: true` failures from `manifest.json` warrant the `no_transcript` flag.
- One Keeper post per run
- Quality over quantity: a themed batch of 5 is better than 12 random videos
- In **unattended mode**, if no queued batch and no priority videos, skip cleanly — never fabricate a theme
- In **interactive mode**, if the queue is empty, prompt the user to run `/plan-batch` rather than guessing
- Batch selection is queue-driven. The legacy title-scanning heuristic is gone — `/plan-batch` is the only source of non-priority batches.
