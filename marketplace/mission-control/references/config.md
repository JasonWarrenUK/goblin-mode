# The project config: `.claude/mission-control.json`

One file per repository, committed, found by walking up from the session's directory and then from the main checkout (so a worktree created before the file was committed still finds it). `mission-control.example.json` beside this file is CHIRPdb's, the first project configured.

| Key | Holds |
|---|---|
| `version` | `1` |
| `project` | A display name |
| `worktrees.dir` | Where kick-off creates worktrees, relative to the main checkout (`.claude/worktrees`) |
| `worktrees.bootstrap` | Prose: what a fresh worktree needs before a task runs. The plugin's `scripts/worktree-bootstrap.sh` symlinks git-ignored `.env*` files and installs every tracked lockfile; name anything beyond that here |
| `resources.<name>` | One shared resource; see below |
| `commands.test`, `.lint`, `.contract`, `.schema`, ... | The commands the end-of-run checks and the briefs quote, as typed from the repository root |
| `commands.stack_status` | A command printing the open PRs with their stack verdicts, for the board and the end skill |
| `conventions` | Files kick-off reads and distils into the shared guidance; every crew brief points at them |
| `facts` | Conventions that are not written in the repository, in the user's words, so the coordinator never has to assert one from memory. Kick-off asks before adding to this list |
| `human_gates` | What stays with the user, in words every brief repeats |
| `migrations.dir`, `migrations.timestamp_format` | Where kick-off assigns one timestamp per task that needs a migration |

## A resource

| Key | Holds |
|---|---|
| `label` | How the board and the refusal name it |
| `gate` | Globs over a simple command's words, anchored at the start, after `poetry run ` is dropped: `poe db-reset-local*`, `supabase db reset*`, `poe *-hosted*`. A line with several commands is checked command by command; heredoc bodies and quoted strings are not commands |
| `probe.ports` | TCP ports that must be free (`lsof`) |
| `probe.pgrep` | A process pattern that must match nothing (`pgrep -fl`) |
| `probe.pg_activity` | `{ dsn, database, ignore_users, ignore_idle_users }`: client connections on the database beyond the stack's own services (`psql`) |
| `probe.migrations` | `{ dsn, table }`: the latest migration the stack holds, shown with every probe so the holder knows what a reset will drop |
| `approve_in_slot` | `true`: while a session holds the slot and runs the command from its own worktree, the mod answers a project hook's `ask` with `allow`. A `deny` is never loosened |
| `human_gate` | `true`: never granted by the ledger; the hook adds context instead of a verdict, and the request path is `mc_need` with the exact command for the user |
| `run_from` | The directory under the worktree the gated commands run from; the needs list prefixes commands with it |
| `reset` | The command that resets the resource, for the needs list and the briefs |
| `notes` | Prose every brief carries about this resource |

## What the hooks do with it

- `PreToolUse` on Bash (`mc.py hook pre-tool-use`): no run, nothing. A gated command without the slot: `deny`, naming the holder and the request path, and the attempt is recorded as a request. The holder, outside its worktree: `deny`. The holder, inside: context only. A human gate: context only. `--by-user` on a command line: `deny`.
- `SessionStart` (`mc.py hook session-start`): a session starting inside a planned worktree is told its task, the coordinator's name and socket, where its brief is and which skill to invoke. The coordinator session is told it coordinates.
- The mod's `tool.check` on Bash: only loosens `ask` to `allow`, only when `mc.py check` says every gated resource the line touches is held by this session, runs in its worktree and is `approve_in_slot`.
