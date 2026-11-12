# Changelog

All notable changes to this plugin are documented here, newest first.

## [Unreleased]

## [0.11.1] - 2026-11-12

### Fixed

- The Needs Jason and Running lists on the board are readable at the pane's width. Each need's number, task tag, markers and (for a running need) start time sit on one row that wraps when it runs long, and the command, the why and a running need's note each take a full-width line beneath it, indented four columns. The why used to share a row with the tag and markers and could be left ten columns wide, wrapping one or two words to a line. A running need's note shows a single line until the need is picked and wraps in full after that.

## [0.11.0] - 2026-11-12

### Added

- A `PreCompact` hook (`mc.py hook pre-compact`) tells the compaction summary what only the conversation holds. The coordinator is asked to keep unanswered messages, freezes and holds in force, reviews in flight, questions put to the user, the user's standing instructions and the ids of its scheduled jobs, and to leave board state to the ledger. A crew session, found by its row or by the planned worktree it runs in, is asked to keep its brief, branch, PR, slot and scheduled work. A session outside a run gets nothing. `references/config.md` and the README list the hook.

### Fixed

- A compacted coordinator no longer reads an approval the user put on hold as one to land. The start context prints a held approval as held with its reason and prints each decision with what it concerns, cutting a long decision before its subject so the subject survives. A real compaction of a live run on 11 November 2026 showed all three faults.
- The coordinator's start context fits the harness's hook output cap. The pending list takes the room the other parts leave under 9,500 characters and ends with a count of the rest and `mc.py pending list`, so the closing reconcile sentence and the re-arm line are never the part that gets cut.
- The protocol, README, coordinate skill and crew skill now say that a resume restores cron jobs, so a session reads `CronList` first and re-arms only what is missing, in line with what the hook prints.

## [0.10.0] - 2026-11-12

### Added

- A crew launched at `low` or `medium` effort starts its launch line with `CLAUDE_CODE_SUBAGENT_EFFORT=high`, the variable Claude Code 2.1.316 added, so the independent branch reviewer it dispatches runs at high effort. A crew at `high` or above gets no prefix, which would only lower its reviewer. The kickoff skill, README and protocol name the prefix so nobody strips it as noise.
- The coordinator records its own scheduled jobs (its wake cron) on `run.json` with `jobs add`, because it has no row of its own, and a resumed coordinator is told about them.
- A coordinator adopted in a new process and a crew session restarted in a fresh process are told which scheduled jobs the role carries. The start hook names them before the session joins, and `adopt coordinator`, `adopt crew` and `join` print the same line, with a `rearm` key under `--json` that the ledger never stores. When the user adopts from a coordinator whose process is still live, the line says its crons still fire there. A `/clear` keeps the process and its crons, so it prints nothing. The start hook also writes the process's current socket onto a crew row, so a `/clear` after a resume is still recognised as the same process.

### Changed

- A resumed session is told to read `CronList` first and create only a cron it does not show, because Claude Code restores cron jobs on `--resume` by itself and a blind re-arm fired a resumed coordinator's wake twice. A Monitor and a watch die with the process and are still re-armed. The re-arm line clips a job's spec to 120 characters and its prompt to 200, with `mc.py jobs list` for the rest, so twelve long jobs cannot push a resume context past the hook's 10,000 character cap.
- `jobs done` takes open jobs only and refuses a repeat with `job <id> is already done`. A crew session's second call used to report success and rewrite `done_at`. An id that no session holds reads `no job <id> on any session in this run` for the coordinator and the person.

### Fixed

- The scheduled jobs of a session that has gone no longer nag on every status check. `retire` closes the jobs on the row it retires, reconcile ignores jobs on a row retired by 0.9.0 or earlier, and the coordinator or the person (`--by-user`) can close the job of a session that is gone, which `jobs done` refused before because a session without a row had nothing to close. A run on CHIRPdb hit this with a `watch-246` job.
- A finished job of the coordinator's no longer hides the same id open on a gone crew row, a gone crew row with no task is named by its session id and not as the coordinator, and a compacted crew session is no longer told to re-arm.

## [0.9.0] - 2026-11-11

### Added

