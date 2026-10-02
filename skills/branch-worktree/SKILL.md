---
name: "Branch: Worktree"
description: "Move this session into a new worktree on a given branch (existing, or new from a base), or list and prune worktrees and their leftovers"
when_to_use: "When the user wants this session working on a branch in its own worktree, or wants stale worktrees cleared away. For a read-only map of what worktrees exist, use hud-worktrees."
model: sonnet
effort: medium
metadata:
  glyph: ᛊ
  family: branch
disable-model-invocation: true
allowed-tools: ["Read", "Glob", "EnterWorktree", "ExitWorktree", "Bash(git:*)", "Bash(gh pr list:*)", "Bash(gh pr view:*)", "Bash(du:*)", "Bash(ls:*)", "Bash(~/.claude/library/scripts/checkout-occupied.sh:*)"]
arguments: ["action", "branch", "name"]
argument-hint: "new <existing-branch>|<new-branch>:<base> [worktree name] | prune"
---

# Branch: Worktree

Two jobs: put this session into a worktree on the right branch, and clear away worktrees nobody needs. The map of what exists lives in `hud-worktrees`; this skill is where the changes happen.

**The session moves with `EnterWorktree`, never `cd`.** A `cd` changes only the shell. The session's working directory, CLAUDE.md, memory and plan files stay pointed at the old checkout, so every later edit and commit silently targets the wrong tree. Every move into a worktree in this skill is an `EnterWorktree` call with `path`; every move out is `ExitWorktree`.

---

## Step 0: Parse the arguments

`$action` is required and is `new` or `prune`.

| Call | Meaning |
|---|---|
| `new <existing-branch>` | worktree on a branch that already exists |
| `new <existing-branch> <name>` | the same, with a chosen worktree name |
| `new <new-branch>:<base>` | create `<new-branch>` from `<base>` in a worktree |
| `new <new-branch>:<base> <name>` | the same, with a chosen worktree name |
| `prune` | list worktrees and offer to remove redundant ones |

A branch name never contains `:` (git forbids it in ref names), so one `:` splits the new branch from its base. `<name>` defaults to the part of the branch after its last `/` (`feat/search-bar` gives `search-bar`; a branch with no `/` is used whole).

Hard stop on invalid input: print the one-line reason and the usage block, run nothing.

| Invalid call | Reason to print |
|---|---|
| `prune` followed by anything | `prune takes no arguments` |
| `new` with no branch | `new needs a branch` |
| `new <branch>` where the branch exists nowhere (not local, not on origin) | `<branch> does not exist; to create it give a base: <branch>:<base>` |
| `new <branch>:<base>` where `<branch>` already exists | `<branch> already exists; drop the :<base> to use it` |
| `new <branch>:<base>` where `<base>` exists nowhere | `base <base> does not exist` |
| a `<name>` outside letters, digits, `.`, `_`, `-` or over 64 characters | `worktree names allow letters, digits, . _ - (max 64)` |

```text
Usage: /branch-worktree new <existing-branch>|<new-branch>:<base> [worktree name]
       /branch-worktree prune
```

Existence checks, after `git fetch origin`: `git show-ref --verify --quiet refs/heads/<b>` (local) and `refs/remotes/origin/<b>` (remote).

---

## Action: `new`

1. `git fetch origin`, then run the Step 0 existence checks.
2. **Where the branch already lives.** Read `git worktree list --porcelain`.
   - Checked out in a worktree under `<main checkout>/.claude/worktrees/`: skip creation, go straight to step 6 with that path.
   - Checked out anywhere else (the main checkout, a sibling directory): stop. Git allows one checkout per branch, and `EnterWorktree` can only reach worktrees under `.claude/worktrees/` once the session is in a worktree. Name the path, and offer to switch that checkout to another branch first or to start a new branch from this one.
3. **Choose the path.** `<main checkout>/.claude/worktrees/<name>`, where the main checkout is the parent of `git rev-parse --path-format=absolute --git-common-dir`, so the answer is the same from inside a worktree. If the directory exists already, stop: it either holds a different branch or is a leftover for `prune` to clear.
4. **Check the directory is ignored:** `git check-ignore -q .claude/worktrees/<name>`. When it is not, say so and offer to append `.claude/worktrees/` to `.gitignore` (shared) or `.git/info/exclude` (local only); never edit either without approval.
5. **Show the command and await approval:**
   - Existing local branch: `git worktree add <path> <branch>`
   - Existing only on origin: `git worktree add --track -b <branch> <path> origin/<branch>`
   - New branch: `git worktree add -b <branch> <path> origin/<base>` (the local `<base>` when it has no remote counterpart)
6. **Move the session:** call `EnterWorktree` with `path` set to the absolute worktree path. Then confirm both facts in one line: `pwd` and `git branch --show-current` match what was asked for. If either does not, say so plainly and stop; do not paper over it with a `cd`.
7. **Close with the reminder:** a fresh worktree has no installed dependencies (`node_modules`, a venv) and no generated files, so run the project's install and any codegen before trusting a test run there.

---

## Action: `prune`

1. **Build the map** exactly as `hud-worktrees` does (its "Always start with the map" section): every worktree with path, branch, dirty or clean, ahead and behind (counted against the PR base for a stacked layer), and which one this session is standing in. Add an **In use** column from `~/.claude/library/scripts/checkout-occupied.sh <path>`: exit 1 means another live Claude session is working there.
2. **Find the candidates.** A worktree is redundant when all of these hold:
   - its branch's PR has merged, or (never PR'd) the branch is merged into the default branch
   - its tree is clean
   - no other live session is in it
   - its branch is not the base of an open PR (`gh pr list --base <branch>`); a stack layer is never a candidate while a child is open

   Also list, separately, anything that is not a worktree but looks like debris:
   - registered worktrees whose directory is gone (`prunable` in `git worktree list --porcelain`)
   - directories under `.claude/worktrees/` that git does not list
   - inside each candidate and each stray directory, the heavy leftovers by name and size (`.venv`, `venv`, `node_modules`, `dist`, `build`; `du -sh`)
3. **Show the table** with the candidates and debris marked, then one AskUserQuestion (multi-select) over them. A dirty worktree is never a silent candidate: if the user wants one cleared, show its uncommitted files first and ask again.
4. **Remove, one at a time, in this order:** `git worktree remove <path>`, then offer `git branch -d <branch>`. After the last one, `git worktree prune`, then the fresh map. Stray directories are deleted only after approval, by name.
5. **If this session is standing in a target:** when it entered that worktree through `EnterWorktree` this session, call `ExitWorktree` with `action: "keep"` first and remove it afterwards. In any other case leave it out of the list and say why. Never `cd` out of it.

---

## Red flags

**Never:** `cd` into a worktree to "move" the session; use `git worktree remove --force` or `git branch -D` to get past a refusal (the refusal is information); remove a worktree you are standing in, one another session is using, or one whose branch is the base of an open PR; create a second branch because the intended name was taken (use the existing one, or stop); edit `.gitignore` or `.git/info/exclude` without approval; delete anything under `.claude/worktrees/` that was not shown in the approved list.

<raw-arguments value="$ARGUMENTS" />
