---
name: "Roadmap: Add Task"
description: "{{ 𝛀𝛀𝛀 }} Add a task to a rich-format project roadmap with correct ID, dependency wiring, and graph integrity — ID assignment, status computation, dependency edges in both directions, and no unconnected islands."
when_to_use: "Whenever the user wants to add a task, feature, or work item to a roadmap — even phrased as 'add this to the roadmap', 'put this in the plan', or 'track this as a task'."
model: opus
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Edit", "Bash(python3:*)"]
argument-hint: [task description (optional)]
---

# Roadmap Task Adder

Adds a well-formed task to an existing rich-format roadmap. The job is not appending a line — it is placing the task correctly in the dependency graph, wiring its relationships in **both** artefacts (`.claude/roadmaps.json` and the PHASE file it names), and leaving the roadmap coherent.

Shared conventions: `~/.claude/library/references/roadmap-conventions.md`. The CLI is `python3 "$HOME"/.claude/library/scripts/roadmap.py`.

---

## Step 1 — Locate the roadmap and check the format

Run `python3 "$HOME"/.claude/library/scripts/roadmap.py detect`. Exit **3** = old simple format — **stop and tell the user to run `roadmap-migrate` first**. Exit **2** = could not locate/parse — ask the user for the path. Only proceed on exit 0.

Read the full `roadmaps.json` and the active phase's PHASE file before adding — you need the existing task graph, milestone IDs, gates, and categories.

---

## Step 2 — Understand what to add

Extract: **description**; **milestone** (which milestone — ask if unclear); **category** (2–3 letter prefix, reuse an existing one in that milestone where it fits); **dependencies** (what must be done first; what it unblocks); **assignee** (ask the user directly — never infer it from the description, the git author, the category owner, or who is running this skill; leave it unset if the user doesn't say). Ask before proceeding if any is ambiguous — a badly placed task is worse than a delayed one.

---

## Step 3 — Assign a task ID

`{MilestoneNum}{Category}.{Seq}` — find the highest sequence in that category and use `next = highest + 1`. Sub-tasks: alpha suffix (`2TI.15a`). **Never reuse an ID**, even a removed one.

---

## Step 4 — Identify dependencies

**Incoming** (`dependsOn`): tasks this new task requires. An entry may be a **task ID**, a **milestone ID** (`M1` — resolves done only when all its tasks are done), or an **external gate ID** (from `externalGates`). If a gate is an incoming dependency, the gate's `blocks[]` must gain this task ID (parity).

**Outgoing**: existing tasks that this new task should now block — add the new ID to their `dependsOn` (and mirror any gate parity). Completing this task may change those tasks' computed status (the recompute handles that).

**Soft (`softDependsOn`):** an optional, best-effort link worth drawing but not worth blocking on — ask if the relationship is a real dependency or a soft one before defaulting to `dependsOn`. Renders dotted, imposes no status, no cycle constraint (see conventions reference for direction).

---

## Step 5 — Graph integrity checks (before writing)

**Orphan check.** A task with no dependency edges in or out is orphaned. Warn (`"This task has no connections to the existing graph — intentional?"`), suggest the most plausible connection, and proceed on the user's call. Some tasks genuinely stand alone.

**Childless check.** If nothing depends on the new task but its nature clearly unlocks future work, create a placeholder child in the appropriate milestone: `- [ ] **{NewID}** — {unlocked capability} _(blocked — depends on {NewTaskID})_`, `status: "blocked"`, with the dependency edge. Skip placeholders for obviously terminal tasks (deploy, final release notes). Tell the user what placeholder was created and why.

---

## Step 6 — Compute the new task's status (mechanical)

The mechanical status rule applies (see conventions reference): empty `dependsOn` → `todo`; any non-`done` dependency → `blocked`; behind a gate that `imposes: paused`/`deferred` → `paused`/`deferred`. `softDependsOn` never feeds this rule. After wiring, confirm the new task's status and any downstream changes with `python3 "$HOME"/.claude/library/scripts/roadmap.py recompute --check` (preview, no write).

---

## Step 7 — Prepare the proposal (do not edit yet)

```text
New task: {ID} — {description}
Milestone: {N} — {Milestone Name}   Status: {todo|blocked|paused|deferred}
Assignee: {name, or "unassigned"}
Dependencies (in): {IDs / milestone / gate, or "none"}
Dependencies (out): {task IDs this gets added to, or "none"}
Placeholder child: {ID and description, or "none"}

Graph changes:
  + roadmaps.json: new task object; edits to {existing tasks' dependsOn}; gate blocks[] updates
  + diagram: regenerated from the JSON (node {ID}; edges {list})
```

Then ask: *"Does this look right? I'll write to the roadmap on your say-so."*

---

## Step 8 — Write to both artefacts (once approved)

1. **`roadmaps.json`** — insert the task object in its milestone's `tasks[]` (field order `id, description, status, dependsOn, softDependsOn, iterative, notes, assignee`; tabs; British spelling). Include `assignee`/`softDependsOn` only when the user gave one — omit them entirely otherwise, exactly like `notes`. Update any existing tasks' `dependsOn`. Update any gate's `blocks[]` for parity. Add the placeholder task if any.
2. **PHASE file** — add the task line under its milestone with the status annotation (`_(blocked — depends on {IDs})_` etc.); update any existing task lines whose dependency clause changed; add the placeholder line.
3. **Mermaid diagram** — replace the entire fenced `mermaid` block with the output of `python3 "$HOME"/.claude/library/scripts/roadmap.py graph --mermaid --direction LR`. Never hand-edit edges, sinks or class lines — the generator recomputes milestone sinks (including any former sink displaced by the new task) and the canonical colours.
4. **`ROADMAP_OVERVIEW.md`** — the task total changed, so update `**N tasks across M milestones.**` (get N from `roadmap.py stats`).

---

## Step 9 — Validate and confirm

Run `python3 "$HOME"/.claude/library/scripts/roadmap.py validate` — it must report clean (parity, acyclicity, status recompute). If an HTML dashboard exists (`docs/artefacts/roadmap-*.html`), refresh it with `roadmap.py render`. Then report: task added; status; edges added; existing tasks modified; placeholder created; any orphan warning.

---

## Conventions

- Task line: `- [ ] **{ID}** — {description}` + annotation. Completed: `- [x] **{ID}** — {description}`.
- roadmaps.json is the source of truth; the PHASE file and overview are projections.
- Everything else (statuses, colours, graph/edge rules, formatting): `~/.claude/library/references/roadmap-conventions.md`.
