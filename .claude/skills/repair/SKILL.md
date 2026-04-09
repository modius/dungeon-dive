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
   python3 scripts/repair_data.py cleanup     # Remove stale pending_imports
   ```

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
| cleanup | None | None |
| timestamps | Low | Discourse API |
| posts | Low | Discourse API |
| transcripts | **HIGH** | youtube-transcript-api |

## Rules
- Always run `report` first to see what needs fixing
- Use `--dry-run` to preview changes
- The `transcripts` subcommand checks rate limits before starting
- Default `--limit 5` for transcripts is intentionally conservative
- Run safe subcommands freely; run `transcripts` only when there's headroom
