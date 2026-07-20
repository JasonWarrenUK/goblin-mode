---
name: "Roadmap: Create"
description: "{{ 𝛀𝛀𝛀 }} Create a project roadmap in the rich phase-array format — roadmaps.json as source of truth plus a PHASE task list and prose overview"
when_to_use: "When a project has no roadmap yet, or an existing simple-style one needs superseding with a new phase built from scratch (for converting an old roadmap, use roadmap-migrate instead)."
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

Shared conventions (status vocabulary, colour table, graph rules, formatting) live in `~/.claude/library/references/roadmap-conventions.md` — read it before writing anything. The CLI is `python3 "$HOME"/.claude/library/scripts/roadmap.py`.

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
- **If a roadmap already exists, check its format first** — run `python3 "$HOME"/.claude/library/scripts/roadmap.py detect`. Exit **3** = old simple format: **stop and tell the user to run the `roadmap-migrate` skill first**, so the new phase is appended to a consistent phase array. Exit **2** = could not locate/parse: ask the user for the path. Only proceed on exit 0 (or when no roadmap exists yet).

### 2. Gather project context

Read what is available to understand the project: `README.md`, `CLAUDE.md`, `docs/` (architecture, proposals, ADRs), and any existing roadmaps in `docs/roadmaps/`.

### 3. Elicit milestones, categories, and dependencies

Ask targeted questions before generating anything (2–3 per round, not a long form):

- **Milestones:** how many (typical 3–5)? Each milestone's goal and its completion criterion.
- **Categories:** the logical groupings within each milestone. Use 2–3 letter prefixes (e.g. `EV` = evaluation, `IN` = ingestion, `SR` = search).
- **Dependencies:** which milestones are sequential vs parallel; any known external blockers or prerequisites.
- **Assignees (optional):** if the user wants to attribute tasks to people up front, ask who owns what. Never infer an assignee from category, milestone, or anything else — leave it unset for any task the user doesn't name an owner for.

### 4. Assign task IDs

Format: `{MilestoneNum}{Category}.{Seq}` — e.g. `1EV.1`, `3IN.6`. Sub-tasks use an alpha suffix: `3IN.2a`. Never reuse an ID; number sequentially within each category; new tasks append (never renumber).

### 5. Compute initial statuses (mechanical)

The mechanical status rule from the conventions reference applies: empty `dependsOn` → `todo`; any non-`done` dependency → `blocked`. No task starts `done` unless the user says the work is already complete. `paused`/`deferred` are only for tasks parked behind a gate or a later phase. `softDependsOn` never feeds this rule.

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

- Field order — tasks: `id, description, status, dependsOn, softDependsOn, iterative, notes, assignee`; gates: `id, name, status, imposes, blocks, notes`. Include `softDependsOn`/`notes`/`iterative`/`assignee` only when meaningful — `assignee` is free-text with no roster, and must never be guessed.
- **External gates** (`externalGates`, per phase, beside `milestones`) model things outside the team's control that block work: `{id, name, status:"external", imposes?, blocks[], notes?}`. `imposes` (default `blocked`; may be `paused` or `deferred`) is the status the gate forces on its blocked children; `blocks[]` is the reverse edge — every task ID that lists this gate in its `dependsOn`. A gate ID can appear in a task's `dependsOn`.
- A `dependsOn` entry may be a **milestone ID** (`M1`, `MP`…): it resolves `done` only when every task in that milestone is `done`.
- The `iterative: true` flag marks a task that loops to convergence — descriptive only, never a cyclic `dependsOn`.
- A `softDependsOn` entry authors an optional, best-effort link that renders dotted in the diagram (`X -.-> Y`) but imposes no status, no cycle constraint, and no sink effect (full semantics in the conventions reference). Use it for relationships worth showing but not worth blocking on — never hand-draw a dotted line into the generated diagram instead.

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
{output of roadmap.py graph --mermaid}
```
````

Task line annotations follow the conventions reference (none / `_(depends on {IDs})_` / `_(blocked — depends on {IDs})_` / `_(paused — reconvene {gateId})_` / `_(deferred to a later phase)_`).

**The diagram is generated, never hand-written.** Once the JSON is written, run:

```bash
python3 "$HOME"/.claude/library/scripts/roadmap.py graph --mermaid --direction LR
```

and paste the output verbatim into the fenced `mermaid` block. It emits the classDefs (canonical status colours), nodes, edges (terminal milestone convention) and `class` statements in the right order. Do not add, remove or recolour lines by hand.

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

The header task count must match `roadmaps.json`. Get it from `python3 "$HOME"/.claude/library/scripts/roadmap.py stats` rather than counting by hand.

### 9. Validate, confirm, and report

1. Run `python3 "$HOME"/.claude/library/scripts/roadmap.py validate` — it must report clean (dependsOn/blocks parity, acyclicity, status recompute). Fix any discrepancy before finishing.
2. Report the three paths created, the milestone and task counts (from `roadmap.py stats`), and the status breakdown.
3. Note any assumptions or areas needing user refinement.

---

## Conventions

- ID format `{MilestoneNum}{Category}.{Seq}`; never reuse IDs.
- roadmaps.json is the source of truth; the PHASE file and overview are projections.
- Everything else (statuses, colours, graph rules, formatting): `~/.claude/library/references/roadmap-conventions.md`.

These roadmaps are maintained by `roadmap-maintain` (status synchronisation) and `roadmap-update-tasks` (adding tasks). Old simple-format roadmaps are upgraded by `roadmap-migrate`; the HTML dashboard comes from `artefact-roadmap` (`roadmap.py render`).
