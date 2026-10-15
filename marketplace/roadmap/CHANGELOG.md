<!-- generated 2026-09-30 by the goblin-mode changelog tooling. Delete this line once you hand-edit this file. -->
# Changelog

All notable changes to this project are documented here, newest first.

## [Unreleased]

## [2.7.0] - 2026-10-15

### Added

- Every write to `roadmaps.json` stamps each non-archived phase with `min_plugin` (`major.minor.0`), and `render` embeds `pluginVersion` in the dashboard. A plugin older than a phase's stamp refuses to write (exit 2, file untouched), and `render` refuses to overwrite a dashboard from a newer plugin. Reads still work on a newer file. The stamp moves only on a newer minor release.

### Changed

- Plugins before 2.7.0 ignore `min_plugin` and `pluginVersion`, so the guard protects only plugins from this release onward. A project with contributors on 2.6.0 or earlier needs a repo-side check for stray dashboard files until they update.
- A first write after upgrading adds one `min_plugin` line to each live phase; the 2.7.0 diff of `roadmaps.json` shows nothing else.

## [2.6.0] - 2026-10-14

### Added

- A phase's `artefact` key names where its HTML dashboard is written, as a path relative to the project root. `render` and `recompute --render` share one resolver: `--out`, then the key, then `docs/artefacts/roadmap-{slug}.html`. Without the key every existing roadmap behaves as before.
- `roadmap.py config artefact PATH [--phase NAME]` writes the key in field order without touching anything else, and `--clear` removes it. An absolute path, a `..` segment or a non-`.html` suffix is refused; `validate` reports a hand-edited one as a discrepancy and `render` refuses to write it.
- `roadmap:configure artefact <path>|clear [phase]` runs `config` and then one `render`, so the file exists at the new path before the skill reports.
- `render --phase` and `config --phase` accept an archived phase, so its dashboard can be regenerated or re-homed. `ready`, `recompute` and `claim` still see active phases only.

### Fixed

- `recompute --render` wrote to the slug path even when a project's dashboard lived elsewhere, and reported no artefact.

## [2.5.0] - 2026-10-12

### Changed

- `claim` takes a blocked task when the work is stacked on the work that unblocks it: every unmet blocker (an unfinished `dependsOn` task, an unfinished member of a milestone in `dependsOn`) already carries `started` in the roadmap file being edited. A gate still in `dependsOn` always refuses, as does a gate that is not done and lists the task in `blocks`. The refusal names the blockers that are not claimed. CHIRPdb's Jira sync is stricter, since it also checks that the claim sits on the same branch or an ancestor, so a blocker claimed on `main` alone passes `claim` but not the sync.

## [2.4.0] - 2026-10-09

### Added

- `roadmap.py assign` sets or clears a task's assignee without claiming it.

### Fixed

- The `/ready` pane can replace an assignee, assign without claiming and act on a claim past the ninth row.

## [2.3.0] - 2026-10-08

### Added

- `/ready`, a mod that was the separate `roadmap-pane` plugin: the ready set in a pane with the claims in play and milestone progress by release tier, refreshed from the plugin's CLI without a turn. A digit picks a row, `c` claims it after asking who and `r` refreshes; `/ready` again closes it. The pane follows the session's working directory, so a move into a worktree reads and claims against that worktree's `roadmaps.json`. Without a roadmap, with an old-format one or when the CLI refuses, it draws a card that says what happened and names the skill that fixes it. Needs Claude Code 2.1.287 or later and draws in the terminal.

### Changed

- The plugin is hand-maintained under `marketplace/roadmap/` instead of being built from skills in the goblin-mode config, so there is one copy of every skill. The CLI's tests, the prose roadmap template and an example roadmap ship with it.

## [2.2.0] - 2026-10-08

### Changed

- `/roadmap-claim` passes the assignee as `--assignee="{name}"`, so a name that starts with a dash is recorded as a name instead of read as an option.
- The refusal for an old single-file `roadmaps.json` reads `run the roadmap migrate skill first` and names no slash command.
- The readme points to `roadmap-pane@goblin-mode` for the ready set as a pane with claim buttons.

### Fixed

- `roadmap.py` drops a milestone's terminal edge when other hard edges already reach that milestone. Task edges and soft edges are untouched, and a milestone always keeps at least one inbound edge. The conventions reference documents the exception.

## [2.1.0] - 2026-10-05

### Changed

- Next Up cards on the dashboard share one three-row layout: milestone and task labels, then the description, then three counts for what finishing the task frees. `▶` counts tasks ready the moment it is done, `◐` counts tasks that still wait on something else and `↓` counts tasks further downstream. A legend explains the icons, the dev label no longer repeats under its own heading and faint dividers separate each dev's group.
- `/roadmap-update-devs` prints its sections under headings and its lists as bordered tables, with the task description in the last column so it wraps inside its cell. The reply grammar prints once, before the first batch.
- `roadmap.py ready` reports `unblocksNow`, `unblocksPartly` and `unblocksLater` for each candidate. A soft milestone member no longer counts as unblocking its milestone's dependents, so `transitiveUnblocks` drops for those tasks and they rank lower in the ready set.

## [2.0.0] - 2026-10-02

### Breaking

- `/roadmap-update-devs` arguments change with no aliases: the `all` horizon is now `open` and the `devless` scope is now `free`. Anything that calls the old forms needs updating.

### Added

