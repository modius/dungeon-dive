# Dungeon Dive Archive

Automated sync of YouTube videos from The Dungeon Dive channel to the
[dungeondive.quest](https://dungeondive.quest) Discourse forum, with a public
dashboard tracking progress.

## What This Does

- Indexes all videos from the Dungeon Dive YouTube channel
- Fetches transcripts and generates promotional summaries
- Posts backdated topics to the Discourse forum
- Maintains a public dashboard showing sync progress

## Live Dashboard

<https://modius.io/dungeon-dive/>

## External Services

| Service | URL | Purpose |
|---------|-----|---------|
| YouTube Channel | [The Dungeon Dive](https://www.youtube.com/@TheDungeonDive) (`UCKW6yMwL_aEu83g6DdjVfxw`) | Source content |
| Discourse Forum | [dungeondive.quest](https://dungeondive.quest) | Target for posts (category ID 5) |
| GitHub Pages | [modius.github.io/dungeon-dive](https://modius.io/dungeon-dive/) | Public dashboard |

## Setup

### Prerequisites

- Python 3.x
- pip packages: `pip install -r requirements.txt`
- [Claude Code](https://claude.com/claude-code) CLI (for scheduled automation)

### API Keys (config.json)

Copy `config.template.json` to `config.json` and fill in your credentials:

```bash
cp config.template.json config.json
```

| Key | Where to get it |
|-----|----------------|
| `youtube.api_key` | [Google Cloud Console](https://console.cloud.google.com/) &rarr; APIs & Services &rarr; YouTube Data API v3 |
| `discourse.api_key` | dungeondive.quest &rarr; Admin &rarr; API &rarr; Create New Key |
| `discourse.api_username` | The Discourse user to post as (currently `thekeeper`) |

See [`assets/references/api-setup.md`](assets/references/api-setup.md) for detailed setup instructions.

> **Warning:** `config.json` is gitignored. Never commit API keys.

### Environment variables (cloud / scheduled runs)

When running in an environment where `config.json` cannot be present (cloud schedulers, CI, ephemeral containers), `scripts/config_utils.py` falls back to environment variables. If `--config` points to a missing file, env vars are used instead.

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `YOUTUBE_API_KEY` | for YouTube fetch / stats | — | Same value as `youtube.api_key` |
| `YOUTUBE_CHANNEL_ID` | no | `UCKW6yMwL_aEu83g6DdjVfxw` | The Dungeon Dive channel |
| `DISCOURSE_URL` | for Discourse posting | — | e.g. `https://dungeondive.quest` |
| `DISCOURSE_API_KEY` | for Discourse posting | — | Admin key for backdating support |
| `DISCOURSE_USERNAME` | for Discourse posting | — | e.g. `thekeeper` |
| `DISCOURSE_CATEGORY_ID` | no | `5` | The Channel category |

Discourse requires all three of `DISCOURSE_URL`, `DISCOURSE_API_KEY`, `DISCOURSE_USERNAME` together — partial setups fail loudly with a clear error rather than crashing downstream.

### Verify Setup

```bash
python3 scripts/test_config.py --config config.json
```

## Operator Workflow

The project is driven by Claude Code skills. You rarely need to run scripts directly — the skills chain the scripts together, handle state files, and write commit messages for you.

### The common path — "I want to import some videos"

Run these skills in order from a Claude Code session in this repo:

1. **`/refresh`** — pulls fresh analytics: content taxonomy, YouTube engagement, insights dashboard. Cheap (~30s, 0.2% of YouTube quota). Do this first so `/plan-batch` has up-to-date signals.
2. **`/plan-batch`** — proposes 2–4 candidate batches based on taxonomy, engagement, untapped topics, and series state. You pick one (or several); the skill writes them into `series_queue.json` as explicit `video_ids` slates.
3. **`/import`** — drains the queue: fetches new YouTube videos, transcribes the queued slate, writes per-video posts to Discourse, composes the Keeper archive update, updates dashboards, commits, pushes. One Keeper post per run.

If the queue is already populated (e.g. you planned yesterday, executing today), skip `/plan-batch` — `/import` will drain whatever is at `active_series[rotation_index]`.

If nothing is queued **and** there are no pending videos from the last 14 days, `/import` will skip cleanly and note the empty queue in CHANGELOG — run `/plan-batch` first.

### Utility skills (use when needed)

| Skill | When |
|-------|------|
| `/fetch-stats` | Refresh engagement numbers only (subset of `/refresh`). |
| `/analyze` | Rebuild the taxonomy only (subset of `/refresh`). Run with `--reanalyze` inside the skill when patterns change. |
| `/channel-insights` | Rebuild the insights dashboard only (subset of `/refresh`). |
| `/repair` | Something is broken — missing posts, stale timestamps, orphaned transcripts. Incremental fixes. |

### Raw scripts (reference)

Skills invoke these under the hood. Rarely needed by operators, but useful for debugging:

```bash
python3 scripts/test_config.py --config config.json          # verify API keys
python3 scripts/check_integrity.py --config config.json      # archive self-check
python3 scripts/fetch_channel_videos.py --config config.json --index video_index.json
python3 scripts/batch_fetch_transcripts.py VIDEO_ID1 VIDEO_ID2 ...
python3 scripts/batch_post.py --config config.json --input-dir ready_to_post
python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html
```

### Rate limits

- **YouTube transcript API:** ~12-15 fetches before IP throttle (resets in ~1 hour). The 12-video batch cap in `/import` stays within this.
- **YouTube Data API (stats):** 0.2% of daily quota per `/fetch-stats` run — safe to run frequently.
- **Discourse API:** No practical limit at current volumes.
- **Recommended frequency:** every few days while there's a backlog; weekly otherwise.

## Scheduled / Unattended Imports

`/import` is designed to be schedule-safe. In unattended mode it:
- Drains the next queued batch from `series_queue.json`, **or**
- Imports any pending videos from the last 14 days (ad-hoc priority), **or**
- Skips cleanly and logs "queue empty — run /plan-batch" to CHANGELOG.

It never fabricates a theme on its own. Pre-plan batches with `/plan-batch` so the scheduler has work to do.

## Project Structure

```
dungeon-dive/
├── docs/                     GitHub Pages root (dashboards)
│   ├── index.html            Archive overview dashboard
│   ├── health.html           System health dashboard
│   ├── content.html          Content analytics dashboard
│   └── insights.html         Channel insights dashboard
├── scripts/
│   ├── fetch_channel_videos.py    Fetch video index from YouTube
│   ├── fetch_youtube_stats.py     Fetch engagement data (views, likes, duration)
│   ├── batch_fetch_transcripts.py Batch transcript download
│   ├── batch_post.py              Post to Discourse
│   ├── analyze_content.py         Content taxonomy analysis
│   ├── build_insights.py          Compute channel insights
│   ├── update_dashboard.py        Update all dashboard pages
│   ├── check_integrity.py         Archive integrity checks
│   ├── check_rate_limit.py        Rate limit guard
│   ├── repair_data.py             Incremental data repair
│   └── test_config.py             Config validation
├── .claude/skills/           Claude Code skill definitions
│   ├── plan-batch/SKILL.md   Propose & queue candidate batches
│   ├── import/SKILL.md       Drain queue & run full import cycle
│   ├── refresh/SKILL.md      Chain analyze + fetch-stats + insights
│   ├── analyze/SKILL.md      Content taxonomy tagging
│   ├── fetch-stats/SKILL.md  YouTube engagement data
│   ├── channel-insights/SKILL.md  Rebuild insights dashboard
│   └── repair/SKILL.md       Incremental data repair
├── archive/
│   ├── transcripts/          Downloaded transcript text files
│   └── posts/                Post metadata JSON files
├── keeper-posts/             Themed Keeper announcement posts
├── video_index.json          Source of truth for all video status
├── series_queue.json         Active/completed series rotation
├── youtube_stats.json        Engagement data (gitignored, volatile)
├── transcript_analytics.json Content taxonomy tags (gitignored, computed)
├── config.json               API credentials (gitignored)
├── CHANGELOG.md              Sync run log
└── requirements.txt          Python dependencies
```

## Claude Code Skills

The project includes purpose-built skills invoked via Claude Code slash commands:

| Skill | Trigger | Purpose |
|-------|---------|---------|
| `/plan-batch` | `plan batch`, `propose batch`, `next batch` | Propose 2–4 candidate batches using taxonomy, engagement, and series state. On user pick, queues the slate(s) into `series_queue.json`. Proposal + queue write only — never imports. |
| `/import` | `import`, `sync` | Drain the next queued batch: transcribe, generate per-video summaries, post to Discourse, compose Keeper archive update, update dashboards, commit, push. Falls back to ad-hoc priority (last 14 days) if queue is empty. |
| `/refresh` | `refresh`, `refresh analytics` | Chains `/analyze` + `/fetch-stats` + `/channel-insights` into one pass. Run before `/plan-batch` for fresh signals. |
| `/analyze` | `analyze`, `run analysis` | Content taxonomy analysis: extract games, formats, mechanics, themes, player modes from transcripts; update tag cloud and content dashboard. |
| `/fetch-stats` | `fetch stats`, `get youtube stats` | Fetch YouTube engagement data (views, likes, comments, duration) via Data API. Safe to run frequently — uses 0.2% of daily quota. |
| `/channel-insights` | `channel insights`, `build insights` | Build channel insights dashboard with performance analytics, publishing patterns, coverage gaps, and actionable suggestions. |
| `/repair` | `repair`, `fix data` | Incremental data repair: fix timestamps, rename legacy files, clean stale data, recover missing posts/transcripts. |

Skill definitions live in `.claude/skills/*/SKILL.md`.

## Current Stats

- **1015** videos indexed
- **393** imported to Discourse
- **314** transcripts archived
- **393** posts archived

(Live counts on the [dashboard](https://modius.io/dungeon-dive/).)
