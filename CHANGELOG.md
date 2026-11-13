<!-- doc-changelog: generated 2026-08-27. Delete this line once you hand-edit this file. -->
# Changelog

All notable changes to this project are documented here, newest first.

## [Unreleased]

## [7.9.0] - 2026-11-13

### Added

- `mission-control` plugin 0.12.0: the text board (`mc_board`, `mc.py status`) shows each live crew session's context fill as `ctx N%` in its State cell, as the `/mc` pane already did. A gone session shows nothing, because its last figure would read as current.
- `mission-control` plugin 0.12.0: `mc.py reconcile` raises a `context-high` line for a live crew session at 70% context or more. The line says that only the user can compact a crew session, and names the window by its live registry name first, then the joined row's name, then the short session id. Four crew sessions had filled their context unnoticed because only the pane carried the figure.
- `mission-control` plugin 0.12.0: the coordinate skill tells the coordinator what to do with a `context-high` line: put it to the user in one line naming the window, ask at a natural boundary (before a PR description or a pool pass, never mid-task) and say so plainly at 85% or more.

## [7.8.1] - 2026-11-12

### Fixed

- `mission-control` plugin 0.11.1: the Needs Jason and Running lists on the board are readable at the pane's width. Each need's number, task tag, markers and (for a running need) start time sit on one row that wraps when it runs long, and the command, the why and a running need's note each take a full-width line beneath it, indented four columns. The why used to share a row with the tag and markers and could be left ten columns wide, wrapping one or two words to a line. A running need's note shows a single line until the need is picked and wraps in full after that.
- `pr-review-dry_run` skill: a strict review in a worktree-isolated session now has a written route for its test run. The session's own worktree stands in for the throwaway one when `HEAD` equals the PR's `headRefOid` and `git status --porcelain` prints nothing, the status is checked again after the suite and anything it wrote is listed in the `tests` line, and a failed check reports the tests as not run, never switching branch, stashing or resetting to pass. A second guide covers gitignored generated inputs, which a fresh worktree lacks and the clean-status check cannot see: copy them in or report the check that needs them as not run.

## [7.8.0] - 2026-11-12

### Added

- `mission-control` plugin 0.11.0: a `PreCompact` hook (`mc.py hook pre-compact`) tells the compaction summary what only the conversation holds. The coordinator is asked to keep unanswered messages, freezes and holds in force, reviews in flight, questions put to the user, the user's standing instructions and the ids of its scheduled jobs, and to leave board state to the ledger. A crew session is asked to keep its brief, branch, PR, slot and scheduled work. A session outside a run gets nothing.

### Fixed

- `mission-control` plugin 0.11.0: a compacted coordinator no longer reads an approval the user put on hold as one to land. The start context prints a held approval as held with its reason and prints each decision with what it concerns, cutting a long decision before its subject so the subject survives. A real compaction of a live run on 11 November 2026 showed all three faults.
- `mission-control` plugin 0.11.0: the coordinator's start context fits the harness's hook output cap. The pending list takes the room the other parts leave under 9,500 characters and ends with a count of the rest and `mc.py pending list`, so the closing reconcile sentence and the re-arm line are never the part that gets cut.
- `mission-control` plugin 0.11.0: the protocol, README, coordinate skill and crew skill now say that a resume restores cron jobs, so a session reads `CronList` first and re-arms only what is missing, in line with what the hook prints.

## [7.7.0] - 2026-11-12

### Added

- Every agent in `agents/` now pins an `effort` level. Since Claude Code 2.1.317 a subagent on a model other than its session's takes that model's own default, which had left the four Opus agents reviewing at `medium` under a `high` session. The Opus agents and the four Sonnet agents pin `high`; the two Haiku agents pin `medium`, which is their default.
- `mission-control` plugin 0.10.0: a crew launched at `low` or `medium` effort starts its launch line with `CLAUDE_CODE_SUBAGENT_EFFORT=high`, so the independent branch reviewer it dispatches runs at high effort. A crew at `high` or above gets no prefix, which would only lower its reviewer.
- `mission-control` plugin 0.10.0: the coordinator records its own scheduled jobs (its wake cron) on `run.json` with `jobs add`, and a resumed coordinator is told about them.
- `mission-control` plugin 0.10.0: a coordinator adopted in a new process and a crew session restarted in a fresh process are told which scheduled jobs the role carries. The start hook names them before the session joins, and `adopt` and `join` print the same line, with a `rearm` key under `--json` that the ledger never stores. A `/clear` keeps the process and its crons, so it prints nothing. The start hook also writes the process's current socket onto a crew row, so a `/clear` after a resume is still recognised as the same process.

### Changed

- `mission-control` plugin 0.10.0: a resumed session is told to read `CronList` first and create only a cron it does not show, because Claude Code restores cron jobs on `--resume` by itself and a blind re-arm fired a resumed coordinator's wake twice. A Monitor and a watch die with the process and are still re-armed. The re-arm line clips a job's spec to 120 characters and its prompt to 200, with `mc.py jobs list` for the rest, so twelve long jobs cannot push a resume context past the hook's 10,000 character cap.
- `mission-control` plugin 0.10.0: `jobs done` takes open jobs only and refuses a repeat with `job <id> is already done`. A crew session's second call used to report success and rewrite `done_at`. An id that no session holds reads `no job <id> on any session in this run` for the coordinator and the person.

### Fixed

