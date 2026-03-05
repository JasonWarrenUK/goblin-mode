---
description: "{{ 𝛀𝛀𝛀 }} Merge from branch"
model: opus
---

## Merge Branch into Current Branch

Arguments: $BRANCH (required) — the branch to merge from

1. Check current branch name and confirm with user
2. Do NOT create a worktree - work in the current directory
3. Run `git fetch origin $BRANCH && git merge origin/$BRANCH`
4. If conflicts exist, list them and resolve preserving our branch's intent
5. Run tests to verify
6. Push with `git push`
