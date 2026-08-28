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

1. `git pull origin main` — **before anything else generates a file.** A nightly `/refresh` pushes `docs/*.html` to this same branch, and once step 11 has rewritten the dashboards a plain `git pull` refuses to run ("local changes would be overwritten"). Pulling here, while the tree is clean, is the only cheap moment. It does not eliminate the race — this run holds the branch from step 1 to step 14, which on a full batch is many minutes — so see the recovery note on step 14.
2. `python3 scripts/check_rate_limit.py` — if exit 1, STOP (daily limit reached).
3. `python3 scripts/test_config.py --config config.json` — if fails, STOP.
4. `python3 scripts/check_integrity.py --config config.json` — if exit 2, STOP and log error.

## Fetch & Select

5. `python3 scripts/fetch_channel_videos.py --config config.json --index video_index.json`
   - **A `requests.exceptions.SSLError` / `SSLEOFError` against `www.googleapis.com` mid-pagination is transient — just re-run the command unchanged.** The script collects every `playlistItems` page before it writes anything, so an aborted run leaves `video_index.json` untouched and a retry is safe (and costs no more quota than the first attempt). Don't be misled by the traceback: it's a wall of `requests` internals with the API key visible in the URL, which reads like a credentials or quota failure and is neither. If a second attempt also fails, treat it as a network/upstream problem and abort the run — do not proceed to selection on a stale index.
6. Select a batch. Batch selection is now queue-driven — `/plan-batch` populates `series_queue.json`; `/import` drains it.

   **Selection decision tree:**

   1. **Ad-hoc priority.** Check for pending videos published in the last 14 days. If any exist, import them as an ad-hoc batch (no series entry), cap at 12, and **exit this run after posting** — do not drain the queue this session. Priority videos always jump the queue; the queue waits one cycle.

   2. **Drain the queue.** Only if no priority videos exist. If `series_queue.active_series` is non-empty and `active_series[rotation_index].video_ids` is non-empty:
      - Take the first `videos_per_batch` IDs from `video_ids`.
      - **Drift check:** for each ID, look it up in `video_index.json`. Skip any where `status != "pending"` (already imported, or `no_transcript`) — log skipped IDs to CHANGELOG. If an ID isn't found in `video_index.json` at all, that's an error; stop and surface it.
      - If after drift-check the slate is empty, skip this series (remove its remaining `video_ids`, move to `completed_series` with a note). Do NOT increment `rotation_index` — removal already shifts the next series into the current slot; just wrap to 0 if the index is now past the end, then re-evaluate from step 2.
      - Otherwise, proceed to import the surviving IDs. Cap at 12.

   3. **Skip.** If no priority videos and the queue is empty (or fully drift-checked to nothing): do nothing, log "queue empty — run /plan-batch" to CHANGELOG, exit cleanly.

   **Unattended mode:** when `/import` is invoked by a scheduler (not interactively), the decision tree above is authoritative. Never start a new theme, never fabricate a batch by scanning titles, never ask for clarification. Priority, drain, or skip — in that order.

   **Interactive mode:** the user may override the selection at any point ("actually import these 5 instead"). Respect the override and skip queue mutation in step 12.

## Transcribe & Post

7. `python3 scripts/batch_fetch_transcripts.py -- VIDEO_ID1 VIDEO_ID2 ...`
   - **Always pass `--` before the video IDs.** YouTube IDs can start with a hyphen (e.g. `-FJcDEQ2CB0`); without the `--` separator, argparse treats such an ID as an unknown flag and exits 2 having fetched nothing. The `--` is harmless when no ID starts with a dash, so use it every time.
   - The script writes structured failure records to `pending_imports/manifest.json` under the `failures` key, each with `error_type` and `permanent: true|false`.
   - **Permanent failures** (`permanent: true` — i.e. `TranscriptsDisabled`, `NoTranscriptFound`, `VideoUnavailable`): the video genuinely has no captions. Mark it as `no_transcript` in `video_index.json` and continue.
   - **Transient failures** (`permanent: false` — typically `RequestBlocked`, `IpBlocked`, `TooManyRequests`, `YouTubeRequestFailed`, network errors): DO NOT mutate the index. The video remains `pending`. Note in CHANGELOG which IDs hit transient errors and continue with whatever transcripts succeeded.
   - **Exit code 2** means the script bailed: more than half the batch hit transient failures, so the runner is almost certainly IP-blocked from YouTube. In that case: do NOT mark anything as `no_transcript`, log "transcript fetch blocked — runner IP issue" to CHANGELOG, abort the run cleanly without proceeding to post generation. The queue is unchanged so the next run will retry.
