---
name: refresh
description: >
  Refresh all Dungeon Dive analytics in one pass — classify new videos, content
  taxonomy, YouTube engagement stats, the committed view history, and the
  showcase + insights dashboards. Chains analyze, fetch-stats, and
  channel-insights into a single run.
  Triggers: "refresh", "refresh analytics", "refresh dashboards", "update everything"
---

Refresh all Dungeon Dive analytics: classification, taxonomy, YouTube stats, view history, and the showcase/insights dashboards.

**`/refresh` is the only writer of `video_classification.json` and `stats_history/`.** Both are committed, and both are written here and pushed in the same run. `/import` and `/fetch-stats` deliberately don't touch them. With a single writer, a local run and the nightly run can never both append to the same file.

## Steps

### 1. Sync with remote

```bash
git pull origin main
```

**Run this first, before generating anything.** A nightly scheduled `/refresh` also pushes `docs/*.html`, so this repo regularly has a refresh commit waiting that you do not have locally. Pull while the tree is still clean — once steps 2–4 have rewritten the dashboards, `git pull` refuses to run ("local changes would be overwritten") and you are stuck reconciling generated HTML by hand.

### 2. Classify new videos

```bash
python3 scripts/classify_videos.py missing --index video_index.json --out /tmp/dd_unclassified.json
```

It prints how many videos (imported **or** pending) have no record in `video_classification.json`, and prints the classification rules when there are any. Usually that's 0–3 a day. If it's 0, skip to step 3.

Otherwise read `/tmp/dd_unclassified.json` (id, date, minutes, title, summary) and classify each row **yourself, from the title and summary, using the printed rules**. Don't use a keyword script: format, lane and series are judgement calls, and that judgement is why this file exists. Before choosing names, open `video_classification.json` and reuse its existing spelling for any `subject`, `franchise` or `series` that already appears. A second spelling splits a subject's history in two on the showcase. Write the records with Python `json.dump` (never the Write tool) as an object mapping video id → record, then:

```bash
python3 scripts/classify_videos.py apply /tmp/dd_records.json
```

`apply` refuses the whole file if any value is outside the closed vocabularies. Fix the record and re-run it; don't edit `VOCAB` to make a value fit.

### 3. Analyze content taxonomy

```bash
python3 scripts/analyze_content.py --index video_index.json
```

Tags all imported videos with game, format, mechanic, theme, player mode, platform, and era facets, and copies each video's curated classification (subject, primary format, lane, solo focus, series) into `transcript_analytics.json`. Only processes new/untagged videos by default. If it warns that videos have no curated classification, step 2 was skipped. Go back and do it.

**Add `--reanalyze` after any change to the tagging logic** (`KNOWN_GAMES`, `AMBIGUOUS_GAME_NAMES`, the extractors in `analyze_content.py`). Cached tags are never revisited otherwise, so a fix silently applies to new videos only and the dashboards keep serving the old numbers. Costs ~40s for the full archive and touches no APIs.

**Use `--reanalyze` on a local run too, whenever the local cache is more than a day or two old.** The nightly `/refresh` runs from a clean clone, and `transcript_analytics.json` is gitignored — so the nightly has no cache and re-derives all 877 videos from scratch every time. A local incremental run does not reproduce that: cached entries keep tags derived from transcripts that have since gone missing from `archive/transcripts/`, so the local dashboard carries tags the nightly cannot regenerate and silently reverts the next day. Verified 2026-09-05: incremental output held 11 extra tags across 11 videos (`review`, `crowdfund-preview`, `discussion`, `tutorial`, `rpg`, `miniatures`, `hex-crawl`, `wargame`), and **all 11 were among the 79 imported videos with no local transcript**. Reproducibility beats the richer-but-unregenerable cache — match the nightly, and fix the cause with `/repair transcripts`.

> **The 79 missing transcripts are the real defect here, not the tagging.** `check_integrity.py` has been reporting `warn` with the recommendation "79 imported videos missing local transcripts" — 42 of them from 2024. Those videos are tagged from title and description alone, every night, on the published dashboards. Treat a rising count as a data-loss signal, not noise.

### 4. Fetch YouTube engagement stats

```bash
python3 scripts/fetch_youtube_stats.py --config config.json --index video_index.json --output youtube_stats.json --max-age-hours 24
```

Pulls views, likes, comments, and duration for all videos. Skips videos refreshed within 24 hours. Uses ~0.2% of daily API quota.

### 5. Record the view history

```bash
python3 scripts/stats_history.py snapshot --stats youtube_stats.json --index video_index.json
```

Appends today's counts to `stats_history/YYYY-MM.csv`: every video under 90 days old, and older ones once a week. The snapshot is dated by the stats' `last_fetched` (UTC). Re-running on the same day replaces that day's rows rather than duplicating them. This history is the only source of age-fair signals: launch curves, the evergreen rate, and weekly channel views per day. `youtube_stats.json` is overwritten on every fetch, so a day without a snapshot is lost for good. (History from 2026-04-09 to 2026-10-02 was backfilled from the git log of `docs/insights.html` with `stats_history.py backfill`. That's a one-off; don't re-run it.)

### 6. Rebuild all dashboards

