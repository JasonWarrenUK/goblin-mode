# Changelog

All notable changes to this plugin are documented here, newest first.

## [Unreleased]

### Added

- **A session's identity survives what used to break it.** A `/clear` issues a new session id while the process, pid and socket stay, which on 28 October 2026 left every coordinator-only write refused until run.json was edited by hand. The ledger now offers the coordinator's own process under its new id as a rebind candidate (the board's `rebind?` line, the session's start context, a reconcile line) and `mc.py adopt coordinator` rebinds it: from that session on the user's yes, or by the user with `/mc adopt coordinator`, which is also how a coordinator started fresh takes the run. A crew session restarted or cleared in a planned worktree adopts the worktree's old row on `join` (state, summary, PR, slots, requests and needs carry over; the old file stays as `<id>.json.adopted`), so no second `briefing` row and no stuck slot. The docstring and protocol now say which operations keep the id.
- **What a process or a conversation held now lives in the ledger.** `mc.py jobs` records each cron job and Monitor on the session's row (the PR watch keeps its own entry), a resume is told what to re-arm, and reconcile names a job whose session is gone. `mc.py pending` keeps the coordinator's open threads and `mc_decide` (and `mc.py decide`) the user's decisions in `decisions.jsonl`, each told session acknowledging with `decide ack`; a resumed or compacted coordinator reads both back from its start context, the end skill's closing paragraph and follow-ups read the decisions, and reconcile names a decision nobody acknowledged. The SessionStart hook also fires on compaction and reprints the crew paragraph with the brief path, which the prompt section now carries too.
- A need takes `--kind measurement` and `--for <task>`; `needs done --result <text|@file>` carries the user's output, and `/mc done <n> <result>` or the board's `d` forwards it to that session and closes the need in one step. The board shows `result → <task>`. A need's why is no longer cut at 240 characters.
- A grant to the slot's current holder extends it (more minutes, only the holder told); `/mc extend <resource> [minutes]` does the same from the board. `force` is for taking a slot only.
- Grant notices and assumption broadcasts go only to live sessions that are still working; a `done` or `retired` row hears nothing more.
- A `gh` or `git push` the permission classifier refused lands on the needs list by itself, with the command and the directory; the crew skill names that as the one response to a refusal.
- `crew add --unlisted` plans a task with no roadmap item: reconcile and the claim check expect no claim, the end skill names it as a roadmap candidate and the board marks it.
- The mod warns off a haiku or sonnet session that tries to coordinate: `/mc start <name>` answers with the model and the override (`/mc start <name> anyway`), a `mc.py start` typed from Bash is refused unless the line carries `--small-model-ok`, and a resumed coordinator session on such a model gets a toast at start.
- Each crew session writes its context window fill to its row on the board's timer (`mc.py report --context <percent>`, a gauge write that moves neither the log nor the row's age), and the board draws it as `ctx 63%` beside the row, amber from 70 and red from 85, so the coordinator sees who is running out of room.
- `mc.py classify`: the project is solo or collaborative, stated as `collaboration` in the config or its gitignored `.local` twin, else inferred from 90 days of human authors and the reviews on the last 30 merged PRs, with the evidence; on a collaborative project the team's hours come from the config, the reviewers' own timestamps or a weekday default. `mc.py start` records the answer on the run (`--collaboration` overrides) and every crew session's start context states it. The global `pr-land`, `pr-review` and `pr-handle_review` skills now read this mode in place of the owner-name heuristic for whether a review is required, and `reconcile` says `solo project; the merge is the user's` where a collaborative run would name a reviewer.
- `mc.py watch`: a crew session's PR watcher, started in the background straight after `gh pr create` by the crew skill. It polls `gh` every five minutes on reviews, review decision, review comments, comments, each check and state, prints the first change and exits, which wakes the session to report it and re-arm; `watch ended` on merge or close. On a collaborative project a change that is not a merge or close is held until the team's hours, so nobody types a pause each evening; on a solo project there is no window, the watch covers checks and state, and a PR with no checks is not watched. The board marks a watched row `watching`. From the CHIRPdb run, where every session improvised its own poll loop and paused it by hand.
- `mc.py retire <task>` (and `/mc retire <task> [dry]` from the board) reclaims a finished crew session's worktree while the run goes on, so a long run does not keep every merged task's dependencies on disk until `end`. It refuses, naming why, while the session is live, the row is not `done`, the PR is open or unknown, the tree is dirty, the session holds a slot, an open PR is based on the branch or a process still has the worktree as its working directory (that one also lands on the needs list with the `kill`). Otherwise it removes the worktree, prunes, deletes the branch with `-d` only (a refusal is reported, never forced) and records the retirement on the row with the time, who ran it and the bytes freed. `--dry-run` prints what would go and the disk it holds. The board reads such a row `retired`, in its own group after `done`; `reconcile` nudges with an `unretired` line once a merged task's worktree has sat an hour; `end` skips what is already retired. From the CHIRPdb run, where a merged task's worktree held several hundred megabytes for a day.

### Fixed

- `mc.py reconcile` reads a task's claim from the roadmap itself (`started` on the task, at the ref where it ought to be) instead of grepping for a `chore(roadmap): claim <id>` commit subject. A claim that reached the trunk through a sync batch or a `done` batch now counts, and an open branch that dropped its own claim commit once the trunk carried the claim is no longer drift. A task the roadmap does not list is named once as `unlisted`, with no claim expected. Reported from the CHIRPdb run, where all three claim lines were false positives.
- A merged PR's line no longer reads `merged, merged`.
- The board's crew group headings (`blocked · 1`, `pr-ready · 2`) are bold, coloured by state and spaced from the group above, so the groups read as sections.

## [0.3.0] - 2026-10-28

### Added

- `mc.py reconcile`: the ledger against ground truth. It reads the live session registry, GitHub's word on each PR and the branches on origin, and prints what drifted: a session no longer running whose row is not `done`, a crew task in the plan that no session joined, a merged or closed PR whose row still reads otherwise, a need left open after its session finished, and a `chore(roadmap): claim` commit missing from a merged PR's base or an open PR's branch (fetched first, only where the repo has a rich roadmap). Each PR line names who it waits on in GitHub's own terms: `waiting on <login>`, `changes requested by <login>`, `approved; the merge is the user's` or `no reviewer requested`. PR facts cache in `<ledger>/pr-facts.json` with the same hang guard as the board's state lookup.
- The brief template carries a `Verify at` row: the viewports and devices a rendered change is checked at before `pr-ready`.

### Changed

- The coordinate skill runs `reconcile` before every status, check-in or answer about where things stand, and after each batch of crew messages; what remains opens the status. It never splits, merges or re-slices a task without an AskUserQuestion naming the slices, and it names a PR's blocker as GitHub does rather than as "the user".
- The crew skill reads its messages immediately before every push, since a pause notice in flight beats the push, and verifies every rendered change at the brief's widths with the primary action still on screen before reporting `pr-ready`.
- The check-in skill fixes drift before asking anyone and opens its list with a `Drift` bucket when any remains.
- `protocol.md` section 11 records each October 2026 drift incident and the rule it left: needs marked done at once, crew joined to the ledger, no slicing without the user, messages read before a push, the real blocker named, rendered changes checked live.

## [0.2.0] - 2026-10-28

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
