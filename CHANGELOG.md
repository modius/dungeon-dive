# Changelog

## 2026-04-08 — Shadows of Brimstone Part II: Through the Portals (8 videos)
- Imported 8 Shadows of Brimstone videos: expansion deep dives Parts 8-14 + Weird West fiction interlude
- Covers Frontier Town, Derelict Ship, Caverns of Cynder, Trederra, Blasted Wastes, Forest of the Dead, Temple of Shadows
- No new videos discovered (1011 total unchanged)
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/24
- Stats: 1011 total, 328 imported, 678 pending, 5 no_transcript
- 26 more Shadows of Brimstone videos remain (allies, enemies, mission packs, hexcrawl, solo RPG, wrap-up)
- Next rotation: Warhammer Quest Part III
- Note: 8 orphaned post files from previous run found in ready_to_post/ (already posted, archival missed)

## 2026-04-07 — Warhammer Quest Part II + Dice Commandos (8 videos)
- Imported 7 Warhammer Quest videos: Take a Look Parts 11-16 (White Dwarf issues c-e, Deathblow, fan/DIY content, Littlemonk's card brick) + Blackstone Fortress overview
- Imported 1 new video: Dice Commandos (published Apr 5)
- 1 new video discovered during fetch (1011 total)
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/23
- Stats: 1011 total, 320 imported, 686 pending, 5 no_transcript
- 18 more Warhammer Quest videos remain (Let's Play campaign, Silver Tower, retrospectives)
- Next rotation: Shadows of Brimstone Part II

## 2026-04-04 — Shadows of Brimstone Part I + Dungeon Degenerates (10 videos)
- Imported 9 Shadows of Brimstone videos: campaign preview, FoFo character overview, buyer's guide, core sets Parts 1-5, five loves/five dislikes
- Imported 1 new Dungeon Degenerates video: Goblin Mode + Lowlife RPG thoughts (published Apr 1)
- 1 new video discovered during fetch (1010 total)
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/22
- Stats: 1010 total, 312 imported, 693 pending, 5 no_transcript
- 33 more Shadows of Brimstone videos remain for future batches

## 2026-04-01 — Warhammer Quest Part I (10 videos)
- Imported 10 Warhammer Quest "Take a Look" videos: Parts 1-10 covering base game, big box expansions, warrior packs, and White Dwarf issues
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/21
- Stats: 1009 total, 302 imported, 702 pending, 5 no_transcript
- 25 more Warhammer Quest videos remain for future batches

## 2026-03-31 — HeroQuest Part II + Siege of Shaddis Horne (7 videos)
- Completed the HeroQuest series: 6 remaining videos (Episodes 3, AxianQuest, Armory, Ogre Horde, board love letter, Jungles of Delthrak)
- New video: Siege of Shaddis Horne (Pauper's Ladder review, published Mar 29)
- Aberration (5b4RSDrkc8I) marked as no_transcript — subtitles still disabled
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/20
- Stats: 1009 total, 292 imported, 712 pending, 5 no_transcript

## 2026-03-29 — Project Bootstrap (Full Session Summary)

### Migration
- Git repo initialized from existing project, pushed to modius/dungeon-dive (public)
- GitHub Pages dashboard live at modius.io/dungeon-dive/
- 1008 videos indexed, scripts promoted to top-level, one-off artifacts gitignored

### Scripts Built
- `config_utils.py` — shared config loading with environment variable fallback for remote execution
- `check_integrity.py` — 6-check integrity verification (index, archive, file validity, naming, dashboard sync, Discourse)
- `post_reply.py` — post replies to existing Discourse topics (Keeper updates to topic 1170)
- `update_dashboard.py` — programmatic dashboard stats and _raw data updates
- All existing scripts updated to shared config loader

### Sync Workflow
- Full end-to-end workflow tested locally: fetch → transcribe → post → Keeper update → dashboard → commit
- 8 HeroQuest videos imported as test batch, Keeper post live at topic 1170
- Scheduled task prompt written and cloud environment created (blocked by proxy — needs follow-up)

### Dashboard (3 pages)
- **Archive** (index.html) — stacked year chart, archive status columns, 5 stat cards, search/filter
- **Health** (health.html) — integrity cards, coverage donuts, sync timeline, problem videos, recommendations
- **Content** (content.html) — top games, content categories, keeper timeline, import velocity
- Keeper art hero banners on all pages (quest board, keeper at desk, hex dungeon map)
- Chart.js for all visualizations

### Outstanding
- Cloud environment network access (proxy blocking Discourse + YouTube APIs from Anthropic infrastructure)
- Problem video index visualization
- Legacy import reconciliation (60 unmatched Discourse topics, 12 legacy transcript filenames)
- Content analytics expansion (34 of 1008 transcripts analyzed so far)

## 2026-03-29 — HeroQuest Batch (8 videos)
- Imported 8 HeroQuest videos: 6 Advanced HeroQuest (review + full let's play campaign) + 2 HeroQuest episodes
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/19
- Stats: 1008 total, 285 imported, 719 pending
- 6 more HeroQuest videos remain for next batch

## 2026-03-29 — Sync Run Aborted (Credential Failure)
- YouTube API: key invalid or quota exceeded
- Discourse API: connection refused (proxy returned 403 Forbidden)
- No videos imported this run — credentials must be fixed before next attempt

## 2026-03-29 — Repository Migration
- Converted project to Git repository
- 1007 videos indexed, 276 imported, 205 transcripts, 213 posts archived
- Dashboard published to GitHub Pages
