# Roadmap Conventions

Shared reference for the roadmap skill family (`roadmap:create`,
`roadmap:create-interview`, `roadmap:maintain`, `roadmap:update-tasks`,
`roadmap:update-devs`, `roadmap:migrate`, `roadmap:dashboard`). Skills point here instead of restating
these rules; the deterministic halves live in
`<plugin-root>/scripts/roadmap.py` (single CLI) and `_roadmap_core.py`.
`<plugin-root>` is the plugin's install directory; every skill's CLI line
gives it resolved.

## The CLI

```bash
python3 <plugin-root>/scripts/roadmap.py <subcommand> [PATH] [--phase NAME]
```

| Subcommand | Purpose | Key flags | Exit codes |
|---|---|---|---|
| `detect` | rich vs old-simple format | | 0 rich · 3 old · 2 unlocatable |
| `validate` | graph integrity + status correctness | | 0 clean · 1 discrepancies · 2 |
| `recompute` | fixed-point status recompute, writes back | `--check` `--json` `--reformat` `--render` | 0 · 1 cycle/format refusal · 2 |
| `stats` | status counts | `--json` | 0 · 2 |
| `graph` | dependency graph | `--json` (default), `--mermaid --direction LR\|TD --omit-done --palette light\|dark\|vars` | 0 · 2 |
| `ready` | actionable todo candidates with leverage signals; `--json` adds `groups` (candidate ids per milestone and per topic, in display order) | `--json` | 0 · 2 |
| `render` | deterministic HTML artefact from `templates/roadmap-artefact.html` | `--out PATH` | 0 · 2 |
| `claim ID` | record that someone has started a task (see Claims) | `--assignee NAME --reassign --date YYYY-MM-DD` | 0 · 1 refusal · 2 |
| `release ID` | drop a claim | `--unassign` | 0 · 1 not claimed · 2 |
| `hook EVENT` | Claude Code hook entry point (`session-start`, `post-tool-use`); reads the hook JSON on stdin | | always 0 |

`PATH` is optional; the roadmap is located by walking up from the cwd. Multiple
active phases are an error, never a silent guess: archive finished phases or
pass `--phase NAME`.

**Detect guard (every skill runs this first):** exit 3 → tell the user to run
`roadmap:migrate`; exit 2 → ask for the roadmap path; exit 0 → proceed.

## Status vocabulary

Six statuses: `todo, blocked, paused, deferred, done, out_of_scope`. In
progress is not one of them: it is a claim on a task (see Claims), so it never
disturbs the rule below.

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

## Claims

A claim says a person has started a task. It is the task's optional `started`
field, an ISO date (`"2026-09-25"`), with `assignee` saying who; it is never
a status and never inferred. Skills and hooks ask which task and who is doing
it; `claim` stamps today's date unless given another.

- **Making one:** `claim ID [--assignee NAME]` refuses unless the task's
  effective status is `todo`, it isn't already claimed and any change of
  assignee is explicit (`--reassign`). `release ID [--unassign]` deletes it.
  Both write `roadmaps.json` only: like `assignee`, a claim has no PHASE.md
  or overview projection.
- **What views show:** a claimed task that is `todo` or `blocked` shows as
  in progress; `paused`, `deferred`, `done` and `out_of_scope` win over a
  claim. `display_status()` in `_roadmap_core.py` is the only implementation;
  the dashboard, Mermaid and `stats` use it; anything mirroring the
  roadmap elsewhere (a tracker sync) should apply the same rule.
- **What it changes:** `ready` lists claimed tasks under `claimed`, never
  among the `candidates`. `recompute` and `validate` never read `started`
  beyond checking it is a date; a claimed task keeps its computed status, so
  one that a reopened dependency blocks shows in progress in views and
  `blocked` to the graph.
- **Where it lives:** normally on the branch doing the work. A branch claims
  a task when, relative to its merge-base with the default branch, the task
  gained `started` or became `done`. Teammates see the claim once the branch
  is pushed; it merges as `done` with the work.
- **Hooks:** `hook session-start` and `hook post-tool-use` notice a branch
  that claims nothing (at session start, or just after it is created) and
  have Claude offer the claim in one question. `git config
  branch.<name>.roadmapClaim none` stops the question for that branch.
- **Staleness:** a claim more than 14 days old on an unfinished task is
  stale. `roadmap:review` flags it; nothing releases it automatically.

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
  entries within a milestone count towards the sink computation
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
| in progress (a claim, see Claims) | azure | `#e8f2ff` / `#0071af` | `#001c30` / `#c6e0ff` | solid + `▸` label marker (azure is close to sky) | someone is on it |
| `blocked` | red | `#fff8f6` / `#e0002b` | `#530003` / `#ffddd8` | bold stroke | stop |
| `paused` | purple | `#fdf4ff` / `#b01fe3` | `#3a004f` / `#f7d9ff` | dasharray 4 3 | deliberately parked |
| `deferred` | cinnamon | `#fff8f3` / `#ac5c00` | `#371d00` / `#ffdfc6` | dasharray 2 4 + italic | shelved for later |
| `out_of_scope` | gray, faded | `#f6f6f6` / `#e2e2e2` | `#222222` / `#3e3e3e` | dasharray 2 2, struck label | struck from play |
| gate (`external`) | yellow | `#fff9e5` / `#7d6f00` | `#292300` / `#ffe53e` | dasharray 4 3 + italic | outside our control |
| milestone (`mile`) | sky | `#e3f7ff` / `#007590` | `#001f28` / `#aee9ff` | bold | structural waypoint |

Pink is the primary accent and is never a status
colour. Shade pattern: light bg = shade 1, stroke/text = shade 4; dark
inverted. Shade differences ≥ 3 keep WCAG AA.

