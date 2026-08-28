# Changelog

## 2026-08-28 — normalised all 856 archived post records; added `/repair normalize` (no import)

Follow-on from today's two-record fix. What began as an inconsistency in two files turned out to be systemic, and the root cause was in the tooling rather than the data.

- **Root cause.** `repair_data.py cmd_posts` recovered a missing post file by storing `topic["post_stream"]["posts"][0]["cooked"]` — Discourse's *rendered HTML*. Every one of the 82 records carrying a `recovered_at` key was HTML-bodied by construction, and also lacked `video_date` and `category`, which `cmd_posts` never wrote. **`cmd_posts` now stores `raw`**, so recovery no longer mints broken records.
- **`raw`, not conversion.** The authored markdown lives on the per-post endpoint (`/posts/{id}.json` → `raw`), not the topic endpoint. Bodies were rebuilt from `raw`, so each archived body is byte-for-byte what was published — no HTML-to-markdown translation, nothing to get subtly wrong.
- **The category finding, which was the real discovery.** `batch_post.py:52` sets the Discourse category from `config.json`'s `category_id` (5, "The Channel") and **never reads the post JSON's `category` field**. The `"category": 8` that 698 records carried, and that CLAUDE.md documented as authoritative, was **dead data that had never had any effect** — and 8 is "Patreon", so it would have been wrong had anything honoured it. Verified against three topics posted earlier today: all landed in category 5 despite their post JSON saying 8.
  - Per user decision, `category` now records each topic's **real** `category_id`. Final distribution: **5** The Channel (811), **6** The Channel/Reviews (29), **7** Gab Fests (12), **9** All Fiction is Fantasy (2), **12** Digital Spelunking (2). Nothing in category 8.
  - Docs corrected: CLAUDE.md's post schema and Key-external-IDs section, and `import/SKILL.md` step 8, now say `category: 5` and state plainly that the field is not read when posting.
- **New subcommand: `repair_data.py normalize`.** Fixes HTML bodies, missing `video_date`, and missing/wrong/name-string categories. `--config` optional (offline-only without it), `--limit N`, `--verify-categories`, honours the global `--dry-run`. `report` gained a **Non-uniform post records** line so the class is visible rather than invisible.
- **Category resolution is two-tier, because the cheap path is incomplete.** A bulk topic→category map built by paging category listings covers only ~650-750 of the forum's topics — **299 of the archive's 856 topics had fallen off the listings entirely.** A per-topic fetch fallback covers the remainder. Using the map alone would have silently left a third of the archive unverified.
- **Two bugs found and fixed in the new code during the run, both worth recording:**
  1. **The guard was too strict.** The initial body guard required `raw` to *open* with the YouTube link. `CVFIzDp5iio` ("Top 10 Life Changing Table Top Games") is an owner-authored post that introduces the video in a sentence *before* linking it, so the guard correctly refused to write it — but for the wrong reason. Guard changed to require `youtube.com/watch?v={video_id}`, which is **stricter** (it pins the exact video, not just any YouTube link) while accepting legitimately-shaped posts. The record normalised cleanly afterwards.
  2. **`normalize` was not idempotent.** Flagging a category as wrong when the topic was merely *absent* from the bulk map meant ~300 records were re-flagged and re-fetched on every run, and the subcommand would never report clean. Absence is now treated as "unverified, not wrong": a stored int is re-flagged only when the map actively disagrees. `--verify-categories` forces a per-topic re-check when that is actually wanted. Confirmed: a second `--dry-run` pass reports **"All post files already match the canonical schema."**
- **What was deliberately not done.** **146 of the 856 bodies have no `----` discussion question**, because none was ever posted for those videos. No question was invented for any of them. Fabricating one would make the archive assert something that was never published — the archive records what went out, not an improved version of it. Giving those legacy topics questions is an edit to live Discourse posts and a separate decision. This is now a written rule in `repair/SKILL.md`.
- Verified across all 856 records: **0** HTML bodies, **0** missing core fields, **0** non-int categories, **0** bodies failing to link their own video. `check_integrity.py` File Validity **PASS**; `repair report` Non-uniform post records **0** (was 148 at the start of the day).
- Also ran `cleanup` per the skill's standing rule — 49 stale `pending_imports` files swept.
- Scale: 851 + 300 + 1 record writes across three passes (the middle pass re-processed the unmapped 300 before the idempotency fix landed), ~800 Discourse requests total. No rate limiting encountered, consistent with CLAUDE.md's note that Discourse has no practical limit at current volumes.

## 2026-08-28 — normalised 2 legacy HTML-bodied post records (repair, no import)

- Follow-up to today's `second-verdict` batch, which surfaced `hX5lVJXMurI` (Quest for the Lost Pixel, t/607) and `UUUH5xnM-Mc` (DungeonQuest, t/605) as post records stored as **rendered Discourse HTML** — youtube-onebox `<div>`, `<p>` wrappers, `<a class="mention">` — rather than the markdown schema.
- **Cause identified:** `repair_data.py cmd_posts` recovers a missing post file by storing `topic["post_stream"]["posts"][0]["cooked"]`, which is Discourse's *rendered* HTML. It does not store `raw`. Every post file carrying a `recovered_at` key is therefore HTML-bodied by construction, and also lacks `video_date` and `category`, which `cmd_posts` never writes.
- **Fix used — lossless, not a conversion.** Discourse exposes the original authored markdown at `/posts/{post_id}.json` → `raw`. Both records were rebuilt from `raw` rather than by HTML→markdown translation, so the archived body is now byte-for-byte what was actually published. `raw` is *not* present on the topic endpoint's post_stream entries; it needs the per-post endpoint, which is why the recovery path never had it.
- **Two findings that changed what got written, neither of them assumptions:**
  - **`category` is 6, not 8.** Both topics live in category 6, not the category 8 used by current per-video posts. Recorded the real `category_id` read from the topic rather than defaulting to the schema's usual value.
  - **Neither post has a `----` discussion question.** Confirmed against `raw` — this is genuinely absent from the live posts, not lost in recovery. **No question was fabricated.** Inventing one would make the archive assert something that was never published; the archive's job is to record what went out, not to improve it retroactively.
- `video_date` backfilled from `video_index.json` `published_at` (2025-03-16T21:00:23Z and 2025-03-26T16:00:30Z). Note these differ from the Discourse `created_at` values (2025-03-16T13:00:00Z, 2025-03-25T13:00:00Z) — `video_date` is the video's publish date by schema definition, not the topic's.
- Provenance preserved: `recovered_at` retained, `normalized_at` added. Key order now matches the current schema on the core five (`video_id`, `title`, `body`, `video_date`, `category`) with `discourse_topic_id` and the two provenance stamps following.
- Verified: no HTML tags remain, both bodies open with their own watch URL, `check_integrity.py` File Validity **PASS** across all 856 post files.
- **Scope note — this class is much larger than the two.** A full scan of `archive/posts/` found **82 HTML-bodied recovered records** (these two now fixed, **80 remaining**) and a further **66 markdown records missing `video_date` or `category`**. 148 of 856 post files are non-uniform. The remaining 80 are fixable by exactly this method; the 66 need only field backfill from the index. Not actioned this run — the request was scoped to the two.
- `scripts/repair_data.py` deliberately **not modified** (per CLAUDE.md); the fix ran as a one-off scratchpad script. A `normalize` subcommand wrapping this method is the obvious permanent home for it.

## 2026-08-28 — The Second Verdict, part 1: amended judgements (6 videos) — queue drain, series continuing