- `mission-control` plugin 0.10.0: the scheduled jobs of a session that has gone no longer nag on every status check. `retire` closes the jobs on the row it retires, reconcile ignores jobs on a row retired by 0.9.0 or earlier, and the coordinator or the person (`--by-user`) can close the job of a session that is gone. A run on CHIRPdb hit this with a `watch-246` job.
- `mission-control` plugin 0.10.0: a finished job of the coordinator's no longer hides the same id open on a gone crew row, a gone crew row with no task is named by its session id and not as the coordinator, and a compacted crew session is no longer told to re-arm.

## [7.6.1] - 2026-11-12

### Fixed

- `pr-review` no longer leaves an empty draft review on a pull request when its own prose checks reject the summary. Step 5 now captures the findings script's output first and posts to GitHub only when the script succeeded and produced a payload, where the old single pipe started posting before the script's failure could stop it. The explanation crediting `pipefail` with the protection is corrected, and `gh api` now prints just the review id that step 6 needs.
- `pr-review` can post from a worktree-isolated session. Claude Code refuses a Bash call whose heredoc body holds a brace, so step 5 gains a fallback that writes the findings JSON to the scratchpad and runs the same capture-then-post shape with no heredoc.
- The usage comment in `partition-findings.mjs` and the `pr-review` intro no longer describe the one-pipe posting method.

## [7.6.0] - 2026-11-11

### Added

- `mission-control` plugin 0.9.0: a repository can gate `git push` on its own checks. `mc.py gate` runs the `push_gate` commands from `.claude/mission-control.json` against the committed HEAD and records the result per commit; the PreToolUse hook then refuses a push whose commit has no green record or whose gate run is still going, in any session of the repo, run or no run. `exempt` globs let a docs-only push through when it goes to the branch it was diffed against. A hosted command a crew session hands to the user now names the main checkout, where the link to the hosted project lives. Details in the plugin's changelog.
- `pr-land` lands several PRs in one run from one read-only plan, merging a stack once from its top layer. Each PR still asks before its merge and reads back its tag, plugin version and changelog before the next one starts.
- `next-task-ship` and the `mission-control` crew skill send the branch to a fresh reviewer before the PR is opened.

### Changed

- `commit-one`, `commit-batch`, `pr-handle_review` and `pr-review` scan their messages, replies and review text for house-rule breaches before sending them, and `pr-review` fails the run on a hit. `pr-handle_review` writes a failing regression test before each fix and pushes only once the suite has finished green.
- `pr-update` reads the PR body back after editing it, and the PR body lint rejects a body holding nothing but its watermark.

### Fixed

- `mission-control`'s warning against a small model starting a run reads the command line the way a shell does, so it no longer fires on greps, JSON filters or commit messages that mention the script, and it catches a quoted script path.

## [7.5.1] - 2026-11-05

### Added

- `mission-control` plugin 0.8.1: the PR watcher can be stopped on purpose with `mc.py watch --stop`, which signals only the calling session's own watcher, where a `pkill` by name had been reaching every session's. A watcher that dies now records its pid and the signal and prints a line saying so, and reconcile names a watcher that reads `watching` with no process. An approval records the head commit it was given on, so reconcile marks one that predates a rewrite as `approved-stale`, and `mc.py pending hold` keeps an approved PR back from landing on purpose. A project config key `claims: "trunk-sync"` skips the claim commit on each branch for repos whose sync writes claims to main. The crew, coordinate and kick-off skills carry the rest of the Tertiary Blast findings: read and fix review comments yourself and leave `pr-handle_review` to the user, check `git diff --check` before a push, message resumed sessions and regenerate shared generated files whole.

### Fixed

- `mission-control` plugin 0.8.1: the watcher's signal handler no longer waits on the ledger lock its own process holds, which could hang the watcher and block every other `mc.py` command on the run. A watcher that returns no longer leaves a pid on its row, so reconcile stops reporting a normal exit as a dead watcher.

## [7.5.0] - 2026-11-05

### Added

- `mission-control` plugin 0.8.0: a crew session that has stopped on a permission prompt or a question in its own window now shows as `waiting on you` on the pane, the text board and the coordinator's briefing, with the window the user has to visit named first. Reconcile reads the process table and names any browser a session left open outside a slot as `browser-open` drift, so a Playwright Chrome no longer sits unnoticed for hours. Details in the plugin's changelog.

### Fixed

- `pr-create` sends the PR body to `gh` exactly as approved, never through `sed`, `awk` or `tail`, and reads the posted body back for its Summary heading before reporting the URL; two PRs had gone up with a body holding only the watermark line after BSD `sed` rejected a GNU form and emptied the file.
- `mission-control`: a slot request now clears when the extension is granted and when the holder releases the slot, so it no longer reads as a queue for a free slot afterwards.

## [7.4.0] - 2026-11-04

### Added

- `mission-control` plugin 0.7.0: kick-off chooses the model and effort each crew session launches on, with a one-line reason the brief carries (Sonnet at medium unless the reason earns Opus at high), and puts each launch line on the board's needs list instead of printing it in chat. The line sets `--model` and `--effort` outright, which is what stops a terminal's `ANTHROPIC_MODEL=opusplan` quietly running every crew on Sonnet, and it closes itself when the session joins. The crew skill inherits the model rather than pinning its own.

### Changed

- `mission-control`'s board reads top to bottom in the order the user acts on it: the live crew, then `Needs Jason` (drawn only while something is open, each need's command line above its reason), then `Running`, `Slots`, `Requests` and an `Archive` of retired and gone sessions that appears only once there is one. The directory in every `cd` the board prints is shell-quoted, so a checkout under a path with a space pastes whole.

