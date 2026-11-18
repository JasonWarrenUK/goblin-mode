---
name: "Rebind Roadbook"
description: "Rebind an older plan as a roadbook (goblin-scout's dependency graph of waypoints, which are tasks): move a 2.x roadmap plugin's .claude/roadmaps.json to .claude/roadbook.json now, on request move its chart, projections and overview to the roadbook's default names in one commit, or convert an old single-Markdown roadmap (four statuses, <a name> anchors, a roadmaps.json pointer registry) into the rich phase-array format."
when_to_use: "When a project still has the old single-Markdown-file roadmap format and needs converting before goblin-scout:start-roadbook or goblin-scout:add-waypoints can be used on it; when the user wants a 2.x project's .claude/roadmaps.json moved to .claude/roadbook.json without waiting for the first write; or when they ask for the chart, projections and overview to take the roadbook's names."
model: sonnet
effort: high
metadata:
  glyph: ᛊ
  family: scout
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "Grep", "Write", "Bash(python3:*)", "Bash(git status:*)", "Bash(git stash:*)", "Bash(git add:*)", "Bash(git commit:*)"]
arguments: ["roadbook"]
argument-hint: "[roadbook path or name (optional)] [outputs]"
---

Bring an older plan onto goblin-scout's **roadbook**. Three jobs, picked by what the project holds and what the user asked for:

| The project holds | Job |
|---|---|
| a phase-array `.claude/roadmaps.json` from the 2.x roadmap plugin | **A. Move the file** (the first write does this anyway; this does it now) |
| a phase-array roadbook, and the user asked for the outputs to take the new names (`outputs` in `$ARGUMENTS`, or said so) | **B. Move the outputs** |
| an old single-Markdown roadmap | **C. Convert the old format** |

Each is user-initiated only (never model-triggered).

Shared conventions: `${CLAUDE_PLUGIN_ROOT}/references/roadbook-conventions.md`. The CLI is `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py`.

## 0. Locate and detect

Resolve the roadbook: `$ARGUMENTS` path/name, else `.claude/roadbook.json`, else `.claude/roadmaps.json`, else a `docs/roadmaps/` scan. Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py detect`:

- Exit **3**: old single-Markdown format; go to **C**.
- Exit **0**: phase-array format. If the file is `roadmaps.json`, or the user asked for the outputs, go to **A** or **B**; otherwise tell the user there is nothing to rebind and stop.
- Exit **2**: could not locate; ask for the path.

Show `git status` and advise the user to commit or stash first: every job here rewrites or moves tracked files. Do not proceed with a dirty tree unless the user says so.

## A. Move the file

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py rebind --dry-run` and show the user the move. On their go-ahead run it without `--dry-run`. It does what goblin-scout 3.0.0's first write would: moves `.claude/roadmaps.json` (and `roadmaps.local.json` beside it) to the roadbook names, rewrites no value, pins each phase's chart to the path a 2.x plugin rendered it to, and stamps the live phase so a 2.x plugin refuses the file. Relay its notice line, and any note that a moved local file is no longer ignored by git.

Commit the move on its own: `git add .claude` and `git commit -m "chore(roadbook): move roadmaps.json to roadbook.json"`. If the user also wants the outputs moved, carry on into **B** before committing, so the whole rebind is one commit.

## B. Move the outputs (on request only)

A 2.x project keeps its chart, projections and overview where they were: the migration pins them. This job moves them to the names a new roadbook gets, only when the user asks:

