# The project config: `.claude/goblin-warband.json`

One file per repository, committed, found by walking up from the session's directory and then from the main checkout (so a worktree created before the file was committed still finds it). `goblin-warband.example.json` beside this file is CHIRPdb's, the first project configured.

| Key | Holds |
|---|---|
| `version` | `1` |
| `project` | A display name |
| `worktrees.dir` | Where kick-off creates worktrees, relative to the main checkout (`.claude/worktrees`) |
| `worktrees.bootstrap` | Prose: what a fresh worktree needs before a task runs. The plugin's `scripts/worktree-bootstrap.sh` symlinks git-ignored `.env*` files and installs every tracked lockfile; name anything beyond that here |
| `resources.<name>` | One shared resource; see below |
| `commands.test`, `.lint`, `.contract`, `.schema`, ... | The commands the end-of-raid checks and the orders quote, as typed from the repository root |
| `commands.stack_status` | A command printing the open PRs with their stack verdicts, for the slate and the declare-victory skill |
| `push_gate` | Opt-in push gate: a list of keys of `commands` (`["test", "typecheck", "lint"]`), or `{"commands": [...], "exempt": [globs]}`. `warband.py gate` runs them in order from the checkout root against the committed HEAD (it refuses over uncommitted tracked changes and over untracked files that are not ignored, unless given `--allow-untracked`), stops at the first failure and writes a record under the git common dir. The PreToolUse hook then refuses a `git push` unless HEAD has a green record and none is running; dry runs, bare tag pushes and deletions pass; a push naming a refspec is checked against that ref's commit rather than HEAD. Glob refspecs, `--all`, `--branches`, `--mirror` and `push.default=matching` name no single tip, so only HEAD's record is read and the other tips they send go unchecked. `exempt` globs (`["*.md", "docs/*"]`) let a push through when everything it adds beyond the upstream (else origin's HEAD) matches and the push goes to that same remote and branch (a bare name is its own destination, and a bare push goes to a configured `pushRemote` or `remote.pushDefault`), for docs straight to the trunk. A green record counts only when it ran every key `push_gate` lists now, so adding a key sends the next push back through the gate. The gate applies in any session of the repo, raid or no raid. A key missing from `commands` refuses the push until the config is fixed. Like the rest of the guard it stops accidents; a hand-written record gets past it |
| `claims` | `"trunk-sync"` when the project's roadbook or Jira sync writes claims to the trunk: kick-off then makes no claim commit on a branch (a branch claim conflicted twice with the sync in November 2026) and reconcile does not flag an open PR for a missing claim. Absent or `"branch"`: the default, claim on the branch |
| `conventions` | Files kick-off reads and distils into the shared guidance; every raider's orders point at them |
| `facts` | Conventions that are not written in the repository, in the user's words, so the chief never has to assert one from memory. Kick-off asks before adding to this list |
| `human_gates` | The taboos: what stays with the user, in words every raider's orders repeat |
| `migrations.dir`, `migrations.timestamp_format` | Where kick-off assigns one timestamp per task that needs a migration |

## A resource

| Key | Holds |
|---|---|
| `label` | How the slate and the refusal name it: a noun phrase without a leading article (`local Supabase stack`), since the messages supply `the` |
| `gate` | Globs over a simple command's words, anchored at the start, after `poetry run ` is dropped: `poe db-reset-local*`, `supabase db reset*`, `poe *-hosted*`. A line with several commands is checked command by command; heredoc bodies and quoted strings are not commands |
| `probe.ports` | TCP ports that must be free (`lsof`) |
| `probe.pgrep` | A process pattern that must match nothing (`pgrep -fl`) |
| `probe.pg_activity` | `{ dsn, database, ignore_users, ignore_idle_users }`: client connections on the database beyond the stack's own services (`psql`) |
| `probe.migrations` | `{ dsn, table }`: the latest migration the stack holds, shown with every probe so the holder knows what a reset will drop |
| `approve_in_slot` | `true`: while a session holds the dibs and runs the command from its own worktree, the mod answers a project hook's `ask` with `allow`. A `deny` is never loosened |
| `human_gate` | `true`, a taboo: never granted by the ledger; the hook adds context instead of a verdict, and the request path is `warband_tribute` with the exact command for the user |
| `run_from` | The directory under the worktree the gated commands run from; the tribute list prefixes commands with it |
| `reset` | The command that resets the resource, for the tribute list and the orders |
| `notes` | Prose every raider's orders carry about this resource |

## What the hooks do with it

- `PreToolUse` on Bash (`warband.py hook pre-tool-use`): no raid, nothing. A gated command without the dibs: `deny`, naming the holder and the request path, and the attempt is recorded as a request. The holder, outside its worktree: `deny`. The holder, inside: context only. A taboo: context only. `--by-user`, `--session` or `CLAUDE_CODE_SESSION_ID=` on a `warband.py` command line: `deny`. A gated command inside `sh -c` is read like a bare one.
- `SessionStart` (`warband.py hook session-start`): a session starting inside a planned worktree is told its task, the chief's name and socket, where its orders are and which skill to invoke. The chief's session is told it leads.
- `PreCompact` (`warband.py hook pre-compact`): prints instructions for the compaction summary. The chief is told to keep what only its conversation holds and to leave slate state to the ledger. A raider, found by its row or by the planned worktree it runs in, is told to keep its orders, branch, PR, dibs, scheduled work and unanswered questions. Any other session prints nothing.
- The mod's `tool.check` on Bash: only loosens `ask` to `allow`, only when `warband.py check` says every gated resource the line touches is held by this session, runs in its worktree and is `approve_in_slot`.
