---
name: "Start Roadbook"
description: "Start a project roadbook (the plan goblin-scout keeps) in the rich phase-array format: roadbook.json as source of truth plus a PHASE waypoint list (waypoints are tasks) and prose overview"
when_to_use: "When a project has no roadbook yet, or an existing simple-style one needs superseding with a new phase built from scratch (for converting an old single-file roadmap, use goblin-scout:rebind-roadbook instead)."
model: fable
effort: high
metadata:
  glyph: ᚠ
  family: scout
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Write", "Bash(python3:*)"]
arguments: ["phase"]
argument-hint: "[phase name (optional, e.g. PHASE_1)]"
---

Start a roadbook as three synchronised artefacts:

- `.claude/roadbook.json`: machine-readable **source of truth**, an **array of phase objects** each `{name, path, archived?, externalGates, milestones}`. The active phase is the entry without `archived: true`; archived entries are retained as historical record.
- `docs/roadbook/{PHASE}.md`: human-readable waypoint list and dependency diagram (a projection).
- `docs/reports/ROADBOOK_OVERVIEW.md`: prose overview (a projection).

When creating a new phase alongside existing ones, append a new element and mark the superseded phase `"archived": true`.

Shared conventions (status vocabulary, colour table, graph rules, formatting) live in `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`; read it before writing anything. The CLI is `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py`.

## Behaviour

| Codebase Context   | Arguments Passed | Action |
|--------------------|------------------|--------|
| No roadbook yet    | 0                | Propose a phase name drawn from the project's goal and confirm it |
| N/A                | 1                | Create the roadbook/phase named in the argument |
| A roadbook exists  | 0                | Ask the user which phase to create or if starting a new phase |

## Steps

### 1. Determine scope, context and format

- Check whether `.claude/roadbook.json` exists (or `.claude/roadmaps.json`, its name before 3.0.0) and whether `docs/roadbook/` (or `docs/roadmaps/` in an older project) holds projections.
- If `$ARGUMENTS` is given, use it as the phase name (e.g. `PHASE_2`). If no arguments and no existing roadbook, propose a phase name drawn from the project's goal and confirm it; never default to a bare `PHASE_1`. If no arguments but a roadbook exists, ask the user to clarify intent.
- **If a roadbook already exists, check its format first**: run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py detect`. Exit **3** = old simple format: **stop and tell the user to run the `goblin-scout:rebind-roadbook` skill first**, so the new phase is appended to a consistent phase array. Exit **2** = could not locate/parse: ask the user for the path. Only proceed on exit 0 (or when no roadbook exists yet).

### 2. Gather project context

Read what is available to understand the project: `README.md`, `CLAUDE.md`, `docs/` (architecture, proposals, ADRs) and any existing projections in `docs/roadbook/` (or `docs/roadmaps/`).

### 3. Elicit the work; let the structure emerge

Feature first, structure second: milestones reveal themselves as the conversation groups the work, so never open with "how many milestones?". Ask targeted questions (2–3 per round, not a long form):

- **The work:** what must exist by the end of this phase? What's frustrating enough to fix, and what does each piece unlock?
- **Grouping (proposed, not demanded):** once the features are on the table, propose a milestone grouping (typically 3–5, each with a goal and completion criterion) and 2–3 letter category prefixes (e.g. `EV` = evaluation, `IN` = ingestion). The user corrects a concrete proposal rather than designing structure cold.
- **Dependencies:** which groups are sequential vs parallel; any known external blockers or prerequisites.
- **Scouts (optional):** if the user wants to attribute waypoints to people up front, ask who owns what. Never infer an assignee from category, milestone or anything else; leave it unset for any waypoint the user doesn't name an owner for.

For a big batch of half-formed ideas, `goblin-scout:plan-expedition` is the deeper feature interview; its approved expedition can seed this step's grouping.

### 4. Assign waypoint IDs

Format: `{MilestoneNum}{Category}.{Seq}`, e.g. `1EV.1`, `3IN.6`. Sub-waypoints use an alpha suffix: `3IN.2a`. Never reuse an ID; number sequentially within each category; new waypoints append (never renumber).

### 5. Compute initial statuses (mechanical)

The mechanical status rule from the conventions reference applies: empty `dependsOn` → `todo`; any non-`done` dependency → at least `blocked`, escalating under `deferred > paused > blocked > todo` when a dependency is itself parked. No waypoint starts `done` unless the user says the work is already complete. A root-seeded `paused`/`deferred` (empty `dependsOn`) is only for waypoints parked behind a gate or a later phase from the outset. `softDependsOn` never feeds this rule.

### 6. Generate `.claude/roadbook.json`

The top level is an **array of phase objects**. Append + archive the superseded phase if others exist; otherwise write a one-element array. Tabs for indentation, British spelling.

```json
[
  {
    "name": "{Phase Name}",
    "path": "docs/roadbook/{PHASE}.md",
    "archived": false,
    "externalGates": [],
    "milestones": [
      {
        "id": "M{N}",
        "name": "{Milestone Name}",
        "goal": "{One-sentence objective}",
        "tasks": [
          { "id": "{ID}", "description": "{Waypoint description}", "status": "todo", "dependsOn": [] }
        ]
      }
    ]
  }
]
```

- Waypoint and gate field order follows the conventions reference (a new waypoint never carries `started`: trails come from starting work). Include `softDependsOn`/`softMilestone`/`notes`/`iterative`/`assignee` only when meaningful; `assignee` is free-text with no roster, and must never be guessed.
- **External gates** (`externalGates`, per phase, beside `milestones`) model things outside the team's control that block work: `{id, name, status:"external", imposes?, blocks[], notes?}`. `imposes` (default `blocked`; may be `paused` or `deferred`) is the status the gate forces on its blocked children; `blocks[]` is the reverse edge: every waypoint ID that lists this gate in its `dependsOn`. A gate ID can appear in a waypoint's `dependsOn`.
- A `dependsOn` entry may be a **milestone ID** (`M1`, `MP`…): it resolves `done` only when every waypoint in that milestone is `done`.
- The `iterative: true` flag marks a waypoint that loops to convergence: descriptive only, never a cyclic `dependsOn`.
- A `softDependsOn` entry authors an optional, best-effort link that renders dotted in the diagram (`X -.-> Y`) but imposes no status, no cycle constraint and no sink effect (full semantics in the conventions reference). Use it for relationships worth showing but not worth blocking on; never hand-draw a dotted line into the generated diagram instead.

### 7. Generate `docs/roadbook/{PHASE}.md`

````markdown
# {Project Name} {Phase} Roadbook

{1–3 sentence intro.}

**Critical path:** `{key IDs in sequence}`; {brief explanation}.

---

## Milestone 1: {Name}

**Goal:** {Milestone objective}

- [ ] **{ID}**: {description}
- [ ] **{ID}**: {description} _(depends on {ID})_
- [ ] **{ID}**: {description} _(blocked: depends on {ID}, {ID})_
  - Note: {optional note}

---

## Dependency Diagram

```mermaid
{output of roadbook.py graph --mermaid}
```
````

Waypoint line annotations follow the conventions reference (none / `_(depends on {IDs})_` / `_(blocked: depends on {IDs})_` / `_(paused: reconvene {gateId})_` / `_(deferred to a later phase)_` / the tier-gated `_(deferred: {gateId}, and every {tier} milestone)_` and `_(deferred: follows {ID})_` forms; see Tiers in the conventions reference).

**The diagram is generated, never hand-written.** Once the JSON is written, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py graph --mermaid --direction LR
```

