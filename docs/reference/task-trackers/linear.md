← [Task trackers](README.md)

# Linear

Detection: explicit `taskSource: linear` in the project's `CLAUDE.md`, a Linear CLI (`linear` command) present, or Linear issue IDs found in branch names/commit messages.

## Status transitions

| Git event | Linear action |
|---|---|
| Branch checkout matching issue ID/slug | Set issue → **In Progress** |
| PR created referencing issue | Set issue → **In Review** |
| PR merged to main | Set issue → **Done** (with confirmation) |
| Branch deleted after merge | No action (already handled by merge) |

## Issue matching

Match git branches to Linear issues, in priority order:

1. **Explicit issue ID in branch name** — `feat/JAZ-123-add-auth` → `JAZ-123`
2. **Slug match** — `feat/add-user-authentication` → search Linear for issues with matching title keywords
3. **Commit message references** — `fix(auth): resolve login bug JAZ-456` → `JAZ-456`

## Orphan detection

- **Orphaned issues** — Linear issues "In Progress"/"In Review" with no corresponding branch
- **Untracked branches** — branches with no matching Linear issue (suggest creating one)
- **Stale statuses** — issues "In Progress" where the branch hasn't had a commit in >7 days

---
← [Task trackers](README.md) · [GitHub Issues](github-issues.md) · [git-native](git-native.md)
