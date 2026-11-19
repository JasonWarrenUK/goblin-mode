<!-- doc-changelog: generated 2026-10-05. Delete this line once you hand-edit this file. -->
# Changelog

All notable changes to this plugin are documented here, newest first.

## [Unreleased]

## [0.1.0] - 2026-10-05

### Added

- `/pain` logs friction with Claude Code itself to `library/state/cc-pain-points.json` without starting a turn. `/pain <text>` appends at once and prints the new id; `/pain` alone opens a small pane with an input. The entry records the repo, the branch and the last failed tool call's first line, and an open entry with the same description is never duplicated.
- `/fleet` lists every session on the machine, this one first, from a heartbeat each session writes to the plugin's shared store. Pick a row with `1` to `9` and send that session a message from the input. A row silent for a minute reads `quiet`.
- Running `/pain` or `/fleet` again closes its pane.
- Three options: `enabled` (the one switch; off, the heartbeat stops and neither command registers), `heartbeat_seconds` (15 by default) and `stale_minutes` (10 by default).
- Types for the `$.state` contract: the picked session, the last failed tool and the branch.

### Fixed

- A pain file that will not parse is refused, never overwritten.
- Both commands survive `/clear` and keep what you had typed.

[Unreleased]: https://github.com/JasonWarrenUK/goblin-mode/compare/goblin-util-v0.1.0...HEAD
[0.1.0]: https://github.com/JasonWarrenUK/goblin-mode/releases/tag/goblin-util-v0.1.0
