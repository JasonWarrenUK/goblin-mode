<!-- generated 2026-09-25 by the goblin-mode changelog tooling. Delete this line once you hand-edit this file. -->
# Changelog

All notable changes to this project are documented here, newest first.

## [Unreleased]

### Added

- Initial shareable Roadmap plugin: a dependency-graph roadmap system (JSON source of truth, mechanical status recompute, projected task lists, Mermaid diagrams, an HTML dashboard) packaged for distribution via the goblin-mode marketplace.
- Claim hooks: record a `started` date when work begins on a task's branch, and show claimed tasks on the dashboard, so in-progress work is visible before it's done.
- The plugin now carries its own version number, tracked separately from the root repo's.

### Fixed

- The claim hooks now stay quiet when they can't confidently tell whether a claim applies, instead of guessing.
- The plugin build now keeps an unresolvable plugin root out of the build, instead of shipping a broken path.
- `roadmap:review` now uses its own CLI path instead of a shared one.
