---
name: repair
description: >
  Incrementally repair data issues in the archive. Fix missing timestamps,
  recover transcripts and post files, normalise legacy post records, rename
  legacy files, clean stale data.
  Triggers: "repair", "fix data", "clean up", "recover missing", "normalise records"
---

Incrementally fix known data problems in the Dungeon Dive archive.

## Steps

1. Always start with a report:
   ```bash
   python3 scripts/repair_data.py report
   ```

2. Run safe repairs (no API calls, no risk):
   ```bash
   python3 scripts/repair_data.py schema      # Normalize timestamp formats
   python3 scripts/repair_data.py rename      # Fix legacy transcript filenames
   python3 scripts/repair_data.py cleanup     # Sweep stale pending_imports
   ```

   **The `pending_imports/` sweep (`cleanup`).** `/import` stages a `{video_id}_meta.json` and `{video_id}_transcript.txt` per video in `pending_imports/`. On success `batch_post.py` archives the *transcript* but leaves the *meta* file behind, so meta files accumulate run after run — 384 of them had built up by 2026-08-07, which makes the directory useless to eyeball and buries the manifest. `cleanup` removes both files for any video whose `video_index.json` status is `imported` or `no_transcript`.

   Run it on **every** `/repair` invocation. It needs no flags, touches nothing outside `pending_imports/`, and the directory is gitignored — there is no state to lose and no reason to defer it.

   It deliberately keeps staging files for videos still `pending`: those are a half-finished run (transcript fetched, post not yet made), and the next `/import` reuses them rather than re-hitting the transcript API. Never clear the directory with a bare `rm` — that discards exactly those.

   `report` has surfaced this all along as `Stale pending_imports: N`, typically the largest number in the report. A non-zero count there is not a fault to investigate; it just means `cleanup` hasn't run yet.

3. Run API-backed repairs (low risk, uses Discourse API):
   ```bash
   python3 scripts/repair_data.py timestamps --config config.json   # Backfill missing imported_at
   python3 scripts/repair_data.py posts --config config.json --limit 10  # Recover missing post files
   ```

4. Bring legacy post files up to the canonical schema:
   ```bash
   python3 scripts/repair_data.py --dry-run normalize --config config.json   # always preview first
   python3 scripts/repair_data.py normalize --config config.json
   ```

   **What it fixes, and why the records were wrong.** Three deviations exist, all from older tooling:

   - **Body holds Discourse's rendered HTML** instead of the authored markdown — a youtube-onebox `<div>`, `<p>` wrappers, `<a class="mention">`. Every file written by the `posts` subcommand before 2026-08-28 has this, because `cmd_posts` stored `post_stream.posts[0].cooked`. 82 records were affected.
   - **`video_date` missing** — `cmd_posts` never wrote it. Backfilled from `video_index.json`'s `published_at` (*not* the Discourse `created_at`, which differs: `video_date` means the video's publish date).
   - **`category` missing, a name string, or an unverified nominal value** — 121 had no category, 33 held a *name* (`"Dungeon Diving"`), and 698 held `8`, which nothing ever read and which is in fact "Patreon".

   **The body is recovered from `raw`, never converted.** Discourse's topic endpoint exposes only `cooked` (rendered HTML); the original markdown lives on the per-post endpoint (`/posts/{id}.json` → `raw`). `normalize` reads `raw`, so the archived body is byte-for-byte what was published — there is no HTML-to-markdown translation step and nothing to get subtly wrong. `cmd_posts` was fixed at the same time to store `raw`, so recovery no longer mints HTML records.

   **A guard protects the permanent record.** A fetched body is written only if it contains `youtube.com/watch?v={video_id}` — the watch URL for *that* video. Anything else is skipped and reported rather than written, because the archive is the only copy of some of this text. Note the guard deliberately does **not** require the body to *open* with the link: a handful of legacy posts are owner-authored and introduce the video before linking it (e.g. `CVFIzDp5iio`), and an "opens with" test rejects them wrongly.

   **Category resolution is two-tier.** A bulk topic→category map is built by paging category listings (~40 requests, ~650-750 topics depending on listing depth), with a per-topic fetch as fallback. The listings do **not** cover the whole forum — roughly a third of the archive's topics have fallen off them — so the fallback is not optional.

   **Absence from the map is not evidence of a wrong value.** A stored int category is re-flagged only when the map actively *disagrees*. Treating a map miss as a fault made the subcommand non-idempotent: it re-fetched ~300 records on every run and never reported clean. To deliberately re-verify stored categories against Discourse per topic, pass `--verify-categories` (slow, and rarely needed after the initial sweep).

   **What `category` means.** It records the topic's real Discourse `category_id`. It is *not* read when posting — `batch_post.py` takes the category from `config.json` — so this field is a record of where a topic lives, not an instruction. Values in use across the archive: 5 The Channel (811), 6 The Channel/Reviews (29), 7 Gab Fests (12), 9 All Fiction is Fantasy (2), 12 Digital Spelunking (2).

   **It does not invent discussion questions.** Many legacy posts have no `----` question section because none was ever posted. Adding one would make the archive assert something that was never published. If a legacy topic should gain a question, that is an edit to the live Discourse post and a separate, deliberate decision.

   `--config` is optional: without it only the offline fixes run (a missing `video_date`), and records needing the API are reported and skipped. `--limit N` caps the run (default 0 = no limit); re-run to continue.

5. Run transcript recovery (HIGH risk — uses youtube-transcript-api):
   ```bash
   python3 scripts/repair_data.py transcripts --limit 5  # Conservative default
   ```

## Subcommands

| Subcommand | Risk | API Used |
|------------|------|----------|
| report | None | None |
| schema | None | None |
| rename | None | None |
| cleanup | None | None — run this every time |
| timestamps | Low | Discourse API |
| posts | Low | Discourse API |
| normalize | Low | Discourse API (optional) — idempotent; reports clean when done |
| transcripts | **HIGH** | youtube-transcript-api |

## Rules
- Always run `report` first to see what needs fixing
- Always run `cleanup` — it is free, and skipping it is why `pending_imports/` silently grows
- `--dry-run` is a **global** flag and must come *before* the subcommand: `repair_data.py --dry-run cleanup`, **not** `repair_data.py cleanup --dry-run`. The latter exits 2 with "unrecognized arguments" having done nothing. Same for `--index`, `--archive-dir` and `--pending-dir`; only `--config` and `--limit` are subcommand args and go after.
- The `transcripts` subcommand checks rate limits before starting
- Default `--limit 5` for transcripts is intentionally conservative
- Run safe subcommands freely; run `transcripts` only when there's headroom
- `normalize` rewrites files in `archive/posts/` — the permanent record. **Always `--dry-run` first** and check the target count and skip count look sane before the real run.
- A full `normalize` pass makes ~450 Discourse requests and takes several minutes. That is fine (Discourse has no practical limit at current volumes) but run it in the foreground and let it finish; a half-run archive is harder to reason about than an un-run one. `--limit` exists for deliberate incremental passes.
- Never "fix" a legacy post by writing content that was not published — no invented discussion questions, no rewritten summaries. `normalize` recovers what went out; it does not improve it.
