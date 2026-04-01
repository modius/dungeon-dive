---
name: youtube-discourse-sync
description: >
  Synchronise YouTube channel videos to a Discourse forum. Maintains an index of all channel videos,
  tracks import status, fetches transcripts, generates promotional summaries, and creates backdated
  Discourse topics. Use this skill when: (1) refreshing the video catalogue, (2) browsing/searching
  unimported videos, (3) importing specific videos to Discourse, (4) checking sync status.
  Triggers: "sync videos", "import video", "refresh catalogue", "show unimported", "dungeon dive archive"
---

# YouTube to Discourse Sync

Synchronise YouTube videos from the Dungeon Dive channel to dungeondive.quest Discourse forum.

## Quick Reference

| Command | Action |
|---------|--------|
| "Refresh the video catalogue" | Fetch new videos from YouTube |
| "Sync with Discourse" | Check what's already imported in Discourse |
| "Show unimported videos" | List pending videos |
| "Search for videos about [topic]" | Filter by title/description |
| "Import [video title or URL]" | Create Discourse topic for video |
| "Check sync status" | Show import statistics |

## Full Refresh Workflow

To get an up-to-date view of what needs importing:

```bash
# 1. Get latest videos from YouTube
python3 scripts/fetch_channel_videos.py --config config.json --index video_index.json

# 2. Check what's already in Discourse
python3 scripts/sync_discourse_status.py --config config.json --index video_index.json

# 3. View the dashboard or query the index
```

## Setup

Before first use, ensure configuration is complete:

1. Read `assets/references/api-setup.md` for API key setup
2. Create `config.json` in the workspace folder
3. Run `scripts/test_config.py --config config.json` to verify

## File Locations

