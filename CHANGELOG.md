<!-- doc-changelog: generated 2026-08-27. Delete this line once you hand-edit this file. -->
# Changelog

All notable changes to this project are documented here, newest first.

## [Unreleased]

### Added

- `goblin-util`, two mods: `/pain` appends a pain point to `library/state/cc-pain-points.json` without a turn, with the repo, branch and last failed tool call pre-filled, as a typed line or from a small pane; `/fleet` shows every session on the machine from a heartbeat in the plugin's shared store and sends a picked session a message. One `enabled` switch. Served as `goblin-util@goblin-mode`.

## [6.1.0] - 2026-10-04

### Added

- `goblin-chrome`, the first mod: goblin-mode's face inside the terminal. A goblin in the band that paces, sits, sleeps, startles and watches beside the tier's rune; the turn's closing line and the hint tail in its register; a face above every question; frames by the model tier that served the request; a nine-state day on the local clock; colours from the project theme. One `enabled` switch. Served from the repo's marketplace as `goblin-chrome@goblin-mode`.
- `docs/reference/mods.md`: how a mod is laid out here, how to check one and the conventions the mods follow.

## [6.0.0] - 2026-10-02

### Breaking

- `/roadmap-update-devs` arguments change with no aliases: the `all` horizon is now `open` and the `devless` scope is now `free`. Anything that calls the old forms needs updating.
- `/hud-worktrees` is read-only. `new` and `clean` are gone; use `/branch-worktree new` and `/branch-worktree prune`.
- The roadmap plugin moves to `roadmap-v2.0.0`, which is what carries the root series to a major version. The two argument changes above are the plugin's breaking surface.

### Added

- `roadmap.py ready` takes `--milestones` or `--tiers` (mutually exclusive; `--tiers focus` picks the tier now underway), and a new `open` subcommand lists every task not done or out of scope with the same filters.
- `/roadmap-update-devs` arguments are all optional and default to `ready free current:project`. A third argument, `<phase>:<filter>`, narrows the list to a project, the focus tier, chosen tiers or chosen milestones. The resolved call is echoed before the interview starts.
- Tasks record when they finished. A new optional `ended` field comes with `end ID`, `stamp-ended --base REF --pr N` and `backfill-ended`, and `validate` rejects an `ended` that is malformed, set on a task that is not done or earlier than `started`.
- `/pr-land` stamps end dates onto the PR branch before the merge (Step 1.6), and `/roadmap-maintain` backfills missing dates from git history in a new step 3b, offering `first-seen` rows separately because their date is only a lower bound.
- `/roadmap-claim` claims a roadmap task when work starts and releases it when work stops, asking who is doing it. The claim nudge and the other roadmap skills now point at it.
- `/branch-worktree new` creates a worktree under `.claude/worktrees/` and moves the session into it; `/branch-worktree prune` clears merged worktrees, plus idle worktrees whose branch is still open (the branch stays), stray directories and heavy leftovers such as `.venv`.
- `worktree-state.sh` reports a worktree's dirty count and ahead/behind as JSON for the read-only map.

### Changed

- The dependency diagram in the roadmap dashboard leaves out `out_of_scope` tasks as well as done ones, along with the milestones and tiers they leave empty.
- Routine verification subagents in `/pr-handle_review` run on Sonnet.
- The stacked-PR docs and skills use commands Claude can run without a terminal: `gh stack link <stack#> <pr>` to append a PR, `-m` on `gh stack add` and `--open` on submit.

### Fixed

- `stamp-ended` refuses to run when the merge-base copy of the roadmap has no phase of the active name, instead of stamping every done task as finished by the branch.
- `backfill-ended` skips and reports a task whose date would precede its `started`, rather than writing a file that fails `validate`.
- `/pr-land` never runs a bare `gh stack merge`, which merged every layer of a stack including those above the approved PR; Step 2 now always names the PR.
- `/roadmap-claim` handles a `roadmaps.json` the CLI refuses to rewrite.
- `worktree-state.sh` exits 2 when `git status` fails instead of reporting a modified worktree as clean.

## [5.0.0] - 2026-10-01

### Breaking

- The roadmap plugin is declared stable as `roadmap-v1.0.0`, which is what moves the root series to a major version. Nothing breaks in behaviour: `stats --json`, `graph --mermaid`, the dashboard render data and the milestone states are as they were in 4.0.0.

### Added

