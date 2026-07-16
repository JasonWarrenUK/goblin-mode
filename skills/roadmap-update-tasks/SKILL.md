---
name: roadmap-update-tasks
description: "{{ 𝛀𝛀𝛀 }} Add a task to a rich-format project roadmap with correct ID, dependency wiring, and graph integrity. Use this whenever the user wants to add a task, feature, or work item to a roadmap — even if they just say 'add this to the roadmap', 'put this in the plan', or 'track this as a task'. Handles ID assignment, status computation, dependency edges in both directions, and ensures no task is left an unconnected island."
model: opus
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Bash(python3:*)"]
argument-hint: [task description (optional)]
---

# Roadmap Task Adder

Adds a well-formed task to an existing rich-format roadmap. The job is not appending a line — it is placing the task correctly in the dependency graph, wiring its relationships in **both** artefacts (`.claude/roadmaps.json` and the PHASE file it names), and leaving the roadmap coherent.

The roadmap is three synchronised artefacts: `.claude/roadmaps.json` (source of truth, an array of phase objects; operate on the active non-`archived` entry), `docs/roadmaps/{PHASE}.md` (task list + `graph LR` diagram), and `docs/reports/ROADMAP_OVERVIEW.md` (prose; header count). Shared scripts live in `~/.claude/library/scripts/`.

---

## Step 1 — Locate the roadmap and check the format

Find `.claude/roadmaps.json` (or ask if several roadmaps exist). Run `python3 ~/.claude/library/scripts/detect_format.py`; exit 3 = old simple format — **stop and tell the user to run `roadmap-migrate` first**. Only proceed when rich (exit 0).

Read the full `roadmaps.json` and the active phase's PHASE file before adding — you need the existing task graph, milestone IDs, gates, and categories.

---

## Step 2 — Understand what to add

Extract: **description**; **milestone** (which milestone — ask if unclear); **category** (2–3 letter prefix, reuse an existing one in that milestone where it fits); **dependencies** (what must be done first; what it unblocks). Ask before proceeding if any is ambiguous — a badly placed task is worse than a delayed one.

---

## Step 3 — Assign a task ID

`{MilestoneNum}{Category}.{Seq}` — find the highest sequence in that category and use `next = highest + 1`. Sub-tasks: alpha suffix (`2TI.15a`). **Never reuse an ID**, even a removed one.

---

## Step 4 — Identify dependencies

**Incoming** (`dependsOn`): tasks this new task requires. An entry may be a **task ID**, a **milestone ID** (`M1` — resolves done only when all its tasks are done), or an **external gate ID** (from `externalGates`). If a gate is an incoming dependency, the gate's `blocks[]` must gain this task ID (parity).

**Outgoing**: existing tasks that this new task should now block — add the new ID to their `dependsOn` (and mirror any gate parity). Completing this task may change those tasks' computed status (the recompute handles that).

---

## Step 5 — Graph integrity checks (before writing)

**Orphan check.** A task with no dependency edges in or out is orphaned. Warn (`"This task has no connections to the existing graph — intentional?"`), suggest the most plausible connection, and proceed on the user's call. Some tasks genuinely stand alone.

**Childless check.** If nothing depends on the new task but its nature clearly unlocks future work, create a placeholder child in the appropriate milestone: `- [ ] **{NewID}** — {unlocked capability} _(blocked — depends on {NewTaskID})_`, `status: "blocked"`, with the dependency edge. Skip placeholders for obviously terminal tasks (deploy, final release notes). Tell the user what placeholder was created and why.

---

## Step 6 — Compute the new task's status (mechanical)

Six statuses, no in-progress. Empty `dependsOn` → `todo`; any non-`done` dependency → `blocked`; behind a gate that `imposes: paused`/`deferred` → `paused`/`deferred`. After wiring, you can confirm the new task's status and any downstream changes with `python3 ~/.claude/library/scripts/recompute_roadmap.py --check` (preview, no write).

---

## Step 7 — Prepare the proposal (do not edit yet)

```text
New task: {ID} — {description}
Milestone: {N} — {Milestone Name}   Status: {todo|blocked|paused|deferred}
Dependencies (in): {IDs / milestone / gate, or "none"}
Dependencies (out): {task IDs this gets added to, or "none"}
Placeholder child: {ID and description, or "none"}

Graph changes:
  + roadmaps.json: new task object; edits to {existing tasks' dependsOn}; gate blocks[] updates
  + diagram: node {ID}; edges {list}; if this is a milestone sink, {ID} --> M{N}
```

Then ask: *"Does this look right? I'll write to the roadmap on your say-so."*

---

## Step 8 — Write to both artefacts (once approved)

1. **`roadmaps.json`** — insert the task object in its milestone's `tasks[]` (field order `id, description, status, dependsOn, iterative, notes`; tabs; British spelling). Update any existing tasks' `dependsOn`. Update any gate's `blocks[]` for parity. Add the placeholder task if any.
2. **PHASE file** — add the task line under its milestone with the status annotation (`_(blocked — depends on {IDs})_` etc.); update any existing task lines whose dependency clause changed; add the placeholder line.
3. **Mermaid diagram** — add the node's edges:
   - task→task deps: `{dep} --> {ID}`;
   - milestone-as-dependency: `M{N} --> {ID}` if the new task depends on a whole milestone;
   - **terminal milestone edge:** if the new task is now a *sink* of its milestone (nothing else in that milestone depends on it), emit `{ID} --> M{N}`, and if it now depends on a former sink, remove that former sink's `--> M{N}` edge if the former sink is no longer a sink. (Recompute sinks for the affected milestone; `roadmap_graph.py` gives the authoritative edge set.)
   - Add the new ID to the correct `class {IDs} {status}` line (ascending order). Never inline `:::open`.
4. **`ROADMAP_OVERVIEW.md`** — the task total changed, so update `**N tasks across M milestones.**` (get N from `roadmap_stats.py`).

---

## Step 9 — Validate and confirm

Run `python3 ~/.claude/library/scripts/validate_roadmap.py` — it must report clean (parity, acyclicity, status recompute). Then report: task added; status; edges added; existing tasks modified; placeholder created; any orphan warning.

---

## Conventions

- Task line: `- [ ] **{ID}** — {description}` + annotation. Completed: `- [x] **{ID}** — {description}`.
- Edges: `{A} --> {B}` (A completes before B). Milestone nodes are **terminal** — sinks point in (`{sink} --> M{N}`), milestone-deps point out (`M{N} --> x`); never an initial `M{N} --> {firstTask}` edge.
- classDefs come immediately after `graph LR`; explicit `class {IDs} {status}` statements, never inline.
- Tabs not spaces; British spelling. roadmaps.json is the source of truth; the PHASE file and overview are projections.