- **Config**: `config.json` (user's workspace)
- **Index**: `video_index.json` (user's workspace)
- **Scripts**: `scripts/` directory in this skill folder

## Workflows

### 1. Refresh Video Catalogue

Fetch all videos from the YouTube channel and update the local index.

```bash
python3 scripts/fetch_channel_videos.py --config config.json --index video_index.json
```

For a complete refresh (re-fetch all):
```bash
python3 scripts/fetch_channel_videos.py --config config.json --index video_index.json --full-refresh
```

### 2. Browse Unimported Videos

Load `video_index.json` and filter for `status: "pending"`. Present as a table:

| # | Title | Published | Description (truncated) |
|---|-------|-----------|------------------------|

Allow user to select by number or search by keyword.

### 3. Search Videos

Filter the index by matching against `title` and `description` fields. Case-insensitive substring match.

### 4. Import a Video

For each video to import:

1. **Get video details** from index by title match or video ID
2. **Fetch transcript**:
   ```bash
   python3 scripts/get_transcript.py VIDEO_ID
   ```
3. **Generate summary**: Using the transcript, write a 150-250 word promotional summary following the template in `assets/post-template.md`
4. **Compose post body**:
   ```
   https://www.youtube.com/watch?v=VIDEO_ID

   ---

   [Generated summary]

   ---

   *This video was originally published on [date].*
   ```
5. **Create Discourse topic**:
   ```bash
   python3 scripts/post_to_discourse.py --config config.json \
     --title "Video Title" \
     --body @post_body.txt \
     --video-date "2024-06-15T14:00:00Z"
   ```
6. **Update index**: Set `status: "imported"`, record `discourse_topic_id` and `imported_at`

### 5. Batch Import (Streamlined)

**Step 1: Fetch transcripts** (user runs once)
```bash
# Fetch 5 pending videos from 2025
python3 scripts/batch_fetch_transcripts.py \
  --from-index pending --year 2025 --limit 5

# Or fetch specific videos
python3 scripts/batch_fetch_transcripts.py VIDEO_ID1 VIDEO_ID2 VIDEO_ID3
```

This creates `pending_imports/` with transcript files and metadata.

**Step 2: Generate summaries** (Claude does this)
Tell Claude: "Process the transcripts in pending_imports and generate post files"

Claude will:
- Read all `*_transcript.txt` and `*_meta.json` files
- Generate promotional summaries for each
- Save ready-to-post files to `ready_to_post/`

**Step 3: Post to Discourse** (user runs once)
```bash
# Preview first
python3 scripts/batch_post.py \
  --config config.json --input-dir ready_to_post --dry-run

# Then post for real
python3 scripts/batch_post.py \
  --config config.json --input-dir ready_to_post
```

This creates all topics, **automatically backdates them** to `video_date`, and updates the index.

**Step 4: Update Dashboard** (Claude does this after user confirms posting)

Claude MUST update `docs/index.html` after each batch:
1. Update stats: `total`, `imported`, `pending` counts
2. Update archive counts: transcripts and posts local
3. Add new videos to `allVideos` array with status "imported" and topicId
4. Move posted files from `ready_to_post/` to `archive/posts/`

### 6. Manual Single Import (Alternative)

For importing one video at a time:

```bash
# Fetch transcript
python3 scripts/get_transcript.py VIDEO_ID --output /tmp/transcript.txt

# Share transcript with Claude to generate summary, then post:
python3 scripts/post_to_discourse.py --config config.json \
  --title "Video Title" --body @post_body.txt --video-date "2024-06-15T14:00:00Z"
```

## Claude: Processing Pending Imports

When user asks to "process pending imports":

1. Read `pending_imports/manifest.json` for list of videos
2. For each video, read `{video_id}_transcript.txt` and `{video_id}_meta.json`
3. Generate a promotional summary (150-250 words)
4. Save post file to `ready_to_post/{video_id}_post.json`:
   ```json
   {
     "video_id": "abc123",
     "title": "Video Title",
     "video_date": "2024-06-15T14:00:00Z",
     "body": "https://www.youtube.com/watch?v=abc123\n\n---\n\n[Summary]..."
   }
   ```
5. Create `ready_to_post/manifest.json` with all posts
6. Tell user to run `batch_post.py --dry-run` then without dry-run

## Post File Format (CRITICAL)

Post files in `ready_to_post/` MUST use this exact format for backdating to work:

```json
{
  "video_id": "abc123",
  "title": "Video Title",
  "video_date": "2024-06-15T14:00:00Z",
  "body": "https://www.youtube.com/watch?v=abc123\n\n[Summary content]...",
  "category": 8
}
```

⚠️ **Required fields for backdating**:
- `video_id` — needed for index updates
- `video_date` — the original YouTube publish date (batch_post.py uses this to backdate)

Do NOT use `created_at` — use `video_date`.

## Post Body Format (CRITICAL)

Every post MUST follow this structure:

```
https://www.youtube.com/watch?v={{VIDEO_ID}}

[Summary paragraphs - see guidelines below]

----

[Discussion prompt - a question to encourage community engagement]
```

### Complete Example

```
https://www.youtube.com/watch?v=wLB8pR4uME0

Daniel (@dungeondive) cracks open his collection of the Tomb Raider Collectible Card Game—a late-90s relic that tried to ride the Magic: The Gathering wave with Lara Croft as the hook. The game features competitive dungeon racing where players construct location decks, draw action cards dictating which alleyways they can shoot down, and press their luck deeper into the void while opponents play obstacles on them.

The tragedy? It's a CCG when it should have been a complete card game. Want solo cards? Hope you don't pull a booster pack full of competitive take-that actions. Daniel opens several boosters on camera and watches duplicates pile up while solo-usable cards trickle in. The silver lining: nobody's collecting this, so you can amass a decent haul for cheap on eBay.

----

What dead CCG do you wish had been released as a complete boxed game instead?
```

### Summary Guidelines

- **Length**: 2-4 paragraphs (150-250 words)
- **Tone**: Engaging, community-focused, slightly witty
- **Daniel mention**: Every post MUST use "Daniel (@dungeondive)" on its first mention of Daniel. Subsequent mentions within the same post can just use "Daniel". This applies to EVERY post independently — not once per batch.
- **Include**: Topics covered, highlights, why viewers would enjoy
- **Avoid**: Spoilers, timestamps, excessive detail
- **Closing**: ALWAYS end with `----` followed by a discussion-prompting question related to the video content

## Index Schema

```json
{
  "channel_id": "UC...",
  "last_fetched": "2026-01-31T10:00:00Z",
  "videos": [
    {
      "video_id": "abc123",
      "title": "Episode Title",
      "description": "Video description...",
      "published_at": "2024-06-15T14:00:00Z",
      "thumbnail_url": "https://...",
      "status": "pending|imported|skipped",
      "discourse_topic_id": null,
      "imported_at": null
    }
  ]
}
```

## Status Values

- `pending`: Not yet imported
- `imported`: Successfully posted to Discourse
- `skipped`: Manually marked to skip (e.g., duplicate, off-topic)
- `no_transcript`: Cannot import - no captions available (music videos, art slideshows, very old videos)

## Error Handling

- **No transcript available**: Note in the Discourse post that this is a summary from the video description only
- **API rate limits**: Wait and retry, or reduce batch size
- **Backdate fails**: Topic still created, just with current date (requires admin API key)

## Dependencies

Install required Python packages:
```bash
pip3 install requests youtube-transcript-api
```

## Claude: Post-Batch Checklist

After user confirms `batch_post.py` ran successfully, Claude MUST complete ALL of these steps:

- [ ] **Verify index updated** — check `video_index.json` shows videos as `status: "imported"` with `discourse_topic_id`
- [ ] **Update dashboard stats** — edit `docs/index.html`:
  - Update stats: total, imported, pending counts
  - Update archive counts in the "transcripts • posts local" line
  - Update `yearData` if new videos change year counts
- [ ] **Add videos to dashboard** — add entries to `_raw` data with correct topicId and status "imported"
- [ ] **Archive files** — move posted files from `ready_to_post/` to `archive/posts/` (batch_post.py may do this automatically)
- [ ] **Report to user** — confirm updated counts and provide links to new posts
- [ ] **Provide dashboard link** — always link to `docs/index.html` so user can verify

This checklist ensures the dashboard stays in sync with the actual state of imports.

## CRITICAL: Workflow Sequence

Claude MUST follow this exact sequence and never skip steps or get ahead:

1. **Generate posts** → write `*_post.json` files to `ready_to_post/`
2. **Validate JSON** → verify every post file parses with `json.load()`
3. **Tell user to post** → provide the `batch_post.py` command
4. **WAIT for user to confirm posting** → do NOT proceed until user pastes output
5. **Run post-batch checklist** → update index, dashboard, archive counts
6. **Provide dashboard link** → `docs/index.html`

⚠️ **Common mistakes to avoid:**
- Do NOT start generating the next batch of posts while `ready_to_post/` still has unposted files
- Do NOT forget to tell the user to run `batch_post.py` — always provide the exact command
- Do NOT use `Write` tool for post JSON files — always use Python `json.dump()` to ensure valid JSON escaping
- When adding entries to `_raw` in `docs/index.html`, find the ACTUAL end of the data (it changes after each batch)
- `docs/index.html` uses compact pipe-delimited format inside a template literal. Format: `id|title|date|status|topicId` per line in `_raw`. Parse with `.split('\\n').map(...)`. When updating, parse the `_raw` string, modify entries, and rewrite in the same pipe-delimited format.
- `yearData` counts are TOTAL videos per year (not just imported) — update from index totals, not imported counts
- Always use Python to parse and rewrite `_raw`/allVideos — never use sed on the compact format

## Keeper Post Sign-Off Format

Every Keeper post MUST end with this exact structure:

```
*NNN transcripts • NNN posts archived*

-- The Keeper
*[Witty observation in italics, relevant to the batch theme]*
```

The stats line is factual (current archive counts). The sign-off is always "-- The Keeper" on its own line. The closing observation is a one-liner in italics — wry, thematic, never generic.

## Rate Limit Check

Before fetching transcripts, always run:
```bash
python3 scripts/check_rate_limit.py
```
If exit code 1, the daily limit (2 runs per 24h) has been reached. Skip the run entirely.

## Git Workflow (Scheduled Task)

When running as a scheduled task, follow this sequence after completing the sync workflow:

```bash
git add video_index.json docs/index.html archive/ CHANGELOG.md
git commit -m "sync: imported N videos (batch description)"
git push origin main
```

### What NOT to commit
- `config.json` (API keys)
- `pending_imports/` contents (transient)
- `ready_to_post/` contents (transient)