- A push gate. A repository opts in with `push_gate` in `.claude/mission-control.json`: a list of keys of `commands`, or `{"commands": [...], "exempt": [globs]}`. `mc.py gate` runs those commands in order from the checkout root against the committed HEAD, stops at the first failure and writes a per-commit record under the git common dir, with a lock while it runs. It refuses over uncommitted tracked changes and over untracked files that are not ignored (`--allow-untracked` overrides the second), because a suite can import a file the commit lacks. The PreToolUse hook then denies a `git push` unless the commit being pushed has a green record and no gate run is in flight, in any session of the repo, run or no run; a session outside any run had pushed three commits into a red suite on 4 November.
- What the gate reads: a push naming a refspec is checked against that ref's commit, and dry runs, bare tag pushes and deletions pass. `--tags` beside a branch refspec does not pass, and neither does a tag sent to a branch ref. A green record counts only when it ran every key `push_gate` lists now. `exempt` globs let a docs-only push through only when it goes to the remote and branch it was diffed against (the upstream, else origin's HEAD); a configured `pushRemote` or `remote.pushDefault` counts as another remote. A key missing from `commands` refuses the push. Glob refspecs, `--all`, `--branches`, `--mirror` and `push.default=matching` name no single tip, so the tips they send beyond HEAD's go unchecked.
- `needs add` moves a worktree directory to the same place in the main checkout when the command sits behind a human-gated resource, records the original in `cwd_moved_from` and says so. Eight hosted calls typed from crew worktrees had failed with `LegacyProjectNotLinkedError`, because the link to the hosted project lives in a git-ignored folder that worktrees do not get.

### Changed

- The crew skill runs typecheck with test, lint and contract before a push and lets each run to the end. It names the gate where a project sets one. A new step 1b has a fresh subagent review the branch with `branch-qa_review` before `pr-ready`, two rounds at most. Step 1a gains role or `aria-label` selectors, signing in again when a shot lands on the login page and scrolling the target into view. A push-gate refusal stays off the needs list and goes back to the session that hit it. The crew skill and brief template tell crews to request a slot when implementation starts and to write the verification script while waiting.
- The coordinate skill points at `pr-land`'s queue for several `approved-unlanded` lines.

### Fixed

- The warning that refuses a run start from a haiku or sonnet session splits the line into commands and words the way a shell does and asks whether the script is the command word. It no longer fires on greps, JSON filters and commit messages that only mention the script, and it catches a quoted script path. It looks past `env`, `sudo`, `uv run`, `timeout` and `nice`, reads `bash -c` bodies and skips heredoc bodies and comments.

## [0.8.1] - 2026-11-05

### Added

- `mc.py watch --stop` stops this session's own PR watcher by the pid on its row, and only when the row reads `watching` or `holding` and the process's command line is an `mc.py` watch. It never matches by name. Sessions on the Tertiary Blast run found their watchers exiting 144 with no output, three times on one PR; a background command killed with `pkill -TERM` reports exactly that, and a name match from one session reaches every session's watcher. The watcher now records its pid, catches SIGTERM, SIGHUP and SIGINT; it also says so: `stopped` with `do not re-arm` when `--stop` marked the row, `killed` with the signal and `Re-arm the watch` when something outside did. Reconcile gains `watch-dead` for a watcher that reads `watching` with no process behind it, since SIGKILL leaves no other trace.
- An approval records the PR's head commit when the watcher sees it. Reconcile prints `approved-stale` when the head has moved since, so an approval that predates a rewrite is no longer called ready to land (#231 was approved before its rewrite). `mc.py pending hold <pr> --text <why>` and `pending release <pr>` keep an approved PR back on purpose; reconcile then prints `approved-held` with the reason, and `approved-unlanded` reads as a landing to offer, not one the user authorised.
- A project config key `claims: "trunk-sync"` for repos whose roadmap or Jira sync writes claims to the trunk. Kick-off then makes no claim commit on the branch, which conflicted twice with the sync on the Tertiary Blast run, and reconcile no longer flags an open PR for a missing branch claim.

### Changed

- A watcher that returns drops its pid, and a deadline records `idle` whether or not changes are held, so the board stops counting a watcher that has exited and `watch-dead` stays quiet after a normal exit. Held changes stay in the row and the next watch reports them again.
- The crew skill says to read and fix review comments yourself and put `pr-handle_review` on the needs list, because the skill is the user's to type; to run `git diff --check` before any push; and to put a refused force-push, comment edit or reviewer add on the needs list with the exact command. The coordinate skill says to message each session the user resumed with `claude --continue`, since a resumed session sits at its prompt until it hears something. The kick-off skill says a shared generated file is regenerated whole, never hand-picked by hunk.

### Fixed

- The signal handler no longer writes to the ledger. A signal landing while the watcher held the run lock made the handler wait on a lock its own process held, hanging the watcher and blocking every other `mc.py` command on the run. The record is now written after the lock has been released.
- A stop that races the watcher's exit no longer prints a traceback or leaves a stop marker behind that would make a later outside kill read as meant.

## [0.8.0] - 2026-11-05

### Added

