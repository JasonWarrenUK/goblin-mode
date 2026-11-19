---
name: "Inspect Chambers"
description: "Map every chamber (worktree) in this repo in plain language: where each one is, what state it is in and whether it is safe to touch"
when_to_use: "When the user asks what worktrees exist, seems confused about which checkout they're in or a worktree-related git error appears; chambers are easy to get wrong, which is why this skill exists. Creating or removing one is branch-worktree's job."
model: sonnet
effort: medium
metadata:
  glyph: ᛊ
  family: hud
  goblin-spinner: inspecting the chambers|counting the doors|checking the locks
disable-model-invocation: false # confusion about worktrees is exactly when it should appear; read-only, so no gate is needed
allowed-tools: ["Bash(git worktree list:*)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/worktree-state.sh *)", "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/stack-status.py *)", "Bash(gh pr list:*)", "Bash(gh pr view:*)", "Read", "Glob"]
argument-hint: "(no arguments: shows the map)"
---

# Inspect Chambers

The seneschal calls worktrees chambers: every checkout of the house. They go wrong in predictable ways: removing the one you're standing in, creating a duplicate branch because one already existed, forgetting a chamber exists and wondering why a branch won't delete. This skill's job is to make the current state impossible to misread. It changes nothing: creating a worktree, moving the session into one and removing them all live in `branch-worktree`.

## Always start with the map

Gather first:

1. `git worktree list --porcelain`: every chamber, its path, branch, HEAD.
2. For each chamber: `${CLAUDE_PLUGIN_ROOT}/scripts/worktree-state.sh <path> origin/main`, which prints `dirty` (changed and untracked files), `ahead` and `behind` as JSON; it exits 2 when the base does not resolve, so use `${CLAUDE_PLUGIN_ROOT}/scripts/worktree-state.sh <path>` (its upstream, or null counts when it has none) for a branch with no remote base. It needs `zsh` and `jq`; if it reports `jq not installed`, or the shell reports no `zsh` interpreter, say which is missing and stop. Never call `git -C` directly: a permission rule loose enough for any path also lets `-c` options through.
3. Once, for every open PR: `${CLAUDE_PLUGIN_ROOT}/scripts/stack-status.py --open`. A chamber whose branch's row is `linked` or `chained-unlinked` holds a layer: count it against `origin/<base>` instead of main and say so in the sentence (counting a child against main folds the parent's commits into its ahead-count), and carry the stack number and layer position into the table. `chained-unlinked` is its own finding: the bases form a chain GitHub does not hold as a stack, and `/branch-stack link` is the fix.
4. `pwd`: establish **which chamber you are standing in right now**. This drives every safety check below.

Render as a table plus one plain-English sentence per chamber: what it is, what state it's in, whether it's safe to touch:

```markdown
| Chamber | Branch | State | You are here |
|---|---|---|---|
| ~/code/app (main checkout) | main | clean, up to date | |
| ~/code/app-worktrees/feat/search | feat/search | 2 uncommitted files, 3 ahead | ◀ |
```

Group the table in two sections, both always shown: **deliberate chambers** (the main checkout plus paths following the project's worktree convention, e.g. the sibling `../<repo>-worktrees/<branch>` layout) first, then **machine-made chambers** (session- or tool-created: paths under temp directories or `.claude`, or generated names following no human convention). When provenance is unclear, treat it as deliberate.

Then a **Suggestions** line naming anything that deserves attention: a chamber whose branch's PR has merged (or, un-PR'd, is merged to main; candidate for cleanup), a dirty chamber untouched for weeks, a branch checked out in a chamber that someone might try to check out elsewhere. An abandoned machine-made chamber (clean, branch merged or never pushed) is a first-class cleanup candidate here. When several chambers hold layers of one stack, say so plainly: "these three are layers of stack #191, bottom to top, in three chambers", and that a stack wants one chamber (`gh stack up`/`down` move between layers; a layer checked out elsewhere breaks `gh stack sync`): the spare chambers are cleanup candidates once their branches are back in the stack's own chamber.

Stop here; the map is the output. When the Suggestions line names something to act on, point at the skill that does it: `/branch-worktree new <branch>` to work on a branch in a new chamber, `/branch-worktree use <chamber>` to move into a chamber that exists and `/branch-worktree prune` to clear redundant ones. Those commands are in goblin-mode's own config; on a machine without them, name the git command instead (`git worktree add`, `git worktree remove`, `git worktree prune`) and leave running it to the user.

## Red flags

**Never:** run a command that changes a worktree or a branch from here (no `git worktree add|remove|prune`, no `git branch -d|-D`); tell the user a chamber is safe to remove without having read its dirty state and its PR.
