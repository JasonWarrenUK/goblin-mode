---
name: "Roadmap: Maintain"
description: "{{ 𝛀𝛀𝛀 }} Recompute and synchronise roadmap task statuses across roadmaps.json and its projections, with optional codebase reconciliation"
when_to_use: "When roadmap task statuses might have drifted from actual progress — after a batch of merges, or periodically to keep the dashboard trustworthy. Pass 'reconcile' (or ask to check the roadmap against the code) to also infer done/unblocked tasks from the actual codebase."
model: opus
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Bash(python3:*)", "Bash(git:*)"]
argument-hint: [milestone id, or "reconcile" to also check against the codebase]
---

Keep the roadmap coherent across its artefacts — `.claude/roadmaps.json` (machine-readable source of truth; operate on the active non-`archived` phase), the PHASE file it names (task list + dependency diagram), `docs/reports/ROADMAP_OVERVIEW.md` (prose overview) and the HTML dashboard if one exists — by recomputing statuses from the dependency graph and synchronising every artefact. Optionally, first reconcile the graph itself against the actual codebase.

Shared conventions: `~/.claude/library/references/roadmap-conventions.md`. The CLI is `python3 "$HOME"/.claude/library/scripts/roadmap.py`.

> **Behaviour note.** The recompute (Steps 2–7) is **mechanical**, not inferred. It does *not* guess whether a blocker still applies, does *not* suggest promoting tasks to "in progress" (there is no in-progress state), and does *not* delete completed nodes from the diagram. A task's status is a deterministic function of its `dependsOn`, computed by `roadmap.py recompute`. The **only** sanctioned exception is Step 0: an opt-in, evidence-gated reconciliation against the codebase that proposes `done` calls and blocker-edge removals for you to confirm before anything is written. Outside Step 0, a gate or blocker clears only by a deliberate edit to the graph.

