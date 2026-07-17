← [Task trackers](README.md)

# GitHub Issues

Detection: explicit `taskSource: github` in the project's `CLAUDE.md`, or a GitHub remote with open issues (`gh repo view`, `gh issue list --assignee @me`).

## Status transitions

| Git event | GitHub action |
|---|---|
| Branch checkout matching issue number | Add "in progress" label (if label exists) |
| PR created with `closes #N` or `fixes #N` | Issue auto-linked by GitHub |
| PR merged | Issue auto-closed by GitHub (if linked) |
| Branch with no linked issue | Suggest creating one via `gh issue create` |

## Issue matching

Match git branches to GitHub issues, in priority order:

1. **Explicit issue number in branch name** — `feat/42-add-auth` → `#42`
2. **PR references** — check open PRs for `closes #N` / `fixes #N` links
3. **Commit message references** — `fix(auth): resolve login bug #42` → `#42`

## Orphan detection

- **Orphaned issues** — issues labelled "in progress" with no corresponding branch or PR
- **Untracked branches** — branches with no linked issue
- **Stale issues** — issues with "in progress" label where the linked branch hasn't had a commit in >7 days

---
← [Task trackers](README.md) · [Linear](linear.md) · [git-native](git-native.md)