- `roadmap.py ready` takes `--milestones` or `--tiers` (mutually exclusive; `--tiers focus` picks the tier now underway), and a new `open` subcommand lists every task not done or out of scope with the same filters.
- `/roadmap-update-devs` arguments are all optional and default to `ready free current:project`. A third argument, `<phase>:<filter>`, narrows the list to a project, the focus tier, chosen tiers or chosen milestones. The resolved call is echoed before the interview starts.
- Tasks record when they finished. A new optional `ended` field comes with `end ID`, `stamp-ended --base REF --pr N` and `backfill-ended`, and `validate` rejects an `ended` that is malformed, set on a task that is not done or earlier than `started`.
- `/roadmap-maintain` backfills missing `ended` dates from git history in a new step 3b, offering `first-seen` rows separately because their date is only a lower bound.
- `/roadmap-claim` claims a roadmap task when work starts and releases it when work stops, asking who is doing it. The claim nudge and the other roadmap skills now point at it.

### Changed

- The dependency diagram in the dashboard leaves out `out_of_scope` tasks as well as done ones, along with the milestones and tiers they leave empty.

### Fixed

- `stamp-ended` refuses to run when the merge-base copy of the roadmap has no phase of the active name, instead of stamping every done task as finished by the branch.
- `backfill-ended` skips and reports a task whose date would precede its `started`, rather than writing a file that fails `validate`.
- `/roadmap-claim` handles a `roadmaps.json` the CLI refuses to rewrite.

## [1.0.0] - 2026-09-30

The plugin's API is declared stable: `stats --json`, `graph --mermaid`, the render data the dashboard reads and the milestone state vocabulary. No behaviour changes from 0.2.0; from here, a change to any of those surfaces is a major bump.

## [0.2.0] - 2026-09-30

### Breaking

- `stats --json` measures `donePct` against in-scope tasks (the total less every `out_of_scope` task) rather than the raw total, and reports 100 rather than 0 for a milestone, tier or phase whose tasks are all out of scope.
- A milestone whose every unfinished task is blocked, with no claim in play, now reports state `blocked` where it reported `inProgress`; done work no longer softens it.
- `graph --mermaid` wraps each tier of a tiered phase in its own subgraph, so PHASE.md diagrams change shape at their next regeneration.
- `tierLabel` in the dashboard render data reads `Core` where it read `Primary`; the tier vocabulary is now core, secondary and tertiary in every projection.
- The out-of-scope node stroke changes to `#717171` (light) and `#898989` (dark) in every projection.

### Added

- Each tier header in the dashboard Overview carries its own readout (done, in-scope tasks, percentage and milestones) in the same shape as the phase headline.
- The dependency graph draws each tier of a tiered phase as a labelled subgraph: slate for a tier underway, taupe with a dashed border for one still deferred. The legend gains two tier swatches for tiered phases.

### Changed

- The dashboard Overview opens expanded, so the headline and progress cards show without a click.
- Task counts everywhere (stats line, dashboard headline, milestone counts) leave out-of-scope tasks out of both sides of the fraction, so a struck task is neither done nor outstanding.
- Inside each milestone the Blocked, Done and Out of Scope groups fold away by default, each with its task count in the heading.
- A stuck milestone sorts behind every milestone with actionable work and ahead of the finished ones, keyed on the same state that colours it, so colour and position agree; a tier-deferred milestone stays with its deferred siblings.
- Skill frontmatter `model` levels refreshed.

### Fixed

- A milestone struck out whole draws a full progress bar rather than a green bar at 0% width.
- The task count sits at the far right of every milestone summary, with or without dev chips.

## [0.1.0] - 2026-09-28

### Breaking

- The dashboard's milestone colour rules are rewritten: an empty milestone flags as its own bug state instead of reading as todo, deferred status cascades through release tiers, and `paused` drops out of milestone-level state (it now applies only to individual tasks). `stats --json`'s `milestones[].state` no longer includes `paused`, and `empty` and `deferred` mean something different than before.

### Added

- Initial shareable Roadmap plugin: a dependency-graph roadmap system (JSON source of truth, mechanical status recompute, projected task lists, Mermaid diagrams, an HTML dashboard) packaged for distribution via the goblin-mode marketplace.
- Claim hooks: record a `started` date when work begins on a task's branch, and show claimed tasks on the dashboard, so in-progress work is visible before it's done.
- The plugin carries its own version number, tracked separately from the root repo's.
- Release tiers, read from a `(Secondary)` or `(Tertiary)` suffix on a milestone's name: the dashboard groups milestones by tier within a phase, in collapsible sections that expand once a tier is live, with dev chips showing who's assigned work in each milestone.
- The dependency graph's layout direction (top-down or left-right) is chosen per render from the shape of the graph.
- `next-group` can group tasks by dev, alongside milestone and topic.
- `validate` flags a milestone with zero tasks.

### Fixed

- The claim hooks stay quiet when they can't confidently tell whether a claim applies, instead of guessing.
- The plugin build keeps an unresolvable plugin root out of the build, instead of shipping a broken path.
- `roadmap:review` uses its own CLI path instead of a shared one.
- A milestone with a deferred task and no other actionable work shows as shelved instead of todo or in-progress.
- The dashboard's Overview grid no longer collapses a tiered phase's milestones into a single narrow column.
- Three skills are synced to the conventions reference.

[Unreleased]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v2.6.0...HEAD
[2.6.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v2.5.0...roadmap-v2.6.0
[2.5.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v2.4.0...roadmap-v2.5.0
[2.4.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v2.3.0...roadmap-v2.4.0
[2.3.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v2.2.0...roadmap-v2.3.0
[2.2.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v2.1.0...roadmap-v2.2.0
[2.1.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v2.0.0...roadmap-v2.1.0
[2.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v1.0.0...roadmap-v2.0.0
[1.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v0.2.0...roadmap-v1.0.0
[0.2.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v0.1.0...roadmap-v0.2.0
[0.1.0]: https://github.com/JasonWarrenUK/goblin-mode/releases/tag/roadmap-v0.1.0