## [7.3.0] - 2026-11-04

### Added

- A per-repository versioning policy. `.claude/versioning.json` names the targets (the root, or a plugin) that skip a GitHub tag, a release or a changelog; a target with no tag gets no release either. `pr-land`, `doc-changelog` and `project-tag_version` read it at `origin/main` before tagging, releasing or writing a section, so a landing follows what main committed whichever branch the shell stands on; `safe-version-next.sh` exits 4 for a target the policy keeps untagged. The new `project-versioning_policy` skill shows and changes the file, and a local twin in the repository's git directory lets one machine override it without committing anything. This repository's root keeps its `v*` tags and its changelog and no longer gets GitHub releases, since nothing installable is attached to the root; its 32 root releases were deleted and the plugin series keep theirs.

## [7.2.0] - 2026-11-04

### Added

- `mission-control` plugin 0.6.0: a need the user has started now has its own state. A long job they have typed (a four-hour hosted backfill on the CHIRPdb run) used to sit in the needs-Jason bucket beside needs they had not opened, because the only move was open to done. `needs start`, `/mc started <n>` or `s` on the board marks it on the user's word; the board draws it under `Running` with its start time, the check-in and the coordinator's start context leave it out of the needs count, and it closes as before with the result. A need that failed on its first attempt is re-issued with `--supersedes` (or `mc_need` with `supersedes`), which closes the old one with a link to the new number and carries its kind, recipient and directory over. Details in the plugin's changelog.

### Fixed

- `mission-control`'s reconcile no longer reports a started need as still open when its session finishes or its PR merges, which had told the coordinator to close a job still running. A second `needs start` or `needs done` keeps the first recorded time, each link flag refuses on the wrong action instead of being dropped, and the board reads the link an open need carries.

## [7.1.0] - 2026-11-03

### Added

- `mission-control` plugin 0.5.0: an idle coordinator used to be deaf between prompts, so an approved PR could wait hours for a landing already authorised. The coordinate skill now schedules a half-hourly wake inside the team's hours and removes it at the end of the run, and the watcher writes each approval to the pending list so reconcile names it until the merge. The board's retired and gone groups are collapsed to their headings, with `c` to show them. Details in the plugin's changelog.

### Fixed

- `mission-control` no longer depends on a working git. When a macOS update removes the Command Line Tools, the board, needs, slots, messages and the PR watcher carry on, `status` and `reconcile` name the cause and the fix, and only what needs history waits. While git works, nothing changes: git answers for the checkout and `gh` chooses the repository as before.
- A task id that matched a stray session's row beside the real one refused as ambiguous in `retire`, `grant` and every other resolver path; the resolver now takes the row still working, then the live one, then the one carrying the PR.

## [7.0.0] - 2026-11-02

### Breaking

- The global `pr-land`, `pr-review` and `pr-handle_review` skills no longer decide whether a review is required from the repository owner's name. They read `mc.py --json classify` from the mission-control plugin, so that plugin's script must be on disk at `~/.claude/marketplace/mission-control/`, and `pr-land` requires an approved review on any project the classifier reads as collaborative, personal repositories included. A repository the history misreads sets `collaboration.mode` to `solo` in its `.claude/mission-control.json`.

### Added

- `mission-control` plugin 0.4.0: the ledger is now the one place a run's state lives. `mc.py classify` says whether a project is solo or collaborative and `mc.py watch` is the single PR watcher every crew session starts, quiet outside the team's hours. `mc.py retire` reclaims a merged task's worktree mid-run. A cleared coordinator is offered its role back, a restarted crew session picks up its old row, and scheduled jobs, open threads and the user's decisions are written to the ledger rather than held in conversation. Reconcile reads claims from the roadmap itself, nudges `/roadmap:maintain` after a crew PR merges and names a job whose session is gone. The board shows each crew session's context fill, warns off a haiku or sonnet coordinator, forwards a measurement's result to the session that asked for it and lets a slot be extended without `force`. Details in the plugin's changelog.
- Every plugin's README now lists its commands, the expected workflow in order and the things that run against it: mission-control, roadmap, goblin-chrome and goblin-util.

### Changed

- The mission-control board's crew group headings are bold, coloured by state and spaced, so the groups read as sections.

## [6.17.0] - 2026-10-28

### Added

- `mission-control` plugin 0.3.0: `mc.py reconcile` diffs the board against the live session registry, GitHub and the branches on origin. It prints each drift (a session gone, a crew task never joined, a merged PR whose row is not done, a need left open, a claim commit missing) and who each PR actually waits on by login. The coordinator runs it before every status and never slices a task without asking; crew sessions read their messages immediately before every push and verify rendered changes at the brief's new `Verify at` widths before reporting ready. Details in the plugin's changelog.
- A `gh` guard hook (`library/scripts/gh-guard.py`, wired per machine through `hooks/gh-body-guard.sh`) refuses an inline body on `gh api`, `gh pr comment`, `gh pr review` and `gh issue comment`, and refuses `gh release create` without a non-empty notes file. Both shapes caused real incidents in October: apostrophes stripped from quoted replies and two releases published with empty bodies.
- `pr-handle_review` ends each round with a fresh-context strict re-review of the fixes, at most twice, before drafting replies. The converged round is posted back to GitHub only when the user wrote the original review.
- `pr-land` writes the changelog for every tag a landing produces and, where that tag series already publishes releases, the release too, then reads back the tag, plugin version, changelog heading and release body before reporting.
- `pr-review-dry_run` strict mode runs the project's test suite on the PR head in a throwaway worktree cut from the pull ref, and follow-up mode settles every prior finding before looking for new ones. A failing suite blocks.

