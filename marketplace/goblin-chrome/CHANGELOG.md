<!-- doc-changelog: generated 2026-10-05. Delete this line once you hand-edit this file. -->
# Changelog

All notable changes to this plugin are documented here, newest first.

## [Unreleased]

## [0.1.0] - 2026-10-04

### Added

- A goblin in the band above the prompt. It paces while nothing happens, sits after five minutes, sleeps after ten, startles when a prompt goes in, watches while Claude works and answers a poke. The tier's rune sits at the left of the band and the goblin's dialogue at the right.
- A closing line for every turn with the real numbers in it: `dOnE. 42s. tOoK 7 tHiNgS. bIt mE oNcE.`
- A tail on the hint under the prompt, in the goblin's register, reacting to a fresh session, idling, an unsent draft and typing mid-turn. The engine's own hint stays live.
- A face above every question Claude asks, with an expression chosen by context: expectant, nervous after a failed tool, folded arms for an interrogation, grinning late at night.
- Dialogue for six seconds at a time on a poke, a yawn, a subagent returning, a compaction, a `/clear` and the commit-msg hook bouncing a message.
- A frame, rune and theme colour for each model that served the last request: Fable, Opus, Sonnet and Haiku. A skill that pinned one model while another answered draws both runes in `warn`.
- A nine-state day on the local clock, fading over ten minutes and shifted by Friday evenings, Sundays and sessions past four hours.
- Colours from the project theme in `.claude/themes/`, falling back to the global `clod` family.
- Four options: `enabled` (the one switch), `audio` (a cackle when the commit-msg hook bounces a message), `schedule` and `theme`.
- Types for the `$.state` contract (`palette`, `day`, `frame`, `vitals`, `idle`), readable by a plugin that lists this one under `dependencies`.

[Unreleased]: https://github.com/JasonWarrenUK/goblin-mode/compare/goblin-chrome-v0.1.0...HEAD
[0.1.0]: https://github.com/JasonWarrenUK/goblin-mode/releases/tag/goblin-chrome-v0.1.0