and paste the output verbatim into the fenced `mermaid` block. It emits the classDefs (canonical status colours), nodes, edges (terminal milestone convention) and `class` statements in the right order. Do not add, remove or recolour lines by hand.

### 8. Generate `docs/reports/ROADBOOK_OVERVIEW.md`

```markdown
# {Project} {Phase}: Roadbook Overview

**{N} waypoints across {M} milestones.** Files: `.claude/roadbook.json` (machine-readable), `docs/roadbook/{PHASE}.md` (full waypoint list with Mermaid dependency diagram).

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

The header waypoint count must match `roadbook.json`. Get it from `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py stats` rather than counting by hand.

### 9. Validate, confirm and report

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py validate`; it must report clean (dependsOn/blocks parity, acyclicity, status recompute). Fix any discrepancy before finishing.
2. Report the three paths created, the milestone and waypoint counts (from `roadbook.py stats`) and the status breakdown.
3. Note any assumptions or areas needing user refinement.

---

## Conventions

- ID format `{MilestoneNum}{Category}.{Seq}`; never reuse IDs.
- roadbook.json is the source of truth; the PHASE file and overview are projections.
- Everything else (statuses, colours, graph rules, formatting): `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`.

These roadbooks are tended by `goblin-scout:tend-roadbook` (status synchronisation) and `goblin-scout:add-waypoints` (adding waypoints, or a single new milestone via its `m` mode). Old single-file roadmaps are converted by `goblin-scout:rebind-roadbook`; the chart (the HTML page) comes from `goblin-scout:unroll-chart` (`roadbook.py render`).

The two skills split by scope: this skill (`goblin-scout:start-roadbook`) builds an entire phase from scratch, multiple milestones at once, when none exists yet or an old one is being superseded wholesale. `goblin-scout:add-waypoints m` appends exactly one milestone to a phase that already exists. Reach for this skill only in the "no roadbook yet" / "starting a new phase" cases in the Behaviour table above; a single new milestone inside a live phase is the other skill's job.
