← [Wiki home](../README.md)

# Hooks

Hooks are scripts Claude Code runs automatically on lifecycle and tool events. This repo uses them for two different jobs: **global hooks** (`hooks/`) run in every session regardless of project, and **project-level hooks** (`.claude/hooks/`) run only when this repo itself is the active project — mostly relevant when working on this config from a remote (web) session.

> [!NOTE]
> There's also `hooks/pre-commit` — a plain **git hook**, not a Claude Code hook. It's a repo-scoped dispatcher installed via a global `core.hooksPath` override, shared across every repo on this machine. It delegates to a project's own `scripts/pre-commit` if one exists. Unrelated machinery, same directory, easy to confuse — see [below](#the-pre-commit-git-hook).

## Global hooks (`hooks/`)

Wired in [`settings.json`](configuration.md):

| Hook | Event | What it does |
|---|---|---|
| `session-start-worktree.sh` | `SessionStart` | Detects if the session is running inside a git worktree (not the main working tree) and injects a warning that `node_modules` won't exist there — npm/bun/test commands need to run from the main repo root instead. |
| `settings-sync.sh` | `SessionStart` | Strips `//` comments and trailing commas from `settings.local.jsonc`, writes the result to `settings.local.json`. This is what makes the JSONC-source-of-truth pattern work: edit the `.jsonc`, never the `.json` directly — it's regenerated every session start. Warns (to stderr) if `.json` has keys the `.jsonc` doesn't, so a stale key never gets silently dropped without notice. |
| `stop-uncommitted-check.sh` | `Stop` | When Claude finishes responding, checks `git status --porcelain` in the current directory. If the tree isn't clean, prints a one-line summary (staged/unstaged/untracked counts) nudging a commit. Silent when clean. |

`settings.json` also wires two hooks that aren't files in `hooks/` — they shell out directly to `ccstatusline`:

| Hook | Event | What it does |
|---|---|---|
| `bunx -y ccstatusline@latest --hook` | `PreToolUse` (matcher: `Skill`) | Updates the status line when a skill is about to run. |
| `bunx -y ccstatusline@latest --hook` | `UserPromptSubmit` | Updates the status line on every prompt submit. |

## Project-level hooks (`.claude/hooks/`)

Only active when this `~/.claude` directory is itself opened as a project (e.g. working on this config remotely). Both are `SessionStart` hooks that branch on `CLAUDE_CODE_REMOTE`, so exactly one runs per session:

| Hook | Runs when | What it does |
|---|---|---|
| `session-start.sh` | `CLAUDE_CODE_REMOTE=true` (web sessions) | Detects project identity, package manager, framework, test runner, linter, database, ORM, API style, and monorepo tooling by probing for config files and lockfiles. Captures git branch/type/ahead-count/recent-commits. Installs dependencies if `node_modules` is missing. Exports everything as env vars for the session. |
| `session-start-local.sh` | local terminal sessions | Detects git worktree state, stale branches (>20 commits behind default), and in-progress rebase/merge/cherry-pick. Checks for `zed`, `bun`, `gh` on PATH and reports which are missing. |

## The `pre-commit` git hook

`hooks/pre-commit` is a POSIX shell dispatcher, not a Claude Code hook — it's what `git commit` itself runs, installed machine-wide via a global `core.hooksPath`. It looks for a `scripts/pre-commit` in whichever repo you're committing to and delegates to it; repos without that convention are unaffected. Reinstalled by each repo's own `bun run prepare`.

## Adding a hook

1. Decide global (`hooks/`) or project-level (`.claude/hooks/`).
2. Write the script; keep it fast and silent on the happy path — hooks that chatter on every session get ignored.
3. Wire it in the relevant `settings.json` under `hooks.<Event>`, following the existing array-of-arrays shape.
4. If it's meant to run only in one session type, branch on `CLAUDE_CODE_REMOTE` like the two project-level hooks do.

---
← [Wiki home](../README.md) · [Skills](skills.md) · [Agents](agents.md) · [Configuration](configuration.md)
