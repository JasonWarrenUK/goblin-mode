---
name: "Suggest: Task"
description: "{{ 𝚫𝚫𝚫 }} Suggest the next logical task — grounded in the roadmap's pre-vetted ready-set when one exists, codebase analysis otherwise"
when_to_use: "When you don't know what to work on next and want a grounded recommendation rather than picking arbitrarily."
model: haiku
effort: low
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Bash(python3:*)", "Bash(npm:*)", "Bash(bun:*)", "Bash(pnpm:*)", "Bash(deno:*)"]
argument-hint: [named dev (default none)] [topic focus (optional)]
---

Suggest the next logical task I can complete. Selection is grounded in deterministic data wherever possible — you choose between pre-vetted options rather than deriving them.

## Step 0 — Parse arguments

`$ARGUMENTS` may carry an assignee, a focus area, both, or neither — positionally, assignee first. Parse by intent, not blind position-splitting:

- No arguments → no assignee, no focus.
- One token/phrase that plainly reads as a person's name → treat as **assignee** only.
- One token/phrase that plainly reads as a topic/area (e.g. "auth", "the export flow") → treat as **focus** only, even though it's in the first position. Don't force a topic into the assignee slot.
- Two tokens/phrases where the first is a name and the rest is a topic → first is **assignee**, remainder is **focus**.
- If genuinely ambiguous which is which, ask rather than guess.

## Step 1 — Try the roadmap first

Run `python3 "$HOME"/.claude/library/scripts/roadmap.py detect`.

**Exit 0 (rich roadmap):** run `python3 "$HOME"/.claude/library/scripts/roadmap.py ready --json` and `... stats`. The `candidates` array is the complete set of actionable tasks — every one is unblocked by definition. Each candidate carries an `assignee` field (empty string when unassigned — never assume unassigned means "anyone" without saying so). Pick using the supplied signals, in this order of pull:

1. **Assignee**, when given — filter to candidates whose `assignee` matches. If none match, say so explicitly (`"No ready task assigned to {name}."`), then fall back to the highest-leverage pick from the full candidate set below — never stay silent and never invent a match.
2. Focus area, when given — filter to candidates matching it
3. `transitiveUnblocks` — prefer the task that unblocks the most downstream work
4. `isMilestoneSink` on a milestone with high `milestoneDonePct` — closing out a nearly-done milestone beats starting a new front

Name the chosen task by its roadmap ID and say which signals drove the choice. If `candidates` is empty, say so and name the cheapest unblock instead (which blocker or gate, if cleared, frees the most tasks — read the `stats` breakdown).

**Exit 3 or 2 (no rich roadmap):** fall back to Step 2.

## Step 2 — Fallback: codebase analysis

Analyse the current state of the codebase, then compare it to the project documentation. Rules:

1. Conserve tokens by being selective in which files you read.
2. Where possible, use dev scripts in @./package.json & @./scripts rather than reading file content.
3. If a focus area was given, focus suggestions on that area.
4. There is no roadmap data here to filter by assignee — if an assignee was given, say this fallback can't honour it rather than guessing.

## Always

- If the task will take longer than 45 minutes, subdivide it and suggest the first subtask.
- After suggesting the task, add a **"When complete, you'll be able to:"** section. Describe concretely and specifically what the user will see on screen or be able to do in the app that they cannot do right now. Focus on observable behaviour, not implementation detail.

<raw-arguments value="$ARGUMENTS" />