Mermaid class names match statuses (`todo`, `blocked`, `paused`, `deferred`,
`done`, `outOfScope`) plus `inProgress` for a claimed task in play, `mile`
and `external`. Legacy diagrams used `open`
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
| `done` | every member `done`/`out_of_scope` (nothing actionable, nothing deferred) or `donePct == 100` | green |
| `blocked` | ≥1 member `blocked` (and not already deferred/done) | red |
| `paused` | ≥1 member `paused` (and not already deferred/done/blocked) | purple |
| `inProgress` | `0 < donePct < 100` or a member shows in progress (a claim), nothing blocked/paused | **azure**: shared with claimed tasks, distinct from sky (milestone-structural) |
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
dependency graph) lives in exactly one place: `roadmap:maintain`'s
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
flips `out_of_scope`, disturbs a root-seeded held status or makes or drops a
claim (a claim is a person's statement).

**Evidence rule:** positive, specific, whole-task evidence only. Absence of a
match is never evidence of completion. A task whose feature is only partly
built is left as-is (inference never claims it; see Claims) rather than
marked done. Corroboration (a passing test, a real call-site) outweighs a lone
definition.

**Candidate seeding (efficiency):** only non-terminal tasks (`todo`,
`blocked`, `paused`; never `done`/`out_of_scope`/`deferred`) are candidates:
claimed tasks first (`ready --json`'s `claimed`, the likeliest to be built
already), then the rest ordered by leverage (`ready --json`'s `candidates`). Search is bounded to files changed
since the last reconciliation (or a recent window on first run), with 1–3
targeted search terms drawn from each candidate's description/notes, never
a whole-tree scan.

**Confirmation gate:** every proposed edit is shown with its evidence and
applied only once approved, mirroring the proposal-then-write pattern in
`roadmap:update-tasks`. Discrepancies found in the other direction (a task
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
- Task field order: `id, description, status, dependsOn, softDependsOn?, softMilestone?, iterative?, notes?, assignee?, started?, pr?`
- `assignee` is free-text (no roster/validation), omit-when-empty like `notes`.
  Never inferred: a skill setting it must ask, never guess from description,
  git author, category or who's running the skill.
- `started` is the claim date (see Claims), omit-when-empty; `claim` and
  `release` keep the field order.
- `pr` is an optional integer: the GitHub PR number that ships the task,
  worth setting by hand when a task ships. It lets a later run detect that a
  `done` dependency is still unmerged and stack a dependent branch on it
  instead of branching from main. It is never
  a status signal: `done` still means done whether merged or not, and
  `recompute` ignores the field entirely.
- Milestone field order: `id, name, goal, tasks`. Only `id` is enforced by
  `roadmap.py` (`_require_id`); `name` and `goal` default to empty strings
  everywhere else. Don't add fields beyond these four.
- Milestone ID assignment: `M{max existing milestone number in the phase + 1}`,
  same never-reuse rule as task IDs. Milestones have no `dependsOn` field of
  their own; a milestone-level gate is expressed on the task(s) inside it
  (`dependsOn: ["M{a}"]` on the task, not on the milestone object). Appending
  a milestone at the end of the sequence is unambiguous; nothing yet defines
  what happens on a mid-sequence insertion, since `M{N}` numbering is loosely
  coupled to task-ID category prefixes elsewhere in the roadmap (a category
  can span several milestones): treat that as an open question, not a rule
  to invent on the spot, until a real need forces the decision.
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
  `_(deferred to a later phase)_` when the deferral is out of this phase
  entirely. A task deferred *within* the current phase by a tier-release gate
  (see Tiers below) instead uses `_(deferred: {gateId}, and every {tier}
  milestone)_` on the tier's entry task and `_(deferred: follows {ID})_` on
  each task chained behind it: "a later phase" would be false when the work
  is still this phase's, just gated on the envelope rather than the calendar.

### Tiers

A phase may split into tiers (e.g. core/secondary/tertiary) released one
after another by gate, not by date: a tier's entry task depends on every
milestone in the tier(s) before it plus that tier's release gate (`imposes:
"deferred"`), and every other task in the tier chains behind the entry task
via ordinary `dependsOn`. This is the one case a root-seeded parked status
doesn't fit: root-seeding only holds for empty `dependsOn`, and a tier's
tasks depend on the whole of the tier(s) before them, so the gate is what
keeps them `deferred` under `recompute` rather than escalating to `blocked`
the moment their nominal deps are all `done`. See the deferred annotation
forms above for how this renders in PHASE.md.

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
| No roadmap yet | `roadmap:create` |
| Old single-file format detected | `roadmap:migrate` |
| Half-formed ideas to explore into tasks | `roadmap:create-interview` |
| One known task to add | `roadmap:update-tasks` (`t` mode) |
| Several tasks with an asserted dependency order | `roadmap:update-tasks` (`c` mode) |
| New milestone needed | `roadmap:update-tasks` (`m` mode) |
| Tasks need owners, or a dev's load needs handing over | `roadmap:update-devs` (`ready\|all` horizon, `devless\|<dev>\|all` scope) |
| Work landed / statuses drifted | `roadmap:maintain` (add `reconcile` to check against code) |
| Mark a task in progress, or stop working on one | `roadmap:maintain` (runs `claim` / `release`; the hooks usually offer the claim first) |
| Priorities / freshness / health / dependency-graph review | `roadmap:review` (lens: `health`, `deps` or default full) |
| Render the HTML dashboard | `roadmap:dashboard` |
| Choose the next task (one pick) | `roadmap:next-suggest` |
| See the whole ready-set | `roadmap:next-group` |
