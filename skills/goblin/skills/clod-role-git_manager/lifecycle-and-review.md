# Branch Lifecycle, Pull Requests, Merge Strategies, Conflict Resolution

Detail for `git-manager`.

## Branch Lifecycle

### Creating Branches

**From main/master**:
```bash
# Update main first
git checkout main
git pull origin main

# Create and checkout new branch
git checkout -b feat/add-user-dashboard

# Or in one command
git checkout -b feat/add-user-dashboard origin/main
```

**Branch from another branch (stacked work)**:
```bash
# When feature depends on another feature whose PR is still open
git checkout feat/base-feature
git checkout -b feat/add-dependent-feature
```

The dependent branch then opens as a **stacked PR**: base set to
`feat/base-feature`, not main, so each PR shows only its own layer's diff and
GitHub retargets the child automatically when the parent merges. Full
mechanics, the `gh stack` CLI and the caveats live in
`~/.claude/library/references/stacked-prs.md`; the short version:

```bash
gh stack init feat/base-feature          # or start the stack before branching
gh stack add feat/add-dependent-feature  # new branch as the next layer
gh stack submit                          # one PR per layer, correct bases

# after fixing something on the base layer
gh stack rebase --upstack && gh stack push
```

Keep stacks to 3 layers or fewer, and never rename or delete a branch that is
the base of an open PR outside `gh stack modify`.

### Keeping Branches Updated

**Rebase on main** (preferred for clean history):
```bash
# Update main
git checkout main
git pull origin main

# Rebase feature branch
git checkout feat/add-user-dashboard
git rebase main

# If conflicts, resolve and continue
git add .
git rebase --continue

# Force push (rewrites history)
git push --force-with-lease origin feat/add-user-dashboard
```

**Merge main** (preserves branch history):
```bash
git checkout feat/add-user-dashboard
git merge main

# Resolve conflicts if any
git add .
git commit
git push origin feat/add-user-dashboard
```

**When to rebase vs merge**:
- **Rebase**: Feature branches, personal branches, clean history desired
- **Merge**: Shared branches, preserving collaboration history, release branches

### Cleaning Up Branches

**Delete local branch**:
```bash
# After merge
git branch -d feat/add-user-dashboard

# Force delete (if not merged)
git branch -D experiment/test-failed-approach
```

**Delete remote branch**:
```bash
git push origin --delete feat/add-user-dashboard
```

**Prune deleted remote branches**:
```bash
git fetch --prune
```

## Pull Request Best Practices

### Before Creating PR

**Checklist**:
- [ ] All tests passing
- [ ] Code follows style guide
- [ ] No console.logs or debugging code
- [ ] Branch rebased on latest main
- [ ] Commit messages follow convention
- [ ] Self-review completed

### PR Title and Description

**Title format**:
- Title case
- Brief and descriptive
- Understandable to non-devs: no jargon, ticket numbers, or type prefixes

**Examples**:
```
Add User Authentication System
Fix Login Button Crash on Mobile
Refactor Database Connection Logic
Update API Documentation
```

**Description template**:
```markdown
## What
Brief description of what this PR does.

## Why
Why this change is needed.

## How
High-level explanation of approach.

## Testing
How to test these changes.

## Screenshots (if applicable)
Visual changes shown here.

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Reviewed own code
```

### PR Size Guidelines

**Ideal PR size**: 200-400 lines changed

**Too large** (>500 lines):
- Hard to review
- Increases merge conflicts
- Higher bug risk
- Consider splitting

**Split large PRs**:
```
Instead of:
- feat/implement-complete-dashboard (1500 lines)

Split into a stack (each layer builds on the one below):
- feat/add-dashboard-layout (300 lines)        → base: main
- feat/add-dashboard-charts (250 lines)        → base: feat/add-dashboard-layout
- feat/add-dashboard-filters (200 lines)       → base: feat/add-dashboard-charts
- test/add-dashboard-integration (150 lines)   → base: feat/add-dashboard-filters
```

When the pieces are genuinely independent (no layer needs another's code),
prefer parallel branches off main instead; a stack buys reviewable layering at
the cost of ordered merging, so only pay that cost when the dependency is real.

### Code Review

**As author**:
- Respond to all comments
- Don't take feedback personally
- Explain reasoning when disagreeing
- Mark conversations resolved
- Request re-review after changes

**As reviewer**:
- Be constructive and specific
- Ask questions rather than demand changes
- Acknowledge good work
- Distinguish: must-fix vs nice-to-have
- Review within 24 hours if possible

## Merge Strategies

### Merge Commit (Default)

**When to use**: Preserving complete branch history
```bash
git checkout main
git merge --no-ff feat/add-user-dashboard
```

**Pros**:
- Complete history preserved
- Easy to revert entire feature
- Clear feature boundaries

**Cons**:
- Many merge commits clutter history
- Harder to read linear history

### Squash and Merge

**When to use**: Cleaning up messy branch history
```bash
git checkout main
git merge --squash feat/add-user-dashboard
git commit -m "feat(dashboard): add user dashboard system"
```

**Pros**:
- Clean, linear history
- Single commit per feature
- Easy to read git log

**Cons**:
- Loses granular history
- Harder to revert partial work

### Rebase and Merge

**When to use**: Clean history with atomic commits
```bash
git checkout feat/add-user-dashboard
git rebase main
git checkout main
git merge --ff-only feat/add-user-dashboard
```

**Pros**:
- Linear history
- Preserves atomic commits
- No merge commits

**Cons**:
- Rewrites history (don't do on shared branches)
- More complex workflow

## Conflict Resolution

### Understanding Conflicts

**Conflict markers**:
```
<<<<<<< HEAD
// Current branch code
const user = getCurrentUser();
=======
// Incoming branch code
const user = fetchUser();
>>>>>>> feat/add-user-dashboard
```

### Resolution Strategies

**Manual resolution**:
```bash
# See conflicted files
git status

# Edit files to resolve conflicts
# Remove markers, keep correct code

# Stage resolved files
git add conflicted-file.ts

# Continue operation
git rebase --continue
# or
git merge --continue
```

**Choose theirs/ours**:
```bash
# Keep incoming changes (theirs)
git checkout --theirs conflicted-file.ts

# Keep current changes (ours)
git checkout --ours conflicted-file.ts

# Then continue
git add conflicted-file.ts
git rebase --continue
```

### Preventing Conflicts

**Strategies**:
- Keep branches short-lived
- Rebase frequently on main
- Coordinate with team on shared files
- Small, focused changes
- Clear code ownership