### Changed

- `doc-changelog` commits straight to `main` from a throwaway worktree, with a fetch and ancestry check before the push, and falls back to a `docs/` branch only when the remote refuses. Release notes are cut with python3, refused when empty and compared with the published body afterwards.
- `pr-handle_review` posts every reply and comment from a file, never from a quoted string.
- `CLAUDE.md` §8.2a records the docs-straight-to-main rule.

## [6.16.0] - 2026-10-28

### Added

- `mission-control` plugin 0.2.0: the board groups crew by state, each group under a subheading with its count. A coordinator's probed board now shows `merged` or `closed` beside a crew PR, and the coordinator can correct another session's row with `mc_report` and `for`. A crew session that opens a PR records it on the board without being asked. Details in the plugin's changelog.

### Fixed

- `mission-control`: a session whose folder path differed from the crew plan only in letter case now joins the run and appears on the board. Board refreshes land in the order they were read, session-row writes wait for the run lock instead of overwriting each other, and releasing a slot restores the state it interrupted. The kickoff and end skills give `mc.py --json status`, the flag order that works.

## [6.15.0] - 2026-10-27

### Added

- `roadmap` plugin 2.9.0: `validate` reports a `dependsOn` entry naming a task in a lower release tier when the task already requires it through another entry. A tier reaches a lower tier by milestone, never by task, so the edge adds nothing. The message names the covering entry and says to move the ID into `notes`; a roadmap that already carries such edges reports them as discrepancies. Details in the plugin's changelog.

### Changed

- `roadmap:update-tasks` and `roadmap:create-interview` apply the tier gate when adding a task: the lower-tier milestones its siblings carry, with a covered lower-tier prerequisite recorded as `Extends {ID}` in `notes` rather than wired. The proposal shows the gate and the sibling it came from.

## [6.14.1] - 2026-10-27

### Changed

- `pr-land` rebases a PR onto `main` itself when the only thing blocking it is a stale roadmap dashboard check (new Step 1.1). It acts once, only when the PR touches no roadmap file, the branch is behind `main` and `main`'s own run of that check passes. The rebase runs in the worktree that already holds the branch, or in a new one; it stops if another live session occupies that worktree or the branch has local commits the remote lacks. On a repo that requires reviews it asks before force-pushing; on a personal repo it records the pre-rebase SHAs and proceeds. A stacked PR names every layer `gh stack sync` will push. Afterwards it waits for the roadmap check to register on the new commit before re-running the readiness check.
- `pr-land`'s never-list and `pr-handle_review` name this rebase as the second exemption from "never rebase reviewed commits", beside a stack's cascading rebase. `pr-handle_review` never performs it.
- `library/references/stacked-prs.md` matches the `sync` row to gh-stack v0.2.1.

## [6.14.0] - 2026-10-27

### Added

- `mission-control` plugin 0.1.0: coordinate several Claude Code sessions on one repository. A ledger of shared-resource slots enforced by a `PreToolUse` hook, a `/mc` board pane, `mc_*` tools that report, request, grant and broadcast, a kick-off skill that creates the worktrees and writes each session's brief, and the protocol from the 23 October CHIRPdb run. CHIRPdb's `.claude/mission-control.json` is the first project config. Details in the plugin's changelog.

## [6.13.1] - 2026-10-26

### Fixed

- `stack-status.py` reads the `gh-stack` tracking file from the per-worktree git dir as well as the common dir. gh-stack v0.1.0 writes it to `git rev-parse --git-dir`, so from a linked worktree the script saw only the empty common-dir file and reported a tracked stack as untracked, with a `gh stack checkout` hint that changed nothing. It asks `gh stack --version` to decide which file that version reads from the current checkout (per worktree before 0.2.0, the common dir from 0.2.0) and counts only that one for the verdict; the other file's stacks are listed as not read from here. Its JSON gains `gh_stack_version`, `tracking_files`, `tracking_paths` and a `file` and `active` per stack; the table names the version, the files it read or the paths it looked in.
- `library/references/stacked-prs.md` describes where each gh-stack version keeps local tracking instead of calling it one file shared by every worktree.

## [6.13.0] - 2026-10-22

### Added

- Roadmap plugin 2.8.0: `/ready` shows every ready task, scrolls when the list outgrows the pane and groups the tasks by dev, milestone or tier. Details in the plugin's changelog.

## [6.12.0] - 2026-10-21

### Added

- `branch-stack` skill: read, link, extend, sync and tidy a GitHub stack without opening or landing a PR. Actions are `status`, `link`, `add`, `sync` and `tidy`; opening a layer stays with `pr-create` and landing one with `pr-land`.
- `stack-status.py` reports a verdict for each branch (`linked`, `chained-unlinked`, `independent` or `no-pr`), read from GitHub's stack field, the PR bases and local `gh-stack` tracking. Fork PRs are kept out of stack chains and local branch data.

### Changed

