---
name: "Roadmap: Audit Dependencies"
description: "{{ 𝛀𝛀𝛀 }} Interview-led audit of the roadmap's dependency graph — are the edges, gates and milestone boundaries actually rational?"
when_to_use: "When the dependency graph deserves scrutiny — tasks that feel blocked for no reason, suspiciously parallel milestones, before committing to a milestone's build order, or periodically once a roadmap has grown past its original shape."
model: opus
effort: high
disable-model-invocation: false # explicit: read-only interview, safe for Claude to open when the graph smells wrong
allowed-tools: ["Read", "Glob", "Grep", "Bash(python3:*)"]
arguments: ["milestone"]
argument-hint: [milestone id (optional, to scope the audit)]
---

# Roadmap: Audit Dependencies

The status recompute keeps statuses *consistent with* the graph; nothing checks that the graph itself is *right*. Edges accrete: a dependency that made sense at authoring time survives long after the reason evaporated, and a missing edge never announces itself. This skill walks the graph with the user and questions it, milestone by milestone.

Read-only: the output is a proposed edit list. `roadmap-maintain` applies edge changes; `roadmap-update-tasks` adds anything new. Shared conventions: `~/.claude/library/references/roadmap-conventions.md`.

## Step 1 — Load the graph

`python3 "$HOME"/.claude/library/scripts/roadmap.py detect` (exit 3 → run `roadmap-migrate` first; exit 2 → ask for the path). Then gather:

- `roadmap.py graph --json` — the full edge set
- `roadmap.py ready --json` and `stats` — leverage signals and the status distribution
- `.claude/roadmaps.json` directly — `softDependsOn`, gates, notes, milestone goals

If `$ARGUMENTS` names a milestone, scope the walk to it (plus its cross-milestone edges — those are often where the rot is).

## Step 2 — Build the suspect list before asking anything

Derive findings mechanically first, so the interview spends the user's attention only where the graph is genuinely questionable:

- **Suspicious hard edges** — a `dependsOn` between tasks that share no obvious artefact (different area, different category, no note explaining it). Candidate for removal or demotion to `softDependsOn`.
- **Suspicious absences** — task pairs that plainly touch the same artefact (matching terms in descriptions/notes) with no edge either way.
- **Over-serialised chains** — A→B→C→D where the middle links look like authoring order, not real dependency; each unnecessary link delays the tail.
- **Bottlenecks** — a task whose `transitiveUnblocks` dwarfs the rest; is the fan-in real, or are several dependants only loosely related to it?
- **Gate rationality** — every external gate: is it still genuinely external, still imposing the right status (`blocked`/`paused`/`deferred`), and is its `blocks[]` list still the honest set?
- **Milestone boundaries** — tasks whose edges mostly cross into a *different* milestone probably live in the wrong one; milestone-ID dependencies (`M1`) worth checking against intent (all of M1, or really just two tasks in it?).
- **Soft/hard misfiles** — `softDependsOn` entries that in truth gate the work, and hard edges that are really "nice to sequence".

## Step 3 — The interview

Walk milestone by milestone, 2–4 questions per round, each anchored to a specific finding with the evidence inline ("`3IN.2` depends on `2EV.4`, but nothing in either description links them — what's the connection?"). Never ask about edges the suspect list gives no reason to doubt, and never present the whole list as homework.

For each finding the user engages with, converge on one of: **keep** (reason now recorded for the notes field), **remove**, **demote to soft**, **promote to hard**, **add missing edge**, **move task to another milestone**, **gate edit**. End each round: *"More of this milestone, or move on?"*

## Step 4 — Propose

```text
Edge removals:    {task} -x-> {dep}   — {why}
Edge additions:   {task} ---> {dep}   — {why}
Soft/hard flips:  {task} ~~~> {dep}   — {direction and why}
Gate edits:       {gateId} — {change}
Moves:            {task} → {milestone} — {why}
Note updates:     {task} — record kept-edge rationale
```

Confirm the list, then hand off: edge/gate/status changes go to `roadmap-maintain` (its Step 2 applies explicit edits, recomputes and re-projects); new tasks or milestone moves go to `roadmap-update-tasks`. This skill writes nothing itself.

## Red flags

**Never:** edit `roadmaps.json` or any projection directly; propose removing an edge just because it's inconvenient (the question is whether it's *true*); treat a user's "I don't remember why" as licence to delete — an unexplained edge that keeps coming up gets a note, not a silent removal; let the audit balloon into feature planning (that's `roadmap-create-interview`).

<raw-arguments value="$ARGUMENTS" />
