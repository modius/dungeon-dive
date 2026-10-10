---
name: backfill-transcripts
description: >
  Recover missing local transcripts for videos that are already imported (the
  "N imported videos missing local transcripts" warning from check_integrity.py),
  up to 10 per run within the transcript-fetch rate budget. Posts nothing.
  /import calls this on days with no priority videos and an empty queue; it can
  also be run by hand.
  Triggers: "backfill transcripts", "recover transcripts", "missing transcripts", "fetch missing transcripts"
---

Recover the transcripts that older imports never archived (79 as of 2026-10-10, most of them imported between mid-2024 and early 2025). They feed `/analyze` taxonomy, so recovering them improves the next `/refresh`. **Nothing is posted.** No Discourse topics, no Keeper post, no `series_queue.json` change, and no change to any video's `status`.

## Pre-flight

**When `/import` invokes this skill (`from-import` in the args), skip this section.** That run has already pulled, checked config and integrity, and passed the headroom figure in. Use that figure, and don't run the guard a second time.

Standalone runs:

1. `git pull origin main` with a clean tree, for the same reason as `/import` step 1: the nightly `/refresh` pushes `docs/*.html`, and this skill rewrites them.
2. `python3 scripts/check_rate_limit.py --max-videos 15`. Exit 1 means STOP. Note the headroom it prints. **Use 15, not the script's default of 20.** See `/import` step 2 for why: the IP block after a burst lasts ~24 h.
3. `python3 scripts/check_integrity.py --config config.json`. Exit 2 means STOP. Keep the report it writes; it gets committed with the run.
4. **Don't take the budget a real import needs.** If any video in `video_index.json` is `pending`, there's import work to do, so ask the user before spending the fetch budget here.

## Steps

1. **Size the slate:** `min(10, headroom)`. If headroom is under 3, stop: a backfill isn't worth pushing a near-exhausted window. The trade-off is that a 10-video backfill uses most of the 24 h budget, so a fresh upload in the next ~23 h may be refused and slip a day (priority videos stay `pending` and retry, so nothing is lost). That's why `/import` only backfills on days with no other work, and why this stops at 10 rather than the full 15.
2. **Pick candidates** in a Python snippet: `status == "imported"` in `video_index.json`, no `archive/transcripts/{id}_transcript.txt`, and **not listed in `archive/transcript_backfill.json`'s `unavailable` map** (videos already confirmed to have no captions; see step 5). Order by `published_at` descending, newest first, since recent videos matter most to the analytics, and take the slate size. If none are eligible, stop, and note in CHANGELOG that the backfill is complete.
3. **Fetch into a separate staging dir** so the main `pending_imports/manifest.json` isn't overwritten:
   ```
   python3 scripts/batch_fetch_transcripts.py --output-dir pending_imports/backfill -- ID1 ID2 ...
   ```
   Always pass `--`, because IDs can start with a hyphen. **Exit code 2** means the runner IP is blocked: don't probe or retry, write the rate manifest (step 6, since the requests were still made), log "transcript backfill blocked — runner IP issue", and commit as an aborted run.
4. **Archive the successes:** move each `pending_imports/backfill/{id}_transcript.txt` to `archive/transcripts/{id}_transcript.txt`, the same filename and content that `batch_post.py`'s `archive_files()` produces. Never overwrite an existing archive transcript. Leave the rest of `pending_imports/backfill/` alone (gitignored; `/repair cleanup` doesn't need to know about it).
5. **Record permanent failures** (`permanent: true` in `pending_imports/backfill/manifest.json`) in `archive/transcript_backfill.json` so later runs don't keep re-requesting them. Create the file if it's missing:
   ```json
   {"unavailable": {"VIDEO_ID": {"error_type": "TranscriptsDisabled", "checked_at": "2026-10-10"}}}
   ```
   Write it with `json.dump(..., indent=2, ensure_ascii=False)`. **Do not change `status` in `video_index.json`:** these videos are `imported`, with live topics, and `no_transcript` means "never posted". Transient failures are not recorded; those videos stay eligible for the next backfill.
6. **Write the rate manifest:** hand-write `archive/posts/post_results_<UTC YYYYMMDD_HHMMSS>.json` listing **every attempted ID**, successes and failures alike, because every fetch counts toward the burst:
   ```json
   {"posted_at": "2026-10-10T00:40:00Z", "kind": "transcript_backfill",
    "results": [{"video_id": "ID1", "status": "transcript_backfill"}, ...]}
   ```
   `check_rate_limit.py` counts `len(results)` across `post_results_*.json`, so skipping this hides the fetches from the guard and lets the next run blow the real budget.
7. **Rebuild the archive dashboards:** `python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html`. The transcript count and the health page's per-video archive data both change.
8. **CHANGELOG** heading `## YYYY-MM-DD — Queue empty — transcript backfill (N recovered)` (use `## YYYY-MM-DD — Transcript backfill (N recovered)` for a standalone run). When called from `/import`, this one entry covers the whole run, so open it with that run's pre-flight and selection notes, including "queue empty — run /plan-batch". Include the headroom figure, the IDs and titles attempted, how many were recovered, any permanent IDs added to the ledger, any transient IDs, and the remaining missing count. To get that count, re-run `check_integrity.py`, then delete the second integrity report rather than committing it.
9. **Validate, commit and push.** Run `/refresh`'s step 7 dashboard validation; it must print `dashboards validated`. Then:
   ```
   git add video_index.json docs/index.html docs/health.html archive/ CHANGELOG.md
   git commit -m "backfill: recovered N transcripts (M remaining)"
   git push origin main
   ```
   If the push is rejected, recover exactly as `/import` step 14 does: `git pull --rebase`, never `git reset --hard` (the commit carries archive transcripts), and resolve any `docs/*.html` conflict with `git checkout --ours`, regenerate, then validate. Check `git status` is clean before finishing.

## Rules
- Do **not** use `repair_data.py transcripts`. It runs the guard at the default 20, writes no rate manifest, and re-requests captionless videos forever.
- Never change a video's `status`. Captionless imported videos go in `archive/transcript_backfill.json`, not `no_transcript`.
- Always write the `post_results_*.json` rate manifest for every ID attempted, even on an aborted fetch.
- Cap at 10 per run and never exceed the guard's headroom. Don't run a second backfill in the same 24 h window to "finish the job".
- Leave `pending_imports/` alone at the end, as `/import` does.
- Do NOT modify Python scripts unless explicitly asked.