- A crew session that stops on a permission prompt or a question in its own window used to look like any other working session. The registry already carried a waiting status the pane ignored; now a live row with it gains a red `waiting on you (prompt)` tag and dot, the text board opens with a `Waiting on you` section naming the window and how long the session has sat there, the coordinator's context section leads with those sessions and coordinate step 0a says to name the window to the user before any other status. The check-in skips such a row and opens its list with the window, `mc_send` to `all` names any recipient sat on a prompt so the sender knows not to wait on a reply, and the crew skill says to report `waiting-jason` and tell the coordinator before asking anything in-window.
- Reconcile traces every open browser back to the session that launched it: it reads the process table, finds each browser under a Playwright MCP server, walks the parent chain to a pid the registry knows and prints a `browser-open` drift line naming the browser (`Google Chrome`, `firefox`) when that session holds no slot. Inside a slot the browser is the check in progress and is left alone. The crew skill says to close the browser before releasing a slot, with the drift line as the backstop; three browsers sat open for hours on the 4 November run and were only found by hand.

### Changed

- The text board prints `Waiting on you`, then `Needs Jason`, then the crew table, in the order the user acts on it; the pane already read that way.
- `/mc extend` tells the holder the deadline the CLI reports rather than a fixed 15 minutes, since an extension granted without a number takes the minutes the holder asked for.

### Fixed

- A slot request cleared neither when the extension was granted nor when the holder released the slot, so it stayed on the board reading as a queue for a free resource. It now clears on both, and a grant with no `--minutes` extends by the request's own figure.

## [0.7.0] - 2026-11-04

### Added

- Kick-off chooses the model and effort each crew session launches on with a one-line reason and puts the launch line on the needs list instead of printing it in chat. Of the ten crew transcripts from October 2026 that could be matched, eight ran almost entirely on Sonnet: `ANTHROPIC_MODEL=opusplan` in the terminal environment outranks the `model` in settings and runs Sonnet outside plan mode, and the crew skill's own `model: sonnet` would have put the brief and the five questions on Sonnet even where a launch said otherwise. Now `crew add` takes `--model`, `--effort`, `--name`, `--reason` and `--plugin-dir`, keeps the first three on the plan entry and raises a need of kind `launch` as the coordinator's: `cd <worktree>` first, then `claude --model <m> --effort <e> --name <name> [--plugin-dir <root>] '<the opening prompt>'`, every value shell-quoted so a plugin root under `Application Support` stays one argument. `--model` on the line beats `ANTHROPIC_MODEL`; `--effort` beats the settings but not `CLAUDE_CODE_EFFORT_LEVEL`. The board draws it under `Needs Jason` with a `launch` marker and the why (`start crew 10SE.2 in a new terminal window (opus, high: reworks the shared ranking query)`); a session joining as that task, fresh or by adopting the old row, closes it by itself; a second `crew add` for the task supersedes the open one; a `crew add` for a task whose session is already live (a migration timestamp assigned later, say) raises no line and closes any open one, and so does one that drops the worktree; reconcile's `unjoined` line names the number. The brief gets a `Model` row and the guidance's crew table a `Model` column. The kick-off rule is `sonnet` at `medium` unless a reason the brief carries earns `opus` at `high` (an adversarial review, an open design, a shared surface other tasks lean on, a migration); the hand-over now says to open the board and run each launch need in a new terminal window. The crew skill sets `model: inherit` and no effort, so the launch line's flags hold for its first turn.

### Changed

- The board reads top to bottom in the order the user acts on it: `Crew` holds the live sessions only, `Needs Jason` comes next and is drawn only while something is open (no more `nothing.` line), then `Running`, `Slots`, `Requests` and a new `Archive` section, drawn only once a session is over, holding the `retired` and `gone` groups with the same `c` toggle and default collapse they had under Crew. Each need now shows the line to type first (`cd <dir> && <command>`, in the Claude colour) and the reason beneath it in dim text with its markers; a need with no command, or one running, keeps its reason on the row. The directory in that `cd` is shell-quoted on the pane and the text board alike, so a checkout under a path with a space no longer splits it; a plain path draws as before. The text board (`mc.py status`, `/mc status`, `mc_board`) prints in the same order, with a gone session in an `Archive` table at the end rather than `(gone)` in the crew table.

## [0.6.0] - 2026-11-04

### Added

