# LazyGit Integration and Advanced Patterns

Detail for `git-manager`.

## LazyGit Integration

### Common LazyGit Workflows

**Starting LazyGit**:
```bash
# From project root
lazygit

# Or use alias: lg
lg
```

### LazyGit Key Bindings

**Status panel**:
- `space` - Stage/unstage file
- `a` - Stage all
- `c` - Commit
- `P` - Push
- `p` - Pull

**Branches panel**:
- `space` - Checkout branch
- `n` - New branch
- `d` - Delete branch
- `r` - Rebase
- `M` - Merge

**Commits panel**:
- `s` - Squash commit
- `r` - Reword commit
- `e` - Edit commit
- `d` - Delete commit
- `R` - Revert commit

**Files panel**:
- `space` - Stage changes
- `d` - Discard changes
- `e` - Edit file
- `o` - Open file
- `s` - Stash changes

### LazyGit Best Practices

**Staging workflow**:
```
1. Review changes in Files panel
2. Use arrow keys to navigate
3. Press 'space' to stage individual files
4. Or press 'a' to stage all
5. Press 'c' to commit
6. Write commit message
7. Press 'P' to push
```

**Interactive rebase**:
```
1. Go to Commits panel
2. Navigate to commits
3. Press 'e' to edit/reorder
4. Press 's' to squash
5. Press 'r' to reword
6. Push with force-with-lease
```

**Conflict resolution**:
```
1. LazyGit shows conflicts in red
2. Press 'e' to edit file
3. Resolve conflicts in editor
4. Return to LazyGit
5. Stage resolved files
6. Continue rebase/merge
```

## Advanced Patterns

### Git Stash

**Save work in progress**:
```bash
# Stash changes
git stash

# Stash with message
git stash save "WIP: redesign dashboard"

# List stashes
git stash list

# Apply latest stash
git stash apply

# Apply and remove stash
git stash pop

# Apply specific stash
git stash apply stash@{2}

# Drop stash
git stash drop stash@{0}
```

### Cherry-Picking

**Apply specific commits to another branch**:
```bash
# Get commit hash
git log

# Apply commit to current branch
git cherry-pick abc123

# Cherry-pick multiple commits
git cherry-pick abc123 def456

# Cherry-pick without committing
git cherry-pick --no-commit abc123
```

### Bisect (Find Bug Introduction)

**Binary search for problematic commit**:
```bash
# Start bisect
git bisect start

# Mark current commit as bad
git bisect bad

# Mark known good commit
git bisect good abc123

# Git checks out middle commit
# Test if bug exists

# Mark as good or bad
git bisect good  # or git bisect bad

# Repeat until bug commit found
# Reset when done
git bisect reset
```

### Reflog (Recover Lost Work)

**View all HEAD movements**:
```bash
# Show reflog
git reflog

# Recover deleted branch
git checkout -b recovered-branch abc123

# Undo reset
git reset --hard abc123
```
