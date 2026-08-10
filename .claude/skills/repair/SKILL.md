---
name: repair
description: >
  Incrementally repair data issues in the archive. Fix missing timestamps,
  recover transcripts and post files, rename legacy files, clean stale data.
  Triggers: "repair", "fix data", "clean up", "recover missing"
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

4. Run transcript recovery (HIGH risk — uses youtube-transcript-api):
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
| transcripts | **HIGH** | youtube-transcript-api |

## Rules
- Always run `report` first to see what needs fixing
- Always run `cleanup` — it is free, and skipping it is why `pending_imports/` silently grows
- `--dry-run` is a **global** flag and must come *before* the subcommand: `repair_data.py --dry-run cleanup`, **not** `repair_data.py cleanup --dry-run`. The latter exits 2 with "unrecognized arguments" having done nothing. Same for `--index`, `--archive-dir` and `--pending-dir`; only `--config` and `--limit` are subcommand args and go after.
- The `transcripts` subcommand checks rate limits before starting
- Default `--limit 5` for transcripts is intentionally conservative
- Run safe subcommands freely; run `transcripts` only when there's headroom