- Decision tree: `fetch_channel_videos` found **0 new videos** (index steady at 1057); **0** pending published since 2026-08-14 → no priority batch. Drained `active_series[0]` = `second-verdict` (`videos_per_batch: 6`, 11 IDs queued). **Drift check: all 6 slate IDs confirmed `pending`, nothing skipped.** 5 IDs remain → series stays in `active_series` as part 2.
- Pre-flight: `git pull` **fast-forwarded 92f6c43..2dce8c1** — the nightly `/refresh` had pushed `docs/content.html` and `docs/insights.html`. Pulling at step 1 with a clean tree is what made that free; by step 11 the same pull would have been refused. Rate limit OK (6/20 videos in 24h across two runs, 14 headroom), config OK (Discourse admin confirmed → backdating works), integrity **WARN, exit 1** (79 imported missing local transcripts, issue #2; dashboard stats unparseable — cosmetic). All 6 transcripts fetched cleanly (13.2k–21.9k chars, **0 permanent and 0 transient failures**). The `--` separator mattered again: the slate opens with `-3dLSMzi38k`.
- **Theme.** Every video in this series is Daniel revising a prior judgement in public — a re-rating, a re-purchase, a return to a game he had already filed. The batch spans 2020–2023 and four different flavours of second thought: a game ranked and defended in third place, a beloved world revisited to find the new supplement broken, a top-50 placement he argues on camera was twenty places too low, and a list built entirely out of games he sold and bought back.
- Posts (all backdated to the exact `published_at`, 202–234w summaries, "Daniel (@dungeondive)" on first mention in each):
  - https://dungeondive.quest/t/prophecy-fantasy-adventure-that-doesnt-rock-the-boat/2084 (2020-02-02 — Vlaada Chvátil's 2004 fantasy romp, both expansions on the table, run solo under the Dragon Realm co-op rules. The board is a globe rather than a track; five astral planes act as boss sites. **The structural point worth keeping:** movement is not a die roll but a purchase — one gold hops between ports, two gold opens a magic gate, one gold rents a horse for two spaces — and health/strength and willpower/magic are each one stat doing double duty as life and currency. Chance deck never punishes outright. His verdict is a ranking, delivered plainly: Talisman 2nd ed first on art and character variety, Runebound second, Prophecy third — characters barely differ, art has only low-budget charm, and nothing in it is as memorable as being turned into a frog. Still sets it up about once a year.)
  - https://dungeondive.quest/t/return-to-the-wurstreich-a-look-at-grime-gold-at-the-ghostgates-and-die-wurst-issue-2/2088 (2021-04-04 — Dungeon Degenerates: Hand of Doom, two pieces of new material. *Die Wurst* issue 2 carries almost no gameplay content and is better for it: Ralph Bakshi, Uriah Heep's *Demons and Wizards*, 1970s plastic model kits, and a continuation of the Satanic Panic piece. Gaming centrepiece is Eric Bouchard's guide to running the game as an RPG — an idea Daniel had already floated himself; an editor's note confirms an official RPG is intended but back-burnered while Sean Äaberg recovers from a stroke. **The main draw and the main problem are the same object:** *Grime & Gold at the Ghostgates* is a full choose-your-own-adventure module pinned to one board location and playable as a mid-campaign interlude — he immediately wants one for every landmark on the map — but a page of rules is missing outright and the wandering-monster rules are still absent even after errata went up on BGG. Advises waiting for the corrected printing.)
  - https://dungeondive.quest/t/fortune-glory-revisiting-a-game-i-should-have-ranked-higher/2087 (2022-09-11 — a Patreon poll chose the revisit and the revisit turns into a public correction: ranked ~29th in his top 50, he now argues for far higher, possibly above Shadows of Brimstone, which is bigger but far harder to get to a table. Five reasons given. **The two that carry the video:** tension from turn one, because in co-op the villains start already sitting on an artifact so the victory tug-of-war is live before you act; and serendipity, illustrated by a New York auction card colliding with a villain event that lets the cult secretly buy artifacts at auction — two random draws making a story neither could tell alone. Also: his photographer starts allied with the President, whose ability simply deletes an enemy. Complaints are exceptions-on-exceptions and the fact that gold coins are the victory track while blue coins are currency, which he says is backwards.)
  - https://dungeondive.quest/t/the-return-of-the-walking-dead-revisiting-heres-negan-the-board-game/2086 (2022-10-11 — underrated enough that he forgot to put it on his own top 50 and now says that was a mistake. Mantic's pitch as he frames it: the tension of Space Hulk but fully co-op, and therefore genuinely good solo where Space Hulk's variants never are. **The design that makes it:** Negan walks a fixed dotted route and must be escorted to the far end, but he will not open a door because he expects doors opened for him, and will not enter an unsecured room — forced to, he enrages, swings the bat, and strips reputation and stamina from everyone nearby. His behaviour runs off a small AI deck Daniel describes as the thing you learn to love and hate; he has never hated a plastic figure more. Walkers enter as face-down tokens resolved only on line of sight, lifted straight from Space Hulk. Verdict: worth $60, must-buy near $40; tiles look dull, everything else is high quality.)
  - https://dungeondive.quest/t/gloom-and-shadows-a-recipe-for-adventure-shadows-of-and-gloom-of-kilforth/2085 (2023-01-25 — both boxes combined into one set; a diabolist werewolf three chapters into a saga against the Bishop of Pride, racing a 25-turn night deck. **Two design details earn real admiration.** First, the fix for combining sets: when a card demands a specific named location that may not be in play, you draw a token pointing at a grid position instead — which makes mixing the boxes trivial. Second, rewards arrive as *rumours* rather than items: you don't take the helm you won, you learn where it is and go fetch it, turning every reward into a small side quest. Hit points double as action points, so damage costs tempo as well as life. Two honest cautions: the narrative is dots rather than prose and reads dry if you won't join them — he admits he isn't always in the mood — and it is keyword-dense, exception-heavy and unforgiving of long gaps between plays.)
  - https://dungeondive.quest/t/top-five-games-i-sold-and-bought-again/2089 (2023-04-16 — the most autobiographical video in the batch and the one that names the series' theme. Dungeoneer (5th) for a glory/peril currency engine he says still hasn't been replicated; Space Hulk (4th), the first big-box game he bought with his own money in high school, sold when he moved to Southern California to chase music, rebought at 4th edition and still the best-produced game he owns; Kingdom Death: Monster (3rd), sold at a hefty profit during the out-of-print spike to fund a DSI Pro 2 synthesizer he still uses, rebought at 1.5; Plaid Hat's Dungeon Run (2nd), semi-co-op until the boss dies and the MacGuffin turns it into tag. **First is Arkham Horror 2nd Edition**, his reintroduction to the hobby — impenetrable until Universal Head's rules summaries made it click — sold, replaced with Eldritch Horror and Elder Sign, and eventually bought back as a complete collection. That purchase is what prompted the list.)
- **Proper-noun discipline:** names were taken from the transcripts where clearly spoken and cross-checked where not. *Thomas Denmark*, *Richard Halliwell*, *Adam Poots*, *Richard Launius and Kevin Wilson*, *Universal Head*, *Eric Bouchard*, *Ralph Bakshi*, *Uriah Heep*, *DSI Pro 2*, *Mr. Bistro* (Plaid Hat) all appear in the captions unambiguously. **Deliberately handled:** the Prophecy transcript renders the designer as "vladislao" — corrected to Vlaada Chvátil, the only plausible referent for a 2004 Z-Man-reprinted fantasy game; the *Die Wurst* transcript gives only "sean", supplied as Sean Äaberg from the game's authorship. Auto-captions also garble Runebound as "room bound" throughout Prophecy and Kilforth as "kill forth" — both normalised.
- Keeper **series update** (register A, **299w body prose** — inside the 250–400 target; 11-entry catalogue excluded per the register-A budget rule): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/131. Titled "The Second Verdict". Framing is a ledger of every judgement the archive has handed down, **written in pencil** — "Pencil is the honest medium. A verdict delivered once, in ink, and never revisited is not a verdict at all — it is a monument." Closes: "The first verdict tells you what a thing seemed to be. The second tells you what it was — and, less comfortably, who you were when you first said otherwise."
- **Integrated 11-entry Exhibit Catalogue**, chronological 2020→2025, six fresh imports interleaved with all five `related_imported_ids` (Hand of Fate: Ordeals t/1847, Bloodborne t/1833, Quest for the Lost Pixel t/607, DungeonQuest t/605, Fallen Land 2nd Ed t/1174) as one list with no visual distinction between new and pre-existing. **Hooks for the five pre-existing entries were written fresh from `archive/posts/<id>_post.json`.** Note for part 2: per the register-A rule these same five related IDs are reused in the next part's catalogue *by design* — vary the hook wording, don't drop them.
- **Two of the related posts are legacy HTML-bodied records** (`hX5lVJXMurI`, `UUUH5xnM-Mc` — stored as rendered Discourse HTML with a youtube-onebox div rather than the current markdown schema). Readable for hook-writing, but worth noting as a pre-existing archive inconsistency; not touched this run.
- Stats: 1057 total, **856 imported**, 190 pending, 11 no_transcript. Archive: 777 transcripts, 856 posts — dashboard cross-check matches the Keeper sign-off exactly.
- `series_queue.json`: 6 IDs drained from `second-verdict`, **5 remain** (`9rVcXaVHCXw`, `vqsoh8y6xa8`, `OddgScxecfA`, `Ulotto-Re6w`, `ZrqtNoiNSdw`) → series **not** completed, stays in `active_series`. `last_part` 0→1, `last_imported` 2026-08-28, `keeper_post` set to 1170/131. **`rotation_index` incremented 0→1** per the multi-part rule (the entry was not removed, so nothing shifted underneath it) — `escape-from-dulce` is next.
- Queue remaining: **19 videos across 3 series** — `escape-from-dulce` (4, next up), `loose-pages-exhibit-completions-pt2` (10), `second-verdict` (5, part 2).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-27 — Wander: The Cult of Barnacle Bay, the tide returns Parts Four and Six (5 videos) — queue drain, series completed
- Decision tree: `fetch_channel_videos` found **0 new videos**; the Crimson Desert priority drop earlier today cleared the 14-day window, so **0** pending since 2026-08-13 → no priority batch. Drained `active_series[0]` = `wander-barnacle-bay-pt2` (`videos_per_batch: 5`, one-shot). **Drift check: all 5 slate IDs confirmed `pending`, nothing skipped.** This is the first archive batch since 2026-08-17 — the queue was empty for nine days and then bumped twice by fresh uploads.
- Pre-flight: `git pull` already up to date. Rate limit OK (3/20 videos in 24h across two runs, 17 headroom), config OK (Discourse admin confirmed → backdating works), integrity **WARN, exit 0** (79 imported missing local transcripts, issue #2; dashboard stats unparseable — cosmetic). All 5 transcripts fetched cleanly (3.9k–22.9k chars, **0 permanent and 0 transient failures**). **The `--` separator earned its keep this run:** the slate contains `-WID9zHoKhE`, which begins with a hyphen and would have been parsed as an unknown flag without it. **Transcript-window note:** 1 fetch this morning + 5 now = 6 in the day, well inside the ~12–15-per-window ceiling.
- **Why this batch existed at all — the finding that produced it.** `wander-barnacle-bay` was closed on 2026-07-07 under the title "Wander: The Cult of Barnacle Bay — **Complete Let's Play**" having imported 5 videos, and its Keeper post (1170/119) wrote the shortfall into the fiction: *"The numbering skips a beat or two; the tide took Parts Four and Six before they could be shelved. No matter. The story holds without them."* Both parts were `pending` in the index the entire time, along with the 2019 unboxing, the mid-series Update and the Final Wrap Up. `/plan-batch` caught it on 2026-08-26 by diffing `completed_series` themes against full membership rather than trusting the completion record — a check that did not exist in the skill before that run and was added to `.claude/skills/plan-batch/SKILL.md` in 118023c. **The playlist alone would not have found it:** the *Wander* playlist omits Part 6 *and* Part 7, so a playlist-only diff under-reports the arc by two.
- Posts (all backdated to the exact `published_at`, 215–225w summaries). Topic IDs are not in publish order — `batch_post.py` works the input directory in filename order — so t/2082 is the March 2019 unboxing while t/2078 is a November session. Read `published_at`, never infer chronology from topic ID.
  - https://dungeondive.quest/t/wander-the-cult-of-barnacle-bay-take-a-look/2082 (2019-03-06 — the unboxing, and the earliest video in the exhibit by seven months. Second game off his most-anticipated-2019 list to arrive. **The genuinely interesting content is not the components but the self-examination:** he was deeply into anthropomorphic animals as a child — dates it to finding a Ninja Turtles comic on a food-court magazine stand around 1985 and the RPG the following year — drifted away, and says on camera that some of the drift is stigma around the furry subculture that he isn't sure he should have absorbed, adding plainly that he has nothing against furries. He also rejects the "kids' game" dismissal outright: nearly every game he owns is a kids' game and he's fine with that. Structural praise: the campaign book branches (the intro scenario opens onto three different follow-ups), tarot-sized event cards carry non-combat skill checks, bosses have AI decks, and the 40-page rulebook is rectangular rather than square — a format point he cheerfully admits he raises more than any other reviewer. Concern flagged at the time: only four or five grunt types in the base game. Also notes his Kickstarter box shipped wrong — missing initiative cards and starting gear for the bonus heroes, but containing High Tide spawn cards he hadn't bought.)
  - https://dungeondive.quest/t/wander-the-cult-of-barnacle-bay-lets-play-and-review-part-4/2078 (2019-11-05 — the first of the two "lost" parts. Tank and Ross come up the ladder out of the flooded waterways into Barnacle Bay proper, and he opens by praising the tiles for evoking an inhabited place — flowerbeds, garden gates, shovels, woodpiles, a well, a town square — rather than functioning as decoration. **Two things worth keeping:** first, a genuine rules contradiction he cannot resolve and asks viewers about — the objective demands three keys from three darkness tiles while the special rules imply a single key opens the magical gate; second, a scar-tissue aside about setup anxiety, invoking first-edition Mansions of Madness where a setup error could render a scenario unwinnable without anyone noticing until far too late. Guards are introduced (shielded, block line of sight, force close heroes to target them first). Four spawn cards plus an XP-tier spawn flood the board. Closes on a rules point he disagrees with: his crit-counter cannot strike a ranged attacker even at close range per the designer — **he plays it straight on camera and says he will house-rule it at home**, which is a cleaner statement of his whole reviewing posture than anything in the wrap-up.)
  - https://dungeondive.quest/t/wander-the-cult-of-barnacle-bay-lets-play-and-review-part-6/2081 (2019-11-14 — the second "lost" part, and it picks up directly from Part 5's cliffhanger with Tank face-down. Lays out the three rally routes — own action, ally's action, or a health potion — and the cost that makes them matter: every knockdown drops the morale track and morale at zero ends the run. Ross fails three rally attempts; Tank self-rallies on his own third try and heals half. **A second rules ambiguity, handled the same way as Part 4's:** stepping up the initiative track appears to grant a hero two consecutive turns, he can't persuade himself that's intended, and he rules *against* his own heroes pending confirmation. The event deck then turns the session — Trixie offers two treasures outright with a knowledge-check puzzle for a third at risk of morale; he takes the certain pair and declines the gamble, drawing a Tidal Blast and a convention-exclusive Dragon Bow, the best weapon seen in the game. Tank's two-handed-as-one-handed ability lets him keep his shield while wielding the bow; Ross surrenders his. Also admits to knocking both XP trackers off the table mid-session.)
  - https://dungeondive.quest/t/wander-the-cult-of-barnacle-bay-update/2080 (2019-11-17 — 3,875 chars, the shortest transcript in the batch and the most archivally interesting. Announces the playthrough will finish two scenarios off-camera so the first boss battle can be filmed — which is precisely what Part 7 delivers the next day, so this video is the connective tissue explaining an otherwise unexplained jump. Reasons given are domestic and specific: the hobby room fits exactly one game set up at a time and the dining table, his usual overflow, is occupied by his wife's sewing project. The remainder is a report from **Dungeon Siege West**, where he had spent the week running games — a different crowd from a typical board game convention, darker because of the music side. He met the people behind **Lurker Magazine** (perfect-bound, black and white, ~$20 an issue, ships with a seven-inch record) and is considering contributing written reviews. **The buried lede:** viewers have been asking for dungeon synth coverage and he is thinking about it — "a subculture of a subculture of a subculture". This is the channel visibly deciding to widen, in 2019.)
  - https://dungeondive.quest/t/wander-the-cult-of-barnacle-bay-final-wrap-up-review/2079 (2019-11-19 — the considered verdict, and the exhibit's proper closing statement. Opens on the beast epic and is the most personal stretch of the whole series: Watership Down, The Book of the Dun Cow, Redwall, plus a small taxonomy of how such stories differ and where Wander sits — the animals were never anything else. Art direction he calls faultless, singling out a dockside tile that reads briny and gunky without tipping into the grotesque. **Best structural observation in the batch:** the event deck is deliberately weighted toward rewarding the party, because a game that punishes exploration stops being explored — explicitly contrasted with Kingdom Death, where opening anything is usually a mistake. Also wants more crawls to steal the advanced initiative track, rates the boss AI decks a highlight, and praises the token economy for fitting one tray while noting Folklore: The Affliction and Madeira do it better by printing each token's effect on the token. The one complaint, consistent with Part 5's Kill Bill argument: clearing enemies grants XP, XP triggers more spawns, and the back half of each scenario bogs down where it should accelerate — though in boss fights that same escalation is the best thing in the box. Disclaims his videos as rules references and notes his errors likely balanced out.)
- **Proper-noun discipline:** names used were cross-checked against the five already-archived posts rather than taken from captions — *Panda Cult Games*, *Elder Bane*, *Tank*, *Ross*, *Tristan* (the BGG rules guru), *Trixie*, *Tidal Blast*, *High Tide*, *Dungeon Siege West*, *Lurker Magazine* all appear in prior archived summaries or the index. **Deliberately omitted:** both designers (captions give "Jonathan Philip Bradford and Heath Foley", unverifiable), the wizard hero (rendered variously "ibex us" / "I Bexar"), the panda-Cthulhu bonus boss (described functionally as "named for the publisher"), and the two men behind Lurker Magazine (captions give "John and Reuben" — plausible, unconfirmable, and naming real people on a guess is the worst version of this error).
- Keeper **series update** (register A, **319w body prose** — inside the 250–400 target; 10-entry catalogue excluded per the register-A budget rule, max hook 15 words): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/130. Titled "What the Tide Gave Back". **The framing is the correction itself** — the Keeper opens by admitting the previous post's "the story holds without them" was a lie of convenience, observes that a gap described confidently enough stops reading as a hole in the record, and closes: "The Keeper has amended the record. It is the only apology an archive knows how to make."
- **The 10-entry integrated Exhibit Catalogue is the point of this batch.** Five fresh imports and all five `related_imported_ids` render as one chronological list with no visual distinction: Take a Look → Parts 1–7 in unbroken sequence → Update in its correct slot before Part 7 → Final Wrap Up. A reader arriving today cannot tell which half was imported in July and which in August. Hooks for the five pre-existing entries were **written fresh from `archive/posts/<id>_post.json`**, not copied from the 2026-07-07 Keeper post — deliberately different lures for the same five videos (e.g. Part 5 now leads on the Kill Bill complaint rather than "the cold-dice session").
- Stats: 1057 total, **850 imported**, 196 pending, 11 no_transcript. Archive: 771 transcripts, 850 posts — dashboard cross-check matches the Keeper sign-off exactly.
- `series_queue.json`: all 5 IDs drained → `video_ids` empty → **`wander-barnacle-bay-pt2` completed** and moved to `completed_series` (`parts_completed: 1`, `total_videos: 5`, `completed_date: 2026-08-27`, `keeper_post` retained; `video_ids`/`videos_per_batch`/`one_shot`/`status`/`last_imported`/`related_imported_ids` dropped per the completed-entry convention). **`rotation_index` was 0 and was NOT incremented** — the entry was completed, so per the rule it was only clamped; removal shifted `second-verdict` into slot 0, which is now correctly next. `completed_series` holds 62 entries. **The combined `wander-barnacle-bay` exhibit now stands at 10 videos across two themes and two Keeper posts, seven weeks apart.**
- Queue remaining: **25 videos across 3 series** — `second-verdict` (11, 2 parts of 6, next up), `escape-from-dulce` (4), `loose-pages-exhibit-completions-pt2` (10).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-27 — Crimson Desert priority drop (1 video) — ad-hoc, queue untouched
- Decision tree: `fetch_channel_videos` found **1 new video**, pending and published 2026-08-26 (cutoff 2026-08-13) → **ad-hoc priority batch**, exit after posting. `series_queue.json` deliberately not mutated — verified unchanged at the end of the run (`git diff --stat` clean on that path). **This is the second consecutive cycle bumped by a fresh upload**, and the newly-planned queue has now waited one day without draining; `wander-barnacle-bay-pt2` remains at `rotation_index` 0 with all 5 IDs intact.
- Pre-flight: `git pull` already up to date (no nightly `/refresh` commit landed since yesterday's push). Rate limit OK (2/20 videos in 24h from yesterday's drop, 18 headroom). Config OK (Discourse admin confirmed → backdating works). Integrity **WARN, exit 0** (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos.py` and the transcript fetch both succeeded first attempt (34,243 chars — the longest single transcript in recent memory; **0 permanent and 0 transient failures**). **Transcript-window note:** 2 fetches yesterday + 1 today, ~21 hours apart, nowhere near the ~12–15-per-window ceiling.
- Post (backdated to the exact `published_at`, 231w):
  - https://dungeondive.quest/t/crimson-desert-and-the-joys-of-digital-tourism/2077 (2026-08-26 — a **Digital Dive** entry; Daniel opens "welcome back to the digital dive", so this is video-game content, not tabletop. The framing is a recantation: he wrote a scathing Crimson Desert review for Patreon at launch, bounced off it hard, **and then bought the game a second time** — first on PS5, which he says looks and runs badly enough that he will not recommend it on base hardware at all, then on Steam, where a low-end PC at 1080p with Ray Reconstruction enabled finally got him a stable ~60fps and a world he wanted to live in. ~30–40 hours across both saves, six chapters in, no intention of finishing — he notes he has hundreds of hours in Skyrim and Assassin's Creed Odyssey and has never completed either. **The editorial core is his own analogy:** he calls the experience *digital tourism* and compares the world directly to "a big open-world hex crawl I might play on my tabletop", which is what earns this a place on a board game channel. The click moment is specific and off-quest — a puzzle opened a giant fan, he deployed wings, rode the air current up to one of the floating sky islands and fought a boss nothing had sent him to find. Praised: combat closer to Dynasty Warriors than Souls (an explicit power fantasy, massive-scale battles), freely swappable gear modifiers that make stats near-equivalent so you equip whatever looks best, force-arm traversal, a dog that fetches loot, no load screens outside fast travel, and camp companions you can physically go and join on the missions you sent them on. **Criticised with equal specificity:** the first eight to ten hours are chores, controls are cumbersome, unresponsive and "five layers of complexity more than it needs to be", the swimming is awful, and puzzles never signal when you simply lack the required ability — "this game hates your time". Structural complaint worth keeping: the secrets are samey, every puzzle paying the same skill point and every waterfall cave the same gear chest, and quests do not snowball into further adventures the way Skyrim's did — bite-sized rather than building, which he half-misses and half-appreciates. He is candid that he plays on easy and looks up puzzle solutions on Google and YouTube without guilt.)
- **Proper-noun caution — heavy garbling in this transcript, so almost none were used.** The captions render the five region names as "Hernand", "Diminus"/"Deinis"/"dimminimus", "Delissia", "Pyoon" (three spellings for one region inside a single video), plus "Toria curved sword", "cuckoo pot", "Greymanes" and a second playable character as "Damian". **None of these appear in the post.** Only *Crimson Desert*, *Pearl Abyss* and *Ray Reconstruction* were used as proper nouns — the first two pinned by the title and general knowledge, the third a real and unambiguous rendering technique. Regions, items, the crafting system and the companion character are all described functionally or omitted. Same discipline as Forgotten Depths (2026-08-17) and Vanaheim (2026-08-26).
- **`video_date` correction caught pre-post.** The post JSON was first written with a placeholder `2026-08-26T16:00:00Z`; the index records `2026-08-26T16:00:30Z`. Corrected from `video_index.json` **before** `batch_post.py` ran, so the topic is backdated to the exact second. Worth noting as a near-miss: a guessed timestamp will backdate successfully and silently, and nothing downstream would have flagged the 30-second drift. Always read `published_at` rather than reconstructing it.
- Keeper **priority drop** (register B, **162w body** — inside the 100–200 target): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/129. Framing is a postcard rather than a parcel — "a view of somewhere that does not exist, sent by a man who had already pronounced the place not worth visiting."
- **"From the deeper stacks" cross-reference, 3 entries, chosen to bridge digital and tabletop:** t/1852 (Unexplored 2: The Wayfarer's Legacy — the channel's earlier case for a video game a board gamer ought to play, and the closest precedent for this post existing at all), t/1557 (The Ultimate Guide to Solo Hexcrawls — the tabletop answer to the exact comparison Daniel makes on camera), t/1161 (Video Games? Why? Channel Update — where he sets out why the Digital Dive strand exists). Hooks written from the archived post bodies. The five Dark Souls parts (t/1993–t/2065) were considered and dropped: they share the medium but not the subject — that series is about difficulty and mastery, this video is about aimless looking, and t/2065 already carried a Souls cross-reference block on 2026-08-16.
- Stats: 1057 total, **845 imported**, 201 pending, 11 no_transcript. Archive: 766 transcripts, 845 posts — dashboard cross-check matches the Keeper sign-off exactly.
- `series_queue.json` untouched, as required for a priority run: 4 active series, 30 videos, `rotation_index` 0 → `wander-barnacle-bay-pt2`.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-26 — In Ruins + Vanaheim buyer's guide priority drop (2 videos) — ad-hoc, queue untouched
- Decision tree: `fetch_channel_videos` found **2 new videos**, both pending and inside the 14-day window (cutoff 2026-08-12) → **ad-hoc priority batch**, exit after posting. `series_queue.json` deliberately not mutated. Moot this cycle in any case: `active_series` is **still empty** (drained 2026-08-17), so there was no archive slate to bump — branch 2 would have fallen straight through to branch 3.
- Pre-flight: `git pull` fast-forwarded bbc1d3f→095258e (nightly `/refresh` dashboards only — `docs/content.html`, `docs/insights.html`). Rate limit OK (**0**/20 videos in 24h, full headroom — nine days since the last import). Config OK (Discourse admin confirmed → backdating works). Integrity **WARN, exit 0** (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos.py` and both transcript fetches succeeded first attempt (16.8k and 24.0k chars, **0 permanent and 0 transient failures**).
- Posts (both backdated to the exact `published_at`; 229w and 224w summaries):
  - https://dungeondive.quest/t/in-ruins-build-a-castle-ruin-a-castle-make-a-dungeon-solo-rpg/2076 (2026-08-19 — M. Allen Hall's dungeon-building RPG for 1–6, structured as three phases over one castle's lifetime: build it, ruin it, then fight over the remains. Daniel has only played solo but suspects two or three players is where it lands, the competitive/semi-cooperative edge needing someone to push against. Phase one is lore then construction — answer questions (castle name, who built it, how the common folk feel), then nine rooms per faction hung off a starting 8x8 throne room, a five-card hand where **card value sets room size and every door connecting new room to old earns builder points**, spendable on L-shapes, corridors, stairs, or a secret room known only to your own faction. Phase two spans 300 years in three eras, each with a rolled cause of ruination, and **here only suits matter** — diamonds partially damage, clubs majorly damage, spades destroy, hearts repair one degree. Phase three is the land grab: flip cards to claim rooms, total surviving lair values for score. Six factions (goblins, undead, bandits, cultists, slimes, kobolds), the non-player ones run off a rudimentary card-value AI. **The tell is his own castle** — Gloom Shade Citadel, King Starstrider, war-prophets in the observatory, a necromantic cult in the crypt that loses control of what it summoned, then bandits tunnelling the vault, then supernatural drought — a full three-era history written *before* play so the eras could link. 32 pages, a D66 spark table, player reference and solo tables; he calls it more game than the activity-shaped genre usually delivers, and wants to play it with his wife.)
  - https://dungeondive.quest/t/vanaheim-2026-revisit-and-buyers-guide/2075 (2026-08-23 — a revisit and, mostly, a purchasing map: The Game Crafter storefront has grown several new doors since the 2023 review and choosing between them had become confusing. **Frank tier placement** — below Quest for the Lost Pixel, Rogue Dungeon, Doom Pilgrim and Iron Helm; "a great B-tier game", and he explicitly declines to either oversell or undersell it. What he loves is unchanged and structural: the **town-building phase**, where the first purchase should be the one-coin notice board, and every later building carries an icon that seeds its own side-quest cards into a growing deck — his stated reason is *sense of place*. Also praised: the item deck expanding by character level 1–5 with traps, ambushes and events mixed into the treasure so looting becomes press-your-luck; aspirational gear you find before you can use it; the decision decks delivering small choose-your-own-adventure beats mid-dungeon. Only real complaint is visual cohesion — clip art and asset packs from a one-man operation — which he frames as an '80s ziplock-bag DIY charm rather than a defect. **The buyer's guide is the practical core:** $65 base game still complete, or new cheaper entry points at ~$32 (level 1), ~$30 (levels 2–3), ~$16 (levels 4–5); base-game owners should add Decisions and Domains ($12) to catch up with what the designer added along the way; his standout recommendation is Through the Shimmering Portal (~$20), which bolts on an Arthurian quest-of-virtues, a stone-ring portal and a whole overland biome with its own village; Fury of the Jotnar ($12) and Hall of the Skinwalkers ($12) are smaller; the deluxe character pack is the one he'd skip. Endgame is still reach level five and kill the Fire Drake.)
- **Proper-noun caution:** captions render the game as "Valhalla" once and Vanaheim otherwise (title pins the correct form), the new class as "the Lark", and the original designer only as "John" in the 2023 archived post. The new post names **no** designer for Vanaheim — the transcript never states one — and describes expansions by their printed titles only. Same discipline as the Forgotten Depths run on 2026-08-17.
- Keeper **priority drop** (register B, **185w body** — inside the 100–200 target): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/128. Framing is two parcels — "a castle in three states at once" and "a corrected map" — since one video is a thing built and the other is directions for buying one.
- **"From the deeper stacks" cross-reference, 3 entries, all genuine fits:** t/1841 (the original 2023 Vanaheim review — same game, three years and several expansions earlier, when the town-building was the whole surprise), t/1853 (Delve — the archive's nearest cousin to In Ruins: a hold drawn ever downward, explicitly in the *How to Host a Dungeon* lineage), t/607 (Quest for the Lost Pixel Top 10 Reevaluation — the Game Crafter benchmark Daniel measures Vanaheim against **by name, on camera**, and whose designer he says also considered splitting his game into level packs). Hooks were written from the archived post bodies for all three, not from memory. Grimgrove (t/1293) and the JT Smith Game Crafter conversation (t/809) were considered and dropped as weaker Game-Crafter-adjacency matches — the 1–3 cap plus quality-over-quantity.
- Stats: 1056 total, **844 imported**, 201 pending, 11 no_transcript. Archive: 765 transcripts, 844 posts — dashboard cross-check matches the Keeper sign-off exactly.
- `series_queue.json` untouched, as required for a priority run: `active_series: []`, `rotation_index: 0`, `completed_series` 61 entries.
- ⚠️ **THE QUEUE IS STILL EMPTY, and this is now the second consecutive cycle carried entirely by priority drops.** `/plan-batch` remains **blocking** for archive work: with `active_series: []`, the next `/import` skips cleanly unless another upload lands inside the 14-day window. 201 videos remain pending — no shortage of material, only of queued slates.
- **`/plan-batch` leads standing, both still valid:** (1) the Forgotten Depths history from 2026-08-17 — 2 pending (`hBhD4lpfrvw` 2019-12-15, `TWUoFcCtDhA` 2022-07-24) against 4 imported (t/1392, t/2066, t/1985, t/609), a complete 2019→2026 arc, still timely while the reprint is news. (2) **New from this run: a Game Crafter print-on-demand thread.** Today's Vanaheim video is effectively a survey of that ecosystem and name-checks Quest for the Lost Pixel, Rogue Dungeon, Doom Pilgrim and Iron Helm as its benchmarks — all four already well represented (t/1291, t/1840, t/1223, t/1671 and more), which makes for strong `related_imported_ids` if any pending POD titles can be found to anchor a slate.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-17 — Nearly Effortless Fun, Part Two (7 videos) — queue drain, series completed, **QUEUE NOW EMPTY**
- Decision tree: `fetch_channel_videos` found **0 new videos**; the Forgotten Depths upload was imported earlier today, so **0** pending in the last 14 days (cutoff 2026-08-03) → no priority batch. Drained `active_series[0]` = `nearly-effortless-fun-pt2` (`videos_per_batch: 7`, 7 IDs queued, `last_part: 1`). Drift check: all 7 slate IDs confirmed `pending`, nothing skipped.
- Pre-flight: `git pull` already up to date (the nightly `/refresh` dashboards were pulled during this morning's priority run). Rate limit OK (2/20 videos in 24h across two runs, 18 headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN → exit 1 (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). All 7 transcripts fetched cleanly (9.1k–20.0k chars, **0 permanent and 0 transient failures**). **Transcript-window note:** 1 fetch this morning + 7 now = 8 in the day, ~9 hours apart, comfortably inside the ~12–15-per-window ceiling; the relevant unit remains fetches per throttle window, not per day.
- Posts (all backdated to the exact `published_at`, 216–237w summaries). **Topic IDs are not in publish order** — `batch_post.py` works through the input directory in filename order, so t/2067 is the November 2023 video and t/2068 the December 2022 one. Harmless, but don't infer chronology from topic ID when building a catalogue; read `published_at`.
  - https://dungeondive.quest/t/ghost-stories-meets-legends-of-andor-join-the-rangers-oltree/2068 (2022-12-21 — an impulse buy days after learning the game existed, off a Dice Tower top-ten of co-ops from a reviewer he trusts, and frankly because it is gorgeous; Antoine Bauza's name on the box seals it since Ghost Stories is a favourite, and he reads Oltree as Ghost Stories crossed with Legends of Andor, most of the art by Vincent Dutrait; **characters are deliberately thin by design** — a health bar, one power, one die toward a skill test — and he recommends three or four Rangers, having found two genuinely punishing; the fortress rings eight regions and buildings raised there add dice to the four test types, the chunky custom dice scoring on 5–6 with a third success face purchasable for one point of health; almost everything else is decks of bad news — assignments, a page-turning Chronicle story deck, incidences laid face-down three per region, problems that smother village benefits, and events, with an adversity die deciding which fires each turn; lose if defence or prestige reaches zero, secure regions with towers to stop spawns; **the one real caveat is one he concedes rather than raises** — on a first run you may not deduce what the Chronicle wants until it is too late to build for it, which he guessed right and won, and which he knows is a dealbreaker for others but not for him)
  - https://dungeondive.quest/t/put-the-dungeon-in-the-bag-again-bag-of-dungeon-2/2069 (2023-02-01 — Gunpowder Studios review copy, minis included and being passed to a patron because he prefers the wooden meeples; reckons Gunpowder have quietly cornered the light small-box crawl and this may be their best; **leans more co-operative than the original** via *tagging*, which spends an action to haul another hero into your fight and is often the only way anything dies early; the eight heroes carry that weight — a rogue who outright kills on doubles, a hunter whose crossbows never break, Moonbeam the fairy with a once-per-combat psionic blast who is shoved out of her square whenever hit, a wizard paying health for spells, a changeling who three times wears the shape of something she killed; **poison is the clever cruelty — it fills inventory slots rather than simply hurting**, so a poisoned hero is a disarmed one; hunt four brood seeds each granting their bearer a power, then lay out the whole forest to find the tree and plant them, at which point the boss arrives; solo gives each hero a single life, likened to an arcade run, and he hasn't won yet; purple enemy faces are different stronger enemies for combo play with Bag of Dungeon 1, joined by a pit-and-crossroads ladder tile; closes on a daydream of splicing Seven Moons' overland map onto both Bags of Dungeon for one long campaign, crediting his Shadows of Brimstone experiment for the idea)
  - https://dungeondive.quest/t/stranger-things-upside-down-ip-games-are-good-now-actually/2070 (2023-06-21 — CMON, designed by Rob Daviau, used to argue a thesis: licensed games are good now, where in the Toys R Us era a board game of your favourite show was garbage nine times in ten; files it near Horrified, not quite as good, a genuine gateway; **unusually candid about the source material** — the eighties texture, Winona Ryder and the D&D-in-a-basement opening all land, he thinks the writers stopped knowing what to do with Eleven and Mike after season one, anything with Steve, Dustin, Robin or Erica is gold, and Eddie in season four is some of his favourite television; seasons one and two share a double-sided board, Hawkins above and the tunnels beneath, which he calls one of the coolest he has seen and praises specifically for painted art rather than show stills; underneath it is threat management — stacks of mostly-hidden challenge tokens cleared by spending action cards, fear as hit points, walkie-talkie icons rewarding co-location, hazard icons dictating scene-card draws, and investigating the lab to ignore scenes; Eleven is not playable but six of her powers can be triggered; **best structural observation: banking safe turns leaves you eventually holding a hand of pure hazard**, a fair imitation of dramatic ebb and flow; four gripes — no group movement, no item trading, no dice at all where a small press-your-luck die would help, and too few items and allies to stay fresh)
  - https://dungeondive.quest/t/cursed-a-fantasy-themed-solo-blackjack/2071 (2023-07-30 — Goblin Hour Games via a Game Crafter crowd sale, bought largely on the red-and-sepia line art; one player, 3–6 minutes, described plainly as fantasy solo blackjack and a near-perfect travel game; a witch lifts your curse for eight monster souls; **every card does three jobs** — a monster whose power is your target number, a weapon with damage and a melee-or-ranged tag, and an item on the reverse, plus keywords and treasure chests granting an item draw; **the same deck is also your hit points**, so overshooting or stopping short costs cards off the top and running out ends the run, which is the economy he admires most; plays a full game on camera and loses holding seven of the eight souls; items reward attention — a soul crystal letting you bust without penalty, smoke bombs shuffling spent cards back in, a whetstone, a backpack fishing items out of the discard, a mimic that becomes a power-4 monster the moment you draw it as loot; daggers count as either one or six, declared on the draw, a real decision in a game this small)
  - https://dungeondive.quest/t/revisiting-the-heros-journey-home-solo-card-based-adventure-game/2073 (2023-08-03 — prompted by a question in the Dungeon Dive Facebook group; Graham Cranfield's game, and one he loves in play but forgets when listing favourites, exactly as with Hand of Fate: Ordeals; **the premise is an inversion — the quest is already won and you play the walk home**, and which quest you completed sets your party budget, the Minotaur paying 19 points and handing over a ball of string that replays a journey card; adventurers carry passive and active abilities, spellcasters draw spells at random, and casting is paid in gold *or* hit points, stats doubling as currency being a mechanism he loves anywhere; the newest expansion adds spellcasting monsters that only cast when their physical attack misses, plus Game Changer cards including a vow of poverty trading monster rewards for gold at every village and a fourth prayer; **lovely aside** — the designer posted that expansion to his office shortly before the pandemic and he found it there, crumpled, roughly two years later, having never been able to thank him; plays with a fan-made 52-card subset of the journey deck because the full one is large and diluted; the game famously shipped with no box, in a burlap sack, and he built one from an old game he'd stopped enjoying plus a scanned cover)
  - https://dungeondive.quest/t/a-quick-look-at-lost-ones-of-dreams-shadows/2072 (2023-11-05 — Gordon Alfred's game, set in the Of Dreams & Shadows world, and **unusually blunt**: the parent game isn't fantastic and this one is okay rather than great, worth the ~$30 sale price, with a harder recommendation withheld for one specific reason saved for the end; argues it is really interactive fiction in a board game's clothes, a very rules-light cousin of The 7th Continent or Tainted Grail; kidnapped by the Fae, you wake on tile one and look for a way home across 121 unique tiles each with a storybook page, connections printed along the edges so setup is trivial; **the system he genuinely likes is that ability cards are simultaneously interaction currency and hit points**, so you cannot engage every story hook and the game becomes a running argument about what to leave unexplored; the Nightmare, a raven entering play the first time you trip its icon, walks toward you while a moon clock runs down; 12 story tokens imply 12 major plot points; praises writing and art strongly; **the complaint is the box and it is not incidental** — huge standee wells, empty space, the carton sized only to fit an adventure guide that could have been printed smaller, and it fits perfectly in a spare Legends Untold box, at which size he'd recommend it warmly)
  - https://dungeondive.quest/t/explorers-of-the-woodlands-a-critter-crawl-review/2067 (2023-11-14 — From the Woods Studios, developed by Jeffrey Wood; a light-hearted critter-crawl for 1–4, solo played with two heroes; **pauses to legislate a definition he has clearly wanted for a while** — anything smaller than an FFG Elder Sign box is a small-box game, anything up to Arkham Horror is medium; each turn rolls four hero dice to assign, 1–3 buying movement and 4+ buying orbs that serve as both currency and the key to two special powers; tiles come off a dungeon deck with the boss shuffled into the last three, monsters carry a target number, combat is a dice pool evaluated die by die with elemental weaknesses adding pips and other heroes able to lend dice; thorn cards come in easy, normal and hard variants which he draws at random, rating the difficulty dial highly in a family-weight game; **the lair cards are the reason he keeps it** — an entrance card pairs with an interior, three consecutive successful encounters see you out with two treasures, one failure ejects you with the consequences; campfires heal to full on first visit, plus taverns and rage cards buffing minions and bosses; wishlist is specific — three power cards per hero drawn blind, four more cards per lair deck, a few more events)
- Keeper **series update** (register A, **360w body prose** — inside the 250–400 target; catalogue 266w, excluded per the register-A budget rule): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/127. Titled "The Low Door, Third Knock", continuing the crate-at-the-low-door conceit from part 1 without reusing its framing.
- **The editorial find of this batch: these seven exhibits are quietly all about containers**, which is what the Keeper prose is built on. One draws its dungeon from a bag; one is a single deck serving as monsters, weapons, loot *and* the hero's remaining life; one shipped in a burlap sack and had a box built for it out of a game its owner stopped loving; one occasions a formal on-camera ruling about how large a box may be before it stops being small; and one is sentenced to a lesser recommendation purely for arriving in a carton three sizes too grand when a rival's spare box on the same shelf would have fitted it exactly. That through-line was not in the queue entry — it emerged from reading the seven transcripts together, and it is a better organising idea than "low-friction games" would have been on its own.
- **12-entry integrated Exhibit Catalogue**, chronological 2020→2025, all five `related_imported_ids` folded in with no visual distinction from the 7 fresh imports. **These are the same five related IDs part 1 used on 2026-08-07**, per the fixed-at-queue-time rule — so the block recurs across both parts of the series by design. Hooks were **rewritten fresh from the archived post bodies** rather than copied from part 1's Keeper post, so a reader who saw both gets different lures for the same five topics. `import/SKILL.md` patched this run to state the recurrence explicitly, since the existing wording forbids substitution without saying what to do when a multi-part series reuses its list.
- **Caption corrections applied** (auto-captions garble proper nouns badly in this batch): "layer" → **lair** throughout Explorers of the Woodlands, unambiguous from context (a cave entered via an entrance card and an interior card); "old Trey"/"ultre"/"Ultra" → **Oltree** (pinned by the video title); "Antoine Bowser" → **Antoine Bauza** (pinned by the video's own attribution of Ghost Stories); "Vincent Detroit"/"Vincent Dew track" → **Vincent Dutrait**; "Rob davio" → **Rob Daviau**; "cool mini or not" → **CMON**; "ego waffles" → **Eggo**. **Deliberately omitted rather than guessed:** Oltree's co-designer, Explorers of the Woodlands' illustrator (Daniel says on camera he butchered the name himself), the Dungeon Crusade collaborator whose name this archive has spelled two different ways, and most of Bag of Dungeon 2's hero and boss names.
- Stats: 1054 total, 842 imported, 201 pending, 11 no_transcript. Archive: 763 transcripts, 842 posts — dashboard cross-check matches the Keeper sign-off exactly.
- `series_queue.json`: all 7 IDs drained → `video_ids` empty → **`nearly-effortless-fun-pt2` completed** and moved to `completed_series` (`parts_completed: 2`, `total_videos: 14` = 7 on 2026-08-07 + 7 today, `completed_date: 2026-08-17`, keeper_post retained; `video_ids`/`videos_per_batch`/`one_shot`/`status`/`last_imported`/`related_imported_ids` dropped per the completed-entry convention). **`rotation_index` was 0 and was NOT incremented** — the entry was completed, so per the rule it was only clamped, and since `active_series` is now empty it is set to 0. `completed_series` now holds 61 entries.
- ⚠️ **THE QUEUE IS NOW EMPTY.** `active_series: []`. This was the last active series, and it has drained. The next `/import` will hit branch 3 of the decision tree and **skip cleanly** unless a fresh upload lands inside the 14-day priority window first. `/plan-batch` has moved from overdue to **blocking**: without it there is no archive work left to do, only priority drops. 201 videos remain pending, so there is no shortage of material — only a shortage of queued slates.
- **Ready-made `/plan-batch` lead still standing from this morning:** two pending Forgotten Depths videos (`hBhD4lpfrvw`, 2019-12-15; `TWUoFcCtDhA`, 2022-07-24) against four already-imported entries (t/1392, t/2066, t/1985, t/609) — a complete 2019→2026 history of one game, timely while the reprint is news.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-17 — Forgotten Depths reprint priority drop (1 video) — ad-hoc, queue untouched
- Decision tree: `fetch_channel_videos` found **1 new video**, pending and published 2026-08-16 (cutoff 2026-08-03) → **ad-hoc priority batch**, exit after posting. `series_queue.json` deliberately not mutated. That is **four consecutive cycles** the archive slate has been bumped. `nearly-effortless-fun-pt2` (7 videos, `rotation_index` 0) has now been waiting ten days since 2026-08-07 and remains the **only** active series. `/plan-batch` is overdue — see the Forgotten Depths note below, which hands it a ready-made theme.
- Pre-flight: `git pull` fast-forwarded b14e626→f20de60 (nightly `/refresh` dashboards only — `docs/content.html`, `docs/insights.html`). Rate limit OK (1/20 videos in 24h from yesterday's drop, 19 headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN → exit 1 (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos.py` succeeded first attempt this run (no repeat of yesterday's transient SSL abort). Transcript fetched cleanly (12,222 chars, **0 permanent and 0 transient failures**).
- Post (backdated to the exact `published_at`, 241w):
  - https://dungeondive.quest/t/forgotten-depths-reprint-coming-soon/2066 (2026-08-16 — a short announcement rather than a review: Forgotten Depths has been out of print, and a BoardGameGeek thread from a publisher picking it up suggests a new print run. Daniel reached out to the poster for clarification and got no reply before filming, so the concrete details stop there and he openly admits the rest is an excuse to talk about an all-time favourite, which he calls one of the best dungeon crawls ever made and a certainty for his forthcoming top 10 at an unknown position. **The genuinely interesting content is the novelty argument** — he states plainly that he does *not* usually prize novelty, that most of the crawls he loves play much the same and that this suits him, and that Forgotten Depths is his single exception because every ordinary step of the genre is handled a little sideways. Specifics captured: 1–3 players, three explorers, each with a personal upgradeable combat deck *and* a personal loot/power deck so the fighter finds armour where the wizard finds spells; monster decks tiered 1–3; diamond symbols on cards triggering special abilities; dungeons built from map cards traversed node-to-node rather than tile-to-tile, where open-circle symbols must be connected into shapes as you lay them, larger and more complex shapes unlocking better points of interest that arrive as tarot-sized cards carrying lore, searches, ambushes, XP and panoramas. Expansion ranking: the campfire conversation deck (drawn from a subset keyed to party composition) deepens world and character but adds little play and is the one to skip if buying selectively; the Ever Chamber's biome-within-a-biome and hidden forge, and the modular lore/sub-dungeon set, carry the mechanical weight. Practical notes: not a campaign, saveable between biomes, true solo works, he prefers two heroes.)
- **Proper-noun caution — the auto-captions and the 2024 archived post disagree, so names were deliberately left out of the new post.** This transcript renders the illustrator as "Miriam Churchland", the wizard as "Syl", the modular expansion as "Vault of Yarok" and the designer as "Peter Alberson"; the archived summary for t/1392 (written from the 2024 transcript) says "Marin Churchland", "Sil" and "Vault of Yar". With two caption sources contradicting each other on first names and one expansion title, the post names neither designer nor illustrator and describes the expansions functionally ("the campfire conversation deck", "the Ever Chamber", "the modular lore set") — only *Ever Chamber* is used as a proper name, both sources agreeing on it. Same discipline as the Pauper's Ladder spellings on 2026-08-14: a functional description is always safe, a garbled proper noun is not.
- Keeper **priority drop** (register B, **153w body** — inside the 100–200 target, 192w including stats and sign-off): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/126. Framing is the reprint itself — the only mechanism by which the shelves grow *backwards*.
- **"From the deeper stacks" is unusually strong this time: all three entries are the same game, forming a seven-year sightings trail.** WITAWITADD - Exploration! (t/1985, 2019-12-12 — Forgotten Depths is the revelation that prompted that episode, via the tetromino-shaped legendary-location tiles), Forgotten Depths - A top 10 contender (t/1392, 2024-12-04 — the full second-edition case, five innovations, a week of constant play), and The Best Games of 2024 (t/609, 2024-12-29 — where it landed on the countdown). Hooks pulled from those three archived post bodies (`archive/posts/Sf25ENrbQGM_post.json`, `FG5G2G-XjhE_post.json`, `9gFQ9rFMKEA_post.json`), not invented. Note t/609's archived body is stored as rendered Discourse HTML rather than markdown — readable, but a reminder that older archived posts are not uniformly formatted.
- **"Ten Tabletop Games for fans of Dark Souls" (t/2033) was excluded despite being cited on camera.** The video opens by referring back to it explicitly ("I recently mentioned this game in my top 10 games that I would recommend to fans of Dark Souls"), which makes it the single most topical match in the archive — but it published 2026-08-09, eight days ago, and "deeper stacks" means the distant past, not last week. Three genuinely old Forgotten Depths sightings were available, so nothing was lost. Recording the reasoning because the *next* reader of this decision will see a strong match apparently ignored.
- Stats: 1054 total, 835 imported, 208 pending, 11 no_transcript. Archive: 756 transcripts, 835 posts — dashboard cross-check matches the Keeper sign-off exactly.
- **`/plan-batch` lead — a Forgotten Depths slate is sitting right there and the reprint news makes it timely.** Two pending videos on the same game: `hBhD4lpfrvw` (2019-12-15, "A Unique Dungeon Adventure") and `TWUoFcCtDhA` (2022-07-24, "A Smallish Game in a GIANT BOX!"). With t/1392 and the new t/2066 already imported, plus t/1985 and t/609 as context, that is a two-video import with four strong `related_imported_ids` — a complete 2019→2026 history of one game, ordered chronologically, published while the reprint is actually news. Not acted on this run: the priority rule forbids touching the queue, and fabricating a theme mid-priority-run is explicitly out of bounds. Flagged for the next `/plan-batch`.
- Continuity note: the Souls run did not produce an episode this cycle (Part 5 landed 2026-08-14, cadence has been every 3–4 days), so Part 6 is likely imminent and will trigger a fifth consecutive priority drop. The queue is genuinely at risk of starvation, not merely delayed.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-16 — Dark Souls Pt5 priority drop (1 video) — ad-hoc, queue untouched
- Decision tree: `fetch_channel_videos` found **1 new video**, pending and published 2026-08-14 (cutoff 2026-08-02) → **ad-hoc priority batch**, exit after posting. `series_queue.json` deliberately not mutated. That is now **three consecutive cycles** the archive slate has been bumped by priority uploads; `nearly-effortless-fun-pt2` (7 videos, `rotation_index` 0) has been waiting since 2026-08-07 and is the **last active series** — the queue empties the moment it drains, so a `/plan-batch` run is overdue.
- Pre-flight: `git pull` fast-forwarded 17cdd88→a135df0 (nightly `/refresh` dashboards only — `docs/content.html`, `docs/insights.html`). Rate limit OK (0/20 videos in 24h, full headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN → exit 1 (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic).
- **`fetch_channel_videos.py` died on the first attempt** with `requests.exceptions.SSLError: SSLEOFError(8, 'EOF occurred in violation of protocol')` against `www.googleapis.com` **mid-pagination** (third `playlistItems` page, `pageToken=EAAaH1BUOkNMWU...`). Purely transient — a plain re-run with no arguments changed succeeded and picked up the 1 new video. Worth recording because the failure mode is misleading: the traceback is a wall of `requests` internals with the API key visible in the URL, which reads like a credentials or quota problem and is neither. The script writes the index only after all pages are collected, so the aborted run left `video_index.json` untouched and the retry was safe. `import/SKILL.md` step 5 patched this run to say so.
- Transcript fetched cleanly (23,438 chars, **0 permanent and 0 transient failures**) — no index mutations beyond the import.
- Post (backdated to the exact `published_at`, 237w):
  - https://dungeondive.quest/t/a-normal-guy-plays-dark-souls-part-5-to-the-bottom-of-blighttown/2065 (2026-08-14 — **the episode opens with several minutes that are not gameplay at all**: an unguarded defence of Blighttown traced back to Demon's Souls and the Valley of Defilement, areas assembled from what a kingdom discards, people included. The anchoring memory is from his first playthrough — hundreds of hours in, no fast travel, so far below Firelink Shrine he could not picture the climb back, then reaching the bottom bonfire, looking up, and seeing blue sky and the tree above; he says flatly that no other game has given him that feeling, which is the promise Part 4 closed on and pays off here. The descent itself is played slowly on purpose: spider shield against the blowdart snipers because toxic is damage you cannot outheal, with the note that there are about four of them and they do **not** respawn, so clearing them permanently quiets the level; the +7 claymore still needing three hits; uneven ground refusing backstabs unless you share a plane with the enemy; a fond, forgiving mention of the original Xbox 360 framerate at ~20–24fps. Navigation advice worth keeping — follow the fire-poles, they sit at the tops and bottoms of ladders. The washing pole jump is abandoned on principle (an invisible wall makes it one of the hardest jumps in the game). The ninja set is found and worn. He credits **Illusory Wall** for the explanation of why enemies here seem to materialise: detection by sight, sound *and* smell. The parasite at the sewer outlet keeps its Power Within pyromancy, spared by navigational defeat rather than mercy. Two deaths to gravity. Next episode: the swamp, then Quelaag.)
- Keeper **priority drop** (register B, **169w body** — inside the 100–200 target, 199w including stats and sign-off): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/125. Single-parcel framing — the courier declines to bring it past the threshold because it has taken on the character of where it was left.
- **"From the deeper stacks" cross-reference used all three slots on the video-game-to-tabletop seam** rather than on the Souls series itself: Rune (t/1832, 2023 — "Dark Souls on your table", the solo Souls-like Daniel reckons out-lores the licensed game), Revisiting Bloodborne: The Board Game (t/1833, 2022 — an adaptation that punishes you for engaging with the thing it adapts), and Horror-themed video games and board games (t/1909, 2022 — whether a box on a table can ambush you the way a screen can). Parts 1–4 (t/1993, t/2017, t/2032, t/2050) were **deliberately excluded**: they are all inside the last fortnight, each was announced in a previous drop, and "deeper stacks" is meant to reach for the distant past, not the previous instalment. "Ten Tabletop Games for fans of Dark Souls" (t/2033) is the single strongest topical match in the whole archive but was excluded on the same rule — it is seven days old. **The Rune deep cut has now been spent twice** (2026-08-10 and here); the seam is close to exhausted, and a sixth Souls episode may warrant omitting the section entirely rather than reaching for a weak match.
- Hooks for all three deep-stack entries pulled from their archived post bodies (`archive/posts/KTnAV2qb5CY_post.json`, `UqLF2eIaDxg_post.json`, `tcomjtcMjLE_post.json`), not invented.
- Stats: 1053 total, 834 imported, 208 pending, 11 no_transcript. Archive: 755 transcripts, 834 posts — dashboard cross-check matches the Keeper sign-off exactly.
- Continuity note: five Souls episodes in sixteen days, cadence roughly every 3–4 days, and the video signs off promising the swamp and Quelaag. Expect Part 6 to trigger another priority drop before `nearly-effortless-fun-pt2` gets a look in.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-14 — The Prototype Table (12 videos) — queue drain, series completed
- Decision tree: `fetch_channel_videos` found **0 new videos**; the two priority uploads were imported earlier today, so **0** pending in the last 14 days → no priority batch. Drained `active_series[1]` = `prototype-table` (`one_shot`, `videos_per_batch: 12`, 12 IDs queued). Drift check: all 12 slate IDs confirmed `pending`, nothing skipped.
- Pre-flight: `git pull` already up to date. Rate limit OK (2/20 videos in 24h from this morning's priority run, 18 headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN → exit 1 (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). All 12 transcripts fetched cleanly (16.5k–42.3k chars, **0 permanent and 0 transient failures**) — no index mutations beyond the imports. **Timing note:** the morning's priority run fetched 2 transcripts at 10:33 and this run fetched 12 at 13:33 — 14 in one day, but three hours apart, comfortably past the ~1h throttle reset, so the ~12–15-per-window ceiling was never approached. The relevant unit is fetches *per window*, not per day; the 2026-08-10 entry's "a third run today would be unwise" was about two runs 20 minutes apart, which is a different situation.
- Posts (chronological, all backdated, 211–229w summaries). **`video_date` correction:** the post JSONs were first written with midnight placeholders, then rewritten from `video_index.json`'s `published_at` before posting, so all 12 backdate to the exact YouTube publish time rather than 00:00:00Z. Worth doing on every batch — a midnight timestamp is invisible on the forum but silently wrong in the archive.
  - https://dungeondive.quest/t/lets-unbox-dawnshade-the-watchers-prophecy/2053 (2022-03-08 — a re-shot unboxing, the genuine first-open lost to broken audio; drawn in by the promise of an endless path quest system plus a 200-page CYOA narrative, with the explicit hope it isn't another read-the-storybook-A-to-Z game; admires the trade-paperback rulebook, printed dice, hexagonal pop-out player boards and the quest tiles whose numbers key into logbook events; **two reservations that the follow-up video vindicates** — 16 pounds of box weight that is mostly weighted poker chips he'd have swapped for cardboard at the same price, and magazine-thin logbook covers on a metal spiral he plans to laminate; notes with relief that everything drops back into the moulded trays without a Tetris puzzle)
  - https://dungeondive.quest/t/dawnshade-why-it-isnt-for-me/2057 (2022-03-15 — one week later, explicitly not a review, but enough plays to know it's going on the sell pile; genuine praise for production, art and writing, and for the adventure board, the per-game quest tile stack, the movement-driven threat track and a campaign that finishes in three games; **the objection is precise and worth preserving** — nearly every non-combat challenge resolves as a dexterity mini-game (shuffleboard dice, a lock-pick roll between stacked chips, gambling flips, a spinning-top duel), so the advertised deep character builds have no bearing on how challenges are overcome; his verdict is that this should have been sold as a themed dexterity game and leaned into fully, which would have made it unique; also notes dexterity games are flat solo, with no table to cheer)
  - https://dungeondive.quest/t/arcadia-tenebra-a-look-at-the-protoype/2052 (2022-05-02 — prototype ahead of a second Kickstarter attempt after the first failed to fund; pitched as adjacent to A Touch of Evil with little overlap; anti-heroes in an Eastern European folklore-and-steampunk province with Tesla in the cast, racing three clues back to the police chief before the blood moon; **the lucky/unlucky decks are the standout** — items that arrive attached to a small quest you must complete before equipping, and cursed unluckies with their own removal quest that drags you across the map; shop restocks from discards; concerns are that it's too easy with nothing to waylay you between regions, a long badly-organised rulebook showing translation strain, and thin encounter decks)
  - https://dungeondive.quest/t/a-look-at-the-dungeons-of-doria-prototype-part-1-the-stuff/2059 (2022-05-23 — a Game Crafter prototype built by Victor, a member of the Dungeon Dive Facebook group, ahead of crowdfunding; says up front he already wants the game and will be sorry to post it back; rates the rulebook better laid out than plenty of published ones while being clear this is a crunchy, older-feeling action-point design on d10s; **the loot is the headline** — 400+ cards, ranked with Dungeon Crusade, Dungeon Universalis and Quest for the Lost Pixel as kings of loot-in-the-base-box, each item carrying a line of lore, with traps shuffled into the same deck so searching is push-your-luck; 19 monsters × 4 levels multiplied by a modifier deck (soul eater, sweeping blow, doppelganger); 17 standalone scenarios plus four campaigns; one complaint about Game Crafter's sooty laser-cut chits)
  - https://dungeondive.quest/t/the-dungeons-of-doria-prototype-part-2-game-discussion/2055 (2022-05-24 — the play report; **the character system is the strongest praise and the clearest through-line to the Souls block running on the channel this fortnight** — like a FromSoftware game your class only sets opening stats and gear, levelling puts points into raw attributes, and since every item has attribute requirements you build toward the loot you find; demonstrates by drawing six random cards and speccing a character around a shield-blade; full worked example of the initiative/action-point track, where turns interleave by remaining points and your *final* action may go negative, making a 15-point hammer best swung last; armour breaks when used to negate damage, sets repair for the cost of the priciest piece; criticisms: the initiative track is visually cluttered despite being the core, starting weapons can't hurt armoured level-one monsters unless you take the warrior, and the rules say "adjacent" where they mean orthogonal)
  - https://dungeondive.quest/t/nanolith-a-look-at-the-prototype-of-this-cyberpunk-adventure-game/2060 (2022-08-15 — unpaid preview, with his standing note that he rarely does crowdfunding coverage without something worth showing; first reason for wanting it to exist is that there are too few cyberpunk adventure games, which prompts **a full detour through his cyberpunk shelf** — Bester's *The Stars My Destination* as ground zero, Rudy Rucker, Richard Paul Russo, Bruce Bethke who coined the word, the Sprawl trilogy — before landing on his favourite, John Shirley's *City Come A-Walkin'*, from which he reads a long passage on a punk band because it gets the punk rather than the cyber; mechanically the stress system marries theme to mechanism (every 1 rolled costs stress; the track shrinks each time it triggers, so pushing a cybernetic body harder makes it fail sooner); also nano-sync abilities and a hacker sidekick that downloads enemy programs and turns them back)
  - https://dungeondive.quest/t/rogue-angels-mass-effect-for-your-table-top-kickstarter-prototype-preview/2062 (2023-09-03 — accepts the "Mass Effect on your tabletop" framing, literal cut scenes included, and places it in the lineage he's described before of designers raised on video games now making tabletop ones; legacy elements are impermanent (dry-erase, repositionable stickers) so a campaign resets; **the cooldown-slot card system draws the most interest** — abilities are played onto a numbered slot and cycle back to hand as the timer ticks, while damage arrives as cards that clog those same slots until a character with all slots full falls unconscious; he explicitly prefers this to Gloomhaven's permanent card loss, comparing it to Tales from the Red Dragon Inn; bag-draw mini-game for doors and consoles banks successes across turns so the party can cooperate on one lock; closes frankly that he probably won't back it — three campaign books is more game than he knows he'll play)
  - https://dungeondive.quest/t/slay-the-dragon-an-osr-nsr-fantasy-rpg-crowdfunding-preview/2056 (2024-04-03 — a Polish OSR/NSR prototype with the practical complication that much of the box is still untranslated, so the read is based on English basic rules he printed himself; learns the system by rolling a character on camera — d3 attributes, then an archetype that determines *where* on a single d20 skill table you roll, low results giving weapon proficiencies and high ones magic, which he rates highly; his rogue ends up with no weapon proficiency at all, prompting a solo house rule; player-facing combat as an exchange of blows where you deal damage defending as well as attacking; treasure drawn blind as bag tokens, too dangerous to sort mid-dungeon, cashed against charts on exit; **main criticism is the absence of random tables and a proper bestiary** — the things a low-prep GM or soloist actually leans on)
  - https://dungeondive.quest/t/arcadia-tenebra-the-embodiment-of-a-flawed-gem-review/2058 (2024-05-28 — the finished game two years after the prototype above, framed as the embodiment of two ideas the hobby talks about constantly, the flawed gem and the passion project; indie roots everywhere — the thinnest cards he's seen, stapled zine rulebooks, a hand-packed box that arrived crushed in bubble wrap with a thank-you note inside; emphatic that it is a solo game, best true solo; **clear content warning given on camera** — gruesome violence, drugs, crude language and an unannounced sexual assault encounter; the review's best passage is a story not a mechanism: a lucky card had him steal Seven League Boots from a boy at a camp that happened to sit on his actual map position, and failing a test there next turn drew the needle-lined armour that could only be removed by returning and settling the debt; also takes the rulebook's "if unclear, roleplay it" seriously, deliberately choosing worse-odds encounters to honour the story, and finds the game much better for it)
  - https://dungeondive.quest/t/grimcoven-a-look-at-this-boss-battler-prototype-from-awaken-realms/2063 (2024-06-02 — an Awaken Realms prototype, no money exchanged and none offered; states the Bloodborne resemblance immediately, and notes that it being a *scenario* game rather than a campaign is part of why he agreed to look; **the corruption system is the design he likes most** — experience is called lament, slotting it unlocks abilities and eventually flips your hunter to a corrupted version with its own mini, but the higher you climb the nastier the corruption card drawn each turn, up to attacking your own allies; boss attack cards each represent a body part with its own health, and destroying one removes that attack permanently and triggers a reaction card beneath, compared to Kingdom Death; his favourite element is the environment card deck (carriage, well, pile of skulls, a witch's hut that adds a tile) keyed into secret cards that spin off escort side quests mid-fight, with the worry that engaging with them may feel like a wasted turn; criticisms: almost no flavour text, and a lot of fiddly tracking. Verdict: wait and see)
  - https://dungeondive.quest/t/neon-hope-a-cyberpunk-adventure-card-game-preview/2061 (2024-11-27 — opens by reading the scenario's introduction aloud; the framing is loss — **Civitas Nihilium (t/23) became one of his favourite games of that year and is now nearly unobtainable**, and Neon Hope occupies similar ground, described as the cybernetic offspring of Arkham Horror LCG and Netrunner, tonally cyberpunk crossed with solarpunk; locations and NPCs carry tokens cleared through four task types then flip to a second stage, often an NPC who joins as a follower; two systems praised — the chip pool works like Arkham's bag but three chips are set aside *unseen* at setup so you never know the exact contents, and the surveillance track doubles as timer and second front, with purple network cards you hack to keep the state off your back; reservations are about scope and specifically how much between-scenario deck-building there'll be, which he names as the part of Arkham he doesn't enjoy)
  - https://dungeondive.quest/t/dragons-down-natives-legends-kickstarter-preview/2054 (2025-01-05 — expansion preview for his game of the year 2024; spends the opening on two non-components: a campaign with no stretch goals and files already at the manufacturer, which he calls consumer-friendly after years of waiting, and the adventure journal, which he played a few games without and missed badly because tracking discoveries builds a story you can retrace; **the most striking change is subtractive** — the last scraps of flavour text are being deleted from the civilization cards, so priests are no longer the priests of the sacred grove but simply priests, completing the game's commitment to telling you nothing; he connects this to Shadows of Malice, whose designer he thinks should have held the line on having no art at all; content: a gnome lineage, eight classes including a Beast Master who tames roaming monsters and can fly the realm on a hired juvenile dragon, a Necromancer with four skeletons, three new native groups haggled for with the existing dice; notes one game where no new natives appeared at all and likes it — an underpopulated realm is its own story prompt)
- Keeper **series update** (register A, **309w body prose** — inside the 250–400 target; catalogue excluded): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/124. Framed as the table by the loading door where the Keeper puts things that have not finished becoming themselves, on the observation that every exhibit here describes an object that did not exist at the moment of description — and that the document routinely outlives the thing documented. The argument: a finished game tells you what it decided, a prototype tells you what it was still deciding, and these notes are often the only record anyone kept of that. **14-entry integrated Exhibit Catalogue**, chronological 2022→2025, both `related_imported_ids` folded in with no visual distinction from the 12 fresh imports (Dragons Down review t/308, Dragons Down: Desolation t/309). Hooks for those two drawn from their archived post bodies, not invented.
- **The chronology earns its keep twice in this catalogue.** Arcadia Tenebra appears at position 3 (2022 prototype) and position 9 (2024 finished review), two years apart in the same list, so the reader watches one object cross from the prototype table to the shelf proper — which is the whole thesis of the batch. And the three Dragons Down entries land 11 → 12 → 14, base game and expansion before the new preview, which is the order a reader needs them in and the reverse of import order.
- Stats: 1052 total, 833 imported, 208 pending, 11 no_transcript. Archive: 754 transcripts, 833 posts — dashboard cross-check matches the Keeper sign-off exactly.
- `series_queue.json`: all 12 IDs drained → `video_ids` empty → **`prototype-table` completed** and moved to `completed_series` (`parts_completed: 1`, `total_videos: 12`, `completed_date: 2026-08-14`, keeper_post recorded; `video_ids`/`videos_per_batch`/`one_shot`/`status`/`last_imported`/`related_imported_ids` dropped per the completed-entry convention). **`rotation_index` was 1 and was NOT incremented** — removing the completed entry from slot 1 left `active_series` one element long, so the index was merely clamped to 0. Remaining queue: `nearly-effortless-fun-pt2` (7 videos) — **the last active series.** Once it drains the queue is empty and `/import` will start skipping; a `/plan-batch` run is due.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-14 — Dark Souls Pt4 + Tower of Elmarsh priority drop (2 videos) — ad-hoc, queue untouched
- Decision tree: `fetch_channel_videos` found **2 new videos**, both pending and both published in the last 14 days (cutoff 2026-07-31) → **ad-hoc priority batch**, exit after posting. `series_queue.json` deliberately not mutated; the queue (`nearly-effortless-fun-pt2` 7, `prototype-table` 12, `rotation_index` 1) waits another cycle — that's two consecutive cycles the archive slate has been bumped, but the priority rule is unambiguous and the channel's upload cadence is what it is.
- Pre-flight: `git pull` fast-forwarded 77941cf→1d4511e (nightly `/refresh` dashboards only — `docs/content.html`, `docs/insights.html`). Rate limit OK (0/20 videos in 24h, full headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN → exit 1 (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). Both transcripts fetched cleanly (17.5k and 24.7k chars, **0 permanent and 0 transient failures**) — no index mutations beyond the imports.
- Posts (chronological, backdated, 230w and 234w):
  - https://dungeondive.quest/t/a-normal-guy-plays-dark-souls-part-4-the-depths-and-the-gaping-dragon/2050 (2026-08-10 — the deliberately short route through the Depths: shortcut opened, sewer proper mostly skipped, one detour for the large ember that triggers a homeward-bone round trip to Andre for claymore +7; Balder Shield traded for the spider shield on toxic resistance and, admittedly, looks; lore-adjacent commentary carries the episode — Balder as a kingdom named in item text and never visited, scepticism about the butchers being female, the theory that the kitchen is provisioning the dragon below; **answers a comment accusing him of knowing too much for a self-described noob** — hundreds of hours watching LobosJr and others supplies knowledge but not skill, demonstrated by his first death of the run being to gravity; the only real prep is killing the channeler that would otherwise buff the boss, then gold pine resin, Solaire pointedly not summoned to keep the health pool down, tail off before head; closes promising a mini-review of Blighttown as the level that made him feel something no other game has)
  - https://dungeondive.quest/t/tower-of-elmarsh-a-paupers-ladder-adventure-game/2051 (2026-08-12 — Paul Stapleton's open-world adventure gamebook that is also a board game and, in combat, a roll-and-write; review copy from the designer; premise sits inside established Pauper's Ladder lore, with Moon Towers risen across the land and a hero plus party of rogues/rangers/smiths/mages/adventurers/hawk guards racing a clock to bring one down; three books — rules, adventure paragraphs, locations — plus player aids and downloadable PDFs; keyword-and-checkbox system compared favourably to Fabled Lands, some map locations expanding into mini-maps that echo the small dungeons in Coppershell Bay, achievements page adding light roguelike progression across plays; **combat gets the closest look** — five white dice against rows of boxes (some linked) plus one enemy die that punishes matching values, each class bending dice differently and exhausting when used, walked through a worked encounter aiding a woman beset by wolves via ranger volley, two hawk guards and an adventurer reroll; enthusiastic verdict at ~$20, sole complaint the paper covers)
- Keeper **priority drop** (register B, **186w body** — inside the 100–200 target): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/123. Two-parcel framing, one damp with sewer water and one smelling of woodsmoke and paper. "From the deeper stacks" cross-reference went **all three entries to the Pauper's Ladder world** rather than splitting across both new videos: Moon Towers expansion (t/1808, 2022 — literally where the bone-white towers of Elmarsh's premise first rose), Crows of Coppershell Bay (t/130, 2024 — the tin dungeons Elmarsh's mini-maps are measured against), Pauper's Ladder comprehensive overview (t/1807, 2023). The Dark Souls half got no cross-reference **by design** — Parts 1–3 (t/1993, t/2017, t/2032) are all inside the last fortnight and were announced in the previous two drops, and the one genuine deep cut, Rune (t/1832), was spent on 2026-08-10. Padding it with a weak match would have been worse than omitting it, per the quality-over-quantity rule.
- Hooks for the three deep-stack entries were pulled from their archived post bodies (`archive/posts/rixzhpBKdfg_post.json`, `-27X7n7IstM_post.json`, `i6kooD4epJ0_post.json`), not invented. Those archived summaries also settled spelling the auto-captions garbled — "Pauper's Ladder" (not "Poppers"), "The Crows of Coppershell Bay", publisher Bedsit Games. The publisher name was left out of the new post rather than trusting the transcript; likewise the wolves in the worked example are described generically, since the caption rendering of their name is unreliable.
- Stats: 1052 total, 821 imported, 220 pending, 11 no_transcript. Archive: 742 transcripts, 821 posts — dashboard cross-check matches the Keeper sign-off exactly.
- Continuity note: the Souls block continues (Part 4 is the fourth in fifteen days) and Blighttown is explicitly set up for Part 5, so expect at least one more priority drop before the queue gets a look in. The Elmarsh review reopens the Pauper's Ladder seam, which now has ~8 imported videos across 2022–2026 — a plausible `/plan-batch` theme if any pending stragglers exist in it.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-10 — The Annals (10 videos) — queue drain, series completed
- Decision tree: `fetch_channel_videos` found 0 new videos; the 2 priority uploads were imported earlier today, so **0** pending in the last 14 days → no priority batch. Drained `active_series[1]` = `annals` (`one_shot`, `videos_per_batch: 10`, 10 IDs queued). Drift check: all 10 slate IDs confirmed `pending`, nothing skipped.
- Pre-flight: rate limit OK (2/20 videos posted in 24h from this morning's priority run, 18 headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN → exit 1 (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). All 10 transcripts fetched cleanly (7.5k–41.2k chars, **0 permanent and 0 transient failures**) — no index mutations beyond the imports. Note the day's transcript total across both runs was 12, right at the ~12–15 throttle ceiling; a third run today would be unwise.
- Posts (chronological, all backdated, 205–225w summaries):
  - https://dungeondive.quest/t/channel-update/2034 (2018-09-18 — three months' silence explained: a recording room too hot to light in summer, and hobby interests that move in extreme cyclical phases; the summer went to a total David Lynch immersion (*Fire Walk With Me* his favourite, a book about it a long-held ambition, *Twin Peaks: The Return* watched with his wife); announces the channel will widen to horror and weird fiction — Bartlett, Partridge's *Dark Harvest*, Bradbury, Sturgeon, King's *Cycle of the Werewolf* — while explicitly refusing the geek-culture-channel format; closes by accepting that some subscribers will leave and stating the channel only continues if it stays interesting to him. **The earliest articulation of the one-appetite thesis the whole Annals slate keeps returning to.**)
  - https://dungeondive.quest/t/the-dungeon-dive-collection-2019/2040 (2019-01-02 — establishes the annual January collection tour as a tradition; ~550 subscribers after year two, goal of a video a week, planned long series on Myth ("a flawed gem") and Shadows of Brimstone; Arcadia Quest sold for being competitive and four-player-best against a stated preference for solo-anytime games; Dungeon Saga sold with the video's best line — the long-awaited cult film finally on DVD whose special features read "English language, interactive menus" — and the specific charge that loot is divvied between chapters while every in-play chest holds potions; first appearance of the storage constraint that recurs for eight years)
  - https://dungeondive.quest/t/the-first-annual-dungeon-dive-game-awards-2019/2038 (2019-12-29 — eight categories, bad news first: Skull Tales as Biggest Disappointment, rules called a disaster and a developer response amounting to "our game is too complex for you", kept on the shelf in hope of a rework; Biggest Surprise ties Explore! Forests of Adrimon (talked past its drab iconography by a Tom Chick review) with Cthulhu: Death May Die; Best Support to Blackstone Fortress against Games Workshop's history of abandoning boxed games; Best Art to Dark Venture for singular-vision boldness over mere competence; Most Underrated to *Here's Negan* — his least-viewed review — for Negan as an independently-moving agent of chaos, plus a plea for more NPCs like him; top five ends on Hellboy **Kickstarter box only**, with the retail version explicitly excluded)
  - https://dungeondive.quest/t/the-state-of-the-channel-and-collection-2020/2042 (2020-01-12 — nearly 80 videos delivered against a 52 target, the year he found a rhythm; growth slower than the hoped-for 2,000 subscribers, diagnosed plainly as the cost of a single-subject niche he has no interest in widening; **the durable decision here is the Kickstarter-preview policy** — no more previews except for games he loves or badly wants funded, because the space is saturated and he'd rather discuss finished games than run advertisements; sell list reasoned rather than listed (Village Attacks on graphic design, Talisman 3rd's board going on the wall as art); Cave Evil bought openly as an art object he may never play; Horrified flagged as the top-five omission he regrets)
  - https://dungeondive.quest/t/the-dungeon-dives-2020-retrospective-and-look-forward-to-2021/2037 (2020-12-27 — no awards show, because only ~20 of 130 videos covered 2020 releases; Patreon launched at 40 patrons against an expectation of 10–20; the *Art Of* series begins (Cave Evil, Talisman 2nd) scored with his own music, defended as the thing distinguishing him from other board game channels; **the thesis video** — reading the old fiction convinces him sword and sorcery is dead as a publishing genre and has migrated wholesale into board and video games, making book coverage inseparable from game coverage even though those videos draw the fewest views and the most downvotes; disappointments candid, incl. Medara sold without a review to avoid dogpiling a Kickstarter darling; highlights are books — first-printing DAW Elric with Whelan covers, a 17-pound Taschen)
  - https://dungeondive.quest/t/the-state-of-the-collection-2021/2041 (2021-02-05 — a tour he wasn't going to film, made on request, and the reluctance is the story: roughly as much left as arrived; ~20 games inbound with no room forces a "super curated" collection where only what he loves survives; Bloodborne going, Dark Souls finally sold for ~$20 at a heavy loss, Sands of Sheerak out after the designer's answers convinced him he dislikes everything it adds over Forests of Adrimon; **two clean renunciations** — done with gamebooks (keeping only Fabled Lands) because he keeps trying to reignite an enthusiasm he no longer needs, and done with artistic RPG books after realising on the Super Blood Harvest review that only the owner enjoys the artistry, with a plea that those authors write solo games instead; predicts accurately that he'll rewatch and find he said he'd sell 60% of the collection)
  - https://dungeondive.quest/t/the-dungeon-dives-2021-year-end-review-patreon-questions-a-look-forward-to-2022/2036 (2021-12-19 — the longest and most personal of the set; **the patron Q&A is the substance** — he calculates ~10 cents an hour, admits he no longer knows whether his love of games sustains the channel or the channel sustains his interest, and ranks board games below books and music in his own hierarchy as the hobby he'd drop first; direct on moderation, noting the sword and sorcery book videos draw the most abuse at a fraction of the views, and defending discussion of misogyny/racism/colonialism in old pulp as encouragement to read clear-eyed rather than a warning off; calls peak dungeon crawl passed on manufacturing and shipping economics, says a big Kickstarter box now brings more stress than joy, and predicts design shifting as the Gloomhaven generation succeeds the HeroQuest generation; personal: leaving a 17-year white-collar job for manual labour at a ~50% pay cut; Sleeping Gods takes #1 as his new benchmark for campaign games)
  - https://dungeondive.quest/t/channel-update-future-of-the-dungeon-dive-and-all-fiction-is-fantasy/2035 (2022-10-31 — ends the Hobbycast: scripted and research-heavy, took longer than his videos despite being audio-only, never found traction; Fridays repurposed to solo RPGs on an analytics signal (the search term kept surfacing); **the headline is the channel split** — books move to *All Fiction is Fantasy* because YouTube dislikes multi-topic channels and Patreon alone won't pay the bills, with old book videos staying put but recompiled by subject into supercuts on the new channel; game-and-book crossover stays here as his distinguishing feature; candid on money — three days a week plus another job, patrons lost over two months, a solo RPG beginner's guide he'd hoped would go viral and didn't, and an admitted dislike of self-promotion. **Directly reversed in 2025 by t/1301.**)
  - https://dungeondive.quest/t/the-dungeon-dive-presents-2022-year-in-review-best-gaming-experiences-of-2022/2039 (2023-01-08 — the year he went part-time, ~30 hours a week, 180+ videos averaging half an hour, which he notes out-produces any TV show short of a soap opera; Solo RPG Friday launched, *Alone Together* with Perplexing Ruins began, creator interviews ran (Ghost b'twixt, Dungeon Crusade, Dark Venture, Silver Tower); countdown is explicitly experiences not releases — Familiar Tales at 10 as Hawthorne's best, Talisman Adventures at 6 as the surprise whose light/dark fate system inspired his own oracle, Explore! Domain of Mirza Noctis at 5 marking his return to the series; **#3 is the standout** — Shadows of Brimstone played as a solo RPG with a hex crawl, the most fun he's had with the game, arguing its cards could simply be tables with little lost; Popper's Ladder at 2, Lands of Galzyr at 1 as "the pinnacle of effortless fun")
  - https://dungeondive.quest/t/2023-year-in-review-channel-update-patron-q-a-best-gaming-experiences-of-the-year/2043 (2024-01-07 — opens asking viewers to be kind to themselves, then says why: cognitive decline from long covid he doesn't expect to fully recover from, and the deaths of his father-in-law, an old friend and his dog; still produced 150+ videos and describes the games as genuinely therapeutic; frank channel update — views never recovered from something around October 2022, YouTube isn't paying the bills, one more year at this level while shifting weight to Patreon, answered with a deliberate slowdown to ~2 videos a week covering fewer games in more depth, burned out on constantly learning new games rather than on playing; Runebound Retrospective named his proudest series and most frustrating reception; The Doomed for innovation, Doom Pilgrim best small game, Albion's Legacy deluxe the out-of-nowhere discovery, HeroQuest + fan-made Axian Quest cards rated among the best expansions he's played for anything; game of the year Freelancers)
- Keeper **series update** (register A, **353w body prose** — inside the 250–400 target; catalogue excluded): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/122. Framed as the shelf on which an archive records *itself*, with the observation that read in sequence these are not housekeeping but one man repeatedly rediscovering the same thing in a slightly different hand — that games, books, films and music are one appetite wearing four coats, and every attempt to file them separately fails within a year or two. **14-entry integrated Exhibit Catalogue**, chronological 2018→2026, all 4 `related_imported_ids` folded in with no visual distinction from the 10 fresh imports (Best Games of 2024 t/609, "I've made a huge mistake" t/1301, "Video Games? Why?" t/1161, Games of the Year 2025 t/1167). Hooks for the pre-existing four drawn from their archived post bodies. The chronology does real work here: t/2035 (2022, splitting the books off) and t/1301 (2025, admitting the split was a tactical error and folding them back) sit six entries apart in one list, which is the whole argument for ordering by publish date rather than import date.
- Stats: 1050 total, 819 imported, 220 pending, 11 no_transcript. Archive: 740 transcripts, 819 posts — dashboard cross-check matches the Keeper sign-off exactly.
- `series_queue.json`: all 10 IDs drained → `video_ids` empty → **`annals` completed** and moved to `completed_series` (`parts_completed: 1`, `total_videos: 10`, `completed_date: 2026-08-10`, keeper_post recorded; `video_ids`/`videos_per_batch`/`one_shot`/`status`/`last_imported`/`related_imported_ids` dropped per the completed-entry convention). **`rotation_index` held at 1, NOT incremented** — removing the entry at index 1 shifted `prototype-table` from slot 2 into slot 1, so the same index already points at the next series; incrementing would have skipped it. Remaining queue: `nearly-effortless-fun-pt2` (7), `prototype-table` (12) — 19 videos across 2 series.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-10 — Dark Souls priority drop (2 videos) — ad-hoc, queue untouched
- Decision tree: `fetch_channel_videos` found **2 new videos**, both pending and both published in the last 14 days (cutoff 2026-07-27) → **ad-hoc priority batch**, exit after posting. `series_queue.json` deliberately not mutated; the queue (`nearly-effortless-fun-pt2` 7, `annals` 10, `prototype-table` 12) waits one more cycle.
- Pre-flight: rate limit OK (0/20 videos posted in 24h, full 20 headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN → exit 1 (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). Both transcripts fetched cleanly (23.5k and 26.8k chars, **0 permanent and 0 transient failures**) — no index mutations beyond the imports.
- Posts (chronological, backdated, 240w each):
  - https://dungeondive.quest/t/a-normal-guy-plays-dark-souls-part-3-the-capra-demon/2032 (2026-08-07 — Black Knight hunting and Havel backstabbed through his own shield for the ring that buys carry-load headroom without losing the fast roll; lower Undead Burg as a catalogue of FromSoftware ambush vocabulary (bleeding dogs, paired torch hollows, three-door thief ambush); black leather set swapped in on *fashion souls* grounds; the Capra Demon — the wall he openly admits he was putting off filming — taken first try via the stairs-and-ledge routine, dogs first then a plunging attack; long farming tail for the Balder Shield, where he draws souls-as-currency-and-XP back to first-edition D&D gold and argues weapon upgrade level outranks character level)
  - https://dungeondive.quest/t/ten-tabletop-games-for-fans-of-dark-souls/2033 (2026-08-09 — defines the criteria first (exploration, lore, itemisation, combat beyond dice, mood) then measures ten picks against them rather than against Souls' difficulty; two out-of-print (*Dark Light: Memento Mori*, with one of the only real dodge-roll mechanisms in a board game; *Forgotten Depths*, exploration driven by room and corridor shapes plus a deck of bonfire conversations); gettable: *The Restless*, *Corrupted Crypts*, *Kernathalis*; *Vermis* and *Loom* as the metatextual pair — guidebooks for video games that never existed, the latter shipping an actual game plus VHS and vinyl; *Mork Borg* earning its slot on humour as much as grime; *Rune*/*Reap* modelling bonfires, respawns and world-state clocks directly; *Dungeons of Doria* on pure loot and aspirational stat-gated gear. Also notes on camera that the channel has been struggling on YouTube.)
- Keeper **priority drop** (register B, 178w body — inside the 100–200 target): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/121. Two-parcel framing, filed under *bonfire, adjacent to*. "From the deeper stacks" cross-reference is unusually well-earned this run — three of the ten games recommended in the new video are already in the archive, so the section links straight back to them rather than reaching for a genre resemblance: Darklight Memento Mori review (t/1653, 2018 — the list's own first pick), Vermis (t/1932), Rune (t/1832, whose title already reads "Dark Souls on your table").
- Stats: 1050 total, 809 imported, 230 pending, 11 no_transcript. Archive: 730 transcripts, 809 posts — dashboard cross-check matches the Keeper sign-off exactly.
- Continuity note: this is the third Dark Souls playthrough part in ten days (Parts 1–3 at t/1993, t/2017, t/2032), and the recommendations video lands two days after Part 3 — the channel is running a deliberate Souls block, so expect further priority drops in this vein before the queue gets a look in.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-10 — `/repair`: swept 384 stale `pending_imports` meta files
- Ran `repair_data.py cleanup`. Removed 384 orphaned `{video_id}_meta.json` files, all for videos already `imported`. `pending_imports/` is back to `.gitkeep` + `manifest.json`. Report total dropped 463 → 79 issues (the remaining 79 are missing local transcripts, issue #2 — unchanged).
- **The sweep was never missing.** `cleanup` has existed and worked correctly the whole time, and `report` has been printing `Stale pending_imports: N` as the largest number in its output. Nothing in the workflow ever called it: `/import` doesn't, and `/repair` is only run when someone already suspects a problem. Cause of the debris: `batch_post.py` archives the staged *transcript* on success but leaves the *meta* file, so meta files accrue one per imported video, run after run.
- `repair/SKILL.md`: documented what `cleanup` actually removes, that it should run on **every** `/repair` invocation (no flags, gitignored directory, nothing to lose), and — importantly — that it deliberately *keeps* staging files for still-`pending` videos, since those are a half-finished run the next `/import` resumes from without re-hitting the transcript API. Added the matching "run this every time" note to the subcommand table.
- `repair/SKILL.md`: fixed a real footgun. `--dry-run` is a **global** argparse flag and must precede the subcommand (`repair_data.py --dry-run cleanup`); written the natural way (`cleanup --dry-run`) it exits 2 with "unrecognized arguments" having done nothing. The Rules line said only "use `--dry-run` to preview changes" while every example in the file put flags after the subcommand. Same positioning applies to `--index`, `--archive-dir`, `--pending-dir`; only `--config` and `--limit` are subcommand args.
- `import/SKILL.md`: added a rule not to touch `pending_imports/` at end of run — `/repair` owns the sweep, and a bare `rm` would discard exactly the resumable staging files.
- No script changes (`scripts/*.py` untouched, per CLAUDE.md).

## 2026-08-07 — Nearly Effortless Fun, Part Two (7 videos) — queue drain, part 1 of 2
- Decision tree: **0** pending videos published in the last 14 days (most recent pending is 2025-01-19) → no priority batch. Drained `active_series[0]` = `nearly-effortless-fun-pt2` (`videos_per_batch: 7`, 14 IDs queued). Drift check: all 7 slate IDs confirmed `pending` in `video_index.json`, nothing skipped.
- Pre-flight: rate limit OK (0/20 videos posted in 24h, full 20 headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN → exit 1 (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos` found 0 new videos. All 7 transcripts fetched cleanly (12.4k–22.9k chars, **0 permanent and 0 transient failures**) — no index mutations beyond the imports.
- Posts (chronological, all backdated, 208–223w summaries):
  - https://dungeondive.quest/t/adventure-games-discover-the-story-the-dungeon-the-review/2031 (2019-11-21 — Kosmos' narrative-first sibling to the EXIT line; only complaint is the absurd title; four characters carrying one trait each (attentive/skilled/knowledgeable/strong) that matters by whose passage you're reading; no death, only lost health → worse ending; item cards combined by reading numbers lowest-first to hunt a matching book passage, non-existent passage = meaningless combination; chapters 2–3 permanently alter the dungeon and push you past content you'll never see; ~two good plays per group at ~$8/hour, then loanable indefinitely)
  - https://dungeondive.quest/t/destinies-app-based-adventure-time/2026 (2022-05-05 — skipped on Kickstarter, bought after a month of Facebook group enthusiasm; solo fell flat, four players sharing three characters was a great night; witch/huntsman/noble with two destinies each, the card-back clue the only hidden information; 2d6 vs a token track lowered by XP, rechargeable fate dice for big checks; **the standout** is item scanning that accommodates lateral use — a sword and an herb used in ways he assumed would be refused; sustained complaint about plastic bloat, minis too small to tell apart, expansion in a base-sized box a quarter full because of one figure)
  - https://dungeondive.quest/t/a-look-at-7-moons-heroes-of-dragon-reach/2028 (2022-07-31 — Gunpowder Studios, same house as Bag of Dungeon; accidental deluxe purchase; emissary of one of four kingdoms gathering wood/iron/stone before the shadow army arrives at the seventh moon; mount economy carries the decisions — foot 2d6-pick-one, 5g horse adds them, sacrifice horse + 10g for a dragon that flies over wilderness/lakes/mountains but flees on a 1 and carries less, so horse is the sweet spot; volatile market re-rolled on every sale; rates solo above two-handed co-op for its token-bag timer that changes board state rather than counting down; gripe: first 4–5 turns are dull, and he sketches the fix)
  - https://dungeondive.quest/t/wayward-an-ultimate-indie-game-and-the-ultimate-beer-pretzel-dungeon-city-crawl/2030 (2022-08-04 — Bruce Hurst review copy after a Facebook group member reminded him the game existed, having dismissed it years earlier as too simple; no box at all, ziploc pieces, double-sided vinyl poster, tiddlywink tokens; called a family-weight DungeonQuest; 12 action chips a turn, next player hoovers them with a magnetised wand he confesses to loving at 47; everything haloed on the board — axes, shields for trap thresholds, torches for staircase shortcuts, dock tokens, tarot re-rolls, unbreakable lock picks 1/2/3 that combine; 3d6 for bridge carrying capacity; Watchers room drags the 100-gold endgame threshold down while you're deep inside; mostly wants Hurst to sell maps for solo RPGs)
  - https://dungeondive.quest/t/familiar-tales-a-delightful-fantasy-adventure/2029 (2022-08-28 — declares his friendship with Jerry Hawthorne up front, having been hard on Aftermath's onboarding; best Plaid Hat rulebook since Dungeon Run, browser app needing no download, fully voice acted, runs enemy turns and tracks danger; four familiars raising a displaced princess across three eras, her mood managed and a crying baby able to alert guards; fail-forward via misfortune points; multi-use cards (might/agility/blocking/insight + movement + combo icons) with fatigue cards clogging the deck and adding danger; solo variant merges all four decks into one, which he prefers to four hands; culmination of Mice and Mystics → Stuffed Fables → Comanauts → Aftermath; had to physically stop playing to record)
  - https://dungeondive.quest/t/coraquest-an-adorable-family-weight-dungeon-crawl-with-a-lot-of-charm/2027 (2022-11-02 — Cora and Dan Hughes' father-daughter lockdown project, Cora's art tidied by her dad; HeroQuest territory, 1–4p family co-op, ages 6+, ten standalone quests with punning names and a troublesome gnome called Kevin; **the timer he genuinely admires** — explore to move the token to your card, fail to explore and it ticks, run out and spiders spawn on every web tile then it resets to 2; never a lose condition, just makes standing still expensive; pointed criticisms: always four heroes regardless of player count (his Mice and Mystics complaint), stingy dice, a determination re-roll that rarely rescues anything, and one unconscious hero ending the run — wants far more bad-luck mitigation in a children's game)
  - https://dungeondive.quest/t/bn1-an-adventure-game-city-crawl-set-in-the-modern-city-of-brighton/2025 (2022-11-15 — Paul Stapleton / Bedsit Games, of the beloved Popper's Ladder; tourist city crawl in modern Brighton, first to 50 anecdote points and back to the station; looks like roll-and-move and quietly isn't — five characters each with a bespoke 12-card deck drawn four at a time and spent completely, identical movement values carrying different bonuses; bus day-savers, cabs, busking, park-eaten provisions, memorabilia shop decks, oversized destination cards with press-your-luck teeth; the local lore is what he keeps returning to — Max Miller, Doreen Valiente, Fatboy Slim, and George Montague and Disco Pete, to whom the game is dedicated; the rule against counting spaces on your own turn read as simulated city bustle)
- Keeper series update (**369w body prose**, inside the 250–400 target; catalogue excluded per register A): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/120. Framed as a *second* crate arriving at the same low shelf — a deliberate callback to Part One's "The Unhurried Crate" — with the argument that box weight and adventure size are unrelated quantities. **12-entry integrated Exhibit Catalogue**, chronological 2019→2025, all 5 `related_imported_ids` folded in with no visual distinction from the 7 fresh imports (Bag of Dungeon t/1710, Roll Player Adventures t/1869, Lands of Galzyr t/1867, Quests over Coffee t/1868, Five (Nearly) Effortlessly Fun Games t/1870). Hooks for the pre-existing five were drawn from their archived post bodies. Nice bit of self-corroboration surfaced by the chronology: 7 Moons and BN1, both imported today, reappear years later on Daniel's own five-most-effortless list (t/1870).
- Stats: 1048 total, 807 imported, 230 pending, 11 no_transcript. Archive: 728 transcripts, 807 posts — dashboard cross-check matches the Keeper sign-off exactly.
- `series_queue.json`: 7 IDs drained from `nearly-effortless-fun-pt2`, **7 remaining** (`8UWpsEyQwCU`, `Ao4VRNX_h4A`, `IQ3zeRLgnt4`, `NX-1jJ1PuxY`, `cga1y52KSCk`, `bJHikj8skz4`, `6ob9UwPviJA`) → series continues, `last_part: 1`, `last_imported: 2026-08-07`, keeper_post recorded. **`rotation_index` incremented 0 → 1** (round-robin fairness, entry not completed) — now points at `annals`. Remaining queue: `nearly-effortless-fun-pt2` (7), `annals` (10), `prototype-table` (12) — 29 videos across 3 series.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-06 — Dark Venture (6 videos) — queue drain, series completed
- Decision tree: **0** pending videos published in the last 14 days → no priority batch. Drained `active_series[0]` = `dark-venture` (one-shot, `videos_per_batch: 6`). Drift check: all 6 slate IDs confirmed `pending` in `video_index.json`, nothing skipped. This is the slate deferred one cycle by yesterday's Arkham Horror priority drop.
- Pre-flight: rate limit OK (2/20 videos posted in 24h, 18 headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN → exit 1 (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos` found 0 new videos. All 6 transcripts fetched cleanly (11.5k–30.9k chars, **0 permanent and 0 transient failures**) — no index mutations beyond the imports.
- Posts (chronological, all backdated, 226–238w each):
  - https://dungeondive.quest/t/dark-venture-kickstarter-preview-take-a-look/2021 (2018-11-19 — unpaid, unsolicited KS preview Daniel requested himself after seeing the art; 1–4p adventure card game, Dungeoneer comparison; players build the map from hand; blue location paragraphs + green actions-book branches as interactive fiction; NPCs built identically to heroes, lootable; 12 rounds sunrise→sunset; TSR / Gamma World / City of Chaos influences named; admits to a year on a similar design of his own)
  - https://dungeondive.quest/t/dark-venture-review-and-give-away/2024 (2020-02-17 — full verdict + game/Vile Invaders giveaway supplied by Robert Lemon, who also drew the DD clipboard logo; reads the Cataclysm intro; enemies placed to wall opponents off quest sites; won his 2019 best-art award; complaints precise — too-small rulebook with a 12-page BGG errata PDF, exactly one helmet in the item deck; his house solo rules adopted semi-officially)
  - https://dungeondive.quest/t/battle-of-the-ancients-a-look-at-the-demo-version/2022 (2020-10-22 — the skirmish spinoff, a genre he says outright isn't his; four asymmetric demo factions (Vorpin/Bomark/Orpal/Dargon), S and D values as dice counts, genetic memory banking up to 3 faces; wants the narrative scenarios and the small quadrant over the full 16×16 map)
  - https://dungeondive.quest/t/dark-venture-further-discussion/2023 (2021-05-09 — discussion-over-photos format experiment; the **seeding** argument: roguelikes publish seeds, board games don't, so why not ship a deck-stacking order as bespoke narrative; Princess Bretta's rowboat quest, Deathbed Isle's red-smoke hero, the sword-obsessed Dirt Twins landing on a Blade Hoarder side quest; peated Islay scotch as the pace metaphor)
  - https://dungeondive.quest/t/dark-venture-battle-of-the-ancients-a-look-at-the-pre-production-game-and-expansions/2020 (2022-10-02 — three near-final boxes opened at once; five base factions incl. the Alder King; double-sided map, overlays stacking into upper floors; scenario/adventure/victory modes, 13 solo-capable scenarios, faction guide on the flip of book B; secret reward cards as light legacy; announces the DV reprint and his solo rules going official)
  - https://dungeondive.quest/t/dark-venture-battle-of-the-ancients-narrative-skirmish-battles-in-a-weird-and-twisted-world/2019 (2023-01-18 — five things after real play; Dargon vs Bomark + Alder King in adventure mode; two complaints, both about gathering — the 50/50 d6 and rules asking players to *agree* whether a square could hold wood; quackalope dropping grenade eggs; AI chases whatever moved, so stillness steers it; "both grotesque and compassionate" on Lemon's art)
- Keeper series update (323w body prose, inside the 250–400 target; catalogue excluded from the count as per register A): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/119. Framed as a **correspondence** rather than a review cycle — the unsolicited 2018 letter, the house rules that became official rules, the logo that ended up in the background of hundreds of unrelated videos. **10-entry integrated Exhibit Catalogue**, chronological 2018→2026, all 4 `related_imported_ids` folded in with no visual distinction from the 6 fresh imports (Rob Lemon interview t/273, new expansions t/225, Grimgrove/soundtracks t/1226, 2nd Edition review t/1262). Hooks for the pre-existing four were drawn from their archived post bodies rather than invented.
- Stats: 1048 total, 800 imported, 237 pending, 11 no_transcript. Archive: 721 transcripts, 800 posts — dashboard cross-check matches the Keeper sign-off exactly.
- `series_queue.json`: `dark-venture` drained to empty → removed from `active_series`, appended to `completed_series` (`parts_completed: 1`, `total_videos: 6`, `completed_date: 2026-08-06`, keeper_post retained). **`rotation_index` left at 0** — removal already shifted the next series into the slot, so it now points at `nearly-effortless-fun-pt2` (14 videos, 2×7). Remaining queue: `nearly-effortless-fun-pt2`, `annals`, `prototype-table` — 36 videos across 3 series.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-06 — Arkham Horror 2nd Edition Remastered (1 video) — ad-hoc priority drop
- Decision tree: 1 priority pending in last 14 days (`pCghepSi0M8`, published 2026-08-05T16:00Z) → ad-hoc priority batch, exit after posting. Queue untouched. **This deferred the freshly-planned `dark-venture` slate by one cycle** — `active_series` was populated earlier the same session (see below), so unlike the last three runs there was a real batch waiting.
- Pre-flight: rate limit OK (1/20 videos posted in 24h, 19 headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos` found 1 new video (`pCghepSi0M8`). Transcript fetched cleanly (17,063 chars, 0 permanent and 0 transient failures).
- Post:
  - https://dungeondive.quest/t/arkham-horror-2nd-edition-remastered-my-thoughts/2018 (FFG's new "Vault" reprint line opens with AH2e, Gamefound October 2026; Daniel reacts as a fan with no insider access, going all-in but only on components that affect play; praises the clearer board — legible roads, bridges restored, topographic Other World border — the respectful box, and cardboard standees kept instead of plastic bloat; "the complete collection" read as all four large + four small expansions with a fifth box consolidating the smalls; reservations on warping double-layer dashboards, board footprint (wants a Darkest Night 2e fold), pastel investigator card backs, vague "new gameplay elements"; wish list of packed-in history, artist credits, Miskatonic Horror folded into the other expansions, and 1–2 investigator scaling; states plainly he'd rather have had a fourth edition, citing his own interview with Richard Launius; 2026-08-05, 249w)
- Keeper priority drop (alert register, inside the 250 cap) with a 3-entry **From the deeper stacks** cross-reference — AH2e at 20 years (t/14, the verdict on the game being remastered), Arkham Horror 1987 (t/16, Launius's original and the 4e that never came), Eldritch Horror / Brian Lumley (t/1545, the pulp lineage Daniel wants documented in the new box): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/118.
- Stats: 1048 total, 794 imported, 243 pending, 11 no_transcript. Archive: 715 transcripts, 794 posts.
- `series_queue.json`: unchanged (priority runs never mutate the queue). `active_series` holds 4 series / 42 videos queued this session by `/plan-batch` — `dark-venture` (6, one-shot) at rotation_index 0, then `nearly-effortless-fun-pt2` (14, 2×7), `annals` (10, one-shot), `prototype-table` (12, one-shot). Next non-priority `/import` drains Dark Venture.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-06 — `/plan-batch`: 4 series queued (42 videos), queue refilled from empty
- Queue had been empty since `hobbycast-2022` completed on 2026-08-03. Proposed 4 candidates from the 243-video pending pool; user queued all four in their stated order.
- **Playlist signal pass** (86 playlists fetched live, membership filtered to owner uploads): most themed playlists are already fully imported. Two useful negative findings — the *Dungeon Synth* (41 items), *vaporwave* (26) and *Radio dramas* (13) playlists are almost entirely **other creators' uploads**, so they are not viable themes despite reading as open territory; and *Nearly Effortless Fun* has 14 of 23 owner videos still pending, the largest genuinely-uncovered curated playlist on the channel.
- Also surfaced an archive gap worth a future `/repair` or straggler sweep: **Wander Part 6 (`dFH36q7iWiU`) is pending while Parts 1–5 and 7 are imported**, and it is missing from Daniel's own Wander playlist. A *Loose Pages II* sweep of 11 playlist-verified stragglers (Wander ×5, Peril of Cymbaline Isle ×3, Four Against Darkness ×2, a DungeonQuest Quick Hit) was offered and not taken this round.
- Queued (rotation order as listed by user):
  - `dark-venture` — 6 videos, one-shot, 4 cross-refs. 2018 Kickstarter preview → 2023 Battle of the Ancients, with 4 already-imported videos (incl. the Rob Lemon designer interview) making an integrated 10-entry catalogue spanning 2018–2026. Dropped `3Cm_qVj04z0` from the proposed 7 — a 3:10 giveaway winner announcement, too thin for a 150–250w summary.
  - `nearly-effortless-fun-pt2` — 14 videos, 2 parts of 7, 5 cross-refs. Framed explicitly as Part Two of `effortless-fun-cozy-adventures` (completed 2026-06-30); 4 of its 5 cross-refs already appeared in that Keeper post's catalogue. Best-performing slate at avg 5,134v vs a 4,553v channel median.
  - `annals` — 10 videos, one-shot, 4 cross-refs. Gapless year-end/state-of-the-channel spine 2018–2024. Weakest on views (avg 3,292v, below median) — a heritage batch, not a traffic batch. Excluded `Aq3emUbqTbA` ("Welcome to the Dungeon Dive!", 0:30) as too short to transcribe usefully, plus the Patreon and T-shirt announcements.
  - `prototype-table` — 12 videos, one-shot, 2 cross-refs. Prototypes and pre-production previews; contains both the 2022 *Arcadia Tenebra* prototype and its 2024 review. Only two clean payoff cross-refs exist (Dragons Down review + expansion) because most of these prototypes never got a follow-up video — arguably the theme's point. Held back Legends Untold KS preview, Peacemakers (1,252v), Bloodsport Gambler.
- Validation before write: every slate ID confirmed `pending`, every `related_imported_ids` entry confirmed `imported` with a non-null `discourse_topic_id`, no video duplicated across slates, no theme-slug collision with `completed_series`. `rotation_index` set to 0 (`active_series` was empty).
- Note: `transcript_analytics.json` / `youtube_stats.json` were 6 days stale (2026-07-30) at planning time. View counts are stable enough for relative ranking, and the pending pool has no taxonomy tags anyway (those derive from transcripts), so playlist membership and title scanning carried the selection. Worth a `/refresh` before the next planning pass.

## 2026-08-05 — A Normal Guy Plays Dark Souls Part 2 (1 video) — ad-hoc priority drop
- Decision tree: 1 priority pending in last 14 days (`JpctKDg71Pg`, published 2026-08-03) → ad-hoc priority batch, exit after posting. Queue untouched — and empty in any case since `hobbycast-2022` completed on 2026-08-03, so nothing was deferred by taking the priority path.
- Pre-flight: rate limit OK (0/20 videos posted in 24h, full headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos` found 1 new video (`JpctKDg71Pg`). Transcript fetched cleanly (36,055 chars, 0 permanent and 0 transient failures).
- Post:
  - https://dungeondive.quest/t/a-normal-guy-plays-dark-souls-part-2-ringing-the-first-bell-of-awakening/2017 (Hellkite bridge → first Bell of Awakening; two noob traps named — the unscaling Drake Sword he leaned on for half his first playthrough, and the Ring of Favor and Protection that breaks on removal; Lautrec kicked off the ledge without aggro; Solaire summoned for the Bell Gargoyles for the first time in ~8 years; the Firelink elevator that took him 30 hours to reach originally, tied to an argument for limited fast travel and against Elden Ring's open world; 2026-08-03, 229w)
- Keeper priority drop (166w body, alert register, inside the 100–200 target) with a 3-entry **From the deeper stacks** cross-reference — Part 1 (t/1993, the run's start), Hobbycast E1 (t/2011, the full FromSoftware ranking incl. the Elden Ring and Sekiro complaints Part 2 alludes to), Rune (t/1832, Dark Souls folded onto cardboard): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/117.
- Stats: 1047 total, 793 imported, 243 pending, 11 no_transcript. Archive: 714 transcripts, 793 posts.
- `series_queue.json`: unchanged (priority runs never mutate the queue). **`active_series` is empty** — `/plan-batch` still needed before the next non-priority `/import`.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-03 — Hobbycast: The 2022 Podcast Run (12 videos) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days (yesterday's `aEQu0cO-iG8` already imported) → queue drain. `hobbycast-2022` at rotation_index 0 (one_shot, vpb=12). All 12 drift-checked `pending`, none skipped — the slate survived intact after waiting two deferred cycles.
- Pre-flight: rate limit OK (1/20 videos posted in 24h, 19 headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos` found 0 new videos.
- Transcripts: **12/12 fetched cleanly** (8,199 → 39,567 chars), 0 permanent and 0 transient failures. Full 12 in one pass sits at the low end of the ~12–15/hr throttle; no back-off needed.
- The channel's audio wing. Daniel started the Hobbycast in April 2022 explicitly because the YouTube algorithm penalises range — so everything that would have diluted the main channel (SF paperbacks, anime, 1950s radio drama, other people's small channels, his own complaints) went into a podcast instead. The run is unusually confessional: three FromSoftware games abandoned because they outran his reflexes, playing board games named as sometimes the worst part of owning them, and an AMA that reads as autobiography.
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/dungeon-dive-hobbycast-e1-intro-and-ranking-of-soulsborneringkiro-games/2011 (E1 — why the podcast exists; every modern FromSoft game ranked, DS3 last and *Bloodborne* first; DS2 defended as a game about memory; 2022-04-01, 203w)
  - https://dungeondive.quest/t/dungeon-dive-hobbycast-episode-2-ten-things-i-look-for-in-a-great-dungeon-crawl-or-adventure-game/2010 (E2 — ten criteria checked against his top 10; character campaigns over narrative ones; loot with lore not bigger numbers; 2022-04-08, 205w)
  - https://dungeondive.quest/t/dungeon-dive-hobbycast-episode-3-game-purge-2022/2012 (E3 — ~two dozen sales, each with a cause of death; shelf space and solo play do the deciding; *Hero Path* as "Talisman by way of an educational toy store"; 2022-04-15, 216w)
  - https://dungeondive.quest/t/hobbycast-episode-7-ten-great-science-fiction-novels/2016 (E7 — ten novels read off a physical stack; Stapledon's *Sirius* the only book to make him cry in public; Bester named best SF ever written; 2022-05-06, 201w)
  - https://dungeondive.quest/t/episode-9-top-5-japanese-animated-science-fiction-things/2008 (E9 — *Akira* fifth, *Galaxy Express 999* first; the cut list is longer than the list; 2022-05-13, 195w)
  - https://dungeondive.quest/t/episode-12-when-playing-board-games-is-my-least-favorite-part-of-the-hobby/2007 (E12 — the effort-to-pleasure ratio; every other medium settled its conventions; proposes licensing engines so designers spend effort on art and story; 2022-06-03, 208w)
  - https://dungeondive.quest/t/hobbycast-episode-15-how-to-make-better-game-recommendations/2006 (E15 — five fixes, starting with asking questions; you don't have to like what you recommend; community-scale stakes; 2022-06-24, 201w)
  - https://dungeondive.quest/t/episode-19-top-5-audio-radio-dramas/2015 (E19 — golden age → revival history; *X Minus One* first; laments that sword and sorcery was ignored by the form; 2022-07-22, 188w)
  - https://dungeondive.quest/t/episode-21-a-handful-of-youtube-channels-to-enjoy/2009 (E21 — eight channels, nearly all under 5k subs, chosen for lo-fi; splices himself back in mid-episode to add a forgotten one; 2022-08-06, 189w)
  - https://dungeondive.quest/t/episode-24-five-games-to-get-get-back-to-the-table/2014 (E24 — *Bloodborne* re-evaluated, *Robinson Crusoe* and *Nemo's War* unlearned, the obstacle named as mental; 2022-08-26, 193w)
  - https://dungeondive.quest/t/episode-25-ask-the-dungeon-dive-anything/2013 (E25 — three collecting eras; the given-away Pokémon cards; three zines, print-on-demand, never crowdfunded; Gonzo; 2022-09-02, 199w)
  - https://dungeondive.quest/t/episode-26-my-ten-least-favorite-things-about-dungeon-crawl-and-adventure-games/2005 (E26 — the mirror of E2; every complaint illustrated with a game he loves; chits at number one; 2022-09-09, 201w)
- Keeper series post ("The Hobbycast — The 2022 Run" — 368w prose, series register inside the 250–400 target; Exhibit Catalogue of 17, chronological, integrating all 5 `related_imported_ids` inline with the 12 new and no new/existing distinction: Hobbycast 4 / MORK BORG (t/1268), Hobbycast 14 / Top 50 postmortem (t/1588), Ep 22 / New Edge Sword & Sorcery (t/1359), Ep 23 / Pete Jank (t/1242), FOMO (t/1552)): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/116.
- Stats: 1046 total, 792 imported, 243 pending, 11 no_transcript. Archive: 713 transcripts, 792 posts.
- `series_queue.json`: `hobbycast-2022` fully drained (12/12 imported, no drops) → moved to `completed_series` (parts_completed: 1, total_videos: 12, completed_date: 2026-08-03, keeper_post retained). **`active_series` now empty**; rotation_index clamped to 0. Next run has nothing to drain — **run `/plan-batch` before the next `/import`** or it will skip cleanly.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-03 — Astroprisma: Expansion Overview and Cybersphere Update (1 video) — ad-hoc priority drop
- Decision tree: 1 priority pending in last 14 days (`aEQu0cO-iG8`, published 2026-08-02) → ad-hoc priority batch, exit after posting. Queue untouched; drain waits one cycle (second consecutive cycle deferred — `hobbycast-2022` has now waited twice).
- Pre-flight: rate limit OK (0/20 videos posted in 24h, full headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos` found 0 new videos — `aEQu0cO-iG8` was already in the index from a prior fetch. Transcript fetched cleanly (11,085 chars, 0 permanent and 0 transient failures).
- Post:
  - https://dungeondive.quest/t/astroprisma-expansion-overview-and-cybersphere-update-solo-rpg/2004 (follow-up to the 2026-07-12 Astroprisma review — the Cybersphere hacking-legend criticism withdrawn after viewers found it printed one page early in the settlement-activities spread; six expansions ranked: Exo Anomaly (connective tissue between set pieces, bundled with his copy) > Cloud Nine Casino (five-chapter Ambrosia infiltration) > Wanted (six bounties + contractor/hiding-place/complication/twist tables) > Vaporwave 3000, Sea of Neon, Ceramic Skin; album picks The Black Dog *Feral Grace* and Eno/Lanois/Eno *Apollo*; 2026-08-02, 234w)
- Keeper priority drop (135w body, alert register, well under the 250 cap) with a 3-entry **From the deeper stacks** cross-reference — Astroprisma original review (t/1919, the review this despatch amends), Grimscar Expanded (t/1697, same expansions-overview exercise on a different shelf), CY_Korg (t/1558, cyberpunk stripped to its meanest parts): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/115.
- Stats: 1046 total, 780 imported, 255 pending, 11 no_transcript. Archive: 701 transcripts, 780 posts.
- `series_queue.json`: unchanged (priority runs never mutate the queue). 1 series / 12 videos still queued: hobbycast-2022 (rotation_index 0).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-02 — The Drafting Table: Design, Art, and Conversation (8 videos) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days (yesterday's `r6_PIKzQJ8Q` already imported) → queue drain. `drafting-table` at rotation_index 0 (one_shot, vpb=9). All 9 drift-checked pending, none skipped.
- Pre-flight: rate limit OK (1/20 videos posted in 24h, 19 headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos` found 0 new videos.
- Transcripts: 8/9 fetched cleanly (33,058 → 68,067 chars). **1 permanent failure** — `Tj9CJM4ti2w` (*The Art of Cave Evil*) returned `TranscriptsDisabled`, marked `no_transcript` in `video_index.json`. 0 transient failures. Day's transcript total = 9, at the low end of the ~12–15/hr throttle.
- The channel's making-of wing: art-forward modules bought to read rather than run, the two-year *Alone Together* conversation with Allan of Perplexing Ruins, and the two Design Diaries where Daniel autopsies a decade of his own dead prototypes and names the disease (patching bad rules instead of going back to fix them).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/silent-titans-a-look-at-the-new-artistic-rpg-module-from-patrick-stuart/2001 (Silent Titans — the module-as-artwork at its usable limit; Into the Odd rules on a bookmark; read as weird fiction, never run; 2019-04-25, 218w)
  - https://dungeondive.quest/t/exploring-the-perplexing-ruins-fallen-campaign-notebook-hilgaarb-and-more/1997 (Fallen / Hilgaarb — usage die and gear-depletion die; rank-and-wound combat; a five-stage grave-robbing built with Untold Encounters; 2022-07-10, 206w)
  - https://dungeondive.quest/t/alone-together-with-the-dungeon-dive-and-perplexing-ruins-episode-1-solo-rpg-friday/1995 (Ep 1 — Allan's route in via d100 Dungeon; both abandon the term OSR; $15 outfits a table for years; 2022-11-18, 190w)
  - https://dungeondive.quest/t/alone-together-with-perplexing-ruins-and-the-dungeon-dive-episode-2/2000 (Ep 2 — heroes don't die because then there's no story; threat tiers over attrition; Deadball as a curveball; 2022-12-23, 198w)
  - https://dungeondive.quest/t/alone-together-episode-3-games-game-design-and-world-building-mechanisms/1998 (Ep 3 — the League of Dungeoneers review discourse; Zine Quest overload; the **long tail** and Vaults of Vaarn as the model; 2023-03-10, 189w)
  - https://dungeondive.quest/t/alone-together-with-the-dungeon-dive-and-perplexing-ruins-science-fiction-and-other-stuff/1996 (Ep 4 — why sci-fi is harder than dungeons; empty space as a feature; Space Aces beats Starforged; gumption instead of HP; 2023-06-02, 198w)
  - https://dungeondive.quest/t/design-diary-1-all-aboard-the-fail-train-next-stop-the-island-of-discarded-game-ideas/1999 (Diary #1 — Talisman/Mertwig's Maze/Runebound/Arkham Horror as sources; the prototype graveyard; don't patch, go back; 2023-07-25, 193w)
  - https://dungeondive.quest/t/design-diary-2-a-land-in-peril-artist-reveal-discussing-challenges-player-questions/1994 (Diary #2 — name and artist revealed (Craig Price); milestones destroy map locations instead of buffing the boss; 2023-09-17, 188w)
- Keeper series post ("The Drafting Table" — 308w prose, series register inside the 250–400 target; Exhibit Catalogue of 13, chronological, integrating all 5 `related_imported_ids` inline with the 8 new with no new/existing distinction: Hobbycast 16 / Dustin Freund (t/275), Rob Lemon interview (t/273), Jason Glover conversation (t/276), Artist Trading Cards (t/1300), Game Crafter with JT Smith (t/809)): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/114.
- Stats: 1045 total, 779 imported, 255 pending, 11 no_transcript. Archive: 700 transcripts, 779 posts.
- `series_queue.json`: `drafting-table` drained (8 imported + 1 no_transcript dropped) → moved to `completed_series` (parts_completed: 1, total_videos: 8, completed_date: 2026-08-02, keeper_post retained, note records the dropped `Tj9CJM4ti2w`). rotation_index stays 0 (removal shifts remaining forward) → next is `hobbycast-2022`. 1 series / 12 videos remain queued.
- Skill patch: `import/SKILL.md` drain step now says to remove **permanent-failure IDs from the same slate** alongside the imported ones. Previously only imported IDs were dropped, so a `no_transcript` video left in `video_ids` would force a wasted rotation where the next run drift-checks the slate to nothing and completes the series anyway — same end state, one cycle later. Transient failures still stay in `video_ids` to retry.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-08-01 — A Normal Guy Plays Dark Souls Part 1 (1 video) — ad-hoc priority drop
- Decision tree: 1 priority pending in last 14 days (`r6_PIKzQJ8Q`, published 2026-07-31) → ad-hoc priority batch, exit after posting. Queue untouched; drain waits one cycle.
- Pre-flight: rate limit OK (0/20 videos posted in 24h, full headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos` found 1 new video. Transcript fetched cleanly (33,058 chars, 0 permanent and 0 transient failures).
- Post:
  - https://dungeondive.quest/t/a-normal-guy-plays-dark-souls-part-1-intro-through-taurus-demon/1993 (Digital Dive casual let's play — hunter start, master key, claymore build; Dark Souls as level-design masterclass; no-tutorial design; Firekeeper Soul suicide run, Petrus' stashed treachery, Solaire, Taurus Demon via gold pine resin; two episodes planned, more depends on views; 2026-07-31, 239w)
- Keeper priority drop (169w body, alert register, well under the 250 cap) with a 3-entry **From the deeper stacks** cross-reference — Rune (t/1832, Dark Souls on the table), Revisiting Bloodborne: The Board Game (t/1833, same studio, less kind translation), Video Games? Why? Channel Update (t/1161, why the Digital Dive exists): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/113.
- Stats: 1045 total, 771 imported, 264 pending, 10 no_transcript. Archive: 692 transcripts, 771 posts.
- `series_queue.json`: unchanged (priority runs never mutate the queue). 2 series / 21 videos still queued: drafting-table (9, rotation_index 0), hobbycast-2022 (12).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-31 — What I Talk About When I Talk About Dungeon Diving (11 videos) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days (all six most-recent uploads already imported) → queue drain. `witawitadd-essays` at rotation_index 0 (one_shot, vpb=11). All 11 drift-checked pending, none skipped; full slate fetched cleanly (9,506 → 32,008 chars, 0 permanent and 0 transient failures). Day's transcript total = 11, under the ~12–15/hr throttle.
- Pre-flight: rate limit OK (5/20 videos posted in 24h, 15 headroom), config OK (Discourse admin confirmed → backdating works), integrity WARN (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos` found 0 new videos.
- The channel's essay wing: nine WITAWITADD entries (2019–2022, incl. the unlabelled *Confessions of a Rule Book Junkie*) plus the two *Diving In* episodes that succeeded the series. No games on the table — the archivist working backwards from the shelf to the reason for the shelf.
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/what-i-talk-about-when-i-talk-about-dungeon-diving-episode-one/1984 (Episode One — collections aren't personality tests; the 1984 red box during the Satanic Panic; imagination as a tool that dulls unused; 2019-01-30, 224w)
  - https://dungeondive.quest/t/witawitadd-episode-two-house-rules/1988 (House Rules — the Order of Vampire Hunters timer made elastic, deferred armour damage, carried-over XP; 2019-05-19, 243w)
  - https://dungeondive.quest/t/witawitadd-yo-dawg-i-heard-you-like-games/1990 (Yo Dawg — games played before games: Microscope, Fiasco, The Quiet Year, Call to Adventure, Life and Legend; 2019-11-09, 241w)
  - https://dungeondive.quest/t/witawitadd-exploration/1985 (Exploration — the five ingredients of the *illusion* of exploration; Forgotten Depths' tetromino legendary locations; 2019-12-12, 229w)
  - https://dungeondive.quest/t/witawitadd-escapism/1989 (Escapism — recorded late March 2020; escapism starts at the storefront, not the table; the R2-D2 fire hydrant; 2020-03-30, 234w)
  - https://dungeondive.quest/t/witawitadd-empty-tombs/1987 (Empty Tombs — answering the "nothing happens" complaint; Anor Londo's emptiness as choice, not limit; 2020-04-21, 243w)
  - https://dungeondive.quest/t/witawitadd-slow-questing/1982 (Slow Questing — upkeep as the test of a leave-standing game; Runebound house rules; Fabled Lands' purchasable house; 2020-05-06, 246w)
  - https://dungeondive.quest/t/confessions-of-a-rule-book-junkie/1986 (Rule Book Junkie — NES manuals as the origin story; ten rulebooks he admires; credit your artists, include an index; 2020-12-13, 250w)
  - https://dungeondive.quest/t/lets-talk-about-combat-witawitadd/1992 (Combat — the genre's central verb, mostly unloved; KDM S-tier, Space Hulk most intense, initiative tracks worth stealing; 2022-02-27, 247w)
  - https://dungeondive.quest/t/diving-in-episode-1-why-do-i-love-dice/1991 (Dice — luck grants permission to lose; five dice systems ranked; the unidentified plus/minus die; 2023-12-07, 250w)
  - https://dungeondive.quest/t/diving-in-episode-2-stat-tests-and-my-issues-with-player-focused-puzzles-in-rpgs/1983 (Stat tests — a viewer comment reframed; if the GM tests your wits, why not your deadlift?; 2023-12-21, 250w)
- Keeper series post ("What I Talk About When I Talk About Dungeon Diving" — 180w prose / 500w total, series register at the hard cap; Exhibit Catalogue of 16, chronological, integrating all 5 `related_imported_ids` inline with the 11 new with no new/existing distinction: Shadows of Brimstone Part 30 house rules (t/1518), Expedition to Skull Island (t/1825), Why I don't do let's plays (t/1956), My thoughts on AI art (t/241), Witcher Adventure Game house rules (t/1172)): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/112.
- Stats: 1044 total, 770 imported, 264 pending, 10 no_transcript. Archive: 691 transcripts, 770 posts.
- `series_queue.json`: `witawitadd-essays` drained empty → moved to `completed_series` (parts_completed: 1, total_videos: 11, completed_date: 2026-07-31, keeper_post retained). rotation_index stays 0 (removal shifts remaining forward) → next is `drafting-table`. 2 series / 21 videos remain queued: drafting-table (9), hobbycast-2022 (12).
- Skill patch: `import/SKILL.md` register A word budget clarified — the 250–400 target / 500 hard cap now applies to **body prose**, with the Exhibit Catalogue excluded, since catalogue length scales with batch size (16 entries here ≈ 300 words, which alone left almost no room for prose under a total-word cap).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-30 — Loose Pages: Exhibit Completions (5 videos) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days (yesterday's JJ0wEMAa0Qg already imported) → queue drain. `loose-pages-exhibit-completions` at rotation_index 0 (one_shot, vpb=5). All 5 drift-checked pending; full slate fetched cleanly (17,501 → 24,862 chars, 0 failures). Day's transcript total = 5, well under the ~12–15/hr throttle.
- Pre-flight: rate limit OK (1/20 videos posted in 24h), config OK, integrity WARN (79 imported missing local transcripts, issue #2 — non-blocking; dashboard stats unparseable — cosmetic). `fetch_channel_videos` found 0 new videos.
- Posts (chronological by publish date — a grab-bag slate whose only common thread is the exhibits each one completes):
  - https://dungeondive.quest/t/dungeon-degenerats-mean-streets-expansion-and-my-five-favorite-characters/1980 (Dungeon Degenerates *Mean Streets* — plague tokens in the settlements, settlement encounter deck, top-5 characters; 2019-05-31, 208w)
  - https://dungeondive.quest/t/zona-it-ain-t-a-roadside-picnic/1977 (Zona: The Secret of Chernobyl — *Roadside Picnic* lineage, competitive not co-op, emissions-wave timer; 2020-06-10, 214w)
  - https://dungeondive.quest/t/glory-2nd-edition-simplicity-is-thy-name/1981 (Glory 2nd Ed — 7-page rulebook, opt-in combat, rule-breaking ability/goods/fate decks; 2022-11-01, 215w)
  - https://dungeondive.quest/t/forbidden-psalm-using-battlemats-to-suggest-narrative-and-customizing-your-experience/1979 (Forbidden Psalm follow-up — battlemat exits as branching campaign, Solitary Defilement crossover, home-made paper minis; 2023-01-16, 204w)
  - https://dungeondive.quest/t/pirates-of-the-scumribbean-pirate-borg-review-solo-rpg-friday/1978 (Pirate Borg — Spirit as fifth stat, d66 apocalypse table, naval combat, Skeleton Point sandbox; 2023-03-31, 207w)
- Keeper series post ("Loose Pages" — 233w prose / 464w total, series register; Exhibit Catalogue of 9, chronological, integrating all 4 `related_imported_ids` inline with the 5 new with no new/existing distinction: Dungeon Degenerates Traditional Review (t/1373), An overview of Forbidden Psalm (t/1259), Six Runebound Alternatives (t/1345), The Everrain/Sleeping Gods/Pirate Borg (t/1745)): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/111.
- Stats: 1044 total, 759 imported, 275 pending, 10 no_transcript. Archive: 680 transcripts, 759 posts.
- `series_queue.json`: `loose-pages-exhibit-completions` drained empty → moved to `completed_series` (parts_completed: 1, total_videos: 5, completed_date: 2026-07-30, keeper_post retained). rotation_index stays 0 (removal shifts remaining forward) → next is `witawitadd-essays`. 3 series / 32 videos remain queued: witawitadd-essays (11), drafting-table (9), hobbycast-2022 (12).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-30 — Priority drop: Dungeons of Galora (1 video) — ad-hoc, queue untouched
- Decision tree: 1 priority pending in last 14 days (JJ0wEMAa0Qg, "Dungeons of Galora", published 2026-07-29) → ad-hoc priority run. Exited after posting; queue NOT drained or mutated — `loose-pages-exhibit-completions` (1 series / 5 videos) waits one cycle per the priority rule.
- Pre-flight: rate limit OK (0/20 posted in 24h), config OK, integrity WARN (79 imported missing local transcripts, issue #2 — non-blocking). `fetch_channel_videos` picked up 1 new video (JJ0wEMAa0Qg).
- Transcript fetched cleanly (23,898 chars, 0 failures).
- Post: https://dungeondive.quest/t/dungeons-of-galora-a-solo-dungeon-crawl-rpg/1976 (Dungeons of Galora — Gustavo Fileto's Latin-American-folklore solo crawl; scaling test target + fixed-round combat; 2026-07-29, 221w).
- Keeper priority drop ("Fresh Despatch" — 151w / priority register; "From the deeper stacks" cross-ref of 3: Fixing Tedious Combat in Solo RPGs (t/1902, the combat sermon Galora practises), Corrupted Crypts (t/1887, kindred one-author crawl), 2D6 Dungeon (t/1703, last crawl combat that excited him)): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/110.
- Stats: 1044 total, 754 imported, 280 pending, 10 no_transcript. Archive: 675 transcripts, 754 posts.
- `series_queue.json`: untouched (priority run). rotation_index stays 0; `loose-pages-exhibit-completions` remains next in the queue (1 series / 5 videos).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-28 — The Second Shelf: Bookshelf Tours & the Wider Library (12 videos) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days (most recent pending is 2025-01-19) → queue drain. `second-shelf` at rotation_index 0 (one_shot, vpb=12). All 12 drift-checked pending; full slate fetched cleanly (1,689 → 21,292 chars, 0 failures). Day's transcript total = 12, at the low edge of the ~12–15/hr throttle, no transient errors.
- Posts (chronological by publish date — five *Shelf by Shelf* tours interleaved with the channel's literary/art sidelines: literary update → weird-western dive → Fighting Fantasy history → Warhammer illustrated guide → art-RPG zines → 90s cyberpunk):
  - https://dungeondive.quest/t/beyond-the-reading-rainbow-literary-update/1971 (Beyond the Reading Rainbow — Fracassi/Carson/Chiang; 2018-10-18, 183w)
  - https://dungeondive.quest/t/shelf-by-shelf-part-one/1974 (Shelf by Shelf Pt1 — Philip K. Dick, Dunsany, McDermott; 2019-04-22, 176w)
  - https://dungeondive.quest/t/when-the-west-gets-weird/1964 (When the West Gets Weird — western/weird-western fiction, Brimstone-inspired; 2020-07-12, 175w)
  - https://dungeondive.quest/t/shelf-by-shelf-part-two/1963 (Shelf by Shelf Pt2 — Lansdale, Simak, Gene Wolfe; 2020-08-04, 174w)
  - https://dungeondive.quest/t/shelf-by-shelf-part-three/1972 (Shelf by Shelf Pt3 — Michael Cisco, Bradbury, Sturgeon, Akira; 2020-08-09, 157w)
  - https://dungeondive.quest/t/win-a-copy-of-michael-cisco-s-unlanguage/1970 (Unlanguage giveaway — period piece, contest long closed; 2020-08-13, 163w)
  - https://dungeondive.quest/t/shelf-by-shelf-part-four/1965 (Shelf by Shelf Pt4 — Ballard, Blatty, Ligotti; 2020-09-06, 161w)
  - https://dungeondive.quest/t/you-are-the-hero-damn-right-i-am/1969 (YOU Are the Hero — Fighting Fantasy history, artist credits; 2020-11-03, 167w)
  - https://dungeondive.quest/t/the-world-of-warhammer-the-official-illustrated-guide-take-a-look/1968 (World of Warhammer Illustrated Guide — Old World lore, no artist credits; 2020-11-17, 167w)
  - https://dungeondive.quest/t/super-blood-harvest-omnibus-taking-a-look-at-this-wonderfully-illustrated-artistic-rpg-module/1973 (Super Blood Harvest — Dirk w/ a Vengeance art-RPG zines; 2020-12-15, 164w)
  - https://dungeondive.quest/t/shelf-by-shelf-part-five/1967 (Shelf by Shelf Pt5 — Stapledon, Wellman/Silver John, Rucker; 2020-12-19, 152w)
  - https://dungeondive.quest/t/solis-by-a-a-attanasio-quintessential-90s-cyberpunk/1966 (Solis — A.A. Attanasio 90s cyberpunk review; 2021-07-19, 172w)
- Keeper series post ("The Second Shelf" — ~223w prose / series register; Exhibit Catalogue of 15, chronological, integrating 3 `related_imported_ids` inline with the 12 new (no new/existing distinction): House of Danger (t/1763, CYOA on the table), House on Abigail Lane (t/1907, horror novella round-up), ...and the Gunslinger Followed (t/1915, solo western RPG)): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/109.
- Stats: 1043 total, 753 imported, 280 pending, 10 no_transcript. Archive: 674 transcripts, 753 posts.
- `series_queue.json`: `second-shelf` drained empty → moved to `completed_series` (parts_completed: 1, total_videos: 12, completed_date: 2026-07-28, keeper_post retained). rotation_index stays 0 (FIFO — removal shifts remaining forward) → next is `loose-pages-exhibit-completions`. 1 series / 5 videos remain queued: loose-pages-exhibit-completions.
- Note: Discourse threw two 502s (nginx) on the Keeper reply during a forum update; per-video posts had already landed. Reply succeeded on retry once the update finished.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-27 — City of Kings, March 2018: the aborted let's-play saga (7 videos) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days → queue drain. `city-of-kings-2018` at rotation_index 0 (one_shot, vpb=7). All 7 drift-checked pending; full slate fetched cleanly (1,815 → 24,949 chars, 0 failures). Day's transcript total reached 12 — at the low edge of the ~12–15/hr throttle, no transient errors.
- Posts (chronological by publish date — a coherent narrative arc: coverage → aborted playthrough → reset → scenario win → review → 2023 reflection):
  - https://dungeondive.quest/t/city-of-kings-take-a-look/1955 (Take a Look — unboxing/overview, standees-vs-minis soapbox; 2018-03-03, 205w)
  - https://dungeondive.quest/t/aborted-city-of-kings-story-one-chapter-one-lets-play/1954 (ABORTED Story 1 Ch1 — Oakwood; 2018-03-08, 197w)
  - https://dungeondive.quest/t/aborted-city-of-kings-story-one-chapter-2-part-1-lets-play/1960 (ABORTED Story 1 Ch2 pt1 — Orc Hunt, game bares its teeth; 2018-03-10, 193w)
  - https://dungeondive.quest/t/a-message-about-the-city-of-kings-lets-play/1958 (A Message — 2-min mea culpa, playthrough reset; 2018-03-10, 180w)
  - https://dungeondive.quest/t/city-of-kings-desecration-scenario-lets-play-easy-mode/1959 (Desecration Scenario, easy mode — first win; 2018-03-11, 198w)
  - https://dungeondive.quest/t/city-of-kings-review/1957 (Review — admired then sold; theme/mechanism disconnect; 2018-03-13, 207w)
  - https://dungeondive.quest/t/why-i-dont-do-many-if-any-lets-play-videos-and-who-to-watch-instead/1956 (2023 vlog — why he doesn't do let's-plays; retroactive coda; 2023-07-13, 206w)
- Keeper series post ("The Case That Was Never Closed" — ~225w prose / series register; Exhibit Catalogue of 7, chronological; `related_imported_ids` empty): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/108.
- Stats: 1043 total, 741 imported, 292 pending, 10 no_transcript. Archive: 662 transcripts, 741 posts.
- `series_queue.json`: `city-of-kings-2018` drained empty → moved to `completed_series` (parts_completed: 1, total_videos: 7, completed_date: 2026-07-27, keeper_post retained). rotation_index stays 0 (FIFO — remaining entries shift forward) → next is `second-shelf`. 2 series / 17 videos remain queued: second-shelf → loose-pages-exhibit-completions.
- Note: three imports today (1 priority + 4 + 7 = 12 videos posted); analytics from the mid-day /refresh are now stale by 11 imported videos — next /refresh will reconcile.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-27 — Spring 2019: The Miniatures-Adventure Review Season (4 videos) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days → queue drain. `spring-2019-review-season` at rotation_index 0 (one_shot, vpb=4). All 4 drift-checked pending; full slate fetched cleanly (15,854 → 27,678 chars, 0 failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/fireteam-zero-a-weird-war-2-game-review/1950 (Fireteam Zero — ultra-lean Weird War skirmish; 2019-02-27, 193w)
  - https://dungeondive.quest/t/widowers-wood-an-iron-kingdoms-adventure-board-game-review/1952 (Widower's Wood — Iron Kingdoms co-op tactical; 2019-04-09, 193w)
  - https://dungeondive.quest/t/hellboy-the-board-game-the-review-the-video/1951 (Hellboy — Kickstarter-vs-retail gap; 2019-04-30, 195w)
  - https://dungeondive.quest/t/mice-and-mystics-an-overview-review/1953 (Mice and Mystics — Jerry Hawthorne beast epic; 2019-05-29, 196w)
- Keeper series post ("The Spring 2019 Field Season" — ~230w prose / series register; Exhibit Catalogue of 6, chronological, integrating 2 `related_imported_ids` — Silver Tower Pt1 (t/1510, Hewitt-Williams bloodline) + Hellboy 2026 Revisit (t/1921) — inline with the 4 new, no new/existing distinction): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/107.
- Stats: 1043 total, 734 imported, 299 pending, 10 no_transcript. Archive: 655 transcripts, 734 posts.
- `series_queue.json`: `spring-2019-review-season` drained empty → moved to `completed_series` (parts_completed: 1, total_videos: 4, completed_date: 2026-07-27, keeper_post retained). rotation_index stays 0 (FIFO — remaining entries shift forward) → next is `city-of-kings-2018`. 3 series / 24 videos remain queued: city-of-kings-2018 → second-shelf → loose-pages-exhibit-completions.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-27 — Priority drop: When Less is More — Minimalism in Adventure Games (1 video)
- Decision tree: 1 priority pending in last 14 days (`9rJgQmuc2SM`, published 2026-07-26) → ad-hoc priority run. Queue untouched; `spring-2019-review-season` (rotation_index 0) waits one cycle.
- Transcript pulled cleanly (17,502 chars, 0 failures).
- Post: https://dungeondive.quest/t/when-less-is-more-minimalism-in-table-top-adventure-games/1949 (essay on artistic/component/mechanical minimalism — Adventure of D, Seven Moons, Glory 2e, Shadows of Malice, Darkest Night, Dragons Down, Search for the Emperor's Treasure; 2026-07-26, 210w).
- Keeper priority-drop post (~150w alert register; "From the deeper stacks" cross-refs 3 — Search for the Emperor's Treasure (t/1821, the game that inspired the topic), Dragons Down review (t/308, direct game-name overlap), Small Box Thunderdome incl. Adventure of D (t/1681)): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/106.
- Stats: 1043 total, 730 imported, 303 pending, 10 no_transcript. Archive: 651 transcripts, 730 posts.
- `series_queue.json` untouched (priority runs never mutate the queue). 4 series / 28 videos remain queued: spring-2019-review-season → city-of-kings-2018 → second-shelf → loose-pages-exhibit-completions.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-24 — Crates of Ambition: The Big-Box Kickstarter Wave (12 videos) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days → queue drain. `big-box-kickstarter-wave` at rotation_index 0 (one_shot, vpb=12). All 12 drift-checked pending; full slate fetched cleanly (15,705 → 69,753 chars, 0 failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/the-ghosts-betwixt-a-prototype-preview/1941 (Ghosts Betwixt prototype — family crawl; 2019-04-03, 189w)
  - https://dungeondive.quest/t/assault-on-doomrock-an-underrated-gem/1945 (Doomrock 2nd ptg + Doompocalypse; 2020-04-09, 194w)
  - https://dungeondive.quest/t/ghosts-betwixt-unboxing/1944 (Ghosts Betwixt retail unboxing; 2021-12-01, 192w)
  - https://dungeondive.quest/t/lets-take-a-look-at-the-ghosts-betwixt-chapter-1/1940 (Ghosts Betwixt Ch.1 in-depth; 2021-12-28, 194w)
  - https://dungeondive.quest/t/stars-of-akarios-a-casual-unboxing/1946 (Stars of Akarios unboxing; 2022-06-28, 185w)
  - https://dungeondive.quest/t/10-things-i-love-about-stars-of-akarios-a-great-game-thats-not-for-me/1943 (Stars of Akarios impressions; 2022-06-30, 198w)
  - https://dungeondive.quest/t/the-everrain-a-detailed-unboxing-of-the-base-kickstarter-pledge/1938 (The Everrain unboxing; 2023-03-17, 186w)
  - https://dungeondive.quest/t/valor-villainy-lludwigs-labyrinth-detailed-unboxing/1939 (Valor & Villainy unboxing; 2023-05-21, 190w)
  - https://dungeondive.quest/t/assault-on-doomrock-ultimate-edition-a-detailed-casual-unboxing-and-comparison/1937 (Doomrock Ultimate Ed. + comparison; 2024-01-02, 186w)
  - https://dungeondive.quest/t/dead-throne-world-of-veles-a-casual-unboxing/1947 (Dead Throne 2nd ed. unboxing; 2024-02-13, 189w)
  - https://dungeondive.quest/t/ultimate-tanares-adventures-a-casual-and-detailed-unboxing/1936 (Ultimate Tanares unboxing; 2024-06-16, 189w)
  - https://dungeondive.quest/t/forging-the-path-to-arydia-unboxing-organizing-and-the-learning-process/1942 (Arydia prep/unboxing; 2025-01-26, 199w)
- Keeper series post ("Crates of Ambition" — 190w prose / series register; Exhibit Catalogue of 12, chronological; `related_imported_ids` empty): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/105.
- Stats: 1042 total, 729 imported, 303 pending, 10 no_transcript. Archive: 650 transcripts, 729 posts.
- `series_queue.json`: `big-box-kickstarter-wave` drained empty → moved to `completed_series` (parts_completed: 1, total_videos: 12, completed_date: 2026-07-24, keeper_post retained). rotation_index stays 0 (FIFO — remaining entries shift forward) → next is `spring-2019-review-season`. 4 series / 28 videos remain queued.
- SKILL patch: import step 12 no longer instructs dropping `keeper_post` on completed entries — provenance is worth keeping and recent completions already retained it.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-24 — Priority drop: Mini Rogue: Season 2 (1 video)
- Decision tree: 1 priority pending in last 14 days (`4n4yKMederk`, published 2026-07-22) → ad-hoc priority run. Queue untouched; `big-box-kickstarter-wave` (rotation_index 0) waits one cycle.
- Transcript pulled cleanly (28,045 chars, 0 failures).
- Post: https://dungeondive.quest/t/mini-rogue-season-2-expanded-and-better-than-ever/1935 (Mini Rogue: The Council standalone expansion; 2026-07-22, 203w).
- Keeper priority-drop post (~150w alert register; "From the deeper stacks" cross-refs 3 — original Mini Rogue review (t/1714), 2026 Mini Rogue revisit (t/1323, direct game-name overlap), Rolling Deep roguelike (t/1828, genre)): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/104.
- Stats: 1042 total, 717 imported, 315 pending, 10 no_transcript. Archive: 638 transcripts, 717 posts.
- `series_queue.json` untouched (priority runs never mutate the queue). 5 series / 40 videos remain queued: big-box-kickstarter-wave → spring-2019-review-season → city-of-kings-2018 → second-shelf → loose-pages-exhibit-completions.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-22 — The Dungeon Dive Book Club (12 videos) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days → queue drain. `dungeon-dive-book-club` at rotation_index 0 (one_shot, vpb=12 — amended from 10 on 2026-07-21 with two playlist-sourced additions). All 12 drift-checked pending; full slate fetched cleanly (3,097 → 20,340 chars, 0 failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/gateways-to-abomination-by-matthew-m-bartlett-book-review/1928 (Bartlett; 2018-09-27, 204w)
  - https://dungeondive.quest/t/the-exorcist-william-peter-blatty-and-the-trilogy-of-faith/1927 (Blatty Trilogy of Faith; 2019-10-25, 198w)
  - https://dungeondive.quest/t/dungeon-dive-book-club-agents-of-dreamland-by-caitlin-r-kiernan/1934 (club founding announcement; 2020-07-20, 196w)
  - https://dungeondive.quest/t/agents-of-dreamland-by-caitlin-r-kiernan-dungeon-dive-book-club-review/1926 (Kiernan review; 2020-08-18, 208w)
  - https://dungeondive.quest/t/channel-update-and-september-book-club-announcement-the-gods-of-pegana-by-lord-dunsany/1925 (Pegāna announcement + channel-split poll; 2020-08-25, 194w)
  - https://dungeondive.quest/t/gods-of-pegana-by-lord-dunsany-dungeon-dive-book-club-review/1929 (Dunsany review; 2020-09-19, 195w)
  - https://dungeondive.quest/t/the-dark-tower-re-read-read-dungeon-dive-book-club/1931 (Dark Tower re-read announcement; 2020-09-26, 199w)
  - https://dungeondive.quest/t/october-2021-reading-schedule/1924 (Oct 2021 devil-books slate; 2021-09-30, 193w)
  - https://dungeondive.quest/t/the-devil-is-dead-by-r-a-lafferty-book-review/1933 (Lafferty; 2021-10-11, 198w)
  - https://dungeondive.quest/t/the-torturer-by-peter-saxon-book-review/1923 (Saxon; 2021-10-17, 208w)
  - https://dungeondive.quest/t/the-auctioneer-by-joan-samson-book-review/1930 (Samson; 2021-10-30, 200w)
  - https://dungeondive.quest/t/vermis-by-plastiboo-a-book-so-good-i-dont-want-to-finish-it/1932 (Vermis; 2023-05-17, 197w)
- Keeper series post ("The Reading Room" — ~140w prose / series register; integrated Exhibit Catalogue of 16: 12 new + 4 `related_imported_ids` (t/1910, t/1907, t/1797, t/1908), chronological): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/103.
- Stats: 1041 total, 716 imported, 315 pending, 10 no_transcript. Archive: 637 transcripts, 716 posts.
- `series_queue.json`: `dungeon-dive-book-club` drained empty → moved to `completed_series` (parts_completed: 1, total_videos: 12, completed_date: 2026-07-22). rotation_index stays 0 (FIFO — remaining entries shift forward) → next is `big-box-kickstarter-wave`. 5 series / 40 videos remain queued.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-20 — Priority drop: Battletech Alpha Strike + Hellboy revisit (2 videos)
- Decision tree: 2 priority pending in last 14 days (`aVKjY_uB3tA` published 2026-07-15, `NJXuNpJ26us` published 2026-07-19) → ad-hoc priority run. Queue untouched (still empty — `/plan-batch` needed).
- Transcripts: 2/2 pulled cleanly (7,673 and 21,908 chars, 0 failures).
- Posts:
  - https://dungeondive.quest/t/battletech-alpha-strike-with-aces-co-op-solo-rules-overview/1922 (Alpha Strike + Aces co-op/solo AI; 2026-07-15, 211w)
  - https://dungeondive.quest/t/hellboy-the-board-game-2026-revisit/1921 (Hellboy revisit — five loves, eternal #11; 2026-07-19, 202w)
- Keeper priority-drop post (~200w alert register; "From the deeper stacks" cross-refs 3 — Battle Masters (t/1192, explicitly referenced in the Battletech video), Silver Tower Part One (t/1510, same designer as Hellboy), HeroQuest Episode 1 (t/1424)): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/102.
- Stats: 1041 total, 704 imported, 327 pending, 10 no_transcript. Archive: 625 transcripts, 704 posts.
- `series_queue.json` untouched (priority runs never mutate the queue). **Queue remains empty — run `/plan-batch` before the next non-priority import.**
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-13 — Priority drop: Astroprisma (1 video)
- Decision tree: 1 priority pending in last 14 days (`NEahGL5R0HI`, published 2026-07-12) → ad-hoc priority run. Queue untouched (it's empty anyway — still needs `/plan-batch`).
- Transcript pulled cleanly (53,635 chars, 0 failures).
- Post: https://dungeondive.quest/t/astroprisma-one-book-solution-for-great-sci-fi-solo-roleplaying-solo-rpg/1919 (Camilla Mah's one-book sci-fi solo RPG; 2026-07-12, 220w).
- Keeper priority-drop post (~180w alert register; "From the deeper stacks" cross-refs 3 — Space Aces (t/1918), Substratum Protocol (t/1912), Ironsworn: Starforged review (t/1728) — all sci-fi solo RPGs, first two share the Star Dogs referee-handbook pairing): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/101.
- Stats: 1039 total, 702 imported, 327 pending, 10 no_transcript. Archive: 623 transcripts, 702 posts.
- `series_queue.json` untouched (priority runs never mutate the queue). **Queue remains empty — run `/plan-batch` before the next non-priority import.**
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-12 — The 2024–25 Solo RPG Wave (8 videos) — queue drain, series complete, queue now empty
- Decision tree: 0 priority pending in last 14 days → queue drain. `2024-solo-rpg-wave` at rotation_index 0 (one_shot, vpb=8). All 8 video_ids drift-checked pending; full slate fetched in one go.
- Transcripts: 8/8 pulled cleanly (18,426 → 66,322 chars, 0 transient/permanent failures). Note: `batch_fetch_transcripts.py` needs a `--` separator when an ID starts with a dash (`-FJcDEQ2CB0`) — argparse otherwise treats it as a flag and exits 2 without fetching anything.
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/a-solo-rpg-with-an-entire-galaxy-to-explore-space-aces-review-and-gameplay/1918 (Space Aces: Voyages in Infinite Space; 2024-04-07, 203w)
  - https://dungeondive.quest/t/a-superb-solo-rpg-of-paranormal-investigation-the-unseen-world-review-and-gameplay/1911 (The Unseen World; 2024-05-05, 214w)
  - https://dungeondive.quest/t/and-the-gunslinger-followed-we-deal-in-lead-overview-review-game-play-solo-rpg/1915 (We Deal in Lead; 2024-05-26, 214w)
  - https://dungeondive.quest/t/3-solo-rpgs-3-reviews-3-play-sessions-rage-in-hell-the-outcast-and-corny-gron-solo-rpg/1916 (Rage in Hell / The Outcast / Chëdny Groń; 2024-06-12, 214w)
  - https://dungeondive.quest/t/a-land-in-peril-lets-make-a-quest-solo-rpg-design-diary/1913 (A Land in Peril design diary; 2024-07-24, 209w)
  - https://dungeondive.quest/t/roll-and-play-fiction-and-fantasy-solo-rpg-tools/1914 (Roll & Play toolkits; 2024-12-22, 200w)
  - https://dungeondive.quest/t/loom-the-bells-of-basin-city-lore-solo-rpg/1917 (LOOM: Bells of Basin City + lore book; 2024-12-26, 216w)
  - https://dungeondive.quest/t/substratum-protocol-solo-rpg-review/1912 (Substratum Protocol; 2025-01-22, 226w)
- Keeper series post ("The Zine Flood" — ~200w prose / series register; Exhibit Catalogue of 8, chronological; no `related_imported_ids`): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/100.
- Stats: 1038 total, 701 imported, 327 pending, 10 no_transcript. Archive: 622 transcripts, 701 posts.
- `series_queue.json`: `2024-solo-rpg-wave` drained empty → moved to `completed_series` (parts_completed: 1, total_videos: 8, completed_date: 2026-07-12). **`active_series` is now empty; rotation_index reset to 0. Next run needs `/plan-batch` unless a priority video appears.**
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-10 — The Keeper's October: the lost parcel (1 video) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days → queue drain. `keepers-october-horror` at rotation_index 0 with a single remaining ID — `ZA_G9BP9HLY`, the transient `VideoUnplayable` failure from this morning's run. Retry succeeded cleanly (17,189 chars), confirming the failure was genuinely transient; no manual YouTube check needed.
- Post: https://dungeondive.quest/t/five-one-killer-works-of-horror-to-read-in-october-2020/1910 (October 2020 horror reading list — Ligotti, Ducornet, Chambers, Prime Evil, To Sleep Perchance to Dream; 2020-09-27, 210w).
- Keeper series post ("The Lost Parcel" — follows up the morning's October Annex post; 1-entry Exhibit Catalogue): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/99.
- Stats: 1038 total, 693 imported, 335 pending, 10 no_transcript. Archive: 614 transcripts, 693 posts.
- `series_queue.json`: `keepers-october-horror` drained empty → moved to `completed_series` (parts_completed: 2, total_videos: 7, completed_date: 2026-07-10). rotation_index advanced and wrapped to 0 → `2024-solo-rpg-wave` (8 videos) is next. 1 series remains queued.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-10 — The Keeper's October: Horror Films & Reading Lists (6 of 7 videos) — queue drain, partial
- Decision tree: 0 priority pending in last 14 days → queue drain. `keepers-october-horror` at rotation_index 0 (one_shot, vpb=7). All 7 video_ids drift-checked pending; full slate attempted.
- Transcripts: 6/7 pulled cleanly (3,991 → 35,608 chars). **1 transient failure:** `ZA_G9BP9HLY` ("Five (+ one) Killer Works of Horror to Read in October 2020") — `VideoUnplayable` ("This video is not available"), flagged `permanent: false` by the fetcher, so it stays `pending` and remains in the queue for the next cycle. If it fails again next run it may be delisted/region-locked on YouTube's side and worth a manual check.
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/the-house-on-abigail-lane-and-others-horror-novella-round-up-for-october-10-2020/1907 (Burke/Cisco/Barker novella round-up; 2020-10-10, 199w)
  - https://dungeondive.quest/t/horror-reading-list-for-october-2022-poltergeist-we-are-here-to-hurt-each-other-and-more/1908 (October 2022 reading list; 2022-09-30, 200w)
  - https://dungeondive.quest/t/the-ten-greatest-my-favorite-horror-films-of-all-time-imo/1904 (top 10 horror films; 2022-10-07, 190w)
  - https://dungeondive.quest/t/ghost-stories-taoist-monks-hopping-vampires-and-brides-with-white-hair/1906 (Ghost Stories board game review; 2022-10-13, 197w)
  - https://dungeondive.quest/t/horror-themed-video-games-and-board-games-which-works-best-audio-only/1909 (horror in games essay; 2022-10-21, 186w)
  - https://dungeondive.quest/t/the-dungeon-dive-reviews-31-1-horror-movies-watched-october-2022/1905 (31 (+1) October movie reviews; 2022-11-04, 190w)
- Keeper series post (~250w prose / series register; Exhibit Catalogue of 6, chronological; no `related_imported_ids`): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/98.
- Stats: 1038 total, 692 imported, 336 pending, 10 no_transcript. Archive: 613 transcripts, 692 posts.
- `series_queue.json`: 6 IDs drained from `keepers-october-horror`; `ZA_G9BP9HLY` remains its sole video_id, so the series stays active (last_part → 1, last_imported 2026-07-10). rotation_index stays 0. 2 series / 9 videos remain queued: keepers-october-horror (1) → 2024-solo-rpg-wave (8).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-09 — Priority drop: Fixing Tedious Combat in Solo RPGs (1 video)
- Decision tree: 1 priority pending in last 14 days (`roO2HBjdtQw`, published 2026-07-08) → ad-hoc priority run. Queue **not** drained; `keepers-october-horror` (rotation_index 0) waits one cycle.
- Transcript pulled cleanly (0 transient/permanent failures).
- Post: https://dungeondive.quest/t/fixing-tedious-combat-in-solo-rpgs/1902 (solo-RPG combat house-rules discussion; 2026-07-08, 205w).
- Keeper priority-drop post (~150w alert register; "From the deeper stacks" cross-refs 3 — 2D6 Dungeon (t/1703), Scarlet Heroes/Cymbaline (t/1575), A Land in Peril (t/1756) — all directly referenced or thematically tight): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/97.
- Stats: 1038 total, 686 imported, 342 pending, 10 no_transcript. Archive: 607 transcripts, 686 posts.
- `series_queue.json` untouched (priority runs never mutate the queue). 2 series remain queued (15 videos): keepers-october-horror → 2024-solo-rpg-wave.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-07 — Wander: The Cult of Barnacle Bay (5 videos) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days → queue drain. `wander-barnacle-bay` at rotation_index 0 (one_shot, vpb=5). All 5 video_ids drift-checked pending; full slate fetched in one go.
- Transcripts: 5/5 pulled cleanly (12,038 → 22,252 chars, 0 transient/permanent failures). Complete single-game Let's Play; parts run 1 → 2 → 3 → 5 → 7 (Parts 4 & 6 never uploaded — flagged at plan-batch, catalogue renders the gap without comment).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/wander-the-cult-of-barnacle-bay-let-s-play-and-review-part-1/1897 (2019-10-29, 196w)
  - https://dungeondive.quest/t/wander-the-cult-of-barnacle-bay-let-s-play-and-review-part-2/1899 (2019-11-01, 197w)
  - https://dungeondive.quest/t/wander-the-cult-of-barnacle-bay-let-s-play-and-review-part-3/1901 (2019-11-03, 197w)
  - https://dungeondive.quest/t/wander-the-cult-of-barnacle-bay-let-s-play-and-review-part-5/1898 (Part 5 — above-ground swarm, hero downed — 2019-11-12, 188w)
  - https://dungeondive.quest/t/wander-the-cult-of-barnacle-bay-let-s-play-and-review-part-7/1900 (Part 7 finale/boss — 2019-11-18, 178w)
- Keeper series post (~250w prose / series register; Exhibit Catalogue integrates the 1 `related_imported_id` — FOMO/Wander reflection (t/1552) — with the 5 new posts, 6 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/96.
- Stats: 1037 total, 685 imported, 342 pending, 10 no_transcript. Archive: 606 transcripts, 685 posts.
- `series_queue.json`: `wander-barnacle-bay` moved to `completed_series` (parts_completed: 1, total_videos: 5, completed_date: 2026-07-07). Removed from `active_series`; remaining 2 shift forward, rotation_index stays 0 → now `keepers-october-horror`. 2 series / 15 videos remain queued.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-07 — Zombie & Undead Survival (8 videos) — queue drain, series complete
- Decision tree: 0 priority pending in last 14 days → queue drain. `zombie-undead-survival` at rotation_index 0 (first of 4 series queued 2026-07-06), one_shot, vpb=8. All 8 video_ids drift-checked pending; full slate fetched in one go.
- Transcripts: 8/8 pulled cleanly (12,291 → 60,793 chars, 0 transient/permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/zombicide-black-plague-friends-and-foes-and-no-rest-for-the-wicked/1891 (Black Plague expansions overview; 2018-10-23, 193w)
  - https://dungeondive.quest/t/let-s-objectify-some-plastic-featuring-zombicide-invader/1889 (Invader mini/party showcase; 2020-08-10, 185w)
  - https://dungeondive.quest/t/zombicide-invader-review/1888 (Invader review — Daniel's farewell to the franchise; 2020-08-16, 203w)
  - https://dungeondive.quest/t/carnival-zombie-second-edition-a-low-effort-unboxing-a-tower-defense-survival-zombie-game/1893 (Carnival Zombie 2E unboxing; 2022-08-30, 188w)
  - https://dungeondive.quest/t/carnival-zombie-2nd-edition-initial-thoughts-on-the-agonizing-choices/1892 (Carnival Zombie 2E initial thoughts; 2022-09-06, 196w)
  - https://dungeondive.quest/t/pandemonium-a-few-things-i-like-about-this-flawed-horror-survival-game/1895 (Pandemonium — B-movie horror survival; 2022-10-18, 190w)
  - https://dungeondive.quest/t/last-night-on-earth-soloing-the-zombie-apocalypse/1890 (Last Night on Earth solo deep-dive; 2024-10-27, 198w)
  - https://dungeondive.quest/t/last-night-on-earth-the-zombie-game-a-look-at-the-web-exclusive-expansions/1894 (LNoE web expansions; 2024-10-29, 196w)
- Keeper series post (~250w prose / series register; Exhibit Catalogue integrates the 3 `related_imported_ids` — Walking Dead Universe RPG (t/1643), Here's Negan (t/1645), ZomBN1 (t/606) — with the 8 new posts, 11 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/95.
- Stats: 1037 total, 680 imported, 347 pending, 10 no_transcript. Archive: 601 transcripts, 680 posts.
- `series_queue.json`: `zombie-undead-survival` moved to `completed_series` (parts_completed: 1, total_videos: 8, completed_date: 2026-07-07). Removed from `active_series`; the 3 remaining series shift forward, so rotation_index stays 0 → now `wander-barnacle-bay` (preserves queued FIFO order). 3 series / 20 videos remain queued.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-06 — Priority drop: Corrupted Crypts (1 video)
- Decision tree: 1 priority pending in last 14 days (`uNX13pgpGBU`, published 2026-07-05) → ad-hoc priority run. Queue **not** drained; `zombie-undead-survival` (rotation_index 0, first of 4 series queued 2026-07-06) waits one cycle.
- Transcript pulled cleanly (22,800 chars, 0 transient/permanent failures).
- Post: https://dungeondive.quest/t/corrupted-crypts-solo-dungeon-crawl-review/1887 (War Claw Games solo card-crawl by Waclaw Trauer; 2026-07-05, 211w).
- Keeper priority-drop post (~175w alert register; "From the deeper stacks" cross-refs 3 — Doom Pilgrim (t/1758) & Elder Space (t/1183), same designer, + Vanaheim (t/1841), fellow Game Crafter indie crawl): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/94.
- Stats: 1037 total, 672 imported, 355 pending, 10 no_transcript. Archive: 593 transcripts, 672 posts.
- `series_queue.json` untouched (priority runs never mutate the queue). 4 series remain queued (28 videos): zombie-undead-survival → wander-barnacle-bay → keepers-october-horror → 2024-solo-rpg-wave.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-02 — Survival & Wilderness Crawls (7 videos) — queue drain, series complete
- Pre-flight: `fetch_channel_videos.py` hit transient SSL EOF errors (`www.googleapis.com`) on first two attempts; curl confirmed network healthy; succeeded on retry (0 new videos). Noted as intermittent TLS flakiness, not a quota/config issue.
- Decision tree: 0 priority pending in last 14 days → queue drain. `survival-wilderness-crawls` at rotation_index 0 (one_shot, vpb=7). All 7 video_ids drift-checked pending; full slate fetched in one go.
- Transcripts: 7/7 pulled cleanly (266 → 45,843 chars, 0 transient/permanent failures). Note: `iEHsfr9bvpg` (Robinson Crusoe) is a genuine ~15-second teaser clip (56 words) — real transcript, not a failure; posted as an honest 79-word teaser rather than padding to the 150-word floor.
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/spire-s-end-take-a-look/1884 (Spire's End card adventure; 2020-09-23, 191w)
  - https://dungeondive.quest/t/a-look-at-rocky-mountain-man-a-game-of-wilderness-exploration-and-survival/1880 (1800s fur-trapper hex crawl; 2021-11-09, 183w)
  - https://dungeondive.quest/t/a-look-at-unbroken-a-solo-survival-resource-management-dungeon-crawl/1883 (solo survival/revenge, euro-tight; 2022-04-12, 175w)
  - https://dungeondive.quest/t/it-s-finally-time-for-robinson-crusoe/1882 (teaser clip; 2022-09-06, 79w)
  - https://dungeondive.quest/t/a-look-at-spires-end-hildegard/1881 (standalone follow-up, slingshot dice; 2022-11-09, 176w)
  - https://dungeondive.quest/t/broken-shores-aka-godshard-an-exhaustive-look-at-this-brutal-nautical-fantasy-survival-solo-rpg/1879 (drowned-world D100 RPG; 2023-04-21, 184w)
  - https://dungeondive.quest/t/posthuman-saga-humans-vs-mutants-in-a-struggle-for-survival/1878 (competitive post-apoc survival; 2023-12-12, 187w)
- Keeper series post (~250w prose / series register; Exhibit Catalogue integrates the 3 `related_imported_ids` — Fallen Land: Take a Look (t/1595), Critter Crawl: Aftermath (t/1634), Returning to Fallen Land (t/1590) — with the 7 new posts, 10 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/93.
- Stats: 1036 total, 671 imported, 355 pending, 10 no_transcript. Archive: 592 transcripts, 671 posts.
- `series_queue.json`: `survival-wilderness-crawls` moved to `completed_series` (parts_completed: 1, total_videos: 7, completed_date: 2026-07-02). `active_series` now empty; rotation_index reset to 0. **Queue is empty — run `/plan-batch` before the next drain.**
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-07-02 — Priority drop: Star Wars: Outer Rim — Hot Shots (1 video)
- Decision tree: 1 priority pending in last 14 days (`0PBCtb7Va-c`, published 2026-07-01) → ad-hoc priority run. Queue **not** drained; `survival-wilderness-crawls` (rotation_index 0) waits one cycle.
- Transcript pulled cleanly (16,735 chars, 0 transient/permanent failures).
- Post: https://dungeondive.quest/t/star-wars-outer-rim-hotshots-expansion-overview/1877 (fan-made Captain Kiwi expansion overview; ~$150, non-essential, 2026-07-01, 203w).
- Keeper priority-drop post (~180w alert register; "From the deeper stacks" cross-refs 2 Star Wars videos — Mandalorian Adventures: Clan of Two (t/1720), The Mandalorian Adventures review (t/175)): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/92.
- Stats: 1036 total, 664 imported, 362 pending, 10 no_transcript.
- `series_queue.json` untouched (priority runs never mutate the queue).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-30 — Effortless Fun: Cozy Narrative Adventures (6 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `effortless-fun-cozy-adventures` at rotation_index 0 (2nd of the 3 series queued 2026-06-30), one_shot, vpb=6. All 6 video_ids drift-checked pending; full slate fetched in one go.
- All 6 transcripts pulled cleanly (14,786 → 23,910 chars, 0 transient/permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/roll-player-adventures-effortless-fun/1869 (the game that coined "effortless fun"; fail-forward gamebook hybrid, 2022-01-26, 202w)
  - https://dungeondive.quest/t/dice-throne-adventures-a-great-game-that-can-be-hard-to-recommend/1871 (Puzzle-Quest-style thematic Yahtzee; pricey expansion barrier, 2022-06-26, 201w)
  - https://dungeondive.quest/t/lands-of-galzyr-initial-thoughts/1866 (open-world critter-crawl; initial thoughts, 2022-12-07, 194w)
  - https://dungeondive.quest/t/lands-of-galzyr-a-wonder-of-design-and-adventure/1867 (the full review; near-top-10; static-character gripe, 2022-12-14, 193w)
  - https://dungeondive.quest/t/quests-over-coffee-have-coffee-will-quest/1868 (tiny 10-minute Game Crafter quest game; indie humour, 2023-07-20, 183w)
  - https://dungeondive.quest/t/five-nearly-effortlessly-fun-games/1870 (the manifesto top-list: Seven Moons, Escape the Dark Castle, Glory, Bin1, Galzyr, 2025-01-08, 177w)
- Keeper series post (~221w prose / series register; Exhibit Catalogue integrates the 3 `related_imported_ids` — Sleeping Gods, Six Runebound Alternatives, Lands of Galzyr vs Freelancers vs Mansions — with the 6 new posts, 9 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/91.
- Note: run was interrupted after posting/archiving (session exit); Keeper post, dashboard, queue drain, CHANGELOG and commit completed in a follow-up pass.
- Stats: 1035 total, 663 imported, 362 pending, 10 no_transcript.
- `series_queue.json`: `effortless-fun-cozy-adventures` moved to `completed_series` (parts_completed: 1, total_videos: 6, completed_date: 2026-06-30). rotation_index stays 0, now pointing at `survival-wilderness-crawls` (the last queued series).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-30 — RetroLook: Vintage Dungeon & Adventure Classics (8 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `retrolook-vintage-classics` at rotation_index 0 (1st of the 3 series queued 2026-06-30), one_shot, vpb=8. All 8 video_ids drift-checked pending; full slate fetched in one go.
- All 8 transcripts pulled cleanly (10,706 → 32,238 chars, 0 transient/permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/dragon-strike-1993-take-a-look/1860 (TSR's VHS-packed HeroQuest answer; secretly a fine RPG intro, 2019-02-21, 191w)
  - https://dungeondive.quest/t/retrolook-dragonfire-1992/1861 (Heartbreaker's not-good-but-charming HeroQuest clone, 2020-05-09, 203w)
  - https://dungeondive.quest/t/dungeons-dragons-dragon-quest-retrolook/1864 (TSR's art-soaked D&D on-ramp; teaches THAC0, 2020-09-02, 170w)
  - https://dungeondive.quest/t/dark-world-1992-retrolook/1859 (Mattel's stunning toy castle wrapped around a hollow game, 2020-09-15, 179w)
  - https://dungeondive.quest/t/tsrs-the-classic-dungeon-retrolook/1857 (the 1975 ur-dungeon reissued; basic but iconic board, 2020-10-18, 184w)
  - https://dungeondive.quest/t/a-look-at-barbarian-prince-a-stone-cold-classic-of-solo-adventure-gaming/1858 (the free 1981 solo classic; getting lost is half the game, 2022-01-02, 176w)
  - https://dungeondive.quest/t/minion-hunter-a-dark-conspiracy-game-retrolook-w-the-minion-nation-expansion/1862 (1992 GDW Talisman-meets-Arkham co-op; dry, begs a reprint, 2024-06-04, 183w)
  - https://dungeondive.quest/t/the-hobbit-adventure-board-game-1995-retrolook/1863 (ICE Talisman-style Middle-earth race; gorgeous McBride cover, 2024-07-07, 180w)
- Keeper series post (~228w prose / series register; Exhibit Catalogue integrates the 2 `related_imported_ids` — Talisman Casual Let's Play, Advanced HeroQuest — with the 8 new posts, 10 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/90.
- Stats: 1035 total, 657 imported, 368 pending, 10 no_transcript.
- `series_queue.json`: `retrolook-vintage-classics` moved to `completed_series` (parts_completed: 1, total_videos: 8, completed_date: 2026-06-30). rotation_index stays 0, now pointing at `effortless-fun-cozy-adventures`. 2 series remain queued (effortless-fun-cozy-adventures, survival-wilderness-crawls).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-29 — Draw Your Own Dungeon: Map-Making Solo Games (4 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `map-making-solo-games` at rotation_index 0 (4th and last of the series queued 2026-06-26), one_shot, vpb=4. All 4 video_ids drift-checked pending; full slate fetched in one go.
- All 4 transcripts pulled cleanly (10,945 → 24,004 chars, 0 transient/permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/delve-a-map-making-drawing-game/1853 (Anna Blackwell solo map-drawing; dwarven hold, card-driven, 2020-11-28, 199w)
  - https://dungeondive.quest/t/colostle-a-solo-rpg-adventure-take-a-look/1855 (Nick Angel journaling RPG; castle holding oceans, 2021-09-07, 195w)
  - https://dungeondive.quest/t/paper-dungeons-a-dungeon-crawl-themed-roll-and-write-game/1854 (dungeon "scrawler" roll-and-write; 12 dungeons, 2022-04-17, 186w)
  - https://dungeondive.quest/t/unexplored-2-the-wayfarers-legacy-a-video-game-i-recommend-to-fans-of-ttrpgs-and-board-games/1852 (roguelite w/ bag-builder challenges; very tabletop, 2022-07-15, 190w)
- Keeper series post (~206w prose / series register; Exhibit Catalogue integrates the 5 `related_imported_ids` — 2D6 Dungeon, Cartograph, Cartograph Atlas, A Wayfarer's Tale, Fantasy Map Maker — with the 4 new posts, 9 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/89.
- Stats: 1035 total, 649 imported, 376 pending, 10 no_transcript.
- `series_queue.json`: `map-making-solo-games` moved to `completed_series` (parts_completed: 1, total_videos: 4, completed_date: 2026-06-29). **`active_series` now empty, rotation_index 0** — the four series queued by /plan-batch on 2026-06-26 are all drained. Next non-priority /import will skip cleanly; run /plan-batch to queue more.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-29 — Escape the Dark & the Atmospheric Card-Crawl (6 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `escape-the-dark-card-crawl` at rotation_index 0 (3rd of the 4 series queued 2026-06-26), one_shot, vpb=6. All 6 video_ids drift-checked pending; full slate fetched in one go.
- Transcript fetch note: video ID `-GYR8m5pqkI` begins with a hyphen, so argparse treated it as a flag — re-ran `batch_fetch_transcripts.py` with a `--` options terminator. All 6 transcripts then pulled cleanly (14,374 → 23,395 chars, 0 transient/permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/hand-of-fate-ordeals/1849 (deck-builder that feels like an adventure; bind-attacks combat, 2019-01-16, 198w)
  - https://dungeondive.quest/t/escape-the-dark-castle-review/1846 (top-10 group nightcap; black-and-white art + Death Book, 2020-08-05, 192w)
  - https://dungeondive.quest/t/escape-the-dark-sector-review/1848 ("Dark Castle Advanced": ammo/ranged combat; better solo, 2020-09-11, 178w)
  - https://dungeondive.quest/t/revisiting-hand-of-fate-ordeals-a-game-that-should-have-been-a-massive-hit/1847 (Endless = best tabletop roguelike he's played, 2020-11-01, 192w)
  - https://dungeondive.quest/t/escape-the-dark-sector-a-look-at-mission-packs-2-and-3/1851 (Mutant Syndrome + Quantum Rift; Dark Castle crossover idea, 2022-08-14, 186w)
  - https://dungeondive.quest/t/hex-dek-a-hex-map-in-a-deck-of-cards-and-a-stealth-design-diary-for-the-land-in-peril-rpg/1850 (Philip Reed card tools + A Land in Peril RPG design diary, 2023-10-08, 195w)
- Keeper series post (~216w prose / series register; Exhibit Catalogue integrates the 2 `related_imported_ids` — "A Deck of Cards" solo tool, Top 10 Card Decks — with the 6 new posts, 8 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/88.
- Stats: 1035 total, 645 imported, 380 pending, 10 no_transcript.
- `series_queue.json`: `escape-the-dark-card-crawl` moved to `completed_series` (parts_completed: 1, total_videos: 6, completed_date: 2026-06-29). rotation_index stays 0, now pointing at `map-making-solo-games` (the last queued series).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-29 — Priority drop: Recluse (1 video)
- Decision tree: fetch found 1 new video → 1 priority pending in last 14 days (`zXbAf49C9vE`, published 2026-06-28) → ad-hoc priority run. Queue untouched (escape-the-dark-card-crawl still at rotation_index 0).
- Transcript pulled cleanly (16,654 chars, 0 failures). Full 20-video posting headroom (24h window had rolled over since the 2026-06-26 runs).
- Post: https://dungeondive.quest/t/recluse-a-solo-engine-for-mork-borg-solo-rpg/1845 (Maizy Rose's expanded Mörk Borg solo engine; Solitary Defilement grown Ironsworn-deep, 2026-06-28, 200w).
- Keeper priority-drop post (~178w, alert register): one new arrival + "From the deeper stacks" cross-reference (3 archive picks — Solitary Defilement Session Zero, Mörk Manual, Ironsworn: Starforged Pt1): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/87.
- Stats: 1035 total, 639 imported, 386 pending, 10 no_transcript.
- `series_queue.json` unchanged — priority runs never mutate the queue. 2 series still queued (escape-the-dark-card-crawl, map-making-solo-games).
- Note: the 2026-06-27 /import was deferred (rate-limit headroom too low for the 6-video escape-the-dark batch); no work done that run.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-26 — The New Wave: Modern Miniatures Dungeon Crawlers (7 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `modern-minis-crawlers` at rotation_index 0 (2nd of the 4 series queued this session), one_shot, vpb=7. All 7 video_ids drift-checked pending; full slate fetched in one go.
- All 7 transcripts pulled cleanly (16,519 → 35,253 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/middara-take-a-look/1839 (Succubus's 500-page scripted JRPG-on-the-table; take-a-look, not review, 2019-02-14, 191w)
  - https://dungeondive.quest/t/chronicles-of-drunagor-initial-thoughts/1843 (wuxia-flavoured action-cube heroes; scripted-campaign gripes, 2021-05-18, 183w)
  - https://dungeondive.quest/t/dungeons-of-draggmar-amazing-art-and-initial-frustrations/1838 (gorgeous Darkest-Dungeon art, frustrating learning curve, 2022-11-23, 186w)
  - https://dungeondive.quest/t/vanaheim-a-rogue-lite-indie-dungeon-crawl-for-your-table-top/1841 (Game Crafter roguelike with a town-building metagame, 2023-07-09, 178w)
  - https://dungeondive.quest/t/midhalla-a-viking-themed-fantasy-dungeon-crawl-with-low-luck-strategy-kickstarter-preview/1837 (0%-luck keyword combat + tower defense; KS preview, 2023-08-13, 179w)
  - https://dungeondive.quest/t/now-this-is-how-you-do-a-second-edition-rogue-dungeon-2nd-edition-overview-and-comparison/1840 (the community-driven HD remaster; a model 2e, 2024-04-10, 184w)
  - https://dungeondive.quest/t/a-moody-trip-into-the-dark-depths-of-a-dungeon-crypts-of-obscurum-review/1842 (grimy solo gamebook; dice-assignment stat system, 2024-05-01, 187w)
- Keeper series post (~217w prose / series register; Exhibit Catalogue integrates the 3 `related_imported_ids` — Massive Darkness, Swords & Sorcery, Valpiedra — with the 7 new posts, 10 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/86.
- Stats: 1034 total, 638 imported, 386 pending, 10 no_transcript.
- `series_queue.json`: `modern-minis-crawlers` moved to `completed_series` (parts_completed: 1, total_videos: 7, completed_date: 2026-06-26). rotation_index stays 0, now pointing at `escape-the-dark-card-crawl`. 2 series remain queued (escape-the-dark-card-crawl, map-making-solo-games).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-26 — Screen to Tabletop: Video-Game Adaptations (8 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `video-game-adaptations` at rotation_index 0 (first of 4 series queued by /plan-batch this session), one_shot, vpb=8. All 8 video_ids drift-checked pending; full slate fetched in one go.
- All 8 transcripts pulled cleanly (12,958 → 55,486 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/fallout-the-board-game-having-fun-with-a-flawed-game/1834 (FFG Fallout; nails exploration, fumbles the win condition, 2019-06-27, 207w)
  - https://dungeondive.quest/t/fallout-atomic-bonds-cooperative-upgrade-take-a-look/1829 (the co-op upgrade that turned a flawed game great, 2020-09-14, 195w)
  - https://dungeondive.quest/t/bloodborne-speedrun-the-board-game-or-times-up-stop-having-fun/1831 (great trick-weapon combat sabotaged by the timer, 2021-02-02, 185w)
  - https://dungeondive.quest/t/revisiting-bloodborne-the-board-game-this-hunters-dream-is-a-frustrating-one/1833 (the revisit; off to the sale pile, 2022-11-01, 191w)
  - https://dungeondive.quest/t/a-detailed-unboxing-of-skyrim-the-adventure-game/1830 (Modiphius Skyrim unboxing; expensive box, lots of air, 2023-04-09, 186w)
  - https://dungeondive.quest/t/rune-yes-indeed-prepare-engraved-to-roll-dice-dark-souls-on-your-table/1832 (Spencer Campbell solo Souls-like; out-Dark-Souls the official game, 2023-08-29, 196w)
  - https://dungeondive.quest/t/elder-scrolls-v-skyrim-the-adventure-game-the-biggest-but-in-gaming-review/1836 (the full review; flawed, overpriced, loved; best threat-timer he's seen, 2024-01-10, 194w)
  - https://dungeondive.quest/t/heroes-of-cerulea-the-legend-of-zelda-solo-rpg-review/1835 (pixel-perfect Zelda solo RPG; video-game logic, 2024-08-14, 191w)
- Keeper series post (~199w prose / series register; Exhibit Catalogue integrates the 5 `related_imported_ids` — Arkham 3e vs Fallout vs Skyrim, Hellbringer/Diablo, Witcher Adventure Game, Valpiedra, LA-1 — with the 8 new posts, 13 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/85.
- Stats: 1034 total, 631 imported, 393 pending, 10 no_transcript.
- `series_queue.json`: `video-game-adaptations` moved to `completed_series` (parts_completed: 1, total_videos: 8, completed_date: 2026-06-26). rotation_index stays 0, now pointing at `modern-minis-crawlers`. 3 series remain queued (modern-minis-crawlers, escape-the-dark-card-crawl, map-making-solo-games).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-26 — Priority drop: Rolling Deep (1 video)
- Decision tree: 1 new video on fetch → 1 priority pending in last 14 days (`xGMFiacVSrk`, published 2026-06-24) → ad-hoc priority run. Queue untouched (`active_series` remains empty).
- Transcript pulled cleanly (25,627 chars, 0 failures).
- Post: https://dungeondive.quest/t/rolling-deep-solo-dice-building-roguelike-kickstarter-preview/1828 (Bitewing solo dice-building roguelite Kickstarter preview; low-roll engine-building, Cuphead art, 2026-06-24, 205w).
- Keeper priority-drop post (~170w, alert register): one new arrival + "From the deeper stacks" cross-reference (3 archive picks — Sigils of Nightfall, 9D6 Quest, Ball X Pit): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/84.
- Stats: 1034 total, 623 imported, 401 pending, 10 no_transcript.
- `series_queue.json` unchanged — priority runs never mutate the queue. `active_series` still empty; run /plan-batch before the next non-priority /import.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-24 — Pulp Treasure-Hunters & Cursed Tombs (6 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `pulp-treasure-hunters` at rotation_index 0, one_shot, vpb=7. All 7 video_ids drift-checked pending; full slate fetched in one go.
- Transcripts: 6 of 7 pulled cleanly (15,408 → 26,801 chars). 1 permanent failure — `zufjmNpcSlg` (The art of TOMB) TranscriptsDisabled → marked `no_transcript`. 0 transient failures.
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/tomb-overview-and-solo-play-development/1826 (AEG's gorgeous-but-broken party crawler; Daniel's homebrew solo variant, 2020-04-04, 206w)
  - https://dungeondive.quest/t/pulp-invasion-an-ok-game-with-a-great-look/1822 (Todd Sanders bag-builder; vintage Steeger pulp art over a pasted-on theme, 2022-05-04, 210w)
  - https://dungeondive.quest/t/expedition-to-skull-island-pirate-themed-hex-crawling-perfect-for-slow-questing/1825 ($5 itch.io pirate hex-crawl; huge unexplored-hex tables, 2022-05-17, 206w)
  - https://dungeondive.quest/t/curse-of-the-mummys-tomb-games-workshop-the-solo-mode-is-basically-candyland/1824 (1988 GW; Gary Chalk art atop a Candyland solo mode, 2022-10-25, 218w)
  - https://dungeondive.quest/t/a-look-at-treasure-by-torchlight-a-light-and-simple-solo-dungeon-crawler/1823 (Dr. Trash Games crawler; charming but over-produced and overpriced, 2023-08-01, 203w)
  - https://dungeondive.quest/t/search-for-the-emperors-treasure-another-classic-adventure-game-from-tom-wham/1821 (Tom Wham's 1981 Holy Grail; D&D night in a box, 2023-08-15, 210w)
- Keeper series post (~210w prose / series register; Exhibit Catalogue integrates the 5 `related_imported_ids` — Dungeon Degenerates, Relic, Secrets of the Lost Tomb, Tomb Raider CCG, Tomb Raider: Crypt of Chronos — with the 6 new posts, 11 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/83.
- Stats: 1033 total, 622 imported, 401 pending, 10 no_transcript.
- `series_queue.json`: `pulp-treasure-hunters` moved to `completed_series` (parts_completed: 1, total_videos: 6, completed_date: 2026-06-24). `active_series` now **empty**, rotation_index 0 — next non-priority /import will skip cleanly; run /plan-batch to queue more.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-24 — Into the Grimdark: Games Workshop's Sci-Fi Skirmishes (5 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `into-the-grimdark` at rotation_index 0, one_shot, vpb=5. All 5 video_ids drift-checked pending; full slate fetched in one go.
- All 5 transcripts pulled cleanly (15,037 → 24,467 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/core-space-the-sci-fi-miniatures-game-from-battle-systems/1816 (Battle Systems' shape-shifting sci-fi sandbox; his favourite game of 2019, 2019-05-23, 199w)
  - https://dungeondive.quest/t/revisiting-the-blackstone-fortress/1819 (deeper base-campaign dive; Strikeforce two-hero fix from White Dwarf 2019 annual, 2020-03-08, 191w)
  - https://dungeondive.quest/t/core-space-new-expansions-take-a-look/1820 (Shift Change at Mega Core, Rogue Purge, Dangerous Days campaign book, 2020-06-05, 190w)
  - https://dungeondive.quest/t/a-look-at-space-hulk-death-angel-the-card-game/1817 (Konieczka's co-op card-game distillation of Space Hulk; the brutal d6, 2022-05-26, 197w)
  - https://dungeondive.quest/t/space-hulk-is-a-forever-game-review/1818 (the full board game; five reasons it endures, OverWatch + 2½-min timer, 2024-12-08, 190w)
- Keeper series post (~360 words, series register; Exhibit Catalogue integrates the 5 `related_imported_ids` — Blackstone overview + Silver Tower parts 1–4 — with the 5 new posts, 10 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/82.
- Stats: 1033 total, 616 imported, 408 pending, 9 no_transcript.
- `series_queue.json`: `into-the-grimdark` moved to `completed_series` (parts_completed: 1, total_videos: 5, completed_date: 2026-06-24). `active_series` now holds only `pulp-treasure-hunters` (rotation_index 0) — queue still has one series for the next non-priority /import.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-23 — Ker Nethalas & the Solo OSR Dungeon-Delve (5 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `ker-nethalas-solo-osr` at rotation_index 0 (the last queued series), one_shot, vpb=5. All 5 video_ids drift-checked pending; full slate fetched in one go.
- All 5 transcripts pulled cleanly (24,294 → 68,100 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/advanced-dungeon-goons-review-and-session-recap-solo-rpg/1810 (Tunnel-Goons-based rules-light fantasy, soloed with oracle + decks, 2022-11-25, 209w)
  - https://dungeondive.quest/t/random-quest-dungeon-delve-straddling-the-line-between-boxed-card-board-game-and-solo-rpg/1813 (boxed crawl / solo-RPG identity crisis, 2023-08-27, 200w)
  - https://dungeondive.quest/t/wail-solo-adventures-in-a-dream-like-fantasy-world-solo-rpg/1812 (FromSoft-flavoured hex-crawl + journaling, 2023-12-14, 217w)
  - https://dungeondive.quest/t/a-mega-review-of-a-mega-dungeon-crawl-ker-nethalas-into-the-midnight-throne/1811 (the anchor — Blackoath's brutal living mega-dungeon, 2024-05-19, 205w)
  - https://dungeondive.quest/t/knave-2nd-edition-review-from-the-solo-perspective-solo-rpg/1809 (Ben Milton's OSR toolkit; debuts the "solo score", 2024-06-30, 194w)
- Keeper series post (400 words, series register; Exhibit Catalogue integrates the 5 `related_imported_ids` with the 5 new posts — 10 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/81.
- Stats: 1033 total, 611 imported, 413 pending, 9 no_transcript.
- `series_queue.json`: `ker-nethalas-solo-osr` moved to `completed_series` (parts_completed: 1, total_videos: 5, completed_date: 2026-06-23). **`active_series` is now EMPTY (rotation_index 0). Queue exhausted — run /plan-batch before the next non-priority /import (it would otherwise skip cleanly with a "queue empty" note).**
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-22 — Pauper's Ladder — the King-Crimson adventure game (4 videos, 1 no_transcript)
- Decision tree: 0 priority pending in last 14 days (yesterday's Arabian Nights now imported) → queue drain. `paupers-ladder` at rotation_index 0, one_shot, vpb=5. All 5 video_ids drift-checked pending.
- Transcript fetch: 4 succeeded cleanly (26,210 → 45,665 chars); 1 permanent failure — `P6a8zyHf7YY` ("The Art of Paupers' Ladder (with music by Daniel J. Davis)"), TranscriptsDisabled. Wordless music-over-art piece, genuinely no captions → marked `no_transcript` in video_index.json.
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/paupers-ladder-the-king-crimson-and-genesis-of-adventure-games/1806 (intro; prog-rock Talisman/Prophecy-adjacent crawl; provided by creator Paul Stapleton — disclosed in post, 2022-02-16, 195w)
  - https://dungeondive.quest/t/a-look-at-moon-towers-an-expansion-for-paupers-ladder/1808 (Moon Towers expansion unbox + Illustrated Field Guide, 2022-07-03, 207w)
  - https://dungeondive.quest/t/lets-explore-brighthelm-a-few-turns-of-paupers-ladder-with-the-moon-towers-expansion/1805 (casual solo playthrough as Darius Burr, 2022-07-05, 203w)
  - https://dungeondive.quest/t/paupers-ladder-a-perfect-level-of-abundance-a-comprehensive-overview/1807 (comprehensive overview of all modes/expansions, 2023-10-15, 193w)
- Keeper series post (376 words, series register; Exhibit Catalogue integrates the 3 `related_imported_ids` with the 4 new posts — 7 entries chronological. Music-only Art piece omitted as no_transcript): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/80.
- Stats: 1033 total, 606 imported, 418 pending, 9 no_transcript.
- `series_queue.json`: `paupers-ladder` moved to `completed_series` (parts_completed: 1, total_videos: 4, completed_date: 2026-06-22; 4 imported + 1 no_transcript). `active_series` now holds **1** — `ker-nethalas-solo-osr` is the last queued series. **Queue nearly dry — run /plan-batch after the next drain.**
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged); no_transcript count up to 9.

## 2026-06-22 — Priority drop: Tales of the Arabian Nights 40th Anniversary — new solo mode (1 video)
- Decision tree: 1 priority pending in last 14 days (`GME--_-r_lU`, published 2026-06-21) → ad-hoc priority batch. Queue untouched (paupers-ladder still next).
- Channel fetch found 1 new video (total 1033).
- Transcript fetched cleanly (24,167 chars, 0 failures).
- Post: https://dungeondive.quest/t/is-the-new-solo-mode-actually-good-tales-of-the-arabian-nights-40th-anniversary-edition/1804 (enthusiastic — the new dedicated solo mode is the most *complete* way to play; 15 CYOA quests layered on the full game, 2026-06-21, 196w).
- Keeper priority drop (213 words, alert register) with a "From the deeper stacks" cross-reference to two storytelling-game matches: Tales of the Arthurian Knights (t1317, same paragraph-book engine) and Lovecraftesque (t1319): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/79.
- Stats: 1033 total, 602 imported, 423 pending, 8 no_transcript.
- `series_queue.json`: unchanged (priority runs never mutate the queue). Next non-priority `/import` drains `paupers-ladder` at rotation_index 0 (then ker-nethalas-solo-osr).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-19 — Xia: Legends of a Drift System — space-western sandbox playthrough (3 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `xia-drift-system` at rotation_index 0, one_shot, vpb=3. All 3 video_ids drift-checked pending. (Second drain of the day — rate guard had 15-video headroom; this run brings the rolling 24h count to 8.)
- All 3 transcripts pulled cleanly (17,725 → 20,450 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/xia-legends-of-a-drift-system-with-expansions-part-one/1802 (pre-game: table presence, ship backstories, Embers expansion essential, 2020-12-05, 204w)
  - https://dungeondive.quest/t/xia-legends-of-a-drift-system-part-two-the-anxious-first-days-of-a-greenhorn-space-captain/1800 (the dozen roads to fame; NPC AI cards, 2020-12-07, 194w)
  - https://dungeondive.quest/t/xia-legends-of-a-drift-system-part-three-see-you-space-cowboy/1801 (endgame + final thoughts; d20 NPC fame system; Patreon vote noted, 2020-12-10, 204w)
- Keeper series post (331 words, series register; Exhibit Catalogue = 3 new posts + 1 `related_imported_id` (Spacers t36), 4 entries chronological): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/78.
- Stats: 1032 total, 601 imported, 423 pending, 8 no_transcript.
- `series_queue.json`: `xia-drift-system` moved to `completed_series` (parts_completed: 1, total_videos: 3, completed_date: 2026-06-19). `active_series` now holds 2; `paupers-ladder` slid into rotation_index 0, then ker-nethalas-solo-osr.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-19 — The Ran(King) of King — Part 2 of 2 (5 videos; series complete)
- Decision tree: 0 priority pending in last 14 days → queue drain. `ran-king-of-king` at rotation_index 0, one_shot=false, vpb=6, last_part=1, 5 video_ids remaining. Took all 5 (final part); all drift-checked pending.
- All 5 transcripts pulled cleanly (9,756 → 13,271 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date — Parts 7–11):
  - https://dungeondive.quest/t/cycle-of-the-werewolf-the-ran-king-of-king-part-7/1796 (Cycle of the Werewolf — Wrightson-illustrated novella, 2020-10-05, 192w)
  - https://dungeondive.quest/t/the-dark-tower-i-the-gunslinger-the-ran-king-of-king-part-8/1797 (Dark Tower I: The Gunslinger — straight to #1, 2020-10-31, 192w)
  - https://dungeondive.quest/t/it-mild-spoilers-the-ran-king-of-king-part-9/1795 (IT — cosmic dread + the Losers' love, 2020-11-30, 194w)
  - https://dungeondive.quest/t/the-dark-tower-ii-the-drawing-of-the-three-the-ran-king-of-king-part-10-spoilers/1798 (Dark Tower II: Drawing of the Three — new #1, 2021-01-16, 199w)
  - https://dungeondive.quest/t/the-dark-tower-iii-the-waste-lands-the-ran-king-of-king-part-11-spoilers/1799 (Dark Tower III: The Waste Lands, 2021-02-22, 204w)
- Keeper series post (359 words, series register; Exhibit Catalogue = 5 new posts + 1 `related_imported_id` (Top 10 Horror Books t1395), 6 entries chronological. Per multi-part rendering, this Part-2 post covers its own slate + related — it does not re-list Part 1's six): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/77.
- Stats: 1032 total, 598 imported, 426 pending, 8 no_transcript.
- `series_queue.json`: **series COMPLETE.** Final 5 drained → video_ids empty. `ran-king-of-king` moved to `completed_series` (parts_completed: 2, total_videos: 11, completed_date: 2026-06-19). `active_series` now holds 3; `xia-drift-system` slid into rotation_index 0, followed by paupers-ladder, ker-nethalas-solo-osr.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-18 — The Ran(King) of King — Part 1 of 2 (6 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `ran-king-of-king` at rotation_index 0, **one_shot=false, vpb=6** (11 video_ids total). Took first 6; all drift-checked pending.
- All 6 transcripts pulled cleanly (7,848 → 10,424 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date — the channel's original Part 1–6 order):
  - https://dungeondive.quest/t/firestarter-the-ran-king-of-king-part-1/1789 (Firestarter — lower-tier, forgettable, 2020-08-05, 201w)
  - https://dungeondive.quest/t/the-tommyknockers-the-ran-king-of-king-part-2/1791 (The Tommyknockers — unhinged but loved, Under the Dome seed, 2020-08-24, 208w)
  - https://dungeondive.quest/t/desperation-the-ran-king-of-king-part-3/1793 (Desperation — desert firecracker, 2020-09-06, 205w)
  - https://dungeondive.quest/t/needful-things-the-ran-king-of-king-part-4/1794 (Needful Things — greed satire, bloated middle, 2020-09-13, 199w)
  - https://dungeondive.quest/t/skeleton-crew-and-the-mist-the-ran-king-of-king-part-5/1792 (Skeleton Crew + The Mist masterpiece, 2020-09-27, 194w)
  - https://dungeondive.quest/t/pet-sematary-the-ran-king-of-king-part-6/1790 (Pet Sematary — bleakest, best straight horror, 2020-10-05, 205w)
- Keeper series post (359 words, series register; Exhibit Catalogue = 6 new posts + 1 `related_imported_id` (Top 10 Horror Books t1395), 7 entries chronological): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/76.
- Stats: 1032 total, 593 imported, 431 pending, 8 no_transcript.
- `series_queue.json`: **multi-part progress recorded, NOT completed.** Removed the 6 drained IDs; `last_part` 0→1, `last_imported` 2026-06-18, `keeper_post` set. 5 video_ids remain (Parts 7–11). Per SKILL, rotation_index advances only on completion → stays 0, so the next non-priority `/import` drains Part 2 (the final 5).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-18 — Small-Box & Micro Solo Crawls — big adventures, tiny footprints (7 videos)
- Decision tree: 0 priority pending in last 14 days (the A Touch of Evil updated review now imported) → queue drain. `small-box-micro-crawls` at rotation_index 0, one_shot, vpb=7. All 7 video_ids drift-checked pending; full slate fetched in one go.
- All 7 transcripts pulled cleanly (7,739 → 37,680 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/crypt-of-chaos-a-small-box-dungeon-crawl/1788 (Crystal Dagger card-driven dungeon solitaire, 2021-08-15, 204w)
  - https://dungeondive.quest/t/6-x-6-tales-a-micro-overland-crawl-from-jack-d/1785 (free PnP 6x6 overland survival crawl, 2022-05-25, 196w)
  - https://dungeondive.quest/t/the-science-fiction-small-box-game-shoot-out/1782 (4-way SF small-box ranking, Deep Space D-6 wins, 2022-05-29, 190w)
  - https://dungeondive.quest/t/micro-dungeon-crawl-travel-pack-how-many-games-can-i-fit-in-the-one-card-dungeon-box/1787 (5 games in one card-sized box, 2022-09-27, 193w)
  - https://dungeondive.quest/t/one-card-dungeon-expansion-preview-and-more-super-small-crawls/1783 (OCD expansion preview — bosses, classes, treasure die, 2023-03-13, 179w)
  - https://dungeondive.quest/t/squire-for-hire-a-micro-tile-laying-score-chasing-solo-puzzle-game/1784 (15-min loot-bag tile-laying puzzle, 2023-08-24, 197w)
  - https://dungeondive.quest/t/a-small-box-solo-dungeon-crawl-set-in-a-world-of-pestilence-light-in-the-dark-review/1786 (Arona plague-doctor tile-laying crawl, 2024-04-24, 199w)
- Keeper series post (390 words, series register; Exhibit Catalogue integrates the 5 `related_imported_ids` with the 7 new posts — 12 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/75.
  - **Cap note (applied lesson):** with the largest catalogue yet (12 entries), body prose was budgeted tight at ~150w → total 390w, comfortably under the 500 hard cap (vs the 2026-06-15 City of Chaos overshoot to 513w on 11 entries).
- Stats: 1032 total, 587 imported, 437 pending, 8 no_transcript.
- `series_queue.json`: `small-box-micro-crawls` moved to `completed_series` (parts_completed: 1, total_videos: 7, completed_date: 2026-06-18). `active_series` now holds 4; `ran-king-of-king` (2-part) slid into rotation_index 0, followed by xia-drift-system, paupers-ladder, ker-nethalas-solo-osr.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-18 — Priority drop: Why I Love A Touch of Evil (Updated Review 2026) (1 video)
- Decision tree: 1 priority pending in last 14 days (`IM0HdpgIDq8`, published 2026-06-17) → ad-hoc priority batch. Queue untouched.
- Channel fetch found 1 new video (total 1032).
- Transcript fetched cleanly (21,818 chars, 0 failures).
- Post: https://dungeondive.quest/t/why-i-love-a-touch-of-evil-the-supernatural-game-updated-review-2026/1781 (top-10 re-evaluation — five things he loves; femme-fatale werewolf hunt; Goldilocks content, flat showdown, 2026-06-17, 198w).
- Keeper priority drop (217 words, alert register) with a "From the deeper stacks" cross-reference to the archived A Touch of Evil coverage — the 2019 Review (t1691), the 2021 playthrough Part One (t1689), and the 2024 "One thing I love about" (t1644): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/74.
- Stats: 1032 total, 580 imported, 444 pending, 8 no_transcript.
- `series_queue.json`: unchanged (priority runs never mutate the queue). Next non-priority `/import` drains `small-box-micro-crawls` at rotation_index 0 (then ran-king-of-king, xia-drift-system).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-15 — Warhammer Quest: City of Chaos — the complete Let's Play (9 videos)
- Decision tree: 0 priority pending in last 14 days (yesterday's console-ranking now imported) → queue drain. `city-of-chaos` at rotation_index 0, one_shot, vpb=9. All 9 video_ids drift-checked pending; full slate fetched in one go (under the ~12-fetch transcript throttle).
- All 9 transcripts pulled cleanly (10,866 → 26,774 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date; Intro → 7-part Let's Play → Review):
  - https://dungeondive.quest/t/city-of-chaos-introduction/1772 (2018-01-21, 190w)
  - https://dungeondive.quest/t/city-of-chaos-lets-play-part-1/1774 (2018-01-30, 184w)
  - https://dungeondive.quest/t/city-of-chaos-lets-play-part-2/1771 (2018-02-02, 178w)
  - https://dungeondive.quest/t/city-of-chaos-lets-play-part-3/1769 (2018-02-08, 188w)
  - https://dungeondive.quest/t/city-of-chaos-lets-play-part-4/1770 (2018-02-10, 197w)
  - https://dungeondive.quest/t/city-of-chaos-lets-play-part-5/1777 (2018-02-10, 197w)
  - https://dungeondive.quest/t/city-of-chaos-lets-play-part-6/1773 (2018-02-16, 187w)
  - https://dungeondive.quest/t/city-of-chaos-lets-play-part-7/1776 (2018-02-19, 183w)
  - https://dungeondive.quest/t/city-of-chaos-the-review/1775 (2018-02-19, 193w)
- Keeper series post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/73. Exhibit Catalogue integrates the 2 `related_imported_ids` (Warhammer Quest "Take a Look" topics 1436/1437) with the 9 new posts — 11 entries chronological by publish date.
  - **Cap note:** the live reply ran **513 words, 13 over the 500 hard cap** — driven by the record 11-entry integrated catalogue. The committed `keeper-city-of-chaos.md` was trimmed to 487w (under cap); no edit tool to amend the live post, and re-posting would breach one-Keeper-post-per-run. Process takeaway: for large integrated catalogues (>8 entries), budget body prose to ~150w.
- Stats: 1031 total, 579 imported, 444 pending, 8 no_transcript.
- `series_queue.json`: `city-of-chaos` moved to `completed_series` (parts_completed: 1, total_videos: 9, completed_date: 2026-06-15). `active_series` now holds 3 series; `small-box-micro-crawls` slid into rotation_index 0 (followed by ran-king-of-king, xia-drift-system).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-15 — Priority drop: Ranking Every Video Game Console I've Owned (1 video)
- Decision tree: 1 priority pending in last 14 days (`yJTEsQi0G98`, published 2026-06-14) → ad-hoc priority batch. Queue untouched.
- Channel fetch found 1 new video (total 1031).
- Transcript fetched cleanly (42,850 chars, 0 failures).
- Post: https://dungeondive.quest/t/ranking-every-video-game-console-ive-owned/1768 (off-topic personal piece — 20 home consoles ranked Atari→PS5, PlayStation 1 at #1, 2026-06-14, 196w).
- Keeper priority drop (177 words, alert register) with a "From the deeper stacks" cross-reference to topic 1161 ("Video Games? Why? Channel Update" — the genuine thematic companion; Runebound/"souls" title matches were false positives and excluded): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/72.
- Stats: 1031 total, 570 imported, 453 pending, 8 no_transcript.
- `series_queue.json`: unchanged (priority runs never mutate the queue). Next non-priority `/import` drains `city-of-chaos` at rotation_index 0.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-13 — Gamebooks & Choose Your Own Adventure — the solo gamebook dispatches (5 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `gamebooks-cyoa` at rotation_index 0, one_shot, vpb=5. All 5 video_ids drift-checked pending; full slate fetched in one go.
- All 5 transcripts pulled cleanly (11,245 → 31,342 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/choose-your-own-adventure-house-of-danger/1763 (Prospero Hall/Z-Man CYOA adaptation, zero-complexity comfort game, 2020-08-03, 211w)
  - https://dungeondive.quest/t/cages-of-fear-a-gamebook-by-joe-ward/1766 (Escape the Dark Castle poured into a book, d3 room-advance, skeletons, 2022-07-21, 217w)
  - https://dungeondive.quest/t/loom-portent-of-the-vale-part-game-book-part-solo-rpg-part-madlib-with-a-lot-of-atmosphere/1765 (Shield Dice madlib-prose monastery walk, FromSoft vibe; patron disclosure noted in post, 2023-09-05, 195w)
  - https://dungeondive.quest/t/the-citadel-of-bureaucracy-endless-destinies-the-clockwork-city-a-gamebook-double-feature/1767 (Fighting-Fantasy office parody + 52-card-driven combat gamebook, 2024-01-17, 192w)
  - https://dungeondive.quest/t/what-lies-beneath-a-game-book-of-solo-dungeon-diving-dice-decisions-and-death/1764 (Scaffidi/Glover crawl, dice-minigame tests, XP carryover between deaths, 2024-02-18, 196w)
- Keeper series post (352 words, series register with 5-entry Exhibit Catalogue, chronological): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/71.
- Stats: 1030 total, 569 imported, 453 pending, 8 no_transcript.
- `series_queue.json`: `gamebooks-cyoa` moved to `completed_series` (parts_completed: 1, total_videos: 5, completed_date: 2026-06-13). `active_series` now holds 4 series; `city-of-chaos` slid into rotation_index 0 (followed by small-box-micro-crawls, ran-king-of-king, xia-drift-system).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-12 — Solo RPG Tools — oracles, encounter cards, and the toolkit-builder dispatches (5 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `solo-rpg-tools` at rotation_index 0, one_shot, vpb=5. All 5 video_ids drift-checked pending; full slate fetched in one go.
- All 5 transcripts pulled cleanly (9,399 → 58,634 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/untold-encounters-of-the-random-kind-an-invaluable-tool-for-the-solo-gamer/1757 (Loke's 1,000+ encounter book, underrated solo staple, 2022-06-22, 202w)
  - https://dungeondive.quest/t/campaign-creator-a-great-tool-for-solo-rpgs-from-shieldice-studio/1759 (Shieldice deck — quests/interludes/themes campaign skeleton, 2022-09-29, 200w)
  - https://dungeondive.quest/t/doom-pilgrim-random-encounters-of-an-otherworldly-kind/1758 (Warclaw dice-less interactive-fiction deck, weird-fiction prompt-mine, 2023-03-12, 205w)
  - https://dungeondive.quest/t/the-veiled-dungeon-and-the-long-road-rpg-tool-kits-from-loke-battle-mats-solo-rpg/1755 (Loke map+monster toolboxes, premade-meets-sandbox, 2023-08-22, 197w)
  - https://dungeondive.quest/t/my-favorite-tool-for-solo-rpgs-a-deck-of-cards-a-land-in-peril-solo-rpg/1756 (deck-of-cards collection tour + A Land in Peril dev notes, 2024-03-24, 190w)
- Keeper series post (434 words, series register; Exhibit Catalogue integrates the 5 `related_imported_ids` with the 5 new posts, 10 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/70.
- Stats: 1030 total, 564 imported, 458 pending, 8 no_transcript.
- `series_queue.json`: `solo-rpg-tools` moved to `completed_series` (parts_completed: 1, total_videos: 5, completed_date: 2026-06-12). `active_series` now holds 5 series; `gamebooks-cyoa` slid into rotation_index 0, followed by the four newly-queued series (city-of-chaos, small-box-micro-crawls, ran-king-of-king, xia-drift-system).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-11 — Massive Darkness — CMON's untapped crawl + the MD2 reassessment (3 videos)
- Decision tree: 0 priority pending in last 14 days (yesterday's Kryptothera now imported) → queue drain. `massive-darkness` at rotation_index 0, one_shot, vpb=3. All 3 video_ids drift-checked pending; full slate fetched in one go.
- All 3 transcripts pulled cleanly (4,065 → 16,588 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/lets-objectify-some-plastic-featuring-massive-darkness/1752 ("Let's Objectify Some Plastic" series opener — pick the party on sculpts alone, 2020-04-30, 203w)
  - https://dungeondive.quest/t/massive-darkness-review/1753 (a contrarian defence — great loot/monsters, lifeless map, Kickstarter-diluted, 2020-05-02, 210w)
  - https://dungeondive.quest/t/massive-darkness-2-what-am-i-doing-wrong/1754 (MD2 combat plea — melee mobs one-shotting across the board, 2022-04-03, 199w)
- Keeper series post (330 words, series register with 3-entry Exhibit Catalogue, chronological): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/69.
- Stats: 1030 total, 559 imported, 463 pending, 8 no_transcript.
- `series_queue.json`: `massive-darkness` moved to `completed_series` (parts_completed: 1, total_videos: 3, completed_date: 2026-06-11). `active_series` now holds 2 series; `solo-rpg-tools` slid into rotation_index 0.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-11 — Priority drop: Kryptothera - The Cryptid Pursuit (1 video)
- Decision tree: 1 priority pending in last 14 days (`hJ3DwYLFjcY`, published 2026-06-10) → ad-hoc priority batch. Queue untouched.
- Channel fetch found 1 new video (total 1030).
- Transcript fetched cleanly (31,680 chars, 0 failures).
- Post: https://dungeondive.quest/t/kryptothera-the-cryptid-pursuit-overview/1751 (publisher review copy; competitive cryptid-hunting game played two-handed solo, great event deck, ~90 stat-check cryptids, 2026-06-10, 223w).
- Keeper priority drop (144 words, alert register; no "deeper stacks" cross-reference — no genuinely cryptid/monster-hunting-themed video already in the archive, so omitted per quality-over-quantity rule): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/68.
- Stats: 1030 total, 556 imported, 466 pending, 8 no_transcript.
- `series_queue.json`: unchanged (priority runs never mutate the queue). Next non-priority `/import` drains `massive-darkness` at rotation_index 0.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-10 — Kingdom Death: Monster — the Monologues + art-book postscript (4 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `kingdom-death-monologues` at rotation_index 0, one_shot, vpb=4. All 4 video_ids drift-checked pending; full slate fetched in one go.
- All 4 transcripts pulled cleanly (13,190 → 14,011 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/the-monster-monologues-episode-1-kingdom-death-monster-discussion/1750 (modified Hero mode for character-driven survivors, stone-statue painting, 2018-12-06, 203w)
  - https://dungeondive.quest/t/the-monster-monologues-episode-two-paint-and-chat/1749 (paint-along + Kickstarter "all-in" culture broadside, 2018-12-07, 191w)
  - https://dungeondive.quest/t/the-monster-monologues-episode-3-kingdom-death-monster-discussion/1747 (lost-audio reshoot, primer post-mortem, expansion build tour, 2019-01-18, 212w)
  - https://dungeondive.quest/t/fire-on-the-velvet-horizon-take-a-look-at-the-best-monster-manual-ever-written/1748 (Patrick Stuart & Scrap Princess, stat-free weird-fiction bestiary, 2019-03-05, 208w)
- Keeper series post (338 words, series register with 4-entry Exhibit Catalogue, chronological): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/67.
- Stats: 1029 total, 555 imported, 466 pending, 8 no_transcript.
- `series_queue.json`: `kingdom-death-monologues` moved to `completed_series` (parts_completed: 1, total_videos: 4, completed_date: 2026-06-10). `active_series` now holds 3 series; `massive-darkness` slid into rotation_index 0.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-10 — Sleeping Gods — Red Raven's open-world deep dive (4 videos, 1 no_transcript)
- Decision tree: 0 priority pending in last 14 days → queue drain. `sleeping-gods` at rotation_index 0, one_shot, vpb=5. All 5 video_ids drift-checked pending.
- Transcript fetch: 4 succeeded cleanly (20,043 → 22,487 chars); 1 permanent failure — `ub9JNL8EhJ4` ("Sleeping Gods - Visual Introduction - With Music by Daniel J. Davis"), TranscriptsDisabled. It's a wordless music-over-visuals piece with genuinely no captions → marked `no_transcript` in video_index.json.
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/sleeping-gods-traversing-a-sea-of-wonder/1746 (pipe-and-whiskey first verdict — a masterpiece, top-10 of all time, 2021-02-09, 213w)
  - https://dungeondive.quest/t/sleeping-gods-questions-and-answers-and-literature-discussion-no-spoilers/1743 (first Laukat game he loved + nautical-fantasy reading list, 2021-02-12, 214w)
  - https://dungeondive.quest/t/sleeping-gods-the-spoiler-filled-look/1744 (post-campaign teardown, a crewman dies, carryover gripes, 2021-02-14, 205w)
  - https://dungeondive.quest/t/lets-talk-about-the-everrain-and-sleeping-gods-pirate-borg-and-godshard/1745 (The Everrain weighed against Sleeping Gods and sold, 2023-04-19, 215w)
- Keeper series post (360 words, series register with 4-entry Exhibit Catalogue, chronological): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/66.
- Stats: 1029 total, 551 imported, 470 pending, 8 no_transcript.
- `series_queue.json`: `sleeping-gods` moved to `completed_series` (parts_completed: 1, total_videos: 4, completed_date: 2026-06-10); all 5 video_ids resolved (4 imported + 1 no_transcript). `active_series` now holds 4 series; `kingdom-death-monologues` slid into rotation_index 0.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged); no_transcript count up to 8.

## 2026-06-09 — Solo RPG Friday — the 2023 review wave (7 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `solo-rpg-friday-2023` at rotation_index 0, one_shot, vpb=7. All 7 video_ids drift-checked pending; full slate fetched in one go.
- All 7 transcripts pulled cleanly (9,403 → 29,787 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/a-detailed-look-at-sacrifice-from-blackoath-entertainment-solo-rpg/1736 (magicless Berserk/Dark Souls D20, branded survivors, 2023-01-06, 192w)
  - https://dungeondive.quest/t/5-things-about-twelve-years-a-condensed-hex-and-dungeon-crawl-solo-rpg-friday/1742 (tiny zine crawl, 12-year Lich King clock, 2023-02-03, 198w)
  - https://dungeondive.quest/t/wandering-souls-a-solo-rpg-adventure-journaling-game/1741 (journaling preview, rogue-legacy twist, 2023-02-17, 199w)
  - https://dungeondive.quest/t/what-the-heck-is-an-rpg-anyway-solo-rpg-friday/1738 (discussion essay, seven markers of an RPG, 2023-03-03, 203w)
  - https://dungeondive.quest/t/outdoor-encounter-cards-from-phil-reed-tools-for-random-encounters-solo-rpg-friday/1737 (rules-agnostic deck, on-camera island campaign, 2023-04-14, 189w)
  - https://dungeondive.quest/t/broken-cask-society-culinary-adventure-time-solo-rpg/1739 (fantasy Bourdain inn-touring, the Water Wagon, 2023-06-07, 202w)
  - https://dungeondive.quest/t/the-oracle-story-generator-a-tool-for-creating-adventures-and-campaigns-solo-rpg/1740 (Nord Games 5-deck actor/action/subject engine, 2023-10-01, 205w)
- Keeper series post (457 words total, series register; Exhibit Catalogue integrates the 4 `related_imported_ids` with the 7 new posts, 11 entries chronological by publish date): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/65.
- Stats: 1029 total, 547 imported, 475 pending, 7 no_transcript.
- `series_queue.json`: `solo-rpg-friday-2023` moved to `completed_series` (parts_completed: 1, total_videos: 7, completed_date: 2026-06-09). `active_series` now holds 5 series; `sleeping-gods` slid into rotation_index 0.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-08 — Etherfields — the dreams quartet (Nov–Dec 2020) (4 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `etherfields` at rotation_index 0, one_shot, vpb=4. All 4 video_ids drift-checked pending; full quartet fetched in one go.
- All 4 transcripts pulled cleanly (17,066 → 32,247 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/etherfields-part-one-preliminary-thoughts-after-tutorial-mission-minor-spoilers-on-tutorial/1732 (banished board + rewritten rulebook, metafictional tutorial hooks him, 2020-11-18, 202w)
  - https://dungeondive.quest/t/etherfields-part-two-spoilers-component-flip-through-spoilers/1735 (spoiler-heavy component tour, 300+ tiles, hidden cloud deck, 2020-11-19, 205w)
  - https://dungeondive.quest/t/etherfields-part-three-we-are-like-the-dreamer-who-dreams-and-then-lives-inside-the-dream/1733 (the long reverie review — Lynch, Lovecraft, The Caretaker, 2020-11-22, 206w)
  - https://dungeondive.quest/t/etherfields-more-thoughts-spoiler-warnings-given/1734 (six-question Q&A, spoiler-rich defence of the nightly loop, 2020-12-02, 209w)
- Keeper series post (348 words, series register with 4-entry Exhibit Catalogue, chronological): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/64.
- Stats: 1029 total, 540 imported, 482 pending, 7 no_transcript.
- `series_queue.json`: `etherfields` moved to `completed_series` (parts_completed: 1, total_videos: 4, completed_date: 2026-06-08). `active_series` now holds 6 series; `solo-rpg-friday-2023` slid into rotation_index 0.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-08 — Priority drop: Deep Regrets - Solo Review (1 video)
- Decision tree: 1 priority pending in last 14 days (`ppIXkOvS4WI`, published 2026-06-07) → ad-hoc priority batch. Queue untouched.
- Transcript fetched cleanly (26,387 chars, 0 failures).
- Post: https://dungeondive.quest/t/deep-regrets-solo-review/1731 (rare negative review — gorgeous art, flat solo cataloguing with no conflict; hoped-for tabletop *Dredge* that wasn't, 2026-06-07, 212w).
- Keeper priority drop (alert register): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/63.
- Stats: 1029 total, 536 imported, 486 pending, 7 no_transcript.
- `series_queue.json`: unchanged (priority runs never mutate the queue). Next non-priority `/import` drains the series at rotation_index 0.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-05 — Ironsworn: Starforged — Vincent Baker's sci-fi trilogy (3 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `ironsworn-starforged` at rotation_index 0, one_shot, vpb=3. All 3 video_ids drift-checked pending; full trilogy fetched in one go.
- All 3 transcripts pulled cleanly (17,621 → 29,127 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/ironsworn-starforged-part-1-inspiration-and-session-0-solo-rpg/1727 (sci-fi inspirations + Truths-driven session zero with Brother Quint Savoy, 2023-05-05, 207w)
  - https://dungeondive.quest/t/ironsworn-starforged-part-2-session-recap-and-detailed-look-at-the-oracles-solo-rpg/1729 (Astrid Ruiz arc + oracle architecture tour, 2023-05-10, 194w)
  - https://dungeondive.quest/t/ironsworn-starforged-review-when-a-well-made-thing-isnt-for-me-solo-rpg/1728 (the move count breaks the campaign; praise survives, 2023-05-12, 220w)
- Keeper series post (437 words, series register with 3-entry Exhibit Catalogue, chronological): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/62.
  - Word count overshot the 400 target but stayed under the 500 hard cap; the three-part confessional arc justified the extra room.
- Stats: 1028 total, 535 imported, 486 pending, 7 no_transcript.
- `series_queue.json`: `ironsworn-starforged` moved to `completed_series` (parts_completed: 1, total_videos: 3, completed_date: 2026-06-05). `active_series` now holds 7 series; `etherfields` slid into rotation_index 0.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-03 — Priority drop: Mandalorian Adventures: Clan of Two + Star Wars Talk (1 video)
- Decision tree: 1 priority pending in last 14 days (`F5WCr1Md6mk`, published 2026-06-03) → ad-hoc priority batch. Queue untouched.
- Transcript fetched cleanly (42,716 chars, 0 failures).
- Post: https://dungeondive.quest/t/mandalorian-adventures-clan-of-two-expansion-and-star-wars-talk/1720 (Clan of Two expansion + 14-entry live-action Star Wars ranking, 2026-06-03, 211w).
- Keeper priority drop (191 words, alert register): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/61.
  - **New pattern:** Keeper now includes a "From the deeper stacks" section pointing to thematically related videos already in the archive — in this case the 2024 base-game review (topic 175). Pattern to be codified in `import/SKILL.md`.
- Stats: 1028 total, 532 imported, 489 pending, 7 no_transcript.
- `series_queue.json`: unchanged (priority runs never mutate the queue). `active_series` holds 8 queued series totalling ~36 videos (queued in the three `queue:` commits prior to the small-box import); next non-priority `/import` drains `ironsworn-starforged` at rotation_index 0.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-03 — Small-Box Dungeon Crawls (non-Glover) — 2020–2022 boom (8 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `small-box-non-glover` at rotation_index 0, one_shot, vpb=8. All 8 video_ids drift-checked pending; full batch fetched in one go.
- All 8 transcripts pulled cleanly (15,667 → 26,598 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/bag-of-dungeon-the-review/1710 (Gunpowder Studios tile-laying crawl, 2020-03-28, 233w)
  - https://dungeondive.quest/t/a-look-at-rogue-dungeon/1713 (Albert Danish / Chad Minnichia — Game Crafter favourite, 2021-04-11, 221w)
  - https://dungeondive.quest/t/the-dungeon-of-d-a-small-box-dungeon-crawl-done-right/1711 (Jack D — multi-use card economy, 2021-04-24, 222w)
  - https://dungeondive.quest/t/smaller-things-a-look-at-small-games-that-pack-a-lot-of-punch/1715 (shelf-tour of the small-box collection, 2021-05-14, 210w)
  - https://dungeondive.quest/t/taking-a-look-at-mini-rogue-and-expansions-tabletop-rogue-like/1714 (Nuts Publishing — exploding sixes + stance card, 2022-01-23, 231w)
  - https://dungeondive.quest/t/tiny-epic-dungeons-an-abundance-of-icons-decisions-challenge/1716 (Gamelyn — torch + goblin-cap dual timers, 2022-02-21, 223w)
  - https://dungeondive.quest/t/a-look-at-deck-box-dungeons/1712 (app-driven small-box crawl, 2022-04-05, 223w)
  - https://dungeondive.quest/t/which-of-these-four-small-box-games-is-right-for-you/1717 (Iron Helm vs Rogue Dungeon vs Mini Rogue vs Unbroken, five-axis bracket, 2022-04-14, 210w)
- Keeper series post (452 words, series register with 10-entry Exhibit Catalogue — 8 new + 2 related-imported, chronological): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/60.
  - Catalogue spans 2020-03 *Bag of Dungeon* through 2025-04 *Rogue Dungeon: A Rogue's Tale*, with the two Rogue Dungeon follow-ups (2023 designer interview, 2025 expansion review) book-ending the cabinet.
- Stats: 1027 total, 531 imported, 489 pending, 7 no_transcript.
- `series_queue.json`: `small-box-non-glover` moved to `completed_series` (parts_completed: 1, total_videos: 8, completed_date: 2026-06-03). `active_series` now **empty**; rotation_index reset to 0.
- **Next `/import` will skip cleanly — run `/plan-batch` to queue the next series.**
- Setup note: pre-flight integrity check was momentarily denied by a permission policy citing rate-limit (misfire — `check_rate_limit.py` returned exit 0 with 20/20 headroom); succeeded on retry as a solo invocation. Worth flagging if it recurs.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-01 — Solo RPG Toolkit Canon — Solo RPG Friday founding episodes (8 videos)
- Decision tree: 0 priority pending in last 14 days → queue drain. `solo-rpg-toolkit-canon` at rotation_index 0, one_shot, vpb=8. All 8 video_ids drift-checked pending; complete batch fetched in one go.
- All 8 transcripts pulled cleanly (12,612 → 40,137 chars, 0 transient failures, 0 permanent failures).
- Posts (chronological by publish date):
  - https://dungeondive.quest/t/a-look-at-cairn-indie-rpg-along-with-the-escape-the-city-module/1705 (Cairn + Escape the City, 2022-09-08, 217w)
  - https://dungeondive.quest/t/lets-make-a-sandbox-realm-fables-solo-rpg-tools-sandbox/1700 (Realm Fables sandbox build, 2022-09-25, 211w)
  - https://dungeondive.quest/t/5-1-tips-for-starting-a-solo-rpg-solo-rpg-friday/1699 (Solo RPG Friday ep. 1 — six tips, 2022-11-11, 227w)
  - https://dungeondive.quest/t/three-recommendations-for-solo-rpg-systems-combos-1-bonus-recommendation/1704 (Mörk Borg / D100 Dungeon / Scarlet Heroes + Fabled Lands, 2022-12-02, 217w)
  - https://dungeondive.quest/t/2d6-dungeon-for-once-im-excited-about-the-combat-in-a-dungeon-crawler/1703 (Toby Lancaster's shift-and-interrupt combat, 2023-03-24, 211w)
  - https://dungeondive.quest/t/sandbox-generator-a-tool-worth-its-weight-in-gold-review-solo-rpg/1706 (Atelier Clandestine — 19-hex regions, mega-dungeon connectivity, 2023-06-16, 224w)
  - https://dungeondive.quest/t/cartograph-discover-a-land-draw-a-map-have-an-adventure-solo-rpg/1701 (Brandon Lee — map-making as prep for the next game, 2023-08-20, 228w)
  - https://dungeondive.quest/t/dragonbane-rpg-from-the-solo-perspective-overview-review-solo-setup/1702 (Free League box from soloist's chair, 2023-11-19, 234w)
- Keeper series post (498 words, series register with 13-entry Exhibit Catalogue — 8 new + 5 related-imported, chronological): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/59.
  - Catalogue spans 2022-08 beginner's guide through 2025-08 *It's Fun to Go Alone* round-up, framing the eight new entries inside Daniel's three-year solo-coverage arc.
- Stats: 1027 total, 523 imported, 497 pending, 7 no_transcript.
- `series_queue.json`: `solo-rpg-toolkit-canon` moved to `completed_series` (parts_completed: 1, total_videos: 8, completed_date: 2026-06-01). `rotation_index` stays at 0 (list shifted); next drain runs `small-box-non-glover` (8 video_ids + 2 related_imported_ids, vpb: 8).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-06-01 — Priority drop: Tomb Raider + Grimscar (2 videos)
- Decision tree: 2 priority pending videos in last 14 days — `mOqGGh-ot08` *Tomb Raider: The Crypt of Chronos - I LOVE This Game (Review)* (published 2026-05-31) and `gAlQprevPh0` *Grimscar Expanded - Expansions Overview (Solo RPG)* (published 2026-05-27). Ad-hoc priority run; queue untouched.
- Fetch: 2 new videos discovered (1027 total).
- Transcripts pulled cleanly (39,257 + 13,713 chars, 0 transient failures, 0 permanent failures).
- Posts:
  - https://dungeondive.quest/t/grimscar-expanded-expansions-overview-solo-rpg/1697 (203-word summary, backdated to 2026-05-27T16:00:25Z).
  - https://dungeondive.quest/t/tomb-raider-the-crypt-of-chronos-i-love-this-game-review/1698 (206-word summary, backdated to 2026-05-31T16:00:39Z).
- Keeper priority drop (terse alert, 167 words): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/58.
- Stats: 1027 total, 515 imported, 505 pending, 7 no_transcript.
- `series_queue.json` untouched (priority run). Next drain still runs `solo-rpg-toolkit-canon`.
- Setup note: fresh checkout — installed `requests` + `youtube-transcript-api` via `pip3 install --user` (Xcode python3 3.9; pip 21.2.4 doesn't support `--break-system-packages`).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-27 — Priority drop: Alone Against the Zone (1 video)
- Decision tree: 1 priority pending video in last 14 days (`ccZaP6LEaLI` *Alone Against the Zone - Review and Overview*, published 2026-05-24). Ad-hoc priority run; queue untouched.
- Fetch: 1 new video discovered (1025 total).
- Transcript pulled cleanly (28,630 chars, 0 transient failures, 0 permanent failures).
- Post: https://dungeondive.quest/t/alone-against-the-zone-review-and-overview/1695 (226-word summary, backdated to 2026-05-24T16:00:45Z).
- Keeper priority drop (terse alert, ~110 words): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/57.
- Stats: 1025 total, 513 imported, 505 pending, 7 no_transcript.
- `series_queue.json` untouched (priority run). Next drain still runs `solo-rpg-toolkit-canon`.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-23 — A Touch of Evil — a five-year supernatural-game dossier (4 videos)
- Series complete: **A Touch of Evil — a five-year supernatural-game dossier** (one_shot, all 4 IDs imported in a single batch). Total imported: 4.
- Drained queue: the 2019 mid-game *Touch of Evil* review (Banshee session, Hammer-horror framing, "super talisman with theme tightened"), and the Feb 2021 three-part *Coast*-back-in-print run pitting Argot/Maria/Henrik against the Ghost Ship — Reverend Harding's turn-two defection, Argot's *Madness*-possessed lash-out at Henrik, four simultaneous *Order's Influence* cards across the elders, and the final 42-wound icy-waters showdown closing 10 short.
- Catalogue: 5 entries (4 new + 1 related-imported — the May 2024 *One thing I love about...A Touch of Evil* single-mechanism dispatch at topic 1644), chronological by publish date 2019 → 2024.
- Through-line: *the game writes the story, the player connects the dots.* Five years of Flying Frog's signature game returning to Daniel's table — review, full Coast-expanded session arc, and a late-2024 single-mechanism postscript on the town-elder system. Lone complaint after five years: the dice-fishing showdown is the 2% Daniel would redesign in a game that nails the other 98%.
- All 4 transcripts pulled cleanly (0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1024 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/56 (436 words, series register).
- Stats: 1024 total, 512 imported, 505 pending, 7 no_transcript.
- `series_queue.json`: a-touch-of-evil moved to `completed_series` (parts_completed: 1, total_videos: 4, completed_date: 2026-05-23). `rotation_index` stays at 0 (list shifted); next drain runs `solo-rpg-toolkit-canon` (8 video_ids + 5 related_imported_ids, videos_per_batch: 8).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-21 — Priority drop: Wastelandia (1 video)
- Decision tree: 1 priority pending video in last 14 days (`zx1Xu1eI_UM` *Wastelandia: Solo and Co-Op Boss Battler (Review)*, published 2026-05-20). Ad-hoc priority run; queue untouched.
- Fetch: 1 new video discovered (1024 total).
- Transcript pulled cleanly (21,972 chars, 0 failures).
- Posting hit Discourse HTTP 500 twice on first attempt (forum was mid-update). Run was aborted with the post staged. On user-confirmed retry the post went through cleanly: https://dungeondive.quest/t/wastelandia-solo-and-co-op-boss-battler-review/1685 (backdated to 2026-05-20T16:01:45Z).
- Keeper priority drop (terse alert, ~110 words): https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/55.
- Stats: 1024 total, 508 imported, 509 pending, 7 no_transcript. 429 transcripts, 508 posts archived.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-19 — Grey Gnome Games — the Jason Glover catalogue, all of it (11 videos)
- Series complete: **Grey Gnome Games — the Jason Glover catalogue, all of it** (one_shot, all 11 IDs imported in a single batch). Total imported: 11.
- Drained queue: the 2021 *Iron Helm* arrival, the 2021 *Tin Helm* micro-sibling, the 2022 *Iron Chest* big-box expansion, the 2022 *Gate / Gates* tower-defence pair, the 2023 *Zogar's Revenge* tokens-only memory-puzzle, the 2023 *Revisiting Iron Helm* essay that names the design ethos *this-that-or-press-your-luck*, the 2023 *DustRunner* tin-sized Fury-Road racer, the Oct 2023 same-day delivery of *Howling Abyss* + *Cobbled Aisle* (the latter making The Dungeon Dive itself a city location in *Pauper's Ladder*), the Feb 2024 four-way *Small Box Thunderdome*, the Mar 2024 *Gnome Pack #1* Trojan-horse promo bundle, and the May 2024 *Tin Realm* overland sequel.
- Catalogue: 12 entries (11 new + 1 related-imported — the Apr 2023 *Conversation with Jason Glover* interview at topic 276), chronological by publish date 2021 → 2024.
- Through-line: a three-year arc of one designer (Jason Glover) shipping micro-games out of tins, all unified by the *this-that-or-press-your-luck* choice mechanism Daniel finally names mid-arc. Smallest economies, tightest decisions, the cheapest shelf in the archive.
- All 11 transcripts pulled cleanly (0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1023 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/54 (series register).
- Stats: 1023 total, 507 imported, 509 pending, 7 no_transcript.
- `series_queue.json`: grey-gnome-games moved to `completed_series` (parts_completed: 1, total_videos: 11, completed_date: 2026-05-19). `rotation_index` stays at 0 (list shifted); next drain runs `a-touch-of-evil` (4 video_ids + 1 related_imported_id, videos_per_batch: 4).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-18 — Secrets of the Lost Tomb — Daniel's #1 of all time, complete arc (7 videos)
- Series complete: **Secrets of the Lost Tomb — Daniel's #1 of all time, complete arc** (one_shot, all 7 IDs imported in a single batch). Total imported: 7.
- Drained queue: two October 2019 *Monster Stomp* videos (homebrew kill-count mode binning the scenarios entirely; Van Helsing flees on turn one, Joan Deeb finds Amelia Earhart's flight goggles and one-shots a poisonous spider), the four-part Dec 2020 – Jan 2021 *A Masterclass in Abundance* (the considered case for the prosecution and the defence — *Mr Toad's Wild Ride meets Indiana Jones by way of Tsui Hark*, the gold-standard adventure deck, every expansion walked, the five-reasons defence of an all-time Number One), and the Oct 2023 reaction to the incompatible 10th Anniversary Edition Kickstarter (Daniel quietly declines to back it).
- Catalogue: 9 entries (7 new + 2 related-imported — Top-50 part 5 at topic 1584, Hobbycast Postmortem at topic 1588), chronological by publish date 2019 → 2023.
- Through-line: this is the channel's official Number-One Game, the dossier Daniel has been pointing back to for years. The masterclass framing names it explicitly as *over-abundance* — the spiritual opposite of Warhammer Quest: Silver Tower's masterclass-in-efficiency, in the same series. The arc closes on a quiet act of fidelity: when an incompatible reprint arrives in 2023, Daniel passes — *he already has the perfect game.*
- All 7 transcripts pulled cleanly (0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1023 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/53 (499 readable words, series register — at the catalogue-driven upper end given 9 entries).
- Stats: 1023 total, 496 imported, 520 pending, 7 no_transcript.
- `series_queue.json`: secrets-of-the-lost-tomb moved to `completed_series` (parts_completed: 1, total_videos: 7, completed_date: 2026-05-18). `rotation_index` stays at 0 (list shifted); next drain runs `grey-gnome-games` (11 video_ids + 1 related_imported_id, videos_per_batch: 11).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-18 — Priority drop: The Adventurer: Craygor the Cleric (1 video)
- Ad-hoc priority run: fresh upload "The Adventurer: Craygor the Cleric (Solo Hexcrawl Gameplay)" (published 2026-05-17) — second instalment of Daniel's continuing solo-hexcrawl playthrough of *The Adventurer*, with Craygor II (level-one cleric, lineage of Craygors) hunting the relic the first Craygor failed to protect. Win condition: 500 gold = relic found.
- Session beats: flees a hill giant on initiative, explores desecrated god-of-light shrine (aura shield up to 4, tribute left), wins a 2-orc encampment fight and levels up to cleric 2 (gains *prayer* action), enters tomb passage beneath the camp (trap disarmed, 3g + 1 hero point), knifes a sleeping vampire in a forest cemetery. Ends 461g short.
- Transcript pulled cleanly (0 transient failures, 0 permanent failures).
- 1 new video discovered during fetch (1023 total, was 1022).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/52 (149 words, priority-drop register).
- Stats: 1023 total, 489 imported, 527 pending, 7 no_transcript.
- `series_queue.json`: untouched — priority runs never mutate the queue. Queue remains populated (rotation_index 0, 5 active series staged); next non-priority `/import` will drain `secrets-of-the-lost-tomb` first.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-15 — D100 Dungeon — a complete game's arc, series complete (7 videos)
- Series complete: **D100 Dungeon — a complete game's arc, all of it** (one_shot, all 7 IDs imported in a single batch). Total imported: 7.
- Drained queue: two same-day June 2020 first-look videos (a *Let's Talk* introductory hands-on and a same-day *Let's Back Up* supplemental what-you-actually-need explainer) plus the full Nov 2021 World Builder arc — the expansion first-look that builds the Grasslands of Horror and the city of Ever Vamp hex by hex, three session reports following Hindar the Warrior through quest one (forest-of-elves armour fetch + first city brawl that chains into a *Stolen Items* event), quest two (tundra-of-coldness elf fetch + halberd/scythe finds, +5 strength upgrade), back to Ever Vamp for the full settlement-phase checklist (heal/repair/sell/buy/market/train + a plate-mail girdle replacing the stolen belt), and the closing top-twenty review.
- Through-line: Martin Knight's solo paper crawler reframed across sixteen months. June 2020 entry: paper-and-pencil dungeon simulator pitched as a *red-box-on-the-shelf* artefact via the Game Crafter mapping box (entirely optional). Nov 2021 World Builder bolt-on: a hex-crawl overworld with 25-quests-per-page-island, a calendar with aging/fatigue/moon/religious-and-satanic days, action-point economy, and — most importantly — *shared time bookkeeping* where a full rotation of the in-dungeon time track marks one day on the overworld calendar and one pip of fatigue. The four-session arc demonstrates the system rather than reviews it. The final-video verdict: a probable top-twenty game of all time, with bookkeeping reframed as *an adventure diary worth keeping*.
- All 7 transcripts pulled cleanly (0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1022 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/51 (486 words, series register).
- Stats: 1022 total, 488 imported, 527 pending, 7 no_transcript.
- `series_queue.json`: d100-dungeon moved to `completed_series` (parts_completed: 1, total_videos: 7, completed_date: 2026-05-15). `rotation_index` stays at 0 (list shifted); next drain runs `secrets-of-the-lost-tomb` (7 video_ids + 2 related_imported_ids).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-14 — Darklight: Memento Mori — full dossier, series complete (8 videos)
- Series complete: **Darklight: Memento Mori** (one_shot, all 8 IDs imported in a single batch). Total imported: 8. The whole arc — 2018 unboxing through to a 2020 revisit — filed in a single run.
- Drained queue: an April 2018 Take a Look unboxing, the four-part solo Exorcist Let's Play (Parts 1–4 ending in single-shot death to the dread worm's auto-max critical), the April 2018 Review (the *anti-Gloomhaven* verdict, 80% Warhammer Quest + 20% Souls), a February 2019 deep cut on the previously unfilmed Journey and Settlement phases, and a September 2020 Revisiting re-evaluation.
- Through-line: a Kickstarter that announced itself on the box as *inspired by the classics of the '80s and '90s* and then meant it — Warhammer Quest cadence, perma-death from a single bad darkness roll, brutal critical hits, a settlement layer with persistent locations, and an Exploration-Pack environment deck that Daniel argues every crawl should have. By the 2020 revisit the game is effectively dead at the publisher but kept alive by replacement monster/hero cards from designer Mauro Pon and a community house-rule sheet on BGG (tests pass on 5s and 6s, critical hits roll doubled damage dice and keep top half rather than auto-max-ignoring-armour).
- All 8 transcripts pulled cleanly (0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1022 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/50 (459 words, series register).
- Stats: 1022 total, 481 imported, 534 pending, 7 no_transcript.
- `series_queue.json`: darklight-memento-mori moved to `completed_series` (parts_completed: 1, total_videos: 8, completed_date: 2026-05-14). `rotation_index` stays at 0; next drain runs `d100-dungeon` (7 video_ids).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-14 — Priority drop: Ten Things I Look for in a Good Dungeon Crawl (1 video)
- Ad-hoc priority run: fresh upload "Ten Things I Look for in a Good Dungeon Crawl and Adventure Game" (published 2026-05-13) — Daniel's reviewer-calibration primer ahead of his next round of top-10 lists. Ten preferences laid out as taste-signposts, not a scorecard.
- Transcript pulled cleanly (0 transient failures, 0 permanent failures).
- 1 new video discovered during fetch (1022 total, was 1021).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/49 (143 words, priority-drop register).
- Stats: 1022 total, 473 imported, 542 pending, 7 no_transcript.
- `series_queue.json`: untouched — priority runs never mutate the queue. Queue remains populated (rotation_index 0, 7 active series staged from prior `/plan-batch` runs); next non-priority `/import` will drain `darklight-memento-mori` first.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-13 — One thing I love about... — 2024 micro-format experiment, series complete (5 videos)
- Series complete: **One thing I love about... — a 2024 micro-format experiment** (one_shot, all 5 IDs imported in a single batch). Total imported: 5. Queue is now **empty**.
- Drained queue: five short-form Mar–May 2024 *one thing I love about...* videos — Deities & Demigods (1980 AD&D Cthulhu Mythos chapter as historical document), The Walking Dead Universe RPG (d66 random locations table for the mundane-modern shelf), A Touch of Evil (three small square pen-and-ink Hammer-Horror-style game boards), The True OSR (Chapter 5's 40+ d100 random tables — system itself adversarial-by-design, mixed-to-negative on gameplay but unreservedly loved for the tables), and Here's Negan (Negan as AI-controlled NPC chaos engine, plus a hidden reputation race underneath the co-op).
- Through-line: the *form* itself — Daniel set himself the discipline of picking exactly one thing per game and defending only that. Across five disparate titles the answers shape into a pattern (a chapter, a table, a map, a chapter of tables, an AI-controlled NPC). The series is filed not by theme but by *format discipline*. Note: a sixth video in the same format (the Folklore the Affliction *one thing* coda) was already filed with the Folklore dossier earlier in the rotation.
- All 5 transcripts pulled cleanly (0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1021 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/48 (450 words)
- Stats: 1021 total, 472 imported, 542 pending, 7 no_transcript.
- `series_queue.json`: one-thing-i-love moved to `completed_series` (parts_completed: 1, total_videos: 5, completed_date: 2026-05-13). **`active_series` now empty; rotation_index reset to 0.** Run /plan-batch before next non-priority /import.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-12 — Aftermath — Daniel's Wasteland Let's Play, series complete (8 videos)
- Series complete: **Aftermath — Daniel's Wasteland Let's Play** (one_shot, all 8 IDs imported in a single batch). Total imported: 8.
- Drained queue: a 7-part Nov–Dec 2019 Let's Play of Jerry Hawthorne's *Raid on Enjo* mission (Introduction + 5 chapter playthroughs + Finale colony phase) plus the Dec 2019 Critter Crawl review.
- Through-line: Daniel coins the channel term *critter crawl* in volume one and never quite stops using it. The whole run is one campaign mission — *Raid on Enjo* (the dungeon is an old vending machine; the prize is a bag of *onions noodles*) — with a guinea pig (Grumpel) and a mouse (Mesaiya) as heroes. Across the playthrough Daniel surfaces the design highlights one at a time: the encounter-card-references-storybook crosslink (hundreds of narrative moments from a small deck), the four-personal-goal campaign win condition, the Hunt mechanic (enemies follow you between maps), Group Tasks (cards bank across turns toward one collective check), environment rules (heavy objects, low visibility, forced movement), and the colony phase. The final review verdict: *Jerry Hawthorne's best game since Mice and Mystics* — with a sustained rule-book gripe that started in Comanauts (too thin, too dry, no examples, no flavour). One specific in-game complaint: the boss-chapter roach swarm is anticlimactic and house-rule-worthy.
- All 8 transcripts pulled cleanly (0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1021 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/47 (493 words)
- Stats: 1021 total, 467 imported, 547 pending, 7 no_transcript.
- `series_queue.json`: aftermath moved to `completed_series` (parts_completed: 1, total_videos: 8, completed_date: 2026-05-12). rotation_index stays at 0 — next rotation: **one-thing-i-love** (5 videos queued, the last entry in the current active_series).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-11 — Folklore the Affliction — Fall of the Spire, series complete (6 videos)
- Series complete: **Folklore the Affliction — Fall of the Spire** (one_shot, all 6 IDs imported in a single batch). Total imported: 6.
- Drained queue: a 5-part Oct 2020 campaign playthrough of Story One *Into the City* (character selection + 4 chapter recaps + final review), plus an Apr 2024 *One thing I love about...* coda nominating the Adventure Creation Kit toolkit-book.
- Through-line: Daniel's most arresting verdict in the run — Folklore feels to him like *a board-game version of a PlayStation-1-era Japanese RPG* (overworld + small pre-rendered adventure tiles + skirmish-versus-map combat + items + class abilities + fetch-quest rumours). The unique-nostalgia argument earns the game its forgiveness for an enormous bookkeeping load. *Fall of the Spire*'s headline additions surface across the chapters: an **initiative track** (random-then-finesseable position slots with 2-player-scaled bonuses), **charged abilities** on new foes (soft combat timer — three hits triggers a super), **town events** push-your-luck deck, **rumors** deck of side quests Daniel calls one of his favourite features of any dungeon crawl. The 2024 coda completes the *love-letter coda* arc (same shape as Fallen Land): the toolkit-book is the real engine.
- All 6 transcripts pulled cleanly (0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1021 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/46 (461 words)
- Stats: 1021 total, 459 imported, 555 pending, 7 no_transcript.
- `series_queue.json`: folklore-fall-of-the-spire moved to `completed_series` (parts_completed: 1, total_videos: 6, completed_date: 2026-05-11). rotation_index stays at 0 — next rotation: **aftermath** (8 videos queued).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-11 — Machina Arcana — Three Editions of the Lovecraftian Crawler, series complete (4 videos)
- Series complete: **Machina Arcana — Three Editions of the Lovecraftian Crawler** (one_shot, 4 of 5 IDs imported in a single batch). Total imported: 4. 1 ID marked no_transcript.
- Drained queue: a Jan 2020 long-form 2nd-edition review, a Jun 2020 *cure for new-game fatigue* revisit, and Apr 2022 parts 1 and 2 of the 3rd-edition + *To Eternity* expansion deep look. Fifth video (*The Art of Machina Arcana*, hRgIER_2tZg) marked `no_transcript` — captions disabled (TranscriptsDisabled permanent failure); it's a music-and-art piece Daniel composed a score for.
- Through-line: a *rewarding frustration* whose 3rd edition is a *teaching rewrite* rather than a rules rewrite — new guidebook walks the player through opening rounds, manual reorganised, icon clarifications retrofitted via update pack. *To Eternity* expansion replaces roll-to-spawn with timed ticks and flips chapter cards into new map tiles. Andy Lennon's *Codex Eternum* reads as standalone weird fiction. Uri Bilik has named every map tile.
- Drift check: all 5 IDs were pending; 4 transcripts pulled cleanly, 1 permanent failure (TranscriptsDisabled) on hRgIER_2tZg → marked `no_transcript` in video_index.json.
- 0 new videos discovered during fetch (1021 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/45 (467 words)
- Stats: 1021 total, 453 imported, 561 pending, 7 no_transcript.
- `series_queue.json`: machina-arcana moved to `completed_series` (parts_completed: 1, total_videos: 4, completed_date: 2026-05-11). rotation_index stays at 0 — next rotation: **folklore-fall-of-the-spire** (6 videos queued).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged); no_transcript count rises to 7 with hRgIER_2tZg.

## 2026-05-11 — Priority drop: A New Look at Vantage (1 video)
- Ad-hoc priority run — single video published 2026-05-10, queue stays empty (already drained yesterday).
- Imported: **A New Look at Vantage: Was I Wrong?** — Daniel reaffirms his *modern masterpiece* call on Vantage after an economic-victory game won via a non-exploitative path (took over a vacant tailor's shop, made and sold garments, only used three of the 800 location cards). Also flags the Rule Pop app as a significant upgrade over the physical storybooks.
- 1 new video discovered during fetch (1021 total).
- Transcript pulled cleanly (residential IP, 0 transient failures, 0 permanent failures).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/44 (priority-drop register, 126 words)
- Stats: 1021 total, 449 imported, 566 pending, 6 no_transcript.
- `series_queue.json` unchanged — priority videos never touch the queue. Queue remains empty — **run /plan-batch before next non-priority /import**.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-10 — Queue empty — no import (skipped)
- Pre-flight passed; fetch found no new videos; queue empty after dungeon-crusade completion.
- Decision: skip cleanly. No priority videos in last 14 days, no active series to drain.
- Action requested: run /plan-batch to populate the queue before next /import.

## 2026-05-09 — Dungeon Crusade — Avalon Beckons, Part 2 — series complete (5 videos)
- Series complete: **Dungeon Crusade — Avalon Beckons** (parts_completed: 2, total_videos: 11). Final drain of 5 IDs.
- Drained queue tail: an Oct 2021 status update on the Quick Reference Guide and KS reprint, a Nov 2021 dining-table session braided with sword-and-sorcery novels (The Maze of Peril, Engor's Sword Arm), the Jul 2022 Hobbycast Episode 20 long-form interview with Roger Pearce, a Sep 2022 custom-quest design walkthrough, and a Mar 2024 short-form encounter-deck appreciation.
- Through-line for Part 2: the *long tail* arc — once the unboxing is done, what does ongoing engagement look like? The QRG and Evolved Minions variant resolve Daniel's headline criticism (the relearn cost). The Hobbycast unpacks 14 years of design history and Roger's eclectic influences (Dark Tower, Dungeon Quest, Warhammer Quest, HeroQuest, Baldur's Gate, Icewind Dale, Eye of the Beholder, Ultima — plus an unexpected detour into GTA5 wave-mode survival maps). The custom-quest video argues for a community-quest movement and demonstrates the cleanest way to shorten Dungeon Crusade is to *cut* subsystems wholesale (no mining, no tavern tasks, no celebration day, single sitting). The 2024 closer nominates the encounter deck as the gold standard for what separates great dungeon crawls from good ones. Eleven volumes total across two parts.
- All 5 transcripts pulled cleanly (0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1020 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/44
- Stats: 1020 total, 448 imported, 566 pending, 6 no_transcript.
- `series_queue.json`: dungeon-crusade moved to `completed_series` (parts_completed: 2, total_videos: 11, completed_date: 2026-05-09). `active_series` now empty; rotation_index reset to 0. **Queue empty — run /plan-batch before next /import.**
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-08 — Dungeon Crusade — Avalon Beckons, Part 1 (6 videos)
- Drained queue head: the first six videos of Daniel's January 2021 series on **Dungeon Crusade Book One: Genesis of Evil** — a welcome-to-Avalon opener with the Avalon Adventure Board Game appetizer, a storage walkthrough, a two-part spoiler-rich component deep dive, the Tomb of Kaladar small-table setup, and the first review.
- Through-line: Daniel discloses the Roger-Pearce friendship up front and uses it as a discipline rather than a free pass. The series settles on a *layers-of-simple-systems* frame — patrol routes that give the dungeon a life of its own, an upkeep-phase initiative that splinters six heroes into improvised sub-parties, a difficulty dial the player turns rather than the designer, a mining-and-recipe gem loop, and an interactive book of lore in the avalon adventure board game. The standees are the best he has ever held; Dean Spencer's trap art is his personal favourite. The sustained criticism, all the way through to the review, is the 70-page conversational Crusader's Handbook — verbose enough to bury simple rules in paragraphs of voice and probably under-blind-tested (icon mismatches, treasure-chest icons stamped over critical raid arrows, dungeons unlabelled in the rulebook). Hero special abilities also flat from level 1 to 3 (just +1 damage per tier). Verdict: an uphill climb that the four-to-eight-hour epic dungeon crawl underneath fully earns.
- All 6 transcripts pulled cleanly (0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1020 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/43
- Stats: 1020 total, 443 imported, 571 pending, 6 no_transcript.
- `series_queue.json`: dungeon-crusade drained 6 of 11 IDs (last_part: 1, last_imported: 2026-05-08). 5 IDs remain queued for the next drain. rotation_index stays at 0 — series continues.
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-07 — Dungeon Universalis — third leg of the heavyweights triangle, series complete in one drain (7 videos)
- Series complete: **Dungeon Universalis — the third leg of the heavyweights triangle** (one_shot, all 7 IDs imported in a single batch). Total imported: 7.
- Drained queue head: a five-video first-week deep dive in May 2020 (Take a Look Parts 1–3, Boxing it All Up bonus, Creating Characters), the May 2020 defining review, and an August 2022 follow-up on the official upgrade pack.
- Through-line: anachronistic Spanish-designed kitchen-sink dungeon crawl from Oscar Bribián / Ludic Dragon, started life as a fan-made Advanced HeroQuest expansion. Daniel's frame across the run is *toolbox over tightly-tuned design* — twelve hundred pieces of unique art, sixteen schools of magic, two complete bestiaries, an in-box solo app, and a 120-page rulebook that wrote a rule for everything from swimming to turning your ally into a living bomb. The 2022 follow-up confirms Ludic Dragon shipped the rulebook revisions and bestiary cards Daniel asked for in his original review. Verdict in the review: \"a good game that is almost a great game.\"
- All transcripts pulled cleanly (residential IP, 0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1020 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/42
- Stats: 1020 total, 437 imported, 577 pending, 6 no_transcript.
- `series_queue.json`: dungeon-universalis moved to `completed_series` (parts_completed: 1, total_videos: 7, completed_date: 2026-05-07). rotation_index stays at 0 — next rotation: **dungeon-crusade** (11 videos queued, 6+5 split).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-07 — Priority drop: GameMaster's Apprentice — An Oracle for Every Genre (1 video)
- Ad-hoc priority run — single video published 2026-05-06, queue waits one cycle.
- Imported: GameMaster's Apprentice: An Oracle for Every Genre — Daniel compares post-apocalyptic, cyberpunk, weird horror, sci-fi, steampunk and basic decks side-by-side after an $80–90 DriveThruRPG haul; lands on "buy the basic plus one genre" rather than the full set.
- 1 new video discovered during fetch (1020 total).
- Transcript pulled cleanly (residential IP, 0 transient failures).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/41
- Stats: 1020 total, 430 imported, 584 pending, 6 no_transcript.
- `series_queue.json` unchanged — priority videos never touch the queue. Next rotation remains: **dungeon-universalis** (7 videos queued).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-06 — Fallen Land — six-year wasteland chronicle, series complete in one drain (6 videos)
- Series complete: **Fallen Land: Wasteland Chronicles** (one_shot, all 6 IDs imported in a single batch). Total imported: 6.
- Drained queue head: a 2019 take-a-look (the original Arthur's-Toys-flavoured discovery video), a 2023 four-years-on revisit, the 2023 Descendants expansion review, the 2023 second-edition unboxing (with comp copy from the publisher), the 2024 "one thing I love about" documentation appreciation, and the 2024 definitive solo review of 2nd edition + Descendants.
- Through-line: the first run in the channel archive to track a *complete relationship arc* with a single game — find → fixture → permanent shelf slot. Two recurring threads: Daniel's praise for Fallen Dominion's commitment to retail availability after Kickstarter, and his framing of the game's documentation (quick start guide, scenario book, first-player council-of-towns sheet, indexed rulebook) as a gold standard and a signal of designer confidence. Postmortem-noted as one of the games he forgot to enter into the Top 50 comparison engine.
- All transcripts pulled cleanly (residential IP, 0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1019 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/40
- Stats: 1019 total, 429 imported, 584 pending, 6 no_transcript.
- `series_queue.json`: fallen-land moved to `completed_series` (parts_completed: 1, total_videos: 6, completed_date: 2026-05-06). rotation_index stays at 0 — next rotation: **dungeon-universalis** (7 videos queued).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-05 — Top 50 Games of All Time — series complete in one drain (6 videos)
- Series complete: **Top 50 Games of All Time** (one_shot, all 6 IDs imported in a single batch). Total imported: 6.
- Drained queue head: Parts 1–5 of the countdown (March–April 2022) plus the June 2022 Hobbycast Episode 14 postmortem.
- Through-line: Daniel ran 200 games through the Pub Meeple comparison engine in one sitting in March 2022, took the top 50, and rolled them out ten per episode. Two recurring threads across the series — *length* as the genre's chronic flaw, and *verve over polish* as the explicit reason Secrets of the Lost Tomb beats Warhammer Quest at #1. Postmortem flags Tomb as a regret (kept on potential alone), names three forgotten games (Walking Dead: Here's Negan, Hand of Fate: Ordeals, Fallen Land), and delivers four explicit negative reviews — Gloomhaven, Middara, Sword & Sorcery, Mage Knight — landing the case that "balance" is another word for boring.
- Part 5 also doubles as Daniel's full-time business plan: aiming for 1000 patrons at $5/month, plus podcast ads, merch, dungeon-synth albums, solo RPG modules.
- All transcripts pulled cleanly (residential IP, 0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1019 total unchanged).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/39
- Stats: 1019 total, 423 imported, 590 pending, 6 no_transcript.
- `series_queue.json`: top-50-games-of-all-time moved to `completed_series` (parts_completed: 1, total_videos: 6, completed_date: 2026-05-05). rotation_index stays at 0 — next rotation: **fallen-land** (6 videos queued).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-04 — Scarlet Heroes: The Peril of Cymbaline Isle Part II — series complete (4 videos)
- Series complete: **Scarlet Heroes: The Peril of Cymbaline Isle** (Part 2 of 2 — final). Total imported across both parts: 9.
- Drained queue head: Let's Make Some Ruins (Sep 2021), Cymbaline Isle Sessions 4 (wilderness leg) and 5 (Hungry Mother + d20-trade boredom), and the Feb 2022 coda Random Solo RPG Thoughts (Paldren Omtar, *Arcane Artifacts*, weather table, open-Q on offstage rivals).
- Through-line: out of the city, into the wilds — and then a frank in-session craft revelation about rerouting unwinnable encounters through reaction tables, plus an honest mid-fight admission that boss-stand-up combat stalls into pure d20 trades.
- All transcripts pulled cleanly from residential IP — 0 transient failures, 0 permanent failures.
- 0 new videos discovered during fetch (1019 total unchanged from this morning's run).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/38
- Stats: 1019 total, 417 imported, 596 pending, 6 no_transcript.
- `series_queue.json`: scarlet-heroes moved to `completed_series` (parts_completed: 2, total_videos: 9, completed_date: 2026-05-04). rotation_index stays at 0 — next rotation: **top-50-games-of-all-time** (now at index 0, 6 videos queued).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-04 — Scarlet Heroes: The Peril of Cymbaline Isle Part I (5 videos)
- Queue drain: scarlet-heroes Part 1 of 2. First 5 of 9 video IDs imported (Sessions 0–3 + Encounter Building Cards supplement).
- Imported (Aug–Sep 2021): Session 0 (system + character creation), Session 1 (Crooked Violin tavern, Plundered Tribute hook), Session 2 (cult named — Slaves of the Judging Cloud), Session 3 (church brawl, plague-page recovery), and the supplemental Encounter Building Decks review.
- Through-line: warts-and-all chronicle of learning solo RPG play; Daniel scrapped two Session 1 takes before this run, then settled into the principle "set up situations, not plots."
- All transcripts pulled cleanly (residential IP, 0 transient failures, 0 permanent failures).
- 0 new videos discovered during fetch (1019 total unchanged from this morning's priority drop).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/37
- Stats: 1019 total, 413 imported, 600 pending, 6 no_transcript.
- `series_queue.json`: scarlet-heroes drained 5 IDs (last_part=1, 4 IDs remain). rotation_index stays at 0 — next rotation: **scarlet-heroes Part II** (4 videos remaining).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-05-04 — Priority drop: The Adventurer solo hexcrawl review (1 video)
- Ad-hoc priority run — single video published 2026-05-03, queue waits one cycle.
- Imported: The Adventurer: Solo Hexcrawl Review and Game Play — Ken Kennedy's Drifter series, fantasy entry.
- 1 new video discovered during fetch (1019 total).
- Transcript pulled cleanly (residential IP, no transient failures).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/36
- Stats: 1019 total, 408 imported, 605 pending, 6 no_transcript.
- `series_queue.json` untouched — priority run. Next rotation still: scarlet-heroes (index 0, 9 videos queued).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-04-30 — League of Dungeoneers Part II completes the series (5 videos)
- Series complete: **League of Dungeoneers** (Part 2 of 2 — final). Total imported across both parts: 11.
- Drained queue head: customizing for solo RPG (2023), 12-point Review (2023), three-way Showdown vs Crusade & Universalis (2023), Expansion Preview / reprint announcement (2023), False Prophet expansion + acrylic standees + 2nd-edition upgrade kit (2024).
- Through-line: first-printing rulebook errata caught by Daniel's review → designer responds → second-printing fix arrives, big-box expansion in tow.
- All transcripts pulled cleanly from residential IP — 0 transient failures, 0 permanent failures.
- No new videos discovered (1018 total unchanged from this morning's priority drop).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/35
- Stats: 1018 total, 407 imported, 605 pending, 6 no_transcript.
- `series_queue.json`: league-of-dungeoneers moved to `completed_series` (parts_completed: 2, total_videos: 11, completed_date: 2026-04-30). rotation_index stays at 0 — next rotation: **scarlet-heroes** (now at index 0, 9 videos queued).
- Health: 79 imported videos still missing local transcripts (issue #2 — unchanged).

## 2026-04-30 — Rate limit guard now counts videos, not runs
- `check_rate_limit.py` now sums videos posted across the last 24h (default cap: 20) instead of counting runs (was: 2).
- Motivation: a 1-video priority drop and a 12-video archive drain shouldn't burn equal quota. Video count tracks the actual YouTube transcript-API throttle signal.
- Argument renamed `--max-runs` → `--max-videos`. No callers pass it explicitly, so no breakage. `repair_data.py` still invokes with defaults.
- CLAUDE.md updated.

## 2026-04-30 — Priority drop: Jotunnslayer Hordes of Hel + Conan DLC (1 video)
- Ad-hoc priority run — single video published 2026-04-29, queue waits one cycle.
- Imported: Jotunnslayer: Hordes of Hel (Playing as Conan) — survivor-like, sword-and-sorcery, Conan DLC.
- 1 new video discovered during fetch (1018 total).
- Transcript pulled cleanly (residential IP, no transient failures).
- Keeper post: https://dungeondive.quest/t/dungeon-dive-video-archive-update/1170/34
- Stats: 1018 total, 402 imported, 610 pending, 6 no_transcript
- `series_queue.json` untouched — priority run. Next rotation still: league-of-dungeoneers Part II.
- Health: 79 imported videos still missing local transcripts (issue #2).

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
