# mission-control

> [!NOTE]
> A Claude Code plugin from [goblin-mode](https://github.com/JasonWarrenUK/goblin-mode) for running several sessions on one repository at once: one coordinator, one crew session per task, one worktree each, shared resources held one session at a time. It came out of a five-hour, four-session run on 23 October 2026 and keeps the protocol that worked while taking the typing out of it.

---

## 1. Install

```sh
claude plugin marketplace add JasonWarrenUK/goblin-mode
claude plugin install mission-control@goblin-mode
```

Requires `python3` (3.9+, stdlib only) on `PATH`, `lsof` and `pgrep` for the probes and `psql` where a resource probes a database. The board draws in the terminal and needs Claude Code 2.1.287 or later; the hooks, the CLI and the skills work on any version. The roadmap plugin is optional: kick-off uses its ready set and claims when it finds it.

---

## 2. A run, start to finish: what you type, where, and what not to

### 2.1. The workflow, in order

| Moment | Who | What |
|---|---|---|
| Once per project | the user, any session | `/mission-control:configure` writes `.claude/mission-control.json`: the shared resources, the commands that touch them, how to tell each one is busy, the check commands, the convention files, the conventions that live only in the user's head, and `collaboration` (solo or collaborative, with the team's hours) |
| Kick-off | the user, in an **opus** session that becomes the coordinator | `/mission-control:kickoff 10SE.2 10SE.4 name search` picks the tasks (from the roadmap when there is one), classifies the project solo or collaborative and asks you to confirm, creates a worktree per task, starts the run in the ledger, asks every convention it cannot read, sets numbered shared assumptions, writes the guidance and one brief per session, and prints a launch line per session |
| Launch | the user | runs each launch line in a fresh terminal. The line ends with the opening prompt, which starts the session's first turn; nothing else is typed into it. The `SessionStart` hook names its brief and the coordinator, the mod puts it on the board |
| The run | crew and coordinator, by themselves | crew answer the five questions, report state changes, request slots, watch their PR once it exists and put anything only you can do on the needs list; the coordinator reconciles before every status, grants slots from the machine's state, settles assumptions, reviews draft PRs when the run says so, checks in and retires merged tasks' worktrees |
| Whenever | the user | `/mc` in any session shows the board; the needs list has complete commands with their directories, and that list is the whole of what the run needs from you |
| End | the user, in the coordinator session | `/mission-control:end` links the stack, prunes what `retire` left, runs the checks on the top layer, offers the roadmap follow-ups and archives the ledger |

The protocol itself, with the message shapes: `references/protocol.md`.

### 2.2. Everything you can type

**Slash commands.** Each runs in the session named; the skill refuses or misbehaves elsewhere.

| Command | Where | Does |
|---|---|---|
| `/mission-control:configure` | any session in the project | writes or revises the project config by interview |
| `/mission-control:kickoff [ids...] [name <run>]` | the session that will coordinate (opus) | starts the run; refuses while one is active |
| `/mission-control:coordinate` | the coordinator session | the running protocol: reconcile, grant, check in, retire, escalate |
| `/mission-control:checkin` | the coordinator session | asks every crew session the three questions and gives you one list of what you need to do |
| `/mission-control:crew` | a crew session, once, at its first turn (the launch line does this) | how that session reports, asks for slots, watches its PR and what stays with you |
| `/mission-control:end` | the coordinator session | closes the run |

**`/mc`.** Your own hand on the ledger from any session, with no turn and no model. Every write carries `--by-user`.