- `pr-create`, `pr-land`, `next-task-ship`, `branch-worktree`, `hud-worktrees` and `clod-role-git_manager` detect a stack with `stack-status.py` instead of guessing from a PR's base branch.
- `library/references/stacked-prs.md` covers the rebase model, stale local tracking and one worktree per stack.
- `CLAUDE.md` §1 brought up to date with the git record: Python moves from Learning to Proficient, GDScript is listed as Dabbled, FastAPI joins the backend table, pgvector and the MongoDB work are noted, the testing section lists the runners and practices actually in use, and deployment gains Docker Compose, Cloudflare tunnel and Colima.
- `CLAUDE.md` keeps its section numbers but moves reference detail (§1, plus the long tails of 7.5, 7.6, 8.2, 8.7 and 8.8) into `library/references/`.
- `project-context-loader` and `task-sync` agents run on haiku.
- The repo is licensed under zlib, with the licence scoped to the marketplace plugins.
- `.gitignore` is an allowlist: root entries are ignored unless named. `scratch/`, `output/`, `.claude/` and `settings.local.jsonc` are no longer tracked.
- The customisation guide moved to `docs/guides/` and the wiki index drops its dead links.

## [6.11.0] - 2026-10-15

### Added

- Web design family: `web-design` takes a new interface from a scope document, a roadmap task or an interview to an approved wireframe drawn in the product's own colours. `web-review` loops passes over a shared observation log until every entry is closed, writing back and saving a copy of the log into the repo each pass. `web-conventions` holds the shared ground: asset collation, the observation store's fields and statuses (now including `waived` and `source`) and eleven web principles.
- `web-check` runs the principles check after wireframe approval, at each pass end and at sign-off. `check.py` covers the mechanical half and the `web-principles` agent covers the judgement half; findings block until fixed or waived.
- `web-signoff-guard.sh` hook: `gh pr create` exits 2 while an export on the branch holds open entries. It needs an entry in `settings.json`; the entry is quoted in `docs/reference/hooks.md`.
- `web-walkthrough` captures every page, on every intended device, in every open state, under one naming rule and into a directory of its own.

### Changed

- Screenshots regenerated by `asset-shot` use the new naming rule: `home-390.png` becomes `390-home.png` and `home.png` in a mobile run becomes `1440-home.png`. Committed configs keep their paths, so only a regenerate renames anything.
- `artefact-conventions` and `asset-conventions` carry the shared conventions the web family depends on.
- Changelog skill reworked.

## [6.10.0] - 2026-10-15

### Added

- Roadmap plugin 2.7.0: every write to `roadmaps.json` records the minimum plugin version in a `min_plugin` stamp on each live phase, and dashboards record the version that rendered them. A plugin older than the stamp refuses to write over a roadmap or dashboard a newer plugin produced. Plugins before 2.7.0 ignore the stamp, so the guard protects only from this release onward. Details in the plugin's changelog.

## [6.9.0] - 2026-10-14

### Added

- Roadmap plugin 2.6.0: a phase chooses where its dashboard is written, through an `artefact` key set by `roadmap:configure`. Details in the plugin's changelog.

## [6.8.0] - 2026-10-12

### Breaking

- `branch-worktree new` no longer pauses for approval before creating a worktree; valid arguments are the approval.

### Added

- `branch-worktree new` runs `git worktree add` directly, uses the derived name when none is given and bootstraps the worktree: `worktree-bootstrap.sh` symlinks the main checkout's git-ignored `.env*` files at matching paths, then installs dependencies for each tracked lockfile (bun, poetry, uv, pnpm, npm). The session-start hook warns only when JS dependencies are missing and points at the script.
- Roadmap plugin 2.5.0: `claim` takes a blocked task when every unmet blocker is already claimed.

## [6.7.0] - 2026-10-09

### Added

- Roadmap plugin 2.4.0: `roadmap.py assign` sets or clears an assignee without claiming, and the `/ready` pane can replace an assignee, assign without claiming and act on a claim past the ninth row.

## [6.6.0] - 2026-10-09

### Breaking

- The `roadmap-pane@goblin-mode` plugin is gone. `/ready` now ships inside the roadmap plugin (2.3.0), so anyone who enabled the pane alone must enable `roadmap` instead.
- The config's own roadmap skills are retired: the eleven `roadmap-*` skills, `next-task-suggest`, `next-task-group` and `artefact-roadmap`. The roadmap plugin is the only copy, so invoke the `roadmap:` forms (`/roadmap:claim`, `/roadmap:maintain` and so on).
- `skills/` and `library/` no longer carry the roadmap CLI, its conventions reference or its artefact template. They live in `marketplace/roadmap/`.

### Added

- The goblin holds a prop while a skill runs, chosen by the skill's `metadata.family`: a parcel for `pr`, a lens for `clod-lens`, a pen for `clod-approach`. Props are measured in terminal cells, so wide characters keep the band aligned. Ships as goblin-chrome 0.2.0.
- Spinner words from a skill's `metadata.goblin-spinner`: the spinner shows one of them a minute while the skill runs. Every skill now carries three or four.
- A minion parade: each subagent out stands beside the goblin wearing the face its agent file sets under `goblin-minion`, until its own turn completes. Three are shown and the rest are a count. Every agent now carries a face.
- `python3 library/scripts/skill-lint.py` checks that each skill's glyph mirrors its model and exits 1 on a mismatch, a glyph without a model or a model without a glyph.
- `doc-changelog` gains a `pkg:NAME` scope that reads `.github/release-packages.json`, and `pr-land` offers it for every tag a landing produces.

### Changed

- The `/ready` pane draws a framed header, one row per release tier with a progress chip per milestone, two-line task cards and a separate claims section. Each failure state draws a card that names the skill that fixes it.
- The roadmap plugin is hand-maintained under `marketplace/roadmap/` and moves to 2.3.0; its own changelog lists the changes.

