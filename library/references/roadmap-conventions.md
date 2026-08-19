# Roadmap Conventions

Shared reference for the roadmap skill family (`roadmap-create`,
`roadmap-create-interview`, `roadmap-maintain`, `roadmap-update-tasks`,
`roadmap-migrate`, `artefact-roadmap`). Skills point here instead of restating
these rules; the deterministic halves live in
`~/.claude/library/scripts/roadmap.py` (single CLI) and `_roadmap_core.py`.

## The CLI

```bash
python3 "$HOME"/.claude/library/scripts/roadmap.py <subcommand> [PATH] [--phase NAME]
```

| Subcommand | Purpose | Key flags | Exit codes |
|---|---|---|---|
| `detect` | rich vs old-simple format | | 0 rich · 3 old · 2 unlocatable |
| `validate` | graph integrity + status correctness | | 0 clean · 1 discrepancies · 2 |
| `recompute` | fixed-point status recompute, writes back | `--check` `--json` `--reformat` `--render` | 0 · 1 cycle/format refusal · 2 |
| `stats` | status counts | `--json` | 0 · 2 |
| `graph` | dependency graph | `--json` (default), `--mermaid --direction LR\|TD --omit-done --palette light\|dark\|vars` | 0 · 2 |
| `ready` | actionable todo candidates with leverage signals | `--json` | 0 · 2 |
| `render` | deterministic HTML artefact from `library/templates/roadmap-artefact.html` | `--out PATH` | 0 · 2 |

`PATH` is optional; the roadmap is located by walking up from the cwd. If `~`
is not expanded in your shell context, use `"$HOME"` (as above). Multiple
active phases are an error, never a silent guess: archive finished phases or
pass `--phase NAME`.

**Detect guard (every skill runs this first):** exit 3 → tell the user to run
`roadmap-migrate`; exit 2 → ask for the roadmap path; exit 0 → proceed.

## Status vocabulary

Six statuses, no in-progress: `todo, blocked, paused, deferred, done,
out_of_scope`.

**Mechanical status rule:** empty `dependsOn` → `todo`; any non-done
dependency → at least `blocked`, escalating under the precedence
`deferred > paused > blocked > todo`. `done` and `out_of_scope` are terminal.
A root-seeded `paused`/`deferred` (parked status with empty `dependsOn`) is
held as authored and never recomputed. A `todo` task is by definition
unblocked. Statuses are computed, not judged: run `recompute`, do not
hand-assign (except the held seeds and the terminal pair). `softDependsOn`
never feeds this rule; a soft dependency can never impose `blocked` (or any
other status) on its dependant, regardless of the soft dependency's own
status.

## Graph conventions

**Terminal milestone edges:** a milestone node `M{N}` is a SINK for its own
tasks and a SOURCE for anything depending on the whole milestone:

- each sink task (nothing else in the milestone depends on it) gets
  `{sink} --> M{N}`; the node reads "these tasks complete the milestone"
- a task listing `M{N}` in `dependsOn` gets `M{N} --> {task}`
- never emit an entry edge `M{N} --> {firstTask}`

`roadmap.py graph` emits these edges; never hand-compute sinks.

**Acyclicity:** `dependsOn` must stay acyclic, including through milestones
(a → M2 → member → a is a cycle). Conceptual loops use the `iterative: true`
flag, never a real back-edge; the flag surfaces as a `↻` marker in diagrams,
not an edge.

**Soft edges (`softDependsOn`):** an optional, best-effort link ("renders
in the diagram, imposes nothing") for relationships worth showing but not
worth blocking on. A task's `softDependsOn` list holds ids (task, milestone,
or gate) the same way `dependsOn` does, but resolved through a wholly
separate code path so it stays invisible to every hard-dependency consumer
by construction:

- renders as a dotted arrow `X -.-> Y` (never `-->`) in `graph --mermaid`
  and the artefact
- never imposes status: a soft dependency cannot make its dependant
  `blocked`, no matter the soft dependency's own status
- exempt from the acyclicity rule above; a soft edge may close a loop that
  would be invalid as a hard `dependsOn` edge (that's often the point: an
  override or best-effort refresh that intentionally points "backwards")
- never disqualifies a task from being a milestone sink; only `dependsOn`
  entries within a milestone count toward the sink computation
