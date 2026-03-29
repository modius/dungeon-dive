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

<https://modius.github.io/dungeon-dive/>

## External Services

| Service | URL | Purpose |
|---------|-----|---------|
| YouTube Channel | [The Dungeon Dive](https://www.youtube.com/@TheDungeonDive) (`UCKW6yMwL_aEu83g6DdjVfxw`) | Source content |
| Discourse Forum | [dungeondive.quest](https://dungeondive.quest) | Target for posts (category ID 5) |
| GitHub Pages | [modius.github.io/dungeon-dive](https://modius.github.io/dungeon-dive/) | Public dashboard |

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
├── docs/                     GitHub Pages root (dashboard)
│   └── index.html
├── scripts/                  Python scripts
│   ├── fetch_channel_videos.py
│   ├── batch_fetch_transcripts.py
│   ├── batch_post.py
│   ├── get_transcript.py
│   ├── post_to_discourse.py
│   ├── sync_discourse_status.py
│   ├── build_index_from_csv.py
│   ├── backdate_batch3.py
│   └── test_config.py
├── archive/
│   ├── transcripts/          Downloaded transcript text files
│   └── posts/                Post metadata JSON files
├── pending_imports/          Transient working directory (gitignored)
├── ready_to_post/            Staging for posts awaiting publish (gitignored)
├── keeper-posts/             Curated keeper announcement posts
├── assets/
│   ├── post-template.md      Post body template
│   └── references/
│       └── api-setup.md      API key setup guide
├── video_index.json          Source of truth for all video status
├── config.json               API credentials (gitignored)
├── config.template.json      Credential template
├── SKILL.md                  Claude Code skill instructions
├── CHANGELOG.md              Sync run log
└── requirements.txt          Python dependencies
```

## Current Stats

- **1007** videos indexed
- **276** imported to Discourse
- **205** transcripts archived
- **213** posts archived