### Fixed

- `project-tag_version` carried Haiku's rune on a Sonnet skill. It now carries Sonnet's.
- A subagent's spinner is told apart from the main loop's by its agent id, and every minion stays in the parade however the subagents spawn.
- Agent faces that YAML reads as syntax or a number (`'>.<'`, `'@.@'`, `'0.0'`) are quoted, so the frontmatter check passes.

## [6.5.0] - 2026-10-08

### Added

- `roadmap-pane`, a mod built beside the roadmap plugin from `library/sources/plugins/roadmap-pane/`: `/ready` opens the ready set in a pane with the claims in play and milestone progress, claims a picked task after asking who and closes on a second `/ready`. It ships its own copy of the CLI, so a config that runs the roadmap skills from its own files enables the pane alone. Served as `roadmap-pane@goblin-mode`; this is its first release, 0.1.0.

### Changed

- The CLI's refusal for an old single-file `roadmaps.json` says `run the roadmap migrate skill first` and names no slash command, since the pane can run without the roadmap plugin installed. The pane's own hint names both `/roadmap:migrate` and `/roadmap-migrate`.
- The roadmap plugin moves to 2.2.0; its own changelog lists the changes.

### Fixed

- `/roadmap-claim` and the pane pass the assignee as `--assignee=<name>`, so a name that starts with a dash is recorded as a name instead of read as an option.

## [6.4.1] - 2026-10-07

### Fixed

- The goblin's face above each question has a visible head on dark terminals. Its outline now uses the theme's main text colour instead of the divider colour, which sat too close to the dark surface. The eyes, mouth and fang keep their accent colour. This ships as goblin-chrome 0.1.1.
- `roadmap.py` drops a milestone's terminal edge when other hard edges already reach that milestone. Task edges and soft edges are untouched, and a milestone always keeps at least one inbound edge.

## [6.4.0] - 2026-10-05

### Added

- `/branch-worktree use [worktree name|branch|path]` moves the session into a worktree that already exists. It matches an exact path first, then a directory name, then a branch; when one level matches several worktrees it asks which you mean. With no target it offers the worktrees under `.claude/worktrees/`, each shown with its branch and whether it is dirty. It stops on the worktree you are already in, a prunable one or any outside `.claude/worktrees/`. Before entering a worktree that another live session is working in, it asks. It never creates a worktree or a branch.

### Changed

- `/branch-worktree new` hands over to `use` when the branch is already checked out in a worktree under `.claude/worktrees/`, instead of jumping to its own final steps.
- `/hud-worktrees` names `/branch-worktree use` alongside `new` and `prune` in its suggestions.
- The header of `checkout-occupied.sh` now says a session that moved into a worktree with `EnterWorktree` is recorded against that worktree. The script itself is unchanged.

## [6.3.0] - 2026-10-05

### Changed

- Next Up cards on the roadmap dashboard share one three-row layout: milestone and task labels, then the description, then three counts for what finishing the task frees. `▶` counts tasks ready the moment it is done, `◐` counts tasks that still wait on something else and `↓` counts tasks further downstream. A legend explains the icons, the dev label no longer repeats under its own heading and faint dividers separate each dev's group.
- `/roadmap-update-devs` prints its sections under headings and its lists as bordered tables, with the task description in the last column so it wraps inside its cell. The reply grammar prints once, before the first batch.
- `roadmap.py ready` reports `unblocksNow`, `unblocksPartly` and `unblocksLater` for each candidate. A soft milestone member no longer counts as unblocking its milestone's dependents, so `transitiveUnblocks` drops for those tasks and they rank lower in `next-task-suggest`, `next-task-group` and `roadmap-claim`.
- `clod-config-skill_conventions` gains a "Terminal output templates" section: when a skill's output should use headings and tables.

## [6.2.0] - 2026-10-05

### Added

- `goblin-util`, two mods: `/pain` appends a pain point to `library/state/cc-pain-points.json` without a turn, with the repo, branch and last failed tool call pre-filled, as a typed line or from a small pane; `/fleet` shows every session on the machine from a heartbeat in the plugin's shared store and sends a picked session a message. One `enabled` switch. Served as `goblin-util@goblin-mode`.

## [6.1.0] - 2026-10-04

### Added

- `goblin-chrome`, the first mod: goblin-mode's face inside the terminal. A goblin in the band that paces, sits, sleeps, startles and watches beside the tier's rune; the turn's closing line and the hint tail in its register; a face above every question; frames by the model tier that served the request; a nine-state day on the local clock; colours from the project theme. One `enabled` switch. Served from the repo's marketplace as `goblin-chrome@goblin-mode`.
- `docs/reference/mods.md`: how a mod is laid out here, how to check one and the conventions the mods follow.

## [6.0.0] - 2026-10-02

### Breaking

- `/roadmap-update-devs` arguments change with no aliases: the `all` horizon is now `open` and the `devless` scope is now `free`. Anything that calls the old forms needs updating.
- `/hud-worktrees` is read-only. `new` and `clean` are gone; use `/branch-worktree new` and `/branch-worktree prune`.
- The roadmap plugin moves to `roadmap-v2.0.0`, which is what carries the root series to a major version. The two argument changes above are the plugin's breaking surface.

### Added

