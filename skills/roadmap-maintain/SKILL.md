---
name: roadmap-maintain
description: "{{ 𝛀𝛀𝛀 }} Recompute and synchronise roadmap task statuses across roadmaps.json and its projections"
model: opus
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Bash(python3:*)", "Bash(git:*)"]
argument-hint: [milestone id (optional, e.g. M3)]
---

Keep the roadmap coherent across its three artefacts — `.claude/roadmaps.json` (machine-readable source of truth, an array of phase objects; operate on the active non-`archived` entry), the PHASE file it names (task list + dependency diagram), and `docs/reports/ROADMAP_OVERVIEW.md` (prose overview) — by recomputing statuses from the dependency graph and synchronising every artefact.

Shared scripts live in `~/.claude/library/scripts/` (invoke as `python3 ~/.claude/library/scripts/{name}.py`; use `"$HOME"/.claude/...` if `~` is not expanded).

> **Behaviour note (changed from the old judgement-based skill).** Status is now **mechanical**, not inferred. This skill does *not* guess whether a blocker still applies, does *not* suggest promoting tasks to "in progress" (there is no in-progress state), and does *not* delete completed nodes from the diagram (done tasks stay, classed `done`). A task's status is a deterministic function of its `dependsOn`, computed by `recompute_roadmap.py`. To clear a gate or blocker you edit the graph (remove the dependency); the recompute then follows.

If `$ARGUMENTS` names a milestone (e.g. `M3`), scope your *reporting* to that milestone; the recompute always reads the whole graph, because dependencies cross milestones.

## Steps

### 1. Read the artefacts and check the format

Run `python3 ~/.claude/library/scripts/detect_format.py`. Exit 3 = old simple format — **stop and tell the user to run `roadmap-migrate` first** (a mechanical recompute is meaningless on a four-status anchored Markdown file). Only proceed when the roadmap is rich (exit 0).

Read `.claude/roadmaps.json`, the active phase's PHASE file (its `path`), and `docs/reports/ROADMAP_OVERVIEW.md`.

The status vocabulary is `todo`, `blocked`, `paused`, `deferred`, `done`, `out_of_scope` — no in-progress. Gates live in `externalGates` with an `imposes` value; a `dependsOn` entry may be a task, a milestone ID, or a gate ID.

### 2. Apply the explicit status changes the user requested

If the user is marking tasks `done` (or resetting them to `todo`/`blocked`), edit those `status` fields in `roadmaps.json` first — preserving tab indentation, field order (`id, description, status, dependsOn, iterative, notes`), and the `notes`/`iterative` values exactly. The recompute in step 3 sets every *derived* status; you only hand-edit terminal decisions (`done`, `out_of_scope`) and deliberate parked seeds.

### 3. Recompute every derived status (delegated to the script)

Run `python3 ~/.claude/library/scripts/recompute_roadmap.py`. It applies the fixed-point recompute under the precedence rule `deferred > paused > blocked > todo` and **writes the corrected statuses back** to `roadmaps.json`, preserving formatting. It prints each `{ID}: old -> new` change; capture that list — it drives the projection sync below.

The rule it applies (for reference; you do not compute this by hand):

- a `done` task, or a milestone whose tasks are all `done` → imposes nothing;
- a not-`done` task → imposes `max(blocked, its own status)`, so `paused`/`deferred` propagate down the chain;
- a gate → imposes its `imposes` value (default `blocked`).
- Held seeds (`done`, `out_of_scope`, and root-seeded `paused`/`deferred` with empty `dependsOn`) are never recomputed but still propagate.

If the script exits 1 it has found a **cycle** in `dependsOn` and refused to write — surface the reported cycle to the user and stop; the graph must be fixed (loops belong on the `iterative` flag, not a real back-edge).

### 4. Synchronise the PHASE file task lines

For each task whose status changed (from the script's output), update its line in the PHASE file. If the file uses status sub-sections, move the task under the matching sub-section (omit any that would be empty); otherwise leave it in place. Update the checkbox and trailing annotation:

| Status                              | Checkbox | Trailing annotation                                        |
| ----------------------------------- | -------- | ---------------------------------------------------------- |
| `done`                              | `- [x]`  | none                                                       |
| `blocked`                           | `- [ ]`  | `_(blocked — depends on {comma-separated dependsOn IDs})_` |
| `paused`                            | `- [ ]`  | `_(paused — reconvene {gateId})_`                          |
| `deferred`                          | `- [ ]`  | `_(deferred to a later phase)_`                            |
| `todo` with dependencies (all done) | `- [ ]`  | `_(depends on {IDs})_`                                     |
| `todo` with empty `dependsOn`       | `- [ ]`  | none                                                       |
| `out_of_scope`                      | `- [ ]`  | left as authored (terminal)                                |

Line format: `- [ ] **{ID}** — {description}` + annotation. Indented `- Note:` sub-bullets stay attached to their task and are never moved. Do not reorder tasks — they stay in milestone/category/sequence order.

### 5. Synchronise the Mermaid dependency diagram

The diagram (under `## Dependency Diagram`) uses `graph LR` with the terminal milestone convention. Update only the **task class-assignment lines** so each task ID sits in exactly the list matching its recomputed status (ascending order):

```
	class {IDs} open      %% every todo task
	class {IDs} blocked   %% every blocked task (including gate-only blocks)
	class {IDs} paused
	class {IDs} deferred
```

Done and `out_of_scope` tasks appear in none of these (done carries `done`; out-of-scope becomes `:::outOfScope`). Gate and milestone nodes keep their own class and never appear in the task lists. Preserve the leading tab on the class lines.

Do **not** add/remove edges or nodes here — edge placement is `roadmap-update-tasks`'s job. As a read-only cross-check, confirm the diagram's edges match the graph (every `dependsOn` has a matching edge, every gate `dependsOn` is mirrored in the gate's `blocks[]`, milestone sinks point into their node); **report** any mismatch rather than fixing it. `python3 ~/.claude/library/scripts/roadmap_graph.py` gives the authoritative edge set to compare against.

### 6. Keep ROADMAP_OVERVIEW.md in sync

A pure status update does not change the task total, so the header count usually holds. If it changed (after an add/remove), update `**N tasks across M milestones.**` — get the number from `python3 ~/.claude/library/scripts/roadmap_stats.py`. Do not rewrite the prose narrative.

### 7. Validate and report

Run `python3 ~/.claude/library/scripts/validate_roadmap.py` — it must report clean. Then report each `{ID}: old → new` status change grouped by milestone, the IDs moved between the Mermaid class lists, and the overview count if it changed.

---

## Notes

- roadmaps.json is the source of truth; when it and the PHASE file disagree, recompute from roadmaps.json.
- The recompute is mechanical — never infer status from descriptions, external context, or likelihood of completion. A gate clears by a deliberate edit (removing the gate ID from `dependsOn` and its `blocks[]`), not by this skill's judgement.
- `done` and `out_of_scope` are terminal. `paused`/`deferred` are computed from dependencies (a task is paused because a gate imposes it, not because someone typed it), except a root-seeded parked task with empty `dependsOn`, which is held as authored.
- Tabs not spaces; British spelling. No in-progress state — if asked to mark something "in progress", clarify the six options.