- an unresolvable `softDependsOn` id is reported by `validate` (mirroring
  `dependsOn`'s unresolvable-id check), not silently dropped

Author soft edges as data in `roadmaps.json`; never hand-draw a `-.->` line
into a generated `PHASE.md` or artefact; the next regeneration wipes
anything not in the source data.

**Soft milestone members (`softMilestone: true`):** a task-level flag making
the derived milestone-complete edge (`{task} -.-> M{N}`) soft instead of
hard. The task stays a member of its milestone (counted in `donePct`,
listed under the milestone) but:

- never gates milestone completion: anything depending on `M{N}` is
  satisfied without it
- its milestone-complete edge renders dotted and is exempt from the
  through-milestone acyclicity check
- it is never reported as `isMilestoneSink` by `ready`; closing it does
  not close the milestone

Use it for best-effort milestone work (eval coverage, polish) that should
stay visible in the milestone without holding up everything downstream.

## Status → colour table (canonical)

One palette for every projection. `STATUS_STYLE` in `roadmap.py` is the
machine-readable copy; `graph --mermaid` emits literal hexes for PHASE.md
(GitHub cannot resolve CSS vars) and `--palette vars` emits semantic custom
properties for the artefact. Never restate colours in a skill; regenerate
diagrams from the CLI.

| Status | Family | Light (bg / stroke) | Dark (bg / stroke) | Non-colour encoding | Semantics |
|---|---|---|---|---|---|
| `done` | green | `#e0ffd9` / `#008217` | `#062800` / `#72ff6c` | solid | finished, quietly |
| `todo` | gray | `#f6f6f6` / `#6f6f6f` | `#222222` / `#8b8b8b` | solid | blank slate |
| `blocked` | red | `#fff8f6` / `#e0002b` | `#530003` / `#ffddd8` | bold stroke | stop |
| `paused` | purple | `#fdf4ff` / `#b01fe3` | `#3a004f` / `#f7d9ff` | dasharray 4 3 | deliberately parked |
| `deferred` | cinnamon | `#fff8f3` / `#ac5c00` | `#371d00` / `#ffdfc6` | dasharray 2 4 + italic | shelved for later |
| `out_of_scope` | gray, faded | `#f6f6f6` / `#e2e2e2` | `#222222` / `#3e3e3e` | dasharray 2 2, struck label | struck from play |
| gate (`external`) | yellow | `#fff9e5` / `#7d6f00` | `#292300` / `#ffe53e` | dasharray 4 3 + italic | outside our control |
| milestone (`mile`) | sky | `#e3f7ff` / `#007590` | `#001f28` / `#aee9ff` | bold | structural waypoint |

Pink is the primary accent (Jason's terminal gradient) and is never a status
colour. Shade pattern: light bg = shade 1, stroke/text = shade 4; dark
inverted. Shade differences ≥ 3 keep WCAG AA.

Mermaid class names match statuses (`todo`, `blocked`, `paused`, `deferred`,
`done`, `outOfScope`) plus `mile` and `external`. Legacy diagrams used `open`
for todo and Bootstrap-era hexes; regenerating via `graph --mermaid` replaces
both. classDef lines always come straight after the `graph LR`/`graph TD`
line; before it is a silent render failure.

## Milestone-level state (artefact only)

A milestone has no `status` field; it is not itself a task. The HTML artefact
derives a milestone-level state from its member tasks' status counts, purely
for that artefact's own colour and sort (`roadmap.py`'s `milestone_state()`;
never written back to `roadmaps.json`, never used by `recompute`/`validate`).
Six states, four of which form a top-level sort partition (deferred first,
ahead of percentage; then inProgress, todo, done); blocked/paused surface as
their own card colour but sit outside that four-way partition:

| State | Fires when | Colour |
|---|---|---|
| `deferred` | ≥1 member `deferred`, no `todo`/`blocked`/`paused` member left | cinnamon (shares the task-status hue) |
| `done` | every member `done`/`out_of_scope` (nothing actionable, nothing deferred), or `donePct == 100` | green |
| `blocked` | ≥1 member `blocked` (and not already deferred/done) | red |
| `paused` | ≥1 member `paused` (and not already deferred/done/blocked) | purple |
| `inProgress` | `0 < donePct < 100`, nothing blocked/paused | **azure** — unclaimed by task status, distinct from sky (milestone-structural) |
| `todo` | nothing started, or a genuinely empty (zero-task) milestone | gray |

An all-`out_of_scope` milestone (struck-from-play) reads as `done`, not
`deferred` (shelved-for-later): different signal, and nothing remains
actionable either way. A milestone with one `deferred` task and nine `done`
ones still reads `deferred` even at 90% complete: the deliberate shelving
call outranks percentage. An empty milestone (zero tasks) stays `todo`
rather than claiming to be finished.

## Dev-chip colour (artefact only)

Assignee is free-text with no roster (see below) and never inferred, so the
artefact never maps a name to a colour by hand. `roadmap.py`'s `dev_colour()`
hashes the lowercased, trimmed assignee string with `zlib.crc32` (never
Python's builtin `hash()`, which is salted per `PYTHONHASHSEED` and would
assign a different colour to the same person across separate render runs)
into a fixed palette, disjoint from every status/milestone/gate hue above:
teal, lime, magenta, indigo, amber, rose.

## Codebase reconciliation (inference)

Inference (deciding a task's status from the actual code rather than the
dependency graph) lives in exactly one place: `roadmap-maintain`'s
reconciliation step. Every other status change is mechanical (see above).
This is deliberately narrow so the rest of the family can keep treating
status as computed, not judged.

**What inference may propose**, never write directly:

- **`done`**: the task's described feature is fully implemented in code.
- **Dependency/gate edge removal**: a blocker's prerequisite is now
  satisfied, so the edge is removed from `dependsOn` (and a gate's `blocks[]`
  in step); recompute then unblocks the task, same as any other edit to the
  graph.

Nothing else. Inference never hand-sets `todo`, `blocked`, `paused` or
`deferred` directly; those stay purely derived. It never re-opens `done`,
flips `out_of_scope`, or disturbs a root-seeded held status.

**Evidence rule:** positive, specific, whole-task evidence only. Absence of a
match is never evidence of completion. A task whose feature is only partly
built is left as-is (there is no in-progress status) rather than marked
done. Corroboration (a passing test, a real call-site) outweighs a lone
definition.

**Candidate seeding (efficiency):** only non-terminal tasks (`todo`,
`blocked`, `paused`; never `done`/`out_of_scope`/`deferred`) are candidates,
ordered by leverage (`ready --json`). Search is bounded to files changed
since the last reconciliation (or a recent window on first run), with 1–3
targeted search terms drawn from each candidate's description/notes, never
a whole-tree scan.

**Confirmation gate:** every proposed edit is shown with its evidence and
applied only once approved, mirroring the proposal-then-write pattern in
`roadmap-update-tasks`. Discrepancies found in the other direction (a task
marked `done` whose code can no longer be found) are reported as drift, never
auto-reverted; absence still isn't evidence.

## File formatting

- `roadmaps.json`: tab indentation, `ensure_ascii` off, trailing newline
  (`recompute` refuses to write non-canonical files without `--reformat`)
- `docs/artefacts/roadmap-*.html`: `render`'s own canonical form (tabs,
  single-line JSON payload), not a formatter's. A repo running Prettier (or
  another formatter) in a hook or CI should exclude the artefact glob from
  it, the same way `.claude/roadmaps.json` is excluded, so regenerating the
  dashboard never fights the formatter.