- `roadmap.py ready` takes `--milestones` or `--tiers` (mutually exclusive; `--tiers focus` picks the tier now underway), and a new `open` subcommand lists every task not done or out of scope with the same filters.
- `/roadmap-update-devs` arguments are all optional and default to `ready free current:project`. A third argument, `<phase>:<filter>`, narrows the list to a project, the focus tier, chosen tiers or chosen milestones. The resolved call is echoed before the interview starts.
- Tasks record when they finished. A new optional `ended` field comes with `end ID`, `stamp-ended --base REF --pr N` and `backfill-ended`, and `validate` rejects an `ended` that is malformed, set on a task that is not done or earlier than `started`.
- `/pr-land` stamps end dates onto the PR branch before the merge (Step 1.6), and `/roadmap-maintain` backfills missing dates from git history in a new step 3b, offering `first-seen` rows separately because their date is only a lower bound.
- `/roadmap-claim` claims a roadmap task when work starts and releases it when work stops, asking who is doing it. The claim nudge and the other roadmap skills now point at it.
- `/branch-worktree new` creates a worktree under `.claude/worktrees/` and moves the session into it; `/branch-worktree prune` clears merged worktrees, plus idle worktrees whose branch is still open (the branch stays), stray directories and heavy leftovers such as `.venv`.
- `worktree-state.sh` reports a worktree's dirty count and ahead/behind as JSON for the read-only map.

### Changed

- The dependency diagram in the roadmap dashboard leaves out `out_of_scope` tasks as well as done ones, along with the milestones and tiers they leave empty.
- Routine verification subagents in `/pr-handle_review` run on Sonnet.
- The stacked-PR docs and skills use commands Claude can run without a terminal: `gh stack link <stack#> <pr>` to append a PR, `-m` on `gh stack add` and `--open` on submit.

### Fixed

- `stamp-ended` refuses to run when the merge-base copy of the roadmap has no phase of the active name, instead of stamping every done task as finished by the branch.
- `backfill-ended` skips and reports a task whose date would precede its `started`, rather than writing a file that fails `validate`.
- `/pr-land` never runs a bare `gh stack merge`, which merged every layer of a stack including those above the approved PR; Step 2 now always names the PR.
- `/roadmap-claim` handles a `roadmaps.json` the CLI refuses to rewrite.
- `worktree-state.sh` exits 2 when `git status` fails instead of reporting a modified worktree as clean.

## [5.0.0] - 2026-10-01

### Breaking

- The roadmap plugin is declared stable as `roadmap-v1.0.0`, which is what moves the root series to a major version. Nothing breaks in behaviour: `stats --json`, `graph --mermaid`, the dashboard render data and the milestone states are as they were in 4.0.0.

### Added

- PR descriptions gain a Verification section (what was run and what was not) and an optional WARNING alert for breaking changes, so neither crowds the Overview.
- `md-lint.py` checks GitHub-rendered Markdown for five layout faults: a `---` that turns the line above into a heading, text swallowed by a `</details>` block, a missing blank line after `<summary>`, backticks inside `<summary>` and doubled rules.
- A `PreToolUse` hook, `pr-body-lint.sh`, blocks `gh pr create` and `gh pr edit` when the body would render wrongly, whichever skill or ad-hoc command wrote it. Its entry in `settings.json` is not in git, so copy it onto any other machine (see `docs/reference/hooks.md`).

### Changed

- PR descriptions open with a 2-4 sentence plain-language Overview. The detail moves to Changes, where each block gives an intro, a reason per bullet and a Review line.
- `pr-create` and `pr-update` run the layout linter before showing a draft, and `pr-update` reshapes a body written to the older template: verification notes and breaking-change text move out of the Overview.
- The roadmap plugin ships as `roadmap-v1.0.0`.

### Fixed

