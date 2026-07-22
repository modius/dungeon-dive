---
name: plan-batch
description: >
  Propose 2-4 candidate batches for the next /import run using taxonomy,
  engagement, and series state. When the user picks, queues the chosen
  slate(s) into series_queue.json for /import (or a scheduled /import) to drain.
  Triggers: "plan batch", "propose batch", "what should we import", "suggest batch", "next batch"
---

Propose candidate batches for the next import cycle and — when the user picks — queue the chosen slate(s) into `series_queue.json` as explicit, ordered video lists. Reads archive state, analytics, and engagement data; writes only to `series_queue.json`; never imports.

## Inputs (read-only)

- `video_index.json` — pending videos with title, published_at, status
- `series_queue.json` — active_series, rotation_index, completed_series (written to only after user selection)
- `transcript_analytics.json` — per-video taxonomy (games, formats, mechanics, themes, modes)
- `youtube_stats.json` — view_count, like_count, comment_count per video
- `keeper-posts/` — prior themes to avoid re-covering
- `docs/insights.html` — most recent insights suggestions (optional signal)
- **Channel playlists** (YouTube Data API, live) — Daniel's own curation; see *Playlist signal* below

If `transcript_analytics.json` or `youtube_stats.json` is stale (>24h), suggest the user run `/refresh` first.

## Playlist signal

The channel maintains ~85 public playlists — the creator's own editorial taxonomy. Fetch them fresh during every proposal pass (cheap: `playlists.list` + a few `playlistItems.list` calls, ~1 quota unit each; no cache file needed):

1. `GET youtube/v3/playlists?part=snippet,contentDetails&channelId=UCKW6yMwL_aEu83g6DdjVfxw&maxResults=50` (paginate).
2. For playlists relevant to a forming candidate, fetch membership via `playlistItems.list` (part=`snippet,contentDetails`).
3. **Filter to owner:** playlists can contain other creators' videos (e.g. the *Myth 2* playlist is entirely Keith Lowe's uploads). Drop any item whose `videoOwnerChannelTitle` isn't The Dungeon Dive / whose ID isn't in `video_index.json`.

Use membership three ways:

- **Slate authority.** When a candidate theme matches a playlist, prefer the playlist's membership over title matching — it catches typo'd titles ("Dungeon Degenerats") and videos that never name the game ("Zona" in *Runebound Alternatives*).
- **Straggler sweeps** (candidate type 7). Diff each playlist against `video_index.json` status: a playlist that is ≥80% imported with 1–3 pending remainders is an exhibit-completion opportunity. Bundle stragglers across playlists into a single small batch when individually too few.
- **Uncovered territories.** Playlists with substantial pending membership and no completed theme (music/culture: *Dungeon Synth*, *vaporwave*, *Radio dramas*; formats: *Digital Dive*, *Vanishing Point*, *Shelf by Shelf*) are ready-made candidate themes.

Also consult playlist membership during the related-imported survey — co-membership in a curated playlist is a strong cross-reference signal, often stronger than shared taxonomy tags.

## Propose — what to surface

Always include (if applicable):

1. **Priority batch** — any pending video published in the last 14 days. Shown first when present.
2. **Active queue head** — if `series_queue.active_series` is non-empty, show the series at `rotation_index` so the user knows what's already queued.

Then add 1–2 creative options from:

3. **Untapped topic** — a game with high cross-reference count but low dedicated coverage (ratio ≥5:1). Pull pending videos that mention it.
4. **Thematic cluster** — pending videos sharing a game tag (5–10 videos), especially ones that form a coherent sub-theme.
5. **High-performer format cluster** — pending videos in a format that historically averages high views (deep-dive, top-list, tutorial).
6. **Era dive** — pending videos from a specific year + game-family combination.
7. **Playlist-derived cluster** — a straggler sweep or uncovered territory surfaced by the *Playlist signal* pass above.

Cap candidates at **4**. Minimum **2**.

## Candidate format

```
### [N]. Theme Title — N videos

**Hook:** One line — why this batch makes a compelling Keeper post.

**Rationale:** What data supports this (series state, view averages, untapped ratio, era coherence).

**Risk / notes:** One line — overlap with prior keeper posts, narrow pool, etc.

**Videos to import:**
- 2019-12-07 — A Failing of the Cthulhu Mythos Board Games (wxWz6zDC2wo)
- …

**Related already-imported (suggested cross-references):**
- 2021-04-02 — A Conversation with Jason Glover (9hgzA60ZGZg) — the designer behind the catalogue
- …
```

