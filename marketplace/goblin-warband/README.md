# goblin-warband

A warband raids in good order or not at all. One chief, many sessions, one repo: orders read, dibs called, tribute paid, spoils counted.

> [!NOTE]
> A Claude Code plugin from [goblin-mode](https://github.com/JasonWarrenUK/goblin-mode) for running several sessions on one repository at once: one chief, one raider per task, one worktree each, shared resources held one session at a time. It came out of a five-hour, four-session raid on 23 October 2026 and keeps the protocol that worked while taking the typing out of it.

---

## 1. Install

```sh
claude plugin marketplace add JasonWarrenUK/goblin-mode
claude plugin install goblin-warband@goblin-mode
```

Requires `python3` (3.9+, stdlib only) on `PATH`, `lsof` and `pgrep` for the probes and `psql` where a resource probes a database. The slate draws in the terminal and needs Claude Code 2.1.287 or later; the hooks, the CLI and the skills work on any version. The goblin-scout plugin is optional: kick-off uses its ready set of waypoints and starts trails when it finds it.

**Upgrading from mission-control.** The marketplace's renames map loads goblin-warband in place of mission-control; if `/plugin` reports it not cached, run `/plugin install goblin-warband@goblin-mode` once. The first warband command moves `~/.claude/mission-control/` (archived raids included) to `~/.claude/goblin-warband/`, and says so once in a toast and in `/read-slate`. A repository's `.claude/mission-control.json` and its `.local` twin move too, but only where git ignores both the old name and the new one; each leaves a link at its old name, because a session still running the old plugin reads that name alone and would otherwise push with no gate until it restarts (delete the links once every session has restarted); a config git tracks, or one hidden by a rule that names the old file alone, stays where it is and is read from its old name, and the slate says how to rename it without taking the gate from a session still on the old plugin: a `git mv` in a commit once no such session is left, or a wider ignore rule and then a rename that leaves a link. Nothing needs renaming by hand while a raid is carried on. While a raid is still live in the old ledger nothing moves: the warband carries every raid on from the old ledger and the old config names with every gate in force, and says so in a toast and in `/read-slate`. Everything moves on the first command after the last raid there ends (`/end-raid` ends one); a raid whose repository no longer exists does not hold the move back. Once `~/.claude/goblin-warband/` exists it is the ledger: a raid that turns up in the old folder later (started by a session still on the old plugin) is never read or carried on, and a toast and `/read-slate` name the old folder. End such a raid first, from its repository, with `warband.py end --old-ledger --by-user`, which archives it under the old folder's `runs/` and needs no session on the old plugin. Only once no raid is live there and every session on the old plugin has restarted is the folder moved or deleted by hand. Leave the new folder to the move: one made by hand while a raid is live in the old ledger takes over at once, and that raid drops out of view. The move rewrites no values, so a push gate whose commands name `marketplace/mission-control` paths needs them changing by hand. Gate records are not carried over: green records under `<git-common-dir>/mission-control/gate/` are not read once renamed, so the first push of each commit after upgrading needs a fresh `warband.py gate` run. Restart sessions that were open before the update, so none of them keeps running the old plugin's hooks.

---

## 2. A raid, start to finish: what you type, where and what not to

### 2.1. The workflow, in order

| Moment           | Who                                                           | What |
|------------------|---------------------------------------------------------------|------|
| Once per project | the user, any session                                         | `/goblin-warband:configure-warband` writes `.claude/goblin-warband.json`: the shared resources, the commands that touch them, how to tell each one is busy, the check commands, the convention files, the conventions that live only in the user's head and `collaboration` (solo or collaborative, with the team's hours) |
| Kick-off         | the user, in an **opus** session that becomes the chief       | `/goblin-warband:declare-raid 10SE.2 10SE.4 name search` picks the tasks (from the roadbook's waypoints when there is one), classifies the project solo or collaborative and asks you to confirm, chooses each raider's model and effort with a reason, creates a worktree per task, starts the raid in the ledger, asks every convention it cannot read, sets numbered decrees, writes the guidance and one set of orders per raider and puts one launch line per raider on the tribute list |
| Launch           | the user                                                      | opens the slate (`/show-slate`) and runs each `launch` tribute in a new terminal window, one per raider. The line carries `cd <worktree>`, `--model` (which beats `ANTHROPIC_MODEL`), `--effort` (which beats your settings but not `CLAUDE_CODE_EFFORT_LEVEL`, if you export it) and the opening prompt, which starts the session's first turn; nothing else is typed into it. The tribute closes when the raider joins; the `SessionStart` hook names its orders and the chief, the mod puts it on the slate |
| The raid         | raiders and chief, by themselves                              | raiders answer the five questions, report state changes, request dibs, watch their PR once it exists and put anything only you can do on the tribute list; the chief reconciles before every status, grants dibs from the machine's state, settles decrees, reviews draft PRs when the raid says so, checks in and dismisses merged tasks' raiders |
| Whenever         | the user                                                      | `/show-slate` in any session shows the slate; the tribute list has complete commands with their directories, and that list is the whole of what the raid needs from you |
| End              | the user, in the chief's session                              | `/goblin-warband:declare-victory` links the stack, prunes what `retire` left, runs the checks on the top layer, offers the roadbook follow-ups and archives the ledger |

The protocol itself, with the message shapes: `references/protocol.md`.

### 2.2. Everything you can type

**Slash commands.** Each runs in the session named; the skill refuses or misbehaves elsewhere.

| Command                                                  | Where                                                         | Does |
|----------------------------------------------------------|---------------------------------------------------------------|------|
| `/goblin-warband:configure-warband`                      | any session in the project                                    | writes or revises the project config by interview |
| `/goblin-warband:declare-raid [ids...] [name <raid>]`    | the session that will lead (opus)                             | starts the raid; refuses while one is active |
| `/goblin-warband:lead-raid`                              | the chief's session                                           | the running protocol: reconcile, grant, check in, dismiss, escalate |
| `/goblin-warband:summon-raiders`                         | the chief's session                                           | asks every raider the three questions and gives you one list of the tribute you owe |
| `/goblin-warband:join-raid`                              | a raider, once, at its first turn (the launch line does this) | how that raider reports, asks for dibs, watches its PR and what stays with you |
| `/goblin-warband:declare-victory`                        | the chief's session                                           | closes the raid |

**Your own commands.** Your own hand on the ledger from any session, with no turn and no model. Every write carries `--by-user`.

| Form                                                     | Does |
|----------------------------------------------------------|------|
| `/show-slate`                                            | opens or closes the slate |
| `/start-raid <name> [anyway]`                            | starts a raid with this session as chief; a haiku or sonnet session is warned off and `anyway` overrides |
| `/grant-dibs <resource> <task\|branch\|name> [minutes]`  | grants dibs (taking them from a holder if need be) and messages the grantee |
| `/extend-dibs <resource> [minutes]`                      | gives the current holder longer and tells only them |
| `/release-dibs <resource>`                               | releases dibs |
| `/agree-tribute <n> [note]`                              | marks tribute `n` agreed (stored as `started`): you typed it and it runs on (a backfill, a long measurement); the note says where it is watched. It moves to the slate's `Tribute agreed` group and leaves the tribute count until `/pay-tribute` closes it with the result |
| `/pay-tribute <n> [result or @file]`                     | marks tribute `n` paid (stored as `done`); for a measurement, the pasted output (or a file's contents) goes to the session that wanted it in the same step |
| `/reclaim-post chief\|raider`                            | from the session taking the role: rebinds the raid to this session after a `/clear` or a fresh start (the slate shows `rebind?` when this is waiting), or carries over a raider's row |
| `/dismiss-raider <task> [dry]`                           | reclaims a merged task's worktree (section 7 has the preconditions); `dry` only prints |
| `/read-slate`                                            | the slate as text, machine probed |
| `/show-spoils [refresh]`                                 | opens the raid's spoils page in the browser; `refresh` asks GitHub and git first |
| `/claim-spoils <pr> [group]`                             | shows a PR from outside the raid on the spoils page, under the group named (Outside the raid by default) |
| `/ignore-spoils <pr>`                                    | stops reconcile naming an open PR no task claims |
| `/end-raid [force]`                                      | ends the raid; `force` ends it with dibs still held |

**The slate's keys** are in section 3.

**The CLI by hand.** `python3 <plugin-root>/scripts/warband.py <subcommand>` from inside the repository. You can run any of them; the ones that steer the raid take `--by-user` when typed by you from a session that is not the chief's. The ones worth knowing: `status [--probe]`, `gate` (run the project's push gate on HEAD, section 5.1), `reconcile`, `classify [--fresh]`, `retire <task> [--dry-run]`, `watch --pr <n> [--once]`, `needs list`, `needs add --why ... --kind measurement --for <task> [--supersedes <n>]`, `needs start <n> --note ...`, `needs done <n> [--result ...|--superseded-by <m>]`, `prs add|pin|ignore|hold|release|note|list`, `dashboard [--refresh] [--open]`, `crew list`, `crew add --task ... --model <m> --effort <e> --name ... --reason ... [--unlisted] [--plugin-dir <root>]` (which puts the raider's launch line on the tribute list), `adopt coordinator|crew`, `jobs list [--all]`, `pending list`, `decide list`, `probe [resource]`, `end --old-ledger` (ends and archives a raid left live in the old mission-control folder beside the new one). `--help` lists the rest.

### 2.3. Do not

Each of these runs against the protocol, and most were learned on a live raid.

- **Do not lead from a haiku or sonnet session.** The mod refuses `warband.py start` from one; `--small-model-ok` and `anyway` exist for the case where you mean it, and that case has not come up.
- **Do not type into a raider after its launch line**, and do not strip `--model`, `--effort` or a leading `CLAUDE_CODE_SUBAGENT_EFFORT=high` from the line: kick-off chose them for the task and the orders' Model row says why; without the flag the terminal's `ANTHROPIC_MODEL` decides, which is how every raider ran Sonnet in October 2026. Its instructions come from its orders and the chief's messages. A ruling goes to the chief's session, which broadcasts it; a command only you can run goes on the tribute list, which tells you the directory.
- **Do not run a gated command yourself in a worktree another session holds the dibs for**, and do not run one from the main checkout during a raid. The dibs are what keep two resets apart.
- **Do not run hosted reads, hosted writes or merges from any session.** They are taboos; a session that is refused is behaving correctly. Type them yourself from the tribute list.
- **Do not prune a worktree by hand mid-raid.** `retire` checks the session is closed, the PR landed, the tree clean and nothing running in it; `end` is the backstop.
- **Do not set up your own PR polling, Monitor or cron in a raider and do not tell sessions to pause for the night.** `warband.py watch` is the one shape; the quiet hours come from `collaboration.hours` in the config.
- **Do not start a raid while one is active**, and do not edit `run.json` or a session row by hand. `warband.py end` archives; the CLI is the only writer.
- **Do not pass `--by-user`, `--session` or `CLAUDE_CODE_SESSION_ID=` to a model.** The hook refuses a `warband.py` line a model runs with any of them; they are yours.
- **Do not state a convention to the chief that is not written in the repository.** Put it in the config's `facts` instead, so the next raid has it too.
- **Do not expect the chat to be the truth.** The slate is; a session whose row is stale is told to report, not believed.
- **Do not fix a `/clear` by editing `run.json`.** A `/clear` gives the chief a new session id; the slate shows `rebind?` and `/reclaim-post chief` from that session rebinds the raid, logged. A raider restarted in its worktree adopts its own row on join.
- **Do not relay a measurement by hand.** The tribute is raised with kind `measurement`; `/pay-tribute <n>` with the output pasted (or `@<file>`) sends it to the session that wanted it and closes the tribute in one step.
- **Do not let a session schedule anything only in conversation.** A cron job or Monitor is recorded with `warband.py jobs add` first, so a resume is told what it had and re-arms what is missing (CronList first, since a resume restores cron jobs); the PR watch records itself. The chief's open threads go on the pending list and the user's rulings on the rulings record, so a compaction loses neither.

---

## 3. `/show-slate`: the slate

Opens a pane with the raid, or closes it. In a fullscreen terminal of 110 columns or more it docks beside the transcript; narrower, it sits above the prompt. Docked, it asks for 100 columns, but the engine caps a dock at 45% of the terminal, so it gets 100 only from about 222 columns (a 120-column window gives it 54); a width you drag the dock to wins. Each raider's row lines its state, PR, context and age up in columns sized to the rows on screen; on a narrow pane age drops first, then context, except that context stays while any raider is at 70% or more. The summary sits on the line below, ahead of the branch, so the cut at the edge takes the branch. It runs with no turn, so it works while Claude is busy. While open it refreshes itself every `refresh_seconds`.

| Section     | Shows |
|-------------|-------|
| Header      | raid name as the title with your role beside it, a rule, a `rebind?` line in amber when the chief's process runs under a new session id and waits for `/reclaim-post chief`, the count of open threads on the chief's pending list, then in dim text the start time, base commit, who leads, how many decrees, how many sessions are live and the ledger's age |
| Raiders     | the live sessions grouped by state, one row each: busy or idle (from Claude Code's own session registry), task, branch, worktree name, state (reading orders, raiding, holding dibs, spoils ready, blocked, waiting, awaiting tribute, done), PR with GitHub's word beside it, `watching` while its PR watcher runs, `ctx 63%` (the session's own context fill, amber from 70, red from 85), last summary and the age of the last report (`2m ago`) |
| PRs         | drawn once a PR is recorded: one line of totals (open, ready to merge, held, questions), then only the PRs where you move next, with any restamp cost; `o` opens the full page |
| Tribute owed | drawn only while something is owed. Numbered; the complete line to type comes first (`cd <dir> && ...`) and the reason beneath it, with `result → <task>` on a measurement naming the session that gets the output when you mark it paid and `launch` on a raider's launch line, which runs in a new terminal window and closes by itself when the raider joins; the count is what the raid needs from you now |
| Tribute agreed | tribute you have agreed that runs on, each with its start time and the note on where it is watched; no command to type, `d` with the result closes each |
| Dibs        | each held resource with its holder, window and purpose; overdue in red; what the machine says about it; the free resources |
| Dibs called | pending dibs requests, with what will run and for how long |
| Archive     | drawn only once a session is over: dismissed (its worktree reclaimed) and gone (the session left; its last state dimmed beside it), each group collapsed to its heading and count until `c` shows the rows |

| Key           | Does |
|---------------|------|
| `1` to `9`    | picks a session row (shows its full summary) |
| `q` to `p`    | picks a request |
| `g`           | grants the picked request: asks the minutes, then grants as you and messages the grantee |
| `s`           | marks the picked tribute agreed: you typed it and it runs on; the input takes a note on where it is watched |
| `d`           | marks the picked tribute paid; the input takes the result (or `@<file>`) for a measurement, which goes to the session that wanted it |
| `x`           | releases dibs (asks which) |
| `c`           | shows or collapses the Archive's rows (dismissed and gone), collapsed by default to their headings and counts |
| `o`           | opens the spoils page in the browser |
| `r`           | refreshes, probing the machine |
| Esc, or `/show-slate` | closes |

The other commands are your hand on the ledger from any session, no turn, no model: `/start-raid <name> [anyway]`, `/grant-dibs <resource> <task|branch|name> [minutes]`, `/release-dibs <resource>`, `/pay-tribute <n>`, `/dismiss-raider <task> [dry]`, `/read-slate`, `/end-raid [force]` (the full table is in section 2.2). Every write they make carries `--by-user`, which the hook refuses on any `warband.py` command a model runs (and on the old plugin's `mc.py`, which can still write to a carried-on ledger), along with `--session` and a `CLAUDE_CODE_SESSION_ID=` assignment. That is a guard against accidents: a variable expanded later, a copied script or a hand-written ledger file get past it.

---

## 4. The tools

Registered in every session where the plugin is on; the CLI refuses the chief-only ones from anywhere else. Each tool writes the ledger and then hands the model the exact `SendMessage` call to make, recipient named as `ListAgents` lists it: a message the mod sent itself got no verdict from the auto-mode classifier in every session of the first live raid, while the model's own `SendMessage` is judged as usual.

| Tool                   | Who     | Does |
|------------------------|---------|------|
| `warband_report`       | raider  | state (`briefing` reading orders, `working` raiding, `in-slot` holding dibs, `pr-ready` spoils ready, `blocked`, `waiting` with what it waits on, `waiting-jason` awaiting tribute while a tribute of its own is owed, `done`), one-line summary, PR number |
| `warband_dibs`         | raider  | `request` records the request and hands over the line for the chief (what will run, for how long); `release` records the results and hands over the line that reports them |
| `warband_tribute`      | anyone  | an item only the user can do: why, the exact command, the directory and `pr` when it blocks one. Kind `question` is a question for the user, with no command; the answer goes back to the asker when it is marked paid. Goes on the slate and the spoils page; from a raider, the line for the chief follows. `supersedes` re-issues an earlier tribute that failed, keeping its kind, recipient and directory |
| `warband_send`         | anyone  | resolves a task id, branch, session name, `chief` or `all` to the recipient names `SendMessage` takes now, so a changed name or ref does not lose a session |
| `warband_grant`        | chief   | probes the machine, refuses while busy, grants, then hands over the grant line for the grantee and the notice line for every other raider |
| `warband_revoke`       | chief   | releases another session's dibs and hands over the line that tells the holder |
| `warband_decree`       | chief   | sets or changes a numbered decree; every raider's prompt carries the list, and the broadcast line follows for each live raider |
| `warband_ruling`       | chief   | records what the user decided (a finding's routing, one option over another, a scope withdrawn) with the sessions told, and hands over the line for each; a raider acknowledges with `warband.py decide ack <n>` |
| `warband_slate`        | chief   | the slate as text, probes included |
| `warband_label_spoils` | chief   | one sentence on a PR's line on the spoils page, for what cannot be derived; it disappears once the PR's head, review decision or state moves |

---

## 5. The hooks and the dibs

Three things enforce the dibs; none asks a session to do what its own permissions refuse.

- **`PreToolUse` on Bash** (`scripts/warband.py hook pre-tool-use`): during a raid, a command matching a resource's `gate` is refused unless this session holds the dibs and runs it from its own worktree. The refusal says who holds them and how to ask, and the attempt appears on the slate as a request. A `human_gate` resource (a taboo) gets context instead of a verdict. The same hook gates a command inside `sh -c`, `bash -c` or `zsh -c`, and a subagent's calls count as its parent's. `--by-user`, `--session` and `CLAUDE_CODE_SESSION_ID=` on a model's `warband.py` command line are refused.
- **The mod's `tool.check` on Bash**: when the project's own hook answers `ask` on a gated command (CHIRPdb's `db-reset-local-anyway`, say), and this session holds the dibs, runs from its worktree and the resource is `approve_in_slot`, the mod answers `allow`. A `deny` is never loosened. Off with the `approve_in_slot` option.
- **`SessionStart`** (`scripts/warband.py hook session-start`): a session starting inside a planned worktree is told its task, the chief's name and socket, where its orders are and to invoke `/goblin-warband:join-raid`.

A fourth hook has nothing to do with dibs: `PreCompact` (`scripts/warband.py hook pre-compact`) tells the compaction summary what a session in a raid must keep. `references/config.md` says what each hook does.

Hosted reads, credentials, writes, merges and anything irreversible stay with the user: the config marks them `human_gate` (the taboos), no dibs cover them and the path is the tribute list with the exact command. A hosted command's directory is the main checkout: only that tree is linked to the hosted project (the link is in a git-ignored folder a worktree does not get), so `needs add` moves a worktree directory to the same place in the main checkout and says so on the tribute.

### 5.1. The push gate

A project opts in with `push_gate` in its config (see `references/config.md`). The same `PreToolUse` hook then refuses a `git push` until `python3 <plugin-root>/scripts/warband.py gate` has printed green for the commit the push names (HEAD when it names none). The gate runs the named `commands` entries in order from the checkout root against the committed HEAD, stops at the first failure and writes a record under the git common dir; it refuses to run over uncommitted tracked changes or untracked files that are not ignored, because the record is for the commit (`warband.py gate --allow-untracked` overrides the second). A push while a gate run is in flight is refused, and a new commit makes the old record stale, and so does a key added to `push_gate` that the record did not run. Dry runs, bare tag pushes and deletions carry no branch tip and pass; `exempt` globs let a docs-only push through when it goes to the branch it is diffed against (the upstream, else origin's HEAD) on the same remote. Glob refspecs, `--all`, `--branches`, `--mirror` and `push.default=matching` name no single tip, so only HEAD's record is read and the other tips they send go unchecked. It applies in any session of the repository, raid or no raid. Like the rest of the guard it stops accidents: a hand-written record gets past it.

---

## 6. Trust between sessions

The user starts the raid in the chief's session; the ledger records that session's id, and reads its messaging socket and name live from Claude Code's session registry on every read, since a restart or a resume changes both while the id stays. Every raider's system prompt gains a section naming the raid, the chief's session and socket, the decrees and the taboos. A cross-session message carries its sender's socket in the harness's `from` attribute; the receiving mod marks a message from the chief's socket as verified against the ledger, one from a raider's socket as that raider's and one from any other socket that opens by speaking as the warband or the chief (under the new names or the old) as not the chief. Anything else is an ordinary peer and gets no mark. No passphrase, nothing saved to memory, no trust line to type.

The boundary is honest about what it is: every session on the machine is the same user's, and a peer message is treated as a teammate's by Claude Code already. The mark tells the raider which teammate carries the user's instructions for this raid.

---

## 7. The ledger

`~/.claude/goblin-warband/<repo slug>/`, one JSON file per fact so sessions never clobber each other: `run.json` (name, chief, base, PR approval, collaboration, raiders' plan, decrees, tribute, the chief's pending list), `sessions/<id>.json` (the row, its watch and its scheduled jobs; a row carried over to a new session id leaves `<old id>.json.adopted` behind), `slots/<resource>.json` (the dibs), `requests/<resource>__<id>.json`, `decisions.jsonl` (the rulings: what the user decided, appended, with each session's acknowledgement), `prs/<n>.json` (one per PR the raid cares about: task, group, pinned, hold and what lifts it, the chief's note), `pr-facts.json` and `migrations.json` (the cached GitHub facts and migration scan the spoils page reads), `dashboard.html` (the spoils page itself, redrawn on every ledger write), `briefs/<task>.md` (the orders), `guidance.md`, `log.jsonl`. `warband.py end` moves it under `runs/`. None of it needs a working git: while git works it answers for the checkout and `gh` chooses the repository as it always has; when git fails the checkout and the remote are read from the `.git` entry and the git config file (the remote chosen the way `gh` chooses it: the one `gh repo set-default` marked, else `upstream`, else `github`, else `origin`), every `gh` call names that repository outright, and (a macOS update removing the Command Line Tools, say) the slate, `status` and `reconcile` print one line naming the cause and the fix while tribute, dibs, messages and the watcher carry on; only what needs history (the claim check, `retire`, the author count) waits for git. The CLI identifies a caller by `CLAUDE_CODE_SESSION_ID`, which Claude Code sets for every Bash child; the mod passes its own id. Writes that steer the raid are the chief's or `--by-user`.

`python3 <plugin-root>/scripts/warband.py --help` lists every subcommand; `status --probe` is the slate as text. `reconcile` diffs the ledger against the live registry, GitHub and the branches on origin (each merged PR's own base, each open PR's own branch) and prints what drifted (gone or unjoined sessions, merged PRs whose row is not done, tribute left owed, a waypoint whose roadbook carries no trail at the ref where it ought to; a task the roadbook does not list is named once, with no trail expected; a merged task's worktree still on disk an hour on; a merged raider's PR whose waypoint still reads `todo` on the roadbook at the trunk, answered by `/goblin-scout:tend-roadbook` from the main checkout; a PR the watcher saw approved and not yet landed, with the time) and who each PR actually waits on. `warband.py` reads the roadbook from `.claude/roadbook.json` first and falls back to `.claude/roadmaps.json`. `retire <task>` dismisses a finished raider's worktree while the raid goes on: it refuses while the session is live, the row is not done, the PR is open, the tree is dirty, dibs are held, something runs in the tree or an open PR is stacked on the branch, then removes the worktree, prunes, deletes the branch with `-d` only and records it on the row; `--dry-run` prints what would go and the disk it holds. `classify` says whether the project is solo or collaborative (stated as `collaboration` in the config or its gitignored `.local` twin, else inferred from 90 days of authors and the reviews on merged PRs) and the team's hours; `start` records the answer on the raid. `watch [--pr N]` is a raider's PR watcher, run in the background: a five-minute `gh` poll that prints the first change (reviews, decision, comments, checks, state) and exits, held outside the team's hours on a collaborative project unless the PR merged or closed.

---

## 8. Options

| Option            | Default | What it does |
|-------------------|---------|--------------|
| `enabled`         | true    | The one switch. Off, nothing is registered; the command hooks still run |
| `approve_in_slot` | true    | Answer a project hook's `ask` with `allow` while this session holds the dibs and runs from its worktree |
| `refresh_seconds` | 15      | How often an open slate rereads the ledger |

---

## 9. Files

| File                                          | Holds |
|-----------------------------------------------|-------|
| `scripts/warband.py`                          | The ledger CLI and both command hooks; `python3 -m unittest test_warband` in that directory runs its tests |
| `scripts/worktree-bootstrap.sh`               | Symlinks git-ignored `.env*` files and installs every tracked lockfile in a fresh worktree |
| `hooks/register.tsx`                          | The slate, the slash commands, the tools, the prompt section, the message mark, the dibs approval; `claude plugin test <plugin-root>` runs `hooks/warband.test.tsx` |
| `types/index.d.ts`                            | The `$.state` contract |
| `references/protocol.md`                      | The protocol, with the message shapes |
| `references/config.md`                        | The project config schema |
| `references/goblin-warband.example.json`      | CHIRPdb's config |
| `templates/brief.md`, `templates/guidance.md` | What kick-off writes per raider (the orders) and per raid |
| `skills/`                                     | `declare-raid`, `lead-raid`, `join-raid`, `summon-raiders`, `declare-victory`, `configure-warband` |

Check it with `claude plugin validate <plugin-root> --strict` and `claude plugin test <plugin-root>`.