| Output | 2.x default | Roadbook default |
|---|---|---|
| the chart | `docs/artefacts/roadmap-{slug}.html` | `docs/artefacts/chart-{slug}.html` |
| a phase's projection | `docs/roadmaps/{PHASE}.md` | `docs/roadbook/{PHASE}.md` |
| the prose overview | `docs/reports/ROADMAP_OVERVIEW.md` | `docs/reports/ROADBOOK_OVERVIEW.md` |

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py rebind --outputs --dry-run` and show the user every move it lists. A path the project chose for itself (an `artefact` or `path` outside those defaults) is left alone and does not appear. If a target already exists the CLI refuses before moving anything; relay that and stop.
2. On the user's go-ahead run it without `--dry-run`. It moves the roadbook file too when it is still `roadmaps.json`, clears the pinned `artefact` so the chart takes the new default, rewrites each default `path`, and moves the files with `git mv` where git tracks them.
3. Search the project for links to the old paths (`grep -rn "docs/roadmaps/\|ROADMAP_OVERVIEW\|artefacts/roadmap-"`, skipping `.git`) and show the user each hit. Update a link only where the user agrees; a dated record (a changelog entry, an old report) keeps its words.
4. Commit everything in one commit: `git add -A .claude docs` plus any link the user agreed to update, then `git commit -m "chore(roadbook): move the chart, projections and overview to the roadbook's names"`.

## C. Convert the old format

An old **simple-format** roadmap becomes the **rich phase-array format** the other goblin-scout skills expect. This is a one-way structural rewrite of the source of truth; the other skills detect the old format and point the user here.

**Old (simple) format:** a single `docs/roadmaps/{name}.md` is the source of truth, with `<a name="m{N}">` anchors, four sections (In Progress / To Do / Blocked / Completed), `- [ ]`/`- [x]` checkboxes, prose `**depends on {IDs}**` clauses, a `graph TD` diagram; `.claude/roadmaps.json` is a `{"roadmaps":[{name,path}]}` pointer registry.

**Rich format:** `.claude/roadbook.json` is the source of truth: an **array of phase objects** `{name, path, archived?, externalGates, milestones}` with six statuses (`todo, blocked, paused, deferred, done, out_of_scope`), external gates, milestone and gate dependencies and a mechanical status recompute. The phase's projection (its `path`) and `docs/reports/ROADBOOK_OVERVIEW.md` are projections.

### C1. Parse the old Markdown

Read the `.md`. For each `<a name="m{N}">` milestone block, capture:

- Milestone number and name; the goal (`> **Goal:**` / `> [!IMPORTANT]` block).
- Waypoints in each section (`m{N}-doing`, `m{N}-todo`, `m{N}-blocked`, `m{N}-done`): the ID, the description and any `**depends on {IDs}**` clause. Note which section each came from (`doing`/`todo`/`blocked`/`done`).

Also parse the aggregated `graph TD` diagram for `{A} --> {B}` edges; merge these into each waypoint's dependency set, so a dependency drawn only in the diagram (never written in prose) is kept.

### C2. Derive milestones, waypoints and dependencies

Build milestone objects `{id: "M{N}", name, goal, tasks:[…]}`. Each waypoint: `{id, description, dependsOn:[…]}` with `dependsOn` the union of its prose depends-clause and its incoming Mermaid edges. The old format has no external gates, so `externalGates: []`. Preserve any `- Note:` sub-bullets as a waypoint's `notes` field.

### C3. Assign statuses (seed, then recompute)

Seed each waypoint's status from its old section, then let the recompute derive the rest:

- **Completed** (`- [x]`): `done` (terminal seed, kept).
- **In Progress**: in the rich format, in progress is a **trail** (a `started` date), never a status, and the old format never said which scout or since when. Seed as `todo` (the recompute promotes it to `blocked` if it has dependencies that are not `done`). **Record every waypoint remapped this way** for the report: the user may want to re-seed one deliberately (`paused`, say).
- **To Do / Blocked**: leave unseeded; the recompute sets `todo` (no dependencies, or all done) or `blocked` (any dependency not done).

Write the seeded JSON, then run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py recompute` so every non-terminal status is *derived*. This guarantees the converted file passes validation immediately.

### C4. Write the phase-array `roadbook.json`

Write `.claude/roadbook.json` as a single phase object in an array (or, if converting one roadmap among several pointer-registry entries, append this phase and mark the others as needed). Structure, tabs, field order and British spelling exactly as `goblin-scout:start-roadbook` Step 6. Set the phase `name` from the old roadmap's name (or `$ARGUMENTS`), `path` to the `.md` it will regenerate (reuse the old path so existing links hold), `archived: false`, `externalGates: []`. Remove the old pointer-registry `.claude/roadmaps.json` once the new file is written.

### C5. Regenerate the `.md` as a rich projection

Overwrite the old `.md` at the same path with the rich layout (see `goblin-scout:start-roadbook` Step 7): milestone headings, `- [ ] **{ID}**: {description}` lines with status annotations, and a generated `graph LR` diagram; no `<a name>` anchors, no four-section structure, no `graph TD`. The diagram is the verbatim output of `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py graph --mermaid --direction LR` (terminal milestone edges, canonical colours, correct classDef placement; nothing hand-computed).

### C6. Generate `ROADBOOK_OVERVIEW.md`

The old format had no prose overview. Synthesise a minimal one at `docs/reports/ROADBOOK_OVERVIEW.md` (see `goblin-scout:start-roadbook` Step 8) from the milestone goals, with the header count from `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py stats`. **Flag the narrative sections as stubs** for the user to flesh out; invent no decision or rationale the source did not hold.

### C7. Validate and report

Run `python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/roadbook.py validate`: it must report clean; fix any discrepancy. Then report:

- Milestones and waypoints converted; the status distribution (`roadbook.py stats`).
- **In-progress remaps**: every waypoint that lost its in-progress state, so the user can start a trail on any still under way (`roadbook.py claim <ID> --assignee <name>`, asking which scout) or re-seed one deliberately.
- Any dependency edges recovered **only** from the Mermaid diagram (never written in prose); worth a glance in case the diagram was stale.
- The three paths written, and a note that `ROADBOOK_OVERVIEW.md`'s narrative is a stub.

---

## Notes

- C is one-way: the old single-file model cannot be rebuilt from the rich format, hence the git-checkpoint advice. A and B are moves, so `git revert` undoes either.
- B runs only when the user asks. The collision a roadbook escapes is in shared repositories, where moving a chart or a projection breaks links other people hold; that is their call, never a default.
- Statuses end up **derived**: the recompute is the source of truth for everything except `done`/`out_of_scope` seeds.
- Tabs not spaces; British spelling throughout. Afterwards the roadbook is tended by `goblin-scout:tend-roadbook`, extended by `goblin-scout:add-waypoints` and its chart drawn by `goblin-scout:unroll-chart`.