8. Generate post files for each video:
   - Read transcript from `pending_imports/`
   - Write 150-250 word summary per SKILL.md guidelines
   - Every post MUST use "Daniel (@dungeondive)" on its first mention of Daniel
   - Save to `ready_to_post/{video_id}_post.json` with `video_date` for backdating, `category: 5`
   - **`category` is not read by `batch_post.py`** — it takes the category from `config.json` (5, "The Channel"). Write 5 so the record matches where the topic actually lands. The long-standing `category: 8` was dead data and factually wrong (8 is "Patreon").
   - Validate all JSON files
9. `python3 scripts/batch_post.py --config config.json --input-dir ready_to_post`

## Keeper Post

10. Compose a Keeper post in The Keeper's voice — Vancian wry humour, atmospheric, thematic. This is a **teaser**, not an index: the per-video post summaries already do the analytical work. The Keeper's job here is to set atmosphere, frame the batch, and hook readers into clicking through.

    The format depends on the run type. There are two registers:

    **A. Series / archive batch (queue drain):**
    - **Target 250-400 words of body prose, hard cap 500. The Exhibit Catalogue, stats line and sign-off do NOT count toward that budget** — catalogue length scales with batch size (a 16-entry catalogue runs ~300 words on its own), so a total-word cap would squeeze the prose to nothing on large slates. Budget the prose; let the catalogue be as long as the slate demands. The body prose is *atmospheric framing only* — it does NOT walk through each video. The Exhibit Catalogue at the bottom carries the per-video hooks.
    - Body prose: open with an atmospheric arrival/delivery/rumour, name the series, gesture at the overall arc in one or two short paragraphs. ~150-250 words is plenty. If you find yourself describing what's *in* a specific video, stop and move that detail to the catalogue hook for that video.
    - **Always include an "Exhibit Catalogue" linked list near the bottom**, regardless of batch size. Place it between the closing prose and the stats/sign-off. Each entry: bullet, link with the video title, em-dash, one short hook phrase (≤15 words) that brings out *one* interesting highlight from that video. The hook is the reader's lure to click through — make it specific, not generic. The per-video Discourse posts already contain the analytical 150-250 word summaries; the Keeper does not duplicate that work.
    - **The catalogue is an integrated thematic index, not just a per-batch index.** If the queue entry has a non-empty `related_imported_ids`, those previously-imported videos are part of the *same* Exhibit Catalogue alongside the just-imported ones — single list, no second section, no visual distinction between "new" and "existing" entries. The reader gets one coherent thematic tour of the subject. Resolve each related-imported ID via `video_index.json` using its recorded `discourse_topic_id` to build `https://dungeondive.quest/t/<discourse_topic_id>` links.
      - **Where to read topic IDs for the just-imported videos:** `video_index.json`. `batch_post.py` writes each fresh `discourse_topic_id` into the index as it posts, so after step 9 the whole catalogue — new and pre-existing alike — resolves from that one file. Do *not* expect `ready_to_post/post_results.json` to still be there: the same script archives it to `archive/posts/post_results_<timestamp>.json` on success, so the path in `ready_to_post/` is gone by the time you compose.
      - **Where to get hooks for the pre-existing entries:** you did not read those transcripts this run, so read `archive/posts/<video_id>_post.json` and pull the hook from the summary body already written for that video. Never invent a specific detail for a video you haven't read — a vague hook is a bug, but a fabricated one is worse.
    - **Catalogue ordering: chronological by publish date** (the videos' YouTube `published_at` / per-post `video_date`), regardless of when they were imported. This reflects the channel's actual timeline and lets the catalogue read as a sub-thematic history. Example: a batch importing Parts 1, 2, 4, 5, 6 with Part 3 already in the archive renders the catalogue as 1 → 2 → 3 → 4 → 5 → 6, all six linking to their topics, the reader unable to tell which was imported when.
    - Editorial selection of related-imported IDs is fixed at queue time by `/plan-batch`; do NOT add to or substitute the list at composition. The queue rule already caps `related_imported_ids` at 5.
    - **Multi-part series reuse the same `related_imported_ids` in every part, and that is intended — include them again.** A series drained over two or more runs will list the identical related entries in each part's catalogue. Do not drop them from later parts to avoid repetition and do not swap in different ones: each Keeper post must stand alone as a complete thematic tour for a reader who only sees that one. What you *should* vary is the wording — write the hooks fresh from `archive/posts/<video_id>_post.json` rather than copying the phrasing out of the previous part's Keeper post, so someone reading both gets a different lure for the same topic.

    **B. Priority drop (ad-hoc priority run, fresh uploads):**
    - **Target 100-200 words, hard cap 250 words.** This is an alert, not an essay. The aim is to flag that fresh material has arrived, not to summarise it — the per-video posts already exist for that.
    - One short atmospheric framing sentence or paragraph (a courier, a parcel, a despatch).
    - A linked list of the new videos with **at most one short sentence of hook** per entry — title-as-link, then a single phrase that gives the reader just enough to decide whether to click. No plot recap, no exhibit-catalogue prose.
    - **"From the deeper stacks" cross-reference** (when warranted): immediately after the new-arrivals list, include a short follow-up section with **1–3** thematically related videos already in the archive. The framing is "if this caught your eye, here are a couple from the dark distant past in the same vein." Same bullet format as the new-arrivals list: title-as-link, em-dash, one short hook phrase.
      - How to find candidates: extract the priority video's central subjects (game name, designer, franchise, mechanic, theme) from its title and post summary, then scan `video_index.json` for `status == "imported"` entries whose titles match those subjects. If `transcript_analytics.json` exists, prefer videos that share taxonomy tags. Pick the 1–3 strongest matches (a clear game-name or franchise overlap beats a vague genre overlap).
      - Build links via the matched videos' `discourse_topic_id`: `https://dungeondive.quest/t/<discourse_topic_id>`.
      - **Quality over quantity.** If nothing in the archive is a genuine fit, **omit the section entirely** — don't pad with weak matches. A priority drop with no cross-reference is fine.
      - The 1–3 cap, the alert register, and the 250-word hard cap still apply with the cross-reference section included.
    - Close with a one-line note that planned excavations resume next cycle.
    - Sign-off as below.

    Both registers share:
    - Sign off with:
      ```
      *NNN transcripts • NNN posts archived*

      -- The Keeper
      *[Witty observation]*
      ```
      **Where the two numbers come from** (these go into a public post — get them right):
      - **transcripts** = `ls archive/transcripts/ | wc -l`
      - **posts archived** = the `imported` count in `video_index.json`, equivalently `ls archive/posts/*_post.json | wc -l`

      Do **not** use a bare `ls archive/posts/ | wc -l` — that directory also holds ~120 `post_results_*.json` run manifests and overstates the count by that much. Both numbers must be read *after* `batch_post.py` has run (it archives the transcript and post files on success), and the Keeper post is composed before `update_dashboard.py`, so don't wait for the dashboard's "Archive: N transcripts, N posts" line — use it afterwards as a cross-check instead.
    - Save to `keeper-posts/keeper-THEME.md`
    - `python3 scripts/post_reply.py --config config.json --topic-id 1170 --body @keeper-posts/keeper-THEME.md`

**Note on The Keeper's voices:** there are three registers. (1) The per-video post summaries from step 8 — analytical, 150-250 words, encourage viewing the video. (2) The series Keeper archive update — atmospheric, 250-400 words of prose (cap 500, catalogue excluded — see register A above), encourage browsing the forum thematically. (3) The priority-drop Keeper update — terse alert, 100-200 words, signals fresh arrivals without re-summarising them. Match the register to the run type. Don't conflate them.

## Wrap Up

11. `python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html`
12. Update `series_queue.json` (skip entirely if this was an ad-hoc priority run — priority videos never touch the queue — or an interactive user override):
    - **Drain:** remove the imported IDs from `active_series[rotation_index].video_ids`. **Also remove any ID from this run's slate that hit a `permanent: true` transcript failure** — it was just marked `no_transcript` and can never become importable, so leaving it in `video_ids` only forces a wasted rotation where the next run drift-checks the slate to nothing. Removing it now reaches the same end state one cycle earlier. Note the dropped ID and its reason in the `completed_series` entry (or CHANGELOG if the series continues). IDs that hit **transient** failures stay in `video_ids` — they're still `pending` and will retry.
    - **Record progress:** increment `last_part`, set `last_imported` to today's date (YYYY-MM-DD), set `keeper_post` to the URL of the keeper reply just posted.
    - **Complete if drained:** if `video_ids` is now empty, remove the entry from `active_series` and append to `completed_series` with:
      - `parts_completed`: final `last_part` value
      - `total_videos`: sum of all videos imported across parts (track via a running counter, or count post files)
      - `completed_date`: today (YYYY-MM-DD)
      - `keeper_post`: retain the URL of the final part's Keeper reply (provenance — lets you find the announcement for a completed series)
      Drop fields that don't apply to completed entries (`video_ids`, `videos_per_batch`, `one_shot`, `status`, `last_imported`).
    - **Advance rotation:**
      - **If the entry was completed (removed from `active_series`):** do NOT increment `rotation_index`. Removing the entry already shifts every later entry forward one slot, so the same index now points at what was the *next* series — incrementing on top of that skips a series. Only clamp: if `rotation_index` is now past the end of `active_series`, wrap to 0; if `active_series` is empty, set to 0.
      - **If the entry was NOT completed (multi-part, still has `video_ids`):** increment `rotation_index` for round-robin fairness so the next run rotates to the following series. If it now points past the end, wrap to 0.
13. Update CHANGELOG.md with run summary.
14. Commit and push:
    ```
    git add video_index.json docs/index.html docs/content.html docs/health.html archive/ keeper-posts/ CHANGELOG.md series_queue.json
    git commit -m "sync: imported N videos (theme description)"
    git push origin main
    ```

    **Stage all three dashboards, not just `docs/index.html`.** Step 11's `update_dashboard.py` regenerates `docs/content.html` and `docs/health.html` as well. Leaving them unstaged doesn't fail this run — it fails the *next* one, whose step-1 `git pull` aborts with "local changes would be overwritten" against the nightly `/refresh`'s dashboard commit. Check `git status` is clean (bar untracked scratch dirs) before you finish.

    **If the push is rejected** (`! [rejected] main -> main (fetch first)`), a concurrent run — usually the nightly `/refresh` — landed while this import was working. Rebase; do not reset:

    ```
    git pull --rebase origin main
    ```

    > **Never use `/refresh`'s `git reset --hard HEAD~1` recovery here.** That advice is safe in `/refresh` because its commit contains only regenerable dashboards. An `/import` commit does not: it carries `archive/posts/` and `archive/transcripts/` (the permanent record), the `discourse_topic_id` values written into `video_index.json` for topics that are **already live on Discourse**, the Keeper post, the drained `series_queue.json`, and the CHANGELOG. Discarding that commit loses work that re-running cannot recreate — the posts exist remotely, so a second run would not repost them, and the index would no longer know their topic IDs.

    The only file both runs touch is `docs/*.html`, so that is the only place the rebase can conflict. Resolve it by regenerating, never by hand-editing the HTML:

    ```
    python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html
    git add docs/index.html docs/content.html docs/health.html
    git rebase --continue
    ```

    Then push again. If the rebase conflicts in any file *other* than `docs/*.html`, stop and surface it — that means two runs mutated the archive or the queue concurrently, which is not a case to resolve automatically.

## Rules
- Do NOT modify Python scripts unless explicitly asked
- Recover from a rejected push with `git pull --rebase`, never `git reset --hard` — an `/import` commit contains the archive, live topic IDs, and the Keeper post, none of which a re-run can recreate
- Never resolve a conflict in `docs/*.html` by hand; regenerate with `update_dashboard.py` and continue the rebase
- Leave `pending_imports/` alone at the end of a run — `/repair`'s `cleanup` subcommand owns sweeping it, and it keeps staging files for still-`pending` videos on purpose so a half-finished run can resume without re-hitting the transcript API. Never `rm` the directory to tidy it.
- If transcript fetch returns transient failures (IP block, rate limit, network), do NOT mark videos as `no_transcript` — they remain `pending` for the next run. Only `permanent: true` failures from `manifest.json` warrant the `no_transcript` flag.
- One Keeper post per run
- Quality over quantity: a themed batch of 5 is better than 12 random videos
- In **unattended mode**, if no queued batch and no priority videos, skip cleanly — never fabricate a theme
- In **interactive mode**, if the queue is empty, prompt the user to run `/plan-batch` rather than guessing
- Batch selection is queue-driven. The legacy title-scanning heuristic is gone — `/plan-batch` is the only source of non-priority batches.
