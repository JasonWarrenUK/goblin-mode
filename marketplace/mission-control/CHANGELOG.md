# Changelog

All notable changes to this plugin are documented here, newest first.

## [Unreleased]

### Changed

- The tools no longer send messages themselves. A message a plugin sends got no verdict from the auto-mode classifier in every session of the first live run, so `mc_slot`, `mc_need`, `mc_send`, `mc_grant`, `mc_revoke` and `mc_assume` now write the ledger and hand the model the exact `SendMessage` call to make, recipient named as `ListAgents` lists it. The board's own `g` grant still sends and toasts the outcome.
- The coordinator's socket and name are read live from the session registry by session id; a restart or a resume no longer leaves the ledger and the briefs naming a dead socket. The brief and guidance templates carry no socket.
- The mark on an incoming peer message now names a crew session by its socket, and marks a message as not the coordinator's only when it opens by speaking as mission control or the coordinator; a peer that merely mentions the plugin gets no mark.
- `mc.py start` records whether the base branch is on origin and, when it is not, puts the push on the needs list as item 1 and warns; the first run found out at the push.
- Kick-off's launch lines end with the opening prompt, since an interactive session takes no first turn from a SessionStart hook; the worktree bootstrap is run with zsh.
- A slot granted from a request the hook recorded names the command plainly, without the `attempted:` prefix.

### Fixed

- The board noticed a run started after the session began only once a pane was open; every tick now rereads the ledger and a tool call rereads before answering.

## [0.1.0] - 2026-10-23

### Added

- The ledger CLI (`scripts/mc.py`): a run per repository with its coordinator, base commit, crew plan, numbered assumptions and needs list; a row per session; one holder per shared resource; pending requests; probes of the machine (ports, processes, database clients, the migration the stack holds); `check` for the mod's approval path; `hook pre-tool-use` and `hook session-start`.
- The `/mc` board pane: crew with liveness from Claude Code's session registry, slots with windows and probe state, requests, the needs list with complete commands; `g` grants, `d` marks done, `x` releases, `r` refreshes; `/mc start|grant|release|done|status|end` as the person's hand from any session.
- Tools `mc_report`, `mc_slot`, `mc_need`, `mc_send` for every session and `mc_grant`, `mc_revoke`, `mc_assume`, `mc_board` for the coordinator; grants probe first and message the grantee and the others; assumptions broadcast with their number.
- A session-scoped system-prompt section naming the run, the coordinator's session and socket, the assumptions and the human gates; a mark on incoming peer messages verified against the coordinator's socket.
- Slot approval: a project hook's `ask` on a gated command is answered `allow` while the session holds the slot and runs from its worktree, for resources marked `approve_in_slot`; never over a `deny`, never for a human gate.
- Skills `kickoff`, `coordinate`, `crew`, `checkin`, `end` and `configure`; the protocol and config references; brief and guidance templates; CHIRPdb's config as the first example.