```bash
python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html
python3 scripts/build_insights.py --index video_index.json --stats youtube_stats.json --analytics transcript_analytics.json --dashboard docs/insights.html
python3 scripts/build_showcase.py --index video_index.json --stats youtube_stats.json --analytics transcript_analytics.json --dashboard docs/content.html
```

`update_dashboard.py` updates the archive pages (index, health). `build_insights.py` writes the recommendations page. `build_showcase.py` writes the channel showcase (`content.html`). The last two embed one data blob each, between `// @…-data-begin` / `// @…-data-end` markers. They rewrite only that blob, so the page markup is a hand-maintained template.

### 7. Validate the generated dashboards

**Run this before `git add`.** Step 8 stages `docs/*.html` by path and commits whatever is on disk — it never looks at the contents. On 2026-10-02 a `git stash pop` left conflict markers inside the inline `<script>` of `docs/insights.html`; the refresh committed and pushed them, and because one syntax error kills the whole script block, **every chart, table and panel on the live insights page rendered blank for ~11 hours.** Nothing in the pipeline noticed.

```bash
python3 - <<'PY'
import pathlib, re, subprocess, sys
bad = []
for name in ("index", "content", "health", "insights"):
    f = pathlib.Path(f"docs/{name}.html")
    if not f.exists():
        continue
    text = f.read_text(encoding="utf-8")
    for marker in ("<<<<<<< ", ">>>>>>> "):
        if re.search("^" + re.escape(marker), text, re.M):
            bad.append(f"{f}: merge conflict markers")
            break
    else:
        # one syntax error in the inline script blanks the entire page
        for script in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", text, re.S):
            if not script.strip():
                continue
            try:
                r = subprocess.run(["node", "--check", "-"], input=script,
                                   capture_output=True, text=True)
            except FileNotFoundError:
                print("note: node not found - skipped JS parse check")
                break
            if r.returncode != 0:
                err = next((l.strip() for l in r.stderr.splitlines() if "Error" in l),
                           "syntax error")
                bad.append(f"{f}: inline script fails to parse - {err}")
                break
if bad:
    print("REFUSING TO COMMIT:")
    for b in bad:
        print("  -", b)
    sys.exit(1)
print("dashboards validated")
PY
```

If it fails, **do not hand-edit the HTML** — discard and regenerate, per the conflict rule below:

```bash
git checkout -- docs/   # or: git stash drop, if a pop caused it
```

Then re-run step 6 and validate again.

### 8. Commit and push

```bash
git add docs/index.html docs/content.html docs/health.html docs/insights.html stats_history/ video_classification.json
git commit -m "insights: refreshed engagement data (N videos, N total views)"

git push origin main
```

**`N videos` means the analyzed count**, the figure `analyze_content.py` prints in step 3 ("Analyzed 877 videos"), i.e. imported videos carrying taxonomy. It is **not** the figure `fetch_youtube_stats.py` prints in step 4 ("Fetched stats for 1060 videos (6 new, 1054 updated)"), which counts the whole channel including pending. Past runs mixed the two, so the history reads 842 → 850 → 856 → **1057** → 870 → 875, and the jumps look like data loss when nothing was wrong. `N total views` is the "total views" line from step 6's insights output. Not committing `docs/index.html` is normal — it only changes when `video_index.json` does, i.e. after an `/import`, not after a `/refresh`.

Note: `youtube_stats.json` is gitignored — do not commit it.

**If the push is rejected** (`! [rejected] main -> main (fetch first)`), a concurrent refresh landed while this run was working. Do NOT hand-merge or `--force` — `docs/*.html` are generated files and a conflict in them is meaningless to resolve by hand. Regenerate instead:

```bash
git reset --hard HEAD~1          # drop your commit; the dashboards are regenerable
git pull --ff-only origin main   # take the other run's commit
```

> This reset is safe **only because a `/refresh` commit contains nothing that can't be regenerated**: dashboards, plus classification records and snapshot rows that steps 2 and 5 rebuild. Do not carry it over to `/import`, whose commit holds the archive, live Discourse topic IDs, and the Keeper post — that one recovers with `git pull --rebase`.

Then re-run steps 2, 5 and 6 and commit again. The reset discarded this run's classification records and snapshot rows. Step 2 regenerates whatever the pulled `video_classification.json` still lacks, and step 5 re-records today's snapshot on top of the other run's. Your local `youtube_stats.json` survives the reset (it is gitignored), so the rebuilt dashboards carry whichever data is fresher — compare the total-views figure in the other run's commit message against yours to confirm which that is. History stays linear and no data is lost.

## When to run

- After `/import` to update analytics with newly imported videos
- Periodically to refresh YouTube engagement numbers
- Before presenting channel performance data to Daniel

## Rules
- Do NOT commit youtube_stats.json (volatile engagement data, gitignored). DO commit `stats_history/` and `video_classification.json`. They are the durable record, and only this skill writes them
- Classify new videos by judgement (step 2), never with a keyword script, and reuse existing subject/series spellings
- Steps must run in order — insights depends on fresh taxonomy and stats
- Safe to run multiple times per day
- Always pull before generating (step 1) — a nightly `/refresh` shares this branch and touches the same generated files
- Never resolve a conflict in `docs/*.html` by hand; discard and regenerate
- Never commit `docs/*.html` without running step 7 — a committed conflict marker or JS syntax error blanks the whole live page silently
