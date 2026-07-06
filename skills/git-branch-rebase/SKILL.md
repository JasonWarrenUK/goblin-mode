---
name: "Merge: Rebase from Branch"
description: "{{ 𝛀𝛀𝛀 }} Rebase from a branch (default main)"
model: opus
disable-model-invocation: true
allowed-tools: ["Bash(git:*)", "Read", "Glob", "Grep", "Edit"]
argument-hint: ["target branch (default main)"]
---

## Rebase Current Branch onto Target

$ARGUMENTS (optional) — the branch to rebase onto. Defaults to `main` when omitted.

1. Resolve `$BRANCH`: use `$ARGUMENTS` if provided, otherwise `main`
2. Check current branch name and confirm with user
3. Do NOT create a worktree - work in the current directory
4. Run `git fetch origin $BRANCH && git rebase origin/$BRANCH`
5. If conflicts exist, list them and resolve one at a time preserving our branch's intent, running `git rebase --continue` after each
6. Run tests to verify
7. Push with `git push --force-with-lease`
