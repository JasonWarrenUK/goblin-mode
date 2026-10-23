# Changelog

All notable changes to this plugin are documented here, newest first.

## [Unreleased]

## [0.1.0] - 2026-10-23

### Added

- The ledger CLI (`scripts/mc.py`): a run per repository with its coordinator, base commit, crew plan, numbered assumptions and needs list; a row per session; one holder per shared resource; pending requests; probes of the machine (ports, processes, database clients, the migration the stack holds); `check` for the mod's approval path; `hook pre-tool-use` and `hook session-start`.
- The `/mc` board pane: crew with liveness from Claude Code's session registry, slots with windows and probe state, requests, the needs list with complete commands; `g` grants, `d` marks done, `x` releases, `r` refreshes; `/mc start|grant|release|done|status|end` as the person's hand from any session.
- Tools `mc_report`, `mc_slot`, `mc_need`, `mc_send` for every session and `mc_grant`, `mc_revoke`, `mc_assume`, `mc_board` for the coordinator; grants probe first and message the grantee and the others; assumptions broadcast with their number.
- A session-scoped system-prompt section naming the run, the coordinator's session and socket, the assumptions and the human gates; a mark on incoming peer messages verified against the coordinator's socket.
- Slot approval: a project hook's `ask` on a gated command is answered `allow` while the session holds the slot and runs from its worktree, for resources marked `approve_in_slot`; never over a `deny`, never for a human gate.
- Skills `kickoff`, `coordinate`, `crew`, `checkin`, `end` and `configure`; the protocol and config references; brief and guidance templates; CHIRPdb's config as the first example.
