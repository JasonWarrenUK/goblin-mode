---
name: "Tend Roadbook"
description: "Tend the roadbook (the plan goblin-scout keeps) after work lands: recompute waypoint (task) statuses from the dependency graph and refresh every projection and the chart, with optional codebase reconciliation"
when_to_use: "When roadbook waypoint statuses might have drifted from actual progress: after a batch of merges, or periodically to keep the chart trustworthy. Pass 'reconcile' (or ask to check the roadbook against the code) to also infer done/unblocked waypoints from the actual codebase."
model: sonnet
effort: high # high rather than medium: the reconcile path infers waypoint completion from codebase evidence
metadata:
  glyph: ᛊ
  family: scout
disable-model-invocation: false # invocable by Claude so it can offer a status sync after merges; the reconcile confirmation gate still applies
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Bash(python3:*)", "Bash(git:*)", "Agent"]
argument-hint: '[milestone id | "reconcile" to also check against the codebase]'
---

Keep the roadbook coherent across its artefacts by recomputing statuses from the dependency graph and synchronising every artefact. The artefacts: `.claude/roadbook.json` (machine-readable source of truth; operate on the active non-`archived` phase), the PHASE file it names (waypoint list + dependency diagram), the prose overview (`docs/reports/ROADBOOK_OVERVIEW.md`, or `ROADMAP_OVERVIEW.md` in a project that predates 3.0.0) and the chart (the HTML page) if one exists. Optionally, first reconcile the graph itself against the actual codebase.

Shared conventions: `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`. The CLI is `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py`.

> **Behaviour note.** The recompute (Steps 2–7) is **mechanical**: nothing in it is inferred. It does *not* guess whether a blocker still applies, does *not* suggest promoting waypoints to "in progress" (that is a trail a scout starts, never a status; see Step 2) and does *not* delete completed nodes from the diagram. A waypoint's status is a deterministic function of its `dependsOn`, computed by `roadbook.py recompute`. The **only** sanctioned exception is Step 0: an opt-in, evidence-gated reconciliation against the codebase that proposes `done` calls and blocker-edge removals for you to confirm before anything is written. Outside Step 0, a gate or blocker clears only by a deliberate edit to the graph.