End with: *"Which batch(es) should I queue? Reply with numbers (e.g. '1' or '1,3') or say 'none'. To edit a candidate's related-imported list, say so."*

## Related-imported survey — the editorial cross-reference pass

Each Keeper post publishes an *Exhibit Catalogue* that is an integrated thematic index of the subject — not just the videos imported in this batch, but every video in the channel that belongs in this exhibit. The catalogue draws from two pools: the videos *just imported* by this run, plus any *already-imported* videos that are tightly bound to the same subject. The editorial pick of which already-imported videos to fold into the exhibit belongs to `/plan-batch` — `/import` does not curate; it just renders what the queue tells it to (in chronological order by publish date).

For each candidate batch, scan the imported pool (`video_index.json` entries with `status: "imported"`, cross-referenced with `transcript_analytics.json` tags) for videos that share game tags, designer references, or theme tags with the batch. Surface up to 5 strong matches under **Related already-imported** for the user to verify or edit. Strict-match rules (the same standards used for batch composition apply): a related video must reference the batch's subject *directly* — designer-tagged, game-tagged, or thematically tight. Don't pad. If a candidate has no clean related-imported matches, omit the section.

When the user picks a candidate they can also direct edits to the related list ("add X, drop Y, the rest are fine"). Default: queue the suggested list as-is unless overridden.

Note for the user-facing proposal: the *Related already-imported* section in each candidate is informational only — at render time the related-imported entries and the just-imported entries become a single chronologically-ordered Exhibit Catalogue in the Keeper post. The reader sees one coherent thematic tour.

## Queue — what to write when user picks

When the user selects one or more candidates, append each to `series_queue.active_series` as:

```json
{
  "theme": "slug-form-of-title",
  "title": "Theme Title exactly as shown",
  "status": "continuing",
  "one_shot": true,
  "videos_per_batch": 8,
  "video_ids": ["vid1", "vid2", ...],
  "related_imported_ids": ["existing_vid1", ...],
  "last_part": 0,
  "last_imported": null,
  "keeper_post": null
}
```

Rules for queue writes:

- `video_ids`: the exact list of video IDs from the candidate, in the order presented.
- `videos_per_batch`: default to `len(video_ids)` for a one-shot. If the user's candidate has >8 videos, ask whether to split (e.g. "9 videos — one batch or split into 5+4?"). Clamp to 3–12.
- `one_shot`: `true` when `len(video_ids) <= videos_per_batch`, else `false`.
- `status: "continuing"` for multi-part; `one_shot` flag carries the rest of the intent.
- `related_imported_ids`: the editorial cross-references the user confirmed. Each ID must exist in `video_index.json` with `status: "imported"` *and* a non-null `discourse_topic_id` (so `/import` can build a valid Discourse link). Cap at 5. The IDs themselves are unordered — `/import` renders the integrated Exhibit Catalogue in chronological order by publish date. Omit the field or use `[]` when there are no clean matches.
- `last_part: 0`, `last_imported: null`, `keeper_post: null` — `/import` populates these as it drains.
- Theme slug: lowercase, hyphenated, no spaces; if it collides with a `completed_series` theme, suffix with `-pt2` (or next available part number).

If multiple candidates are queued in one turn, append them in the order the user listed. Do not touch `rotation_index` unless `active_series` was empty before — in that case, set it to 0.

After writing, confirm to the user:

```
Queued N series in active_series:
  [rotation_index] theme-slug — N videos (one-shot | N parts of M)
  ...
Next /import will pull from: <theme of active_series[rotation_index]>.
```

## Rules

- Proposal is read-only. **Only** `series_queue.json` is written, and only after the user explicitly picks.
- Never call `fetch_channel_videos.py`, `batch_fetch_transcripts.py`, or any other mutating script.
- Respect the 12-video-per-batch cap when proposing and queueing.
- Skip themes already covered in `keeper-posts/` unless the user explicitly frames a continuation.
- If no good options exist, say so honestly — don't pad.
- If the user wants to enqueue a batch that isn't one of the proposed candidates (ad-hoc list of video IDs), do it — validate each ID exists and has `status: pending`, then queue as above.
