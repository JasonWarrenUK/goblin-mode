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

## 2. A run, start to finish

| Moment | Who | What |
|---|---|---|
| Once per project | the user | `/mission-control:configure` writes `.claude/mission-control.json`: the shared resources, the commands that touch them, how to tell each one is busy, the check commands, the convention files and the conventions that live only in the user's head |
| Kick-off | the coordinator session | `/mission-control:kickoff 10SE.2 10SE.4 name search` picks the tasks (from the roadmap when there is one), creates a worktree per task, starts the run in the ledger, asks every convention it cannot read, sets numbered shared assumptions, writes the guidance and one brief per session, and prints a launch line per session |
| Launch | the user | runs each launch line in a terminal. Nothing is typed into the session: the `SessionStart` hook names its brief and the coordinator, the mod puts it on the board |
| The run | crew and coordinator | crew answer the five questions, report state changes, request slots and put anything only the user can do on the needs list; the coordinator grants slots from the machine's state, settles assumptions, reviews draft PRs when the run says so, checks in and keeps the board true |
| Whenever | the user | `/mc` in the coordinator session (or any session) shows the board; the needs list has complete commands with their directories |
| End | the coordinator session | `/mission-control:end` links the stack, prunes closed sessions' worktrees, runs the checks on the top layer, offers the roadmap follow-ups and archives the ledger |

The protocol itself, with the message shapes: `references/protocol.md`.

---

## 3. `/mc`: the board

Opens a pane with the run, or closes it. In a fullscreen terminal of 110 columns or more it docks beside the transcript; narrower, it sits above the prompt. It runs with no turn, so it works while Claude is busy. While open it refreshes itself every `refresh_seconds`.

| Section | Shows |
|---|---|
| Header | run name as the title with your role beside it, a rule, then in dim text the start time, base commit, who coordinates, how many assumptions, how many sessions are live and the ledger's age |
| Crew | one row per session: live and busy or idle (from Claude Code's own session registry), task, branch, worktree name, state (`gone` and dimmed once the session has left), PR, last summary and the age of the last report (`2m ago`) |
| Slots | each held resource with its holder, window and purpose; overdue in red; what the machine says about it; the free resources |
| Requests | pending slot requests, with what will run and for how long |
| Needs Jason | numbered, each with the complete command (`cd <dir> && ...`) |

| Key | Does |
|---|---|
| `1` to `9` | picks a session row (shows its full summary) |
| `q` to `p` | picks a request |
| `g` | grants the picked request: asks the minutes, then grants as you and messages the grantee |
| `d` | marks the picked need done |
| `x` | releases a slot (asks which) |
| `r` | refreshes, probing the machine |
| Esc, or `/mc` | closes |

`/mc` with arguments is your hand on the ledger from any session, no turn, no model: `/mc start <name>`, `/mc grant <resource> <task|branch|name> [minutes]`, `/mc release <resource>`, `/mc done <n>`, `/mc status`, `/mc end [force]`. Every write it makes carries `--by-user`, which the hook refuses on any command a model runs.

---

## 4. The tools

Registered in every session where the plugin is on; the CLI refuses the coordinator-only ones from anywhere else.

| Tool | Who | Does |
|---|---|---|
| `mc_report` | crew | state (`briefing`, `working`, `in-slot`, `pr-ready`, `blocked`, `waiting-jason`, `done`), one-line summary, PR number |
| `mc_slot` | crew | `request` records the request and messages the coordinator with what will run and for how long; `release` records the results and tells the coordinator |
| `mc_need` | anyone | an item only the user can do: why, the exact command, the directory. Goes on the board and to the coordinator |
| `mc_send` | anyone | a line to a session by task id, branch, session name, `coordinator` or `all`; addresses by session id, so a changed name or ref does not lose it |
| `mc_grant` | coordinator | probes the machine, refuses while busy, grants, messages the grantee, notices the others |
| `mc_revoke` | coordinator | releases another session's slot and tells it |
| `mc_assume` | coordinator | sets or changes a numbered shared assumption and broadcasts it; every crew prompt carries the list |
| `mc_board` | coordinator | the board as text, probes included |

---

## 5. The hooks and the slot

Three things enforce the slot; none asks a session to do what its own permissions refuse.

- **`PreToolUse` on Bash** (`scripts/mc.py hook pre-tool-use`): during a run, a command matching a resource's `gate` is refused unless this session holds the slot and runs it from its own worktree. The refusal says who holds it and how to ask, and the attempt appears on the board as a request. A `human_gate` resource gets context instead of a verdict. `--by-user` on a model's command line is refused.
- **The mod's `tool.check` on Bash**: when the project's own hook answers `ask` on a gated command (CHIRPdb's `db-reset-local-anyway`, say), and this session holds the slot, runs from its worktree and the resource is `approve_in_slot`, the mod answers `allow`. A `deny` is never loosened. Off with the `approve_in_slot` option.
- **`SessionStart`** (`scripts/mc.py hook session-start`): a session starting inside a planned worktree is told its task, the coordinator's name and socket, where its brief is and to invoke `/mission-control:crew`.

Hosted reads, credentials, writes, merges and anything irreversible stay with the user: the config marks them `human_gate`, no slot covers them, and the path is the needs list with the exact command.

---

## 6. Trust between sessions

The user starts the run in the coordinator session; the ledger records that session's id and messaging socket. Every crew session's system prompt gains a section naming the run, the coordinator's session and socket, the shared assumptions and the human gates. A cross-session message carries its sender's socket in the harness's `from` attribute; the receiving mod marks a message from the coordinator's socket as verified against the ledger and one that claims to be mission control from any other socket as not. No passphrase, nothing saved to memory, no trust line to type.

The boundary is honest about what it is: every session on the machine is the same user's, and a peer message is treated as a teammate's by Claude Code already. The mark tells the crew session which teammate carries the user's instructions for this run.

---

## 7. The ledger

`~/.claude/mission-control/<repo slug>/`, one JSON file per fact so sessions never clobber each other: `run.json` (name, coordinator, base, PR approval, crew plan, assumptions, needs), `sessions/<id>.json`, `slots/<resource>.json`, `requests/<resource>__<id>.json`, `briefs/<task>.md`, `guidance.md`, `log.jsonl`. `mc.py end` moves it under `runs/`. The CLI identifies a caller by `CLAUDE_CODE_SESSION_ID`, which Claude Code sets for every Bash child; the mod passes its own id. Writes that steer the run are the coordinator's or `--by-user`.

`python3 <plugin-root>/scripts/mc.py --help` lists every subcommand; `status --probe` is the board as text.

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
