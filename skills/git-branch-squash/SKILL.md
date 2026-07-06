---
name: "Merge: Rebase & Squash from Branch"
description: "{{ 𝛀𝛀𝛀 }} Squash and rebase onto a branch (default main)"
model: opus
disable-model-invocation: true
allowed-tools: ["Bash(git:*)", "Read", "Glob", "Grep", "Edit"]
argument-hint: ["target branch (default main)"]
---

## Squash and Rebase onto Target

$ARGUMENTS (optional) — the branch to rebase onto. Defaults to `main` when omitted.

1. Resolve `$BRANCH`: use `$ARGUMENTS` if provided, otherwise `main`
2. Check current branch name and confirm with user
3. Do NOT create a worktree - work in the current directory
4. Run `git fetch origin $BRANCH`
5. Run `git rebase -i origin/$BRANCH` — in the editor, squash or fixup commits as appropriate, leaving one clean commit (or a small number of logical commits) with a descriptive message
6. If conflicts exist, list them and resolve one at a time preserving our branch's intent, running `git rebase --continue` after each
7. Run tests to verify
8. Push with `git push --force-with-lease`
