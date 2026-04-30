# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Automated sync of The Dungeon Dive YouTube channel (`UCKW6yMwL_aEu83g6DdjVfxw`) to the [dungeondive.quest](https://dungeondive.quest) Discourse forum, with a public dashboard at [modius.io/dungeon-dive](https://modius.io/dungeon-dive/). Python scripts do the wire work; Claude Code skills orchestrate them, write commit messages, and compose Keeper posts in voice. **Skills are the primary interface — direct script invocation is for debugging.**

## Skill-driven workflow (the common path)

Run from a Claude Code session in this repo:

1. **`/refresh`** — pulls fresh analytics (taxonomy, engagement, insights). Cheap (~30s, 0.2% YouTube quota). Run before `/plan-batch` so signals are current.
2. **`/plan-batch`** — proposes 2–4 candidate batches; on user pick, writes explicit `video_ids` slates into `series_queue.json`. **Never imports.**
3. **`/import`** — drains the queue: fetch, transcribe, post per-video, compose Keeper update, update dashboards, commit, push. **One Keeper post per run.**

If the queue is already populated, skip `/plan-batch`. If queue is empty AND no priority videos in last 14 days, `/import` skips cleanly and notes "queue empty — run /plan-batch" in CHANGELOG.

Utility skills: `/fetch-stats`, `/analyze`, `/channel-insights` (subsets of `/refresh`); `/repair` for incremental data fixes.

Skill definitions live in `.claude/skills/*/SKILL.md`. Read them when modifying behaviour — `import/SKILL.md` is the most prescriptive.

## Architecture: state files are the contract

The system is mostly stateless scripts coordinating around a few JSON files. Understanding what each owns is essential:

| File | Owner | Role | Committed? |
|------|-------|------|------------|
| `video_index.json` | source of truth | every video's status (`pending`/`imported`/`skipped`/`no_transcript`), Discourse topic ID, timestamps | **yes** |
| `series_queue.json` | `/plan-batch` writes, `/import` drains | active_series with explicit `video_ids`, completed_series log, rotation_index | **yes** |
| `youtube_stats.json` | `/fetch-stats` | engagement data; volatile | **no** (gitignored) |
| `transcript_analytics.json` | `/analyze` | per-video taxonomy tags; computed | **no** (gitignored) |
| `config.json` | user | API keys (YouTube, Discourse) | **no** (gitignored) |
| `pending_imports/`, `ready_to_post/` | transient working dirs | transcript + post staging | **no** (gitignored except `.gitkeep`) |
| `archive/transcripts/`, `archive/posts/` | post-success archive | committed permanent record | **yes** |
| `keeper-posts/keeper-*.md` | per-batch Keeper post bodies | committed | **yes** |
| `docs/*.html` | dashboards | rebuilt by `update_dashboard.py` / `build_insights.py` | **yes** |

**Selection logic in `/import` (decision tree, in order):**
1. **Priority** — pending video in last 14 days → ad-hoc batch (cap 12), exit after posting; queue waits one cycle.
2. **Queue drain** — first `videos_per_batch` IDs from `active_series[rotation_index].video_ids`, drift-checked against `video_index.json` (skip non-pending).
3. **Skip** — log empty-queue note to CHANGELOG, exit.

Priority videos never mutate `series_queue.json`. Interactive user overrides also skip queue mutation.

## Post format (CRITICAL — read before editing post-related code)

Per-video Discourse posts (in `ready_to_post/{video_id}_post.json`) MUST use this schema for backdating:

```json
{
  "video_id": "abc123",
  "title": "Video Title",
  "video_date": "2024-06-15T14:00:00Z",
  "body": "https://www.youtube.com/watch?v=abc123\n\n[Summary]\n\n----\n\n[Discussion question]",
  "category": 8
}
```

Use `video_date`, not `created_at`. `batch_post.py` uses `video_date` for backdating.