- The PR template keeps a blank line around every rule and `<details>` tag. Without them a `---` turned the text above it into a heading (CHIRPdb #139) and a `---` under `</details>` printed literally (#26).

## [4.0.0] - 2026-09-30

### Breaking

- `roadmap.py stats --json` measures `donePct` against in-scope tasks (the total less every `out_of_scope` task) rather than the raw total, and reports 100 rather than 0 for a milestone, tier or phase whose tasks are all out of scope.
- A milestone whose every unfinished task is blocked, with no claim in play, now reports state `blocked` where it reported `inProgress`; done work no longer softens it.
- `graph --mermaid` wraps each tier of a tiered phase in its own subgraph, so PHASE.md diagrams change shape at their next regeneration.
- `tierLabel` in the dashboard render data reads `Core` where it read `Primary`; the tier vocabulary is now core, secondary and tertiary in every projection.
- The out-of-scope node stroke changes to `#717171` (light) and `#898989` (dark) in every projection.

### Added

- Each tier header in the dashboard Overview carries its own readout (done, in-scope tasks, percentage and milestones) in the same shape as the phase headline.
- The dependency graph draws each tier of a tiered phase as a labelled subgraph: slate for a tier underway, taupe with a dashed border for one still deferred. The legend gains two tier swatches for tiered phases.

### Changed

- The dashboard Overview opens expanded, so the headline and progress cards show without a click.
- Task counts everywhere (stats line, dashboard headline, milestone counts) leave out-of-scope tasks out of both sides of the fraction, so a struck task is neither done nor outstanding.
- Inside each milestone the Blocked, Done and Out of Scope groups fold away by default, each with its task count in the heading.
- A stuck milestone sorts behind every milestone with actionable work and ahead of the finished ones, keyed on the same state that colours it, so colour and position agree; a tier-deferred milestone stays with its deferred siblings.
- Skill and agent frontmatter `model` levels refreshed across 18 files.
- The roadmap plugin ships as `roadmap-v0.2.0`.

### Fixed

- A milestone struck out whole draws a full progress bar rather than a green bar at 0% width.
- The task count sits at the far right of every milestone summary, with or without dev chips.

## [3.1.0] - 2026-09-29

### Added

- `checkout-occupied.sh` reports whether another live Claude session is working in a checkout. Its JSON lists each occupying session with the checkout's branch and its count of uncommitted files, and its exit code is 1 when the checkout is occupied.

### Changed

- `pr-land` now runs on opus; it ran on sonnet before.

### Fixed

- `pr-land` no longer runs `git checkout main` in your main checkout after a merge, a switch that sent another session's next commits to `main`. Post-merge work happens in a temporary detached worktree on `origin/main`, and the main checkout is fast-forwarded only when no other session is in it, it is on `main` and it has no uncommitted files.
- On a repo whose CI workflow tags on push, `pr-land` waits for that run and reports the tag CI created. It makes no tag of its own there.

## [3.0.0] - 2026-09-28

### Breaking

- The roadmap dashboard's milestone colour rules are rewritten: an empty milestone now flags as its own bug state instead of silently reading as todo, deferred status cascades through release tiers, and `paused` is dropped from milestone-level state (it now only applies to individual tasks). `stats --json`'s `milestones[].state` no longer includes `paused`, and `empty`/`deferred` mean something different than before.

### Added

- The roadmap dashboard groups milestones by tier within a phase, in collapsible sections that expand once a tier is live, with dev chips showing who's assigned work in each milestone.
- The dependency graph's layout direction (top-down or left-right) is now chosen automatically based on the shape of the graph, rather than fixed.
- `next-task-group` can now group tasks by dev, alongside the existing milestone and topic groupings.

### Fixed

- A milestone with a deferred task and no other actionable work now correctly shows as shelved instead of todo or in-progress.
- The dashboard's Overview section grid no longer collapses a tiered phase's milestones into a single narrow column.

## [2.6.0] - 2026-09-25

### Added

- Plugins can now carry their own version number and changelog, separate from the root repo's: `pr-land` bumps and tags a touched plugin alongside root, and `/doc-changelog plugin:NAME` builds that plugin's own changelog from its own source.

### Fixed

- `pr-land` checks out the PR branch before bumping its plugin's version, and now names the version script's own `--dir` flag instead of colliding with svu's.
- The roadmap plugin's changelog is now written beside its own hand-maintained sources, so a rebuild of the shipped plugin no longer wipes it out.
- The version script's untagged bootstrap path (picking a starting version when no tag exists yet) now only applies in plugin mode, leaving root-repo version resolution untouched.

## [2.5.0] - 2026-09-23

### Added

- Roadmap tasks can now record a claim: a `started` date set when work begins on a branch, shown on the dashboard, so in-progress work is visible before it's done.

### Fixed

- The claim hooks now stay quiet when they can't confidently tell whether a claim applies, instead of guessing.

## [2.4.0] - 2026-09-22

### Added

- A new shareable Roadmap plugin: generates a distributable roadmap dashboard plugin, listed in the goblin-mode marketplace, with its own README built from source and a build step that validates before writing.
- `clod-stack-gum` skill: guidance for building interactive shell prompts and styled terminal output with `gum`.

### Fixed

- The roadmap plugin build now keeps an unresolvable plugin root out of the build and quotes unshipped plugin paths correctly, instead of writing broken paths.
- `roadmap-review` now uses its own CLI path instead of a shared one.

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

[Unreleased]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.8.1...HEAD
[7.8.1]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.8.0...v7.8.1
[7.8.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.7.0...v7.8.0
[7.7.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.6.1...v7.7.0
[7.6.1]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.6.0...v7.6.1
[7.6.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.5.1...v7.6.0
[7.5.1]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.5.0...v7.5.1
[7.5.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.4.0...v7.5.0
[7.4.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.3.0...v7.4.0
[7.3.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.2.0...v7.3.0
[7.2.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.1.0...v7.2.0
[7.1.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v7.0.0...v7.1.0
[7.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.17.0...v7.0.0
[6.17.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.16.0...v6.17.0
[6.16.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.15.0...v6.16.0
[6.15.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.14.1...v6.15.0
[6.14.1]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.14.0...v6.14.1
[6.14.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.13.1...v6.14.0
[6.13.1]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.13.0...v6.13.1
[6.13.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.12.0...v6.13.0
[6.12.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.11.0...v6.12.0
[6.11.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.10.0...v6.11.0
[6.10.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.9.0...v6.10.0
[6.9.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.8.0...v6.9.0
[6.8.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.7.0...v6.8.0
[6.7.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.6.0...v6.7.0
[6.6.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.5.0...v6.6.0
[6.5.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.4.1...v6.5.0
[6.4.1]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.4.0...v6.4.1
[6.4.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.3.0...v6.4.0
[6.3.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.2.0...v6.3.0
[6.2.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.1.0...v6.2.0
[6.1.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v6.0.0...v6.1.0
[6.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v5.0.0...v6.0.0
[5.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v4.0.0...v5.0.0
[4.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v3.1.0...v4.0.0
[3.1.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.6.0...v3.0.0
[2.6.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.5.0...v2.6.0
[2.5.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v2.0.0...v2.3.0
[2.0.0]: https://github.com/JasonWarrenUK/goblin-mode/compare/v1.1.0...v2.0.0
