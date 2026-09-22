<!-- doc-changelog: generated 2026-08-27. Delete this line once you hand-edit this file. -->
# Changelog

All notable changes to this project are documented here, newest first.

## [Unreleased]

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

[Unreleased]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.3.0...HEAD
[2.3.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.0.0...v2.3.0
[2.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v1.1.0...v2.0.0
