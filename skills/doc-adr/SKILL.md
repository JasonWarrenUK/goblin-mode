---
name: "Docs: ADR"
description: "{{ ƔƔƔ }} Create an Architecture Decision Record for a significant technical decision"
when_to_use: "When a technical choice was hard-won or non-obvious enough that future-you (or a teammate) will ask 'why did we do it this way?' — schema shape, library swap, architectural pattern."
model: sonnet
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Write"]
arguments: ["title"]
argument-hint: "[brief decision title]"
---

# Docs: ADR

Replaces the former `doc-adr-create`. Interview to fill `~/.claude/library/templates/ADR.md`, numbered and placed automatically.

## Steps

1. **Resolve the title.** `$title` if given; otherwise ask for one line naming the decision.
2. **Find home and number.** Glob for existing ADRs (`docs/dev/architecture/*-adr.md` first, then any `**/adr/**` or `**/*-adr.md` pattern the project already uses). Next number = highest found + 1, zero-padded to match the local convention (`003`). No existing ADRs → start at `001` in `docs/dev/architecture/`. State what you found and the number you'll use.
3. **Read the template**, then interview — 2–3 questions per round, conversational, probing until every slot can be filled with conviction rather than padding:
   - **Context** — what problem forced a decision? What constraints and forces were real?
   - **Decision** — what exactly was chosen? Specifics, not categories.
   - **Alternatives** — what else was on the table, and why did each lose? An ADR with no credible alternative usually isn't recording a decision.
   - **Consequences** — what gets better, what gets harder, what trade-off was knowingly accepted?
4. **Draft** the ADR filling the template exactly — no invented sections, no slop-filled slots. The test: understandable by someone six months out with no memory of the conversation.
5. **Show the draft and stop for approval.** On approval, write to `{dir}/{NNN}-{decision-slug}-adr.md`. Revise and re-show if changes are requested.

## Notes

- One decision per ADR — if the interview surfaces two decisions, say so and split.
- British spelling; match the tone of any existing ADRs in the project.

<raw-arguments value="$ARGUMENTS" />