- A need has a `started` state between `open` and `done`. On the CHIRPdb run of 3 November 2026 a four-hour hosted backfill the user had typed at 15:16 stayed in the needs-Jason bucket beside needs they had not opened, because the only move was open to done and done is where the result is pasted; asked whether to remove it, the answer was no. Now `mc.py needs start <n> [--note <where it is watched>]`, the board's `s` on a picked need or `/mc started <n> [note]` marks it on the user's word, the way done is. A started need draws under its own `Running` heading with its start time and note (no command to type), is left out of the `Needs Jason` count that the check-in, the text board and the coordinator's start context read (which now says `running for the user: #n since hh:mm`) and closes as before with `/mc done <n>` and the result. The check-in list gains a `Running` bucket, and the coordinate skill says to set the state when the user says they have run something.
- A re-issued need links to the one it replaces: `needs add --supersedes <n>` closes the old need as done with `superseded_by` the new number in one step (and `supersedes` on the new one), and `needs done <n> --superseded-by <m>` does the same when the successor already exists, so a need that failed on its first attempt and was raised again reads in one direction across the two numbers. The log carries a `need-superseded` event. The re-issue keeps the old need's kind, recipient and directory unless the flag says otherwise, so a measurement's result still reaches the session that wanted it; the command is never carried over. `mc_need` takes `supersedes` so a crew re-issue goes through the tool, with the coordinator's line. Each link flag is refused on the wrong action instead of being dropped, and reconcile leaves a started need alone when its session finishes or its PR merges. A re-issue may also come from the session the need is for (not only the one that raised it) and keeps the old need's task tag; the board marks the new need `re-issues #n`.

## [0.5.0] - 2026-11-03

### Added

- An idle coordinator is deaf between prompts: a crew message sits in its inbox until the next turn, and on 2 November 2026 an approved PR waited two and a half hours for a landing already authorised. The coordinate skill now schedules a recurring wake inside the collaboration hours (a cron every 30 minutes, recorded with `jobs add`) whose turn reads the crew messages and acts, and the watcher writes an `approval` item to the pending list the moment a PR is approved, so `reconcile` says `approved-unlanded` with the time until the merge, which closes the item by itself.
- The board's `retired` and `gone` groups are collapsed by default, each heading showing its count; `c` shows and hides them.

### Fixed

- A task id that matched several session rows (a stray session that joined the worktree and closed, marked done, beside the one still working) refused as ambiguous in `retire`, `grant` and every other resolver path. The resolver now passes over rows that are done or retired and takes the one still working; when every row is done, as `retire` meets them, the one carrying the PR is taken; a real tie refuses naming each row's state, liveness and worktree so the id can be used.
- The ledger no longer depends on a working git. On 30 October 2026 a macOS update removed the Command Line Tools, `/usr/bin/git` became Apple's stub, and every `mc.py` command answered "not inside a git repository" while the run sat intact on disk: no board, no needs, no slots, and the session that found the problem could not even file the fix. While git works nothing changes: it answers for the checkout and `gh` chooses the repository as before. When git fails, the checkout and the remote are read from the `.git` entry (a directory, or a worktree's `gitdir:` file) and the git config file, the remote chosen the way `gh` chooses it (the one `gh repo set-default` marked, else `upstream`, else `github`, else `origin`); every `gh` call then names that repository outright with `--repo`, so the watcher and the PR facts keep working; and, `status`, the board and `reconcile` (as a `git-unavailable` line) print one line naming the cause and the fix (`xcode-select --install` on macOS) while needs, slots, messages and the watcher carry on. Only the claim check, `retire` and the author count wait for git, each saying so.

## [0.4.0] - 2026-11-02

### Breaking

- `mc.py start` from a haiku or sonnet session is refused unless the line carries `--small-model-ok`, and `/mc start` from one answers with the model and the `anyway` override. The global `pr-land`, `pr-review` and `pr-handle_review` skills now read `mc.py --json classify` to decide whether a review is required, so this plugin's script has to be on disk for them.

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

- `/mc done <n>` and the board's `d` key passed `--json` after the subcommand, which the CLI's argparse refuses; the flag now leads the line, the test world's fake CLI refuses the wrong order the way argparse does, and the three global PR skills and the kickoff skill spell `mc.py --json classify` and `mc.py --json status`.
- `classify` counted `Claude <noreply@anthropic.com>` as a human author and one person under two email addresses as two, which read this repository as collaborative; authors now merge when they share either a name or an email address (so two spellings of one name collapse too), and Anthropic's noreply address is a bot.
- The watcher's review-comment count read one page of 30; it now paginates.
- The auto-need on a refused GitHub write ignores a PreToolUse hook's refusal (the gh guard on an inline body, this plugin's own slot gate), which is not the user's to type.
- `reconcile` adds a `roadmap-stale` line when a crew PR has merged but its task still reads `todo` on the roadmap at the trunk, and the coordinate skill answers it by running `/roadmap:maintain` from the main checkout and committing the result; it goes quiet once the trunk says done, however the sync happened.
- `mc.py reconcile` reads a task's claim from the roadmap itself (`started` on the task, at the ref where it ought to be) instead of grepping for a `chore(roadmap): claim <id>` commit subject. A claim that reached the trunk through a sync batch or a `done` batch now counts, and an open branch that dropped its own claim commit once the trunk carried the claim is no longer drift. A task the roadmap does not list is named once as `unlisted`, with no claim expected. Reported from the CHIRPdb run, where all three claim lines were false positives.
- A merged PR's line no longer reads `merged, merged`.

### Changed

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
