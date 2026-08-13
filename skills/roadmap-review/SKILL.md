---
name: "Roadmap: Review"
description: "Interview-led review of the roadmap's health — status freshness, the priorities the graph implies, and whether the plan still matches reality"
when_to_use: "Periodically, or when the roadmap feels stale, the priorities feel off, a milestone dragged past its intent, or the user asks 'is the roadmap still right?' — the strategic complement to roadmap-maintain's mechanical sync."
model: opus
effort: high
metadata:
  glyph: ᛟ
  family: roadmap
  bundle: roadmap-system
disable-model-invocation: false # explicit: read-only interview that writes nothing itself
allowed-tools: ["Read", "Glob", "Grep", "Bash(python3:*)", "Bash(git log:*)", "Bash(git diff:*)"]
disallowed-tools: ["Edit", "Write", "NotebookEdit"] # writes nothing itself; hands actions to the roadmap-* writers
arguments: ["milestone"]
argument-hint: "[milestone id (optional, to scope the review)]"
---

# Roadmap: Review

`roadmap-maintain` keeps the roadmap *consistent*; this skill asks whether it's still *true*. A roadmap can validate clean while quietly rotting: done-in-code tasks still `todo`, milestone goals describing last quarter's intent, a ready-set whose leverage ordering nobody has looked at since it was authored. This is a guided health check that ends in decisions, not a report that ends in a shrug.

Read-only: findings route to the skills that write. Shared conventions: `~/.claude/library/references/roadmap-conventions.md`.

## Step 1 — Gather the evidence

`roadmap.py detect` guard as usual (exit 3 → `roadmap-migrate`; exit 2 → ask). Then:

- `roadmap.py stats` and `ready --json` — distribution, per-milestone done-%, the ready-set with leverage signals
- `.claude/roadmaps.json` — milestone goals, gates, notes, parked (`paused`/`deferred`) tasks
- `git log --oneline -30` — what actually shipped recently, as a drift smell-test (full reconciliation belongs to `roadmap-maintain reconcile`; here it only informs questions)

Scope to `$ARGUMENTS`'s milestone when given.

## Step 2 — Assess along four axes

1. **Freshness** — does recent git activity suggest tasks are done-in-code but not marked? Are there `blocked` tasks whose blockers look finished? (Flag for a reconcile run; don't relitigate evidence here.)
2. **Implied priorities** — the ready-set *is* a priority statement: its leverage ordering says what matters next. Does the user agree with what it's saying? A high-leverage candidate nobody intends to touch, or a pet task with zero unblocks being worked first, are both findings.
3. **Milestone integrity** — per milestone: is the goal sentence still the goal? Is a nearly-done milestone (high done-%) worth closing out before opening a new front? Has any milestone become a dumping ground?
4. **The parked and the dead** — every `paused`/`deferred` task and every gate: still genuinely waiting, or quietly obsolete? Any `todo` that will realistically never be done and should be `out_of_scope`?

## Step 3 — The interview

2–4 questions per round, each anchored to a specific observation with its evidence ("M2 is 85% done with two tasks left, but the last five commits were all M4 territory — deliberate?"). Lead with the highest-stakes findings; skip axes that came back clean. End each round: *"More on this, or shall I pull the findings together?"*

## Step 4 — Findings and routing

Present decisions made, grouped by the skill that executes them:

```text
→ roadmap-maintain (reconcile):  {suspected-done tasks to verify against code}
→ roadmap-maintain (explicit):   {status calls: out_of_scope, un-park, re-seed}
→ roadmap-audit-deps:            {edges/gates that came up — full audit if several}
→ roadmap-update-tasks:          {new tasks surfaced}
→ roadmap-create-interview:      {a theme big enough to deserve its own session}
→ No action:                     {reviewed and healthy — say so explicitly}
```

Offer to run the first of these now. This skill writes nothing itself.

When the findings are substantial or worth sharing, also offer to render them visually: map them to `artefact-audit`'s JSON shape and run that skill in render-only mode. Decline gracefully if the terminal summary is all that's wanted.

## Red flags

**Never:** edit any roadmap artefact directly; mark anything done without `roadmap-maintain`'s evidence gate; turn the review into feature brainstorming (route it); manufacture findings when the roadmap is healthy — "nothing needs changing" is a valid, complete outcome.

<raw-arguments value="$ARGUMENTS" />