- PR descriptions gain a Verification section (what was run and what was not) and an optional WARNING alert for breaking changes, so neither crowds the Overview.
- `md-lint.py` checks GitHub-rendered Markdown for five layout faults: a `---` that turns the line above into a heading, text swallowed by a `</details>` block, a missing blank line after `<summary>`, backticks inside `<summary>` and doubled rules.
- A `PreToolUse` hook, `pr-body-lint.sh`, blocks `gh pr create` and `gh pr edit` when the body would render wrongly, whichever skill or ad-hoc command wrote it. Its entry in `settings.json` is not in git, so copy it onto any other machine (see `docs/reference/hooks.md`).

### Changed

- PR descriptions open with a 2-4 sentence plain-language Overview. The detail moves to Changes, where each block gives an intro, a reason per bullet and a Review line.
- `pr-create` and `pr-update` run the layout linter before showing a draft, and `pr-update` reshapes a body written to the older template: verification notes and breaking-change text move out of the Overview.
- The roadmap plugin ships as `roadmap-v1.0.0`.

### Fixed

- The PR template keeps a blank line around every rule and `<details>` tag. Without them a `---` turned the text above it into a heading (CHIRPdb #139) and a `---` under `</details>` printed literally (#26).

## [4.0.0] - 2026-09-30

### Breaking

- `roadmap.py stats --json` measures `donePct` against in-scope tasks (the total less every `out_of_scope` task) rather than the raw total, and reports 100 rather than 0 for a milestone, tier or phase whose tasks are all out of scope.
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
- Skill and agent frontmatter `model` levels refreshed across 18 files.
- The roadmap plugin ships as `roadmap-v0.2.0`.

### Fixed

- A milestone struck out whole draws a full progress bar rather than a green bar at 0% width.
- The task count sits at the far right of every milestone summary, with or without dev chips.

## [3.1.0] - 2026-09-29

### Added

- `checkout-occupied.sh` reports whether another live Claude session is working in a checkout. Its JSON lists each occupying session with the checkout's branch and its count of uncommitted files, and its exit code is 1 when the checkout is occupied.

### Changed

- `pr-land` now runs on opus; it ran on sonnet before.

### Fixed

- `pr-land` no longer runs `git checkout main` in your main checkout after a merge, a switch that sent another session's next commits to `main`. Post-merge work happens in a temporary detached worktree on `origin/main`, and the main checkout is fast-forwarded only when no other session is in it, it is on `main` and it has no uncommitted files.
- On a repo whose CI workflow tags on push, `pr-land` waits for that run and reports the tag CI created. It makes no tag of its own there.

## [3.0.0] - 2026-09-28

### Breaking

- The roadmap dashboard's milestone colour rules are rewritten: an empty milestone now flags as its own bug state instead of silently reading as todo, deferred status cascades through release tiers, and `paused` is dropped from milestone-level state (it now only applies to individual tasks). `stats --json`'s `milestones[].state` no longer includes `paused`, and `empty`/`deferred` mean something different than before.

### Added

- The roadmap dashboard groups milestones by tier within a phase, in collapsible sections that expand once a tier is live, with dev chips showing who's assigned work in each milestone.
- The dependency graph's layout direction (top-down or left-right) is now chosen automatically based on the shape of the graph, rather than fixed.
- `next-task-group` can now group tasks by dev, alongside the existing milestone and topic groupings.

### Fixed

- A milestone with a deferred task and no other actionable work now correctly shows as shelved instead of todo or in-progress.
- The dashboard's Overview section grid no longer collapses a tiered phase's milestones into a single narrow column.

## [2.6.0] - 2026-09-25

### Added

- Plugins can now carry their own version number and changelog, separate from the root repo's: `pr-land` bumps and tags a touched plugin alongside root, and `/doc-changelog plugin:NAME` builds that plugin's own changelog from its own source.

### Fixed

- `pr-land` checks out the PR branch before bumping its plugin's version, and now names the version script's own `--dir` flag instead of colliding with svu's.
- The roadmap plugin's changelog is now written beside its own hand-maintained sources, so a rebuild of the shipped plugin no longer wipes it out.
- The version script's untagged bootstrap path (picking a starting version when no tag exists yet) now only applies in plugin mode, leaving root-repo version resolution untouched.

## [2.5.0] - 2026-09-23

### Added

- Roadmap tasks can now record a claim: a `started` date set when work begins on a branch, shown on the dashboard, so in-progress work is visible before it's done.

### Fixed

- The claim hooks now stay quiet when they can't confidently tell whether a claim applies, instead of guessing.

## [2.4.0] - 2026-09-22

### Added

- A new shareable Roadmap plugin: generates a distributable roadmap dashboard plugin, listed in the goblin-mode marketplace, with its own README built from source and a build step that validates before writing.
- `clod-stack-gum` skill: guidance for building interactive shell prompts and styled terminal output with `gum`.

### Fixed

- The roadmap plugin build now keeps an unresolvable plugin root out of the build and quotes unshipped plugin paths correctly, instead of writing broken paths.
- `roadmap-review` now uses its own CLI path instead of a shared one.

## [2.3.0] - 2026-09-22

### Fixed

- `pr-land`'s check-status gate now defaults to blocking when a PR's check state can't be confidently read, instead of defaulting to allow.
- `pr-land` now blocks on pending (not just failing) checks, and locates the main checkout correctly instead of assuming the current directory.
- `pr-review` and `pr-review-dry_run` now leave a comment-only verdict when the reviewer is reviewing their own PR, rather than posting a blocking review against themselves.
- `pr-review` now treats blocking severity as a merge gate rather than a subjective judgement call, so the same finding gets the same verdict regardless of who's reading it.
- `pr-review-dry_run` now names its review-body anchors so repeat runs update the same anchors instead of duplicating them.
- `pr-create` pushes the branch before stamping its update watermark, and stamps that watermark from the actually-pushed commit rather than a stale local one.
- `pr-update` resolves the PR identifier correctly before acting on it, and now defaults to the current branch's own PR with the body read from stdin.
- `pr-handle_review` now uses the Agent tool and resolves repos by URL.
- `next-task-ship`'s self-review step now correctly matches a comment-only review outcome.
- `roadmap-maintain` now uses the Agent tool instead of the retired Task tool.

## [2.0.0] - 2026-08-27

### Breaking

- Dossier and persona profile files changed shape: `name` is now `slug`, `metadata.*` fields are flattened out, and `personaId`/`dossier_id`/`derived_from_updated` are replaced by `linkedProfileIds`. Every profile file also gained a stable `id` (e.g. `DOS001`, `PER002`) that links reference instead of a slug. Anything reading dossier or persona files directly needs to expect the new fields.

### Added

- **Themes**: a project can now declare its own colour theme (`theme-factory`, `theme-target`) instead of using the hardcoded Reasonable Colors palette: a core palette plus rationale, checked for completeness, contrast (AA/AAA) and originality against every other registered theme.
- **Asset generation**: a new `asset-*` skill family (`asset-shot`, `asset-demo`, `asset-still`, `asset-card`, `asset-pdf`) renders screenshots, demo GIFs, code stills, social cards and PDF previews, all styled from the resolved project theme.
- Every standalone artefact now ships a light/system/dark toggle control, not just the underlying three-state CSS: a reader can actually reach every theme state, not just have it picked for them.
- Stacked pull request support: a task whose dependency is done but not yet merged now stacks its branch and PR on the dependency's own branch, instead of either blocking or accidentally shipping without it. `pr-create`, `pr-land`, `pr-review-dry_run`, `branch-rename` and `hud-worktrees` all understand stacks now.
- `/hud-profiles`: browse dossier and persona profiles without editing either (`list`, `count`, `show <name>`).
- `/hud-cc_releases` and `/track-cc_pain`: paired skills that track Claude Code's own changelog against friction you've actually hit, so a "fixed" note only surfaces once it plausibly resolves something you've confirmed.
- A default reviewer persona (`goblin`) is used for `/red-doc` and `/red-branch` when none is named, instead of asking or refusing.

### Fixed

- Dark-mode roadmap diagrams: edges, arrowheads and edge-label backgrounds now follow the active theme instead of defaulting to a light-canvas appearance that was invisible on a dark background; an explicit light/dark toggle now redraws the diagram, not just a system-level scheme change.
- Theme validation's completeness check now actually diffs a theme against its template, so a theme missing an entire required block is caught with a clear report instead of crashing with an uncaught error further down the pipeline.
- Theme and asset-script command-line parsing no longer misreads a flag's value as a filename (or vice versa) when arguments are given in an unexpected order.
- A project with its own colour theme but no matching output file for what's being generated is now offered the right fix (`/theme-factory`) instead of silently falling back to the default global theme.
- The light/system/dark toggle control now correctly shows which option is active immediately on page load, not only after the reader clicks a button.

[Unreleased]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.1.0...HEAD
[6.1.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.0.0...v6.1.0
[6.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v5.0.0...v6.0.0
[5.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v4.0.0...v5.0.0
[4.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v3.1.0...v4.0.0
[3.1.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.6.0...v3.0.0
[2.6.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.5.0...v2.6.0
[2.5.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.0.0...v2.3.0
[2.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v1.1.0...v2.0.0
