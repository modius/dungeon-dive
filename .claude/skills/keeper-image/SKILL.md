---
name: keeper-image
description: >
  Compose a set of Midjourney prompts to illustrate a Keeper post. Each
  prompt depicts a character (or scene) from the Dungeon Dive video archive
  in a consistent cel-shaded cartoon house style, with The Keeper — a
  mystical owl archivist of the void between the shelves — present in
  the composition.
  Triggers: "keeper image", "image prompt", "midjourney prompt", "art prompt",
  "draw a character", "illustrate the keeper post", "make a prompt"
---

Generate a small set of Midjourney v8 prompts to illustrate a Keeper post.
Each run produces 3–5 prompt variants of the same subject in different moods,
all in a unified cartoon house style with The Keeper always present.

## Canon — who The Keeper is

The Keeper is a **mystical owl**. He is the archivist of the Dungeon Dive
video archive, working in the *void between the shelves*. The owl and the
archivist are not separate beings — they are the same character. He is
**never** drawn as a hooded human figure, never as a librarian-with-an-owl-
pet, never anthropomorphic. He is an owl: wise-looking, slightly otherworldly,
with archivist trappings (a quill in his talons, a tiny pair of spectacles,
a ledger or index card nearby, faint runic glow, drifting parchment) when
the scene wants to foreground his vocation.

## When to use

- The user asks for an image/Midjourney/art prompt
- After an `/import` run, to produce cover art for the just-posted Keeper update
- The user names a specific video, character, hero, or theme to illustrate

## Inputs (read-only)

- `archive/transcripts/<video_id>_transcript.txt` — primary source for visual
  character details (gear, race, class, scenes, specific named items)
- `archive/posts/<video_id>_post.json` — the per-video framing and voice
- `keeper-posts/keeper-<theme>.md` — the atmospheric framing the image should sit alongside
- `series_queue.json` `completed_series` / `active_series` — to locate the
  recent or current theme if the user didn't name one

## Process

1. **Identify the subject.** The user may name it directly ("draw Hindar",
   "make a prompt for the HeroQuest barbarian"). If not, default to the most
   recently posted Keeper theme (read the latest `keeper-posts/keeper-*.md`).
   Confirm with the user if more than one plausible subject exists.

2. **Pull visual material from the transcripts.** Open the relevant
   `archive/transcripts/*.txt` files and extract:
   - Race, class, gender (if stated), approximate age (if stated)
   - Named gear: weapons, armour, helms, cloaks, belts, jewellery, potions
   - Named locations and the run's distinctive scenes (the snake pit, the
     city brawl, the dread-worm room, etc.)
   - Specific in-fiction names (the character's name, their home settlement,
     the quest-giver, the antagonist)

   Use these details verbatim where possible. **Do not invent gear or scenes
   that are not in the transcript.**

3. **Compose 3–5 variants** covering distinct moods. Skip any mood that the
   source doesn't support; always at least 3, never more than 5:
   - **Heroic portrait** — default poster shot, environment-rich
   - **Mid-action** — a specific scene from a session
   - **Aftermath / character moment** — quieter, character-driven
   - **Comedic** — when the source material supports it (e.g. a doomed rookie)
   - **Paper-life framing** — the subject standing on a hand-drawn hex map
     or inside an open ledger; this is the variant where The Keeper is
     foregrounded in his archivist register (quill in talons, perched on the
     ledger, drifting index cards, hints of the void between shelves)

## House style (locked — do not deviate without the user asking)

Every prompt MUST include:

- **Style language** (verbatim, near the end of the prompt):
  *"Modern cel-shaded cartoon illustration, bold clean linework, flat
  saturated colour with subtle gradient shading, expressive character design"*

  Vary only the mood adjective at the start of the style clause when it
  fits the variant (e.g. *"Dynamic cel-shaded cartoon illustration..."* for
  action, *"Melancholy cel-shaded cartoon illustration..."* for aftermath).

- **The Keeper** (the owl) must appear in every prompt. Two registers:
  - **Witness register (default)** — *"A small wise-looking owl perched
    [somewhere context-appropriate], watching [the subject / the viewer]"*.
    Place him on a natural perch (sword cross-guard, rafter, signpost,
    branch, the rim of an inkwell, etc.) — don't have him floating mid-air.
    He's a recurring observer in the corner of most compositions.
  - **Archivist register (paper-life variant)** — foreground the Keeper as
    archivist. He is still an owl, never a hooded human figure. Optional
    archivist trappings: a quill held in his talons, a tiny pair of round
    spectacles, perched directly on an open ledger, drifting index cards
    around him, a faint runic glow, hints of vast dark shelves receding
    into mist (the *void between the shelves*). Choose 1–3 of these — don't
    pile them all on.

- **Parameters** at the very end:
  - `--ar 16:9 --v 8` — **default**, cinematic wide framing that sits well
    above a forum post
  - `--ar 2:3 --v 8` for tight character portraits when the user asks
  - `--ar 3:2 --v 8` for moderate landscape scenes when the user asks
  - Always `--v 8`. Never omit the version. Never use `--v 6`, `--v 7`, or
    `--style raw`.

  Default to `--ar 16:9` for every variant unless the user has specifically
  asked for a portrait/poster shape. Compose the scene to fill the wide frame
  (more environment, side-of-frame Keeper-owl placement, etc.) rather than
  cramming a portrait-shaped subject into it.

## Output format

A one-line intro naming the subject and what the variants offer, then each
variant in this shape:

```
**N. <Variant name> — <one-line description>**

​```
<full prompt ending with --ar X:Y --v 8>
​```
```

Return prompts inline for the user to paste into Midjourney. Do **not** save
them to disk — they're ephemeral by design. Only the skill's own
`example.md` is persisted, and only as a reference for house style.

## Worked example

See `example.md` (next to this file) for a canonical reference set — Hindar
of Ever Vamp + Baranof the Unfortunate from the D100 Dungeon series, five
variants across the two heroes. It exists to anchor the house style; the
skill does **not** persist new prompt sets to disk unless the user asks.

## Rules

- Always `--v 8`. Always cel-shaded cartoon. Always include The Keeper (the owl).
- The Keeper is **never** drawn as a human or hooded archivist figure. He is
  always an owl. In archivist-register scenes he carries the trappings of an
  archivist (quill, ledger, spectacles, drifting cards) but remains an owl.
- Use transcript details verbatim; don't fabricate gear or scenes.
- Don't depict Daniel as the character. Daniel is the host; the subjects are
  the in-fiction characters (named heroes, NPCs, antagonists) or the games'
  iconic figures. Depict Daniel only if the user explicitly asks for "Daniel"
  or "the host".
- One subject per run. If the user wants two heroes from the same series
  illustrated, run the skill twice (or split the variant set 3+2 across both).
- Don't over-specify — Midjourney prompts work best when descriptive but not
  cluttered. ~60–90 words of scene description plus the style clause and
  Keeper presence is the sweet spot.
