# Changelog

All notable changes to this project are documented here, newest first.

## [Unreleased]

## [0.1.0] - 2026-10-08

### Added

- `/ready`, a mod: the ready set in a pane with the claims in play and milestone progress, refreshed from the plugin's own copy of the CLI without a turn. A digit picks a row, `c` claims it after asking who and `r` refreshes; `/ready` again closes it. Needs Claude Code 2.1.287 or later and `python3`; draws in the terminal.
- The pane follows the session's working directory, so a move into a worktree reads and claims against that worktree's `roadmaps.json`. Refusals show the CLI's own line, and an old-format roadmap points at the migrate skill.

[Unreleased]: https://github.com/JasonWarrenUK/goblin-mode/compare/roadmap-pane-v0.1.0...HEAD
[0.1.0]: https://github.com/JasonWarrenUK/goblin-mode/releases/tag/roadmap-pane-v0.1.0
