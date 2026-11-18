---
name: "Review Roadbook"
description: "Interview-led review of the roadbook (the plan goblin-scout keeps): strategic health (freshness, priorities, milestone integrity) and dependency-graph rationality across its waypoints (tasks), in one pass or by lens"
when_to_use: "Periodically, or when the roadbook feels stale, priorities feel off, waypoints feel blocked for no reason or a milestone dragged past its intent. Lenses: 'health' for the strategic pass, 'deps' for the edge audit, default both; the judgement complement to goblin-scout:tend-roadbook's mechanical sync."
model: fable
effort: medium
metadata:
  glyph: ᚠ
  family: scout
disable-model-invocation: false # explicit: read-only interview that writes nothing itself
allowed-tools: ["Read", "Glob", "Grep", "Bash(python3:*)", "Bash(git log:*)", "Bash(git diff:*)"]
disallowed-tools: ["Edit", "Write", "NotebookEdit"] # writes nothing itself; hands actions to the goblin-scout writers
arguments: ["lens", "milestone"]
argument-hint: "[health|deps|full] [milestone id (optional)]"
---

# Roadbook: Review

`goblin-scout:tend-roadbook` keeps the roadbook *consistent*; this skill asks whether it's still *true*. A roadbook can validate clean while quietly rotting: done-in-code waypoints still `todo`, milestone goals describing last quarter's intent, edges that outlived their reason, a ready-set whose leverage ordering nobody has looked at since it was authored. This is a guided check that ends in decisions; a shrug is no ending at all.

Read-only: findings route to the skills that write. Shared conventions: `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`. The CLI is `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py`.

## Step 0: Resolve the lens

`$lens` is `health`, `deps` or `full` (the default when absent). Health runs axes 1 to 4; deps runs axis 5 with its suspect-list machinery; full runs everything. `$milestone` scopes any lens to one milestone (plus its cross-milestone edges; that is often where the rot is).

## Step 1: Gather the evidence

`roadbook.py detect` guard as usual (exit 3 → `goblin-scout:rebind-roadbook`; exit 2 → ask). Then:

- `roadbook.py stats` and `ready --json`: distribution, per-milestone done-%, the ready-set with leverage signals
- `roadbook.py graph --json` (deps and full lenses): the full edge set
- `.claude/roadbook.json`: milestone goals, gates, notes, parked (`paused`/`deferred`) waypoints, `softDependsOn`
- `git log --oneline -30`: what actually shipped recently, as a drift smell-test (full reconciliation belongs to `goblin-scout:tend-roadbook reconcile`; here it only informs questions)

## Step 2: Assess along five axes

1. **Freshness**: does recent git activity suggest waypoints are done-in-code but not marked? Are there `blocked` waypoints whose blockers look finished? Is any trail stale (a `started` date more than 14 days old on an unfinished waypoint) or on a waypoint no longer ready (in `ready --json`'s `claimed` with a `status` other than `todo`)? (Flag for a reconcile run or for the scout on that trail, who can drop it with `goblin-scout:start-trail <ID> release`; never release or change a trail here, and don't relitigate evidence.)
2. **Implied priorities**: the ready-set *is* a priority statement: its leverage ordering says what matters next. Does the user agree with what it's saying? A high-leverage candidate nobody intends to touch, or a pet waypoint with zero unblocks being worked first, are both findings.
3. **Milestone integrity**, per milestone: is the goal sentence still the goal? Is a nearly-done milestone (high done-%) worth closing out before opening a new front? Has any milestone become a dumping ground?
4. **The parked and the dead**: every `paused`/`deferred` waypoint and every gate: still genuinely waiting, or quietly obsolete? Any `todo` that will realistically never be done and should be `out_of_scope`?
5. **Graph rationality** (deps and full lenses): the recompute keeps statuses consistent with the graph; nothing checks the graph itself is right. Edges accrete: a dependency that made sense at authoring time survives long after the reason evaporated, and a missing edge never announces itself. Build the suspect list mechanically before asking anything, so the interview spends the user's attention only where the graph is genuinely questionable:
   - **Suspicious hard edges**: a `dependsOn` between waypoints that share no obvious artefact (different area, different category, no note explaining it). Candidate for removal or demotion to `softDependsOn`.
   - **Suspicious absences**: waypoint pairs that plainly touch the same artefact (matching terms in descriptions/notes) with no edge either way.
   - **Over-serialised chains**: A→B→C→D where the middle links look like authoring order with no real dependency behind them; each unnecessary link delays the tail.
   - **Bottlenecks**: a waypoint whose `transitiveUnblocks` dwarfs the rest; is the fan-in real, or are several dependants only loosely related to it?
   - **Gate rationality**: for every external gate, is it still genuinely external, still imposing the right status and is its `blocks[]` list still the honest set?
   - **Milestone boundaries**: waypoints whose edges mostly cross into a *different* milestone probably live in the wrong one; milestone-ID dependencies (`M1`) worth checking against intent (all of M1, or really just two waypoints in it?).
   - **Soft/hard misfiles**: `softDependsOn` entries that in truth gate the work, and hard edges that are really "nice to sequence".

## Step 3: The interview

2–4 questions per round, each anchored to a specific observation with its evidence inline ("M2 is 85% done with two waypoints left, but the last five commits were all M4 territory; deliberate?", "`3IN.2` depends on `2EV.4`, but nothing in either description links them; what's the connection?"). Lead with the highest-stakes findings; skip axes that came back clean; never present the whole suspect list as homework.

For each graph finding the user engages with, converge on one of: **keep** (reason now recorded for the notes field), **remove**, **demote to soft**, **promote to hard**, **add missing edge**, **move waypoint to another milestone**, **gate edit**. End each round: *"More on this, or shall I pull the findings together?"*

## Step 4: Findings and routing

Present decisions made, grouped by the skill that executes them. Edge changes use this shorthand:

```text
Edge removals:    {waypoint} -x-> {dep}   ({why})
Edge additions:   {waypoint} ---> {dep}   ({why})
Soft/hard flips:  {waypoint} ~~~> {dep}   ({direction and why})
Gate edits:       {gateId}: {change}
Moves:            {waypoint} → {milestone} ({why})
Note updates:     {waypoint}: record kept-edge rationale
```

```text
→ goblin-scout:tend-roadbook (reconcile):  {suspected-done waypoints to verify against code}
→ goblin-scout:tend-roadbook (explicit):   {status calls; soft-edge add/remove; approved edge/gate removals}
→ goblin-scout:add-waypoints:              {new waypoints surfaced}
→ goblin-scout:plan-expedition:            {a theme big enough to deserve its own expedition}
→ No writer yet (edit `.claude/roadbook.json` directly, then `recompute --check`): {a new hard edge between two existing waypoints; a gate field edit outside an approved removal; moving an existing waypoint to a different milestone}
→ No action:                               {reviewed and healthy; say so explicitly}
```

Offer to run the first of these now. This skill writes nothing itself.

## Red flags

**Never:** edit any roadbook artefact directly; mark anything done without `goblin-scout:tend-roadbook`'s evidence gate; propose removing an edge just because it's inconvenient (the question is whether it's *true*); treat a user's "I don't remember why" as licence to delete: an unexplained edge that keeps coming up gets a note, never a silent removal; turn the review into feature brainstorming (route it); manufacture findings when the roadbook is healthy: "nothing needs changing" is a valid, complete outcome.

<raw-arguments value="$ARGUMENTS" />
