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

### Verify Setup

```bash
python3 scripts/test_config.py --config config.json
```

## Manual Workflow

```bash
# 1. Fetch latest videos from YouTube
python3 scripts/fetch_channel_videos.py --config config.json --index video_index.json

# 2. Sync status with Discourse
python3 scripts/sync_discourse_status.py --config config.json --index video_index.json

# 3. Fetch transcripts (batch)
python3 scripts/batch_fetch_transcripts.py --config config.json --index video_index.json --limit 10

# 4. Post to Discourse (after generating summary files in ready_to_post/)
python3 scripts/batch_post.py --config config.json --input-dir ready_to_post --dry-run
python3 scripts/batch_post.py --config config.json --input-dir ready_to_post
```

See [SKILL.md](SKILL.md) for the full workflow, post format guidelines, and Claude integration details.

## Automated Sync (Claude Code Schedule)

The project can run autonomously via a scheduled Claude Code task.

### Schedule Setup

From Claude Code CLI:

```
/schedule create dd-sync
```

### Schedule Prompt

```
You are maintaining the Dungeon Dive video archive. Read SKILL.md for instructions.

1. git pull
2. Fetch latest videos from YouTube
3. Fetch up to 12 transcripts for pending videos (prefer thematic groupings)
4. Generate Discourse post files following SKILL.md format
5. Post to Discourse using batch_post.py
6. Update docs/index.html dashboard
7. Log the run in CHANGELOG.md
8. Commit and push all changes

If rate limited on transcripts, commit what you have and note it in the changelog.
Do NOT modify the Python scripts unless explicitly asked.
```

### Rate Limits

- **YouTube transcript API:** ~12-15 fetches before IP throttle (resets in ~1 hour)
- **Discourse API:** No practical limit at current volumes
- **Recommended frequency:** Daily or every few days

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
│   ├── import/SKILL.md
│   ├── analyze/SKILL.md
│   ├── fetch-stats/SKILL.md
│   ├── repair/SKILL.md
│   └── insights/SKILL.md
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
| `/import` | `import`, `sync` | Full import cycle: fetch videos, select themed batch, transcribe, generate summaries, post to Discourse, write Keeper update, update dashboards |
| `/analyze` | `analyze`, `run analysis` | Content taxonomy analysis: extract games, formats, mechanics, themes, player modes from transcripts; update tag cloud and content dashboard |
| `/fetch-stats` | `fetch stats`, `get youtube stats` | Fetch YouTube engagement data (views, likes, comments, duration) via Data API. Safe to run frequently — uses 0.2% of daily quota |
| `/repair` | `repair`, `fix data` | Incremental data repair: fix timestamps, rename legacy files, clean stale data, recover missing posts/transcripts |
| `/insights` | `insights`, `build insights` | Build channel insights dashboard with performance analytics, publishing patterns, coverage gaps, and actionable suggestions |

Skill definitions live in `.claude/skills/*/SKILL.md`.

## Current Stats

- **1012** videos indexed
- **338** imported to Discourse
- **259** transcripts archived
- **338** posts archived