If `$ARGUMENTS` names a milestone (e.g. `M3`), scope your *reporting* to that milestone; the recompute always reads the whole graph, because dependencies cross milestones. If `$ARGUMENTS` says `reconcile` (or the user's intent is "check the roadbook against what's actually built" / "I just finished a batch, update the roadbook"), run Step 0 first.

## Steps

### 0. Codebase reconciliation (opt-in, only on a reconcile run)

Skip this step entirely on a plain status-sync run. Run it when asked to reconcile, or after the user reports finishing a batch of work.

1. **Detect + load.** Same guard as Step 1: `roadbook.py detect` (stop on exit 2/3). Read `roadbook.json`.
2. **Build the candidate set.** From `roadbook.json` directly, take every waypoint with status `todo`, `blocked` or `paused`. Skip `done`, `out_of_scope` and `deferred`; never reconsider those. Check waypoints on a trail (`ready --json`'s `claimed` list) first: a scout started them, so they are the likeliest to be built already. Note that `roadbook.py ready --json`'s `candidates` only holds effective-`todo` waypoints with no trail, so it under-covers this set on its own; use it purely to *order* the rest of the `todo` portion by leverage (`transitiveUnblocks` / `isMilestoneSink`), so the highest-impact waypoints get checked first and you can stop early on a large roadbook; `blocked`/`paused` candidates still come from the direct JSON read and are checked because their dependency might now be satisfied in code even though they aren't yet `todo`.
3. **Bound the search by recency.** Get the changed-file set since the last reconciliation: if a prior run left a "last reconciled at `<sha>`" marker (see step 7), use `git diff --name-only <sha>..HEAD`; otherwise use a recent window (`git log --oneline -30` and `git diff --name-only HEAD~30..HEAD`, or the whole history for a small/new repo). Only search within this changed-file set, never the whole tree.
4. **Search per candidate.** For each candidate, derive 1–3 concrete terms from its `description`/`notes` (a filename, symbol, route, component name) and `Grep`/`Glob` for them within the changed-file set. Read a file only when a search hits.

   When the candidate set has **4 or more** entries, dispatch one read-only subagent per candidate in parallel instead of looping sequentially: each agent gets the candidate's ID, description, notes and the changed-file set, and returns its classification (below) plus the evidence found. No subagent edits anything; this is search fan-out only, and the confirmation gate in step 7 is unchanged. Below 4 candidates, work the loop directly: dispatch overhead exceeds the saving.
5. **Classify each candidate**, applying the evidence rule below:
   - **Proposed done**: the described feature is fully present (the whole waypoint; partial work does not count), with concrete evidence (file:symbol, route, test, call-site).
   - **Proposed unblock**: only for a blocker that is *not* itself a roadbook waypoint, or is an external gate: something satisfied in code (or lifted externally) with no waypoint ID to flip to `done`. Propose removing that specific `dependsOn`/gate entry (and the gate's `blocks[]`). When the blocker *is* another waypoint, don't propose a separate unblock; proposing that blocking waypoint `done` (above) is sufficient, since `recompute` cascades the unblock automatically once its status changes.
   - **Unconfirmed**: plausible but not conclusive (e.g. partial implementation). Never promote to done or unblock from here.
   - **Reverse drift**: a `done` waypoint whose code can no longer be found. Report only; never revert a terminal status automatically.
6. **Evidence rule (conservatism):**
   - Positive, specific, whole-waypoint evidence only; absence of a match is never evidence of anything.
   - A partially-implemented waypoint stays exactly where it is: inference never starts or releases a trail (a trail is a person's statement).
   - Never touch `done`, `out_of_scope`, or a root-seeded held `paused`/`deferred`.
   - Never infer a gate as cleared casually: gates are external by design; propose removing a gate dependency only on genuine, specific evidence and only through the gate below.
7. **Confirmation gate.** Present the proposal before writing anything:

   ```text
   Proposed done (codebase evidence):
     {ID}: {description}
         evidence: {file:symbol / route / test}

   Proposed unblock (prerequisite satisfied; remove edge):
     {ID}: remove dependency on {depId or gateId}
         evidence: {…}

   Unconfirmed (needs your call):
     {ID}: {why uncertain}

   Reverse drift (marked done, code not found):
     {ID}: {what's missing}
   ```

   Then ask: *"Does this look right? I'll apply what you confirm and recompute."* Only the approved subset proceeds. Record the current `git rev-parse HEAD` as this run's "last reconciled at" marker for next time (mention it in the final report; no separate file needed unless the user wants one persisted).
8. **Hand off.** Feed every approved `done` ID and every approved edge removal into Step 2 below, exactly as if the user had typed them. Continue with Steps 1–7 as normal (Step 1's format check still applies; Step 2 now has explicit edits to make).

### 1. Read the artefacts and check the format

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py detect`. Exit **3** = old simple format: **stop and tell the user to run `goblin-scout:rebind-roadbook` first**. Exit **2** = could not locate/parse: ask the user for the path. Only proceed on exit 0.

Read `.claude/roadbook.json`, the active phase's PHASE file (its `path`), and the overview (`docs/reports/ROADBOOK_OVERVIEW.md`, or `ROADMAP_OVERVIEW.md` in a project that predates 3.0.0).

### 2. Apply the explicit status changes and edge removals requested

If the user is marking waypoints `done` (or resetting them to `todo`/`blocked`), edit those `status` fields in `roadbook.json` first, preserving tab indentation, the conventions reference's waypoint field order and the `notes`/`iterative`/`assignee`/`started`/`softDependsOn`/`softMilestone` values exactly. The recompute in step 3 sets every *derived* status; you only hand-edit terminal decisions (`done`, `out_of_scope`) and deliberate parked seeds. Never touch or infer `assignee` here: this step edits status only. A waypoint reset from `done` to anything else must also lose its `ended` date (delete the line and fix the trailing comma): `validate` rejects an end date on a waypoint that is not done. The end date of a waypoint newly marked `done` is set in step 3b, not by hand.

If the user says a waypoint is **in progress** (a scout has started it), start a trail on it rather than editing its status: hand over to the `goblin-scout:start-trail` skill (`goblin-scout:start-trail <ID> [scout]`), which asks which scout is doing it (never inferring one), runs `roadbook.py claim` and commits the change. If they say work on a waypoint has **stopped**, the same skill releases it (`goblin-scout:start-trail <ID> release`). A trail changes no status, has no PHASE file waypoint-line annotation (the regenerated diagram in step 5 shows it) and never goes through step 3; `claim` refuses a waypoint that isn't ready to start, so relay its message rather than forcing it.

If the user asks to add or remove a soft (optional, best-effort) link between two nodes, edit the relevant waypoint's `softDependsOn` array directly; see the conventions reference for direction and semantics. Soft edges never go through the recompute in step 3; they're pure data, picked up automatically when the diagram regenerates in step 5.

If Step 0 ran, this is also where its **approved** edits land: set `status: done` on each approved done-ID, and remove each approved dependency/gate edge from the relevant waypoint's `dependsOn` (and the gate's `blocks[]`, keeping the two in parity). Apply only what was explicitly approved; an unconfirmed or reverse-drift item from Step 0 is never written here.

### 3. Recompute every derived status (delegated to the script)

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py recompute --render`. It applies the fixed-point recompute under the precedence rule `deferred > paused > blocked > todo`, **writes the corrected statuses back** atomically and refreshes the chart when one exists (at the phase's `artefact` path when `roadbook.json` sets one, else the default `docs/artefacts/chart-{slug}.html`; the same resolver `render` uses). The refreshed chart renders every collapsible section closed by default (template convention); never hand-add `open` attributes to it. It prints each `{ID}: old -> new` change; capture that list, since it drives the projection sync below.

Failure modes, all surfaced by exit 1 with a message; stop and report, never work around:

- **Cycle in `dependsOn`**: the graph must be fixed (loops belong on the `iterative` flag, never on a real back-edge).
- **Non-canonical file formatting**: the file is not tab-indented as the conventions require; ask the user before re-running with `--reformat` (it rewrites the whole file, statuses and all).

The rule it applies is in the conventions reference; you never compute it by hand.

### 3b. Date the finished waypoints

Every `done` waypoint should carry an `ended` date (an ISO date, set after `started`). `roadbook.py stamp-ended` stamps it when a branch lands; this step catches the rest: waypoints marked done by hand, by an earlier reconcile or before the field existed.

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py backfill-ended --dry-run`. It reads the git history of `roadbook.json` and proposes, per done waypoint lacking `ended`, the date of the commit where the waypoint last became done. Show the rows as `{ID}: {date} ({short sha})` and keep the flags visible:

- `[first-seen]`: the waypoint was already done when it first reached git, so the date is only a lower bound (when the roadbook was first committed); the work may have finished earlier.
- `[uncommitted]`: done only in the working tree, so the date is today.
- `[skipped: before started {date}]`: the proposed date precedes the waypoint's `started`, so writing it would fail `validate`. These rows are never written, whichever option is chosen; ask the user to correct `started` by hand or to give the date to set with `roadbook.py end <ID> --date <date>`.

Nothing to propose: say so and move on. Otherwise ask with AskUserQuestion: **Apply all** / **Apply, skipping first-seen** / **Skip**. Apply by rerunning without `--dry-run`; for the skipping option, set the approved rows one at a time with `roadbook.py end <ID> --date <date>`. Dates from a status-change commit are the commit's date, so a waypoint marked done in a later catch-up commit is dated to that commit, not the day the work shipped; say so when a row's commit message looks like a reconcile (`reconcile`, `mark ... done`).

### 4. Synchronise the PHASE file waypoint lines

Once step 3's recompute has produced the authoritative `{ID}: old -> new` list, this step and step 6 read from the same fixed set of changes; if there are enough changed waypoints that it's worth the parallelism (roughly 4+ status changes, or whenever step 6 also has work to do), dispatch both as parallel read-only agents: one diffs the PHASE file's waypoint lines against the authoritative list, one diffs the overview's header counts against `roadbook.py stats`. Each returns a table of what needs to change; you (not a subagent) make every edit here in step 4 and in step 6 sequentially, so two agents proposing overlapping changes never race on the same file. Below that threshold, or when step 6 has nothing to check, just do this step directly.

For each waypoint whose status changed (from the script's output), update its line in the PHASE file. If the file uses status sub-sections, move the waypoint under the matching sub-section (omit any that would be empty); otherwise leave it in place. Update the checkbox and trailing annotation:

| Status                              | Checkbox | Trailing annotation |
|-------------------------------------|----------|---------------------|
| `done`                              | `- [x]`  | none                |
| `blocked`                           | `- [ ]`  | `_(blocked: depends on {comma-separated dependsOn IDs})_` |
| `paused`                            | `- [ ]`  | `_(paused: reconvene {gateId})_` |
| `deferred` (out of this phase)      | `- [ ]`  | `_(deferred to a later phase)_` |
| `deferred` (tier-gated, this phase) | `- [ ]`  | `_(deferred: {gateId}, and every {tier} milestone)_` on the tier's entry waypoint; `_(deferred: follows {ID})_` on each waypoint chained behind it |
| `todo` with dependencies (all done) | `- [ ]`  | `_(depends on {IDs})_` |
| `todo` with empty `dependsOn`       | `- [ ]`  | none                |
| `out_of_scope`                      | `- [ ]`  | left as authored (terminal) |

Line format: `- [ ] **{ID}**: {description}` + annotation. Indented `- Note:` sub-bullets stay attached to their waypoint and are never moved. Do not reorder waypoints: they stay in milestone/category/sequence order.

Soft edges have no annotation of their own: they're carried entirely by the Mermaid diagram (step 5), never by a checkbox-line annotation.

### 5. Regenerate the Mermaid dependency diagram

Replace the entire fenced `mermaid` block under `## Dependency Diagram` with the output of:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py graph --mermaid --direction LR
```

Wholesale replacement: never line-edit class lists or recolour by hand. The generated block carries the canonical classDefs, every edge under the terminal milestone convention, and correct `class` statements, so the diagram cannot drift from the JSON. (A legacy diagram that used the `open` class or old hexes is fixed by this same replacement.) `softDependsOn` entries render as dotted edges (`X -.-> Y`) in this same output: never hand-add a dotted edge afterwards; it authors as data or it gets wiped by the next reconcile.

### 6. Keep the overview in sync

The overview is `ROADBOOK_OVERVIEW.md`, or `ROADMAP_OVERVIEW.md` in a project that predates 3.0.0. A pure status update does not change the waypoint total, so the header count usually holds. If it changed (after an add/remove), update the header `**N waypoints across M milestones.**` (`**N tasks across M milestones.**` in an overview written before 3.0.0; keep whichever word it already uses); get the number from `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py stats`. Do not rewrite the prose narrative.

See step 4's note on running this check as a parallel read-only agent alongside the PHASE-file sync when there's enough changed to justify it; the write here still happens sequentially, after both proposals are in hand.

### 7. Validate and report

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py validate`; it must report clean. Then report each `{ID}: old → new` status change grouped by milestone, whether the diagram block was regenerated, whether the chart was refreshed, the overview count if it changed and the end dates written in step 3b (count, and how many were first-seen or uncommitted). On a reconcile run, also restate the Step 0 proposal outcome (what was approved and applied, what was left unconfirmed, any reverse drift) and the commit SHA to use as next time's "last reconciled at" marker.

---

## Notes

- roadbook.json is the source of truth; when it and the PHASE file disagree, recompute from roadbook.json.
- The recompute (Steps 2–7) is mechanical: never infer status from descriptions, external context or likelihood of completion outside Step 0. A gate clears by a deliberate edit (removing the gate ID from `dependsOn` and its `blocks[]`), never by casual judgement.
- Step 0 is the one sanctioned exception: codebase-inferred `done` calls and blocker-edge removals, always evidence-backed and always confirmed before Step 2 writes them. It is opt-in: only runs on a reconcile request, never silently.
- `done` and `out_of_scope` are terminal; root-seeded parked waypoints are held as authored (details in the conventions reference). Step 0 never re-opens or flips these; reverse drift is reported and never corrected automatically.
- "In progress" is a trail (`claim` / `release` in step 2), never a seventh status: never write `"status": "in_progress"`.
- Never parallelise steps 3, 5 or 7: those are direct `roadbook.py` invocations, and the script is the deterministic source of truth for their output. Parallel subagents belong only in step 0's per-candidate search and steps 4/6's read-only diff-and-propose passes, never around the script itself.
