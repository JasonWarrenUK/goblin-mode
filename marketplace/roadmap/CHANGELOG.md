<!-- generated 2026-09-30 by the goblin-mode changelog tooling. Delete this line once you hand-edit this file. -->
# Changelog

All notable changes to this project are documented here, newest first.

## [Unreleased]

### Added

- `/ready`, a mod: the ready set in a pane with the claims in play and milestone progress, refreshed from the CLI without a turn. A digit picks a row, `c` claims it after asking who, `s` submits the `start_command` option for it. Needs Claude Code 2.1.287 or later; draws in the terminal.

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

[Unreleased]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v1.0.0...HEAD
[1.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v0.2.0...roadmap-v1.0.0
[0.2.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-v0.1.0...roadmap-v0.2.0
[0.1.0]: https://github.com/JasonWarrenUK/goblin-mode/releases/tag/roadmap-v0.1.0