- Task field order: `id, description, status, dependsOn, softDependsOn?, softMilestone?, iterative?, notes?, assignee?, pr?`
- `assignee` is free-text (no roster/validation), omit-when-empty like `notes`.
  Never inferred: a skill setting it must ask, never guess from description,
  git author, category, or who's running the skill.
- `pr` is an optional integer: the GitHub PR number that ships the task,
  recorded by `next-task-ship` at PR creation (worth setting by hand when
  shipping outside that skill). It lets a later run detect that a `done`
  dependency is still unmerged and stack a dependent branch on it instead of
  branching from main (see `library/references/stacked-prs.md`). It is never
  a status signal: `done` still means done, merged or not, and `recompute`
  ignores the field entirely.
- Gate field order: `id, name, status, imposes?, blocks[], notes?`
- Phase field order: `name, path, project?, archived?, externalGates, milestones`
- `project` is optional free text naming the project the phase belongs to
  (distinct from `name`, which names the phase/roadmap, e.g. "MVP"). The
  artefact's `<h1>` reads `{project}: {phase}`; when `project` is absent the
  artefact falls back to the project root directory name (`render`'s
  `_project_name()`), so no migration is needed for existing roadmaps.
- British spelling in all descriptions, notes and prose projections
- PHASE.md task lines: `- [ ] **{ID}**: {description}` with annotations: none
  when `dependsOn` empty; `_(depends on {IDs})_` when all deps done;
  `_(blocked: depends on {IDs})_`; `_(paused: reconvene {gateId})_`;
  `_(deferred to a later phase)_`

## The three artefacts

| File | Role | Regenerated by |
|---|---|---|
| `.claude/roadmaps.json` | source of truth | `recompute` (statuses only) |
| `docs/roadmaps/{PHASE}.md` | task-list projection + Mermaid diagram | skill prose + `graph --mermaid --direction LR` for the diagram block |
| `docs/reports/ROADMAP_OVERVIEW.md` | prose overview | skill prose; header counts from `stats` |
| `docs/artefacts/roadmap-{slug}.html` | interactive dashboard | `render` (fully deterministic; `recompute --render` refreshes it) |

## Which skill when

| Situation | Skill |
|---|---|
| No roadmap yet | `roadmap-create` |
| Old single-file format detected | `roadmap-migrate` |
| Half-formed ideas to explore into tasks | `roadmap-create-interview` |
| One known task to add | `roadmap-update-tasks` |
| Work landed / statuses drifted | `roadmap-maintain` (add `reconcile` to check against code) |
| Priorities / freshness / health / dependency-graph review | `roadmap-review` (lens: `health`, `deps` or default full) |
| Render the HTML dashboard | `artefact-roadmap` |
| Choose the next task (one pick) | `next-task-suggest` |
| See the whole ready-set | `next-task-group` |
| Ship the next task end-to-end | `next-task-ship` |
