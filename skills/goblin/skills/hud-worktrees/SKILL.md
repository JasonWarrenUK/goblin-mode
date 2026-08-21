---
name: "HUD: Worktrees"
description: "Map every worktree in this repo in plain language and shepherd safe create/remove actions"
when_to_use: "When the user asks what worktrees exist, seems confused about which checkout they're in, wants to create or remove a worktree, or a worktree-related git error appears; worktrees are easy to get wrong, which is why this skill exists."
model: sonnet
effort: medium
metadata:
  glyph: ᛊ
  family: hud
disable-model-invocation: false # confusion about worktrees is exactly when it should appear; every mutation awaits approval
allowed-tools: ["Bash(git:*)", "Bash(gh pr list:*)", "Bash(gh pr view:*)", "Read", "Glob"]
arguments: ["action", "branch"]
argument-hint: "[new <branch> | clean] (no args = show the map)"
---

# HUD: Worktrees

Worktrees go wrong in predictable ways: removing the one you're standing in, creating a duplicate branch because one already existed, forgetting a worktree exists and wondering why a branch won't delete. This skill's job is to make the current state impossible to misread, and to fence every action with the checks that prevent those mistakes.

## Always start with the map

Regardless of arguments, gather first:

1. `git worktree list --porcelain`: every worktree, its path, branch, HEAD.
2. For each worktree: `git -C <path> status --porcelain` (dirty?) and `git -C <path> rev-list --left-right --count origin/main...HEAD` (ahead/behind, skip if no upstream). When the branch has an open PR whose base isn't main (`gh pr view <branch> --json baseRefName,number`), it's a stacked layer: count against `origin/<baseRefName>` instead and say so in the sentence; counting a stacked child against main folds the parent's commits into its ahead-count and misreads the layer.
3. `pwd`: establish **which worktree you are standing in right now**. This drives every safety check below.

Render as a table plus one plain-English sentence per worktree: what it is, what state it's in, whether it's safe to touch:

```markdown
| Worktree | Branch | State | You are here |
|---|---|---|---|
| ~/code/app (main checkout) | main | clean, up to date | |
| ~/code/app-worktrees/feat/search | feat/search | 2 uncommitted files, 3 ahead | ◀ |
```

Group the table in two sections, both always shown: **deliberate worktrees** (the main checkout plus paths following the project's worktree convention, e.g. the sibling `../<repo>-worktrees/<branch>` layout) first, then **machine-made worktrees** (session- or tool-created: paths under temp directories or `.claude`, or generated names following no human convention). When provenance is unclear, treat it as deliberate.

Then a **Suggestions** line naming anything that deserves attention: a worktree whose branch's PR has merged (or, un-PR'd, is merged to main; candidate for cleanup), a dirty worktree untouched for weeks, a branch checked out in a worktree that someone might try to check out elsewhere. An abandoned machine-made worktree (clean, branch merged or never pushed) is a first-class cleanup candidate here. When several worktrees form a stack (each branch the PR base of the next), say so plainly: "these three are one stack, bottom to top", since removing or rebasing them out of order is the trap.

With no arguments, stop here; the map is the deliverable.

## Action: `new <branch>`

1. Check whether `<branch>` already exists (`git branch --list <branch>`, `git worktree list`). If it exists **use it**; never create `feat/search-2` because `feat/search` was taken. If it's already checked out in another worktree, point there instead of creating anything.
2. Follow the project's existing worktree path convention if the map shows one; otherwise default to a sibling directory: `../<repo>-worktrees/<branch>`.
3. Show the exact command (`git worktree add <path> <branch>` or `-b <branch>` for a new branch), **await approval**, run it.
4. Remind: a fresh worktree has no `node_modules`, so run the project's install (and any codegen like `svelte-kit sync`) before trusting test output there.

## Action: `clean`

1. From the map, list removal candidates: worktrees whose branch's PR has merged (or whose branch is merged into main, for branches that never had a PR) and whose tree is clean. A branch that is the PR base of an open child is **never** a candidate, whatever its own state. A dirty worktree is **never** a silent candidate; show what's uncommitted and ask.
2. **Never remove the worktree you are standing in.** If the target is the current directory, first give the user the `cd` back to the main checkout, and only proceed after they've moved.
3. For each approved removal, in order: `git worktree remove <path>`, then offer `git branch -d <branch>` (only `-d`, never `-D`; if git refuses, the branch isn't merged and that's worth knowing, not overriding).
4. Finish with `git worktree prune` and a fresh map so the user sees the end state.

## Red flags

**Never:** remove a worktree while inside it; use `git worktree remove --force` or `git branch -D` to silence a refusal (the refusal is information); create a new branch when one with the intended name already exists; leave the user in a deleted directory; always land them back in the main checkout.

<raw-arguments value="$ARGUMENTS" />
