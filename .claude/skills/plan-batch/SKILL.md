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

If `transcript_analytics.json` or `youtube_stats.json` is stale (>24h), suggest the user run `/refresh` first.

## Propose — what to surface

Always include (if applicable):

1. **Priority batch** — any pending video published in the last 14 days. Shown first when present.
2. **Active queue head** — if `series_queue.active_series` is non-empty, show the series at `rotation_index` so the user knows what's already queued.

Then add 1–2 creative options from:

3. **Untapped topic** — a game with high cross-reference count but low dedicated coverage (ratio ≥5:1). Pull pending videos that mention it.
4. **Thematic cluster** — pending videos sharing a game tag (5–10 videos), especially ones that form a coherent sub-theme.
5. **High-performer format cluster** — pending videos in a format that historically averages high views (deep-dive, top-list, tutorial).
6. **Era dive** — pending videos from a specific year + game-family combination.

Cap candidates at **4**. Minimum **2**.

## Candidate format

```
### [N]. Theme Title — N videos

**Hook:** One line — why this batch makes a compelling Keeper post.

**Rationale:** What data supports this (series state, view averages, untapped ratio, era coherence).

**Risk / notes:** One line — overlap with prior keeper posts, narrow pool, etc.

**Videos:**
- 2019-12-07 — A Failing of the Cthulhu Mythos Board Games (wxWz6zDC2wo)
- …
```

End with: *"Which batch(es) should I queue? Reply with numbers (e.g. '1' or '1,3') or say 'none'."*

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