If `$ARGUMENTS` names a milestone (e.g. `M3`), scope your *reporting* to that milestone; the recompute always reads the whole graph, because dependencies cross milestones. If `$ARGUMENTS` says `reconcile` (or the user's intent is "check the roadmap against what's actually built" / "I just finished a batch, update the roadmap"), run Step 0 first.

## Steps

### 0. Codebase reconciliation (opt-in — only on a reconcile run)

Skip this step entirely on a plain status-sync run. Run it when asked to reconcile, or after the user reports finishing a batch of work.

1. **Detect + load.** Same guard as Step 1: `roadmap.py detect` (stop on exit 2/3). Read `roadmaps.json`.
2. **Build the candidate set.** From `roadmaps.json` directly, take every task with status `todo`, `blocked`, or `paused`. Skip `done`, `out_of_scope`, and `deferred` — never reconsider those. Note that `roadmap.py ready --json` only returns effective-`todo` tasks, so it under-covers this set on its own — use it purely to *order* the `todo` portion by leverage (`transitiveUnblocks` / `isMilestoneSink`), so the highest-impact tasks get checked first and you can stop early on a large roadmap; `blocked`/`paused` candidates still come from the direct JSON read and are checked because their dependency might now be satisfied in code even though they aren't yet `todo`.
3. **Bound the search by recency.** Get the changed-file set since the last reconciliation: if a prior run left a "last reconciled at `<sha>`" marker (see step 7), use `git diff --name-only <sha>..HEAD`; otherwise use a recent window (`git log --oneline -30` and `git diff --name-only HEAD~30..HEAD`, or the whole history for a small/new repo). Only search within this changed-file set — never the whole tree.
4. **Search per candidate, not in bulk.** For each candidate, derive 1–3 concrete terms from its `description`/`notes` (a filename, symbol, route, component name) and `Grep`/`Glob` for them within the changed-file set. Read a file only when a search hits.
5. **Classify each candidate**, applying the evidence rule below:
   - **Proposed done** — the described feature is fully present (whole task, not partial), with concrete evidence (file:symbol, route, test, call-site).
   - **Proposed unblock** — only for a blocker that is *not* itself a roadmap task, or is an external gate: something satisfied in code (or lifted externally) with no task ID to flip to `done`. Propose removing that specific `dependsOn`/gate entry (and the gate's `blocks[]`). When the blocker *is* another task, don't propose a separate unblock — proposing that blocking task `done` (above) is sufficient, since `recompute` cascades the unblock automatically once its status changes.
   - **Unconfirmed** — plausible but not conclusive (e.g. partial implementation). Never promote to done or unblock from here.
   - **Reverse drift** — a `done` task whose code can no longer be found. Report only; never revert a terminal status automatically.
6. **Evidence rule (conservatism):**
   - Positive, specific, whole-task evidence only — absence of a match is never evidence of anything.
   - A partially-implemented task stays exactly where it is (there's no in-progress state to move it to).
   - Never touch `done`, `out_of_scope`, or a root-seeded held `paused`/`deferred`.
   - Never infer a gate as cleared casually — gates are external by design; propose removing a gate dependency only on genuine, specific evidence, and only through the gate below.
7. **Confirmation gate.** Present the proposal before writing anything:

   ```
   Proposed done (codebase evidence):
     {ID} — {description}
         evidence: {file:symbol / route / test}

   Proposed unblock (prerequisite satisfied — remove edge):
     {ID} — remove dependency on {depId or gateId}
         evidence: {…}

   Unconfirmed (needs your call):
     {ID} — {why uncertain}

   Reverse drift (marked done, code not found):
     {ID} — {what's missing}
   ```

   Then ask: *"Does this look right? I'll apply what you confirm and recompute."* Only the approved subset proceeds. Record the current `git rev-parse HEAD` as this run's "last reconciled at" marker for next time (mention it in the final report; no separate file needed unless the user wants one persisted).
8. **Hand off.** Feed every approved `done` ID and every approved edge removal into Step 2 below, exactly as if the user had typed them. Continue with Steps 1–7 as normal (Step 1's format check still applies; Step 2 now has explicit edits to make).

### 1. Read the artefacts and check the format

Run `python3 "$HOME"/.claude/library/scripts/roadmap.py detect`. Exit **3** = old simple format — **stop and tell the user to run `roadmap-migrate` first**. Exit **2** = could not locate/parse — ask the user for the path. Only proceed on exit 0.

Read `.claude/roadmaps.json`, the active phase's PHASE file (its `path`), and `docs/reports/ROADMAP_OVERVIEW.md`.

### 2. Apply the explicit status changes and edge removals requested

If the user is marking tasks `done` (or resetting them to `todo`/`blocked`), edit those `status` fields in `roadmaps.json` first — preserving tab indentation, field order (`id, description, status, dependsOn, iterative, notes, assignee`), and the `notes`/`iterative`/`assignee` values exactly. The recompute in step 3 sets every *derived* status; you only hand-edit terminal decisions (`done`, `out_of_scope`) and deliberate parked seeds. Never touch or infer `assignee` here — this step edits status only.

If Step 0 ran, this is also where its **approved** edits land: set `status: done` on each approved done-ID, and remove each approved dependency/gate edge from the relevant task's `dependsOn` (and the gate's `blocks[]`, keeping the two in parity). Apply only what was explicitly approved — an unconfirmed or reverse-drift item from Step 0 is never written here.

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

Run `python3 "$HOME"/.claude/library/scripts/roadmap.py validate` — it must report clean. Then report each `{ID}: old → new` status change grouped by milestone, whether the diagram block was regenerated, whether the HTML artefact was refreshed, and the overview count if it changed. On a reconcile run, also restate the Step 0 proposal outcome (what was approved and applied, what was left unconfirmed, any reverse drift) and the commit SHA to use as next time's "last reconciled at" marker.

---

## Notes

- roadmaps.json is the source of truth; when it and the PHASE file disagree, recompute from roadmaps.json.
- The recompute (Steps 2–7) is mechanical — never infer status from descriptions, external context, or likelihood of completion outside Step 0. A gate clears by a deliberate edit (removing the gate ID from `dependsOn` and its `blocks[]`), never by casual judgement.
- Step 0 is the one sanctioned exception: codebase-inferred `done` calls and blocker-edge removals, always evidence-backed and always confirmed before Step 2 writes them. It is opt-in — only runs on a reconcile request, never silently.
- `done` and `out_of_scope` are terminal; root-seeded parked tasks are held as authored (details in the conventions reference). Step 0 never re-opens or flips these; reverse drift is reported, not corrected automatically.
- No in-progress state — if asked to mark something "in progress", clarify the six options.
