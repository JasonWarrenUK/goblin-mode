← [Task trackers](README.md)

# git-native

The fallback source — always available, since it needs no external tool. Used when no tracker is configured or detected: git itself becomes the task source.

## Task state derivation

| Signal | Inferred status |
|---|---|
| Branch exists, has commits, no PR | **In Progress** |
| PR open | **In Review** |
| Branch merged to main | **Done** |
| Branch with no commits in >7 days | **Stale** |

## Task identity

Without issue IDs, derive task identity from:

- Branch name — `feat/add-auth` → task "Add auth"
- First commit message on the branch → task description
- `.claude/session-state.json` → task context carried over from previous sessions

## Orphan detection

- **Stale branches** — no commits in >7 days, no PR
- **Orphaned PRs** — open PRs with no recent activity
- **Dangling work** — uncommitted changes on non-active branches

---
← [Task trackers](README.md) · [Linear](linear.md) · [GitHub Issues](github-issues.md)
