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
| `push_gate` | Opt-in push gate: a list of keys of `commands` (`["test", "typecheck", "lint"]`), or `{"commands": [...], "exempt": [globs]}`. `mc.py gate` runs them in order from the checkout root against the committed HEAD (it refuses over uncommitted tracked changes and over untracked files that are not ignored, unless given `--allow-untracked`), stops at the first failure and writes a record under the git common dir. The PreToolUse hook then refuses a `git push` unless HEAD has a green record and none is running; dry runs, bare tag pushes and deletions pass; a push naming a refspec is checked against that ref's commit rather than HEAD. Glob refspecs, `--all`, `--branches`, `--mirror` and `push.default=matching` name no single tip, so only HEAD's record is read and the other tips they send go unchecked. `exempt` globs (`["*.md", "docs/*"]`) let a push through when everything it adds beyond the upstream (else origin's HEAD) matches and the push goes to that same remote and branch (a bare name is its own destination, and a bare push goes to a configured `pushRemote` or `remote.pushDefault`), for docs straight to the trunk. A green record counts only when it ran every key `push_gate` lists now, so adding a key sends the next push back through the gate. The gate applies in any session of the repo, run or no run. A key missing from `commands` refuses the push until the config is fixed. Like the rest of the guard it stops accidents; a hand-written record gets past it |
| `claims` | `"trunk-sync"` when the project's roadmap or Jira sync writes claims to the trunk: kick-off then makes no claim commit on a branch (a branch claim conflicted twice with the sync in November 2026) and reconcile does not flag an open PR for a missing claim. Absent or `"branch"`: the default, claim on the branch |
| `conventions` | Files kick-off reads and distils into the shared guidance; every crew brief points at them |
| `facts` | Conventions that are not written in the repository, in the user's words, so the coordinator never has to assert one from memory. Kick-off asks before adding to this list |
| `human_gates` | What stays with the user, in words every brief repeats |
| `migrations.dir`, `migrations.timestamp_format` | Where kick-off assigns one timestamp per task that needs a migration |

## A resource

| Key | Holds |
|---|---|
| `label` | How the board and the refusal name it: a noun phrase without a leading article (`local Supabase stack`), since the messages supply `the` |
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

- `PreToolUse` on Bash (`mc.py hook pre-tool-use`): no run, nothing. A gated command without the slot: `deny`, naming the holder and the request path, and the attempt is recorded as a request. The holder, outside its worktree: `deny`. The holder, inside: context only. A human gate: context only. `--by-user`, `--session` or `CLAUDE_CODE_SESSION_ID=` on an `mc.py` command line: `deny`. A gated command inside `sh -c` is read like a bare one.
- `SessionStart` (`mc.py hook session-start`): a session starting inside a planned worktree is told its task, the coordinator's name and socket, where its brief is and which skill to invoke. The coordinator session is told it coordinates.
- `PreCompact` (`mc.py hook pre-compact`): a session in a run tells the compaction summary what only its conversation holds; the coordinator and a crew session each get their own wording. A session outside the run prints nothing.
- The mod's `tool.check` on Bash: only loosens `ask` to `allow`, only when `mc.py check` says every gated resource the line touches is held by this session, runs in its worktree and is `approve_in_slot`.