| Form | Does |
|---|---|
| `/mc` | opens or closes the board |
| `/mc start <name> [anyway]` | starts a run with this session as coordinator; a haiku or sonnet session is warned off and `anyway` overrides |
| `/mc grant <resource> <task\|branch\|name> [minutes]` | grants a slot, taking it from a holder if need be, and messages the grantee |
| `/mc extend <resource> [minutes]` | gives the current holder longer and tells only them |
| `/mc release <resource>` | releases a slot |
| `/mc done <n> [result or @file]` | marks need `n` done; for a measurement, the pasted output (or a file's contents) goes to the session that wanted it in the same step |
| `/mc adopt coordinator\|crew` | from the session taking the role: rebinds the run to this session after a `/clear` or a fresh start (the board shows `rebind?` when this is waiting), or carries over a crew row |
| `/mc retire <task> [dry]` | reclaims a merged task's worktree (section 7 has the preconditions); `dry` only prints |
| `/mc status` | the board as text, machine probed |
| `/mc end [force]` | ends the run; `force` ends it with slots still held |

**The board's keys** are in section 3.

**The CLI by hand.** `python3 <plugin-root>/scripts/mc.py <subcommand>` from inside the repository. You can run any of them; the ones that steer the run take `--by-user` when typed by you from a session that is not the coordinator. The ones worth knowing: `status [--probe]`, `reconcile`, `classify [--fresh]`, `retire <task> [--dry-run]`, `watch --pr <n> [--once]`, `needs list`, `needs add --why ... --kind measurement --for <task>`, `crew list`, `crew add ... --unlisted`, `adopt coordinator|crew`, `jobs list [--all]`, `pending list`, `decide list`, `probe [resource]`. `--help` lists the rest.

### 2.3. Do not

Each of these runs against the protocol, and most were learned on a live run.

- **Do not coordinate from a haiku or sonnet session.** The mod refuses `mc.py start` from one; `--small-model-ok` and `anyway` exist for the case where you mean it, and that case has not come up.
- **Do not type into a crew session after its launch line.** Its instructions come from its brief and the coordinator's messages. A decision goes to the coordinator session, which broadcasts it; a command only you can run goes on the needs list, which tells you the directory.
- **Do not run a gated command yourself in a worktree another session holds the slot for**, and do not run one from the main checkout during a run. The slot is what keeps two resets apart.
- **Do not run hosted reads, hosted writes or merges from any session.** They are human gates; a session that is refused is behaving correctly. Type them yourself from the needs list.
- **Do not prune a worktree by hand mid-run.** `retire` checks the session is closed, the PR landed, the tree clean and nothing running in it; `end` is the backstop.
- **Do not set up your own PR polling, Monitor or cron in a crew session, and do not tell sessions to pause for the night.** `mc.py watch` is the one shape; the quiet hours come from `collaboration.hours` in the config.
- **Do not start a run while one is active**, and do not edit `run.json` or a session row by hand. `mc.py end` archives; the CLI is the only writer.
- **Do not pass `--by-user`, `--session` or `CLAUDE_CODE_SESSION_ID=` to a model.** The hook refuses an `mc.py` line a model runs with any of them; they are yours.
- **Do not state a convention to the coordinator that is not written in the repository.** Put it in the config's `facts` instead, so the next run has it too.
- **Do not expect the chat to be the truth.** The board is; a session whose row is stale is told to report, not believed.
- **Do not fix a `/clear` by editing `run.json`.** A `/clear` gives the coordinator a new session id; the board shows `rebind?` and `/mc adopt coordinator` from that session rebinds the run, logged. A crew session restarted in its worktree adopts its own row on join.
- **Do not relay a measurement by hand.** The need is raised with kind `measurement`; `/mc done <n>` with the output pasted (or `@<file>`) sends it to the session that wanted it and closes the need in one step.
- **Do not let a session schedule anything only in conversation.** A cron job or Monitor is recorded with `mc.py jobs add` first, so a resume is told to re-arm it; the PR watch records itself. The coordinator's open threads go on the pending list and the user's decisions on the decisions record, so a compaction loses neither.

---

## 3. `/mc`: the board

Opens a pane with the run, or closes it. In a fullscreen terminal of 110 columns or more it docks beside the transcript; narrower, it sits above the prompt. It runs with no turn, so it works while Claude is busy. While open it refreshes itself every `refresh_seconds`.

| Section | Shows |
|---|---|
| Header | run name as the title with your role beside it, a rule, a `rebind?` line in amber when the coordinator's process runs under a new session id and waits for `/mc adopt coordinator`, the count of open threads on the coordinator's pending list, then in dim text the start time, base commit, who coordinates, how many assumptions, how many sessions are live and the ledger's age |
| Crew | grouped by state, one row per session: live and busy or idle (from Claude Code's own session registry), task, branch, worktree name, state (`gone` and dimmed once the session has left, `retired` once its worktree is reclaimed), PR with GitHub's word beside it, `watching` while its PR watcher runs, `ctx 63%` (the session's own context fill, amber from 70, red from 85), last summary and the age of the last report (`2m ago`) |
| Slots | each held resource with its holder, window and purpose; overdue in red; what the machine says about it; the free resources |
| Requests | pending slot requests, with what will run and for how long |
| Needs Jason | numbered, each with the complete command (`cd <dir> && ...`) and, for a measurement, `result → <task>` naming the session that gets the output when you mark it done |

| Key | Does |
|---|---|
| `1` to `9` | picks a session row (shows its full summary) |
| `q` to `p` | picks a request |
| `g` | grants the picked request: asks the minutes, then grants as you and messages the grantee |
| `d` | marks the picked need done; the input takes the result (or `@<file>`) for a measurement, which goes to the session that wanted it |
| `x` | releases a slot (asks which) |
| `r` | refreshes, probing the machine |
| Esc, or `/mc` | closes |

`/mc` with arguments is your hand on the ledger from any session, no turn, no model: `/mc start <name> [anyway]`, `/mc grant <resource> <task|branch|name> [minutes]`, `/mc release <resource>`, `/mc done <n>`, `/mc retire <task> [dry]`, `/mc status`, `/mc end [force]` (the full table is in section 2.2). Every write it makes carries `--by-user`, which the hook refuses on any `mc.py` command a model runs, along with `--session` and a `CLAUDE_CODE_SESSION_ID=` assignment. That is a guard against accidents: a variable expanded later, a copied script or a hand-written ledger file get past it.

---

## 4. The tools

Registered in every session where the plugin is on; the CLI refuses the coordinator-only ones from anywhere else. Each tool writes the ledger and then hands the model the exact `SendMessage` call to make, recipient named as `ListAgents` lists it: a message the mod sent itself got no verdict from the auto-mode classifier in every session of the first live run, while the model's own `SendMessage` is judged as usual.

| Tool | Who | Does |
|---|---|---|
| `mc_report` | crew | state (`briefing`, `working`, `in-slot`, `pr-ready`, `blocked`, `waiting-jason`, `done`), one-line summary, PR number |
| `mc_slot` | crew | `request` records the request and hands over the line for the coordinator (what will run, for how long); `release` records the results and hands over the line that reports them |
| `mc_need` | anyone | an item only the user can do: why, the exact command, the directory. Goes on the board; from crew, the line for the coordinator follows |
| `mc_send` | anyone | resolves a task id, branch, session name, `coordinator` or `all` to the recipient names `SendMessage` takes now, so a changed name or ref does not lose a session |
| `mc_grant` | coordinator | probes the machine, refuses while busy, grants, then hands over the grant line for the grantee and the notice line for every other crew session |
| `mc_revoke` | coordinator | releases another session's slot and hands over the line that tells the holder |
| `mc_assume` | coordinator | sets or changes a numbered shared assumption; every crew prompt carries the list, and the broadcast line follows for each live crew session |
| `mc_board` | coordinator | the board as text, probes included |

---

## 5. The hooks and the slot

Three things enforce the slot; none asks a session to do what its own permissions refuse.

- **`PreToolUse` on Bash** (`scripts/mc.py hook pre-tool-use`): during a run, a command matching a resource's `gate` is refused unless this session holds the slot and runs it from its own worktree. The refusal says who holds it and how to ask, and the attempt appears on the board as a request. A `human_gate` resource gets context instead of a verdict. The same hook gates a command inside `sh -c`, `bash -c` or `zsh -c`, and a subagent's calls count as its parent's. `--by-user`, `--session` and `CLAUDE_CODE_SESSION_ID=` on a model's `mc.py` command line are refused.
- **The mod's `tool.check` on Bash**: when the project's own hook answers `ask` on a gated command (CHIRPdb's `db-reset-local-anyway`, say), and this session holds the slot, runs from its worktree and the resource is `approve_in_slot`, the mod answers `allow`. A `deny` is never loosened. Off with the `approve_in_slot` option.
- **`SessionStart`** (`scripts/mc.py hook session-start`): a session starting inside a planned worktree is told its task, the coordinator's name and socket, where its brief is and to invoke `/mission-control:crew`.

Hosted reads, credentials, writes, merges and anything irreversible stay with the user: the config marks them `human_gate`, no slot covers them, and the path is the needs list with the exact command.

---

## 6. Trust between sessions

The user starts the run in the coordinator session; the ledger records that session's id, and reads its messaging socket and name live from Claude Code's session registry on every read, since a restart or a resume changes both while the id stays. Every crew session's system prompt gains a section naming the run, the coordinator's session and socket, the shared assumptions and the human gates. A cross-session message carries its sender's socket in the harness's `from` attribute; the receiving mod marks a message from the coordinator's socket as verified against the ledger, one from a crew session's socket as that crew's, and one from any other socket that opens by speaking as mission control or the coordinator as not the coordinator. Anything else is an ordinary peer and gets no mark. No passphrase, nothing saved to memory, no trust line to type.

The boundary is honest about what it is: every session on the machine is the same user's, and a peer message is treated as a teammate's by Claude Code already. The mark tells the crew session which teammate carries the user's instructions for this run.

---

## 7. The ledger

`~/.claude/mission-control/<repo slug>/`, one JSON file per fact so sessions never clobber each other: `run.json` (name, coordinator, base, PR approval, collaboration, crew plan, assumptions, needs, the coordinator's pending list), `sessions/<id>.json` (the row, its watch and its scheduled jobs; a row carried over to a new session id leaves `<old id>.json.adopted` behind), `slots/<resource>.json`, `requests/<resource>__<id>.json`, `decisions.jsonl` (what the user decided, appended, with each session's acknowledgement), `briefs/<task>.md`, `guidance.md`, `log.jsonl`. `mc.py end` moves it under `runs/`. The CLI identifies a caller by `CLAUDE_CODE_SESSION_ID`, which Claude Code sets for every Bash child; the mod passes its own id. Writes that steer the run are the coordinator's or `--by-user`.

`python3 <plugin-root>/scripts/mc.py --help` lists every subcommand; `status --probe` is the board as text. `reconcile` diffs the ledger against the live registry, GitHub and the branches on origin (each merged PR's own base, each open PR's own branch) and prints what drifted (gone or unjoined sessions, merged PRs whose row is not done, needs left open, a task whose roadmap carries no claim at the ref where it ought to; a task the roadmap does not list is named once, with no claim expected; a merged task's worktree still on disk an hour on) and who each PR actually waits on. `retire <task>` reclaims a finished crew worktree while the run goes on: it refuses while the session is live, the row is not done, the PR is open, the tree is dirty, a slot is held, something runs in the tree or an open PR is stacked on the branch, then removes the worktree, prunes, deletes the branch with `-d` only and records it on the row; `--dry-run` prints what would go and the disk it holds. `classify` says whether the project is solo or collaborative (stated as `collaboration` in the config or its gitignored `.local` twin, else inferred from 90 days of authors and the reviews on merged PRs) and the team's hours; `start` records the answer on the run. `watch [--pr N]` is a crew session's PR watcher, run in the background: a five-minute `gh` poll that prints the first change (reviews, decision, comments, checks, state) and exits, held outside the team's hours on a collaborative project unless the PR merged or closed.

---

## 8. Options

| Option | Default | What it does |
|---|---|---|
| `enabled` | true | The one switch. Off, nothing is registered; the command hooks still run |
| `approve_in_slot` | true | Answer a project hook's `ask` with `allow` while this session holds the slot and runs from its worktree |
| `refresh_seconds` | 15 | How often an open board rereads the ledger |

---

## 9. Files

| File | Holds |
|---|---|
| `scripts/mc.py` | The ledger CLI and both command hooks; `python3 -m unittest test_mc` in that directory runs its tests |
| `scripts/worktree-bootstrap.sh` | Symlinks git-ignored `.env*` files and installs every tracked lockfile in a fresh worktree |
| `hooks/register.tsx` | The board, `/mc`, the tools, the prompt section, the message mark, the slot approval; `claude plugin test <plugin-root>` runs `hooks/mc.test.tsx` |
| `types/index.d.ts` | The `$.state` contract |
| `references/protocol.md` | The protocol, with the message shapes |
| `references/config.md` | The project config schema |
| `references/mission-control.example.json` | CHIRPdb's config |
| `templates/brief.md`, `templates/guidance.md` | What kick-off writes per session and per run |
| `skills/` | `kickoff`, `coordinate`, `crew`, `checkin`, `end`, `configure` |

Check it with `claude plugin validate <plugin-root> --strict` and `claude plugin test <plugin-root>`.
