# Roadbook Conventions

Shared reference for the goblin-scout skill family (`goblin-scout:start-roadbook`,
`goblin-scout:plan-expedition`, `goblin-scout:tend-roadbook`, `goblin-scout:add-waypoints`,
`goblin-scout:assign-scouts`, `goblin-scout:start-trail`, `goblin-scout:review-roadbook`,
`goblin-scout:rebind-roadbook`, `goblin-scout:unroll-chart`, `goblin-scout:configure-roadbook`).
Skills point here instead of restating these rules; the deterministic halves live in
`<plugin-root>/scripts/roadbook.py` (single CLI) and `_roadbook_core.py`.
`<plugin-root>` is the plugin's install directory; every skill's CLI line
gives it resolved.

The words: the roadbook is what the plugin keeps (`.claude/roadbook.json` and
its projections); a waypoint is a task (an entry in a milestone's `tasks`); a
scout is the person doing one (its `assignee`); a trail is claimed work (a
waypoint with `started`); an expedition is a planned batch of new waypoints;
the chart is the rendered HTML page. Field names in the JSON stay literal.

## The CLI

```bash
python3 <plugin-root>/scripts/roadbook.py <subcommand> [PATH] [--phase NAME]
```

| Subcommand | Purpose | Key flags | Exit codes |
|---|---|---|---|
| `detect` | rich vs old-simple format | | 0 rich · 3 old · 2 unlocatable |
| `validate` | graph integrity + status correctness; in a tiered phase, also no lower-tier waypoint edge the waypoint already requires by milestone (see Tiers) | | 0 clean · 1 discrepancies · 2 |
| `recompute` | fixed-point status recompute, writes back | `--check` `--json` `--reformat` `--render` | 0 · 1 cycle/format refusal · 2 |
| `stats` | status counts; done fractions count in-scope waypoints only (see Waypoint counts) | `--json` | 0 · 2 |
| `graph` | dependency graph | `--json` (default), `--mermaid --direction LR\|TD --omit-done --palette light\|dark\|vars` | 0 · 2 |
| `ready` | actionable todo candidates with leverage signals; `--json` adds `groups` (candidate ids per milestone and per topic, in display order) | `--json` | 0 · 2 |
| `render` | the chart, deterministic HTML from `templates/chart.html`; `--phase` may name an archived phase here | `--out PATH` | 0 · 2 |
| `config KEY VALUE` | set a per-phase option in `roadbook.json`, inserted in field order with nothing else touched; the one key is `artefact`, the chart's path relative to the project root; `--phase` may name an archived phase | `--clear` (remove the key) `--reformat` | 0 · 1 refusal (bad path, non-canonical file) · 2 |
| `claim ID` | start a trail: record that a scout has started a waypoint (see Trails) | `--assignee NAME --reassign --date YYYY-MM-DD` | 0 · 1 refusal · 2 |
| `assign ID` | set or clear an assignee without starting a trail (see Trails) | `--assignee NAME` or `--unassign` (exactly one) | 0 · 1 refusal · 2 |
| `release ID` | drop a trail | `--unassign` | 0 · 1 no trail · 2 |
| `pull` | refresh a phase mirrored from Jira; read-only towards Jira (see Mirrored phases) | `--project KEY --name NAME` (start a mirror) `--issues FILE` `--allow-removals` `--dry-run` | 0 · 1 nothing to mirror, or more than half the mirror would go · 2 no credentials, Jira unreachable, cycle, issue without a key |
| `rebind` | move a 2.x `.claude/roadmaps.json` to `roadbook.json` now, without waiting for the first write; `--outputs` also moves the chart, the projections and the prose overview from their 2.x default names | `--outputs` `--dry-run` | 0 · 1 a target already exists · 2 |
| `hook EVENT` | Claude Code hook entry point (`session-start`, `post-tool-use`); reads the hook JSON on stdin | | always 0 |

`PATH` is optional; the roadbook is located by walking up from the cwd. Multiple
active phases are an error, never a silent guess: archive finished phases or
pass `--phase NAME`.

**Detect guard (every skill runs this first):** exit 3 → tell the user to run
`goblin-scout:rebind-roadbook`; exit 2 → ask for the roadbook path; exit 0 → proceed.

**Before 3.0.0** the plugin was called roadmap and kept `.claude/roadmaps.json`
(and `.claude/roadmaps.local.json`). Both are still read. The first write by
3.0.0 or later moves them to `roadbook.json` and `roadbook.local.json` with one
line of notice; no value is rewritten, and a phase with no `artefact` gets the
chart's old default path pinned there, so the chart stays where it was. A local
file moved alongside the one being written travels byte for byte (no pin, no
stamp, no reformat), so a mirrored phase in it with no `artefact` renders its
chart to `chart-<phase>.html` after the move; `rebind` moves the local file
with its own pin, and `rebind --reformat` is the one way to reformat it. A
write to the local file that would move a committed `roadmaps.json` not in
canonical form is refused, with both files untouched; `rebind --reformat` moves
the two and accepts the reformat. Such a
project also keeps its projections under `docs/roadmaps/` (each phase's `path`
says where) and its overview at `docs/reports/ROADMAP_OVERVIEW.md` until
`rebind --outputs` moves them to the roadbook names.

## Status vocabulary

Six statuses: `todo, blocked, paused, deferred, done, out_of_scope`. In
progress is not one of them: it is a trail on a waypoint (see Trails), so it
never disturbs the rule below.

**Mechanical status rule:** empty `dependsOn` → `todo`; any non-done
dependency → at least `blocked`, escalating under the precedence
`deferred > paused > blocked > todo`. `done` and `out_of_scope` are terminal.
A root-seeded `paused`/`deferred` (parked status with empty `dependsOn`) is
held as authored and never recomputed. A `todo` waypoint is by definition
unblocked. Statuses are computed, not judged: run `recompute`, do not
hand-assign (except the held seeds and the terminal pair). `softDependsOn`
never feeds this rule; a soft dependency can never impose `blocked` (or any
other status) on its dependant, regardless of the soft dependency's own
status.

## Trails

A trail (the CLI calls it a claim) says a scout has started a waypoint. It is
the waypoint's optional `started` field, an ISO date (`"2026-09-25"`), with
`assignee` saying who; it is never a status and never inferred. Skills and
hooks ask which waypoint and which scout is doing it; `claim` stamps today's
date unless given another.

- **Starting one:** the `goblin-scout:start-trail` skill (`goblin-scout:start-trail [ID] [scout|release]`) is the front door: it asks who, runs the CLI, commits the change and offers the push. Underneath, `claim ID [--assignee NAME]` refuses unless the waypoint's
  effective status is `todo`, it isn't already on a trail and any change of
  assignee is explicit (`--reassign`). A `blocked` waypoint can take a trail
  too when the work is stacked on the work that unblocks it: every unmet
  blocker already carries `started` in the roadbook file being edited (a
  stacked branch inherits its parent branch's trails in that file). Unmet
  blockers are each unfinished `dependsOn` waypoint, each unfinished member
  of a milestone in `dependsOn`, every gate `dependsOn` names (whatever its
  status, since a gate resolves by losing its edge) and every gate that is
  not `done` whose `blocks` lists the waypoint. A gate can never take a
  trail, so a waypoint a gate still holds stays unclaimable; the refusal
  names the blockers with no trail. The Jira sync in CHIRPdb is stricter: it
  also requires the blocker's trail to sit on the same branch or an ancestor
  branch, so a blocker claimed on `main` alone passes this check but not the
  sync's.
  `release ID [--unassign]` deletes it.
  `assign ID (--assignee NAME | --unassign)` sets or clears the assignee alone,
  on any waypoint including one on a trail, and never touches `started`. The
  `/scout-waypoints` pane's start-trail key passes `--reassign` itself, because
  the name is typed there on purpose; the `goblin-scout:start-trail` skill
  still asks first.
  All of these write `roadbook.json` only. A trail has no PHASE.md
  waypoint-line annotation and no overview line; the PHASE.md diagram shows it,
  like the chart, once `goblin-scout:tend-roadbook` regenerates the diagram.
- **What views show:** a waypoint on a trail that is `todo` or `blocked` shows
  as in progress; `paused`, `deferred`, `done` and `out_of_scope` win over a
  trail. `display_status()` in `_roadbook_core.py` is the only implementation;
  the chart, Mermaid and `stats` use it; anything mirroring the roadbook
  elsewhere (a tracker sync) should apply the same rule.
- **What it changes:** `ready` lists waypoints on a trail under `claimed`,
  never among the `candidates`. `recompute` and `validate` never read
  `started` beyond checking it is a date; a waypoint on a trail keeps its
  computed status, so one that a reopened dependency blocks shows in progress
  in views and `blocked` to the graph.
- **Where it lives:** normally on the branch doing the work. A branch claims
  a waypoint when, relative to its merge-base with the default branch, the
  waypoint gained `started` or became `done`. Teammates see the trail once
  the branch is pushed; it merges as `done` with the work.
- **Hooks:** `hook session-start` and `hook post-tool-use` notice a branch
  that claims nothing (at session start, or just after it is created) and
  have Claude offer the trail in one question. `git config
  branch.<name>.roadbookClaim none` stops the question for that branch (a
  `roadmapClaim` value set by a 2.x plugin is still read).
- **Staleness:** a trail more than 14 days old on an unfinished waypoint is
  stale. `goblin-scout:review-roadbook` flags it; nothing releases it
  automatically.

## Ended dates

A done waypoint carries an optional `ended` field: the ISO date (`"2026-10-02"`,
no time, no timezone) on which its work finished, the counterpart of
`started`. It records the past, never a plan: there is no target or due date
field, and `validate` rejects `ended` on any waypoint whose status is not
`done`.

- **Writing one:** `end ID [--date YYYY-MM-DD] [--force]` stamps a done waypoint
  (today by default) and refuses to overwrite one without `--force`.
  `stamp-ended --base REF [--pr N]` stamps every done waypoint that was not
  done at the branch's merge-base with REF, plus any done waypoint whose `pr`
  is N; the PR-landing flow runs it on the branch before merge, so the date
  arrives on the default branch with the work. `backfill-ended [--dry-run]`
  dates every done waypoint lacking one from the git history of
  `roadbook.json` (the commit where it last became done);
  `goblin-scout:tend-roadbook` runs it. It skips and reports a waypoint whose
  date would precede its `started`.
  `stamp-ended` exits 1 when the merge-base copy of the file is missing,
  unparseable or has no phase of the active phase's name, rather than
  treating every done waypoint as finished by the branch.
- **How trustworthy the date is:** a status-change commit's date is when the
  roadbook recorded the change, which may be later than when the work shipped.
  A backfill basis of `first-seen` means the waypoint was already done when
  the roadbook first reached git (a lower bound), and `uncommitted` means it
  is done only in the working tree (today).
- **Reopening:** a waypoint reset from `done` loses its `ended` line; `validate`
  flags the stale date otherwise. Finishing it again stamps a new date.
- **Checks:** `validate` also rejects a date that does not parse and an
  `ended` before `started`.
- **What it changes:** nothing computed. `recompute`, `ready` and the graph
  ignore the field; `started` and every status value are unchanged.

## Mirrored phases

A phase with a `source` is a mirror of an external tracker, which is then the
source of truth. A phase without one is unaffected by everything in this
section. The one kind is Jira:

```json
"source": {"kind": "jira", "project": "T2DV"}
```

- **Where it lives:** `.claude/roadbook.local.json`, beside the committed
  `roadbook.json` and kept out of git, so teammates who do not use the plugin
  never see it. When that file exists it is the roadbook every command and
  skill finds; the committed file stays reachable by passing its path. A
  project with no local file resolves as it always has.
- **Starting one:** `pull --project KEY [--name NAME]` creates the file and
  the phase. After that, plain `pull` refreshes it; `--dry-run` prints what
  would change. It needs `JIRA_BASE_URL` (which must be `https://`),
  `JIRA_EMAIL` and `JIRA_API_TOKEN` in the environment, the project's
  `.env.local` or its `.env` (an unquoted trailing `# comment` is ignored),
  and only ever reads; a redirect from Jira is refused, so the token is never
  sent anywhere else. A pull that returns no waypoints (an empty answer, or
  nothing but epics) is refused and writes nothing. So is a pull that would
  remove more than half of four or more mirrored waypoints (a truncated
  answer looks like that); pass `--allow-removals` when Jira really lost them.
  `--dry-run` shows the removals and says a real pull would be refused.
- **What maps to what:** a fix version is a milestone (it keeps its `M{N}`
  when the version is renamed; issues with no version sit in `M0`,
  Unscheduled); an epic is the `topic` of the issues under it and never a
  waypoint; every other issue is a waypoint whose id is the Jira key; a Blocks
  link is a `dependsOn` edge; an issue also depends on its child issues, so a
  story waits for the tickets it was split into, and a child inherits whatever
  blocks its story, so a split of a blocked story is never offered as ready
  (except a blocker that itself already waits on the child, which Jira
  orders the other way round and which would otherwise close a loop). Where
  two inherited blockers would only close a loop together, the one added
  later in key order is left out and `pull` warns.
  A Blocks link to an open issue the mirror does not hold (another project,
  or one a custom `jql` leaves out) becomes a gate with `tracker.issue` set;
  pull owns it, adds it when the link appears and retires it when the blocker
  is done or the link goes. A gate you add to `externalGates` by hand, and a
  mirrored waypoint's edge to it, survive every pull; to hold one of your own
  waypoints behind an outside blocker, add your own gate, since pull rewrites
  a generated gate's `blocks` on every run.
- **Status:** an issue in Jira's done category is `done`, with `ended` from
  its resolution date. Every other issue is left to the mechanical rule
  (`todo` or `blocked`); one Jira has in progress carries `started`, so views
  show it in progress. The Jira status name is kept in `tracker.status`.
  Where Jira and the graph disagree (in progress behind an open blocker,
  done before something it depends on), `pull` says so and changes nothing.
- **Who owns what:** on a mirrored waypoint Jira owns `description`, `status`,
  edges to other mirrored waypoints, `topic`, `assignee`, `started`, `ended`
  and `tracker`. `notes`, `pr`, soft edges and edges to local waypoints are
  yours and survive every pull. `claim`, `assign`, `release` and `end` refuse
  a mirrored waypoint, `stamp-ended` and `backfill-ended` refuse the phase,
  and the trail hooks stay silent in a project with a local roadbook file:
  work is assigned in Jira.
- **Local waypoints:** a waypoint with `"local": true` is your own. It can sit
  in any milestone, depend on mirrored waypoints and be depended on by them,
  and is claimed, released and ended as in any phase. `pull` never rewrites
  one. If something it depends on leaves Jira, the edge moves to its
  `orphaned` list (and returns if the issue does); if its milestone leaves, it
  moves to `M0`. A milestone you add yourself, with no `tracker`, is kept as
  it is.
- **Issues that leave Jira:** a mirrored waypoint whose issue is deleted is
  dropped from the mirror, unless it carries `notes` or a `pr`. Then it is
  parked: moved to a `GONE` milestone, "Gone from Jira", as an `out_of_scope`
  local waypoint with those fields intact, so it counts nowhere and nothing
  you wrote is lost. Delete it by hand once its notes have a new home. If the
  issue returns, its notes and pr go back onto it and the parked copy goes.
- **Topics:** `ready --json` groups by a waypoint's `topic` when it has one
  and falls back to the letters in its id, so ordinary phases group as before.

## Graph conventions

**Terminal milestone edges:** a milestone node `M{N}` is a SINK for its own
waypoints and a SOURCE for anything depending on the whole milestone:

- each sink waypoint (nothing else in the milestone depends on it) gets
  `{sink} --> M{N}`; the node reads "these waypoints complete the milestone"
- exception (transitive reduction): a hard sink edge is dropped when `M{N}`
  is already reachable from the sink through other hard edges, e.g.
  `6HD.5 --> 4PD.3 --> M4 --> 6HD.3 --> M6` makes `6HD.5 --> M6` redundant.
  Only milestone-complete edges are reduced; `dependsOn` waypoint edges and
  soft (dotted) edges stay as authored, and a milestone always keeps at
  least one inbound edge because the surviving path ends in one
- a waypoint listing `M{N}` in `dependsOn` gets `M{N} --> {waypoint}`
- never emit an entry edge `M{N} --> {firstWaypoint}`

`roadbook.py graph` emits these edges; never hand-compute sinks.

**Acyclicity:** `dependsOn` must stay acyclic, including through milestones
(a → M2 → member → a is a cycle). Conceptual loops use the `iterative: true`
flag, never a real back-edge; the flag surfaces as a `↻` marker in diagrams,
never as an edge.

**Soft edges (`softDependsOn`):** an optional, best-effort link ("renders
in the diagram, imposes nothing") for relationships worth showing but not
worth blocking on. A waypoint's `softDependsOn` list holds ids (waypoint,
milestone or gate) the same way `dependsOn` does, but resolved through a
wholly separate code path so it stays invisible to every hard-dependency
consumer by construction:

- renders as a dotted arrow `X -.-> Y` (never `-->`) in `graph --mermaid`
  and the chart
- never imposes status: a soft dependency cannot make its dependant
  `blocked`, no matter the soft dependency's own status
- exempt from the acyclicity rule above; a soft edge may close a loop that
  would be invalid as a hard `dependsOn` edge (that's often the point: an
  override or best-effort refresh that intentionally points "backwards")
- never disqualifies a waypoint from being a milestone sink; only `dependsOn`
  entries within a milestone count towards the sink computation
- an unresolvable `softDependsOn` id is reported by `validate` (mirroring
  `dependsOn`'s unresolvable-id check), never silently dropped

Author soft edges as data in `roadbook.json`; never hand-draw a `-.->` line
into a generated `PHASE.md` or chart; the next regeneration wipes anything
not in the source data.

**Soft milestone members (`softMilestone: true`):** a waypoint-level flag
making the derived milestone-complete edge (`{waypoint} -.-> M{N}`) soft
instead of hard. The waypoint stays a member of its milestone (counted in
`donePct`, listed under the milestone) but:

- never gates milestone completion: anything depending on `M{N}` is
  satisfied without it
- its milestone-complete edge renders dotted and is exempt from the
  through-milestone acyclicity check
- it is never reported as `isMilestoneSink` by `ready`; closing it does
  not close the milestone

Use it for best-effort milestone work (eval coverage, polish) that should
stay visible in the milestone without holding up everything downstream.

## Status → colour table (canonical)

One palette for every projection, derived from the goblin theme. `STATUS_STYLE`
in `roadbook.py` is the machine-readable copy; `graph --mermaid` emits literal
hexes for PHASE.md (GitHub cannot resolve CSS vars) and `--palette vars` emits
semantic custom properties for the chart. Every colour is a theme token or a
mix of two from `templates/chart-theme.css` (the copied goblin theme): mix(a,
b, t) is t of token a over token b. Light fills are 8% washes over the pale
slip, dark ones 8% over the dark sheet; `test_roadbook.py`'s StatusDerivation
recomputes each from the theme CSS. Never restate colours in a skill;
regenerate diagrams from the CLI.

A node's label takes its `text` colour, which is its stroke except on an
inverted node (the milestone's exhibit panel, the gate's slime).

| Status | Theme ink | Light (fill / stroke / label) | Dark (fill / stroke / label) | Non-colour encoding | Semantics |
|---|---|---|---|---|---|
| `done` | moss (`ok`) | `#edf0e6` / `#3c6a1c` / stroke | `#2d3420` / `#a6d46a` / stroke | solid | finished, quietly |
| `todo` | faded ink (`ink-muted`) | `#f5f6f0` / `#4b5a3c` / stroke | `#272b1f` / `#a3ad8c` / stroke | solid | blank slate |
| in progress (a trail, see Trails) | ballpoint (`info`) | `#ebefef` / `#2d5a8c` / stroke | `#2b312a` / `#8db4e8` / stroke | solid + `▸` label marker | a scout is on it |
| `blocked` | rust (`danger`) | `#f5ece7` / `#a3361f` / stroke | `#342e20` / `#ff8a6b` / stroke | bold stroke | stop |
| `paused` | beetroot (`accent`) | `#f3eaea` / `#8c1d4c` / stroke | `#342e26` / `#ff86b4` / stroke | dasharray 4 3 | deliberately parked |
| `deferred` | ochre (`warn`) | `#f3efe4` / `#8a5a00` / stroke | `#31301e` / `#e0a84a` / stroke | dasharray 2 4 + italic | shelved for later |
| `out_of_scope` | ink half into `line` | `#fcfcf8` / `#686e57` / stroke | `#22261a` / `#969d82` / stroke | dasharray 2 2, struck label | struck from play; drawn only in the full graph, since `--omit-done` (the chart's diagram) drops it |
| gate (`external`) | slime | `#e9f1c0` / `#1d2718` / `#1d2718` | `#c5e13e` / `#c5e13e` / `#1d2718` | dasharray 4 3 + italic | outside our control |
| milestone (`mile`) | exhibit panel | `#1d2718` / `#1d2718` / `#e7e9cf` | `#0a0c07` / `#e3e8cc` / `#e3e8cc` | bold | structural marker |

Beetroot is also the chart's link and focus colour (the stamp); it marks a
paused waypoint only with the dashed border beside it. Every label clears
WCAG AA (4.5:1) on its own fill.

Mermaid class names match statuses (`todo`, `blocked`, `paused`, `deferred`,
`done`, `outOfScope`) plus `inProgress` for a waypoint on a trail in play,
`mile` and `external`. Legacy diagrams used `open`
for todo and Bootstrap-era hexes; regenerating via `graph --mermaid` replaces
both. classDef lines always come straight after the `graph LR`/`graph TD`
line; before it is a silent render failure.

The `out_of_scope` ink sits close to `todo`'s faded ink: it is as faint as it
can be while still clearing 4.5:1 on its own fill and 3:1 against both tier
backgrounds below. The dotted border and the struck label tell them apart.

Solid slime sits at a tier background's own luminance in light, so the light
gate is a pale slime wash, mix(slime, slip, .28), with an ink border; dark
keeps solid slime with `on-slime` ink.

### Tier backgrounds (tiered phases only)

A phase with a milestone in tier 1 or above (see Tiers) draws every node of
its dependency graph inside a subgraph for its tier, in `graph --mermaid` and
the chart alike. An untiered phase draws no subgraph, and its diagram is
unchanged. `TIER_STYLE` in `roadbook.py` is the machine-readable copy.

| Tier state | Family | Light (bg / label) | Dark (bg / label) | Non-colour encoding | Fires when |
|---|---|---|---|---|---|
| `underway` | raised sheet: mix(line, surface-raised, .25), dark .75 | `#cbcfac` / `#1d2718` | `#434a32` / `#e3e8cc` | solid border, state named in the label | every lower tier is done and this one holds unfinished work |
| `deferred` | cardboard: mix(card, slip, .5), dark mix(card, card-dark, .75) | `#d8c4a8` / `#1d2718` | `#5a4225` / `#f2e8d0` | dashed border, state named in the label | any lower tier still holds unfinished work |
| `done` | raised sheet (shares `underway`) | as `underway` | as `underway` | state named in the label | the tier holds no unfinished work; drawn only in the full graph, since `--omit-done` drops a finished tier whole (done and `out_of_scope` waypoints alike) |

The subgraph label reads `{tier} · {state}`, for example `Secondary ·
deferred`. A waypoint sits in its milestone's tier, a milestone in its own
and a gate in the lowest tier among the waypoints it gates.

A background is never a node colour. A node's fill is a near-white tint
(near-black in dark) and its stroke carries the hue, so the background is a
muted mid-tone between the two. Gates, enforced by `test_roadbook.py` in
light and dark alike: 3:1 or better against every node stroke and the
diagram's edge line, 1.35:1 or better against every node fill, 4.5:1 or
better for the tier's own label. 3:1 against the fills is out of reach: a
background that dark would hide the edges. The border and the label carry
the tier's state without colour.

## Milestone-level state (chart only)

A milestone has no `status` field; it is not itself a waypoint. The chart
derives a milestone-level state from its member waypoints' status counts,
purely for the chart's own colour (`roadbook.py`'s `milestone_state()`; never
written back to `roadbook.json`, never used by `recompute`). The milestone
sort is a separate computation that never reads `state` (see Milestone sort
and tier grouping below). `validate` does separately flag an empty milestone
(see Empty milestones below), but that check reads waypoint counts directly
rather than going through `milestone_state()`. Six states (`deferred`
fires from two different rules); first true rule wins:

| State | Fires when | Colour |
|---|---|---|
| `empty` | zero waypoints (a bug, see below) | rust (shares the blocked hue) |
| `done` | every member `done`/`out_of_scope` | moss |
| `deferred` (tier cascade) | tier ≥ 1 and any milestone in a lower tier isn't `done` yet (see Tiers) | ochre (shares the waypoint-status hue) |
| `deferred` (member gate) | no actionable member (`todo`/`blocked`/`paused`) left, and ≥1 member is `deferred`; needs no tier suffix, only the cascade above does. Outranks done percentage: one deferred waypoint and nine done ones still reads `deferred` at 90% | ochre |
| `blocked` | stuck: work remains, every unfinished member (done/out_of_scope excluded) is `blocked` and no member shows in progress (`milestone_all_blocked()`). Outranks `inProgress` below it, so done work never softens it: 7 done and 1 blocked reads `blocked`, since nothing in the milestone can be picked up | rust |
| `inProgress` | ≥1 member `done`, or a member shows in progress (a trail). A trail on a blocked waypoint keeps the milestone here: a scout is on it | **ballpoint**: shared with waypoints on a trail |
| `todo` | otherwise | faded ink |

An all-`out_of_scope` milestone (struck-from-play) reads as `done`: nothing
remains actionable, whether it finished or was struck out. A tier's deferred
state cascades: a Tertiary milestone waits on every milestone in Secondary
being `done` too, in addition to Core (see Tiers). A plain, untiered
milestone can still read `deferred` too, from its own member gate rather
than the cascade: a milestone with one deferred waypoint and nine done ones is
"shelved" even though donePct is 90, the deliberate call outranking
percentage. This gate never fires while actionable work remains: a
milestone with five `todo` waypoints and one `deferred` one stays `todo`,
since those five are still live work to pick up. `paused`
is no longer a milestone-level state (a paused member falls through to
`blocked`/`todo` on its own merits); it remains a waypoint-level status.

### Empty milestones

A milestone with zero waypoints is a bug, never a legitimate `todo`/empty state
to render quietly: `roadbook.py validate` reports `{id}: milestone has no
tasks` (exit 1), and the chart's validation banner surfaces the same line.
It still renders (`empty`, rust, "No tasks") so the chart stays usable
while the roadbook is fixed, and it never counts as "unfinished" for a tier
cascade: an empty tier-0 milestone must not permanently defer every later
tier, since that would hide the real problem behind a wrong colour instead
of surfacing it.

## Waypoint counts: in scope only

Every done/total readout and every `donePct` counts in-scope waypoints: the
total less each `out_of_scope` one (`roadbook.py`'s `_in_scope()`, carried as
`inScope` on the phase and on each milestone in `stats --json`). A waypoint
struck from play is neither done nor outstanding, so it leaves both sides of
the fraction. This holds for the `stats` line, the chart's headline, its
per-tier readouts and its milestone counts alike.

`total` stays the raw waypoint count, struck waypoints included: it is what
the `N waypoints across M milestones` header in `ROADBOOK_OVERVIEW.md` reports
(`N tasks across M milestones` in a `ROADMAP_OVERVIEW.md` written before
3.0.0) and what `milestone_state()` reads. A milestone whose every waypoint is
`out_of_scope` has `inScope` 0: its `donePct` reads 100 (`_done_pct()`: waypoints
but none in scope means nothing left to do), the chart prints `Out of
scope` for it, never `0/0`, its progress bar fills to match its `done` colour
and it sorts with the fully-100% milestones. The same rule covers a tier
group or phase struck out whole. A milestone with no waypoints at all stays at 0
(state `empty`, see above).

## Milestone sort and tier grouping (chart only)

`roadbook.py`'s `overview_layout()` computes the Overview and Milestones
sections' shared sort and tier grouping once, server-side; the template
renders it as given and never re-sorts or re-groups. Milestone sort, each
layer breaking ties in the one before:

1. partially done (`0 < donePct < 100`) before fully-0% before stuck
   (state `blocked`, whatever its `donePct`) before fully-100%. A stuck
   milestone holds nothing to pick up, so it sorts behind every milestone
   that does. The sort reads the milestone's `state`, never
   `milestone_all_blocked()` directly, so the tier cascade governs both: a
   Secondary milestone blocked while Core still has open work is coloured
   `deferred` and sorts as deferred, beside its 0% siblings rather than
   behind them
2. tier, ascending (Core first)
3. `donePct`, descending
4. milestone id, natural order (`M2` before `M10`)

A phase with no tiered milestone (see Tiers) gets one flat, unwrapped list in
that order; no tier markup renders at all. Otherwise every milestone groups
under its tier's `<details>`, each carrying the scout chips of everyone
assigned a waypoint in it (done waypoints included) on its summary line. In
the Overview section each tier header also carries that tier's own readout
(`Core · 20/45 Tasks · 44% Complete · 0/6 Milestones`), summed from its
members into the group's `stats`; the Milestones section's tier headers
keep the bare tier name. Group
order: expanded groups first, then groups with any not-done milestone, then
all-done groups; ties break by tier index. A group's own `all-done` reading
excludes nothing (an `empty` member keeps its group out of the all-done
rank, distinct from the tier-cascade's own "empty never blocks" rule above).

## Scout-chip colour (chart only)

Assignee is free-text with no roster (see below) and never inferred, so the
chart never maps a scout's name to a colour by hand. `roadbook.py`'s
`dev_colour()` hashes the lowercased, trimmed assignee string with
`zlib.crc32` (never Python's builtin `hash()`, which is salted per
`PYTHONHASHSEED` and would assign a different colour to the same scout across
separate render runs) into the theme's five inks: beetroot (`accent`), moss
(`accent-2`), ballpoint (`info`, named `biro`), ochre (`warn`) and rust
(`danger`), each on an 8% wash of itself. These are the status inks too, so
a chip is told from a status by its shape, a named pill, never by colour
alone.

## Codebase reconciliation (inference)

Inference (deciding a waypoint's status from the actual code rather than the
dependency graph) lives in exactly one place: `goblin-scout:tend-roadbook`'s
reconciliation step. Every other status change is mechanical (see above).
This is deliberately narrow so the rest of the family can keep treating
status as computed, not judged.

**What inference may propose**, never write directly:

- **`done`**: the waypoint's described feature is fully implemented in code.
- **Dependency/gate edge removal**: a blocker's prerequisite is now
  satisfied, so the edge is removed from `dependsOn` (and a gate's `blocks[]`
  in step); recompute then unblocks the waypoint, same as any other edit to
  the graph.

Nothing else. Inference never hand-sets `todo`, `blocked`, `paused` or
`deferred` directly; those stay purely derived. It never re-opens `done`,
flips `out_of_scope`, disturbs a root-seeded held status or starts or drops a
trail (a trail is a person's statement).

**Evidence rule:** positive, specific, whole-waypoint evidence only. Absence of
a match is never evidence of completion. A waypoint whose feature is only
partly built is left as-is (inference never starts a trail on it; see Trails)
rather than marked done. Corroboration (a passing test, a real call-site)
outweighs a lone definition.

**Candidate seeding (efficiency):** only non-terminal waypoints (`todo`,
`blocked`, `paused`; never `done`/`out_of_scope`/`deferred`) are candidates:
waypoints on a trail first (`ready --json`'s `claimed`, the likeliest to be
built already), then the rest ordered by leverage (`ready --json`'s
`candidates`). Search is bounded to files changed
since the last reconciliation (or a recent window on first run), with 1–3
targeted search terms drawn from each candidate's description/notes, never
a whole-tree scan.

**Confirmation gate:** every proposed edit is shown with its evidence and
applied only once approved, mirroring the proposal-then-write pattern in
`goblin-scout:add-waypoints`. Discrepancies found in the other direction (a
waypoint marked `done` whose code can no longer be found) are reported as
drift, never auto-reverted; absence still isn't evidence.

## File formatting

- `roadbook.json`: tab indentation, `ensure_ascii` off, trailing newline
  (`recompute` refuses to write non-canonical files without `--reformat`)
- `docs/artefacts/chart-*.html` (or the phase's `artefact` path): `render`'s
  own canonical form (tabs, single-line JSON payload); a formatter's form
  would differ. A repo running Prettier (or another formatter) in a hook or
  CI should exclude the chart glob from it, the same way
  `.claude/roadbook.json` is excluded, so regenerating the chart never fights
  the formatter. A project that predates 3.0.0 keeps its chart at
  `docs/artefacts/roadmap-*.html` (pinned in `artefact`), so its existing
  exclusion still applies.
- Chart path resolution, one resolver shared by `render` and
  `recompute --render`: `--out PATH` > the phase's `artefact` key, relative to
  the project root > `docs/artefacts/chart-{slug}.html`, the slug being the
  phase name lower-cased with runs of non-alphanumerics collapsed to `-`. A
  file still under its pre-3.0.0 name, `roadmaps.json`, renders to the 2.x
  default `docs/artefacts/roadmap-{slug}.html` instead, which is the path the
  move pins in `artefact`. A
  project that ignores `docs/artefacts/` in `.gitignore` and wants a custom
  path checked in un-ignores that file itself; the plugin never edits
  `.gitignore`. Moving the path leaves the old file where it was (`config`
  says so); deleting it is the project's job too.
- Version stamp: every write to `roadbook.json` sets `min_plugin` (a
  `major.minor.0` string, after `artefact` in field order) on each non-archived
  phase, and `render` embeds `pluginVersion` in the chart's payload. A plugin
  older than a phase's `min_plugin`, or than the chart it would overwrite,
  refuses with exit 2 and writes nothing. Reads (`validate`, `ready`,
  `recompute --check`) still work. The stamp moves only on a newer minor
  release, so patch releases never touch the file. Plugins before 2.7.0 ignore
  the key, so the guard protects only from the first release that wrote it.
- Waypoint field order: `id, description, status, dependsOn, softDependsOn?, softMilestone?, iterative?, notes?, assignee?, started?, ended?, pr?`
- `assignee` (the scout) is free-text (no roster/validation), omit-when-empty
  like `notes`. Never inferred: a skill setting it must ask, never guess from
  description, git author, category or who's running the skill.
- `started` is the trail date (see Trails), omit-when-empty; `claim` and
  `release` keep the field order.
- `ended` is the finish date (see Ended dates), omit-when-empty, only valid
  on a `done` waypoint; `end`, `stamp-ended` and `backfill-ended` keep the
  field order.
- `pr` is an optional integer: the GitHub PR number that ships the waypoint,
  worth setting by hand when a waypoint ships. It lets a later run detect that
  a `done` dependency is still unmerged and stack a dependent branch on it
  instead of branching from main. It is never
  a status signal: `done` still means done whether merged or not, and
  `recompute` ignores the field entirely.
- Milestone field order: `id, name, goal, tasks`. Only `id` is enforced by
  `roadbook.py` (`_require_id`); `name` and `goal` default to empty strings
  everywhere else. Don't add fields beyond these four.
- Milestone ID assignment: `M{max existing milestone number in the phase + 1}`,
  same never-reuse rule as waypoint IDs. Milestones have no `dependsOn` field
  of their own; a milestone-level gate is expressed on the waypoint(s) inside
  it (`dependsOn: ["M{a}"]` on the waypoint, never on the milestone object).
  Appending a milestone at the end of the sequence is unambiguous; nothing yet
  defines what happens on a mid-sequence insertion, since `M{N}` numbering is
  loosely coupled to waypoint-ID category prefixes elsewhere in the roadbook
  (a category can span several milestones): treat that as an open question
  until a real need forces the decision, and invent no rule on the spot.
- Gate field order: `id, name, status, imposes?, blocks[], notes?`
- Phase field order: `name, path, project?, artefact?, archived?, externalGates, milestones`
- `project` is optional free text naming the project the phase belongs to
  (distinct from `name`, which names the phase, e.g. "MVP"). The
  chart's `<h1>` reads `{project}: {phase}`; when `project` is absent the
  chart falls back to the project root directory name (`render`'s
  `_project_name()`), so no migration is needed for existing roadbooks.
- `artefact` is optional: where this phase's chart is written, as a path
  relative to the project root like `path` (e.g.
  `docs/artefacts/chart-t1c.html`). Absent, the slug default applies.
  Set and cleared by `roadbook.py config artefact` (the
  `goblin-scout:configure-roadbook` skill), never by hand: `validate` reports
  an absolute path, a `..` segment or a non-`.html` suffix as a discrepancy,
  and `render` refuses to write such a path.
- British spelling in all descriptions, notes and prose projections
- PHASE.md waypoint lines: `- [ ] **{ID}**: {description}` with annotations: none
  when `dependsOn` empty; `_(depends on {IDs})_` when all deps done;
  `_(blocked: depends on {IDs})_`; `_(paused: reconvene {gateId})_`;
  `_(deferred to a later phase)_` when the deferral is out of this phase
  entirely. A waypoint deferred *within* the current phase by a tier-release
  gate (see Tiers below) instead uses `_(deferred: {gateId}, and every {tier}
  milestone)_` on the tier's entry waypoint and `_(deferred: follows {ID})_`
  on each waypoint chained behind it: "a later phase" would be false when the
  work is still this phase's, gated on the envelope rather than the calendar.

### Tiers

A phase may split into tiers (e.g. core/secondary/tertiary) released one
after another by gate, not by date. Two shapes carry the gate; a project
picks one and keeps to it:

- **Entry waypoint.** The tier's entry waypoint depends on every milestone in
  the tier(s) before it plus that tier's release gate (`imposes: "deferred"`),
  and every other waypoint in the tier chains behind the entry waypoint via
  ordinary `dependsOn`. This is the one case a root-seeded parked status
  doesn't fit: root-seeding only holds for empty `dependsOn`, and a tier's
  waypoints depend on the whole of the tier(s) before them, so the gate is
  what keeps them `deferred` under `recompute` rather than escalating to
  `blocked` the moment their nominal deps are all `done`. See the deferred
  annotation forms above for how this renders in PHASE.md.
- **Milestone list.** Every waypoint in the tier carries the lower-tier
  milestones it waits on directly, with no release gate and no entry waypoint:
  `["M7", "M8", "M9", "M10", "M11"]` on each tertiary waypoint, or only the
  milestones that matter (`["M1", "M6"]` on a secondary waypoint whose project
  gates on identity and hardening alone). The siblings are the template: a
  new waypoint copies the list its milestone's existing waypoints carry, and
  the first waypoint in a new milestone copies the gate its tier's other
  milestones carry.

**A tier reaches a lower tier by milestone, never by waypoint.** A waypoint in
tier N lists the gate above plus waypoints of its own tier in `dependsOn`, and
nothing from a lower tier by waypoint ID: `13SE.5` carrying `["M10", "10SE.4"]`
is wrong, since M10 `done` already means 10SE.4 `done`, so the waypoint edge
adds nothing and breaks the pattern its siblings follow. The relationship
still matters, so it goes in `notes` (`Extends 10SE.4`, the idiom every
tiered waypoint uses for the lower-tier work it builds on). `validate` reports
a lower-tier waypoint edge the waypoint already requires through another entry
(a milestone, or a waypoint that reaches it) as a discrepancy, naming the
entry that covers it. Two shapes it leaves alone: a milestone entry the
waypoint also reaches through a sibling (`["M1", "M6", "8RT.9"]` is the
pattern itself, even though 8RT.9 carries M1 and M6 too) and a lower-tier
waypoint edge nothing else covers, which may be a deliberate fast-track. An
uncovered prerequisite has two homes, and the waypoint edge is neither: a
waypoint that keeps its tier adds the prerequisite's milestone to its copied
gate (`["M7", "M8", "M9"]` where the siblings carry `["M7", "M8"]`) and notes
`Extends {ID}` as usual; a waypoint that is meant to escape its tier (wanted
soon, so it waits on no lower-tier milestone) carries no gate at all and
says so in `notes`. A `softMilestone` member is the one lower-tier waypoint
its milestone does not cover by membership: a soft member does not gate
milestone completion (see Soft milestone members above), so neither `M10`
in the gate nor M10 added to it reaches a soft `10SE.7` by membership.
That waypoint edge stays in `dependsOn` next to the gate, and `validate`
leaves it alone, unless a hard member of M10 (or anything else the gate
requires) depends on 10SE.7, directly or through other waypoints: the gate
then waits on it after all, so the edge goes and `validate` reports it if
it stays. M10 joins the gate only when the sole path to 10SE.7 runs
through a hard member of M10 and the copied list lacks M10; when an entry
already in the gate reaches it, the gate stays as copied.

**Naming.** The chart reads a milestone's tier from a suffix on its
`name`, case-insensitive, trailing: `(Secondary)`, `(Tertiary)`,
`(Quaternary)`, `(Quinary)` (`roadbook.py`'s `milestone_tier()`). No suffix is
tier 0, labelled Core (`tier_label()` spells every tier name; the vocabulary
is core, secondary, tertiary). It drives the Overview/Milestones tier
grouping and the `deferred` colour cascade (see Milestone-level state
above) and the cross-tier edge check in `validate`; `recompute` never
consults it, relying entirely on the gate-based mechanics above. A tier
group in the chart expands only once every milestone in every lower tier
is `done`, and only when it also holds a ready or in-progress waypoint; a tier
that isn't open yet stays collapsed regardless of what it contains.

## The three artefacts

| File | Role | Regenerated by |
|---|---|---|
| `.claude/roadbook.json` | source of truth | `recompute` (statuses only) |
| `docs/roadbook/{PHASE}.md` (the phase's `path`; `docs/roadmaps/` in a project that predates 3.0.0) | waypoint-list projection + Mermaid diagram | skill prose + `graph --mermaid --direction LR` for the diagram block |
| `docs/reports/ROADBOOK_OVERVIEW.md` (`ROADMAP_OVERVIEW.md` in a project that predates 3.0.0) | prose overview | skill prose; header counts from `stats` |
| `docs/artefacts/chart-{slug}.html`, or the phase's `artefact` path | the chart (interactive HTML page) | `render` (fully deterministic; `recompute --render` refreshes it) |

## Which skill when

| Situation | Skill |
|---|---|
| No roadbook yet | `goblin-scout:start-roadbook` |
| Old single-file roadmap format detected | `goblin-scout:rebind-roadbook` |
| Half-formed ideas to explore into waypoints | `goblin-scout:plan-expedition` |
| One known waypoint to add | `goblin-scout:add-waypoints` (`t` mode) |
| Several waypoints with an asserted dependency order | `goblin-scout:add-waypoints` (`c` mode) |
| New milestone needed | `goblin-scout:add-waypoints` (`m` mode) |
| Starting or dropping work on a waypoint | `goblin-scout:start-trail` (`[waypoint id] [scout\|release]`) |
| Waypoints need owners, or a scout's load needs handing over | `goblin-scout:assign-scouts` (`ready\|open` horizon, `free\|taken\|all\|<scout>` scope, optional `<phase>:<tiers\|milestones\|focus>` slice) |
| Work landed / statuses drifted | `goblin-scout:tend-roadbook` (add `reconcile` to check against code) |
| Mark a waypoint in progress, or stop working on one | `goblin-scout:tend-roadbook` (runs `claim` / `release`; the hooks usually offer the trail first) |
| Priorities / freshness / health / dependency-graph review | `goblin-scout:review-roadbook` (lens: `health`, `deps` or default full) |
| Render the chart | `goblin-scout:unroll-chart` |
| Choose the next waypoint (one pick) | `goblin-scout:suggest-waypoint` |
| See the whole ready-set | `goblin-scout:survey-waypoints` |
