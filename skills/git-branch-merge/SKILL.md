---
name: "Merge: Fast-Forward from Branch"
description: "{{ 𝛀𝛀𝛀 }} Merge from a branch (default main)"
model: opus
disable-model-invocation: true
allowed-tools: ["Bash(git:*)", "Read", "Glob", "Grep", "Edit"]
argument-hint: ["target branch (default main)"]
---

## Merge Branch into Current Branch

$ARGUMENTS (optional) — the branch to merge from. Defaults to `main` when omitted.

1. Resolve `$BRANCH`: use `$ARGUMENTS` if provided, otherwise `main`
2. Check current branch name and confirm with user
3. Do NOT create a worktree - work in the current directory
4. Run `git fetch origin $BRANCH && git merge origin/$BRANCH`
5. If conflicts exist, list them and resolve preserving our branch's intent
6. Run tests to verify
7. Push with `git push`
