---
name: roadmap-create
description: "{{ 𝛀𝛀𝛀 }} Create a project roadmap in the rich phase-array format — roadmaps.json as source of truth plus a PHASE task list and prose overview"
model: opus
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Write", "Bash(python3:*)"]
argument-hint: [phase name (optional, e.g. PHASE_1)]
---

Create a roadmap as three synchronised artefacts:

- `.claude/roadmaps.json` — machine-readable **source of truth**, an **array of phase objects** each `{name, path, archived?, externalGates, milestones}`. The active phase is the entry without `archived: true`; archived entries are retained as historical record.
- `docs/roadmaps/{PHASE}.md` — human-readable task list and dependency diagram (a projection).
- `docs/reports/ROADMAP_OVERVIEW.md` — prose overview (a projection).

When creating a new phase alongside existing ones, append a new element and mark the superseded phase `"archived": true`.

Shared scripts live in `~/.claude/library/scripts/` (invoke as `python3 ~/.claude/library/scripts/{name}.py`; use `"$HOME"/.claude/...` if `~` is not expanded).

## Behaviour

| Codebase Context  | Arguments Passed | Action                                                    |
| ----------------- | ---------------- | --------------------------------------------------------- |
| No other roadmaps | 0                | Create the first project roadmap (default `PHASE_1.md`)   |
| N/A               | 1                | Create the roadmap/phase named in the argument            |
| Roadmaps exist    | 0                | Ask the user which phase to create or if starting a new phase |

## Steps

### 1. Determine scope, context, and format

- Check if `docs/roadmaps/` exists and contains roadmaps; check if `.claude/roadmaps.json` exists.
- If `$ARGUMENTS` is given, use it as the phase name (e.g. `PHASE_2`). If no arguments and no existing roadmap, default to `PHASE_1`. If no arguments but roadmaps exist, ask the user to clarify intent.
- **If a roadmap already exists, check its format first** — run `python3 ~/.claude/library/scripts/detect_format.py`. Exit 3 means it is the old simple format (single Markdown, `<a name>` anchors, or a `{"roadmaps":[…]}` pointer registry). **Stop and tell the user to run the `roadmap-migrate` skill first**, so the new phase is appended to a consistent phase array rather than colliding with the old structure. Only proceed to append a phase once the existing roadmap is rich.

### 2. Gather project context

Read what is available to understand the project: `README.md`, `CLAUDE.md`, `docs/` (architecture, proposals, ADRs), and any existing roadmaps in `docs/roadmaps/`.

### 3. Elicit milestones, categories, and dependencies

Ask targeted questions before generating anything (2–3 per round, not a long form):

- **Milestones:** how many (typical 3–5)? Each milestone's goal and its completion criterion.
- **Categories:** the logical groupings within each milestone. Use 2–3 letter prefixes (e.g. `EV` = evaluation, `IN` = ingestion, `SR` = search).
- **Dependencies:** which milestones are sequential vs parallel; any known external blockers or prerequisites.

### 4. Assign task IDs

Format: `{MilestoneNum}{Category}.{Seq}` — e.g. `1EV.1`, `3IN.6`. Sub-tasks use an alpha suffix: `3IN.2a`. Never reuse an ID; number sequentially within each category; new tasks append (never renumber).

### 5. Compute initial statuses (mechanical)

The six statuses are `todo`, `blocked`, `paused`, `deferred`, `done`, `out_of_scope`. **There is no in-progress state.** For each task at creation:

- Empty `dependsOn` → `todo`
- Any entry in `dependsOn` not yet `done` → `blocked`

No task starts `done` unless the user says the work is already complete. `paused`/`deferred` are only for tasks parked behind a gate or a later phase (see gates below).

### 6. Generate `.claude/roadmaps.json`

The top level is an **array of phase objects**. Append + archive the superseded phase if others exist; otherwise write a one-element array. Tabs for indentation, British spelling.

```json
[
  {
    "name": "{Phase Name}",
    "path": "docs/roadmaps/{PHASE}.md",
    "archived": false,
    "externalGates": [],
    "milestones": [
      {
        "id": "M{N}",
        "name": "{Milestone Name}",
        "goal": "{One-sentence objective}",
        "tasks": [
          { "id": "{ID}", "description": "{Task description}", "status": "todo", "dependsOn": [] }
        ]
      }
    ]
  }
]
```

- Field order — tasks: `id, description, status, dependsOn, iterative, notes`; gates: `id, name, status, imposes, blocks, notes`. Include `notes`/`iterative` only when meaningful.
- **External gates** (`externalGates`, per phase, beside `milestones`) model things outside the team's control that block work: `{id, name, status:"external", imposes?, blocks[], notes?}`. `imposes` (default `blocked`; may be `paused` or `deferred`) is the status the gate forces on its blocked children; `blocks[]` is the reverse edge — every task ID that lists this gate in its `dependsOn`. A gate ID can appear in a task's `dependsOn`.
- A `dependsOn` entry may be a **milestone ID** (`M1`, `MP`…): it resolves `done` only when every task in that milestone is `done`.
- The `iterative: true` flag marks a task that loops to convergence — descriptive only, never a cyclic `dependsOn`.

