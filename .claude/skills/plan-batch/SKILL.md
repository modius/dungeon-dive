---
name: plan-batch
description: >
  Propose 2-4 candidate batches for the next /import run using taxonomy,
  engagement, and series state. Proposal-only — does not import.
  Triggers: "plan batch", "propose batch", "what should we import", "suggest batch", "next batch"
---

Propose candidate batches for the next import cycle. This skill is decision-support: it reads the archive state, analytics, and engagement data, and surfaces 2–4 batch options for the user to choose between. It does **not** run any import steps.

## Inputs (read-only)

- `video_index.json` — pending videos with title, published_at, status
- `series_queue.json` — active_series, rotation_index, completed_series
- `transcript_analytics.json` — per-video taxonomy (games, formats, mechanics, themes, modes)
- `youtube_stats.json` — view_count, like_count, comment_count per video
- `keeper-posts/` — prior themes to avoid re-covering
- `docs/insights.html` — most recent insights suggestions (optional signal)

If `transcript_analytics.json` or `youtube_stats.json` is stale (>24h), suggest the user run `/refresh` first.

## What to propose

Always surface (if applicable):

1. **Priority batch** — any pending video published in the last 14 days. If present, this is always shown first.
2. **Series continuation** — if `series_queue.active_series` is non-empty, the series at `rotation_index` is always shown.

Then add 1–2 creative options from these sources:

3. **Untapped topic** — a game with high cross-reference count but low dedicated coverage (ratio ≥5:1). Pull pending videos that mention it in title or taxonomy.
4. **Thematic cluster** — pending videos sharing a game tag (5–10 videos), especially ones that form a coherent sub-theme (e.g. "all 2019 Cthulhu titles", "post-apocalyptic wave").
5. **High-performer format cluster** — pending videos in a format that averages high views (deep-dive, top-list, tutorial). Biased toward formats that historically outperform.
6. **Era dive** — pending videos from a specific year + game-family combination, for historical-archive value.

Cap total candidates at **4**. Minimum **2**.

## Batch candidate format

Present each candidate as:

```
### [N]. Theme Title — N videos

**Hook:** One line explaining why this batch would make a compelling Keeper post.

**Rationale:** What data supports this. Cite: series state, view averages, untapped ratio, era coherence, etc.

**Risk / notes:** One line on anything to watch — overlap with prior keeper posts, no series_queue entry yet, small pool, etc.

**Videos:**
- 2019-12-07 — A Failing of the Cthulhu Mythos Board Games (wxWz6zDC2wo)
- 2021-08-25 — Mansions of Madness 2nd Edition (tiDCtcHjdQU)
- …
```

After all candidates, end with a single line prompt: *"Which batch should /import pull?"* Do not proceed.

## Rules

- Proposal-only. Never call `fetch_channel_videos.py`, `batch_fetch_transcripts.py`, or any other mutating script.
- Respect the 12-video batch cap when proposing.
- Skip themes already covered in `keeper-posts/` unless explicitly framing as a continuation.
- If no good options exist, say so honestly — don't pad.
- For priority batches (recent videos), include the candidate even if it doesn't fit a theme; it can be bundled with another option.
- If a series is ≥14 days since last_imported, flag it as **overdue** in the rationale.
- Prefer 5–10 videos per candidate. Never propose batches over 12.
