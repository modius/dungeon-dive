# Changelog

## 2026-04-29 — League of Dungeoneers Part I (6 videos)
- Series start: **League of Dungeoneers** (Part 1 of 2)
- Imported 6 videos forming the prototype-to-mechanics arc: A Look at League of Dungeoneers (2022), all-in Kickstarter unboxing (2023), Companions/standees/bestiary deep-dive, Quests, Character creation, Game flow overview
- No new videos discovered (1017 total unchanged)
- No priority videos in last 14 days — drained from queue head
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/33
- Stats: 1017 total, 401 imported, 610 pending, 6 no_transcript
- 5 League of Dungeoneers videos remain (solo customization, review, comparison, expansion preview, 2024 update) — Part II next rotation
- All transcripts pulled cleanly from residential IP — no transient failures (validates the local /import architectural decision from earlier today)

## 2026-04-28 — Priority drop: Solo Hexcrawls + CY_Korg (2 videos)
- Ad-hoc priority run — both videos published in last 14 days; queue waits one cycle.
- Imported 2 priority videos: The Ultimate Guide to Solo Hexcrawls (2026-04-26), CY_Korg - A Simple Cyberpunk Solo Game (2026-04-23)
- 2 new videos discovered during fetch (1017 total)
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/32
- Stats: 1017 total, 395 imported, 616 pending, 6 no_transcript
- `series_queue.json` untouched — priority runs never mutate the queue. Next rotation still: league-of-dungeoneers Part 1.
- Health: still 79 imported videos missing local transcripts (tracked in issue #2).

## 2026-04-20 — Queue-driven batch selection
- Migrated `series_queue.json` schema: active entries now carry explicit `video_ids`, `videos_per_batch`, and `one_shot` fields. Batch selection is queue-driven; `/plan-batch` writes, `/import` drains.
- Reconciled the stale arkham-horror active_series entry (reported `videos_remaining: 1`, reality was 0). Moved to `completed_series` with `parts_completed: 2`, `total_videos: 18`, `completed_date: 2026-04-20`.
- Removed the legacy title-scanning fallback from `/import`. Theme selection is now always via `/plan-batch` — in unattended mode, empty queue means skip, not guess.
- Added drift check: before importing a queued slate, `/import` verifies each `video_id` still has `status: pending` in `video_index.json` and drops any that don't.

## 2026-04-20 — Mythos Part II: Beyond Arkham (11 videos)
- Series continuation: **Arkham Horror / Mythos** (Part 2 of N)
- Imported 10 Lovecraftian Mythos videos: A Failing of the Cthulhu Mythos Board Games (2019), Cthulhu: Death May Die review (2019), Mansions of Madness 2E Thoughts (2021), Eldritch Horror / Lovecraftian theming / Brian Lumley (2021), Call of Cthulhu 7e Starter Set (2022), Returning to Cthulhu: Death May Die (2022), CoC 40th Anniversary + Solo Investigator's Handbook (2022), FOMO / why not backing new Cthulhu & Wander (2022), Little Town & Eldritch Town solo RPG (2023), Galzyr vs Freelancers vs Mansions of Madness 2e comparative review (2024)
- Imported 1 new priority video: Stonesaga review (published Apr 19)
- 1 new video discovered during fetch (1015 total)
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/31
- Stats: 1015 total, 393 imported, 616 pending, 6 no_transcript
- 1 Lovecraftian/Mythos video still pending (per series_queue) — series continues in future rotation

## 2026-04-18 — Mythos Part I: The Gates of Arkham (8 videos)
- New series started: **Arkham Horror / Mythos**
- Imported 8 Arkham Horror videos: AH 3e Take a Look (2018), AH 3e Review (2018), AH 3e vs Fallout vs Skyrim comparative review (2024), Curse of the Dark Pharaoh + Appendix M (2024), Arkham Horror RPG: The Hungering Abyss starter set (2024), Top 5 Places in Arkham City (2024), The Dunwich Horror expansion (2025), Buffy the Vampire Slayer board game (2025)
- No new videos discovered (1014 total unchanged)
- No priority videos in last 21 days — selected new theme from pending archive
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/30
- Stats: 1014 total, 382 imported, 626 pending, 6 no_transcript
- 11 more Lovecraftian/Mythos videos remain (Mansions of Madness, Elder Sign, Eldritch Horror, Cthulhu: Death May Die x2, Call of Cthulhu RPG x2, Little Town / Eldritch Town, earlier Arkham commentary)
- Next rotation: Arkham Horror / Mythos Part II (only active series)

## 2026-04-17 — Shadows of Brimstone Part V: The Final Descent (8 videos)
- Imported 7 Shadows of Brimstone videos: Wrap Up, Solo RPG Episodes 1-3, Gates of Valhalla (Part 31), two 2024 bestiary retrospectives
- Imported 1 new priority video: Fortune and Glory / Conquest of Planet Earth micro expansions (published Apr 15)
- 1 new video discovered during fetch (1014 total)
- **Shadows of Brimstone series complete** — all 38 videos archived across 5 Keeper posts
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/29
- Stats: 1014 total, 374 imported, 634 pending, 6 no_transcript
- No active series remaining — next import will select a new theme or start a new series
- Renamed `/insights` skill to `/channel-insights` to avoid conflict with built-in Claude Code insights
- Created `/refresh` skill to chain analyze + fetch-stats + channel-insights

## 2026-04-15 — Shadows of Brimstone Part IV: Hex Crawl & the Hobby (8 videos)
- Imported 8 Shadows of Brimstone videos: Expansion Heroes (Part 22), Storage (Part 23), Lamination (Part 24), Hexcrawl Parts 1-4 (Parts 26-29), House Rules (Part 30)
- 1 video failed transcript fetch: Part 25 (Art of Shadows of Brimstone) — marked no_transcript
- No new videos discovered (1013 total unchanged)
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/28
- Stats: 1013 total, 366 imported, 641 pending, 6 no_transcript
- 8 Shadows of Brimstone videos remain (Solo RPG trilogy, Gates of Valhalla, Wrap Up, two 2024 retrospectives)
- Next rotation: Shadows of Brimstone Part V (only active series)

## 2026-04-13 — Warhammer Quest Part IV: The Complete Excavation (10 videos)
- IP block lifted; transcripts working again
- Imported 9 Warhammer Quest videos: Silver Tower Parts 1-4, Gold Standard Parts 1-3, Old and New shelf tour, League of Dungeoneers crossover
- Imported 1 new priority video: Choir of Flesh (published Apr 12)
- 1 new video discovered during fetch (1013 total)
- **Warhammer Quest series complete** — all 27 videos archived across 4 Keeper posts
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/27
- Stats: 1013 total, 358 imported, 650 pending, 5 no_transcript
- Next rotation: Shadows of Brimstone Part IV (16 remaining, only active series)

## 2026-04-11 — No import (YouTube IP block)
- youtube-transcript-api upgraded to v1.2.4 (breaking API change) + IP blocked by YouTube
- All transcript fetches failing — not a subtitle availability issue
- Fixed integrity errors: 10 videos from Apr 10 import missing discourse_topic_id/imported_at
- No videos imported this run; both active series (WQ, SoB) have pending videos awaiting transcript access
- Stats: 1012 total, 348 imported, 659 pending, 5 no_transcript
- Action needed: wait for IP block to lift, or configure proxy per youtube-transcript-api docs

## 2026-04-10 — Shadows of Brimstone Part III: Allies, Enemies & Bosses (10 videos)
- Imported 10 Shadows of Brimstone videos: Parts 15-21 + unboxing interlude + 2 giveaways
- Covers ally expansions, mission packs (Crimson Hand, Werewolves, Vampires, Succubi, Black Fang), enemy deep dives (Serpentmen, Void Sorcerers, Undead Outlaws, Flesh Stalkers, Thunder Warriors, Ninja Clan, etc.), and all bosses
- No new videos discovered (1012 total unchanged)
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/26
- Stats: 1012 total, 348 imported, 659 pending, 5 no_transcript
- 16 more Shadows of Brimstone videos remain (expansion heroes, hex crawl, house rules, solo RPG, wrap-up)
- Next rotation: Warhammer Quest Part IV
- Insights dashboard given unique hero image (owl library)

## 2026-04-09 — Warhammer Quest Part III: The Let's Play Campaign (10 videos)
- Imported 9 Warhammer Quest Let's Play videos: Parts 1-9 (Barbarian & Witch Hunter campaign)
- Imported 1 new priority video: The Best Horror Fiction (published Apr 8)
- 1 new video discovered during fetch (1012 total)
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/25
- Stats: 1012 total, 338 imported, 669 pending, 5 no_transcript
- 9 more Warhammer Quest videos remain (Silver Tower, retrospectives, "Still the Gold Standard")
- Next rotation: Shadows of Brimstone Part III

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
