---
name: "Roadmap: Maintain"
description: "{{ 𝛀𝛀𝛀 }} Recompute and synchronise roadmap task statuses across roadmaps.json and its projections"
model: opus
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Bash(python3:*)"]
argument-hint: [milestone id (optional, e.g. M3)]
---

Keep the roadmap coherent across its artefacts — `.claude/roadmaps.json` (machine-readable source of truth; operate on the active non-`archived` phase), the PHASE file it names (task list + dependency diagram), `docs/reports/ROADMAP_OVERVIEW.md` (prose overview) and the HTML dashboard if one exists — by recomputing statuses from the dependency graph and synchronising every artefact.

Shared conventions: `~/.claude/library/references/roadmap-conventions.md`. The CLI is `python3 "$HOME"/.claude/library/scripts/roadmap.py`.

> **Behaviour note.** Status is **mechanical**, not inferred. This skill does *not* guess whether a blocker still applies, does *not* suggest promoting tasks to "in progress" (there is no in-progress state), and does *not* delete completed nodes from the diagram. A task's status is a deterministic function of its `dependsOn`, computed by `roadmap.py recompute`. To clear a gate or blocker you edit the graph (remove the dependency); the recompute then follows.

If `$ARGUMENTS` names a milestone (e.g. `M3`), scope your *reporting* to that milestone; the recompute always reads the whole graph, because dependencies cross milestones.

## Steps

### 1. Read the artefacts and check the format

Run `python3 "$HOME"/.claude/library/scripts/roadmap.py detect`. Exit **3** = old simple format — **stop and tell the user to run `roadmap-migrate` first**. Exit **2** = could not locate/parse — ask the user for the path. Only proceed on exit 0.

Read `.claude/roadmaps.json`, the active phase's PHASE file (its `path`), and `docs/reports/ROADMAP_OVERVIEW.md`.

### 2. Apply the explicit status changes the user requested

If the user is marking tasks `done` (or resetting them to `todo`/`blocked`), edit those `status` fields in `roadmaps.json` first — preserving tab indentation, field order (`id, description, status, dependsOn, iterative, notes`), and the `notes`/`iterative` values exactly. The recompute in step 3 sets every *derived* status; you only hand-edit terminal decisions (`done`, `out_of_scope`) and deliberate parked seeds.

### 3. Recompute every derived status (delegated to the script)

Run `python3 "$HOME"/.claude/library/scripts/roadmap.py recompute --render`. It applies the fixed-point recompute under the precedence rule `deferred > paused > blocked > todo`, **writes the corrected statuses back** atomically, and refreshes the HTML artefact when one exists. It prints each `{ID}: old -> new` change; capture that list — it drives the projection sync below.

Failure modes, all surfaced by exit 1 with a message — stop and report, never work around:

- **Cycle in `dependsOn`** — the graph must be fixed (loops belong on the `iterative` flag, not a real back-edge).
- **Non-canonical file formatting** — the file is not tab-indented as the conventions require; ask the user before re-running with `--reformat` (it rewrites the whole file, not just statuses).

The rule it applies is in the conventions reference; you never compute it by hand.

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

### 5. Regenerate the Mermaid dependency diagram

Replace the entire fenced `mermaid` block under `## Dependency Diagram` with the output of:

```bash
python3 "$HOME"/.claude/library/scripts/roadmap.py graph --mermaid --direction LR
```

Wholesale replacement — never line-edit class lists or recolour by hand. The generated block carries the canonical classDefs, every edge under the terminal milestone convention, and correct `class` statements, so the diagram cannot drift from the JSON. (A legacy diagram that used the `open` class or old hexes is fixed by this same replacement.)

### 6. Keep ROADMAP_OVERVIEW.md in sync

A pure status update does not change the task total, so the header count usually holds. If it changed (after an add/remove), update `**N tasks across M milestones.**` — get the number from `python3 "$HOME"/.claude/library/scripts/roadmap.py stats`. Do not rewrite the prose narrative.

### 7. Validate and report

Run `python3 "$HOME"/.claude/library/scripts/roadmap.py validate` — it must report clean. Then report each `{ID}: old → new` status change grouped by milestone, whether the diagram block was regenerated, whether the HTML artefact was refreshed, and the overview count if it changed.

---

## Notes

- roadmaps.json is the source of truth; when it and the PHASE file disagree, recompute from roadmaps.json.
- The recompute is mechanical — never infer status from descriptions, external context, or likelihood of completion. A gate clears by a deliberate edit (removing the gate ID from `dependsOn` and its `blocks[]`), not by this skill's judgement.
- `done` and `out_of_scope` are terminal; root-seeded parked tasks are held as authored (details in the conventions reference).
- No in-progress state — if asked to mark something "in progress", clarify the six options.
