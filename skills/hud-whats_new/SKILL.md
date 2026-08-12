---
name: "Memo: What's New"
description: "{{ ƔƔƔ }} Summarise what the user can now see or do that they couldn't before this unit of work"
when_to_use: "As an automatic wrap-up right after a feature or fix lands, or whenever the user asks 'what changed?' / 'what can I do now?'."
model: sonnet
disable-model-invocation: false # useful as an automatic wrap-up after a unit of work lands
allowed-tools: ["Read", "Glob", "Grep", "Bash(git log:*)", "Bash(git diff:*)", "Bash(git status:*)"]
---

# What's New

Summarise what the user can now see or do that they couldn't before this unit of work.

## Rules

- Describe **observable behaviour only** — what appears on screen, what the user can interact with, what a command now outputs
- No implementation detail, no file names, no technical explanation
- Write in second person: "You can now..."
- If nothing user-visible changed (docs, tests, refactors only), say so in one sentence
- Keep it to 3–5 bullet points maximum

## Format

**Now you can:**

- [observable behaviour 1]
- [observable behaviour 2]
- ...
