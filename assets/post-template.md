# Discourse Post Template

Use this template when creating Discourse topics for imported videos.

## Template Structure

```markdown
https://www.youtube.com/watch?v={{VIDEO_ID}}

---

{{SUMMARY}}

---

*This video was originally published on {{PUBLISH_DATE}}.*
```

## Placeholders

- `{{VIDEO_ID}}`: YouTube video ID (for embed)
- `{{SUMMARY}}`: AI-generated promotional summary from transcript
- `{{PUBLISH_DATE}}`: Human-readable publish date (e.g., "15 June 2024")

## Summary Guidelines

When generating the summary from the transcript:

1. **Length**: 2-4 paragraphs, approximately 150-250 words
2. **Tone**: Engaging, promotional, community-focused
3. **Content**:
   - What topics/games are covered
   - Key highlights or memorable moments
   - Why community members might enjoy this
4. **Avoid**: Spoilers, excessive detail, timestamps

## Example Post

```markdown
https://www.youtube.com/watch?v=dQw4w9WgXcQ

---

In this episode, the party ventures deep into the Underdark to confront the mysterious drow enclave that's been threatening the surface world. What starts as a reconnaissance mission quickly spirals into an intense negotiation with unexpected allies.

Highlights include an absolutely clutch deception roll from Marcus, some creative problem-solving with an immovable rod, and a cliffhanger ending that left everyone at the table speechless.

If you're a fan of political intrigue mixed with dungeon delving, this one's a must-watch. The party dynamics are in top form, and there are some genuine laugh-out-loud moments scattered throughout.

---

*This video was originally published on 15 June 2024.*
```

## Notes

- The YouTube URL at the top will auto-embed in Discourse (Onebox)
- Keep the horizontal rules (`---`) for visual separation
- The publish date note helps context for backdated posts
