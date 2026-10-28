# Changelog

All notable changes to this plugin are documented here, newest first.

## [Unreleased]

### Added

- The board's crew section is grouped by state, each group under a subheading with its count: `in-slot`, `working`, `blocked`, `waiting-jason`, `briefing`, `pr-ready`, `done`, then `gone` for sessions no longer live. Ledger order holds within a group and the number hotkeys follow the grouped order.
- The coordinator's probed board asks GitHub for each crew PR's state (cached for 60 seconds in `<ledger>/pr-cache.json`) and draws `merged` or `closed` beside the number; the coordinator's prompt section names crew whose PR merged while their row is not `done`. No crew session reports a merge the user made, so the row used to read `pr-ready` for ever.
- `mc.py report --for <session>` and `mc_report` with `for`: the coordinator (or the person with `--by-user`) corrects another session's row. The log records who.
- A crew session that runs `gh pr create` has the PR number and `pr-ready` reported by the mod from the URL `gh` prints.
- `mc.py join --planned` refuses unless the cwd is in a worktree the crew plan names.

### Changed

- Releasing a slot puts back the state it interrupted when that was `pr-ready`, `blocked`, `waiting-jason` or `done`, recorded on the slot as `prior_state`; it used to set `working`, so a session that had reported `pr-ready` read `working` until it reported again. Any other state still returns to `working`. A session holding two slots reads `in-slot` until the last one goes, and a forced grant puts the displaced holder back the same way.
- `report`, `join`, `grant` and `release` hold the run lock while they rewrite a session row. A report landing during a grant or release used to be overwritten by whichever wrote last.
- `mc.py crew add` writes a worktree under the main checkout in the spelling git reports for it.

### Fixed

- A session whose cwd differed from the crew plan only in letter case (`code` and `Code` on a case-insensitive volume) never joined the run, so it was missing from the board and `mc_grant` could not resolve it. The worktree match asks the filesystem whether two paths are one, in the mod, in `crew_for` and in the SessionStart hook.
- Overlapping refreshes could finish out of order and draw the older picture of the ledger. A result is now applied only while no refresh that started later has landed, and a timed refresh is skipped while the previous one is still running. A refresh without probes keeps the PR state and the probes the last probed one found, and a probed refresh overtaken by a plain one still lands its PR state and probes.
- `status --probe` could outlast the mod's 20-second limit and draw the board as broken when `gh` or `psql` hung. A `gh pr view` lookup now waits 3 seconds, and after the first timeout the remaining PRs are answered from the cache alone; each `psql` probe waits 3 seconds.
- `crew add` rewrote a worktree into the main checkout's spelling even where the two spellings are different directories (a case-sensitive volume). It now asks the filesystem first.
- The kickoff and end skills gave `mc.py status --json`; the flag goes before the subcommand (`mc.py --json status`).

## [0.1.0] - 2026-10-27

### Added

- The ledger CLI (`scripts/mc.py`): a run per repository with its coordinator, base commit, crew plan, numbered assumptions and needs list; a row per session; one holder per shared resource; pending requests; probes of the machine (ports, processes, database clients, the migration the stack holds); `check` for the mod's approval path; `hook pre-tool-use` and `hook session-start`.
- The `/mc` board pane: crew with liveness from Claude Code's session registry, slots with windows and probe state, requests, the needs list with complete commands; `g` grants, `d` marks done, `x` releases, `r` refreshes; `/mc start|grant|release|done|status|end` as the person's hand from any session.
- Tools `mc_report`, `mc_slot`, `mc_need`, `mc_send` for every session and `mc_grant`, `mc_revoke`, `mc_assume`, `mc_board` for the coordinator; grants probe first and message the grantee and the others; assumptions broadcast with their number.
- A session-scoped system-prompt section naming the run, the coordinator's session and socket, the assumptions and the human gates; a mark on incoming peer messages verified against the coordinator's socket.
- Slot approval: a project hook's `ask` on a gated command is answered `allow` while the session holds the slot and runs from its worktree, for resources marked `approve_in_slot`; never over a `deny`, never for a human gate.
- Skills `kickoff`, `coordinate`, `crew`, `checkin`, `end` and `configure`; the protocol and config references; brief and guidance templates; CHIRPdb's config as the first example.

### Changed

- The tools no longer send messages themselves. A message a plugin sends got no verdict from the auto-mode classifier in every session of the first live run, so `mc_slot`, `mc_need`, `mc_send`, `mc_grant`, `mc_revoke` and `mc_assume` now write the ledger and hand the model the exact `SendMessage` call to make, recipient named as `ListAgents` lists it. The board's own `g` grant still sends and toasts the outcome.
- The coordinator's socket and name are read live from the session registry by session id; a restart or a resume no longer leaves the ledger and the briefs naming a dead socket. The brief and guidance templates carry no socket.
- The mark on an incoming peer message now names a crew session by its socket, and marks a message as not the coordinator's only when it opens by speaking as mission control or the coordinator; a peer that merely mentions the plugin gets no mark.
- `mc.py start` records whether the base branch is on origin and, when it is not, puts the push on the needs list as item 1 and warns; the first run found out at the push.
- Kick-off's launch lines end with the opening prompt, since an interactive session takes no first turn from a SessionStart hook; the worktree bootstrap is run with zsh.
- A slot granted from a request the hook recorded names the command plainly, without the `attempted:` prefix.

### Fixed

- The board noticed a run started after the session began only once a pane was open; every tick now rereads the ledger and a tool call rereads before answering.
- Slot approval covers a whole line only when every command on it is a gated command the session holds; `G && git push`, a `$(...)` or backtick substitution and unreadable quoting now prompt as before.
- The guard refuses an abbreviated `--by-user`, a quoted one, `--session` and a `CLAUDE_CODE_SESSION_ID=` assignment on an `mc.py` line, and the CLI takes no flag abbreviations. The docstring and README say plainly that this guards against accidents.
- A subagent's Bash calls are gated like its parent's; only the crew brief at session start skips them.
- A gated command inside `sh -c`, `bash -c` or `zsh -c` is gated, and `cd a && cd b` reads as `a/b`.
- `needs`, `assume` and `crew` writes hold a lock on `run.json`, and temp files carry the process id, so concurrent sessions no longer drop a need or crash on a shared temp name.
- `/mc grant` sends the grantee its message only when the CLI granted; a refused grant is reported and sent nowhere. A forced grant tells the session whose slot it took. Its row stops reading `in-slot` too.
