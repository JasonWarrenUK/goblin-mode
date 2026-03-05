---
description: "{{ 𝛀𝛀𝛀 }} Rebase from branch"
model: opus
---

## Rebase Current Branch onto Branch

Arguments: $BRANCH (required) — the branch to rebase onto

1. Check current branch name and confirm with user
2. Do NOT create a worktree - work in the current directory
3. Run `git fetch origin $BRANCH && git rebase origin/$BRANCH`
4. If conflicts exist, list them and resolve one at a time preserving our branch's intent, running `git rebase --continue` after each
5. Run tests to verify
6. Push with `git push --force-with-lease`