### 7. Generate `docs/roadmaps/{PHASE}.md`

````markdown
# {Project Name} {Phase} Roadmap

{1–3 sentence intro.}

**Critical path:** `{key IDs in sequence}` — {brief explanation}.

---

## Milestone 1 — {Name}

**Goal:** {Milestone objective}

- [ ] **{ID}** — {description}
- [ ] **{ID}** — {description} _(depends on {ID})_
- [ ] **{ID}** — {description} _(blocked — depends on {ID}, {ID})_
  - Note: {optional note}

---

## Dependency Diagram

```mermaid
graph LR
	classDef done fill:#c3e6cb,stroke:#1e7e34
	classDef open fill:#d4edda,stroke:#28a745
	classDef blocked fill:#f8d7da,stroke:#dc3545
	classDef paused fill:#e2e3f3,stroke:#5a6ab0,stroke-dasharray:4 3
	classDef deferred fill:#e2e3e5,stroke:#6c757d,stroke-dasharray:2 4,font-style:italic
	classDef external fill:#fff3cd,stroke:#d39e00,stroke-dasharray:4 3,font-style:italic
	classDef mile fill:#cce5ff,stroke:#004085,font-weight:bold

	M1[M1: {Name}]:::mile
	M2[M2: {Name}]:::mile

	%% Milestone 1
	{dep} --> {task}
	{sink} --> M1

	%% Milestone 2
	M1 --> {taskThatDependsOnM1}
	...

	class {todo IDs ascending} open
	class {blocked IDs ascending} blocked
	class {paused IDs ascending} paused
	class {deferred IDs ascending} deferred
```
````

**Task annotation rules:** no annotation if `dependsOn` is empty; `_(depends on {IDs})_` if all deps are done (task is `todo`); `_(blocked — depends on {IDs})_` if any dep is not done; `_(paused — reconvene {gateId})_` / `_(deferred to a later phase)_` for parked tasks.

**Mermaid rules:**

- `graph LR`, classDefs **immediately after** the `graph LR` line (Mermaid rejects `classDef` before the graph-type declaration).
- One `M{N}[M{N}: {Name}]:::mile` node per milestone; one `{gateId}[…]:::external` node per gate.
- **Milestone nodes are TERMINAL** (the house convention): a milestone's *sink* tasks point INTO its node. Compute sinks as *tasks in the milestone that no other task in the same milestone depends on*, and emit `{sink} --> M{N}` for each. The node reads "these tasks complete the milestone".
- **Milestone-as-dependency:** if a task lists a milestone ID in its `dependsOn`, emit `M{N} --> {task}` (the node gates the dependent). This is the only place `M{N} -->` appears as a source.
- Never emit an initial `M{N} --> {firstTask}` entry edge.
- Task→task deps: `{dep} --> {task}`. Soft/iterative loops: `{A} -.->|iterate| {B}`.
- End with explicit `class {IDs} {status}` statements (IDs ascending), never inline `:::open` on task nodes, and **no** `<a name>` anchors or `#m{N}-*` patterns.

You can generate the diagram deterministically instead of by hand once the JSON is written: `python3 ~/.claude/library/scripts/roadmap_graph.py` emits the nodes and edges (including the terminal milestone edges) as JSON.

### 8. Generate `docs/reports/ROADMAP_OVERVIEW.md`

```markdown
# {Project} {Phase}: Roadmap Overview

**{N} tasks across {M} milestones.** Files: `.claude/roadmaps.json` (machine-readable), `docs/roadmaps/{PHASE}.md` (full task list with Mermaid dependency diagram).

> {Rescope/context note if relevant}

---

## What we're building
{2–3 paragraphs on the key deliverables and the reasoning behind the phase structure.}

## Milestone sequence and the reasoning behind it
{One paragraph per milestone.}

## Decisions that shaped the structure
{Key decisions that explain non-obvious choices.}

## External blockers (flag early)
{Dependencies on external parties, unconfirmed decisions, etc.}
```

The header task count must match `roadmaps.json`. Get it from `python3 ~/.claude/library/scripts/roadmap_stats.py` rather than counting by hand.

### 9. Validate, confirm, and report

1. Run `python3 ~/.claude/library/scripts/validate_roadmap.py` — it must report clean (dependsOn/blocks parity, acyclicity, status recompute). Fix any discrepancy before finishing.
2. Report the three paths created, the milestone and task counts (from `roadmap_stats.py`), and the status breakdown.
3. Note any assumptions or areas needing user refinement.

---

## Conventions

- ID format `{MilestoneNum}{Category}.{Seq}`; never reuse IDs.
- roadmaps.json is the source of truth; the PHASE file and overview are projections.
- Tabs not spaces; British spelling (organise, behaviour, synchronise).
- Status rule is mechanical: empty deps → `todo`; any non-done dep → `blocked`. No in-progress state.
- Milestone nodes render terminal (sinks point in; milestone-deps point out).

These roadmaps are maintained by `roadmap-maintain` (status synchronisation) and `roadmap-update-tasks` (adding tasks). Old simple-format roadmaps are upgraded by `roadmap-migrate`.