Body structure: YouTube link → 150–250 word summary → `----` → discussion question. Every post's first mention of Daniel must be **"Daniel (@dungeondive)"** (subsequent mentions just "Daniel"). This applies per-post, not per-batch.

## The Keeper's three voices (don't conflate them)

1. **Per-video summary** (step 8 of `/import`) — analytical, 150–250 words, encourages viewing the video.
2. **Series Keeper update** (queue drain) — atmospheric Vancian wry humour, **target 400 words / hard cap 600**, encourages thematic forum browsing. Group videos by sub-theme, 1–2 sentences narrative each, never a paragraph per video.
3. **Priority drop** (ad-hoc fresh upload run) — terse alert, **target 100–200 words / hard cap 250**. Linked list of new videos with one short hook each. Close with "planned excavations resume next cycle."

All three sign off:
```
*NNN transcripts • NNN posts archived*

-- The Keeper
*[Witty, thematic one-liner in italics]*
```

`keeper-posts/` holds prior posts — read 2–3 recent ones before composing to stay in voice.

## Commands

```bash
# Setup verification
python3 scripts/test_config.py --config config.json

# Archive integrity (run before/after imports; exit 2 = stop)
python3 scripts/check_integrity.py --config config.json

# Rate limit guard for transcript fetches (exit 1 = skip the run)
python3 scripts/check_rate_limit.py

# Raw script invocations (skills wrap these — rarely needed manually)
python3 scripts/fetch_channel_videos.py --config config.json --index video_index.json
python3 scripts/batch_fetch_transcripts.py VIDEO_ID1 VIDEO_ID2 ...
python3 scripts/batch_post.py --config config.json --input-dir ready_to_post [--dry-run]
python3 scripts/update_dashboard.py --index video_index.json --dashboard docs/index.html
python3 scripts/build_insights.py --index video_index.json --stats youtube_stats.json --analytics transcript_analytics.json --series series_queue.json --dashboard docs/insights.html
python3 scripts/post_reply.py --config config.json --topic-id 1170 --body @keeper-posts/keeper-THEME.md
python3 scripts/repair_data.py {timestamps|posts|transcripts|rename} ...
```

Dependencies: `pip3 install -r requirements.txt` (just `requests` and `youtube-transcript-api`).

## Rate limits to respect

- **YouTube transcript API:** ~12–15 fetches before IP throttle (~1h reset). The 12-video cap in `/import` stays under this.
- **YouTube Data API:** ~0.2% of daily quota per `/fetch-stats` — safe to run frequently.
- **`check_rate_limit.py`:** enforces a video-count quota per 24h locally (default 20 videos posted in the period); respect its exit code. The video count is the meaningful unit — a 1-video priority drop and a 12-video drain don't deserve equal weight.
- **Discourse:** no practical limit at current volumes.

## Workflow rules (from SKILL.md, easy to violate)

- Do **not** start generating the next batch of posts while `ready_to_post/` still has unposted files. Sequence is: generate → user runs `batch_post.py` → user confirms → post-batch checklist (index, dashboard, archive).
- Always write post JSON via Python `json.dump()`, never the `Write` tool — escaping bites otherwise.
- `docs/index.html` stores video data as a compact pipe-delimited template literal: `id|title|date|status|topicId` per line in `_raw`. Parse + rewrite in Python; never `sed` it.
- `yearData` counts are **total videos per year**, not just imported. Update from index totals.
- One Keeper post per `/import` run.
- Do not modify `scripts/*.py` unless explicitly asked — skills assume their CLIs are stable.

## What not to commit

`config.json` (API keys), `youtube_stats.json` and `transcript_analytics.json` (volatile/computed), `pending_imports/*` and `ready_to_post/*` (transient staging). `.gitignore` is the authoritative list.

## Key external IDs

- Discourse keeper-thread topic ID for archive updates: **1170** (used by `post_reply.py` for Keeper posts)
- Discourse category for per-video posts: **8** (set in post JSON)
- Discourse category in `config.json`: **5** ("The Channel")
